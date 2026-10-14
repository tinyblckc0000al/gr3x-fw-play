import sys; sys.path.insert(0,'.')
from run_tuning import *
import pickle
names={11:'Standard',12:'Vivid',13:'Monotone',14:'SoftMono',15:'HardMono',16:'HiConBW',17:'Positive',18:'Bleach',19:'Retro',20:'HDR',21:'Cross',22:'Negative'}
outs={}
for t in list(range(0,26)):
    e,obj,info,si=setup()
    try:
        outs[t]=make(e,obj,info,si,t)
    except Exception as ex:
        print(t,'ERR',ex); continue
    if e.asserts: print(t,'asserts',e.asserts)
pickle.dump(outs,open('outs.pkl','wb'))
base=outs[11]
def ranges(a,b):
    r=[];i=0;n=len(a)
    while i<n:
        if a[i]!=b[i]:
            j=i
            while j<n and (a[j]!=b[j] or (j+8<n and a[j:j+8]!=b[j:j+8])): j+=1
            r.append((i,j)); i=j
        else: i+=1
    return r
for t,o in outs.items():
    rs=ranges(base,o)
    print(t,names.get(t,''),[(hex(a-0x120),b-a) for a,b in rs][:12])
