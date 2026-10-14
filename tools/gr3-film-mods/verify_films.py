"""Offline check of a make_films.py output against the stock file: container/decoded sums,
untouched modes byte-identical in emulated R2Y output, and for each replaced mode the composite
R/G/B gamma = fitted curves and the record's look matrix = fitted matrix.
Usage: verify_films.py vivid.json retro.json hdr.json cross.json stock.bin patched.bin"""
import sys, json, struct
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload, section_rows
from run_tuning import setup, make
from make_films import MODES
from make_film import q13_matrix

def decode(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec

fits = [json.load(open(p)) for p in sys.argv[1:5]]
(s_raw, s_dec), (p_raw, p_dec) = decode(sys.argv[5]), decode(sys.argv[6])
print('container sum32', hex(sum32(p_raw)), 'decoded sum32', hex(sum32(p_dec)), 'len same', len(s_dec) == len(p_dec))
diff = np.flatnonzero(np.frombuffer(s_dec, 'u1') != np.frombuffer(p_dec, 'u1'))
rows = section_rows(p_dec)
print('decoded bytes changed', len(diff), 'sections', sorted({r['name'] for r in rows for o in diff if r['start'] <= o < r['end']}))
rt = lambda dec: bytes(dec[0x10870:0x10c5e30])
S, P = rt(s_dec), rt(p_dec)

def run(rtos, tone, stage=1, sub=0, hdr=0):
    e, obj, info, si = setup(stage=stage, rtos=rtos)
    g = e.r32(obj + 0x17c)
    def x(e, st):
        e.w8(st + 0x797, sub); e.w8(st + 0x788, hdr)
    out = make(e, obj, info, si, tone, stage=stage, extra=x)
    u = lambda a: np.frombuffer(bytes(e.u.mem_read(a, 512)), '<u2').astype(int)
    return out, [u(g + o) for o in (0x2a08, 0x2c08, 0x2e08)], u(g), e.u.mem_read(si + 0x38a98, 1)[0], bytes(e.u.mem_read(obj + 0x1f0, 2))

ok = True
for stage in (1, 0):
    for tone, name in ((11, 'Standard'), (13, 'Monotone'), (17, 'Positive'), (18, 'Bleach'), (22, 'Negative')):
        same = run(S, tone, stage)[0] == run(P, tone, stage)[0]
        ok &= same
        print(f'stage {stage} {name}: identical to stock {same}')
    for (name, tone, *_), fit in zip(MODES, fits):
        for sub, hdr in ((0, 0), (2, 0), (0, 1), (0, 2)) if tone == 20 or tone == 21 else ((0, 0),):
            o, comp, base, sel, hdrfld = run(P, tone, stage, sub, hdr)
            want = [np.interp(np.clip(base / 64, 0, 255), np.arange(256), np.array(c)) for c in fit['presets'][0]['curves']]
            err = max(np.abs(comp[i] - want[i]).max() for i in range(3))
            q = q13_matrix(fit['matrix']).ravel().tolist()
            std = run(P, 11, stage)[0]
            nd = np.flatnonzero(np.frombuffer(o, 'u1') != np.frombuffer(std, 'u1'))
            good = err <= 2
            ok &= good
            print(f'stage {stage} {name} sub{sub} 0x788={hdr}: selector {sel}, curve err {err:.0f}/16384, '
                  f'hdr field {hdrfld.hex()}, R2Y diff vs Standard {len(nd)} bytes {"OK" if good else "FAIL"}')

# names and icons, read back from the decoded patched image
from make_names import STRINGS, N_LANG, STRING_ID, NAMES
from make_icons import CATALOG, ICON_ID
from gr3patch import BASE, DSRC, DDST, DLEN
rtos0 = {r['name']: r for r in rows}['RTOS']['start'] + 16
ib = {r['name']: r for r in rows}['ICONBIN']['start'] + 16
def at(dec, a):
    if DDST <= a < DDST + DLEN: a = DSRC + a - DDST
    return rtos0 + a - BASE
W = lambda dec, a: struct.unpack('<I', dec[at(dec, a):at(dec, a) + 4])[0]
def txt(dec, a):
    o = at(dec, a); e = o
    while dec[e:e + 2] != b'\0\0': e += 2
    return dec[o:e].decode('utf-16le')
for mode, sid in STRING_ID.items():
    got = set()
    for lang in range(N_LANG):
        e = W(p_dec, W(p_dec, STRINGS + 4 * lang) + 4 * sid)
        n = p_dec[at(p_dec, e)]
        t = txt(p_dec, W(p_dec, e + 4))
        got.add((t, n == len(t) + 1))
    good = got == {(NAMES[mode], True)}
    ok &= good
    print(f'name {mode}: {got} {"OK" if good else "FAIL"}')
for mode, iid in ICON_ID.items():
    d = W(p_dec, CATALOG + 4 * iid); w_, h_, o_ = struct.unpack('<HHI', p_dec[at(p_dec, d):at(p_dec, d) + 8])
    a, b = s_dec[ib + 4 * o_: ib + 4 * o_ + w_ * h_ * 4], p_dec[ib + 4 * o_: ib + 4 * o_ + w_ * h_ * 4]
    print(f'icon {mode} {iid:#x} {w_}x{h_}: changed {a != b}')
    ok &= a != b
print('ALL OK' if ok else 'FAILURES')
