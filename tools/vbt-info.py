import struct,sys
for p in sys.argv[1:]:
    b=open(p,'rb').read()
    print(p,len(b),b[:20])
    if b[:4]!=b'$VBT': print(' non valido'); continue
    ver,hl,size=struct.unpack_from('<HHH',b,20)
    bdb=struct.unpack_from('<I',b,0x18+4)[0] if False else None
    i=b.find(b'BIOS_DATA_BLOCK')
    v,hs,bs=struct.unpack_from('<HHH',b,i+16)
    print(' bdb ver',v,'offset',hex(i),'bdb size',bs)
    o=i+hs; bl={}
    while o<i+bs-3:
        id_=b[o]; sz=struct.unpack_from('<H',b,o+1)[0]
        if id_==0: break
        bl[id_]=b[o+3:o+3+sz]; o+=3+sz
    print(' blocchi',sorted(bl))
    if 40 in bl: print(' panel_type',bl[40][0], 'opts',bl[40][:8].hex())
    if 2 in bl: print(' general',len(bl[2]))
