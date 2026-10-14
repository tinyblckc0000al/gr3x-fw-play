"""Fit a 3D LUT (.cube) to what the GR III R2Y stage can express in the Cross Process path:

    code_c = CurveC_c( BaseGamma( K * (M @ L)_c ) ) / 16384        c in R,G,B

L = scene-linear sRGB-primaries RGB after the camera matrix (mid gray 0.18), M = look matrix
(record f1, rows sum to 1), BaseGamma = Standard 256-entry gamma table (linear index domain,
dumped by emulation to work/base_gamma_std.npy), CurveC = 256-entry u16 Cross Process curve
(composite is curve(gamma), firmware 0x536E8668), K = index units per linear unit.

K is an ASSUMPTION: Standard puts 18% gray at ~sRGB 0.46, i.e. base-gamma index ~7.8.
Confirm/refine with a RAW+JPG pair before trusting absolute exposure.

Usage: cube_fit.py [--curves-from fit.json] [--boost W [--neutral N]] out.json in_cs cube[:ev] [cube[:ev] ...]
  in_cs: cube input encoding: 'vlog' (V-Gamut/V-Log, as spektrafilm bakes it) or 'srgb' (sRGB-encoded linear image,
         as the abpy/FujifilmCameraProfiles cubes)
  ev:    exposure offset applied to scene-linear before the cube (e.g. +1 = overexposed film)
All cubes share one matrix M; each gets its own 3 curves.
--curves-from: keep the first preset's curves of another fit and solve only M (for a mode that has
to share its curve set with another mode).
--boost W: add the yellow/orange/foliage sample set (warm_samples) with total weight W x the chart's,
so the fit trades some overall accuracy for those hues (films v3), plus near-neutral samples
weighted --neutral N (default 1) x that, so neutrals don't pick up a tint.
"""
import sys, json, os
import numpy as np
import colour
from scipy.optimize import least_squares

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = np.load(os.path.join(HERE, 'work/base_gamma_std.npy')).astype(float)
STD_LOOK = np.array([8116, 743, -667, 15, 8598, -421, -244, 542, 7894]).reshape(3, 3) / 8192
MID_INDEX = 7.8
K = MID_INDEX / 0.18
SRGB = colour.RGB_COLOURSPACES['sRGB']


def base_gamma(lin):
    return np.interp(np.clip(K * lin, 0, 255), np.arange(256), BASE)


def apply_curve(curve, g):
    return np.interp(np.clip(g / 64.0, 0, 255), np.arange(256), curve)


def warm_samples(n=1500, seed=2):
    """Saturated yellows/oranges/yellow-greens (HSV hue 15-90 deg, sat 0.35-1) over 5 stops: autumn foliage."""
    rng = np.random.default_rng(seed)
    h = rng.uniform(15, 90, n) / 360; s = rng.uniform(0.35, 1.0, n); v = np.ones(n)
    rgb = colour.HSV_to_RGB(np.stack([h, s, v], 1))
    lin = SRGB.cctf_decoding(rgb)
    lin = lin / lin.max(1, keepdims=True) * 0.18 * 2.0 ** rng.uniform(-2.5, 2.0, (n, 1)) * 1.5
    return lin


def near_neutral_samples(n=1500, seed=3):
    """Off-whites/greys (chroma up to ~8% channel spread) over 9 stops, so the warm boost can't tint neutrals."""
    rng = np.random.default_rng(seed)
    lin = 1 + rng.uniform(-0.08, 0.08, (n, 3))
    return lin * 0.18 * 2.0 ** rng.uniform(-5, 3, (n, 1))


