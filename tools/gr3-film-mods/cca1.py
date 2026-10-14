"""Per-film CCA1 matrices: the v8/v9 warm-colour fix (FINDINGS §22f/22g). Superseded by film_cave.py (v10): CCA1 acts
in the linear domain before the gamma curves (§22l), not post-gamma as assumed here; and the free area ends at
0x536EF6D8 (0x536EF6DC is the live fixed-preset case), not CAVE_END.

CCA1 is live (cca1_probe red/blue swap, photo-cca1). Its 9 coefficients (12 bit, 0x200 = 1.0, rows = output R,G,B)
live in the ColorMatrix sub-object at +0x32..0x42; only the init 0x536DED70 sets them (identity) and the writer
0x536DF13C copies them to info+0x1240 every Make (still and live view). This patch makes the ColorMatrix Make wrapper
(0x536DF3D4) call a stub instead of calc 0x536DEECC: the stub looks up the look record [ctx+8] in a table, copies that
film's coefficients (or identity for every other mode) to obj+0x32, then jumps to calc.

Stub + table live in the Cross "random" preset branch 0x536EF618.. (only reached for curve-set selector 1, which the
film builds never set); its first instruction becomes a branch to the fixed-preset case 0x536EF6DC so the rest is dead.
"""
import struct

B = lambda at, to, cond=0xE: (cond << 28) | 0x0A000000 | (((to - at - 8) >> 2) & 0xFFFFFF)
BL = lambda at, to: 0xEB000000 | (((to - at - 8) >> 2) & 0xFFFFFF)

CALC, WRAP_BL = 0x536DEECC, 0x536DF3E8
RANDOM, PRESET = 0x536EF618, 0x536EF6DC
CAVE, CAVE_END = 0x536EF61C, 0x536EF998
IDENTITY = [[512, 0, 0], [0, 512, 0], [0, 0, 512]]


def stub(at, table):
    L, C = at + 12, at + 44
    code = [
        0xE92D4010,                              # push {r4, lr}
        0xE5913008,                              # ldr  r3, [r1, #8]        look record
        0xE28F4000 | (table - (at + 16)),        # add  r4, pc, #table
        0xE594C000,                              # L: ldr ip, [r4]
        0xE35C0000,                              # cmp  ip, #0              0 = default (identity)
        0x115C0003,                              # cmpne ip, r3
        0x12844018,                              # addne r4, r4, #24
        B(at + 28, L, 0x1),                      # bne  L
        0xE2844004,                              # add  r4, r4, #4
        0xE2803032,                              # add  r3, r0, #0x32
        0xE3A0C009,                              # mov  ip, #9
        0xE0D4E0B2,                              # C: ldrh lr, [r4], #2
        0xE0C3E0B2,                              # strh lr, [r3], #2
        0xE25CC001,                              # subs ip, ip, #1
        B(at + 56, C, 0x1),                      # bne  C
        0xE8BD4010,                              # pop  {r4, lr}
        B(at + 64, CALC),                        # b    calc
    ]
    assert table - (at + 16) < 256 and L == at + 12 and C == at + 44
    return code


def entry(key, m):
    flat = [int(v) for row in m for v in row]
    assert len(flat) == 9 and all(-2048 <= v < 2048 for v in flat)
    return struct.pack('<I9hH', key, *flat, 0)


def patch_cca1_films(img, by_record):
    """by_record: {look record address: 3x3 int matrix (512 = 1.0)}."""
    def put(at, word, expect=None):
        if expect is not None:
            assert img.word(at) == expect, f'{at:#x}: {img.word(at):#010x} != {expect:#010x}'
        img.write(at, struct.pack('<I', word))
    put(WRAP_BL, BL(WRAP_BL, CAVE), BL(WRAP_BL, CALC))
    put(RANDOM, B(RANDOM, PRESET), 0xEDDF0BE0)          # was vldr d16,[pc,#0x380]
    code = stub(CAVE, CAVE + 17 * 4)
    table = b''.join(entry(k, m) for k, m in by_record.items()) + entry(0, IDENTITY)
    blob = b''.join(struct.pack('<I', c) for c in code) + table
    assert CAVE + len(blob) <= CAVE_END
    img.write(CAVE, blob)
    return dict(stub=hex(CAVE), table=hex(CAVE + 68), bytes=len(blob),
                records={hex(k): m for k, m in by_record.items()})
