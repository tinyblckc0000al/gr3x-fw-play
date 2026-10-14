"""Emulated check of make_ma_probe2.py output: stock modes unchanged, probe modes differ from Standard
only in the CC0CTL byte (info+0x120) and MultiAxial registers, with the designed CC0CTL/selectors/matrices.
Usage: verify_ma_probe2.py stock.bin probe2.bin"""
import sys
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload
from run_tuning import setup, make
from make_ma_probe2 import PROBES, matrix

def rtos(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec, bytes(dec[0x10870:0x10c5e30])
(sd, sdec, S), (pd, pdec, P) = rtos(sys.argv[1]), rtos(sys.argv[2])
print('container sum32', hex(sum32(pd)), 'decoded sum32', hex(sum32(pdec)))

def run(r, tone, stage):
    e, obj, info, si = setup(stage=stage, rtos=r)
    return np.frombuffer(make(e, obj, info, si, tone, stage=stage), 'u1')

MA = np.zeros(0x9000, bool); MA[0x120] = True; MA[400:2920] = True
ok = True
for stage in (1, 0):
    for tone in (11, 13, 18):
        same = (run(S, tone, stage) == run(P, tone, stage)).all(); ok &= same
        print(f'stage {stage} tone {tone}: identical to stock {same}, CC0CTL {run(P, tone, stage)[0x120] & 3}')
    std = run(P, 11, stage)
    for tone, (name, ctl, sel, ctl0) in PROBES.items():
        o = run(P, tone, stage)
        d = np.flatnonzero(o != std)
        outside = d[~MA[d]]
        h = o.view('<u2')
        sv = [(h[240 + 2 * (i // 5) + (1 if i % 5 == 4 else 0)] >> (4 * (i % 5 if i % 5 < 4 else 0))) & 15 for i in range(20)]
        mat_at = lambda m: 272 + 64 * (m // 5) + 10 * (m % 5)
        mats = [[int(v) for v in h[mat_at(m):mat_at(m) + 9]] for m in (0, 1, 13, 59)]
        want = [[v & 0xFFF for v in matrix(m)] for m in (0, 1, 13, 59)]
        good = len(outside) == 0 and (o[0x120] & 3) == ctl and sv == sel and mats == want
        good &= (h[1424] & 0x3F) == (ctl0 or 0)
        ok &= good
        print(f'stage {stage} {name}: CC0CTL {o[0x120] & 3}, bytes differ from Standard {len(d)} (outside {len(outside)}), '
              f'sel {[int(x) for x in sv[:5]]}.., ctl0 {h[1424] & 0x3F}, m0 {mats[0][::4]} m13 {mats[2][::4]} {"OK" if good else "FAIL"}')
print('ALL OK' if ok else 'FAILURES')
