#!/usr/bin/env python3
"""One-command, read-only qualification of B2.4.1. See VERIFICATION.md."""
import argparse
import datetime
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FM = ROOT / 'tools/gr3-film-mods'
sys.path.insert(0, str(FM))
import verification as V

STOCK = ROOT / 'firmware/official-v160/fwdc243b.bin'
DEFAULT = HERE / 'out/fwdc243b-b241.bin'
STAGES = ('selftest', 'structure', 'mutations', 'playback', 'crop_icons', 'references', 'rebuild', 'regression')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def decode(path):
    import codec_path  # noqa: F401
    from gr4_editor.codec.container import inspect_container, sum32
    from gr4_editor.codec.frames import decode_payload, section_rows
    raw = Path(path).read_bytes()
    info = inspect_container(raw)
    decoded, _ = decode_payload(raw[128:info['payload_end']], info['decoded_size'])
    V.require(sum32(raw) == 0 and sum32(decoded) == 0, 'original container/decoded checksum failed')
    rows = {r['name']: r for r in section_rows(decoded)}
    r = rows['RTOS']
    return decoded, decoded[r['start'] + 16:r['end']], rows


def structure(candidate):
    V.require(sha(STOCK) == V.STOCK_SHA, 'wrong stock firmware')
    V.require(sha(candidate) == V.RELEASE_SHA, 'candidate is not the frozen B2.4.1 release')
    stock, sr, rows = decode(STOCK)
    patched, pr, prows = decode(candidate)
    V.require(rows == prows, 'section layout changed')
    V.check_playback(pr)
    V.check_protected(sr, pr)
    # Check all payload changes; the final sum word is a container field.
    allowed = [(rows[n]['start'], rows[n]['end']) for n in ('RTOS', 'ICONBIN')]
    allowed.append((len(stock) - 4, len(stock)))
    print('payload changed bytes', V.check_changes(stock, patched, allowed))
    def descriptor(icon):
        ptr = V.word(sr, 0x5407B540 + 0x20FC + 4 * icon)
        return __import__('struct').unpack('<HHI', V.read(sr, ptr, 8))
    ib, end = rows['ICONBIN']['start'] + 16, rows['ICONBIN']['end']
    icon_ranges = []
    for icon in (5, 6, 7, 0x1D):
        width, height, offset = descriptor(icon)
        icon_ranges.append((4 * offset, 4 * offset + 4 * width * height))
    print('ICONBIN changed bytes, exhaustive', V.check_changes(stock[ib:end], patched[ib:end], icon_ranges))
    print('PASS frozen identity, checksums, mappings, conditions, known ISP windows and region 2')


def mutations(candidate):
    _, stock, _ = decode(STOCK)
    _, good, _ = decode(candidate)
    V.check_playback(good)
    V.check_protected(stock, good)
    cases = [('LS condition', 0x535C251B, 0x70, V.check_playback),
             ('table pointer', 0x532B44E4, 1, V.check_playback),
             ('factory mapping', 0x53D3A2F0, 1, V.check_playback),
             ('film mapping', 0x53D3A2FC, 1, V.check_playback),
             ('region 2', 0x53D445B4, 1, lambda r: V.check_protected(stock, r)),
             ('ISP window', 0x53D36ABC, 1, lambda r: V.check_protected(stock, r))]
    for label, address, mask, check in cases:
        broken = bytearray(good)
        broken[address - V.BASE] ^= mask
        try:
            check(broken)
        except ValueError as exc:
            print('DETECTED', label, str(exc))
        else:
            raise ValueError(f'mutation escaped: {label}')
    print('PASS 6 semantic mutations rejected without using SHA or checksums')


