from pathlib import Path
import sys,json,hashlib
root=Path('workspace/publishing/gr3x-fw-play').resolve();sys.path.insert(0,str(root/'tools/gr3-film-mods'))
from emu import Emu,STOP
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn import arm_const as A
import codec_path
from gr4_editor.codec.container import inspect_container
from gr4_editor.codec.frames import decode_payload
stock=Path('tools/gr3-film-mods/work/fw/rtos_iiix.bin').read_bytes();binary=(root/'workspace/b2_iiix/out/fwdc243b-b241.bin').read_bytes();c=inspect_container(binary);dec,_=decode_payload(binary[128:c['payload_end']],c['decoded_size']);candidate=bytes(dec[0x10870:0x10c5e30]);spans=[(0x53d453f8,0x53d45cb0),(0x53d39c8c,0x53d3a588)];rows=[]
for val in [0,1,2,4,5]:
 for name,raw in [('stock',stock),('candidate',candidate)]:
  e=Emu(raw);obj=e.alloc(0x100);hits=[];mock={};transfers=[]
  def code(u,at,n,_):
   if at==0x53820074:raise RuntimeError('failure handler reached')
   if at!=STOP and not 0x53632898<=at<0x53633f54:
    result=1 if at in (0x537352b0,0x53735274) else 0
    mock[hex(at)]=result
    # Byte->halfword uploader writes a 64-entry stack buffer to these helpers.
    if at in (0x53735c80,0x53735cc0,0x537375a0):
     buf=u.reg_read(A.UC_ARM_REG_R3 if at==0x537375a0 else A.UC_ARM_REG_R1);data=bytes(u.mem_read(buf,32 if at==0x537375a0 else 128));transfers.append(dict(helper=hex(at),caller=hex(u.reg_read(A.UC_ARM_REG_LR)),data_sha256=hashlib.sha256(data).hexdigest(),nonzero_bytes=sum(x!=0 for x in data)))
    e._ret(result)
  def read(u,access,a,n,value,_):
   if any(a<hi and a+n>lo for lo,hi in spans):
    hits.append(dict(pc=hex(u.reg_read(A.UC_ARM_REG_PC)),address=hex(a),size=n,value=bytes(u.mem_read(a,n)).hex(),stock_value=stock[a-0x53000000:a-0x53000000+n].hex()))
  e.u.hook_add(UC_HOOK_CODE,code);e.u.hook_add(UC_HOOK_MEM_READ,read)
  if val==0:e.call(0x53633f38,obj,limit=3000000)
  else:e.call(0x53633e6c,obj,val,limit=3000000)
  bypc={}
  for h in hits:
   z=bypc.setdefault(h['pc'],dict(count=0,min=int(h['address'],16),end=0,changed_from_stock=0));z['count']+=1;z['min']=min(z['min'],int(h['address'],16));z['end']=max(z['end'],int(h['address'],16)+h['size']);z['changed_from_stock']+=h['value']!=h['stock_value']
  for z in bypc.values():z['min']=hex(z['min']);z['end']=hex(z['end'])
  rows.append(dict(image=name,parameter=val,entry='0x53633F38' if val==0 else '0x53633E6C',returned=True,mock_returns=mock,read_summary=bypc,overlap_reads=hits,transfers=transfers))
print(json.dumps(dict(assessment='COUNTEREXAMPLE_WITH_STUBBED_HARDWARE',stock_rtos_sha256=hashlib.sha256(stock).hexdigest(),candidate_bin_sha256=hashlib.sha256(binary).hexdigest(),rows=rows),indent=2))
