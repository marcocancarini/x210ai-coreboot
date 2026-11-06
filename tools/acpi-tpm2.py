import re,struct,sys
lines=open(sys.argv[1],errors='replace').read().split('\n')
start=[i for i,l in enumerate(lines) if l.startswith('TPM2 @')]
print('tabelle',len(start))
for s in start:
    out=bytearray()
    for l in lines[s+1:]:
        m=re.match(r'\s*[0-9A-Fa-f]{4,8}: ((?:[0-9A-Fa-f]{2} ){1,16})',l)
        if not m: break
        out+=bytes.fromhex(m.group(1))
    print('len',len(out),out[:4])
    print('control area %#x start method %d'%(struct.unpack_from('<Q',out,40)[0],struct.unpack_from('<I',out,48)[0]))
