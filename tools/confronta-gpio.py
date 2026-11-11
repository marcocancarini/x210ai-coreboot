#!/usr/bin/env python3
"""Confronta la configurazione dei pin lasciata dal BIOS originale con il gpio.c del port.

Uso: python3 -I tools/confronta-gpio.py pinctrl-stock.txt gpio.c [gpio_early.c ...]

pinctrl-stock.txt si ottiene col BIOS originale avviato:
  sudo sh -c 'cat /sys/kernel/debug/pinctrl/*/pins' > pinctrl-stock.txt

Dal registro DW0 di ogni pin ricava funzione (NFn o GPIO), direzione e livello.
I pin che Linux chiama col nome della funzione (CNV_BTEN, ESPI_CS1_B...) vengono
riportati al numero GPP contando dal vicino con nome numerico nello stesso gruppo.
Stampa i pin diversi e le uscite del BIOS che il port non configura.
"""
import re
import sys


def stato(dw0):
    pm = (dw0 >> 10) & 7
    if pm:
        return 'NF%d' % pm
    tx, rx = not dw0 & (1 << 8), not dw0 & (1 << 9)
    return 'GPO=%d' % (dw0 & 1) if tx else ('GPI' if rx else 'spento')


def leggi_bios(path):
    pins = []
    for riga in open(path):
        m = re.match(r'pin (\d+) \((\S+)\) \S+ (?:GPIO|mode \d) (0x[0-9a-f]+)', riga)
        if m:
            pins.append((int(m.group(1)), m.group(2), int(m.group(3), 16)))
    numerici = {}
    for p, nome, _ in pins:
        m = re.match(r'GPP_([A-Z])_(\d+)$', nome)
        if m:
            numerici[p] = (m.group(1), int(m.group(2)))

    def gpp(p):
        if p in numerici:
            return numerici[p]
        for d in range(1, 32):
            if p - d in numerici:
                g, k = numerici[p - d]
                return g, k + d
            if p + d in numerici:
                g, k = numerici[p + d]
                return g, k - d
        return None

    massimo = {}
    for g, k in numerici.values():
        massimo[g] = max(massimo.get(g, 0), k)

    def gpp_entro_gruppo(p):
        # oltre l'ultimo pin numerico del gruppo si e' in un altro gruppo (es. VGPIO)
        k = gpp(p)
        return k if k and 0 <= k[1] <= massimo[k[0]] else None

    return [(nome, gpp(p), gpp_entro_gruppo(p), stato(dw0)) for p, nome, dw0 in pins]


def leggi_port(paths):
    port = {}
    for path in paths:
        for riga in open(path):
            m = re.search(r'(PAD_\w+)\(GPP_([A-Z])0*(\d+)\s*,\s*([^)]*)\)', riga)
            if not m:
                continue
            macro, g, k, args = m.groups()
            a = [x.strip() for x in args.split(',')]
            if macro.startswith('PAD_NC'):
                s = 'NC'
            elif 'GPO' in macro:
                s = 'GPO=%s' % a[0]
            elif 'NF' in macro:
                s = next((x for x in a if x.startswith('NF')), 'NF?')
            elif 'GPI' in macro:
                s = 'GPI'
            else:
                s = macro
            port[(g, int(k))] = (s, riga.strip()[:90])
    return port


def uguale(bios, port):
    return bios == port or (bios == 'spento' and port == 'NC')


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    bios = leggi_bios(sys.argv[1])
    port = leggi_port(sys.argv[2:])
    confrontati = diversi = 0
    for nome, grezzo, k, s in bios:
        # il numero ricostruito vale se il port ha quel pin, altrimenti solo entro il gruppo
        p = port.get(grezzo) if grezzo else None
        k = grezzo if p else k
        if p is None:
            if s.startswith('GPO'):
                print('solo nel BIOS: %-22s %-9s %s' % (nome, 'GPP_%s%02d' % k if k else '?', s))
            continue
        confrontati += 1
        if not uguale(s, p[0]):
            diversi += 1
            print('diverso:       %-22s GPP_%s%02d BIOS %-7s port %-7s %s' % (nome, k[0], k[1], s, p[0], p[1]))
    print('\n%d pin confrontati, %d diversi' % (confrontati, diversi))


main()
