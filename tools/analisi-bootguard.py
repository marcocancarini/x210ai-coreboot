#!/usr/bin/env python3
# Solo lettura. Controlla la catena di Boot Guard in un dump e, se lanciato sulla
# scheda, decodifica lo stato del ME. Non stampa dati della macchina.
# Uso: python3 -I analisi-bootguard.py dump.bin
import hashlib, os, struct, sys

ALG = {0x04: "sha1", 0x0b: "sha256", 0x0c: "sha384"}
b = open(sys.argv[1], "rb").read()
BASE = 0x100000000 - len(b)


def mgf(seed, n, hn):
    out, c = b"", 0
    while len(out) < n:
        out += hashlib.new(hn, seed + struct.pack(">I", c)).digest()
        c += 1
    return out[:n]


def pss(mod, sig, msg, hn):
    size = len(mod)
    em = pow(int.from_bytes(sig, "big"), 0x10001, int.from_bytes(mod, "little")).to_bytes(size, "big")
    hl = hashlib.new(hn).digest_size
    if em[-1] != 0xbc:
        return False
    masked, h = em[: size - hl - 1], em[size - hl - 1 : size - 1]
    db = bytearray(x ^ y for x, y in zip(masked, mgf(h, len(masked), hn)))
    db[0] &= 0x7f
    salt = bytes(db[db.find(b"\x01") + 1 :])
    return hashlib.new(hn, b"\0" * 8 + hashlib.new(hn, msg).digest() + salt).digest() == h


def key(s):
    # s punta alla firma: versione, algoritmo, chiave, schema, blocco firma.
    bits = struct.unpack_from("<H", b, s + 4)[0]
    n = bits // 8
    mod = b[s + 10 : s + 10 + n]
    return bits, mod, b[s + 10 + n + 7 : s + 10 + n + 7 + n]


fit = struct.unpack_from("<Q", b, len(b) - 0x40)[0] - BASE
if b[fit : fit + 8] != b"_FIT_   ":
    sys.exit("FIT non trovata")
voci = {}
for i in range(1, struct.unpack_from("<I", b, fit + 8)[0] & 0xffffff):
    e = fit + 16 * i
    voci.setdefault(b[e + 14] & 0x7f, []).append(struct.unpack_from("<Q", b, e)[0] - BASE)
print("FIT a %#x, tipi %s" % (fit, sorted(hex(t) for t in voci)))

if 0x0b not in voci or 0x0c not in voci:
    print("Nessun KM o BPM nella FIT: immagine non firmata per Boot Guard")
    sys.exit()

km, bpm = voci[0x0b][0], voci[0x0c][0]
s = km + struct.unpack_from("<H", b, km + 12)[0]
bits, mod, sig = key(s)
oem = hashlib.sha384(mod + struct.pack("<I", 0x10001)).hexdigest()
print("KM a %#x, RSA-%d, firma PSS SHA-384: %s" % (km, bits, pss(mod, sig, b[km:s], "sha384")))
print("Hash chiave OEM: %s... presente nel ME a %s" % (oem[:16], [
    hex(i) for i in range(0x4000, 0x815000) if b[i : i + 48] == bytes.fromhex(oem)]))
digest_bpm = b[km + 0x24 : km + 0x44]

pm = b.find(b"__PMSG__", bpm, bpm + 0x800)
bits, mod, sig = key(pm + 12)
print("BPM a %#x, RSA-%d, firma PSS SHA-256: %s" % (bpm, bits, pss(mod, sig, b[bpm : pm + 12], "sha256")))
print("Chiave BPM autorizzata dal KM:", hashlib.sha256(mod).digest() == digest_bpm)

ib = b.find(b"__IBBS__", bpm, bpm + 0x800)
q = b.find(bytes.fromhex("0c003000"), ib, ib + 0x200)
digest = {}
for _ in range(4):
    a, n = struct.unpack_from("<HH", b, q)
    digest[a] = b[q + 4 : q + 4 + n]
    q += 4 + n
q += 8
segmenti = []
for _ in range(b[q - 1]):
    fl, base, n = struct.unpack_from("<xxHII", b, q)
    q += 12
    if not fl & 1:
        segmenti.append((base - BASE, n))
dati = b"".join(b[o : o + n] for o, n in segmenti)
print("IBB:", [(hex(o), hex(n)) for o, n in segmenti])
for a, hn in ALG.items():
    print("  digest %s: %s" % (hn, hashlib.new(hn, dati).digest() == digest[a]))

p = "/sys/class/mei/mei0/fw_status"
if os.path.exists(p):
    h = [int(x, 16) for x in open(p).read().split()]
    print("HFSTS1 %08x: stato %d, manufacturing %d, errore %d" % (h[0], h[0] & 15, h[0] >> 4 & 1, h[0] >> 12 & 15))
    print("HFSTS3 %08x: SKU %d" % (h[2], h[2] >> 4 & 7))
    print("HFSTS6 %08x: FPF scritti %d, variabili bloccate %d" % (h[5], h[5] >> 30 & 1, h[5] >> 21 & 1))
