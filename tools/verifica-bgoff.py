#!/usr/bin/env python3
"""Controlli sull'immagine Boot Guard off prima di scriverla. Solo lettura.

Uso: python3 -I tools/verifica-bgoff.py dump.bin out-controllo.bin out-bgoff.bin \
         [config.xml config-ricomposta.xml]

Esce con 0 solo se passano tutti i controlli:
  1. le tre immagini hanno la stessa misura e lo stesso descriptor;
  2. fuori dalla regione ME, controllo e bgoff sono identici al dump;
  3. tra controllo e bgoff cambiano solo i 3 byte attesi di UEP slot A;
  4. UEP in bgoff: firma, CRC giusto, profilo 0x18, flag 0, slot B vuoto;
  5. rispetto al dump, MFIT ha toccato solo i blocchi da 4 KiB attesi
     (con la 18.0, come il 2026-11-11);
  6. la catena di Boot Guard (KM, BPM, IBB) resta valida;
  7. se date le config, quella ricomposta differisce da quella del dump
     solo nel profilo di Boot Guard e nell'etichetta dell'harness.
Non stampa dati della macchina.
"""
import importlib.util
import os
import re
import struct
import subprocess
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location('uep', os.path.join(QUI, 'uep.py'))
uep = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uep)

# Blocchi che MFIT 18.0 riscrive su questa scheda: intestazioni $FPT e BPDT,
# FITC, CDMD, UEP. La tabella di layout a 0x4000 deve restare uguale al dump:
# se cambia, l'immagine e' stata costruita con la 18.1 o con altro.
BLOCCHI_ATTESI = {0x5000, 0x2a5000, 0x3a6000, 0x43d000, 0x43e000,
                  0x445000, 0x446000, 0x447000, 0x448000, 0x449000, 0x44a000}
UEP_CAMBIATI = {uep.UEP + 0x04, uep.UEP + 0x05, uep.UEP + 0x53}
PROFILO_OFF = 0x18

esito = []


def controllo(nome, ok, dettaglio=''):
    esito.append(ok)
    print('[%s] %s%s' % ('OK' if ok else 'FALLITO', nome, (': ' + dettaglio) if dettaglio else ''))


def regioni(b):
    fl0 = struct.unpack_from('<I', b, 0x14)[0]
    frba = ((fl0 >> 16) & 0xff) << 4
    out = {}
    for i, n in enumerate(['DESC', 'BIOS', 'ME']):
        r = struct.unpack_from('<I', b, frba + 4 * i)[0]
        base, lim = (r & 0x7fff) << 12, (((r >> 16) & 0x7fff) << 12) | 0xfff
        out[n] = (base, lim + 1)
    return out


def diversi(a, b, s=0, e=None):
    e = len(a) if e is None else e
    return [i for i in range(s, e) if a[i] != b[i]]


def normalizza(path):
    righe = []
    for r in open(path, encoding='utf-8', errors='replace'):
        if 'BtGuardProfileConfig' in r or 'HarnessLabel' in r or 'HarnessRevision' in r:
            continue
        righe.append(re.sub(r'Z:/work/job/[^/"]+/', 'Z:/work/job/X/', r))
    return righe


def main():
    if len(sys.argv) not in (4, 6):
        sys.exit(__doc__)
    dump, ctrl, bgoff = (open(p, 'rb').read() for p in sys.argv[1:4])

    # 1. misura e descriptor
    misure = {len(dump), len(ctrl), len(bgoff)}
    controllo('misura', misure == {32 << 20}, '%s byte' % sorted(misure))
    if len(misure) != 1:
        return
    reg = regioni(dump)
    me_s, me_e = reg['ME']
    controllo('descriptor identico', dump[:0x1000] == ctrl[:0x1000] == bgoff[:0x1000])
    controllo('regione ME dove atteso', (me_s, me_e) == (0x4000, 0x815000), '%#x-%#x' % (me_s, me_e))

    # 2. fuori dal ME nulla cambia
    for nome, img in (('controllo', ctrl), ('bgoff', bgoff)):
        fuori = diversi(dump, img, 0, me_s) + diversi(dump, img, me_e)
        controllo('%s identica al dump fuori dal ME' % nome, not fuori,
                  '%d byte diversi' % len(fuori) if fuori else '')

    # 3. controllo -> bgoff: solo i 3 byte di UEP
    d = set(diversi(ctrl, bgoff, me_s, me_e))
    controllo('controllo -> bgoff solo nei 3 byte di UEP', d == UEP_CAMBIATI,
              ', '.join('%#x' % i for i in sorted(d)))

    # 4. UEP
    a = bgoff[uep.UEP:uep.UEP + uep.LEN]
    crc_ok = struct.unpack_from('<H', a, 4)[0] == uep.crc16(a[6:])
    controllo('UEP slot A valido', a[:4] == b'$UEP' and crc_ok, uep.slot(bgoff, uep.UEP))
    controllo('UEP profilo Boot Guard Disabled', a[0x53] == PROFILO_OFF, '%#04x' % a[0x53])
    controllo('UEP flag +0x58 a 0', a[0x58] == 0, '%#04x' % a[0x58])
    sb = bgoff[uep.UEP + uep.SLOT:uep.UEP + uep.SLOT + uep.LEN]
    controllo('UEP slot B vuoto', sb == b'\xff' * uep.LEN)
    c = ctrl[uep.UEP:uep.UEP + uep.LEN]
    controllo('profilo invariato nel controllo', c[0x53] == dump[uep.UEP + 0x53], '%#04x' % c[0x53])

    # 5. blocchi toccati da MFIT
    blocchi = {i & ~0xfff for i in diversi(dump, bgoff, me_s, me_e)}
    extra = blocchi - BLOCCHI_ATTESI
    controllo('MFIT ha toccato solo i blocchi attesi', not extra,
              ('inattesi: ' + ', '.join('%#x' % x for x in sorted(extra))) if extra
              else '%d blocchi' % len(blocchi))
    controllo('tabella di layout a 0x4000 uguale al dump (MFIT 18.0)',
              dump[0x4000:0x5000] == bgoff[0x4000:0x5000])

    # 6. Boot Guard
    r = subprocess.run([sys.executable, '-I', os.path.join(QUI, 'analisi-bootguard.py'), sys.argv[3]],
                       capture_output=True, text=True)
    attese = ['firma PSS SHA-384: True', 'firma PSS SHA-256: True', 'autorizzata dal KM: True',
              'digest sha1: True', 'digest sha256: True', 'digest sha384: True']
    mancanti = [x for x in attese if x not in r.stdout]
    controllo('catena KM, BPM e IBB valida', r.returncode == 0 and not mancanti and 'False' not in r.stdout,
              ('mancano: ' + '; '.join(mancanti)) if mancanti else '')

    # 7. config
    if len(sys.argv) == 6:
        cfg, rid = sys.argv[4:6]
        prof = re.findall(r'<BtGuardProfileConfig value="([^"]*)"', open(rid, encoding='utf-8').read())
        controllo('config ricomposta con Boot Guard Disabled', prof == ['Boot Guard Disabled'], str(prof))
        a, b = normalizza(cfg), normalizza(rid)
        n = sum(1 for x, y in zip(a, b) if x != y) + abs(len(a) - len(b))
        controllo('config ricomposta uguale al resto', n == 0, '%d righe diverse' % n if n else '')


main()
print()
if esito and all(esito):
    print('ESITO: tutti i %d controlli superati' % len(esito))
    sys.exit(0)
print('ESITO: %d controlli falliti su %d. NON scrivere questa immagine.' % (esito.count(False), len(esito)))
sys.exit(1)
