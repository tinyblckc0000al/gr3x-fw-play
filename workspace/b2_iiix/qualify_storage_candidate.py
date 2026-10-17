#!/usr/bin/env python3
"""Qualify a local storage-repair candidate; never grants release approval."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time

from verify_release import ROOT, HERE, STOCK, decode, sha, qualification_sources
import verification as V


def structure(candidate, directory):
    V.require(sha(STOCK) == V.STOCK_SHA, 'unexpected official firmware')
    old, stock, rows = decode(STOCK)
    new, rtos, grown = decode(candidate)
    V.require(len(rtos) - len(stock) == 0x6000, 'RTOS growth must be exactly 24 KiB')
    V.require(V.BASE + len(stock) == 0x540B55C0 and V.BASE + len(rtos) < 0x55000000,
              'unexpected append mapping or initialized RAM overlap')
    V.require(rtos[0x450:0x45C] == struct.pack('<3I', 0x5407B540, 0x55000000, 0x3A080),
              'startup initialized-data mapping changed')
    V.check_protected(stock, rtos)
    V.check_playback(rtos)
    V.check_factory_icon_descriptors(stock, rtos)
    V.require(list(rows) == list(grown), 'section order changed')
    for name, row in rows.items():
        target = grown[name]
        V.require(row['flags'] == target['flags'], f'section flags changed: {name}')
        if name not in ('RTOS', 'ICONBIN'):
            V.require(old[row['start']:row['end']] == new[target['start']:target['end']],
                      f'non-target section changed: {name}')
    report = json.loads(Path(str(candidate) + '.report.json').read_text())
    V.require(report['_build']['out_sha256'] == sha(candidate), 'build report identifies another BIN')
    allocations = [(a['start'], a['end']) for a in report['_build']['allocations']]
    V.check_allocations(allocations)
    for lo, hi in allocations:
        V.require(lo % 4 == hi % 4 == 0 and 0x540B55C0 <= lo < hi <= 0x540BB5C0,
                  f'allocation not owned by appended storage: {lo:#x}..{hi:#x}')
    relative = [(lo - 0x540B55C0, hi - 0x540B55C0) for lo, hi in allocations]
    V.check_changes(bytes(0x6000), rtos[len(stock):], relative)
    receipt = dict(appended_bytes=0x6000, allocations=len(allocations),
                   allocated_bytes=sum(hi-lo for lo, hi in allocations),
                   unchanged_startup_mapping=True, protected_windows=len(V.PROTECTED),
                   limitations='Allocation ledger is builder-derived; hardware loading/boot requires camera testing.')
    (directory / 'structure.json').write_text(json.dumps(receipt, indent=2) + '\n')


def mutations(candidate, directory):
    _, stock, _ = decode(STOCK)
    _, good, _ = decode(candidate)
    for address in (0x53D39C90, 0x53D453FE, 0x53D3A587, 0x53D45CAF):
        broken = bytearray(good)
        broken[address - V.BASE] ^= 1
        try:
            V.check_protected(stock, broken)
        except ValueError:
            continue
        raise ValueError(f'compensation mutation escaped at {address:#x}')
    low, high, _, _, _ = V.POINTERS[1]
    broken = bytearray(good)
    # Redirect the playback tone table to a previously used stock data region.
    target = 0x53D3A2F0
    for address, value in ((low, target & 65535), (high, target >> 16)):
        word = V.word(broken, address)
        word = (word & ~0xF0FFF) | ((value & 0xF000) << 4) | (value & 0xFFF)
        struct.pack_into('<I', broken, address-V.BASE, word)
    try:
        V.check_playback(broken)
    except ValueError:
        return
    raise ValueError('playback pointer escaped appended storage')


def unit_tests(candidate, directory):
    patterns = ('test_verification.py', 'test_icon_policy.py', 'test_release_gate.py',
                'test_append_storage.py', 'test_storage_layout.py', 'test_crop_icons.py',
                'test_compensation_upload.py')
    env = dict(os.environ, GR3X_STORAGE_CANDIDATE=str(candidate), GR3X_ICON_CANDIDATE=str(candidate))
    for pattern in patterns:
        command = [sys.executable, '-m', 'unittest', 'discover', '-s', str(HERE), '-p', pattern, '-v']
        run(command, directory / (pattern + '.log'), env)


def run(command, log, env=None):
    with log.open('w') as stream:
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, timeout=900, check=False)
    V.require(result.returncode == 0, f'check failed: {log.name}; exit={result.returncode}')


def regression(candidate, directory):
    command = [sys.executable, '-u', str(HERE / 'verify_release.py'), str(candidate), '--stage', 'regression']
    log = directory / 'regression.log'
    run(command, log)
    from verify_release import regression_ok
    V.require(regression_ok(log.read_text()), 'regression output did not end in ALL OK')


def rebuild(candidate, directory):
    with tempfile.TemporaryDirectory() as temp:
        out = Path(temp) / 'fwdc243b.bin'
        run([sys.executable, str(HERE / 'build_iiix.py'), '--stock', 'iiix', str(out)], directory / 'rebuild.log')
        V.require(out.read_bytes() == candidate.read_bytes(), 'deterministic rebuild differs')


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('candidate', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    candidate, directory = args.candidate.resolve(), args.output.resolve()
    directory.mkdir(parents=True, exist_ok=False)
    identity = sha(candidate)
    sources = {str(p.relative_to(ROOT)): sha(p) for p in qualification_sources()}
    report = dict(status='RUNNING', kind='storage-repair-qualification', release='b2.4.2', stock_sha256=sha(STOCK), candidate_sha256=identity,
                  source_sha256=sources, hardware='NOT_TESTED', publish_authorized=False, stages=[])
    report_path = directory / 'report.json'
    for name, operation in [('structure', structure), ('mutations', mutations), ('unit_and_native_probes', unit_tests),
                            ('regression', regression), ('deterministic_rebuild', rebuild)]:
        stage = dict(name=name, status='RUNNING')
        report['stages'].append(stage)
        start = time.monotonic()
        try:
            operation(candidate, directory)
            stage.update(status='PASS', exit_code=0, seconds=round(time.monotonic()-start, 2))
        except Exception as exc:
            stage.update(status='FAIL', exit_code=1, error=str(exc))
            report['status'] = 'FAIL'
            report_path.write_text(json.dumps(report, indent=2)+'\n')
            raise
        report_path.write_text(json.dumps(report, indent=2)+'\n')
        print('PASS', name, flush=True)
    try:
        V.require(sha(candidate) == identity, 'candidate changed during qualification')
        V.require(all(sha(ROOT / p) == h for p, h in sources.items()), 'source changed during qualification')
    except ValueError:
        report['status'] = 'FAIL'
        report_path.write_text(json.dumps(report, indent=2)+'\n')
        raise
    report['status'] = 'PASS'
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    print('PASS local candidate:', report_path, flush=True)


if __name__ == '__main__':
    main()
