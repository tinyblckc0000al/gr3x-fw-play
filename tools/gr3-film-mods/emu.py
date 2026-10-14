import sys, struct
sys.path.insert(0, '.')
from fw import R, BASE, SRC, DST, LEN, w as romw
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_ARM, UC_HOOK_CODE, UC_HOOK_INTR, UC_HOOK_MEM_READ, UC_HOOK_MEM_UNMAPPED, UcError
from unicorn import arm_const as A

HEAP, STACK, STOP = 0x60000000, 0x5F000000, 0x5E000000
STUB_RET0 = {0x536b82d4, 0x5313fbb8}

class Emu:
    def __init__(self, rtos=R):
        u = self.u = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        u.mem_map(BASE, (len(rtos) + 0xFFFF) & ~0xFFFF)
        u.mem_write(BASE, bytes(rtos))
        u.mem_map(0x55000000, 0x01000000)
        u.mem_write(DST, bytes(rtos[SRC - BASE:SRC - BASE + LEN]))
        u.mem_map(HEAP, 0x04000000)
        u.mem_map(STACK - 0x100000, 0x100000)
        u.mem_map(STOP, 0x1000)
        u.reg_write(A.UC_ARM_REG_C1_C0_2, 0xF00000)
        u.reg_write(A.UC_ARM_REG_FPEXC, 0x40000000)
        self.brk = HEAP
        self.asserts = []
        self.reads = []
        self.trace_ranges = []
        self.extra_stubs = {}
        u.hook_add(UC_HOOK_CODE, self._code)
        u.hook_add(UC_HOOK_MEM_READ, self._read)
        u.hook_add(UC_HOOK_INTR, self._intr)
        self.svcs = []

    def alloc(self, n):
        a = self.brk
        self.brk = (self.brk + n + 0x3F) & ~0x3F
        self.u.mem_write(a, bytes(n))
        return a

    def _ret(self, v=None):
        if v is not None:
            self.u.reg_write(A.UC_ARM_REG_R0, v)
        self.u.reg_write(A.UC_ARM_REG_PC, self.u.reg_read(A.UC_ARM_REG_LR))

    def _code(self, u, at, size, _):
        if at in (0x536af2a8, 0x536af31c):
            self._ret(self.alloc(u.reg_read(A.UC_ARM_REG_R0)))
        elif at in (0x536af2e4, 0x536af358):
            self._ret(0)
        elif at == 0x536b93d0:
            if not u.reg_read(A.UC_ARM_REG_R0):
                self.asserts.append((hex(u.reg_read(A.UC_ARM_REG_LR)), u.reg_read(A.UC_ARM_REG_R3)))
            self._ret(0)
        elif at in STUB_RET0:
            self._ret(0)
        elif at in self.extra_stubs:
            v = self.extra_stubs[at]
            self._ret(v(self) if callable(v) else v)

    def _intr(self, u, intno, _):
        self.svcs.append(intno)
        u.reg_write(A.UC_ARM_REG_R0, 0)

    def _read(self, u, access, addr, size, value, _):
        for lo, hi, tag in self.trace_ranges:
            if lo <= addr < hi:
                self.reads.append((u.reg_read(A.UC_ARM_REG_PC), tag, addr - lo, size))
                break

    def call(self, at, *args, limit=5_000_000):
        u = self.u
        for i in range(13):
            u.reg_write(getattr(A, f'UC_ARM_REG_R{i}'), 0)
        for i, v in enumerate(args):
            u.reg_write(getattr(A, f'UC_ARM_REG_R{i}'), v)
        u.reg_write(A.UC_ARM_REG_SP, STACK - 0x100)
        u.reg_write(A.UC_ARM_REG_LR, STOP)
        u.reg_write(A.UC_ARM_REG_CPSR, 0x13)
        try:
            u.emu_start(at, STOP, count=limit)
        except UcError as e:
            pc = u.reg_read(A.UC_ARM_REG_PC)
            raise RuntimeError(f'{e} at pc={pc:#x} lr={u.reg_read(A.UC_ARM_REG_LR):#x}')
        if u.reg_read(A.UC_ARM_REG_PC) != STOP:
            raise RuntimeError(f'did not return, pc={u.reg_read(A.UC_ARM_REG_PC):#x}')
        return u.reg_read(A.UC_ARM_REG_R0)

    def r32(self, a): return struct.unpack('<I', self.u.mem_read(a, 4))[0]
    def w32(self, a, v): self.u.mem_write(a, struct.pack('<I', v))
    def w8(self, a, v): self.u.mem_write(a, bytes([v]))
