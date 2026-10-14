"""Offline check of a make_slots.py build against the stock file (emulated firmware functions).

  * container/decoded sums; only the RTOS section differs
  * image pipeline (ImageTuning Make, still and live view): every stock mode and sub-mode R2Y byte-identical to stock,
    also right after a film was rendered (library curve pointers restored); each film: CCA0 = stock Standard with the
    film's look matrix, composite R/G/B gamma = expanded knots, CSP = round(H P / 512) for hue 4/0/8
  * menu: value count, index <-> tone for sets No0/No1/No2 (stock part identical), names, icons, display codes and
    their strings/icons, the string getter stubs
  * adjustments: for each of the 18 Set*/GetDefaultValue* functions the code path taken for a film tone equals the
    one for PROXY, stock tones unchanged; the 27 rewritten checks give stock(PROXY) for film tones, stock otherwise
Usage: verify_slots.py stock.bin patched.bin name=fit.json ...   (same film order as the build)
"""
import sys, json, struct
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
import numpy as np
from gr4_editor.codec.container import inspect_container, sum32
from gr4_editor.codec.frames import decode_payload, section_rows
from run_tuning import setup, make
from emu import Emu, STOP
from unicorn import UC_HOOK_CODE
from unicorn import arm_const as A
from film_cave import knots_of, expand
from make_film import q13_matrix
import make_slots as M

R2Y, CSP = 0x120, 0x120 + 0x1180
ok = True


def check(cond, msg):
    global ok
    ok &= bool(cond)
    print(('OK   ' if cond else 'FAIL ') + msg)


