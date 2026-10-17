from pathlib import Path
import sys,json,hashlib
root=Path('workspace/publishing/gr3x-fw-play').resolve();sys.path.insert(0,str(root/'tools/gr3-film-mods'))
from run_tuning import setup,make
from unicorn import UC_HOOK_MEM_READ,UC_HOOK_CODE
from unicorn import arm_const as A
import codec_path
from gr4_editor.codec.container import inspect_container
from gr4_editor.codec.frames import decode_payload
stock=Path('tools/gr3-film-mods/work/fw/rtos_iiix.bin').read_bytes();d=(root/'workspace/b2_iiix/out/fwdc243b-b241.bin').read_bytes();c=inspect_container(d);dec,_=decode_payload(d[128:c['payload_end']],c['decoded_size']);candidate=bytes(dec[0x10870:0x10c5e30]);rows=[]
for stage in [0,1]:
 for tone in range(11,23):
  outputs={}
  for name,r in [('stock',stock),('candidate',candidate)]:
   e,obj,info,si=setup(stage=stage,rtos=r);reads=set();flags=[]
   def read(u,access,a,n,v,_):
    if 0x53d36400<=a<0x53d369a0 or 0x53dc2bf8<=a<0x53dc3198:reads.add((a,n))
   def code(u,at,n,_):
    if at==0x536df484:flags.append(u.mem_read(u.reg_read(A.UC_ARM_REG_R1)+0x94,1)[0])
   e.u.hook_add(UC_HOOK_MEM_READ,read);e.u.hook_add(UC_HOOK_CODE,code)
   outputs[name]=make(e,obj,info,si,tone,stage=stage)[0x120:0x120+0x1200]
   rows.append(dict(stage=stage,tone=tone,image=name,calc_flag94=flags,read_count=len(reads),read_min=hex(min(a for a,n in reads)) if reads else None,read_end=hex(max(a+n for a,n in reads)) if reads else None,asserts=e.asserts))
  same=outputs['stock']==outputs['candidate']
  for row in rows[-2:]:row['r2y_prefix_equal']=same
print(json.dumps(dict(scope='existing tuning harness; 12 factory tones x still/liveview; helper stubs inherited from setup',rows=rows),indent=2))
