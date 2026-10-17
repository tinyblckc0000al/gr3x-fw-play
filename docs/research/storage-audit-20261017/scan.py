"""Read-only research census; ARM-aligned decode can mistake data for instructions.
Not a reachability proof, Thumb analysis, or a safety qualification.
"""
from pathlib import Path
import hashlib,json,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_ARM
from capstone.arm import ARM_OP_IMM,ARM_OP_MEM,ARM_REG_PC
raw=Path('tools/gr3-film-mods/work/fw/rtos_iiix.bin').read_bytes()
base=0x53000000
spans=[(0x536ef61c,0x536ef6dc),(0x536ef6fc,0x536ef998),(0x536ef088,0x536ef140),(0x536ef99c,0x536ef9b8)]
md=Cs(CS_ARCH_ARM,CS_MODE_ARM);md.detail=True;md.skipdata=True
hits=[];listing=[]
for chunk in range(0,len(raw),1<<18):
 for i in md.disasm(raw[chunk:chunk+(1<<18)],base+chunk):
  if not i.id:continue
  if 0x536ef140<=i.address<0x536ef1e0:listing.append(f'{i.address:08x} {i.mnemonic} {i.op_str}')
  targets=[]
  if i.mnemonic.startswith(('b','bl')) and len(i.operands)==1 and i.operands[0].type==ARM_OP_IMM:
   targets.append(('branch',i.operands[0].imm))
  for op in i.operands:
   if op.type==ARM_OP_MEM and op.mem.base==ARM_REG_PC and not op.mem.index:
    targets.append(('pc-memory',i.address+8+op.mem.disp))
  for kind,target in targets:
   for lo,hi in spans:
    if lo<=target<hi:hits.append(dict(source=hex(i.address),target=hex(target),kind=kind,instruction=i.mnemonic+' '+i.op_str,source_in_reclaimed=any(a<=i.address<b for a,b in spans)))
words=[]
for off in range(0,len(raw)-3,4):
 w=struct.unpack_from('<I',raw,off)[0]
 if any(a<=w<b for a,b in spans):words.append([hex(base+off),hex(w)])
print(json.dumps(dict(input_sha256=hashlib.sha256(raw).hexdigest(),length=len(raw),hits=hits,aligned_words=words,entry_listing=listing),indent=2))
