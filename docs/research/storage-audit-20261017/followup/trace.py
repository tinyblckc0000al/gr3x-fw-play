from pathlib import Path
import struct,json
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
p=Path('tools/gr3-film-mods/work/fw/rtos_iiix.bin');raw=p.read_bytes();base=0x53000000
md=Cs(CS_ARCH_ARM,CS_MODE_ARM);md.skipdata=True
def dis(a,n):return [f'{i.address:08x} {i.mnemonic} {i.op_str}' for i in md.disasm(raw[a-base:a-base+n],a)]
targets=[0x53633e6c,0x536ef140,0x536e4470,0x536df484,0x536df55c]
calls={hex(x):[] for x in targets};pairs=[];words=[];pending={}
for off in range(0,len(raw)-3,4):
 a=base+off;w=struct.unpack_from('<I',raw,off)[0]
 if w&0x0e000000==0x0a000000:
  v=w&0xffffff;v=v-(0x1000000 if v&0x800000 else 0);t=a+8+v*4
  if t in targets:calls[hex(t)].append(hex(a))
 if w&0x0ff00000==0x03000000:
  pending[(w>>12)&15]=(a,((w>>16)&15)<<12|(w&0xfff))
 elif w&0x0ff00000==0x03400000:
  r=(w>>12)&15
  if r in pending:
   prev,lo=pending[r];v=((((w>>16)&15)<<12|(w&0xfff))<<16)|lo
   if a-prev<=64 and (0x55019700<=v<0x55019b00 or v in targets or v in [0x53dc2bf8,0x53d36400,0x54094d88]):pairs.append(dict(at=hex(prev),high_at=hex(a),value=hex(v),register=r))
 if 0x55019700<=w<0x55019b00 or w in targets or w in [0x53dc2bf8,0x53d36400,0x54094d88]:words.append([hex(a),hex(w)])
result=dict(direct_call_candidates=calls,nearby_ma_address_pairs=pairs,aligned_word_candidates=words,caller_disassembly={addr:dis(int(addr,16)-96,160) for group in calls.values() for addr in group},random_function_disassembly=dis(0x536ef140,0x878),ma_function_disassembly=dis(0x536e4470,0x118))
print(json.dumps(result,indent=2))
