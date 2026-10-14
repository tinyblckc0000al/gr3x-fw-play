"""Replace four Image Control modes with fitted film looks (one cube_fit.py result each).

    Vivid         (tone 12) -> curve set 4 (library R9,G10,B11), own record 0x550196D8
    Retro         (tone 19) -> curve set 3 (R6,G7,B8),           own record 0x55019108
    HDR Tone      (tone 20) -> curve set 3 with library curves R0,G1,B2 swapped in (v4), legacy slot-1 record 0x55019060
    Cross Process (tone 21) -> curve set 2 (R3,G4,B5),           legacy slot-2 record 0x5501939C

Only selector values 2/3/4 (Cross presets 0/1/2) pick a fixed curve set. Value 1 is the Cross
"random" mode (0x536EF618, rand()%6/%9) and 5..8 copy a saved set from SI+0x38A9A, so a fourth
mode has to share a set. v4: curves 0-2 (only used by the Cross "random" preset, unreachable once
the selector is forced per tone) hold HDR's own curves, and the ctx fill writes library pointers 6-8
(RAM 0x5503761C) per call: curves 0,1,2 when tone == 20, else the stock 6,7,8 (Retro's set). So
HDR still uses selector 3 but gets its own curves.

Each record becomes a copy of the shared Standard record with its own look matrix (f1).
Code patches (equal size, in place):
  * ctx fill 0x536DD450/0x536DD4B8: SI+0x38A98 (curve-set selector, ctx+0x9B) is set per tone
    instead of only for Cross Process (where it came from the Cross preset SI+0x797).
  * 0x536DBEB4: HDR Tone passes HDR intensity 0 (as Standard does) instead of SI+0x788.
  * 0x536DC27C: HDR Tone always uses record slot 20 (the SI+0x788=1/2 branch picked slot 24).
  * after camera test 1 (HDR still tone-mapped, Retro still vignetted):
    0x536DBEBC HDR passes SI+0x796 as 0 (ctx+0x1FA; Standard passes 0),
    0x535131FC HDR takes Standard's gate for the extra local-processing pass (was: on if SI+0x796),
    0x536DBE98 Retro writes 0 instead of 4 to ctx+0x1FC (the only ctx field unique to Retro).

Also redraws the four mode icons (make_icons.py) and renames the modes (make_names.py).

Usage: make_films.py [--raw-nr-off | --raw-nr-from-6400 | --raw-nr-above ISO] [--cca1 mats.json] vivid.json retro.json hdr.json cross.json fwdc239b.bin out.bin [icons.png]
  --cca1 mats.json: per-film post-gamma 3x3 from cca1_fit.py --out (cca1.py, FINDINGS §22g)
  --raw-nr-above ISO: keep the RAW NR only above ISO (e.g. 8000 -> from 10000 up) (raw_nr.py, FINDINGS §21c)
  --raw-nr-from-6400: keep the RAW NR only at ISO >= 6400 (raw_nr.py, FINDINGS §21b)
  --raw-nr-off: also turn off the PPU Bayer NR applied to stills before the RAW is stored (raw_nr.py, FINDINGS §21)
"""
import sys, json, struct
from gr3patch import Image, RECORDS
from make_film import q13_matrix, SHARED_REC, REC_LEN, CURVE_LIB

# name, tone, record slot(s) to point at the record, donor record slot, selector value, curve ids R,G,B
MODES = [
    ('vivid', 12, (12,), 12, 4, (9, 10, 11)),
    ('retro', 19, (19,), 19, 3, (6, 7, 8)),
    ('hdr', 20, (20, 24), 1, 3, (0, 1, 2)),
    ('cross', 21, (21,), 2, 2, (3, 4, 5)),
]

B = lambda at, to, cond=0xE: (cond << 28) | 0x0A000000 | (((to - at - 8) >> 2) & 0xFFFFFF)


def patch_code(img):
    def put(at, word, expect=None):
        if expect is not None:
            assert img.word(at) == expect, f'{at:#x}: {img.word(at):#010x} != {expect:#010x}'
        img.write(at, struct.pack('<I', word))

    add38k, strb_a98, ldm_ret = img.word(0x536DD458), img.word(0x536DD460), img.word(0x536DD464)
    assert (add38k, strb_a98) == (0xE283390E, 0xE5C32A98), (hex(add38k), hex(strb_a98))
    put(0x536DD450, 0xE59632D0, 0x159632D0)              # ldrne r3,[r6,#0x2d0] -> ldr
    # Library pointers 6-8 = HDR's curves 0-2 when tone == 20, else stock 6-8. Uses the 4 words after
    # 0x536DD454 (only reached from the dead Cross-preset code this patch overwrites) plus 0x536DD4B8..
    lib = [img.word(CURVE_LIB + 4 * i) for i in range(12)]
    assert all(a >> 16 == 0x53EF for a in lib)
    movw = lambda cond, rd, v: (cond << 28) | 0x03000000 | ((v >> 12) << 16) | (rd << 12) | (v & 0xFFF)
    movt = lambda rd, v: 0xE3400000 | ((v >> 12) << 16) | (rd << 12) | (v & 0xFFF)
    EQ, NE = 0x0, 0x1
    pick = lambda rd, own, stock: [movw(EQ, rd, lib[own] & 0xFFFF), movw(NE, rd, lib[stock] & 0xFFFF), movt(rd, 0x53EF)]
    r4, r5, r7, r0 = 4, 5, 7, 0
    p8 = CURVE_LIB + 24
    put(0x536DD454, 0xE3510014, B(0x536DD454, 0x536DD4B8, 0x0))  # cmp r1,#20 (was beq)
    head = pick(r4, 0, 6) + [B(0x536DD464, 0x536DD4B8)]
    for i, word in enumerate(head):
        put(0x536DD458 + 4 * i, word)
    seq = pick(r5, 1, 7) + pick(r7, 2, 8)
    seq += [movw(0xE, r0, p8 & 0xFFFF), movt(r0, p8 >> 16), 0xE88000B0]   # stm r0,{r4,r5,r7}
    seq += [add38k, 0xE3A02000]                              # add r3,#0x38000 ; mov r2,#0
    for _, tone, _, _, sel, _ in MODES:
        seq += [0xE3510000 | tone, 0x03A02000 | sel]        # cmp r1,#tone ; moveq r2,#sel
    seq += [strb_a98, ldm_ret]
    assert 0x536DD4B8 + 4 * len(seq) <= 0x536DD510, len(seq)
    for i, word in enumerate(seq):
        put(0x536DD4B8 + 4 * i, word)
    patch_mode_fixes(img)


