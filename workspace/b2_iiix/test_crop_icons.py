"""Candidate regression: original crop resources survive added film icons.

Run after building out/fwdc243b-b241.bin, or set
GR3X_ICON_CANDIDATE. The old B2.4 artifact fails the preservation tests.
"""
import os
from pathlib import Path
import struct
import unittest

from verify_release import DEFAULT, STOCK, decode
import verification as V
from emu import Emu
from unicorn import arm_const as A


class CropIconTests(unittest.TestCase):
    candidate = Path(os.environ.get('GR3X_ICON_CANDIDATE', DEFAULT))

    @classmethod
    def setUpClass(cls):
        cls.stock_dec, cls.stock, cls.rows = decode(STOCK)
        cls.patched_dec, cls.patched, rows = decode(cls.candidate)
        if rows != cls.rows:
            raise ValueError('candidate section layout differs')

    def test_known_isp_windows_and_icon_pixel_boundaries_are_preserved(self):
        V.check_protected(self.stock, self.patched)
        ib = self.rows['ICONBIN']['start'] + 16
        end = self.rows['ICONBIN']['end']
        allowed = []
        for icon in (5, 6, 7, 0x1D):
            w, h, offset = self.descriptor(self.stock, icon)
            allowed.append((4*offset, 4*offset + 4*w*h))
        V.check_changes(self.stock_dec[ib:end], self.patched_dec[ib:end], allowed)

    def test_all_other_factory_icon_descriptors_are_unchanged(self):
        def catalog_descriptor(rtos, icon):
            pointer = V.word(rtos, 0x5407B540 + 0x20FC + 4*icon)
            return V.read(rtos, pointer, 8)
        for icon in range(0x29F):
            if icon in (5, 6, 7, 0x1D):
                continue
            with self.subTest(icon=hex(icon)):
                self.assertEqual(catalog_descriptor(self.patched, icon), catalog_descriptor(self.stock, icon))

    def test_final_playback_tables_match_independent_release_expectations(self):
        V.check_playback(self.patched)

    def descriptor(self, rtos, icon):
        e = Emu(rtos)
        e.u.reg_write(A.UC_ARM_REG_R3, icon)
        e.u.reg_write(A.UC_ARM_REG_LR, 1)
        e.u.emu_start(0x5320A804, 0x5320A814, count=40)
        return struct.unpack('<HHI', bytes(e.u.mem_read(e.u.reg_read(A.UC_ARM_REG_R3), 8)))

    def test_factory_crop_descriptors_dimensions_and_pixels_are_preserved(self):
        ib = self.rows['ICONBIN']['start'] + 16
        for icon in (0x2C, 0x2D, 0x2E):
            with self.subTest(icon=hex(icon)):
                want = self.descriptor(self.stock, icon)
                self.assertEqual(self.descriptor(self.patched, icon), want)
                e = Emu(self.patched)
                self.assertEqual((e.call(0x53209FB8, 0, icon), e.call(0x53209FEC, 0, icon)), want[:2])
                w, h, offset = want
                start = ib + 4 * offset
                self.assertEqual(self.patched_dec[start:start + 4*w*h], self.stock_dec[start:start + 4*w*h])

    def test_shooting_and_final_playback_share_distinct_film_icons(self):
        e = Emu(self.patched)
        model, output = e.alloc(0x800), e.alloc(4)
        e.extra_stubs[0x5320AD88] = 0
        e.extra_stubs[0x5320B97C] = model
        offsets = []
        for k in range(8):
            with self.subTest(tone=25+k):
                icon = e.call(0x532935DC, 0, 25+k)
                self.assertNotIn(icon, (0x2C, 0x2D, 0x2E))
                e.extra_stubs[0x535D04D4] = 0x10C+k
                e.call(0x535C24EC, 0, model + 0x18C, 0)
                self.assertEqual(e.call(0x532B44BC, model, output), 1)
                self.assertEqual(bytes(e.u.mem_read(output, 1)), bytes([25+k]))
                self.assertEqual(e.call(0x532B6EEC, 0), icon)
                w, h, offset = self.descriptor(self.patched, icon)
                self.assertEqual((w, h), (40, 40))
                offsets.append(offset)
        self.assertEqual(len(set(offsets)), 8)
        self.assertEqual(e.asserts, [])


if __name__ == '__main__':
    unittest.main()
