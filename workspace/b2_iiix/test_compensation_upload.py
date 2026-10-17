"""Execute the stock CPU uploader with only external hardware helpers replaced.

The observed contract is its 96 actual 32-byte tile submission buffers per setting,
not the substitute helpers' return values. It does not test physical ISP transfers.
"""
import os
from pathlib import Path
import unittest
from verify_release import STOCK, decode
from emu import Emu, STOP
from unicorn import UC_HOOK_CODE, UC_HOOK_MEM_READ
from unicorn import arm_const as A

HERE = Path(__file__).resolve().parent
CANDIDATE = Path(os.environ.get('GR3X_STORAGE_CANDIDATE', HERE / 'out/fwdc243b-b242-storage-rc1.bin'))
# These are the external callees recovered in the original dispatch trace.
RETURNS_ZERO = {
    0x536326E4, 0x536327E8, 0x537352DC, 0x53735880, 0x53735A80,
    0x53735D00, 0x53736090, 0x53736420, 0x53735C80, 0x537352EC,
    0x536B0A74, 0x537375A0, 0x53735284, 0x53735294, 0x53735980,
    0x53735B80, 0x53735EC8, 0x53736258, 0x537365E8, 0x53735CC0,
    0x538526A0, 0x538526A4, 0x53734294, 0x537342B8, 0x537342DC,
    0x5373433C, 0x5373431C, 0x537342FC, 0x537340E4, 0x53734150,
    0x537341BC, 0x53734228,
}
READY = {0x537352B0, 0x53735274}


def trace_tiles(rtos, parameter):
    e = Emu(rtos)
    obj = e.alloc(0x100)
    tiles, appended_reads = [], []

    def code(u, address, size, _):
        if address == 0x537375A0:
            buffer = u.reg_read(A.UC_ARM_REG_R3)
            tiles.append((u.reg_read(A.UC_ARM_REG_LR), u.reg_read(A.UC_ARM_REG_R1),
                          u.reg_read(A.UC_ARM_REG_R2), bytes(u.mem_read(buffer, 32))))
        if address in READY or address in RETURNS_ZERO:
            e._ret(int(address in READY))
        elif address != STOP and not 0x53632898 <= address < 0x53633F54:
            raise ValueError(f'unmodelled uploader callee {address:#x}')

    def read(u, access, address, size, value, _):
        if 0x540B55C0 <= address < 0x53000000 + len(rtos):
            appended_reads.append(address)

    e.u.hook_add(UC_HOOK_CODE, code)
    e.u.hook_add(UC_HOOK_MEM_READ, read)
    if parameter == 0:
        e.call(0x53633F38, obj, limit=3_000_000)
    else:
        e.call(0x53633E6C, obj, parameter, limit=3_000_000)
    return tiles, appended_reads


class CompensationUploadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _, cls.stock, _ = decode(STOCK)
        _, cls.candidate, _ = decode(CANDIDATE)

    def test_cpu_reader_instructions_have_not_changed(self):
        self.assertEqual(self.candidate[0x632898:0x633F54], self.stock[0x632898:0x633F54])

    def test_all_seven_settings_submit_exact_stock_tile_data(self):
        for setting in range(7):
            with self.subTest(setting=setting):
                expected, _ = trace_tiles(self.stock, setting)
                actual, appended_reads = trace_tiles(self.candidate, setting)
                self.assertEqual(len(expected), 96)
                self.assertEqual(len(actual), 96)
                self.assertEqual(actual, expected)
                self.assertEqual(appended_reads, [])


if __name__ == '__main__':
    unittest.main()