def samples(seed=1, boost=0.0):
    rng = np.random.default_rng(seed)
    gray = 0.18 * 2.0 ** np.linspace(-7, 4.5, 600)
    gray = np.repeat(gray[:, None], 3, 1)
    cc = colour.CCS_COLOURCHECKERS['ColorChecker24 - After November 2014']
    xyz = colour.xyY_to_XYZ(np.array(list(cc.data.values())))
    xyz = colour.chromatic_adaptation(xyz, colour.xy_to_XYZ(cc.illuminant), colour.xy_to_XYZ(SRGB.whitepoint))
    chart = np.clip(colour.XYZ_to_RGB(xyz, SRGB, apply_cctf_encoding=False), 0, None)
    charts = np.concatenate([chart * 2.0 ** ev for ev in (-2, -1, 0, 1, 2)])
    cw = np.tile(np.where(np.arange(24) < 2, 60.0, 20.0), 5)    # skin patches weighted 3x
    rnd = rng.random((6000, 3)) ** 2.2 * 2.0 ** rng.uniform(-4, 2, (6000, 1)) * 0.6
    L = np.concatenate([gray, charts, rnd])
    w = np.concatenate([np.full(len(gray), 150.0), cw, np.ones(len(rnd))])
    if boost:
        warm, neu = warm_samples(), near_neutral_samples()
        L = np.concatenate([L, warm, neu])
        w = np.concatenate([w, np.full(len(warm), boost * cw.sum() / len(warm)),
                            np.full(len(neu), NEUTRAL * boost * cw.sum() / len(neu))])
    return L, w, chart


def load_target(path, in_cs, ev):
    lut = colour.read_LUT(path)
    if in_cs not in ('vlog', 'srgb'):
        raise SystemExit('input encoding must be vlog or srgb')
    vg = colour.RGB_COLOURSPACES['V-Gamut']

    def T(L):
        if in_cs == 'vlog':
            x = colour.RGB_to_RGB(L * 2.0 ** ev, SRGB, vg)
            x = colour.models.log_encoding_VLog(np.clip(x, 0, None))
        else:      # sRGB primaries + sRGB OETF of the linear image, clipped at 1 (abpy FujifilmCameraProfiles cubes)
            x = SRGB.cctf_encoding(np.clip(L * 2.0 ** ev, 0, 1))
        return np.clip(lut.apply(x, interpolator=colour.algebra.table_interpolation_tetrahedral), 0, 1)
    return T


def target_of(preset):
    """Target of a fit preset (older fits have no in_cs/ev: vlog, 0)."""
    return load_target(preset['spec'], preset.get('in_cs', 'vlog'), preset.get('ev', 0.0))


def fit_curve(g, t, w, lam=3000.0):
    """Weighted LS for a 256-knot piecewise-linear curve over g/64, 2nd-difference smoothing."""
    x = np.clip(g / 64.0, 0, 255)
    i0 = np.minimum(x.astype(int), 254); f = x - i0
    A = np.zeros((256, 256)); b = np.zeros(256)
    for a_i, a_w in ((i0, 1 - f), (i0 + 1, f)):
        for b_i, b_w in ((i0, 1 - f), (i0 + 1, f)):
            np.add.at(A, (a_i, b_i), w * a_w * b_w)
        np.add.at(b, a_i, w * a_w * t * 16384)
    D = np.diff(np.eye(256), 2, axis=0)
    c = np.linalg.solve(A + lam * D.T @ D + 1e-6 * np.eye(256), b)
    c = np.maximum.accumulate(np.clip(c, 0, 16383))
    return np.round(c).astype(int)


def model(M, curves, L):
    lin = L @ M.T
    return np.stack([apply_curve(curves[c], base_gamma(lin[:, c])) for c in range(3)], 1) / 16384


def M_from(p):
    off = p.reshape(3, 2)
    M = np.zeros((3, 3))
    for r in range(3):
        o = [j for j in range(3) if j != r]
        M[r, o] = off[r]; M[r, r] = 1 - off[r].sum()
    return M


BOOST = 0.0
NEUTRAL = 1.0      # near-neutral weight relative to the warm boost


