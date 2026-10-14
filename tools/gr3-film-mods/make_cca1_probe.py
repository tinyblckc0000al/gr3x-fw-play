"""CCA1 probe firmware = films v7 + red/blue swap in the post-gamma 3x3 (CCA1). TEMPORARY, not for shooting.

Live RAM read-back (script-probe2, FINDINGS §22f): the still R2Y image has CCA1 at info+0x1220 with ctl 0 and an identity
matrix (0x200 on the diagonal, info+0x1240/48/50). The ColorMatrix init 0x536DED70 sets these coefficients once
(out+0x32..0x42, 3x3 row-major, 12 bit) and Make never changes them; writer 0x536DF13C copies them every shot.
This probe makes the init write rows (0,0,1)(0,1,0)(1,0,0) instead: if CCA1 is live, every mode (and probably live
view) shows red and blue swapped (or luma/chroma scrambled if CCA1 works in YCbCr).

Usage: make_cca1_probe.py fwdc239b.bin out.bin   (rebuilds v7 from the stock file, then patches)
"""
import sys, json, struct
from gr3patch import Image
import make_films
from raw_nr import patch_raw_nr_min_iso, above_index
from make_icons import patch_icons
from make_names import patch_names

FITS = ['work/films_v3/fits/ektar_b1n3.json', 'work/films_v3/fits/gold_b4n3.json',
        'work/films_v4/fits/pro400h_own_b4n3.json', 'work/films_v3/fits/portra_b4n3.json']


def strh_ip(rt, imm):
    return 0xE1C000B0 | (12 << 16) | (rt << 12) | ((imm >> 4) << 8) | (imm & 0xF)


SWAP = {                               # address: (old, new)  r2 = 0x200, r3 = 0
    0x536DEDA4: (strh_ip(2, 0x32), strh_ip(3, 0x32)),   # c00 = 0
    0x536DEDB0: (strh_ip(2, 0x42), strh_ip(3, 0x42)),   # c22 = 0
    0x536DEDB8: (strh_ip(3, 0x36), strh_ip(2, 0x36)),   # c02 = 1
    0x536DEDC4: (strh_ip(3, 0x3E), strh_ip(2, 0x3E)),   # c20 = 1
}


def patch_cca1_swap(img):
    for at, (old, new) in SWAP.items():
        assert img.word(at) == old, f'{at:#x}: {img.word(at):#010x} != {old:#010x}'
        img.write(at, struct.pack('<I', new))
    return [hex(a) for a in SWAP]


if __name__ == '__main__':
    img = Image(sys.argv[1])
    make_films.patch(img, [json.load(open(p)) for p in FITS])
    patch_raw_nr_min_iso(img, first=above_index(8000))
    patch_icons(img)
    patch_names(img)
    print('cca1 swap', patch_cca1_swap(img))
    data, rep = img.build()
    open(sys.argv[2], 'wb').write(data)
    print(rep)