def decode(path):
    d = open(path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    return d, dec


(s_raw, s_dec), (p_raw, p_dec) = decode(sys.argv[1]), decode(sys.argv[2])
films = [(a.split('=')[0], json.load(open(a.split('=', 1)[1]))) for a in sys.argv[3:]]
n = len(films)
check(sum32(p_raw) == 0 and sum32(p_dec) == 0 and len(s_dec) == len(p_dec), 'container and decoded sums 0, same length')
rows = {r['name']: r for r in section_rows(s_dec)}
changed = [nm for nm, r in rows.items() if s_dec[r['start']:r['end']] != p_dec[r['start']:r['end']]]
check(changed == ['RTOS', 'ICONBIN'], f'changed sections {changed}')
rt = lambda dec: bytes(dec[0x10870:0x10c5e30])
S, P = rt(s_dec), rt(p_dec)

# icons: other ids keep descriptor and pixels; the film ids are 40x40, inside their own (0x05-0x07) or 0x1D's pixels
CAT = 0x550020FC
def romw(r, a):
    o = (a - 0x55000000 + 0x5407B540 if a >= 0x55000000 else a) - 0x53000000
    return struct.unpack('<I', r[o:o + 4])[0]
def desc(r, i):
    d = romw(r, CAT + 4 * i) - 0x53000000
    return struct.unpack('<HHI', r[d:d + 8])
ib = rows['ICONBIN']['start'] + 16
allowed = [(ib + 4 * desc(S, i)[2], ib + 4 * desc(S, i)[2] + 4 * desc(S, i)[0] * desc(S, i)[1]) for i in M.ICON_IDS[:3] + (M.CARVE_FROM,)]
diff = np.flatnonzero(np.frombuffer(s_dec[ib:rows['ICONBIN']['end']], 'u1') != np.frombuffer(p_dec[ib:rows['ICONBIN']['end']], 'u1')) + ib
inside = all(any(lo <= x < hi for lo, hi in allowed) for x in diff[::97].tolist() + diff[-1:].tolist())
others = all(desc(S, i) == desc(P, i) for i in range(0x29F) if i not in M.ICON_IDS[:len(films)])
films_ok = all(desc(P, i)[:2] == (40, 40) and any(lo <= ib + 4 * desc(P, i)[2] and ib + 4 * desc(P, i)[2] + 6400 <= hi
                                                 for lo, hi in allowed) for i in M.ICON_IDS[:len(films)])
check(inside and others and films_ok, f'icons: {len(diff)} ICONBIN bytes changed, all inside HDF / GR IIIx-cert pixels; '
      f'other descriptors unchanged; film icons 40x40 in place')


# --- image pipeline ------------------------------------------------------------------------------------------------
class Pipe:
    def __init__(self, rtos, stage):
        self.e, self.obj, self.info, self.si = setup(stage=stage, rtos=rtos)
        self.stage = stage

    def run(self, tone, **si):
        e = self.e
        def x(e, st):
            for off, v in si.items():
                e.w8(st + int(off[1:], 16), v)
        out = make(e, self.obj, self.info, self.si, tone, stage=self.stage, extra=x)
        g = e.r32(self.obj + 0x17c)
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
    return [(int(s), int(e) + 1) for s, e in zip(np.r_[d[0], d[cuts + 1]], np.r_[d[cuts], d[-1]])]


STOCK_CASES = [(t, {}) for t in range(11, 23)] + [(21, dict(x797=1)), (21, dict(x797=2)), (18, dict(x786=2)),
                                                  (18, dict(x786=3)), (20, dict(x788=1)), (20, dict(x788=2))]
for stage in (1, 0):
    ps, pp = Pipe(S, stage), Pipe(P, stage)
    bad = [(t, si) for t, si in STOCK_CASES if ps.run(t, **si)[0] != pp.run(t, **si)[0]]
    check(not bad, f'stage {stage}: all stock modes/sub-modes identical to stock {bad or ""}')
    bad = []
    for t, si in STOCK_CASES:                      # film first, then the stock mode in the same emulator
        pp.run(M.FIRST_TONE, )
        if ps.run(t, **si)[0] != pp.run(t, **si)[0]:
            bad.append((t, si))
    check(not bad, f'stage {stage}: stock modes identical right after a film {bad or ""}')
    H = {h: csp(ps.run(11, x77e=h)[0]) for h in (0, 4, 8)}
    for k, (key, fit) in enumerate(films):
        tone = M.FIRST_TONE + k
        # reference: stock firmware, Standard with the film's matrix
        ref_rt = bytearray(S)
        q = q13_matrix(fit['matrix'])
        o = 0x53DC2754 - 0x53000000
        ref_rt[o:o + 18] = struct.pack('<9h', *q.ravel().tolist())
        ref = Pipe(bytes(ref_rt), stage).run(11)[0]
        out, comp, base = pp.run(tone)
        curves = [expand(knots_of(c)) for c in fit['presets'][0]['curves']]
        want = [np.interp(np.clip(base / 64, 0, 255), np.arange(256), c) for c in curves]
        err = max(np.abs(comp[i] - want[i]).max() for i in range(3))
        Pm = np.array(fit.get('post_q512', fit.get('cca1_q512')))
        csp_ok = all((csp(pp.run(tone, x77e=h)[0]) == np.floor((H[h] @ Pm + 256) / 512).astype(int)).all() for h in (0, 4, 8))
        rng = [(hex(a - R2Y), b - a) for a, b in diff_ranges(ref, out)]
        cca0_same = out[R2Y:R2Y + 0x100] == ref[R2Y:R2Y + 0x100]
        # adjustments: film = stock PROXY (Standard) with the film's matrix, except gamma and CSP
        pos_rt = bytearray(S)
        o = {11: 0x53DC2754, 17: 0x53DC272C}[M.PROXY] - 0x53000000
        pos_rt[o:o + 18] = struct.pack('<9h', *q.ravel().tolist())
        pos = Pipe(bytes(pos_rt), stage)
        adj_bad = []
        for prm in (dict(x77d=1), dict(x77d=7), dict(x77f=0), dict(x77f=8), dict(x780=1), dict(x780=8), dict(x781=0),
                    dict(x782=8), dict(x784=8), dict(x77d=6, x780=2, x77f=5)):
            a, b = pos.run(M.PROXY, **prm)[0], pp.run(tone, **prm)[0]
            r = [(x - R2Y, y - x) for x, y in diff_ranges(a, b)]
            if any(not (0x1180 <= x < 0x1192 or 0x2568 <= x < 0x4F68 or x == 0x818F) for x, _ in r):
                adj_bad.append((prm, [(hex(x), m) for x, m in r]))
        check(not adj_bad, f'stage {stage} {key}: saturation/key/contrast/HL/shadow/sharpness act as on PROXY {adj_bad[:2] or ""}')
        check(err <= 2 and csp_ok and cca0_same and not pp.e.asserts,
              f'stage {stage} {key} (tone {tone}): curve err {err:.0f}/16384, CSP=H.P {csp_ok}, first 0x100 R2Y bytes '
              f'(CCA0..) = Standard+film matrix {cca0_same}, R2Y diff vs that at {rng}, asserts {pp.e.asserts}')


# --- menu / names / icons ------------------------------------------------------------------------------------------
def ui_emu(rtos, set_index=0):
    e = Emu(rtos)
    e.extra_stubs.update({0x5320ad88: 0, 0x5320b31c: 0, 0x5320b7fc: 0, 0x532bd6d4: lambda e: set_index})
    return e


def obj_with(e, mode=0, tone=11, active_set=0):
    obj = e.alloc(0x100); ud = e.alloc(0xC00)
    e.w8(obj + 0x1b, mode); e.w32(obj + 4, ud)
    e.w8(ud + 0x1c0, active_set); e.w8(ud + 0x1c2, tone)
    return obj


for st in (0, 1, 2):
    es, ep = ui_emu(S, st), ui_emu(P, st)
    cnt = [(ep.call(0x532c2a9c, obj_with(ep, mode=m)), es.call(0x532c2a9c, obj_with(es, mode=m))) for m in (0, 1, 2)]
    check(cnt[0][0] == 12 + n and cnt[2][0] == 12 + n and cnt[1][0] == cnt[1][1] == 10,
          f'set {st}: value count still/movie/RAW dev = {[c[0] for c in cnt]} (stock {[c[1] for c in cnt]})')
    tones = [ep.call(0x532c2c80, obj_with(ep), i) for i in range(12 + n)]
    stock = [es.call(0x532c2c80, obj_with(es), i) for i in range(12)]
    check(tones[:12] == stock and tones[12:] == list(range(M.FIRST_TONE, M.FIRST_TONE + n)), f'set {st}: index->tone {tones}')
    back = [ep.call(0x532c2f08, obj_with(ep), t) for t in tones]
    check(back == list(range(12 + n)), f'set {st}: tone->index round trip')
    mv = [ep.call(0x532c2c80, obj_with(ep, mode=1), i) for i in range(10)]
    check(mv == [es.call(0x532c2c80, obj_with(es, mode=1), i) for i in range(10)], f'set {st}: movie list unchanged')

es, ep = ui_emu(S), ui_emu(P)
for fn, what in ((M.NAME_FN, 'name'), (M.ICON_FN, 'icon')):
    st = [es.call(fn, 0, t) for t in range(0, 33)]
    pt = [ep.call(fn, 0, t) for t in range(0, 33)]
    films_part = pt[M.FIRST_TONE:M.FIRST_TONE + n]
    want = [M.SID0 + k for k in range(n)] if what == 'name' else list(M.ICON_IDS[:n])
    others = [i for i in range(33) if not M.FIRST_TONE <= i < M.FIRST_TONE + n]
    check(films_part == want and all(st[i] == pt[i] for i in others), f'tone -> {what}: films {[hex(x) for x in films_part]}, rest stock')
for t in list(range(11, 23)) + list(range(M.FIRST_TONE, M.FIRST_TONE + n)) + [M.FIRST_TONE + n]:
    o_s, o_p = obj_with(es, tone=t), obj_with(ep, tone=t)
    a, b = es.call(0x5326c1cc, o_s), ep.call(0x5326c1cc, o_p)
    film = M.FIRST_TONE <= t < M.FIRST_TONE + n
    if not (b == (t if film else a)):
        check(False, f'display code of tone {t}: {b} (stock {a})')
check(True, 'GetStillDispImageControl: films -> own tone as display code, stock tones unchanged')
for fn, what in ((0x532a985c, "display string"), (0x532a9988, "display icon")):
    st = [es.call(fn, 0, c) for c in range(0, 33)]
    pt = [ep.call(fn, 0, c) for c in range(0, 33)]
    want = [M.SID0 + k for k in range(n)] if 'string' in what else list(M.ICON_IDS[:n])
    others = [i for i in range(33) if not M.FIRST_TONE <= i < M.FIRST_TONE + n]
    check(pt[M.FIRST_TONE:M.FIRST_TONE + n] == want and all(st[i] == pt[i] for i in others), f'{what}: films ok, rest stock')


# string getter stubs: called with r3 = language table, r7 = id
def find_bl(rtos, at):
    w = struct.unpack('<I', rtos[at - 0x53000000:at - 0x53000000 + 4])[0]
    return at + 8 + (((w & 0xFFFFFF) ^ 0x800000) - 0x800000) * 4


def text_at(e, entry):
    nchars, flag, _, ptr = struct.unpack('<BBHI', bytes(e.u.mem_read(entry, 8)))
    return bytes(e.u.mem_read(ptr, 2 * (nchars - 1))).decode('utf-16le'), flag


for load_at, reg in ((M.STR1_LOAD, 7), (M.STR2_LOAD, 3)):
    stub = find_bl(P, load_at)
    good = True
    for lang in (0, 5, 20):
        table = ep.r32(ep.r32(0x55002BAC + 4 * lang))
        lt = ep.r32(0x55002BAC + 4 * lang)
        for sid in (0x10c, 0x116, 0x311):
            u = ep.u
            u.reg_write(A.UC_ARM_REG_R3, lt); u.reg_write(A.UC_ARM_REG_R7, sid)
            u.reg_write(A.UC_ARM_REG_LR, STOP); u.reg_write(A.UC_ARM_REG_SP, 0x5F000000 - 0x100)
            u.emu_start(stub, STOP, count=100)
            good &= u.reg_read(getattr(A, f'UC_ARM_REG_R{reg}')) == ep.r32(lt + 4 * sid)
        names = []
        for k in range(n + 1):
            u = ep.u
            u.reg_write(A.UC_ARM_REG_R3, lt); u.reg_write(A.UC_ARM_REG_R7, M.SID0 + k)
            u.reg_write(A.UC_ARM_REG_LR, STOP)
            u.emu_start(stub, STOP, count=100)
            r = u.reg_read(getattr(A, f'UC_ARM_REG_R{reg}'))
            names.append(text_at(ep, r)[0] if r else None)
        good &= names == [M.FILMS[key] for key, _ in films] + [None]
    check(good, f'string getter stub at {load_at:#x}: stock ids unchanged, film ids -> {names}')


# --- adjustments ---------------------------------------------------------------------------------------------------
def path_of(rtos, f, tone, set_index, mode=0):
    """External addresses reached from Set*/GetDefaultValue* f (each one returns 0 at once)."""
    e = Emu(rtos)
    end = f + 4
    while struct.unpack('<I', rtos[end - 0x53000000:end - 0x53000000 + 4])[0] != 0xE1A0C00D:
        end += 4
    word = e.alloc(16); e.w32(word, e.alloc(0x100))
    stubs = {0x5320ad88: 0, 0x5320b31c: 0, 0x532bd6d4: set_index, 0x53525d5c: word, 0x53549ee8: tone}
    seen = []
    stub_lo, stub_hi = 0x536EF088, 0x536EF9B8
    pattern = e.alloc(0x1000)                       # returned by unknown calls (e.g. the defaults struct)
    e.u.mem_write(pattern, bytes(((i >> 1) ^ (i >> 9)) & 0xFF for i in range(0x1000)))

    def hook(u, at, size, _):
        if f <= at < end or stub_lo <= at < stub_hi or at == STOP:
            return
        if at in stubs:
            u.reg_write(A.UC_ARM_REG_R0, stubs[at])
        else:
            seen.append(at)
            u.reg_write(A.UC_ARM_REG_R0, pattern)
        u.reg_write(A.UC_ARM_REG_PC, u.reg_read(A.UC_ARM_REG_LR))
    e.u.hook_add(UC_HOOK_CODE, hook)
    obj = obj_with(e, mode=mode)
    r0 = e.call(f, obj, tone if 0x532C34E8 <= f else 0)  # GetDefaultValue*(obj, tone); Set*(obj, value)
    return seen, r0


bad = []
for f in M.PROXY_FUNCS:
    for st in (0, 1, 2):
        for t in list(range(11, 23)):
            if path_of(S, f, t, st) != path_of(P, f, t, st):
                bad.append((hex(f), st, t))
        want = path_of(S, f, M.PROXY, st)
        for t in (M.FIRST_TONE, M.FIRST_TONE + n - 1):
            if path_of(P, f, t, st) != want:
                bad.append((hex(f), st, t, 'film'))
check(not bad, f'18 adjustment functions x 3 sets: stock tones unchanged, film tones take PROXY ({M.PROXY}) path {bad or ""}')


class Img:          # minimal wrapper for make_slots.check_sites on a raw RTOS
    def __init__(self, r): self.r = r
    def rtos(self): return self.r


sites = M.check_sites(Img(S), M.PROXY)
bad = []
for at, setv, tail in sites:
    for t in (11, 12, 17, 22, 23, 24, M.FIRST_TONE, M.FIRST_TONE + n - 1, 200):
        for active in (0, 1, 2):
            for movie in (0, 1):
                res = []
                for rtos, tone in ((S, M.PROXY if t >= M.FIRST_TONE else t), (P, t)):
                    e = Emu(rtos)
                    e.extra_stubs[tail] = 1
                    obj = e.alloc(0x40); ud = e.alloc(0xC00)
                    e.w32(obj + 4, ud); e.w8(ud + 0x44, movie); e.w8(ud + 0x1c0, active)
                    for off in (0x1c2, 0x1c4, 0x1c6):
                        e.w8(ud + off, 11)
                    e.w8(ud + 0x1c2 + 2 * setv, tone)
                    res.append(e.call(at, obj))
                if res[0] != res[1]:
                    bad.append((hex(at), t, active, movie, res))
check(len(sites) == 27 and not bad, f'{len(sites)} PROXY checks: film tones act as PROXY, others stock {bad[:4] or ""}')
print('ALL OK' if ok else 'SOME FAILED')
