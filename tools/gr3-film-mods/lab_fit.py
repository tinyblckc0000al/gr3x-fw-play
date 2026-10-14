"""Perceptual refit of a joint fit (films v11, FINDINGS §22m): same model as v10 (look matrix -> base gamma -> 3 curves
-> post-gamma 3x3 via the CSP), but the residual is the per-sample dE2000 instead of the RGB difference.

The RGB least squares of cube_fit/joint_fit leaves a systematic chroma deficit (model vs target dC mean -2.1..-2.5 on
the camera chart, |dC| ~4 vs |dL| ~1). Parameters: look matrix and post matrix (rows sum to 1, 6 each) and an additive
correction of each curve on 17 knots (linear between knots), started from the joint fit. Same samples and weights as
joint_fit (boost from the file name, neutral 3). The post matrix is rounded to x/512 and the knot step refitted.

Usage: lab_fit.py in_joint.json out.json [camera-chart.npy]   (prints dE2000 general / warm / chart before -> after)
"""
import sys, json
sys.path.insert(0, '.')
import numpy as np, colour
from scipy.optimize import least_squares
import cube_fit as cf
from cube_fit import samples, warm_samples, target_of, model, M_from, de2000
from joint_fit import q512

NK = 17


def lab(x):
    return colour.XYZ_to_Lab(colour.sRGB_to_XYZ(np.clip(x, 0, 1)))


def unpack(p, M0, P0, cv0):
    dM, dP, kn = p[:6], p[6:12], p[12:].reshape(3, NK)
    M = M_from(M0 + dM)
    P = M_from(P0 + dP)
    xs = np.linspace(0, 255, NK)
    cv = [np.clip(cv0[c] + np.interp(np.arange(256), xs, kn[c]), 0, 16383) for c in range(3)]
    cv = [np.maximum.accumulate(c) for c in cv]
    return M, P, cv


def offdiag(A):
    return np.array([A[r, j] for r in range(3) for j in range(3) if j != r])


def render(M, P, cv, X):
    return np.clip(model(M, cv, X) @ P.T, 0, 1)


def evaluate(M, P, cv, T, chart=None):
    warm = warm_samples(n=1200, seed=11); Lg, _, cc = samples(seed=7); g = Lg[600:]
    sets = [('general', g), ('warm', warm), ('colorchecker', cc)] + ([('camera chart', chart)] if chart is not None else [])
    out = {}
    for nm, X in sets:
        t = T(X); u = t.min(1) > 0.02 if nm == 'camera chart' else np.ones(len(X), bool)
        out[nm] = round(float(de2000(render(M, P, cv, X)[u], t[u]).mean()), 2)
    return out


def lab_fit(f, boost, chart=None):
    cf.NEUTRAL = 3.0
    L, w, _ = samples(boost=boost)
    T = target_of(f['presets'][0])
    tl = lab(T(L))
    sw = np.sqrt(w / w.mean())
    dE = lambda M, P, cv: sw * colour.delta_E(lab(render(M, P, cv, L)), tl, method='CIE 2000')
    M0 = offdiag(np.array(f['matrix'])); P0 = offdiag(np.array(f['cca1_q512']) / 512)
    cv0 = [np.array(c, float) for c in f['presets'][0]['curves']]
    def res(p):
        return dE(*unpack(p, M0, P0, cv0))
    p0 = np.zeros(12 + 3 * NK)
    before = evaluate(*unpack(p0, M0, P0, cv0), T, chart)
    p = least_squares(res, p0, x_scale=np.r_[np.full(12, 0.02), np.full(3 * NK, 200.0)], max_nfev=60).x
    M, P, cv = unpack(p, M0, P0, cv0)
    Q = q512(P)
    # re-solve the curve correction for the rounded post matrix
    def res2(k):
        return dE(M, Q / 512, unpack(np.r_[p[:12], k], M0, P0, cv0)[2])
    k = least_squares(res2, p[12:], x_scale=200.0, max_nfev=20).x
    _, _, cv = unpack(np.r_[p[:12], k], M0, P0, cv0)
    cv = [np.round(c).astype(int) for c in cv]
    after = evaluate(M, Q / 512, cv, T, chart)
    g = json.loads(json.dumps(f))
    g['matrix'] = M.tolist()
    g['presets'][0]['curves'] = [c.tolist() for c in cv]
    g['post_q512'] = Q.tolist()
    g.pop('cca1_q512', None)
    g['lab_fit'] = dict(before=before, after=after)
    return g, before, after


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    chart = np.load(sys.argv[3]) if len(sys.argv) > 3 else None
    g, b, a = lab_fit(json.load(open(src)), 1 if '_b1' in src else 4, chart)
    json.dump(g, open(dst, 'w'))
    print(src.split('/')[-1], 'before', b, 'after', a, 'post', g['post_q512'])
