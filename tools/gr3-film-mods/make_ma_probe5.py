"""MultiAxial probe firmware — round 5. TEMPORARY, not for shooting.

Rounds 1-4 (FINDINGS §15-18a) never made the MultiAxial matrices act on GR III stills. FINDINGS §29: the GR IV has the
same set layout and its stock Standard (and slots 17-19) use an *active* set with values no GR III probe tried:
bounds as pairs (1298,750,0,0, 1448,843,0,0, ...), 12-zone selectors, control[0] = 32, thresholds 328..3200 and
control[10..13] = 1024 (GR III stock 0,0,21,62). Round 5 copies that set (work/ma_probe5/gr4_std_ma.json, from GR IV
1.11 set 0x54049DE8) into GR III probe modes, then ablates one field at a time back to the GR III stock value:

  Vivid     as Positive, selectors = 0 (GR III; every hue -> zone 0)
  Positive  GR IV set + marker matrices (zone z -> grey gain MARK[z], same at all 5 levels)  <- main test
  Negative  as Positive, control[10..20] = GR III stock (0,0,21,62,0,1,2,7,0,640,1280)
  Retro     as Positive, control[0] = 0 (GR III)
  HDR Tone  as Positive, thresholds control[1..8] = 4095 (GR III)
  Cross     as Positive, bounds = 0 (GR III)

As rounds 1-4: probe modes use the Standard look record, Cross curves / HDR and Retro extras off, data in the Cross
curve ROM area; Standard and all other modes keep the stock (inactive) set. (GR IV Standard's own matrices are kept in
gr4_std_ma.json for a later look test; the 4 KB Cross area fits only one 60-matrix table.)

Usage: make_ma_probe5.py fwdc239b.bin out.bin
"""
import sys, struct, json, os
from gr3patch import Image, RECORDS
from make_ma_probe import STD_REC, MA_TABLE, SEL_BLOCK, SEL_BLOCK_LEN, TOBJ, YCC, SMALL, TABLE_AT
from make_ma_probe import patch_code as round1_code

G4 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work/ma_probe5/gr4_std_ma.json')))
MARK = [0.85, 0.30, 0.75, 0.40, 0.65, 0.50, 0.85, 0.30, 0.75, 0.40, 0.65, 0.50]   # zone z -> grey gain


def marker():
    return [round(1024 * MARK[m // 5]) if e in (0, 4, 8) else 0 for m in range(60) for e in range(9)]


GR3_CTL_TAIL = None                    # filled from the stock block (control[10..20])
PROBES = {                             # tone: (name, matrices, field reset to GR III stock)
    12: ('Vivid',    'mark', 'selectors'),
    17: ('Positive', 'mark', None),
    22: ('Negative', 'mark', 'strength'),
    19: ('Retro',    'mark', 'ctl0'),
    20: ('HDR Tone', 'mark', 'thresholds'),
    21: ('Cross',    'mark', 'bounds'),
}


def set_fields(stock_ctl, reset):
    bounds, ctl = list(G4['bounds']), list(G4['control'])
    if reset == 'strength':
        ctl[10:21] = stock_ctl[10:21]
    elif reset == 'ctl0':
        ctl[0] = stock_ctl[0]
    elif reset == 'thresholds':
        ctl[1:9] = stock_ctl[1:9]
    elif reset == 'bounds':
        bounds = [0] * 16
    sel = [0] * 20 if reset == 'selectors' else list(G4['selectors'])
    return bounds, sel, ctl


def patch(img):
    stock_block = bytearray(img.read(SEL_BLOCK, SEL_BLOCK_LEN))
    assert stock_block[:20] == bytes(20)
    stock_ctl = list(struct.unpack('<21H', stock_block[20:62]))
    assert stock_ctl == [0] + [4095] * 8 + [32, 0, 0, 21, 62, 0, 1, 2, 7, 0, 640, 1280], stock_ctl
    assert img.read(YCC, 18) == struct.pack('<9h', *G4['ycc'])
    assert struct.unpack('<8I', img.read(TOBJ, 32)) == (0x53DC2BF8,) * 8     # 10-bit table: stock 0 (GR IV too)
    img.write(TABLE_AT, struct.pack('<540i', *marker()))
    cur = SMALL

    def alloc(data):
        nonlocal cur
        at = cur
        img.write(at, data)
        cur += (len(data) + 3) & ~3
        assert cur <= SMALL + 1536
        return at
    mat_obj = {'mark': alloc(struct.pack('<8I', *[TABLE_AT] * 8))}
    out = {}
    for tone, (name, mats, reset) in PROBES.items():
        bounds, sel, ctl = set_fields(stock_ctl, reset)
        blk = bytearray(stock_block)
        blk[:20] = bytes(sel)
        blk[20:62] = struct.pack('<21H', *ctl)
        b_at, blk_at = alloc(struct.pack('<16H', *bounds)), alloc(bytes(blk))
        s = alloc(struct.pack('<8I', b_at, blk_at, mat_obj[mats], TOBJ, blk_at + 20, YCC, 0, 0))
        slot = 25 if tone == 22 else tone
        img.write(MA_TABLE + 4 * slot, struct.pack('<I', s))
        img.write(RECORDS + 4 * slot, struct.pack('<I', STD_REC))
        out[tone] = (name, mats, reset, hex(s))
    img.write(RECORDS + 4 * 24, struct.pack('<I', STD_REC))
    round1_code(img)
    return out


if __name__ == '__main__':
    img = Image(sys.argv[1])
    print(patch(img))
    data, rep = img.build()
    open(sys.argv[2], 'wb').write(data)
    print(rep)
