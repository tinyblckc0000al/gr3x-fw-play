"""Offline check of a make_film.py output: container/decoded sums, diff extent, and emulated R2Y
output (Cross presets 0-2 vs Standard/HDR) against the stock file.
Usage: verify_film.py fit.json stock.bin patched.bin"""
import sys, json, struct
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload, section_rows
from run_tuning import setup, make

def decode(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec

fit = json.load(open(sys.argv[1]))
(s_raw, s_dec), (p_raw, p_dec) = decode(sys.argv[2]), decode(sys.argv[3])
print('container sum32', hex(sum32(p_raw)), 'decoded sum32', hex(sum32(p_dec)), 'len same', len(s_dec) == len(p_dec))
diff = np.flatnonzero(np.frombuffer(s_dec, 'u1') != np.frombuffer(p_dec, 'u1'))
print('decoded bytes changed', len(diff), 'sections', sorted({r['name'] for r in section_rows(p_dec) for o in diff[:: max(1, len(diff)//50)] if r['start'] <= o < r['end']}))
rt = lambda dec: bytes(dec[0x10870:0x10c5e30])

def run(rtos, tone, preset=0):
    e, obj, info, si = setup(rtos=rtos)
    g = e.r32(obj + 0x17c)
    def x(e, st):
        e.w8(si + 0x38a98, 1 if tone == 21 else 0); e.w8(st + 0x797, preset)
    out = make(e, obj, info, si, tone, extra=x)
    u = lambda a: np.frombuffer(bytes(e.u.mem_read(a, 512)), '<u2').astype(int)
    cca0 = [((v >> 0) & 0xfff) for v in struct.unpack('<9H', out[0x140:0x152])]
    return out, [u(g + o) for o in (0x2a08, 0x2c08, 0x2e08)], u(g)

S, P = rt(s_dec), rt(p_dec)
for tone, name in ((11, 'Standard'), (20, 'HDR')):
    a, b = run(S, tone)[0], run(P, tone)[0]
    print(name, 'R2Y output identical to stock:', a == b)
for k in range(3):
    o_s, c_s, base = run(S, 21, k)
    o_p, c_p, _ = run(P, 21, k)
    want = [np.interp(np.clip(base / 64, 0, 255), np.arange(256), np.array(c)) for c in fit['presets'][k]['curves']]
    err = max(np.abs(c_p[i] - want[i]).max() for i in range(3))
    print(f'Cross preset {k}: R2Y block changed {o_s != o_p}; composite curves vs fit max err {err:.0f}/16384; '
          f'CCA0 stock {list(struct.unpack("<9h", o_s[0x140:0x152]))} -> {list(struct.unpack("<9h", o_p[0x140:0x152]))}')