def playback(candidate):
    import unittest
    from test_playback import PlaybackTests
    PlaybackTests.candidate = candidate
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(PlaybackTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    V.require(result.wasSuccessful(), 'actual playback chain failed')


def crop_icons(candidate):
    import unittest
    from test_crop_icons import CropIconTests
    CropIconTests.candidate = candidate
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CropIconTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    V.require(result.wasSuccessful(), 'factory crop resources or film icons failed')


def references(candidate):
    import numpy as np
    _, stock, _ = decode(STOCK)
    hits = V.scan_references(stock, V.BASE, V.SPANS)
    words = np.frombuffer(stock[:len(stock) // 4 * 4], '<u4')
    for lo, hi in V.SPANS:
        for i in np.flatnonzero((words >= lo) & (words < hi)):
            hits.append(('word', V.BASE + 4 * int(i), int(words[i])))
    print('stock references into reserved spans:', hits[:100])
    V.require(not hits, 'unexplained stock references into spans')
    print('PASS bounded ARM linear scan and aligned pointer census; indirect references remain unproven')


def rebuild(candidate):
    import gr3patch_iiix as gp
    sys.modules['gr3patch'] = gp
    import make_slots15 as m15
    import make_slots16 as m16
    import presets_config
    allocations, writes = [], []
    take, write = m15.Space.take, gp.Image.write
    def tracked_take(space, size, name, prefer=None):
        free_before = [tuple(r) for r in space.free]
        address = take(space, size, name, prefer)
        reserved = (size + 3) & ~3
        V.require_owned(address, reserved, free_before)
        allocations.append((address, address + reserved, name))
        V.check_allocations([(a, b) for a, b, _ in allocations])
        return address
    def tracked_write(image, address, data):
        off = image.off(address)
        V.require(off + len(data) <= image.rtos_end, 'write crosses RTOS end')
        normalized = V.BASE + off - image.rtos0
        if any(normalized < hi and normalized + len(data) > lo for lo, hi in V.SPANS):
            V.require_owned(normalized, len(data), [(a, b) for a, b, _ in allocations])
        writes.append((off, off + len(data)))
        write(image, address, data)
    m15.Space.take, gp.Image.write = tracked_take, tracked_write
    try:
        films, _ = presets_config.load(str(HERE / 'presets.json'), spans=V.SPANS)
        image = gp.Image(str(STOCK))
        info = m15.patch(image, films, None, V.SPANS)
        m16.patch_ma(image, films)
        m16.patch_rawdev(image, films, info)
        m16.patch_exif_tone(image, films)
        m16.patch_playback_detail(image, films)
        built, _ = image.build()
        V.require(hashlib.sha256(built).hexdigest() == V.RELEASE_SHA, 'rebuild SHA differs from frozen B2.4.1')
        V.require(built == candidate.read_bytes(), 'rebuilt bytes differ from candidate')
        print('PASS deterministic rebuild;', len(allocations), 'nonoverlapping allocations')
        print('allocations:', json.dumps(allocations))
        print('tracked RTOS writes:', len(writes))
        print('final free space:', m15.FALLBACK[0].free)
    finally:
        m15.Space.take, gp.Image.write = take, write


def regression(candidate):
    import runpy
    config = json.loads((HERE / 'presets.json').read_text())
    fits = [f'{Path(config[str(t)]).stem}={HERE / "fits" / config[str(t)]}' for t in range(25, 33)]
    sys.argv = [str(FM / 'verify_slots16.py'), str(STOCK), str(candidate), *fits]
    result = runpy.run_path(sys.argv[0], run_name='__main__')
    V.require(result.get('ok') is True, 'functional regression failed')


def selftest(candidate):
    import unittest
    suite = unittest.defaultTestLoader.discover(str(HERE), pattern='test_verification.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    V.require(result.wasSuccessful(), 'verifier selftests failed')


def regression_ok(output):
    lines = output.splitlines()
    return bool(lines) and lines[-1] == 'ALL OK' and not any(x.startswith('FAIL ') for x in lines)


def run_stage(name, candidate, directory, timeout):
    log = directory / f'{name}.log'
    command = [sys.executable, '-u', str(Path(__file__).resolve()), str(candidate), '--stage', name]
    start = time.monotonic()
    result = dict(name=name, status='RUNNING', log=str(log), command=command)
    with log.open('w') as stream:
        try:
            completed = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                                       timeout=timeout, check=False)
            result.update(exit_code=completed.returncode, status='PASS' if completed.returncode == 0 else 'FAIL')
        except subprocess.TimeoutExpired:
            result['status'] = 'TIMEOUT'
    if result['status'] == 'PASS' and name == 'regression':
        if not regression_ok(log.read_text()):
            result['status'] = 'FAIL'
            result['reason'] = 'regression success marker absent or failed check present'
    result['seconds'] = round(time.monotonic() - start, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', nargs='?', type=Path, default=DEFAULT)
    parser.add_argument('--timeout', type=float, default=1800, help='seconds per stage; timeout is never a pass')
    parser.add_argument('--output', type=Path, help='new report directory (must not exist)')
    parser.add_argument('--stage', choices=STAGES, help=argparse.SUPPRESS)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    V.require(sys.flags.optimize == 0 and not os.environ.get('PYTHONOPTIMIZE'), 'optimized Python disables legacy assertions')
    V.require(math.isfinite(args.timeout) and args.timeout > 0, 'timeout must be finite and positive')
    for key in ('GR3_WORK', 'GR3_FILM_MODS', 'GR_CUSTOM_TOOL'):
        V.require(not os.environ.get(key), f'{key} override is unsupported in frozen release qualification')
    if args.stage:
        globals()[args.stage](candidate)
        return 0
    directory = args.output or HERE / 'logs' / ('qualification-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    directory = directory.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    sources = list(HERE.glob('*.py')) + list(FM.glob('*.py')) + list((HERE / 'fits').glob('*.json'))
    sources += [HERE / 'presets.json', HERE / 'VERIFICATION.md']
    sources += list((FM / 'third_party/gr-custom-tool/gr4_editor').rglob('*.py'))
    report = dict(schema_version=1, status='RUNNING', hardware='NOT_TESTED', candidate=str(candidate),
                  candidate_sha256=sha(candidate), stock_sha256=sha(STOCK), python=sys.version,
                  dependencies={p: importlib.metadata.version(p) for p in ('capstone', 'unicorn', 'numpy')},
                  source_sha256={str(p.relative_to(ROOT)): sha(p) for p in sorted(sources)}, stages=[],
                  release='b2.4.1',
                  limitations=['Frozen B2.4.1 only; custom builds require independent verification.',
                               'Linear ARM scan is not complete indirect-address or Thumb analysis.',
                               'Offline checks do not establish DNG cleanliness or hardware safety.',
                               'Rebuild allocation ledger is builder-derived evidence, not independent ownership proof.'])
    report_path = directory / 'report.json'
    def save():
        temp = directory / 'report.json.tmp'
        temp.write_text(json.dumps(report, indent=2) + '\n')
        temp.replace(report_path)
    save()
    try:
        for name in STAGES:
            print(f'RUN {name}', flush=True)
            result = run_stage(name, candidate, directory, args.timeout)
            report['stages'].append(result)
            print(result['status'], name, result['seconds'], 'seconds', flush=True)
            save()
            if result['status'] != 'PASS':
                break
        V.require(sha(candidate) == report['candidate_sha256'] and sha(STOCK) == report['stock_sha256'], 'firmware changed during verification')
        V.require(all(sha(ROOT / p) == h for p, h in report['source_sha256'].items()), 'source/config changed during verification')
        report['status'] = 'PASS' if len(report['stages']) == len(STAGES) and all(s['status'] == 'PASS' for s in report['stages']) else 'FAIL'
    except BaseException:
        report['status'] = 'INCOMPLETE'
        save()
        raise
    completed = {s['name'] for s in report['stages']}
    report['stages'].extend(dict(name=n, status='NOT_RUN') for n in STAGES if n not in completed)
    save()
    print(report['status'], report_path, flush=True)
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as exc:
        print(f'FAIL: {exc}', file=sys.stderr)
        raise SystemExit(1)
