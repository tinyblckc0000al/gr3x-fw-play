import sys; sys.path.insert(0,'.')
from run_tuning import *
from diffmodes_lib import ranges
tone=int(sys.argv[1]) if len(sys.argv)>1 else 11
e,obj,info,si=setup(); base=make(e,obj,info,si,tone)
for o in range(0x77d,0x799):
    for v in (0,8):
        e,obj,info,si=setup()
        out=make(e,obj,info,si,tone,extra=lambda e,st,o=o,v=v: e.w8(st+o,v))
        rs=ranges(base,out)
        if rs: print(hex(o),v,[(hex(a-0x120),b-a) for a,b in rs][:6])