def fit(targets, iters=8):
    L, w, chart = samples(boost=BOOST)
    Ts = [T(L) for T in targets]
    p = np.zeros(6)
    for it in range(iters):
        M = M_from(p)
        lin = L @ M.T
        curves = [[fit_curve(base_gamma(lin[:, c]), Tt[:, c], w) for c in range(3)] for Tt in Ts]

        def res(p):
            Mp = M_from(p)
            return np.concatenate([(np.sqrt(w)[:, None] * (model(Mp, cv, L) - Tt)).ravel() for cv, Tt in zip(curves, Ts)])
        p = least_squares(res, p, x_scale=0.1).x
        rms = np.sqrt(np.mean(res(p) ** 2))
        print(f'iter {it}: weighted rms {rms*255:.2f} /255  M diag {np.round(np.diag(M_from(p)),3)}')
    M = M_from(p)
    lin = L @ M.T
    curves = [[fit_curve(base_gamma(lin[:, c]), Tt[:, c], w) for c in range(3)] for Tt in Ts]
    return M, curves, chart


def fit_matrix(targets, curves):
    L, w, chart = samples(boost=BOOST)
    Ts = [T(L) for T in targets]
    def res(p):
        return np.concatenate([(np.sqrt(w)[:, None] * (model(M_from(p), curves, L) - Tt)).ravel() for Tt in Ts])
    p = least_squares(res, np.zeros(6), x_scale=0.1).x
    print(f'matrix-only fit: weighted rms {np.sqrt(np.mean(res(p) ** 2))*255:.2f} /255')
    return M_from(p), [curves] * len(Ts), chart


def de2000(a, b):
    lab = lambda x: colour.XYZ_to_Lab(colour.sRGB_to_XYZ(np.clip(x, 0, 1)))
    return colour.delta_E(lab(a), lab(b), method='CIE 2000')


if __name__ == '__main__':
    args = sys.argv[1:]
    shared = None
    if args[0] == '--curves-from':
        shared = [np.array(c) for c in json.load(open(args[1]))['presets'][0]['curves']]
        args = args[2:]
    if args[0] == '--boost':
        BOOST = float(args[1])
        args = args[2:]
    if args[0] == '--neutral':
        NEUTRAL = float(args[1])
        args = args[2:]
    out, in_cs, specs = args[0], args[1], args[2:]
    targets = []
    for s in specs:
        path, _, ev = s.partition(':')
        targets.append(load_target(path, in_cs, float(ev or 0)))
    M, curves, chart = fit(targets) if shared is None else fit_matrix(targets, shared)
    std = np.stack([base_gamma((chart @ STD_LOOK.T)[:, c]) for c in range(3)], 1) / 16384
    report = []
    for spec, T, cv in zip(specs, targets, curves):
        tgt = T(chart)
        d_fit, d_std = de2000(model(M, cv, chart), tgt), de2000(std, tgt)
        print(f'{os.path.basename(spec)}: chart dE2000 fit mean {d_fit.mean():.2f} max {d_fit.max():.2f} | '
              f'Standard-vs-target mean {d_std.mean():.2f}')
        gray = tgt[[18, 19, 20, 21, 22, 23]]
        path, _, ev = spec.partition(':')
        report.append(dict(spec=path, in_cs=in_cs, ev=float(ev or 0), curves=[list(map(int, c)) for c in cv],
                           chart_de_mean=float(d_fit.mean()), chart_de_max=float(d_fit.max()),
                           std_de_mean=float(d_std.mean()), target_gray_row=np.round(gray * 255).tolist(),
                           fit_chart=np.round(model(M, cv, chart) * 255).tolist(), target_chart=np.round(tgt * 255).tolist(),
                           std_chart=np.round(std * 255).tolist()))
    print('M =', np.round(M, 4).tolist())
    json.dump(dict(matrix=M.tolist(), mid_index=MID_INDEX, presets=report), open(out, 'w'))