def patch_mode_fixes(img):
    """HDR Tone / Retro side effects outside the look record (camera tests 1-2)."""
    def put(at, word, expect=None):
        if expect is not None:
            assert img.word(at) == expect, f'{at:#x}: {img.word(at):#010x} != {expect:#010x}'
        img.write(at, struct.pack('<I', word))
    put(0x536DBEB4, 0xE3A09000, 0xE5D39788)               # ldrb sb,[r3,#0x788] -> mov sb,#0
    put(0x536DC27C, 0xE1A00000, B(0x536DC27C, 0x536DC818, 0x0))  # beq hdr-variant -> nop
    # Camera test 1 (photo-test1): HDR Tone still tone-mapped locally, Retro still vignetted.
    put(0x536DBEBC, 0xE3A02000, 0xE5D32796)               # HDR: ldrb r2,[r3,#0x796] -> mov r2,#0 (ctx+0x1FA, SI+0x796)
    put(0x535131FC, B(0x535131FC, 0x53513218, 0x0), B(0x535131FC, 0x53513274, 0x0))  # HDR uses Standard's local-process gate
    put(0x536DBE98, 0xE1CE10B0, 0xE1CE40B0)               # Retro: strh r4(=4),[ctx+0x1FC] -> strh r1(=0)


def patch(img, fits):
    shared = bytes(img.read(SHARED_REC, REC_LEN))
    out = {}
    for (name, tone, slots, donor_slot, sel, curve_ids), fit in zip(MODES, fits):
        rec = img.word(RECORDS + 4 * donor_slot)
        mat = img.word(rec + 4)
        assert rec != SHARED_REC
        data = bytearray(shared)
        data[4:8] = struct.pack('<I', mat)
        img.write(rec, bytes(data))
        for s in slots:
            img.write(RECORDS + 4 * s, struct.pack('<I', rec))
        q = q13_matrix(fit['matrix'])
        img.write(mat, struct.pack('<9h', *q.ravel().tolist()))
        for cid, curve in zip(curve_ids or (), fit['presets'][0]['curves']):
            img.write(img.word(CURVE_LIB + 4 * cid), struct.pack('<256H', *curve))
        out[name] = dict(record=hex(rec), matrix_at=hex(mat), q13=q.tolist(), selector=sel, curves=curve_ids)
    patch_code(img)
    return out


if __name__ == '__main__':
    raw_nr_off = '--raw-nr-off' in sys.argv
    if raw_nr_off:
        sys.argv.remove('--raw-nr-off')
    raw_nr_6400 = '--raw-nr-from-6400' in sys.argv
    if raw_nr_6400:
        sys.argv.remove('--raw-nr-from-6400')
    cca1 = None
    if '--cca1' in sys.argv:
        i = sys.argv.index('--cca1')
        cca1 = json.load(open(sys.argv[i + 1]))
        del sys.argv[i:i + 2]
    raw_nr_above = None
    if '--raw-nr-above' in sys.argv:
        i = sys.argv.index('--raw-nr-above')
        raw_nr_above = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    fits = [json.load(open(p)) for p in sys.argv[1:5]]
    img = Image(sys.argv[5])
    info = patch(img, fits)
    if raw_nr_off:
        from raw_nr import patch_raw_nr_off
        info['raw_nr_off'] = patch_raw_nr_off(img)
    if raw_nr_6400:
        from raw_nr import patch_raw_nr_min_iso
        info['raw_nr_from_6400'] = patch_raw_nr_min_iso(img, 6400)
    if raw_nr_above:
        from raw_nr import patch_raw_nr_min_iso, above_index
        info['raw_nr_above'] = patch_raw_nr_min_iso(img, first=above_index(raw_nr_above))
    if cca1:
        from cca1 import patch_cca1_films
        mats = [cca1[p]['q512'] for p in sys.argv[1:5]]
        info['cca1'] = patch_cca1_films(img, {int(info[n]['record'], 16): m for (n, *_), m in zip(MODES, mats)})
    from make_icons import patch_icons, preview
    from make_names import patch_names
    info['icons'] = patch_icons(img)
    info['names'] = patch_names(img)
    if len(sys.argv) > 7:
        preview(img, sys.argv[7])
    data, rep = img.build()
    open(sys.argv[6], 'wb').write(data)
    for k, v in info.items():
        print(k, v)
    print(rep)
