"""Joint refit of a film fit: pre-curve look matrix (CCA0) + 3 curves + post-gamma 3x3 (FINDINGS §22i). The post matrix
('cca1_q512') was put into CCA1 in v8/v9, which actually acts before the curves; v10 applies it through the RGB->YCbCr
matrix instead (film_cave.py, §22l).

Starts from an existing cube_fit result and alternates: CCA1 (least squares on the model output), curves (fit to the
target pulled back through CCA1^-1), look matrix. Same samples/weights as cube_fit (--boost from the file name: b1 -> 1,
else 4; neutral 3). Both matrices keep rows summing to 1, so greys stay grey. CCA1 is rounded to x/512 and the final
curves are refitted against the rounded CCA1.

Usage: joint_fit.py in.json out.json   (writes the fit plus 'cca1_q512'; prints dE before/after)
"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from scipy.optimize import least_squares
import cube_fit as cf
from cube_fit import samples, warm_samples, target_of, model, M_from, de2000, fit_curve, base_gamma


def evaluate(M, cv, C, T):
    warm = warm_samples(n=1200, seed=11); Lg, _, chart = samples(seed=7); g = Lg[600:]
    out = {}
    for nm, X in (('warm', warm), ('general', g), ('chart', chart)):
        a = np.clip(model(M, cv, X) @ C.T, 0, 1); out[nm] = round(float(de2000(a, T(X)).mean()), 2)
    return out


def q512(C):
    Q = np.round(C * 512).astype(int)
    for r in range(3):
        Q[r, r] += 512 - Q[r].sum()
    return Q


def joint(f, boost, iters=6):
    cf.NEUTRAL = 3.0
    L, w, _ = samples(boost=boost)
    M = np.array(f['matrix']); cv = [np.array(c) for c in f['presets'][0]['curves']]
    T = target_of(f['presets'][0]); t = T(L)
    before = evaluate(M, cv, np.eye(3), T)
    qC, qM = np.zeros(6), None
    for _ in range(iters):
        res = lambda q: (np.sqrt(w)[:, None] * (np.clip(model(M, cv, L) @ M_from(q).T, 0, 1) - t)).ravel()
        qC = least_squares(res, qC, x_scale=0.05).x
        C = M_from(qC)
        tp = np.clip(t @ np.linalg.inv(C).T, 0, 1)
        lin = L @ M.T
        cv = [fit_curve(base_gamma(lin[:, c]), tp[:, c], w) for c in range(3)]
        res2 = lambda q: (np.sqrt(w)[:, None] * (np.clip(model(M_from(q), cv, L) @ C.T, 0, 1) - t)).ravel()
        qM = least_squares(res2, np.zeros(6) if qM is None else qM, x_scale=0.1).x
        M = M_from(qM)
    Q = q512(M_from(qC)); C = Q / 512
    tp = np.clip(t @ np.linalg.inv(C).T, 0, 1)
    lin = L @ M.T
    cv = [fit_curve(base_gamma(lin[:, c]), tp[:, c], w) for c in range(3)]
    after = evaluate(M, cv, C, T)
    g = json.loads(json.dumps(f))
    g['matrix'] = M.tolist()
    g['presets'][0]['curves'] = [c.tolist() for c in cv]
    g['cca1_q512'] = Q.tolist()
    g['joint_fit'] = dict(before=before, after=after)
    return g, before, after


if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    g, b, a = joint(json.load(open(src)), 1 if '_b1' in src else 4)
    json.dump(g, open(dst, 'w'))
    print(src.split('/')[-1], 'before', b, 'after', a, 'cca1', g['cca1_q512'])
