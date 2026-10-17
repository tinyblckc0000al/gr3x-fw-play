#!/usr/bin/env python3
"""Read-only publication gate. Run after qualification and committing sources."""
import argparse
import json
from pathlib import Path
import subprocess

from verify_release import ROOT, STOCK, DEFAULT, HERE, sha, qualification_sources
import verification as V


def check(candidate, report_path, hardware_path):
    report = json.loads(report_path.read_text())
    hardware = json.loads(hardware_path.read_text())
    V.check_release_evidence(report, hardware)
    V.require(sha(candidate) == report['candidate_sha256'], 'candidate changed after qualification')
    V.require(sha(STOCK) == report.get('stock_sha256') == V.STOCK_SHA, 'stock identity changed')
    sources = report.get('source_sha256', {})
    expected_sources = {str(p.relative_to(ROOT)) for p in qualification_sources()}
    V.require(bool(sources) and set(sources) == expected_sources, 'qualification source inventory changed')
    for relative, expected in sources.items():
        path = (ROOT / relative).resolve()
        V.require(path.is_relative_to(ROOT), 'source fingerprint is outside the repository')
        V.require(sha(path) == expected, f'source changed after qualification: {relative}')
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT, text=True).split('\0'))
    V.require(set(sources) <= tracked, 'qualified sources must be committed')
    V.require(hardware_path.resolve().is_relative_to(ROOT) and
              str(hardware_path.resolve().relative_to(ROOT)) in tracked, 'camera record must be committed')
    subprocess.run(['git', 'diff', '--exit-code', 'HEAD', '--'], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    return dict(status='PASS', source_commit=commit, firmware_sha256=sha(candidate),
                qualification_sha256=sha(report_path), hardware_record_sha256=sha(hardware_path),
                hardware_evidence=hardware['evidence_type'], hardware_scope=hardware['scope'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('candidate', nargs='?', type=Path, default=DEFAULT)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--hardware', type=Path, default=HERE / 'hardware-b241.json')
    args = parser.parse_args()
    print(json.dumps(check(args.candidate, args.report, args.hardware), indent=2, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f'FAIL: {exc}')
