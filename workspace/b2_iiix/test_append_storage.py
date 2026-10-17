"""Image growth and aligned allocation boundary contracts."""
import copy
import unittest
from verify_release import STOCK
from gr3patch_iiix import Image
from make_slots15 import Space


class AppendStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pristine = Image(str(STOCK))

    def setUp(self):
        self.image = copy.copy(self.pristine)
        self.image.target = bytearray(self.pristine.target)
        self.image.sections = copy.deepcopy(self.pristine.sections)

    def test_append_preserves_existing_vas_and_moves_icon_payload(self):
        old_icon = self.image.sections['ICONBIN']['start']
        before = self.image.read(0x53632898, 32)
        self.assertEqual(self.image.append_rtos(0x6000), (0x540B55C0, 0x540BB5C0))
        self.assertEqual(self.image.read(0x53632898, 32), before)
        self.assertEqual(self.image.sections['ICONBIN']['start'], old_icon + 0x6000)
        self.image.write(0x540B55C0, b'ABCD')
        self.assertEqual(self.image.read(0x540B55C0, 4), b'ABCD')

    def test_invalid_growth_does_not_mutate_the_image(self):
        for size in (0, -0x6000, 1, True, 0x1000000, 1.5):
            with self.subTest(size=size), self.assertRaises(ValueError):
                self.image.append_rtos(size)
        self.assertEqual(self.image.target, self.pristine.target)

    def test_repeat_or_late_growth_is_rejected(self):
        self.image.append_rtos(0x6000)
        with self.assertRaises(ValueError):
            self.image.append_rtos(0x6000)
        self.image = copy.copy(self.pristine)
        self.image.target = bytearray(self.pristine.target)
        self.image.write(0x53632898, b'bad!')
        with self.assertRaises(ValueError):
            self.image.append_rtos(0x6000)

    def test_partial_memory_access_cannot_cross_rtos_or_ram_mapping(self):
        for addr in (0x540B55BE, 0x5503A07E):
            with self.subTest(addr=hex(addr)):
                with self.assertRaises(ValueError):
                    self.image.write(addr, b'ABCD')
                with self.assertRaises(ValueError):
                    self.image.read(addr, 4)
        self.assertEqual(self.image.target, self.pristine.target)

    def test_full_curve_before_knots_is_not_mistaken_for_a_knot_table(self):
        import presets_config
        import make_slots15 as slots
        from emu import Emu
        from unicorn import UC_HOOK_CODE
        from unicorn import arm_const as A
        films, _ = presets_config.load(str(STOCK.parents[2] / 'workspace/b2_iiix/presets.json'))
        films = [films[-1], *films[:-1]]
        start, _ = self.image.append_rtos(0x6000)
        info = slots.patch(self.image, films, kspace_spans=[(start, start+0x2000)],
                           code_spans=[(start+0x2000, start+0x3000)])
        full_curve = int(info[films[0][0]]['knots'], 16)
        entry = next(int(address, 16) for name, address, _ in info['_code']['space']
                     if name == 'knot expander')
        e = Emu(self.image.rtos())
        pointer, output = e.alloc(4), e.alloc(512)
        e.w32(pointer, full_curve)
        e.u.hook_add(UC_HOOK_CODE, lambda u, at, size, _: u.reg_write(A.UC_ARM_REG_R7, output)
                     if at == entry else None)
        e.call(entry, pointer)
        self.assertEqual(e.r32(pointer), full_curve)

    def test_alignment_is_included_before_capacity_decision(self):
        space = Space([(100, 105)])
        with self.assertRaises(SystemExit):
            space.take(5, 'must reserve eight aligned bytes')
        self.assertEqual(space.free, [[100, 105]])
        self.assertEqual(space.take(4, 'fits'), 100)


if __name__ == '__main__':
    unittest.main()
