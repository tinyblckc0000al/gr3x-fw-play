"""Redraw the Image Control icons of the modes replaced by make_films.py (equal size, in place).

Icon catalog RAM 0x550020FC[id] -> descriptor {u16 w, u16 h, u32 word offset}; pixels are RGBA8
at ICONBIN data (section start + 16) + 4*offset. Tone->icon ids from 0x532935DC.
Each new icon reuses the film-strip frame of the Positive Film icon (0xE8: 36x38 opaque box,
sprocket rows 5-7 and 32-34) with a coloured label in the middle band.

Usage (library): patch_icons(img, labels) ; preview: make_icons.py out.png
"""
import struct
import numpy as np
from PIL import Image as PImage, ImageDraw, ImageFont
from gr4_editor.codec.frames import section_rows

CATALOG = 0x550020FC
ICON_ID = dict(vivid=0x224, retro=0x164, hdr=0x15F, cross=0x32, bleach=0x15A)
FRAME_ID = 0xE8
FONT = '/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf'
BG = (53, 53, 54)
LABELS = dict(                        # mode -> (text, colour)
    cross=('P400', (255, 214, 64)),   # Kodak Portra 400
    vivid=('E100', (255, 120, 80)),   # Kodak Ektar 100
    retro=('G200', (255, 170, 30)),   # Kodak Gold 200
    hdr=('400H', (120, 220, 140)),    # Fujifilm Pro 400H
)
LABELS_V10 = dict(LABELS, bleach=('250D', (90, 190, 255)))   # Kodak Vision3 250D on 2383 print (films v10)
LABELS_V12 = dict(LABELS, bleach=('NC', (110, 205, 200)))    # Fujifilm Classic Neg (films v12)


def iconbin(img):
    row = {r['name']: r for r in section_rows(img.original)}['ICONBIN']
    return row['start'] + 16


def descriptor(img, icon_id):
    return struct.unpack('<HHI', img.read(img.word(CATALOG + 4 * icon_id), 8))


def get_icon(img, icon_id):
    w, h, off = descriptor(img, icon_id)
    o = iconbin(img) + 4 * off
    return np.frombuffer(bytes(img.target[o:o + w * h * 4]), 'u1').reshape(h, w, 4).copy()


def put_icon(img, icon_id, rgba):
    w, h, off = descriptor(img, icon_id)
    assert rgba.shape == (h, w, 4) and rgba.dtype == np.uint8
    o = iconbin(img) + 4 * off
    img.target[o:o + w * h * 4] = rgba.tobytes()


def render(frame, text, colour, band=(9, 31)):
    """frame: 40x40 RGBA film-strip icon. Clears the middle band and draws text centred in it."""
    out = frame.copy()
    out[band[0]:band[1], 2:38, :3] = BG
    S = 8                                                 # supersample for anti-aliasing
    h_px = band[1] - band[0] - 4                          # cap height ~ band minus margin
    font = ImageFont.truetype(FONT, int(h_px * S * 1.32))
    big = PImage.new('L', (40 * S, 40 * S), 0)
    d = ImageDraw.Draw(big)
    l, t, r, b = d.textbbox((0, 0), text, font=font)
    max_w = 34 * S
    if r - l > max_w:                                     # squeeze horizontally if too wide
        tmp = PImage.new('L', (r - l + 4, b - t + 4), 0)
        ImageDraw.Draw(tmp).text((-l + 2, -t + 2), text, font=font, fill=255)
        tmp = tmp.resize((max_w, tmp.height), PImage.LANCZOS)
        big.paste(tmp, ((40 * S - max_w) // 2, ((band[0] + band[1]) * S - tmp.height) // 2))
    else:
        d.text(((40 * S - (r - l)) // 2 - l, ((band[0] + band[1]) * S - (b - t)) // 2 - t), text, font=font, fill=255)
    cov = np.asarray(big.resize((40, 40), PImage.LANCZOS)).astype(float)[..., None] / 255
    region = out[band[0]:band[1], 2:38, :3].astype(float)
    mixed = region * (1 - cov[band[0]:band[1], 2:38]) + np.array(colour) * cov[band[0]:band[1], 2:38]
    out[band[0]:band[1], 2:38, :3] = np.clip(np.round(mixed), 0, 255).astype('u1')
    return out


def patch_icons(img, labels=LABELS):
    frame = get_icon(img, FRAME_ID)
    assert frame.shape == (40, 40, 4)
    done = {}
    for mode, (text, colour) in labels.items():
        icon_id = ICON_ID[mode]
        assert descriptor(img, icon_id)[:2] == (40, 40)
        new = render(frame, text, colour)
        put_icon(img, icon_id, new)
        done[mode] = (hex(icon_id), text)
    return done


def preview(img, path, scale=6, modes=('cross', 'vivid', 'retro', 'hdr')):
    tiles = []
    for mode in modes:
        a = get_icon(img, ICON_ID[mode]).astype(float)
        al = a[..., 3:] / 255
        tiles.append((a[..., :3] * al + 128 * (1 - al)).astype('u1'))
    im = np.concatenate(tiles, 1)
    PImage.fromarray(im).resize((im.shape[1] * scale, im.shape[0] * scale), PImage.NEAREST).save(path)


if __name__ == '__main__':
    import sys
    from gr3patch import Image
    img = Image(sys.argv[2] if len(sys.argv) > 2 else '../fwdc239b.bin')
    patch_icons(img)
    preview(img, sys.argv[1])
