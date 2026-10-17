"""A passing summary must not hide missing tests or a different camera build."""
import copy
import unittest

import verification as V


class ReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.report = dict(status='PASS', release='b2.4.1', candidate_sha256=V.RELEASE_SHA,
                           stages=[dict(name=n, status='PASS', exit_code=0) for n in
                                   ('selftest', 'structure', 'mutations', 'playback', 'crop_icons',
                                    'references', 'rebuild', 'regression')])
        self.hardware = dict(status='PASS', release='b2.4.1', firmware_sha256=V.RELEASE_SHA,
                             evidence_type='user_report', scope='Fn crop icon fix',
                             date='2026-10-17', report='真机测试没问题。')

    def test_complete_evidence_is_accepted(self):
        V.check_release_evidence(self.report, self.hardware)

    def test_partial_or_failed_qualification_is_rejected(self):
        for change in ('missing', 'duplicate', 'timeout', 'nonzero', 'summary', 'wrong bin'):
            report = copy.deepcopy(self.report)
            if change == 'missing':
                report['stages'].pop()
            elif change == 'duplicate':
                report['stages'][-1] = report['stages'][0]
            elif change == 'timeout':
                report['stages'][-1]['status'] = 'TIMEOUT'
            elif change == 'nonzero':
                report['stages'][-1]['exit_code'] = 1
            elif change == 'summary':
                report['status'] = 'INCOMPLETE'
            else:
                report['candidate_sha256'] = '0' * 64
            with self.subTest(change=change), self.assertRaises(ValueError):
                V.check_release_evidence(report, self.hardware)

    def test_missing_or_different_camera_evidence_is_rejected(self):
        for field, value in (('status', 'NOT_TESTED'), ('firmware_sha256', '0' * 64),
                             ('release', 'b2.4'), ('report', ''), ('scope', ''), ('date', '')):
            hardware = dict(self.hardware, **{field: value})
            with self.subTest(field=field), self.assertRaises(ValueError):
                V.check_release_evidence(self.report, hardware)

    def test_preflight_binds_commit_and_rejects_source_or_binary_drift(self):
        import json
        from pathlib import Path
        import subprocess
        import tempfile
        from unittest.mock import patch
        import check_release as gate
        from verify_release import DEFAULT, sha

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / 'builder.py'
            source.write_text('# qualified source\n')
            hardware = root / 'hardware.json'
            hardware.write_text(json.dumps(self.hardware))
            report = root / 'report.json'
            report.write_text(json.dumps(dict(self.report, stock_sha256=V.STOCK_SHA,
                                             source_sha256={'builder.py': sha(source)})))
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            subprocess.run(['git', 'add', 'builder.py', 'hardware.json'], cwd=root, check=True)
            subprocess.run(['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                            '-c', 'commit.gpgsign=false', 'commit', '-qm', 'test fixture'], cwd=root, check=True)
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
            with patch.object(gate, 'ROOT', root), patch.object(gate, 'qualification_sources', return_value=[source]):
                receipt = gate.check(DEFAULT, report, hardware)
                self.assertEqual(receipt['source_commit'], commit)
                wrong = root / 'wrong.bin'
                wrong.write_bytes(b'not the camera-tested firmware')
                with self.assertRaisesRegex(ValueError, 'candidate changed'):
                    gate.check(wrong, report, hardware)
                source.write_text('# changed after qualification\n')
                with self.assertRaisesRegex(ValueError, 'source changed'):
                    gate.check(DEFAULT, report, hardware)
