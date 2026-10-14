"""MultiAxial (hue-area colour correction) probe firmware — round 1. TEMPORARY, not for shooting.

The GR III ships MultiAxial with all boundaries/selectors 0 and identity matrices (except matrix 0),
so its geometry is unknown. This build gives six modes their own MultiAxial set (per-tone table
0x55018CF0) whose 60 matrices are pure gains coded by index, so a photo of a hue chart shows which
matrix the hardware picks for each hue/saturation/brightness, and whether it is active at all.

Set layout (calc 0x536DF484 / write 0x536DF55C, register image info+0x120):
  [0] 16 x u16 boundaries (12-bit)      [1] 20 selector bytes (4 bits used), followed directly by
  [4] control block (u16: [0] 6-bit field, [1..8] 12-bit thresholds, [9..20] misc)
  [2] object -> +0x10 -> 540 x int32 matrices (12-bit signed, Q10)    [3] object -> +0x10 -> 360 x 10-bit
  [5] RGB->YCbCr coefficients (77,150,29,-43,-85,128,128,-107,-21)

All probe modes use the Standard look record (no film looks), Cross curves are disabled (selector
forced 0) and the HDR/Retro extras are off (FINDINGS §14a), so the only difference from Standard
is MultiAxial. Data lives in the Cross curve library ROM area (unused while selector is 0).
Standard and the other modes keep the stock MultiAxial set.

Usage: make_ma_probe.py fwdc239b.bin out.bin
"""
import sys, struct
from gr3patch import Image, RECORDS

STD_REC = 0x5501900C
MA_TABLE = 0x55018CF0                 # per-tone MultiAxial set pointers
STOCK_SET = 0x53DC2BA0
SEL_BLOCK, SEL_BLOCK_LEN = 0x53DC2BB8, 0x48   # selectors (20 nibbles) + control block, contiguous
TOBJ, YCC = 0x55019848, 0x53DC3A40
SMALL = 0x53EFB0E4                    # 1536 B free (Cross curves 11, 0, 4 + ... see lib table)
TABLE_AT = 0x53EFB928                 # 4096 B free (Cross curves)
LEVELS = [0.85, 0.68, 0.54, 0.44, 0.35, 0.28, 0.22, 0.18]   # matrix m -> gain LEVELS[m % 8]; bypass = 1.0

EVEN = [i * 256 for i in range(16)]
SHIFTED = [i * 256 + 128 for i in range(16)]
SEL_I = list(range(16)) + [0, 0, 0, 0]
PROBES = {                            # tone: (name, boundaries, selectors, control[0], thresholds)
    12: ('Vivid',    EVEN,    SEL_I,    None, None),
    17: ('Positive', EVEN,    SEL_I,    1,    None),
    22: ('Negative', EVEN,    SEL_I,    0x3F, None),
    19: ('Retro',    EVEN,    [5] * 20, None, None),
    20: ('HDR Tone', SHIFTED, SEL_I,    None, None),
    21: ('Cross',    EVEN,    SEL_I,    None, [512 * (k + 1) - 1 for k in range(8)]),
}


def patch(img):
    stock_block = bytearray(img.read(SEL_BLOCK, SEL_BLOCK_LEN))
    assert stock_block[:20] == bytes(20)
    table = struct.pack('<540i', *[round(1024 * LEVELS[(e // 9) % 8]) if e % 9 in (0, 4, 8) else 0 for e in range(540)])
    img.write(TABLE_AT, table)
    cur = SMALL
    def alloc(data):
        nonlocal cur
        at = cur
        img.write(at, data)
        cur += (len(data) + 3) & ~3
        assert cur <= SMALL + 1536
        return at
    mat_obj = alloc(struct.pack('<8I', *[TABLE_AT] * 8))
    out = {}
    for tone, (name, bounds, sel, ctl0, thr) in PROBES.items():
        b = alloc(struct.pack('<16H', *bounds))
        blk = bytearray(stock_block)
        blk[:20] = bytes(sel)                      # one byte per selector (4 bits used)
        ctl = 20                                    # control block starts at selector block + 0x14
        if ctl0 is not None:
            blk[ctl:ctl + 2] = struct.pack('<H', ctl0)
        if thr is not None:
            blk[ctl + 2:ctl + 18] = struct.pack('<8H', *thr)
        blk_at = alloc(bytes(blk))
        s = alloc(struct.pack('<8I', b, blk_at, mat_obj, TOBJ, blk_at + ctl, YCC, 0, 0))
        slot = 25 if tone == 22 else tone             # Negative uses table slot 25 (0x536DC280)
        img.write(MA_TABLE + 4 * slot, struct.pack('<I', s))
        img.write(RECORDS + 4 * slot, struct.pack('<I', STD_REC))
        out[tone] = (name, hex(s))
    img.write(RECORDS + 4 * 24, struct.pack('<I', STD_REC))
    patch_code(img)
    return out


B = lambda at, to, cond=0xE: (cond << 28) | 0x0A000000 | (((to - at - 8) >> 2) & 0xFFFFFF)


def patch_code(img):
    def put(at, word, expect):
        assert img.word(at) == expect, f'{at:#x}: {img.word(at):#010x} != {expect:#010x}'
        img.write(at, struct.pack('<I', word))
    put(0x536DD444, 0xE35100FF, 0xE3510015)                # Cross curve selector never set (cmp r1,#0x15 -> #0xff)
    put(0x536DBEB4, 0xE3A09000, 0xE5D39788)                # HDR extras off (as films v2)
    put(0x536DBEBC, 0xE3A02000, 0xE5D32796)
    put(0x535131FC, B(0x535131FC, 0x53513218, 0x0), B(0x535131FC, 0x53513274, 0x0))
    put(0x536DC27C, 0xE1A00000, B(0x536DC27C, 0x536DC818, 0x0))
    put(0x536DBE98, 0xE1CE10B0, 0xE1CE40B0)                # Retro extra off (as films v2)


if __name__ == '__main__':
    img = Image(sys.argv[1])
    print(patch(img))
    data, rep = img.build()
    open(sys.argv[2], 'wb').write(data)
    print(rep)
