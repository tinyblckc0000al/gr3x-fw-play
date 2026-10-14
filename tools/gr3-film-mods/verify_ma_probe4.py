"""Emulated check of make_ma_probe4.py output: stock modes unchanged; each probe mode's CCA0 header
(info+0x120..0x13F) = Standard's with the designed OR mask, and no other change outside MultiAxial.
Usage: verify_ma_probe4.py stock.bin probe4.bin"""
import sys
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload
from run_tuning import setup, make
from make_ma_probe4 import PROBES

def rtos(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec, bytes(dec[0x10870:0x10c5e30])
(sd, _, S), (pd, pdec, P) = rtos(sys.argv[1]), rtos(sys.argv[2])
print('container sum32', hex(sum32(pd)), 'decoded sum32', hex(sum32(pdec)))
def run(r, t, st):
    e, obj, info, si = setup(stage=st, rtos=r)
    return np.frombuffer(make(e, obj, info, si, t, stage=st), 'u1')
ok = True
for st in (1, 0):
    for t in (11, 13, 18):
        s = (run(S, t, st) == run(P, t, st)).all(); ok &= s
        print(f'stage {st} tone {t}: identical to stock {s}')
    std = run(P, 11, st)
    for t, (name, off, mask) in PROBES.items():
        o = run(P, t, st); d = np.flatnonzero(o != std)
        hdr = o[0x120:0x140].view('<u4'); want = std[0x120:0x140].view('<u4').copy(); want[off // 4] |= mask
        outside = d[(d < 0x120) | ((d >= 0x140) & (d < 400)) | (d >= 2920)]
        g = (hdr == want).all() and len(outside) == 0; ok &= g
        print(f'stage {st} {name}: header {[hex(x) for x in hdr[:5]]}, changes outside MA {len(outside)} {"OK" if g else "FAIL"}')
print('ALL OK' if ok else 'FAILURES')
