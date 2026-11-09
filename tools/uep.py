"""Analisi della partizione UEP del ME (0x448000-0x44a000, due slot da 4 KiB).

Uso: python3 -I tools/uep.py immagine.bin [altra.bin ...]

Per ogni immagine stampa i due slot: firma, CRC salvato e ricalcolato,
profilo di Boot Guard (+0x53) e flag +0x58. Il CRC e' CRC-16/CCITT-FALSE
(poly 0x1021, init 0xFFFF, senza riflessione) sui byte 0x06-0x208,
individuato confrontando dump, ricostruzione di controllo e Boot Guard off.
Non stampa l'hash della chiave OEM.
"""
import struct
import sys

UEP = 0x448000
SLOT = 0x1000
LEN = 0x208


def crc16(data):
    c = 0xFFFF
    for b in data:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x1021) & 0xFFFF if c & 0x8000 else (c << 1) & 0xFFFF
    return c


def slot(d, off):
    r = d[off:off + LEN]
    if r == b'\xff' * LEN:
        return 'vuoto (FF)'
    sig = r[:4]
    stored = struct.unpack_from('<H', r, 4)[0]
    calc = crc16(r[6:])
    stato = 'valida' if sig == b'$UEP' else 'invalidata' if sig == b'\0\0\0\0' else 'firma ' + sig.hex()
    return ('%s, CRC %04x %s, profilo +0x53=%02x, flag +0x58=%02x'
            % (stato, stored, 'ok' if stored == calc else 'ERRATO (calcolato %04x)' % calc, r[0x53], r[0x58]))


for path in sys.argv[1:]:
    d = open(path, 'rb').read()
    print(path)
    print('  slot A 0x448000:', slot(d, UEP))
    print('  slot B 0x449000:', slot(d, UEP + SLOT))
    a = bytearray(d[UEP:UEP + LEN])
    if a[:4] == b'$UEP' and a[0x58] == 0:
        a[0x58] = 1
        print('  se il ME ripete l\'aggiornamento: slot A con +0x58=01 e CRC %04x,'
              ' slot B = slot A attuale con firma azzerata' % crc16(a[6:]))
