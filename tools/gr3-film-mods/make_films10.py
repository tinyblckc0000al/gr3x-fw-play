"""Films v10: five film modes, post-gamma matrix through the CSP, Bleach Bypass becomes a fifth film (FINDINGS §22l).

    Vivid         (tone 12)        -> curve set 4 (R9,G10,B11),             record 0x550196D8
    Retro         (tone 19)        -> curve set 3 (R6,G7,B8),               record 0x55019108
    HDR Tone      (tone 20)        -> curve set 3, slots 6-8 = curves 0-2,  record 0x55019060
    Cross Process (tone 21)        -> curve set 2 (R3,G4,B5),               record 0x5501939C
    Bleach Bypass (tone 18, 22/23) -> curve set 4, slots 9-11 = knot tables, record 0x55018F94 (own, Bleach matrix)

Each record becomes a copy of the shared Standard record with its own look matrix (as make_films.py; for Bleach this
also drops its toning offsets, emulated info+0x1674). The fit's 'post_q512' (joint_fit.py; older fits call it
'cca1_q512') is applied after the gamma curves through the RGB->YCbCr matrix (film_cave.py). CCA1 is left stock.
Plus the HDR/Retro fixes of make_films.py, icons, names and optionally the RAW NR limit.

v12 (--labels v12): same build, Bleach slot named/labelled for Fujifilm Classic Neg ("Classic Neg", icon "NC").

Usage: make_films10.py [--raw-nr-above ISO] [--labels v10|v12] vivid.json retro.json hdr.json cross.json bleach.json fwdc239b.bin out.bin [icons.png]
"""
import sys, json, struct
from gr3patch import Image, RECORDS
from make_film import q13_matrix, SHARED_REC, REC_LEN, CURVE_LIB
from make_films import patch_mode_fixes
from film_cave import patch_cave, knots_of, expand

# name, tone, record slots, donor slot, selector, library curve ids R,G,B (None = knot tables)
MODES = [
    ('vivid', 12, (12,), 12, 4, (9, 10, 11)),
    ('retro', 19, (19,), 19, 3, (6, 7, 8)),
    ('hdr', 20, (20, 24), 1, 3, (0, 1, 2)),
    ('cross', 21, (21,), 2, 2, (3, 4, 5)),
    ('bleach', 18, (18, 22, 23), 18, 4, None),
]


def post_of(fit):
    return fit.get('post_q512', fit.get('cca1_q512'))


def patch(img, fits):
    shared = bytes(img.read(SHARED_REC, REC_LEN))
    out, post, knots = {}, {}, None
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
        curves = fit['presets'][0]['curves']
        if curve_ids is None:
            knots = [knots_of(c) for c in curves]
            err = max(int(abs(expand(k) - c).max()) for k, c in zip(knots, curves))
        else:
            for cid, curve in zip(curve_ids, curves):
                img.write(img.word(CURVE_LIB + 4 * cid), struct.pack('<256H', *curve))
            err = 0
        P = post_of(fit)
        if P is not None:
            post[rec] = P
        out[name] = dict(record=hex(rec), matrix_at=hex(mat), q13=q.tolist(), selector=sel, curves=curve_ids,
                         knot_err=err, post=P)
    # ctx fill: 0x536DD450 ldrne r3,[r6,#0x2d0] -> ldr (the cave fill needs SI for every tone)
    assert img.word(0x536DD450) == 0x159632D0
    img.write(0x536DD450, struct.pack('<I', 0xE59632D0))
    out['cave'] = patch_cave(img, [(m[1], m[4]) for m in MODES], knots, post)
    patch_mode_fixes(img)
    return out


if __name__ == '__main__':
    raw_nr_above = None
    if '--raw-nr-above' in sys.argv:
        i = sys.argv.index('--raw-nr-above')
        raw_nr_above = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    labels = 'v10'
    if '--labels' in sys.argv:
        i = sys.argv.index('--labels')
        labels = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    fits = [json.load(open(p)) for p in sys.argv[1:6]]
    img = Image(sys.argv[6])
    info = patch(img, fits)
    if raw_nr_above:
        from raw_nr import patch_raw_nr_min_iso, above_index
        info['raw_nr_above'] = patch_raw_nr_min_iso(img, first=above_index(raw_nr_above))
    from make_icons import patch_icons, preview, LABELS_V10, LABELS_V12
    from make_names import patch_names, NAMES_V10, NAMES_V12
    info['icons'] = patch_icons(img, dict(v10=LABELS_V10, v12=LABELS_V12)[labels])
    info['names'] = patch_names(img, dict(v10=NAMES_V10, v12=NAMES_V12)[labels])
    if len(sys.argv) > 8:
        preview(img, sys.argv[8], modes=('cross', 'vivid', 'retro', 'hdr', 'bleach'))
    data, rep = img.build()
    open(sys.argv[7], 'wb').write(data)
    for k, v in info.items():
        print(k, v)
    print(rep)
