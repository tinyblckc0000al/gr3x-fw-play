#!/usr/bin/env python3
"""Phase-2 configurable preset build: presets.json -> a validated film list for the
make_slots15 / make_slots16 patch code.

presets.json maps the internal tone number (string, FIRST_TONE..FIRST_TONE+7) to a fit
filename resolved under the central fits/ dir:

    {"25": "portra400.json", ..., "32": "velvia50.json"}

The EXIF ImageTone code (268..275) is DERIVED from the tone at build time
(make_slots16 EXIF_CODE0 + k) and must never be hand-edited here.

Every fit file carries the per-preset display metadata in a "preset" block:

    "preset": {"name": "Portra 400", "icon_label": "P400",
               "icon_rgb": [255, 214, 64], "full_curve": false}

load() is fail-fast (SystemExit, non-zero exit) and checks, per the phase-2 spec:
  * capacity  - count vs the film icon-id / string-id budget and the film-data spans;
  * parameters- matrix 3x3, presets[0].curves 3x256, hue_q10 12x3x3 (rows sum 1024),
                post_q512/cca1_q512 3x3 (all numeric);
  * names/icons- name, icon_label (1..4 ASCII), icon_rgb (3 x 0..255) present and unique;
  * completeness- contiguous tone range (count is fixed by the frozen EXIF mapping).

CLI:  python workspace/b2_iiix/presets_config.py workspace/b2_iiix/presets.json
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))            # .../workspace/b2_iiix
_ROOT = os.path.dirname(os.path.dirname(_HERE))               # .../gr3x-hack
_FM = os.environ.get('GR3_FILM_MODS', os.path.join(_ROOT, 'tools', 'gr3-film-mods'))
if os.path.isdir(_FM) and _FM not in sys.path:
    sys.path.insert(0, _FM)

N_SLOTS = 8          # FIRST_TONE..FIRST_TONE+7, bound to EXIF codes 268..275


def _fail(msg):
    raise SystemExit(f'presets: {msg}')


def _m15():
    try:
        import make_slots15 as M15
    except Exception as e:                                    # pragma: no cover
        _fail(f'cannot import make_slots15 from {_FM}: {e}')
    return M15


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_matrix(m, where):
    if not (isinstance(m, list) and len(m) == 3 and all(isinstance(r, list) and len(r) == 3 for r in m)):
        _fail(f'{where}: matrix must be 3x3')
    if not all(_num(v) for r in m for v in r):
        _fail(f'{where}: matrix entries must be numbers')


def _check_curves(presets, where):
    if not (isinstance(presets, list) and presets and isinstance(presets[0], dict)):
        _fail(f'{where}: presets must be a non-empty list of objects')
    c = presets[0].get('curves')
    if not (isinstance(c, list) and len(c) == 3 and all(isinstance(ch, list) and len(ch) == 256 for ch in c)):
        _fail(f'{where}: presets[0].curves must be 3 x 256')
    if not all(_num(v) for ch in c for v in ch):
        _fail(f'{where}: curve entries must be numbers')


def _check_hue(q, where):
    if not (isinstance(q, list) and len(q) == 12 and all(
            isinstance(g, list) and len(g) == 3 and all(isinstance(r, list) and len(r) == 3 for r in g) for g in q)):
        _fail(f'{where}: hue_q10 must be 12 x 3 x 3')
    for g in q:
        for r in g:
            if not all(_num(v) for v in r) or not all(float(v).is_integer() for v in r):
                _fail(f'{where}: hue_q10 entries must be integers')
            if sum(r) != 1024:
                _fail(f'{where}: hue_q10 rows must sum to 1024 (got {sum(r)})')


def _check_post(p, where):
    if p is None:
        return
    if not (isinstance(p, list) and len(p) == 3 and all(isinstance(r, list) and len(r) == 3 for r in p)):
        _fail(f'{where}: post_q512 must be 3x3')
    if not all(_num(v) for r in p for v in r):
        _fail(f'{where}: post_q512 entries must be numbers')


def load(presets_path, fits_dir=None, *, first_tone=None, n_slots=N_SLOTS, spans=None, max_full_curve=None):
    """Return (films, meta).

    films: [(key, display_name, fit_dict, replaced_tone_or_None)] in tone order, ready for
    make_slots15.patch / make_slots16. meta: report/derivation summary.
    """
    M15 = _m15()
    if first_tone is None:
        first_tone = M15.FIRST_TONE
    if fits_dir is None:
        fits_dir = os.path.join(_HERE, 'fits')

    try:
        raw = json.load(open(presets_path))
    except FileNotFoundError:
        _fail(f'{presets_path}: not found')
    except json.JSONDecodeError as e:
        _fail(f'{presets_path}: invalid JSON: {e}')
    if not isinstance(raw, dict):
        _fail(f'{presets_path}: must be a JSON object of tone -> fit filename')

    tones = {}
    for k, v in raw.items():
        try:
            t = int(k)
        except (TypeError, ValueError):
            _fail(f'{presets_path}: key {k!r} is not an integer tone')
        if t in tones:
            _fail(f'{presets_path}: duplicate tone {t}')
        if not isinstance(v, str) or not v:
            _fail(f'{presets_path}: tone {t}: value must be a fit filename string')
        tones[t] = v
    want = list(range(first_tone, first_tone + n_slots))
    if sorted(tones) != want:
        _fail(f'{presets_path}: tones {sorted(tones)} != required {want} (count is fixed by the frozen '
              f'EXIF ImageTone mapping, see make_slots16 EXIF_CODE0)')

    entries = []
    seen = set()
    for t in want:
        fn = tones[t]
        if os.path.basename(fn) != fn or fn in ('', '.', '..'):
            _fail(f'tone {t}: {fn!r} must be a bare filename inside the fits dir')
        path = os.path.join(fits_dir, fn)
        if os.path.normpath(path) in seen:
            _fail(f'tone {t}: {fn} is used by another tone too')
        seen.add(os.path.normpath(path))
        if not os.path.isfile(path):
            _fail(f'tone {t}: fit {path} not found')
        try:
            fit = json.load(open(path))
        except json.JSONDecodeError as e:
            _fail(f'{path}: invalid JSON: {e}')
        if not isinstance(fit, dict):
            _fail(f'{path}: must be a JSON object')

        where = f'{fn} (tone {t})'
        _check_matrix(fit.get('matrix'), where)
        _check_curves(fit.get('presets'), where)
        _check_hue(fit.get('hue_q10'), where)
        _check_post(fit.get('post_q512', fit.get('cca1_q512')), where)

        p = fit.get('preset')
        if not isinstance(p, dict):
            _fail(f'{where}: missing "preset" metadata block (name / icon_label / icon_rgb / full_curve)')
        name = p.get('name')
        if not (isinstance(name, str) and name.strip()):
            _fail(f'{where}: preset.name must be a non-empty string')
        label = p.get('icon_label')
        if not (isinstance(label, str) and 1 <= len(label) <= 4 and all(32 <= ord(c) < 127 for c in label)):
            _fail(f'{where}: preset.icon_label must be 1..4 printable ASCII chars (got {label!r})')
        rgb = p.get('icon_rgb')
        if not (isinstance(rgb, list) and len(rgb) == 3
                and all(isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= 255 for v in rgb)):
            _fail(f'{where}: preset.icon_rgb must be 3 integers 0..255 (got {rgb!r})')
        full = p.get('full_curve', False)
        if not isinstance(full, bool):
            _fail(f'{where}: preset.full_curve must be a boolean')
        for rk in ('raw_nr', 'raw_nr_above'):
            if rk in fit and not (isinstance(fit[rk], int) and not isinstance(fit[rk], bool)):
                _fail(f'{where}: {rk} must be an integer')
        if 'raw_nr_above' in p and not (isinstance(p['raw_nr_above'], int) and not isinstance(p['raw_nr_above'], bool)):
            _fail(f'{where}: preset.raw_nr_above must be an integer')

        entries.append(dict(tone=t, key=os.path.splitext(fn)[0], name=name, path=path, file=fn, fit=fit,
                            icon_label=label, icon_rgb=list(rgb), full_curve=full))

    # ---- capacity pre-check (the patch allocator is the exact gate) --------------------------------------
    if len(entries) > len(M15.ICON_IDS):
        _fail(f'{len(entries)} presets > {len(M15.ICON_IDS)} film icon ids available')
    sid_budget = M15.SID_MAX - M15.SID0 + 1
    if len(entries) > sid_budget:
        _fail(f'{len(entries)} presets > string-id budget {sid_budget}')
    region_cap = max((hi - lo for lo, hi in spans), default=None) if spans else None
    limit_full = max_full_curve
    if limit_full is None and region_cap is not None:
        limit_full = region_cap // (3 * 512)
    if limit_full is None:
        limit_full = 1
    n_full = sum(1 for e in entries if e['full_curve'])
    if n_full > limit_full:
        _fail(f'{n_full} full-curve presets > {limit_full} (each needs 1536 B in the largest data span)')
    if spans:
        cap = sum(hi - lo for lo, hi in spans)
        need = sum((3 * 512) if e['full_curve'] else M15.KNOT_BYTES for e in entries)
        if need > cap:
            _fail(f'film knot/curve data {need} B > span capacity {cap} B')

    films = [(e['key'], e['name'], e['fit'], None) for e in entries]
    meta = dict(first_tone=first_tone, count=len(entries), fits_dir=fits_dir,
                presets_path=os.path.abspath(presets_path),
                presets={e['tone']: dict(file=e['file'], name=e['name'], icon_label=e['icon_label'],
                                         icon_rgb=e['icon_rgb'], full_curve=e['full_curve']) for e in entries})
    return films, meta


def main(argv):
    presets_path = argv[0] if argv else os.path.join(_HERE, 'presets.json')
    spans = None
    if '--spans' in argv:                                      # optional capacity check with the build's spans
        i = argv.index('--spans')
        spans = [(int(a, 16), int(b, 16)) for a, b in (s.split(':') for s in argv[i + 1].split(','))]
    films, meta = load(presets_path, spans=spans)
    print(f'{presets_path}: OK - {meta["count"]} presets, tones {meta["first_tone"]}..'
          f'{meta["first_tone"] + meta["count"] - 1}')
    for t, p in meta['presets'].items():
        print(f'  {t}: {p["file"]:22s} {p["name"]:14s} icon={p["icon_label"]:4s} rgb={p["icon_rgb"]}'
              f'{"  full_curve" if p["full_curve"] else ""}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
