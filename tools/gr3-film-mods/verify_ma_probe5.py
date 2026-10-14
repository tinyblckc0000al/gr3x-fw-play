"""Emulated check of make_ma_probe5.py output: stock modes unchanged; every probe mode differs from Standard only in
MultiAxial registers; Positive carries the GR IV bounds/selectors/control and the marker matrices; each ablation mode
differs from Positive only in the register range of the field it resets.
Usage: verify_ma_probe5.py stock.bin probe5.bin"""
import sys
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload
from run_tuning import setup, make
from make_ma_probe5 import PROBES, G4, marker


def rtos(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec, bytes(dec[0x10870:0x10c5e30])


(sd, _, S), (pd, pdec, P) = rtos(sys.argv[1]), rtos(sys.argv[2])
print('container sum32', hex(sum32(pd)), 'decoded sum32', hex(sum32(pdec)))


def run(r, tone, stage):
    e, obj, info, si = setup(stage=stage, rtos=r)
    return np.frombuffer(make(e, obj, info, si, tone, stage=stage), 'u1')


MA = np.zeros(0x9000, bool); MA[400:2920] = True          # MultiAxial register bytes (as rounds 1-4)
mat_at = lambda m: 272 + 64 * (m // 5) + 10 * (m % 5)      # halfword index of matrix m
MAT_HW = set(h for m in range(60) for h in range(mat_at(m), mat_at(m) + 9))
RANGES = {None: set(), 'bounds': set(range(224, 240)), 'ctl0': {1424}, 'thresholds': set(range(1428, 1436)),
          'strength': set(range(1436, 1451)), 'selectors': set(range(240, 248))}
ok = True
for stage in (1, 0):
    for tone in (11, 13, 18):
        same = (run(S, tone, stage) == run(P, tone, stage)).all(); ok &= same
        print(f'stage {stage} tone {tone}: identical to stock {same}')
    std = run(P, 11, stage)
    pos = run(P, 17, stage); hp = pos.view('<u2')
    mk = marker()
    good = list(hp[224:240] & 0xFFF) == G4['bounds']
    sv = [int((hp[240 + 2 * (i // 5) + (1 if i % 5 == 4 else 0)] >> (4 * (i % 5 if i % 5 < 4 else 0))) & 15) for i in range(20)]
    good &= sv == G4['selectors']
    good &= all(list(hp[mat_at(m):mat_at(m) + 9] & 0xFFF) == [v & 0xFFF for v in mk[9 * m:9 * m + 9]] for m in range(60))
    good &= int(hp[1424] & 0x3F) == G4['control'][0] and list(hp[1428:1436] & 0xFFF) == G4['control'][1:9]
    print(f'stage {stage} Positive: bounds {list(map(int, hp[224:228]))}.. sel {sv[:6]}.. ctl0 {int(hp[1424] & 0x3F)} '
          f'thr {list(map(int, hp[1428:1432]))}.. tail {list(map(int, hp[1436:1451]))} {"OK" if good else "FAIL"}')
    ok &= good
    for tone, (name, mats, reset) in PROBES.items():
        o = run(P, tone, stage)
        d = np.flatnonzero(o != std)
        outside = d[~MA[d]]
        good = len(outside) == 0 and (o[0x120] & 3) == 1 and len(d) > 0
        if tone != 17:
            dh = set(np.flatnonzero(o.view('<u2') != hp).tolist())
            allowed = RANGES[reset]
            good &= len(dh) > 0 and dh <= allowed
            extra = f', vs Positive {len(dh)} hw in {reset}'
        else:
            extra = ''
        ok &= good
        print(f'stage {stage} {name}: CC0CTL {o[0x120] & 3}, differ from Standard {len(d)} B (outside MA {len(outside)}){extra} '
              f'{"OK" if good else "FAIL"}')
print('ALL OK' if ok else 'FAILURES')
