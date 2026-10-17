"""Independent, fail-closed checks for the frozen GR IIIx 1.60 B2.4.1 release.

No patch-generator imports. Linear reference scanning is evidence, not a proof
against arbitrary indirect addressing or dynamically generated code.
"""
import struct

BASE = 0x53000000
SPANS = [(0x53D453F8, 0x53D45CB0), (0x53D39C8C, 0x53D3A588)]
RELEASE_SHA = '88829723a3a1f8edfe70c0153c636d51fda2bdd2aac75641195142560b7e8128'
STOCK_SHA = '708e79f3b7b96a7e1581b4acf4c412233050a1832718ef7f06c8397db1b431c7'
ICONS = (5, 6, 7, 0x1D, 0x2A0, 0x2A1, 0x2A2, 0x2A3)
FACTORY_TONES = (11, 12, 10, 14, 15, 16, 17, 8, 19, 20, 21, 22)
FACTORY_ICONS = (0x15A, 0, 0x162, 0x166, 0x224, 0, 0x165, 0x15E, 0x160, 0xE8, 0, 0x164, 0x15F, 0x32, 0x17)
TABLES = ((0x53D3A2DC, bytes(range(1, 21))),
          (0x53D3A2F0, bytes(FACTORY_TONES) + bytes(range(25, 33))),
          (0x53D3A304, struct.pack('<25H', *FACTORY_ICONS, 0, 0, *ICONS)))
# (MOVW, MOVT, destination, condition, register); checked independently of report.json.
POINTERS = ((0x535C2518, 0x535C2520, 0x53D3A2DC, 9, 3),
            (0x532B44E4, 0x532B44EC, 0x53D3A2F0, 14, 3),
            (0x532B6F40, 0x532B6F4C, 0x53D3A304, 9, 2))
WORDS = {0x532C2B7C: 0xE3A00014, 0x532C2B80: 0xE12FFF1E,
         0x535C2514: 0xE3500013, 0x532B44DC: 0xE3500013, 0x532B6F3C: 0xE3530018}
# Known uploader windows: retain every byte, rather than relying on absence of references.
U1 = (0x53D36ABC, 0x53D3BE30, 0x53D3DD54, 0x53D3EE1C, 0x53D431F8, 0x53D46058,
      0x53D3FBE4, 0x53D38840, 0x53D46E20, 0x53D40F94, 0x53D3A834, 0x53D42430)
U2 = (0x53D35CBC, 0x53D37884, 0x53D44EB0, 0x53D39788, 0x53D440B0, 0x53D3CDD4)
PROTECTED = [(0x53D445B4, 0x53D44EB0)] + [(a, a + 0xDC8) for a in U1] + \
            [(a, a + 0x1C4) for a in U2] + [(a, a + 0x1B6) for a in (0x53D39608, 0x53D47BE8)]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def require_owned(address, size, allocations):
    require(size >= 0 and any(lo <= address and address + size <= hi for lo, hi in allocations),
            f'unowned write [{address:#x}, {address + size:#x})')


def check_allocations(allocations):
    ordered = sorted(allocations)
    require(all(lo < hi for lo, hi in ordered), 'empty/reversed allocation')
    require(all(a[1] <= b[0] for a, b in zip(ordered, ordered[1:])), 'overlapping allocations')


def check_changes(old, new, allowed):
    import numpy as np
    require(len(old) == len(new), 'length changed')
    changes = np.flatnonzero(np.frombuffer(old, 'u1') != np.frombuffer(new, 'u1'))
    covered = np.zeros(len(changes), dtype=bool)
    for lo, hi in allowed:
        covered |= (lo <= changes) & (changes < hi)
    require(bool(covered.all()), f'unapproved changed bytes: {changes[~covered][:16].tolist()}')
    return len(changes)


def read(rtos, address, size):
    off = address - BASE
    require(0 <= off and off + size <= len(rtos), f'read out of bounds {address:#x}')
    return rtos[off:off + size]


def word(rtos, address):
    return struct.unpack('<I', read(rtos, address, 4))[0]


def check_playback(rtos):
    for addr, expected in WORDS.items():
        require(word(rtos, addr) == expected, f'instruction mismatch {addr:#x}')
    for low, high, target, cond, reg in POINTERS:
        for at, imm, opcode in ((low, target & 65535, 0x03000000), (high, target >> 16, 0x03400000)):
            value = word(rtos, at)
            require(value & 0xFFF0F000 == (cond << 28 | opcode | reg << 12), f'pointer opcode {at:#x}')
            require(((value >> 16 & 15) << 12 | value & 4095) == imm, f'pointer target {at:#x}')
    for addr, expected in TABLES:
        require(read(rtos, addr, len(expected)) == expected, f'playback table {addr:#x}')


def check_protected(stock, candidate):
    for lo, hi in PROTECTED:
        require(read(stock, lo, hi - lo) == read(candidate, lo, hi - lo), f'protected window {lo:#x}')


def scan_references(code, base, spans):
    """ARM linear scan with bounded local MOVW tracking; not global dataflow analysis."""
    from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM, CS_GRP_JUMP, CS_GRP_CALL, CS_GRP_RET
    from capstone.arm import ARM_INS_MOVW, ARM_INS_MOVT, ARM_REG_PC, ARM_OP_MEM
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    md.detail = True
    md.skipdata = True
    pending, hits = {}, []
    def record(kind, source, target):
        if any(lo <= target < hi for lo, hi in spans):
            hits.append((kind, source, target))
    # Keep chunks bounded so Capstone does not allocate millions of instructions at once.
    for offset in range(0, len(code), 1 << 20):
        chunk = code[offset:offset + (1 << 20)]
        end = base + offset
        for ins in md.disasm(chunk, base + offset):
            end = ins.address + ins.size
            if not ins.id:
                pending.clear()
                continue
            for op in ins.operands:
                if op.type == ARM_OP_MEM and op.mem.base == ARM_REG_PC and not op.mem.index:
                    # Post-index addressing uses the unmodified PC for the access.
                    post = '],' in ins.op_str
                    record('pc', ins.address, ins.address + 8 + (0 if post else op.mem.disp))
            if ins.id == ARM_INS_MOVT:
                reg = ins.operands[0].reg
                if reg in pending:
                    low, at, cond = pending[reg]
                    if ins.address - at <= 64 and cond == ins.cc:
                        record('pair', ins.address, ins.operands[1].imm << 16 | low)
            _, writes = ins.regs_access()
            for reg in writes:
                pending.pop(reg, None)
            if any(ins.group(g) for g in (CS_GRP_JUMP, CS_GRP_CALL, CS_GRP_RET)) or ARM_REG_PC in writes:
                pending.clear()
            elif len(ins.bytes) == 4 and int.from_bytes(ins.bytes, 'little') & 0x0FF00000 == 0x03000000:
                pending[ins.operands[0].reg] = (ins.operands[1].imm, ins.address, ins.cc)
        require(end == base + offset + len(chunk), 'incomplete disassembly coverage')
    return hits
