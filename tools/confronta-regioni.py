import sys
base=open(sys.argv[1],'rb').read()
regs=[('DESC',0,0x4000),('ME',0x4000,0x815000),('DevExp2',0x815000,0x1200000),('BIOS',0x1200000,0x2000000)]
for p in sys.argv[2:]:
    b=open(p,'rb').read(); print(p.split('/')[-1],len(b))
    for n,s,e in regs:
        d=[i for i in range(s,e) if i<len(b) and base[i]!=b[i]]
        if not d: print(' ',n,'identica'); continue
        blk=sorted({i&~0xfff for i in d})
        ff=sum(1 for i in d if b[i]==0xff)
        print(' ',n,len(d),'byte',hex(d[0]),'-',hex(d[-1]),'blocchi4K',len(blk),'di cui a FF',ff,[hex(x) for x in blk[:10]])
