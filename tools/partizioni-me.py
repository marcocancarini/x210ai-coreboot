import struct,sys
a=open(sys.argv[1],'rb').read(); c=open(sys.argv[2],'rb').read(); g=open(sys.argv[3],'rb').read()
def diffs(x,y,s,e):
    o=[]
    for p in range(s,e,0x1000):
        q=min(p+0x1000,e)
        if x[p:q]!=y[p:q]: o+= [j for j in range(p,q) if x[j]!=y[j]]
    return o
ME=(0x4000,0x815000)
hits=[]; i=ME[0]
while True:
    i=a.find(b'$FPT',i,ME[1])
    if i<0: break
    hits.append(i); i+=4
print('$FPT a',[hex(h) for h in hits])
ents=[]
if hits:
    i=hits[0]; base=i; n=struct.unpack_from('<I',a,i+4)[0]; print('entries',n)
    if n<64:
        for k in range(n):
            e=i+32+k*32; nm=a[e:e+4].decode('latin1').rstrip('\0'); off,sz=struct.unpack_from('<II',a,e+8)
            if off not in(0,0xffffffff) and sz not in(0,0xffffffff): ents.append((base+off,sz,nm))
ents.sort()
for off,sz,nm in ents: print('  %-5s %#x-%#x'%(nm,off,off+sz))
print('-- blocchi cambiati dump->controllo')
dc=diffs(a,c,*ME); dg=diffs(c,g,*ME)
for b in sorted({j&~0xfff for j in dc}):
    n=sum(1 for j in dc if j&~0xfff==b); own=[nm for off,sz,nm in ents if off<=b<off+sz]
    print('  %#x %4d byte %s'%(b,n,own))
print('-- controllo->bgoff',[(hex(j),hex(c[j]),hex(g[j])) for j in dg])
print('-- contesto 0x448000', a[0x448000:0x448060].hex())
print('-- ctrl    0x448000', c[0x448000:0x448060].hex())
print('-- bgoff   0x448000', g[0x448000:0x448060].hex())
