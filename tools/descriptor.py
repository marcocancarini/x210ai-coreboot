import struct,sys
for p in sys.argv[1:]:
    b=open(p,'rb').read()
    print(p,len(b))
    sig=struct.unpack_from('<I',b,0x10)[0]
    print(' sig %08x'%sig)
    fl0,fl1,fl2=struct.unpack_from('<III',b,0x14)
    frba=((fl0>>16)&0xff)<<4; fmba=(fl1&0xff)<<4
    names=['DESC','BIOS','ME','GbE','PDR','DevExp1','BIOS2','?7','EC/BMC','DevExp2']
    for i in range(10):
        r=struct.unpack_from('<I',b,frba+4*i)[0]
        base=(r&0x7fff)<<12; lim=((r>>16)&0x7fff)<<12|0xfff
        if (r&0x7fff)<=((r>>16)&0x7fff): print('  FREG%d %-8s %08x-%08x'%(i,names[i],base,lim))
    for i in range(3):
        m=struct.unpack_from('<I',b,fmba+4*i)[0]
        rd=(m>>8)&0xfff; wr=(m>>20)&0xfff
        fmt=lambda v:[names[j] for j in range(10) if v>>j&1]
        print('  FLMSTR%d %08x read=%s write=%s'%(i+1,m,fmt(rd),fmt(wr)))
