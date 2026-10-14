"""MultiAxial probe firmware — round 4 (last planned). TEMPORARY, not for shooting.

Rounds 1-3 (FINDINGS §15-17b): MultiAxial's own set (boundaries, selectors, control[0], thresholds,
360-entry hue table, matrices) never makes the matrices act, and CC0CTL bits 0-1 are a CC0K gain.
Remaining guess: an enable bit elsewhere in the CCA0 header (info+0x120..0x13F), which no tuning code
writes except CC0CTL bits 0-1 (rest stock 0). Each probe mode ORs a mask into one header word.

Stub (as round 2, dead Cross-preset code 0x536DD4B8, entered from MultiAxial Make's tail call):
probe sets' YCbCr array halfword 9 = 0xA500 | word offset, halfwords 10-11 = 32-bit OR mask.
MultiAxial config in every probe mode: bounds i*256, selectors i, stock thresholds, hue table 384,
round-2 coded matrices.

Usage: make_ma_probe4.py fwdc239b.bin out.bin
"""
import sys, struct
from gr3patch import Image, RECORDS
from make_ma_probe import STD_REC, MA_TABLE, SEL_BLOCK, SEL_BLOCK_LEN, TOBJ, YCC, SMALL, TABLE_AT, EVEN, SEL_I, B
from make_ma_probe import patch_code as round1_code
from make_ma_probe2 import matrix, STUB
from make_ma_probe3 import TABLE_VALUE, HUE_TABLE_AT

PROBES = {                            # tone: (name, CCA0 header byte offset (word aligned), OR mask)
    12: ('Vivid',    0x00, 0x000000FC),   # CC0CTL bits 2-7
    17: ('Positive', 0x00, 0x0000FF00),   # CC0CTL bits 8-15
    22: ('Negative', 0x00, 0xFFFF0000),   # CC0CTL bits 16-31
    19: ('Retro',    0x04, 0xFFFFFFFF),
    20: ('HDR Tone', 0x08, 0xFFFFFFFF),
    21: ('Cross',    0x10, 0xFFFFFFFF),
}


def patch(img):
    stock_block = bytearray(img.read(SEL_BLOCK, SEL_BLOCK_LEN))
    assert stock_block[:20] == bytes(20)
    ycc = img.read(YCC, 18)
    img.write(TABLE_AT, struct.pack('<540i', *[v for m in range(60) for v in matrix(m)]))
    img.write(HUE_TABLE_AT, struct.pack('<360i', *[TABLE_VALUE] * 360))
    cur = SMALL
    def alloc(data):
        nonlocal cur
        at = cur
        img.write(at, data)
        cur += (len(data) + 3) & ~3
        assert cur <= SMALL + 1536
        return at
    mat_obj = alloc(struct.pack('<8I', *[TABLE_AT] * 8))
    hue_obj = alloc(struct.pack('<8I', *[HUE_TABLE_AT] * 8))
    bounds = alloc(struct.pack('<16H', *EVEN))
    blk = bytearray(stock_block)
    blk[:20] = bytes(SEL_I)
    blk_at = alloc(bytes(blk))
    out = {}
    for tone, (name, off, mask) in PROBES.items():
        assert off % 4 == 0 and off < 0x20
        ycc_at = alloc(ycc + struct.pack('<HI', 0xA500 | off, mask))
        assert (ycc_at + 0x14) % 4 == 0
        s = alloc(struct.pack('<8I', bounds, blk_at, mat_obj, hue_obj, blk_at + 20, ycc_at, 0, 0))
        slot = 25 if tone == 22 else tone
        img.write(MA_TABLE + 4 * slot, struct.pack('<I', s))
        img.write(RECORDS + 4 * slot, struct.pack('<I', STD_REC))
        out[tone] = (name, hex(off), hex(mask), hex(s))
    img.write(RECORDS + 4 * 24, struct.pack('<I', STD_REC))
    round1_code(img)
    patch_stub(img)
    return out


def patch_stub(img):
    assert img.word(0x536E4498) == B(0x536E4498, 0x536DF55C)
    assert img.word(STUB) == 0xE5D73797
    stub = [
        0xE5902014,                       # ldr    r2, [r0, #0x14]     YCbCr coeffs (set[5])
        0xE1D231B2,                       # ldrh   r3, [r2, #0x12]     tag = 0xA500 | offset
        0xE5922014,                       # ldr    r2, [r2, #0x14]     OR mask
        0xE2433CA5,                       # sub    r3, r3, #0xa500
        0xE3530020,                       # cmp    r3, #0x20
        0x3791C003,                       # ldrlo  ip, [r1, r3]
        0x318CC002,                       # orrlo  ip, ip, r2
        0x3781C003,                       # strlo  ip, [r1, r3]
        B(STUB + 32, 0x536DF55C),         # b      MultiAxial writer
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
