"""MultiAxial probe firmware — round 3. TEMPORARY, not for shooting.

Round 2 (FINDINGS §16a): CC0CTL is a CC0K output gain (0 -> x0.5, 1 -> x1, 2 -> x2, 3 -> x4), not a
MultiAxial enable. But rounds 1 and 2 both show a small selector-dependent effect (greens -2 codes,
cyan..magenta +1 at x1 when selectors = i vs. all equal), so MultiAxial runs at stock CC0CTL = 1 and
something else keeps its matrices from acting. Candidates, both stock-neutral:
  * the 360 x 10-bit per-degree table (set[3] object +0x10, stock all 0) = per-hue strength/shift;
  * the 8 x 12-bit thresholds (control[1..8], stock 4095) = saturation/luma windows.
Round 3 crosses them at stock CC0CTL with round 2's coded matrices (level = m % 10, tint = m // 10).

Usage: make_ma_probe3.py fwdc239b.bin out.bin
"""
import sys, struct
from gr3patch import Image, RECORDS
from make_ma_probe import STD_REC, MA_TABLE, SEL_BLOCK, SEL_BLOCK_LEN, TOBJ, YCC, SMALL, TABLE_AT, EVEN, SEL_I
from make_ma_probe import patch_code as round1_code
from make_ma_probe2 import matrix

TABLE_VALUE = 384                      # nonzero whether the 10-bit field is unsigned (0.375) or signed (+384)
HUE_TABLE_AT = TABLE_AT + 540 * 4      # after the matrices; 1440 B, region ends 0x53EFC928
THR0 = [0] * 8
RAMP = [512 * (k + 1) - 1 for k in range(8)]
PROBES = {                             # tone: (name, thresholds (None = stock 4095), hue table, selectors)
    12: ('Vivid',    THR0, False, SEL_I),
    17: ('Positive', RAMP, False, SEL_I),
    22: ('Negative', None, True,  SEL_I),
    19: ('Retro',    THR0, True,  SEL_I),
    20: ('HDR Tone', RAMP, True,  SEL_I),
    21: ('Cross',    THR0, True,  [0] * 20),
}


def patch(img):
    stock_block = bytearray(img.read(SEL_BLOCK, SEL_BLOCK_LEN))
    assert stock_block[:20] == bytes(20)
    assert struct.unpack('<8H', stock_block[22:38]) == (4095,) * 8
    img.write(TABLE_AT, struct.pack('<540i', *[v for m in range(60) for v in matrix(m)]))
    img.write(HUE_TABLE_AT, struct.pack('<360i', *[TABLE_VALUE] * 360))
    assert HUE_TABLE_AT + 1440 <= 0x53EFC928
    stock_tobj = img.read(TOBJ, 32)
    assert set(struct.unpack('<8I', stock_tobj)) == {0x53DC2BF8}
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
    out = {}
    for tone, (name, thr, table, sel) in PROBES.items():
        blk = bytearray(stock_block)
        blk[:20] = bytes(sel)
        if thr is not None:
            blk[22:38] = struct.pack('<8H', *thr)
        blk_at = alloc(bytes(blk))
        s = alloc(struct.pack('<8I', bounds, blk_at, mat_obj, hue_obj if table else TOBJ, blk_at + 20, YCC, 0, 0))
        slot = 25 if tone == 22 else tone
        img.write(MA_TABLE + 4 * slot, struct.pack('<I', s))
        img.write(RECORDS + 4 * slot, struct.pack('<I', STD_REC))
        out[tone] = (name, thr, table, hex(s))
    img.write(RECORDS + 4 * 24, struct.pack('<I', STD_REC))
    round1_code(img)
    return out


if __name__ == '__main__':
    img = Image(sys.argv[1])
    print(patch(img))
    data, rep = img.build()
    open(sys.argv[2], 'wb').write(data)
    print(rep)
