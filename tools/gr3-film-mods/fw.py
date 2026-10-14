import struct, re
import os
S=os.environ.get('GR3_WORK', os.path.dirname(os.path.abspath(__file__)) + '/work')
R=open(S+'/fw/rtos.bin','rb').read()
BASE=0x53000000
SRC,DST,LEN=0x5407b540,0x55000000,0x3a080
def off(a):
    if DST<=a<DST+LEN: return SRC-BASE+a-DST
    return a-BASE
def rd(a,n): o=off(a); return R[o:o+n]
def w(a): return struct.unpack('<I',rd(a,4))[0]
def cstr(a):
    o=off(a); e=R.index(b'\0',o); return R[o:e].decode('latin1')
def find_all(b):
    return [BASE+m.start() for m in re.finditer(re.escape(b),R)]
def ptr_refs(a):
    p=struct.pack('<I',a); out=[]
    for m in re.finditer(re.escape(p),R):
        if m.start()%4==0: out.append(BASE+m.start())
    return out
def addr_of_off(o):
    if SRC-BASE<=o<SRC-BASE+LEN: return DST+o-(SRC-BASE)
    return BASE+o

import numpy as np
_W=np.frombuffer(R[:len(R)//4*4],dtype='<u4')
def _half(w): return ((w>>4)&0xF000)|(w&0xFFF)
def movw_xrefs(target):
    """ARM-mode MOVW/MOVT pairs (same reg, within 16 instrs) producing target."""
    lo=target&0xFFFF; hi=target>>16
    W=_W
    movw=(W&0x0FF00000)==0x03000000
    movt=(W&0x0FF00000)==0x03400000
    val=((W>>4)&0xF000)|(W&0xFFF)
    iw=np.nonzero(movw&(val==lo))[0]; out=[]
    for i in iw:
        rd=(W[i]>>12)&15
        for j in range(i+1,min(i+24,len(W))):
            if movt[j] and ((W[j]>>12)&15)==rd:
                if val[j]==hi: out.append(BASE+4*int(i))
                break
    return out
def lit_xrefs(target):
    return ptr_refs(target)

from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM
_md=Cs(CS_ARCH_ARM,CS_MODE_ARM)
def dis(a,n=40):
    o=off(a); out=[]
    for ins in _md.disasm(R[o:o+4*n],a):
        out.append(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
    return '\n'.join(out)
def func_start(a):
    # scan back for push {...lr}
    while a>BASE:
        x=w(a)
        if (x&0xFFFF4000)==0xE92D4000: return a
        if (x&0xFFFF0FFF)==0xE52D0004 and (x>>12)&15==14: return a  # str lr,[sp,#-4]!
        a-=4
    return None

def bl_callers(target):
    W=_W; idx=np.arange(len(W))
    isbl=(W&0x0F000000)==0x0B000000
    imm=(W&0x00FFFFFF).astype(np.int64)
    imm=np.where(imm&0x800000, imm-0x1000000, imm)
    dest=BASE+idx*4+8+imm*4
    return [BASE+4*int(i) for i in np.flatnonzero(isbl&(dest==target))]

def func_insns(f, maxn=3000):
    """Linear disassemble from f until next function prologue (skips data via capstone skipdata)."""
    md=Cs(CS_ARCH_ARM,CS_MODE_ARM); md.skipdata=True
    o=off(f); out=[]
    for ins in md.disasm(R[o:o+4*maxn],f):
        if ins.address>f+8 and ins.mnemonic=='push' and 'lr' in ins.op_str: break
        if ins.address>f+8 and ins.mnemonic=='mov' and ins.op_str=='ip, sp': break
        out.append(ins)
    return out
def calls(f):
    return [(i.address,int(i.op_str[1:],16)) for i in func_insns(f) if i.mnemonic in('bl','blx') and i.op_str.startswith('#')]
def strrefs(f):
    """strings loaded via movw/movt in function"""
    ins=func_insns(f); regs={}; out=[]
    for i in ins:
        if i.mnemonic=='movw':
            r,v=i.op_str.split(', #'); regs[r]=int(v,16)
        elif i.mnemonic=='movt':
            r,v=i.op_str.split(', #')
            if r in regs:
                a=(int(v,16)<<16)|regs[r]
                try:
                    s=cstr(a)
                    if len(s)>=3 and s.isprintable(): out.append((i.address,a,s))
                except Exception: pass
    return out

def vtable_for(name):
    """find typeinfo whose name ptr -> name string, then vtables (ptr to typeinfo at vt-4)"""
    res=[]
    for a in find_all(b'\0'+name.encode()+b'\0'):
        a+=1
        for ti_name_ref in ptr_refs(a):
            ti=ti_name_ref-4
            for vref in ptr_refs(ti):
                res.append((ti,vref+4))
    return res
