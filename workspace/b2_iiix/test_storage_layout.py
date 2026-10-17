"""Candidate storage invariants, independent of builder allocation addresses.

GR3X_STORAGE_CANDIDATE selects the local test BIN. Old B2.4.1 must fail.
"""
import os
from pathlib import Path
import struct
import unittest
from verify_release import decode, STOCK, DEFAULT


class StorageLayoutTests(unittest.TestCase):
    candidate = Path(os.environ.get('GR3X_STORAGE_CANDIDATE', DEFAULT))

    @classmethod
    def setUpClass(cls):
        cls.stock_dec, cls.stock, cls.stock_rows = decode(STOCK)
        cls.decoded, cls.rtos, cls.rows = decode(cls.candidate)

    def test_storage_grows_rtos_without_crossing_initialized_ram(self):
        self.assertGreater(len(self.rtos), len(self.stock))
        self.assertLess(0x53000000 + len(self.rtos), 0x55000000)
        self.assertEqual(self.rtos[0x450:0x45C], struct.pack('<3I', 0x5407B540, 0x55000000, 0x3A080))

    def test_complete_byte_tile_compensation_tables_match_stock(self):
        # 64 rows * 8 columns * 7 interleaved settings = 3584, not 452 B.
        for base in (0x53D35CBC, 0x53D37884, 0x53D44EB0,
                     0x53D39788, 0x53D440B0, 0x53D3CDD4):
            with self.subTest(base=hex(base)):
                off = base - 0x53000000
                self.assertEqual(self.rtos[off:off + 3584], self.stock[off:off + 3584])

    def test_random_code_and_ma_zero_table_are_no_longer_repurposed(self):
        for lo, hi in ((0x536EF088, 0x536EF140), (0x536EF618, 0x536EF6DC),
                       (0x536EF6FC, 0x536EF9B8), (0x53DC2BF8, 0x53DC3198),
                       (0x54094D88, 0x54094DA8)):
            with self.subTest(start=hex(lo)):
                a, b = lo - 0x53000000, hi - 0x53000000
                self.assertEqual(self.rtos[a:b], self.stock[a:b])

    def test_following_section_contents_are_relocated_without_corruption(self):
        self.assertEqual(list(self.rows), list(self.stock_rows))
        growth = len(self.rtos) - len(self.stock)
        for name, old in self.stock_rows.items():
            new = self.rows[name]
            if old['start'] >= self.stock_rows['RTOS']['end']:
                self.assertEqual(new['start'] - old['start'], growth)
            if name not in ('RTOS', 'ICONBIN'):
                self.assertEqual(self.decoded[new['start']:new['end']],
                                 self.stock_dec[old['start']:old['end']])


if __name__ == '__main__':
    unittest.main()
