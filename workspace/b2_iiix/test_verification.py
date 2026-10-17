"""Regression tests for verifier blind spots; no camera or firmware writes."""
import importlib.util
import struct
import unittest


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('verification'), 'verification module is required')
        import verification
        self.v = verification

    def test_conditional_pair_and_pc_literal_are_detected(self):
        # movwls r3,#0x1234; movtls r3,#0x53d3; ldr r0,[pc,#4]
        code = struct.pack('<4I', 0x93013234, 0x934533d3, 0xe59f0004, 0xe12fff1e)
        hits = self.v.scan_references(code, 0x53000000, [(0x53d30000, 0x53d40000), (0x53000014, 0x53000018)])
        self.assertIn(('pair', 0x53000004, 0x53d31234), hits)
        self.assertIn(('pc', 0x53000008, 0x53000014), hits)

    def test_clobber_and_branch_do_not_reuse_old_low_half(self):
        for middle in (0xe3a03000, 0xea000000):
            code = struct.pack('<3I', 0xe3013234, middle, 0xe34533d3)
            self.assertEqual(self.v.scan_references(code, 0x53000000, [(0x53d30000, 0x53d40000)]), [])

    def test_full_write_interval_must_fit_one_allocation(self):
        self.v.require_owned(100, 4, [(100, 104)])
        for addr, size in ((100, 5), (99, 2), (104, 1), (100, -1)):
            with self.subTest(addr=addr, size=size), self.assertRaises(ValueError):
                self.v.require_owned(addr, size, [(100, 104)])

    def test_unaligned_changed_byte_is_not_skipped(self):
        old = bytes(200)
        new = bytearray(old)
        new[1] = 1  # old 1-in-97 sampling could miss this
        with self.assertRaises(ValueError):
            self.v.check_changes(old, new, [(0, 1), (2, 200)])

    def test_full_byte_tile_read_windows_reject_single_byte_changes(self):
        stock = bytes(0xD50000)
        for address in (0x53D39C90, 0x53D453FE, 0x53D3A587, 0x53D45CAF):
            with self.subTest(address=hex(address)):
                broken = bytearray(stock)
                broken[address - self.v.BASE] = 1
                with self.assertRaisesRegex(ValueError, 'protected window'):
                    self.v.check_protected(stock, broken)

    def test_overlapping_allocations_fail(self):
        with self.assertRaises(ValueError):
            self.v.check_allocations([(100, 110), (109, 120)])
        self.v.check_allocations([(100, 110), (110, 120)])




class RunnerTests(unittest.TestCase):
    def test_failure_marker_overrides_zero_exit(self):
        from verify_release import regression_ok
        self.assertFalse(regression_ok('FAIL bad\nALL OK\n'))
        self.assertFalse(regression_ok('OK partial\n'))
        self.assertTrue(regression_ok('OK good\nALL OK\n'))

    def test_timeout_is_not_success(self):
        import tempfile
        from pathlib import Path
        from verify_release import run_stage, DEFAULT
        with tempfile.TemporaryDirectory() as d:
            result = run_stage('structure', DEFAULT, Path(d), 0.000001)
        self.assertEqual(result['status'], 'TIMEOUT')

if __name__ == '__main__':
    unittest.main()
