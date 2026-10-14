"""Compare film fits on warm hues (yellow/orange/foliage) vs. everything else.
For each fit.json: dE2000 and signed Lab hue error (model - target, deg; negative = model too yellow/green
when target is orange-ward) on a held-out warm set, plus dE2000 on the chart (5 exposures) and random colours.
Usage: eval_warm.py fit.json [fit.json ...]   (cube taken from the fit's first preset spec)"""
import sys, json
import numpy as np, colour
from cube_fit import load_target, model, warm_samples, samples, de2000

def lab(x): return colour.XYZ_to_Lab(colour.sRGB_to_XYZ(np.clip(x, 0, 1)))

warm = warm_samples(n=1200, seed=11)
Lg, _, chart = samples(seed=7)
general = Lg[600:]                                   # charts + random, without the gray ramp
for p in sys.argv[1:]:
    f = json.load(open(p)); M = np.array(f['matrix']); cv = [np.array(c) for c in f['presets'][0]['curves']]
    spec = f['presets'][0]['spec']; path, _, ev = spec.partition(':')
    T = load_target(path, 'vlog', float(ev or 0))
    mw, tw = model(M, cv, warm), T(warm)
    a, b = lab(mw), lab(tw)
    ha, hb = np.degrees(np.arctan2(a[:, 2], a[:, 1])), np.degrees(np.arctan2(b[:, 2], b[:, 1]))
    chroma = np.hypot(b[:, 1], b[:, 2]) > 15
    dh = ((ha - hb + 180) % 360 - 180)[chroma]
    dw = de2000(mw, tw); dg = de2000(model(M, cv, general), T(general)); dc = de2000(model(M, cv, chart), T(chart))
    print(f'{p}: warm dE {dw.mean():.2f} (p90 {np.percentile(dw, 90):.1f}), warm hue err mean {dh.mean():+.1f} deg |{np.abs(dh).mean():.1f}| ; '
          f'chart dE {dc.mean():.2f}, general dE {dg.mean():.2f}')
