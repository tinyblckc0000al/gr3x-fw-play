from pathlib import Path
import sys,hashlib,json,struct
root=Path('workspace/publishing/gr3x-fw-play').resolve()
sys.path.insert(0,str(root/'tools/gr3-film-mods'))
import codec_path
from gr4_editor.codec.container import inspect_container
from gr4_editor.codec.frames import decode_payload
items={}
for name,p in [('stock',root/'firmware/official-v160/fwdc243b.bin'),('candidate',root/'workspace/b2_iiix/out/fwdc243b-b241.bin')]:
 if not p.exists() and name=='stock':p=root/'firmware/official-v160/fwdc243b.bin'
 data=p.read_bytes();c=inspect_container(data);raw,_=decode_payload(data[128:c['payload_end']],c['decoded_size'])
 items[name]=(raw[0x10870:0x10c5e30],hashlib.sha256(data).hexdigest())
a,b=items['stock'][0],items['candidate'][0]
def get(r,addr,n):return r[addr-0x53000000:addr-0x53000000+n]
out={'firmware_sha256':{k:v[1] for k,v in items.items()},'raw_stock_sha256':hashlib.sha256(a).hexdigest(),'regions':[]}
for lo,n in [(0x53d453f8,2232),(0x53d39c8c,2300),(0x53dc2bf8,1440),(0x53d36400,1440),(0x53d45cb0,108),(0x53d3a588,240),(0x55019848,32)]:
 if lo>=0x55000000:continue
 x,y=get(a,lo,n),get(b,lo,n)
 out['regions'].append({'start':hex(lo),'size':n,'stock_zero':not any(x),'candidate_zero':not any(y),'changed_bytes':sum(i!=j for i,j in zip(x,y))})
for lo in [0x536ef618,0x536ef6dc,0x536ef998,0x536ef9b8]:
 out[hex(lo)]={k:get(v[0],lo,4).hex() for k,v in items.items()}
# Full-image ARM-aligned branch census. Data words may decode as false-positive branches.
hits=[]
for off in range(0,len(a)-3,4):
 w=struct.unpack_from('<I',a,off)[0]
 if w&0x0e000000 !=0x0a000000:continue
 imm=w&0xffffff
 if imm&0x800000:imm-=0x1000000
 target=0x53000000+off+8+imm*4
 if target==0x536ef088:hits.append(hex(0x53000000+off))
out['arm_branch_words_to_gaussian']=hits
out['MA_object_ROM_address']='0x54094d88'
out['MA_object_pointers']={k:[hex(x) for x in struct.unpack('<8I',get(v[0],0x54094d88,32))] for k,v in items.items()}
out['stock_aligned_words_into_MA_table']=[[hex(0x53000000+o),hex(struct.unpack_from('<I',a,o)[0])] for o in range(0,len(a)-3,4) if 0x53dc2bf8<=struct.unpack_from('<I',a,o)[0]<0x53dc3198]
print(json.dumps(out,indent=2))
