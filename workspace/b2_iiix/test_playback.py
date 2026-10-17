"""Execute actual final-image playback code; only EXIF input and singleton lookup are stubbed."""
import sys
import unittest

from verify_release import DEFAULT, decode, FM
sys.path.insert(0, str(FM))
from emu import Emu


class PlaybackTests(unittest.TestCase):
    candidate = DEFAULT
    @classmethod
    def setUpClass(cls):
        _, cls.rtos, _ = decode(cls.candidate)

    def test_all_factory_and_film_codes_and_invalid_boundaries(self):
        e = Emu(self.rtos)
        model = e.alloc(0x800)
        output = e.alloc(4)
        e.extra_stubs[0x5320AD88] = 0
        e.extra_stubs[0x5320B97C] = model
        tones = [11, 12, 10, 14, 15, 16, 17, 8, 19, 20, 21, 22, 25, 26, 27, 28, 29, 30, 31, 32]
        icons = [0x166, 0x224, 0x162, 0x165, 0x15E, 0x160, 0xE8, 0x15A, 0x164, 0x15F, 0x32, 0x17,
                 5, 6, 7, 0x1D, 0x2A0, 0x2A1, 0x2A2, 0x2A3]
        for index, (tone, icon) in enumerate(zip(tones, icons)):
            with self.subTest(code=hex(0x100 + index)):
                e.extra_stubs[0x535D04D4] = 0x100 + index
                e.call(0x535C24EC, 0, model + 0x18C, 0)
                self.assertEqual(e.r32(model + 0x18C + 0x25 * 4), index + 1)
                self.assertEqual(e.call(0x532B44BC, model, output), 1)
                self.assertEqual(bytes(e.u.mem_read(output, 1)), bytes([tone]))
                self.assertEqual(e.call(0x532B6EEC, 0), icon)
        for invalid in (0, 0xFF, 0x114, 0xFFFF):
            with self.subTest(invalid=hex(invalid)):
                e.extra_stubs[0x535D04D4] = invalid
                e.call(0x535C24EC, 0, model + 0x18C, 0)
                self.assertEqual(e.r32(model + 0x18C + 0x25 * 4), 0)
                self.assertEqual(e.call(0x532B44BC, model, output), 0)
                self.assertEqual(e.call(0x532B6EEC, 0), 0)
        self.assertEqual(e.asserts, [])


if __name__ == '__main__':
    unittest.main()
