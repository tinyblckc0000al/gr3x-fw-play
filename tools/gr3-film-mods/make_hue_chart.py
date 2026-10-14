"""Hue chart for the MultiAxial probe: 36 hues x 6 saturation/brightness rows + gray row, with
white corner markers for alignment. Shown full screen on a monitor and photographed.
Usage: make_hue_chart.py out.png [width height]"""
import sys, colorsys
from PIL import Image, ImageDraw
W, H = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (3840, 2160)
ROWS = [(1.0, 1.0), (0.6, 1.0), (0.3, 1.0), (1.0, 0.55), (0.6, 0.55), (0.3, 0.55)]
im = Image.new('RGB', (W, H), (40, 40, 40)); d = ImageDraw.Draw(im)
m = int(H * 0.06); gx0, gy0, gx1, gy1 = m * 2, m * 2, W - m * 2, H - m * 2
cols, rows = 36, len(ROWS) + 1
cw, ch = (gx1 - gx0) / cols, (gy1 - gy0) / rows
pad = max(2, int(min(cw, ch) * 0.08))
for r, (s, v) in enumerate(ROWS):
    for c in range(cols):
        rgb = tuple(round(255 * x) for x in colorsys.hsv_to_rgb(c / cols, s, v))
        d.rectangle([gx0 + c * cw + pad, gy0 + r * ch + pad, gx0 + (c + 1) * cw - pad, gy0 + (r + 1) * ch - pad], fill=rgb)
for c in range(cols):                       # gray row: 36 levels
    g = round(255 * (c / (cols - 1)) ** 1.0)
    d.rectangle([gx0 + c * cw + pad, gy0 + len(ROWS) * ch + pad, gx0 + (c + 1) * cw - pad, gy0 + rows * ch - pad], fill=(g, g, g))
for x, y in ((m // 2, m // 2), (W - m * 3 // 2, m // 2), (m // 2, H - m * 3 // 2), (W - m * 3 // 2, H - m * 3 // 2)):
    d.rectangle([x, y, x + m, y + m], fill=(255, 255, 255))
im.save(sys.argv[1])
print(sys.argv[1], im.size, f'cell {cw:.0f}x{ch:.0f}px')
