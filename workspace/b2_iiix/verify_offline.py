#!/usr/bin/env python3
"""Independent offline verification for an IIIx film build (contrast with verify_slots16.py):

  * container codec: sums, zero-change roundtrip exact, decoded payload sizes
  * byte-level diff: how many payload bytes changed and in which sections
  * rendering with the camera's own code (Unicorn): R2Y output per mode vs stock;
    stock modes (11 Standard, 12 Vivid, 17 Positive, 21 Cross, 22 Negative) must be
    byte-identical to stock; a film tone must differ (that is the point).

Run from anywhere:
  python workspace/b2_iiix/verify_offline.py stock.bin built.bin [name=fit.json ...]

For the B2.1 preserve-Cross build, tone 21's R2Y diff must be 0 (its 9 library
curves are untouched), where the previous 8-preset build showed 2144.
"""
import sys, os
import numpy as np

FM = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tools/gr3-film-mods')
sys.path.insert(0, FM)
import codec_path  # noqa: F401
from gr4_editor.codec.container import inspect_container, repair_last_word, sum32
from gr4_editor.codec.frames import decode_payload, section_rows, framed_container
from gr4_editor.firmware import _repack_frames
from run_tuning import setup, make

R2Y, BASE, DSRC, DDST, DLEN, RT0 = 0x120, 0x53000000, 0x5407B540, 0x55000000, 0x3A080, 0x10870


def decode_of(path):
    raw = open(path, 'rb').read()
    info = inspect_container(raw)
    dec, _ = decode_payload(raw[128:info['payload_end']], info['decoded_size'])
    return raw, dec


def roundtrip_exact(raw, dec):
    tgt = repair_last_word(bytes(dec))
    payload, _ = _repack_frames(raw, dec, tgt, growth=False)
    return framed_container(raw, payload, tgt) == raw


def section_of(diff_off, rows):
    for nm in ('RTOS', 'ICONBIN'):
        r = rows[nm]
        if r['start'] <= diff_off < r['end']:
            return nm
    return '?'


class Pipe:
    def __init__(self, rtos, stage=1):
        self.e, self.obj, self.info, self.si = setup(stage=stage, rtos=rtos)

    def run(self, tone, **si):
        def x(e, st):
            for off, v in si.items():
                e.w8(st + int(off[1:], 16), v)
        return bytes(make(self.e, self.obj, self.info, self.si, tone, stage=1, extra=x))


def main():
    stock_p, built_p = sys.argv[1], sys.argv[2]
    s_raw, s_dec = decode_of(stock_p)
    b_raw, b_dec = decode_of(built_p)

    for who, raw, dec in (('官方', s_raw, s_dec), ('自建', b_raw, b_dec)):
        ok_csum = sum32(repair_last_word(bytes(dec))) == 0
        rt = roundtrip_exact(raw, dec)
        print(f'{who}文件: {len(raw)} B  容器校验={"OK" if ok_csum else "FAIL"}  零改动往返一致={rt}')

    print(f'payload 大小: 官方={len(s_dec)} 自建={len(b_dec)}')
    rows = {r['name']: r for r in section_rows(s_dec)}
    off = np.flatnonzero(np.frombuffer(s_dec, 'u1') != np.frombuffer(b_dec, 'u1'))
    print()
    print(f'payload 差异字节数 = {len(off)}')
    from collections import Counter
    dist = Counter(section_of(int(o), rows) for o in off)
    print(f'差异分布(按段): {dict(dist)}')
    print(f'差异范围: {hex(int(off[0]))} .. {hex(int(off[-1]))}')
    print()
    rt = lambda dec: bytes(dec[RT0:0x10c5e30])
    S, P = rt(s_dec), rt(b_dec)
    n_rt = int(np.flatnonzero(np.frombuffer(S, 'u1') != np.frombuffer(P, 'u1')).size)
    print(f'RTOS 差异字节数 = {n_rt}')
    print()

    print('用相机自己的代码(Unicorn)对比每个槽的调参输出:')
    cs, cp = Pipe(S), Pipe(P)
    cs.run(12); cp.run(12)                       # matched warm-up (first emulated render differs: lazy init)
    checks = [(11, 'Standard', False), (12, 'Vivid', False), (17, 'Positive', False),
              (21, 'Cross', False), (22, 'Negative', False), (25, 'Portra(胶片,应不同)', True)]
    ok = True
    for tone, label, expect_diff in checks:
        a, b = cs.run(tone), cp.run(tone)
        d = int(np.flatnonzero(np.frombuffer(a, 'u1') != np.frombuffer(b, 'u1')).size)
        good = (d == 0) != expect_diff           # stock tones identical, film tone different
        ok &= good
        star = '' if good else '  <-- 意外!'
        print(f'  tone {tone:2d} {label:22s} R2Y 差异={d:5d}{star}')
    # tone 21 under the x797 adjustment variants as well (the preserve-Cross build must stay identical)
    for si in ({'x797': 1}, {'x797': 2}):
        a, b = cs.run(21, **si), cp.run(21, **si)
        d = int(np.flatnonzero(np.frombuffer(a, 'u1') != np.frombuffer(b, 'u1')).size)
        ok &= d == 0
        print(f'  tone 21 Cross x797={si["x797"]} R2Y 差异={d}')
    print()
    print('ALL OK' if ok else 'FAILED')


if __name__ == '__main__':
    main()