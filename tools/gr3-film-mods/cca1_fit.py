"""Fit a neutral-preserving 3x3 for CCA1 (after the film curves, display-encoded RGB) per film fit (FINDINGS §22g).

Same objective as work/films_v4/postgamma_ceiling.py: the fixed matrix+curves fit is kept, and q (6 off-diagonal
terms, rows sum to 1 so greys stay grey) minimises the weighted error to the film target on the cube_fit samples.

Usage: cca1_fit.py fit.json [...] [--out mats.json]
"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from scipy.optimize import least_squares
from cube_fit import samples, warm_samples, load_target, model, M_from, de2000


def fit_cca1(f):
    L, w, _ = samples(boost=4)
    M = np.array(f['matrix']); cv = [np.array(c) for c in f['presets'][0]['curves']]
    T = load_target(f['presets'][0]['spec'], 'vlog', 0)
    m = model(M, cv, L); t = T(L)
    res = lambda q: (np.sqrt(w)[:, None] * (np.clip(m @ M_from(q).T, 0, 1) - t)).ravel()
    q = least_squares(res, np.zeros(6), x_scale=0.05).x
    C = M_from(q)
    Q = np.round(C * 512).astype(int)
    for r in range(3):                       # keep each row summing to exactly 512 (greys stay grey after rounding)
        Q[r, r] += 512 - Q[r].sum()
    assert np.abs(Q).max() < 2048
    stats = {}
    warm = warm_samples(n=1200, seed=11); Lg, _, _ = samples(seed=7); g = Lg[600:]
    for nm, X in (('warm', warm), ('general', g)):
        a = model(M, cv, X); b = np.clip(a @ (Q / 512).T, 0, 1); tt = T(X)
        stats[nm] = (round(float(de2000(a, tt).mean()), 2), round(float(de2000(b, tt).mean()), 2))
    return Q, stats


if __name__ == '__main__':
    args = sys.argv[1:]
    out = None
    if '--out' in args:
        i = args.index('--out'); out = args[i + 1]; del args[i:i + 2]
    res = {}
    for p in args:
        Q, st = fit_cca1(json.load(open(p)))
        res[p] = dict(q512=Q.tolist(), stats=st)
        print(p.split('/')[-1], Q.tolist(), st)
    if out:
        json.dump(res, open(out, 'w'), indent=1)
