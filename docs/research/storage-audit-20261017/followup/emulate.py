"""Read-only function-level traces. Uploader hardware helpers are stubbed.
This models selected CPU paths, not camera DMA/boot/scheduling.
"""
from pathlib import Path
import sys,json,hashlib,struct
root=Path('workspace/publishing/gr3x-fw-play').resolve();sys.path.insert(0,str(root/'tools/gr3-film-mods'))
from emu import Emu,STOP
from unicorn import UC_HOOK_CODE,UC_HOOK_MEM_READ
from unicorn import arm_const as A
import codec_path
from gr4_editor.codec.container import inspect_container
from gr4_editor.codec.frames import decode_payload
raw=Path('tools/gr3-film-mods/work/fw/rtos_iiix.bin').read_bytes()
d=(root/'workspace/b2_iiix/out/fwdc243b-b241.bin').read_bytes();c=inspect_container(d);dec,_=decode_payload(d[128:c['payload_end']],c['decoded_size']);patched=bytes(dec[0x10870:0x10c5e30])
spans=[(0x53d453f8,0x53d45cb0),(0x53d39c8c,0x53d3a588)]
upload=[]
for v in range(7):
 e=Emu(raw);obj=e.alloc(0x100);reads=set();stubs=set();errors=[]
 def hook(u,at,size,_):
  if at==0x53820074:errors.append(hex(at));u.emu_stop();return
  if at!=STOP and not 0x53632898<=at<0x53633f38:
   stubs.add(hex(at));e._ret(1 if at in (0x537352b0,0x53735274) else 0)
 def read(u,access,a,n,val,_):
  if 0x53d30000<=a<0x53d50000:reads.add((a,n))
 e.u.hook_add(UC_HOOK_CODE,hook);e.u.hook_add(UC_HOOK_MEM_READ,read)
 e.call(0x53633e6c,obj,v,limit=3000000)
 hit=[(hex(a),n) for a,n in sorted(reads) if any(a<hi and a+n>lo for lo,hi in spans)]
 upload.append(dict(parameter=v,returned=True,span_overlap_reads=hit,distinct_data_reads=len(reads),stubbed_helper_entries=sorted(stubs),errors=errors,reads=[[hex(a),n] for a,n in sorted(reads)]))
ma=[]
for flag in [0,1]:
 outputs={}
 for name,r in [('stock',raw),('candidate',patched)]:
  e=Emu(r);obj=e.alloc(0x1000);cfg=e.alloc(0x1000);out=e.alloc(0x4000);reads=set()
  e.w32(cfg+0xc,0x53dc2ba0);e.w8(cfg+0x94,flag)
  def read(u,access,a,n,val,_):
   if 0x53d36400<=a<0x53d369a0 or 0x53dc2bf8<=a<0x53dc3198 or 0x55019848<=a<0x55019868:reads.add((a,n))
  e.u.hook_add(UC_HOOK_MEM_READ,read)
  e.call(0x536e4470,obj,cfg,out)
  data=bytes(e.u.mem_read(out,0x4000));outputs[name]=data
  table=[(a,n) for a,n in reads if 0x53d36400<=a<0x53d369a0 or 0x53dc2bf8<=a<0x53dc3198]
  ma.append(dict(input_flag_94=flag,image=name,returned=True,output_sha256=hashlib.sha256(data).hexdigest(),asserts=e.asserts,zero_table_distinct_reads=len(table),zero_table_min=hex(min(a for a,n in table)) if table else None,zero_table_end_exclusive=hex(max(a+n for a,n in table)) if table else None,read_program_counters_note='reads records addresses and sizes; instruction PCs not retained',reads=[[hex(a),n] for a,n in sorted(reads)]))
 for row in ma[-2:]:
  row['stock_candidate_output_equal']=outputs['stock']==outputs['candidate']
  row['output_diff_offsets']=[hex(i) for i,(a,b) in enumerate(zip(outputs['stock'],outputs['candidate'])) if a!=b]
# Preserve counterexamples as evidence; assess caller reachability separately.
print(json.dumps(dict(assessment='BOUNDED_CPU_EMULATION_HARDWARE_HELPERS_STUBBED',stock_rtos_sha256=hashlib.sha256(raw).hexdigest(),candidate_bin_sha256=hashlib.sha256(d).hexdigest(),uploader=upload,ma=ma),indent=2))
