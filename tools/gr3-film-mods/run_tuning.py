import sys; sys.path.insert(0,'.')
from emu import *

DEFAULTS = {**{o: 4 for o in (0x77d,0x77e,0x77f,0x780,0x781,0x782,0x784,0x787,0x792,0x793,0x794)}, 0x783: 1, 0x786: 1, 0x798: 1}

def setup(stage=1, rtos=None):
    e = Emu() if rtos is None else Emu(rtos)
    for f in (0x536decb4, 0x536e4634, 0x536e4de4, 0x536e5070, 0x536e7348, 0x536eaf80, 0x536ec3e0, 0x536eb0b0, 0x536e9d1c):
        e.extra_stubs[f] = 0
    obj = e.alloc(0x400); cfg = e.alloc(0x1000)
    e.w32(obj, 0x53dbd8a0)
    e.call(0x536da1fc, obj, cfg)
    e.call(0x536da62c, obj, cfg)
    e.w32(obj, 0x53dbd8a0)
    info = e.alloc(0x9000)
    si = e.alloc(0x80000)
    e.w8(info + 0x82ac, stage)
    e.w32(info + 0x82d0, si)
    return e, obj, info, si

def make(e, obj, info, si, tone, stage=1, extra=None):
    st = si + (0x71248 if stage else 0)
    for off_, v in DEFAULTS.items(): e.w8(st + off_, v)
    e.w8(st + 0x77c, tone)
    if extra: extra(e, st)
    e.call(0x536dd8f0, obj, info)
    return bytes(e.u.mem_read(info, 0x9000))

if __name__ == '__main__':
    e, obj, info, si = setup()
    out = make(e, obj, info, si, 11)
    print('asserts', e.asserts, 'svcs', len(e.svcs))
    print('nonzero bytes in out', sum(1 for b in out if b))
