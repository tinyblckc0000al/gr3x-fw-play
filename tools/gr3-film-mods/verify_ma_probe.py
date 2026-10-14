"""Emulated check of make_ma_probe.py output: stock modes unchanged, probe modes differ from Standard
only in MultiAxial registers, and those registers hold the designed boundaries/selectors/control/matrices.
Usage: verify_ma_probe.py stock.bin probe.bin"""
import sys, struct
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload
from run_tuning import setup, make
from make_ma_probe import PROBES, LEVELS

def rtos(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec, bytes(dec[0x10870:0x10c5e30])
(sd, sdec, S), (pd, pdec, P) = rtos(sys.argv[1]), rtos(sys.argv[2])
print('container sum32', hex(sum32(pd)), 'decoded sum32', hex(sum32(pdec)))

def run(r, tone, stage):
    e, obj, info, si = setup(stage=stage, rtos=r)
    def x(e, st): e.w8(st + 0x797, 0)
    return np.frombuffer(make(e, obj, info, si, tone, stage=stage, extra=x), '<u2').astype(int)

# MultiAxial register halfwords: YCC 208-216, bounds 224-239, selectors 240-247, matrices 272-1100, table 1040-1400, control 1280-1460
MA = np.zeros(0x9000 // 2, bool); MA[200:1460] = True
ok = True
for stage in (1, 0):
    for tone in (11, 13, 18):
        same = (run(S, tone, stage) == run(P, tone, stage)).all(); ok &= same
        print(f'stage {stage} tone {tone}: identical to stock {same}')
    std = run(P, 11, stage)
    for tone, (name, bounds, sel, ctl0, thr) in PROBES.items():
        o = run(P, tone, stage)
        d = np.flatnonzero(o != std)
        outside = d[~MA[d]]
        good = len(outside) == 0
        good &= list(o[224:240]) == bounds
        sv = [(o[240 + 2 * (i // 5) + (1 if i % 5 == 4 else 0)] >> (4 * (i % 5 if i % 5 < 4 else 0))) & 15 for i in range(20)]
        good &= sv == sel
        good &= (o[1424] & 0x3F) == (ctl0 if ctl0 is not None else 0)
        if thr: good &= list(o[1428:1436]) == thr
        good &= o[272] == round(1024 * LEVELS[0]) and o[282] == round(1024 * LEVELS[1])
        ok &= good
        print(f'stage {stage} {name}: regs differ from Standard {len(d)} (outside MA {len(outside)}), bounds {list(o[224:228])}.., sel {sv[:6]}.., ctl0 {o[1424] & 0x3F}, thr {list(o[1428:1431])}.., m0/m1 gain {o[272]},{o[282]} {"OK" if good else "FAIL"}')
print('ALL OK' if ok else 'FAILURES')
