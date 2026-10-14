"""Is there noise reduction in a DNG? Measures the noise of flat areas per Bayer plane (FINDINGS §21).

Untouched sensor noise is white: neighbouring same-colour pixels are uncorrelated (lag-1 correlation ~0) and the
variance grows linearly with the signal (shot noise, var/mean ~ constant at one ISO). Bayer NR smooths it: positive
lag-1 correlation and lower var/mean. Each plane is cut into 16x16 blocks, a quadratic is subtracted to remove the
scene, and the 40% quietest blocks per brightness bin are kept (= flat areas); in a dark frame all blocks are kept.
The printed lag is the excess over white noise (0 = no NR; a 3x3 box blur blended in at 10/25/50% gives about
+0.02/+0.07/+0.20). Scene texture left in the blocks also adds a little, so compare shots of the same scene.

Usage: raw_noise.py file.DNG [...]
"""
import sys
import numpy as np
import rawpy

BS = 16
BIAS = -0.023      # lag-1 of pure white noise after the quadratic detrend (simulated); reported lag is minus this


def plane_stats(p):
    h, w = p.shape[0] // BS * BS, p.shape[1] // BS * BS
    blk = p[:h, :w].reshape(h // BS, BS, w // BS, BS).transpose(0, 2, 1, 3).reshape(-1, BS, BS)
    yy, xx = np.mgrid[0:BS, 0:BS]
    A = np.stack([np.ones(BS * BS), yy.ravel(), xx.ravel(), (yy * xx).ravel(), (yy ** 2).ravel(), (xx ** 2).ravel()], 1)
    coef, *_ = np.linalg.lstsq(A, blk.reshape(len(blk), -1).T, rcond=None)
    res = blk - (A @ coef).T.reshape(-1, BS, BS)
    var = res.var((1, 2))
    lag = ((res[:, :, 1:] * res[:, :, :-1]).mean((1, 2)) + (res[:, 1:, :] * res[:, :-1, :]).mean((1, 2))) / 2 / var
    return blk.mean((1, 2)), var * BS * BS / (BS * BS - 6), lag


def flat(mean, var):
    if np.median(mean) < 30:                      # dark frame (camera face down): every block is flat
        return np.abs(mean) < 30
    ok = (mean > 30) & (mean < 12000)
    edges = np.geomspace(30, 12000, 16)
    b = np.digitize(mean, edges)
    sel = np.zeros_like(ok)
    for k in np.unique(b[ok]):
        m = ok & (b == k)
        if m.sum() >= 20:
            sel |= m & (var <= np.percentile(var[m], 40))
    return sel


def analyze(path):
    r = rawpy.imread(path)
    raw = r.raw_image_visible.astype(np.float64)
    names = 'RGBG'
    rows = []
    for dy in (0, 1):
        for dx in (0, 1):
            c = r.raw_pattern[dy, dx]
            mean, var, lag = plane_stats(raw[dy::2, dx::2] - r.black_level_per_channel[c])
            s = flat(mean, var)
            rows.append((names[c], int(s.sum()), np.median(lag[s]) - BIAS if s.any() else np.nan,
                         np.median(var[s] / mean[s]) if s.any() else np.nan))
    return rows


if __name__ == '__main__':
    import subprocess
    for path in sys.argv[1:]:
        try:
            iso = subprocess.run(['exiftool', '-s3', '-ISO', path], capture_output=True, text=True).stdout.strip()
        except OSError:
            iso = '?'
        rows = analyze(path)
        lag = np.nanmean([x[2] for x in rows])
        print(f'{path}  ISO {iso:>6}  lag-1 corr {lag:+.3f}  ' +
              '  '.join(f'{n}: n={k} lag {l:+.3f} var/mean {v:.2f}' for n, k, l, v in rows))
