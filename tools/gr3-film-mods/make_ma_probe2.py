"""MultiAxial probe firmware — round 2. TEMPORARY, not for shooting.

Round 1 (FINDINGS §15a) showed no MultiAxial effect at all. The block's registers live inside the
CCA0 register group (info+0x120: byte 0 = 2-bit CC0CTL, +0x20 CC0K matrix, +0x40 Y-blend, +0x80..
MultiAxial), and the ColorMatrix calc hard-codes CC0CTL = 1 (0x536DEF10 `mov r3,#1`). Round 2 tries
the other CC0CTL values per mode, on the hypothesis that 1 = linear matrix only.

Per-mode CC0CTL: the probe sets' YCbCr coefficient arrays (set[5], 9 halfwords read by the writer)
carry a tag in halfword 9 (stock: unused padding 0) = 0xA500 | ctl. MultiAxial Make's tail call
(0x536E4498 `b write`) is redirected to a stub in the dead Cross-preset code at 0x536DD4B8 (dead
because the Cross selector compare is patched to #0xff, as in round 1) that, when the tag is present,
replaces CC0CTL bits 0-1 in info+0x120 (ColorMatrix writes it just before), then jumps to the writer.

Matrices: matrix m = diag(R, G, B) with G = 256 * LEVELS[m % 10] and R/B = G * TINTS[m // 10], so a
patch's brightness gives m % 10 and its R/G, B/G shift gives m // 10. Peak entry 256 stays <= 1.0
whether the format is Q8, Q9 or Q10 (round 1 assumed Q10; stock matrix 0 suggests Q9).

Usage: make_ma_probe2.py fwdc239b.bin out.bin
"""
import sys, struct
from gr3patch import Image, RECORDS
from make_ma_probe import STD_REC, MA_TABLE, SEL_BLOCK, SEL_BLOCK_LEN, TOBJ, YCC, SMALL, TABLE_AT, EVEN, SEL_I, B
from make_ma_probe import patch_code as round1_code

LEVELS = [1.0, 0.84, 0.7, 0.59, 0.5, 0.42, 0.35, 0.3, 0.25, 0.21]
TINTS = [(1, 1), (0.75, 1), (1, 0.75), (0.75, 0.75), (0.55, 1), (1, 0.55)]   # (R/G, B/G) per m // 10
STUB = 0x536DD4B8
PROBES = {                            # tone: (name, CC0CTL, selectors, control[0])
    12: ('Vivid',    2, SEL_I,    None),
    17: ('Positive', 3, SEL_I,    None),
    22: ('Negative', 2, SEL_I,    0x3F),
    19: ('Retro',    3, SEL_I,    0x3F),
    20: ('HDR Tone', 0, SEL_I,    None),
    21: ('Cross',    2, [0] * 20, None),
}


def matrix(m):
    g = 256 * LEVELS[m % 10]
    r, b = TINTS[m // 10]
    return [round(g * r), 0, 0, 0, round(g), 0, 0, 0, round(g * b)]


def patch(img):
    stock_block = bytearray(img.read(SEL_BLOCK, SEL_BLOCK_LEN))
    assert stock_block[:20] == bytes(20)
    ycc = img.read(YCC, 18)
    assert img.read(YCC + 18, 2) == bytes(2)
    img.write(TABLE_AT, struct.pack('<540i', *[v for m in range(60) for v in matrix(m)]))
    cur = SMALL
    def alloc(data):
        nonlocal cur
        at = cur
        img.write(at, data)
        cur += (len(data) + 3) & ~3
        assert cur <= SMALL + 1536
        return at
    mat_obj = alloc(struct.pack('<8I', *[TABLE_AT] * 8))
    bounds = alloc(struct.pack('<16H', *EVEN))
    out = {}
    for tone, (name, ctl, sel, ctl0) in PROBES.items():
        blk = bytearray(stock_block)
        blk[:20] = bytes(sel)
        if ctl0 is not None:
            blk[20:22] = struct.pack('<H', ctl0)
        blk_at = alloc(bytes(blk))
        ycc_at = alloc(ycc + struct.pack('<H', 0xA500 | ctl))
        s = alloc(struct.pack('<8I', bounds, blk_at, mat_obj, TOBJ, blk_at + 20, ycc_at, 0, 0))
        slot = 25 if tone == 22 else tone
        img.write(MA_TABLE + 4 * slot, struct.pack('<I', s))
        img.write(RECORDS + 4 * slot, struct.pack('<I', STD_REC))
        out[tone] = (name, ctl, hex(s))
    img.write(RECORDS + 4 * 24, struct.pack('<I', STD_REC))
    round1_code(img)
    patch_stub(img)
    return out


def patch_stub(img):
    assert img.word(0x536E4498) == B(0x536E4498, 0x536DF55C)
    assert img.word(STUB) == 0xE5D73797                   # ldrb r3,[r7,#0x797] (Cross preset, now dead)
    stub = [
        0xE5902014,                                         # ldr   r2, [r0, #0x14]   YCbCr coeffs (set[5])
        0xE1D221B2,                                         # ldrh  r2, [r2, #0x12]   halfword 9 = tag
        0xE2023CFF,                                         # and   r3, r2, #0xff00
        0xE3530CA5,                                         # cmp   r3, #0xa500
        0x05D13000,                                         # ldrbeq r3, [r1]         CC0CTL byte
        0x03C33003,                                         # biceq r3, r3, #3
        0x02022003,                                         # andeq r2, r2, #3
        0x01833002,                                         # orreq r3, r3, r2
        0x05C13000,                                         # strbeq r3, [r1]
        B(STUB + 36, 0x536DF55C),                           # b     MultiAxial writer
    ]
    for i, word in enumerate(stub):
        img.write(STUB + 4 * i, struct.pack('<I', word))
    img.write(0x536E4498, struct.pack('<I', B(0x536E4498, STUB)))


if __name__ == '__main__':
    img = Image(sys.argv[1])
    print(patch(img))
    data, rep = img.build()
    open(sys.argv[2], 'wb').write(data)
    print(rep)
