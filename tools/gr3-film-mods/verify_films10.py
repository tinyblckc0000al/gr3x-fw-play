"""Offline check of a make_films10.py build against the stock file, by emulating ImageTuning Make (still and live view).

  * container/decoded sums; untouched modes (Standard, the monochromes, Positive, Negative) R2Y byte-identical to stock
  * each film: composite R/G/B gamma = fitted curves (Bleach: the expanded knot tables) for every sub-mode
  * RGB->YCbCr matrix (info+0x1180) = round(H P / 512) for the hue settings 4 (default), 0 and 8; Standard keeps H
  * CCA1 (info+0x1240) stock identity everywhere; R2Y differences vs Standard only in CCA0/gamma/CSP
Usage: verify_films10.py vivid.json retro.json hdr.json cross.json bleach.json stock.bin patched.bin
"""
import sys, json, struct
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload
from run_tuning import setup, make
from make_films10 import MODES, post_of
from film_cave import knots_of, expand
from make_film import q13_matrix

R2Y, CSP, CCA1 = 0x120, 0x120 + 0x1180, 0x1240      # offsets in the info block


def decode(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec


fits = [json.load(open(p)) for p in sys.argv[1:6]]
(s_raw, s_dec), (p_raw, p_dec) = decode(sys.argv[6]), decode(sys.argv[7])
print('container sum32', hex(sum32(p_raw)), 'decoded sum32', hex(sum32(p_dec)), 'len same', len(s_dec) == len(p_dec))
rt = lambda dec: bytes(dec[0x10870:0x10c5e30])
S, P = rt(s_dec), rt(p_dec)


def run(rtos, tone, stage=1, **si):
    e, obj, info, sinfo = setup(stage=stage, rtos=rtos)
    g = e.r32(obj + 0x17c)
    def x(e, st):
        for off, v in si.items():
            e.w8(st + int(off[1:], 16), v)
    out = make(e, obj, info, sinfo, tone, stage=stage, extra=x)
    u = lambda a: np.frombuffer(bytes(e.u.mem_read(a, 512)), '<u2').astype(int)
    return out, [u(g + o) for o in (0x2a08, 0x2c08, 0x2e08)], u(g)


def csp(out):
    v = [x & 0x1FF for x in struct.unpack('<9H', out[CSP:CSP + 18])]
    return np.array([x - 512 if x >= 256 else x for x in v]).reshape(3, 3)


def diff_ranges(a, b):
    d = np.flatnonzero(np.frombuffer(a, 'u1') != np.frombuffer(b, 'u1'))
    if not len(d):
        return []
    cuts = np.flatnonzero(np.diff(d) > 16)
    starts, ends = np.r_[d[0], d[cuts + 1]], np.r_[d[cuts], d[-1]]
    return [(int(s), int(e) + 1) for s, e in zip(starts, ends)]


ok = True
for stage in (1, 0):
    std_s, std_p = run(S, 11, stage)[0], run(P, 11, stage)[0]
    H = {h: csp(run(S, 11, stage, x77e=h)[0]) for h in (0, 4, 8)}
    for tone, name in ((11, 'Standard'), (13, 'Monotone'), (14, 'Soft Mono'), (15, 'Hard Mono'), (16, 'HiCon B&W'),
                       (17, 'Positive'), (22, 'Negative')):
        same = run(S, tone, stage)[0] == run(P, tone, stage)[0]
        ok &= same
        print(f'stage {stage} {name}: identical to stock {same}')
    for (name, tone, slots, *_), fit in zip(MODES, fits):
        curves = [np.array(c) for c in fit['presets'][0]['curves']]
        if name == 'bleach':
            curves = [expand(knots_of(c)) for c in curves]
        Pm = np.array(post_of(fit))
        subs = [{}]
        if tone == 20: subs += [dict(x788=1), dict(x788=2)]
        if tone == 21: subs += [dict(x797=1), dict(x797=2)]
        if tone == 18: subs += [dict(x786=2), dict(x786=3)]
        for si in subs:
            o, comp, base = run(P, tone, stage, **si)
            want = [np.interp(np.clip(base / 64, 0, 255), np.arange(256), c) for c in curves]
            err = max(np.abs(comp[i] - want[i]).max() for i in range(3))
            want_csp = np.floor((H[4] @ Pm + 256) / 512).astype(int)
            csp_ok = (csp(o) == want_csp).all()
            cca1_ok = o[CCA1:CCA1 + 18] == std_s[CCA1:CCA1 + 18]
            rng = [(hex(a - R2Y), b - a) for a, b in diff_ranges(std_p, o)]
            good = err <= 2 and csp_ok and cca1_ok
            ok &= good
            print(f'stage {stage} {name:6s} {si or ""}: curve err {err:.0f}/16384, CSP {"=" if csp_ok else "!="} H.P '
                  f'{csp(o).tolist()}, CCA1 stock {cca1_ok}, R2Y diff vs Standard at {rng} {"OK" if good else "FAIL"}')
        for h in (0, 8):
            o = run(P, tone, stage, x77e=h)[0]
            hue_ok = (csp(o) == np.floor((H[h] @ Pm + 256) / 512).astype(int)).all()
            ok &= hue_ok
            print(f'   hue {h}: CSP = H(hue).P {hue_ok}')
print('ALL OK' if ok else 'SOME FAILED')
