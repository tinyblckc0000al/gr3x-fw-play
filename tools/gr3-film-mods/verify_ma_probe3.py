"""Emulated check of make_ma_probe3.py output: stock modes unchanged; probe modes differ from Standard
only in MultiAxial registers, with the designed thresholds, hue table, selectors and matrices; CC0CTL stays 1.
Usage: verify_ma_probe3.py stock.bin probe3.bin"""
import sys
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload
from run_tuning import setup, make
from make_ma_probe2 import matrix
from make_ma_probe3 import PROBES, TABLE_VALUE

def rtos(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec, bytes(dec[0x10870:0x10c5e30])
(sd, sdec, S), (pd, pdec, P) = rtos(sys.argv[1]), rtos(sys.argv[2])
print('container sum32', hex(sum32(pd)), 'decoded sum32', hex(sum32(pdec)))

def run(r, tone, stage):
    e, obj, info, si = setup(stage=stage, rtos=r)
    return np.frombuffer(make(e, obj, info, si, tone, stage=stage), 'u1')

MA = np.zeros(0x9000, bool); MA[400:2920] = True
mat_at = lambda m: 272 + 64 * (m // 5) + 10 * (m % 5)
ok = True
for stage in (1, 0):
    for tone in (11, 13, 18):
        same = (run(S, tone, stage) == run(P, tone, stage)).all(); ok &= same
        print(f'stage {stage} tone {tone}: identical to stock {same}')
    std = run(P, 11, stage); hs = std.view('<u2')
    for tone, (name, thr, table, sel) in PROBES.items():
        o = run(P, tone, stage); h = o.view('<u2')
        d = np.flatnonzero(o != std)
        outside = d[~MA[d]]
        sv = [int((h[240 + 2 * (i // 5) + (1 if i % 5 == 4 else 0)] >> (4 * (i % 5 if i % 5 < 4 else 0))) & 15) for i in range(20)]
        mats = [[int(v) for v in h[mat_at(m):mat_at(m) + 9]] for m in (0, 13, 59)]
        tab = h[1040:1460] & 0x3FF
        n_tab = int((tab == TABLE_VALUE).sum())
        good = len(outside) == 0 and (o[0x120] & 3) == 1 and sv == sel
        good &= mats == [[v & 0xFFF for v in matrix(m)] for m in (0, 13, 59)]
        good &= list(h[1428:1436]) == (thr if thr is not None else [4095] * 8)
        good &= (n_tab >= 300) == table
        ok &= good
        print(f'stage {stage} {name}: CC0CTL {o[0x120] & 3}, differ {len(d)} B (outside {len(outside)}), thr {list(map(int, h[1428:1431]))}.., '
              f'hue-table fields == {TABLE_VALUE}: {n_tab}, sel {sv[:4]}.. {"OK" if good else "FAIL"}')
print('ALL OK' if ok else 'FAILURES')
