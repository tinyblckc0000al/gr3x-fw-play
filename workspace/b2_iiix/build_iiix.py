#!/usr/bin/env python3
"""Local GR IIIx 1.60 eight-preset storage-repair test candidate.

All new curve, text, mapping, helper code and MA allocations use a 24 KiB
appended RTOS area. Stock compensation tables, random code and MA zero table
are preserved. This builder does not flash, push, tag or publish.

Usage: build_iiix.py --stock iiix OUT.bin [name=fit.json ...]
"""
import argparse, datetime, hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FM = os.path.join(ROOT, 'tools/gr3-film-mods')
sys.path.insert(0, HERE)
sys.path.insert(0, FM)

DEFAULT8 = [
    ('portra',     'Portra 400',     'work/films_v16/fits/portra.json'),
    ('ektar',      'Ektar 100',      'work/films_v16/fits/ektar.json'),
    ('gold',       'Gold 200',       'work/films_v16/fits/gold.json'),
    ('pro400h',    'Pro 400H',       'work/films_v16/fits/pro400h.json'),
    ('vision3',    'Vision3 250D',   'work/films_v16/fits/vision3.json'),
    ('classicneg', 'Classic Neg',    'work/films_v16/fits/classicneg.json'),
    ('vision3500t','Vision3 500T',   'work/films_v16/fits/vision3500t.json'),
    ('velvia',     'Velvia',         'workspace/b2_iiix/fits/velvia.json'),
]
STOCK = {
    'iiix': os.path.join(ROOT, 'firmware/official-v160/fwdc243b.bin'),
    'iii':  os.path.join(ROOT, 'firmware/official-gr3-v210/fwdc239b.bin'),
}

# Historical regions overlap live 64x8x7 compensation tables. Never allocate there.
UNSAFE_LEGACY_SPANS = [(0x53D453F8, 0x53D45CB0), (0x53D39C8C, 0x53D3A588)]
RTOS_GROWTH = 0x6000



def refs_into_stock(stock_path, spans):
    """[(evidence)] word pointers or movw/movt address loads in the stock image's CODE/DATA region (payload up to
    the end of RTOS at 0x10c5e30; the sections after it are image pixels whose random 32-bit values would be
    indistinguishable from pointers) whose value lands in `spans`. The preserve-Cross build requires this to be
    empty (the same 'no pointers into it' bar the MA patch used for ZERO_SRC)."""
    import numpy as np
    import codec_path  # noqa: F401  (toolchain path setup)
    from gr4_editor.codec.container import inspect_container
    from gr4_editor.codec.frames import decode_payload
    d = open(stock_path, 'rb').read(); i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    rt0, rt_end = 0x10870, 0x10c5e30            # RTOS section within the decoded payload (Image.rtos0/rtos_end)
    code = dec[rt0:rt_end]                       # audit scope = RTOS code/data (pixels after it excluded)
    w = np.frombuffer(code, '<u4')
    spans = [(int(s[0]), int(s[1])) for s in spans]
    # word pointers whose VALUE lands in one of the spans (vectorized membership)
    m = np.zeros(len(w), dtype=bool)
    for lo, hi in spans:
        m |= (w >= lo) & (w < hi)
    hits = [f'word at payload+{hex(rt0 + 4 * int(x))}' for x in np.flatnonzero(m)]
    # ARM MOVW/MOVT imm16 = (imm4 << 12) | imm12 with imm4 = bits[19:16], imm12 = bits[11:0].
    # The old B2.1 decode spread nibbles (bits 15:8 treated as part of the immediate), which dropped imm12's
    # middle bits and silently failed to flag the 0x53D36ABC window --> false "0 references" clearance.
    imm16 = lambda v: ((v >> 16) & 0xF) << 12 | (v & 0xFFF)  # noqa: E731
    movw = (w & 0x0FF00000) == 0x03000000
    movt = (w & 0x0FF00000) == 0x03400000
    wi = np.flatnonzero(movw)
    ti = np.flatnonzero(movt)
    wlo, wrd = imm16(w[wi]), (w[wi] >> 12) & 0xF
    tlo, trd = imm16(w[ti]), (w[ti] >> 12) & 0xF
    for k in range(len(ti)):
        j0 = int(np.searchsorted(wi, ti[k] - 8)); j1 = int(np.searchsorted(wi, ti[k]))
        for j in range(j0, j1):
            if wrd[j] == trd[k]:
                a = (tlo[k] << 16) | wlo[j]
                for lo, hi in spans:
                    if lo <= a < hi:
                        hits.append(f'movw/movt {hex(a)} at payload+{hex(rt0 + 4 * int(ti[k]))}')
                        break
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stock', choices=('iiix', 'iii'), default='iiix')
    ap.add_argument('--presets', default=os.path.join(HERE, 'presets.json'),
                    help='config-driven film list (phase 2): JSON mapping internal tone -> fit filename under '
                         'fits/. Default: workspace/b2_iiix/presets.json. Ignored when positional films or '
                         '--default8 are given.')
    ap.add_argument('--default8', action='store_true', help='use the built-in 8-film list instead of presets.json')
    ap.add_argument('--raw-nr-above', type=int, default=None)
    ap.add_argument('--legacy-b', action='store_true',
                    help='explicit legacy/regression option reproducing the old B2.0 build (film data inside the 12 '
                         'library curve areas; fill stub does not reproduce the stock Cross Process branch). '
                         'NOT the deliverable.')
    ap.add_argument('--protect-cross', action='store_true',
                    help='now the default behavior (preserve factory Image Controls including Cross Process); '
                         'kept as an explicit no-op alias for compatibility.')
    ap.add_argument('out')
    ap.add_argument('films', nargs='*', help='name=path/to/fit.json (appended, in menu order)')
    ns = ap.parse_args()

    if ns.stock == 'iiix':
        import gr3patch_iiix as gp
    else:
        import gr3patch as gp
    sys.modules['gr3patch'] = gp
    import make_slots15 as M15
    import make_slots16 as M16

    if ns.stock != 'iiix' or ns.legacy_b:
        raise SystemExit('test candidate supports exact GR IIIx 1.60 with appended storage only')
    img = gp.Image(STOCK[ns.stock])
    start, end = img.append_rtos(RTOS_GROWTH)
    protect = [(start, start + 0x2000)]
    code_spans = [(start + 0x2000, start + 0x3000)]
    ma_spans = [(start + 0x3000, start + 0x4000)]

    # --- film list: positional name=fit.json > --default8 > presets.json (phase-2 default) --------------------
    preset_meta = None
    if ns.films:
        items = []
        for a in ns.films:
            key, path = a.split('=', 1)
            items.append((key, M15.FILMS.get(key, key), path))
        films = [(key, lbl, json.load(open(path)), None) for key, lbl, path in items]
        source = 'cli'
    elif ns.default8:
        items = [(k, lbl, os.path.join(FM if not p.startswith('workspace') else ROOT, p))
                 for k, lbl, p in DEFAULT8]
        films = [(key, lbl, json.load(open(path)), None) for key, lbl, path in items]
        source = 'default8'
    else:
        import presets_config
        films, preset_meta = presets_config.load(ns.presets, spans=protect)
        source = 'presets'
        print(f'films: {len(films)} from {preset_meta["presets_path"]}', file=sys.stderr)
        for t, p in preset_meta['presets'].items():
            print(f'  tone {t}: {p["file"]:22s} {p["name"]:14s} icon={p["icon_label"]:4s}'
                  f'{"  full_curve" if p["full_curve"] else ""}', file=sys.stderr)

    refs = []
    if protect:
        refs = refs_into_stock(STOCK[ns.stock], protect)
        assert not refs, '\n'.join(refs[:20])

    info = M15.patch(img, films, ns.raw_nr_above, protect, code_spans)
    info['_multiaxial'] = M16.patch_ma(img, films, ma_spans)
    info['_rawdev'] = M16.patch_rawdev(img, films, info)
    info['_exif_tone'] = M16.patch_exif_tone(img, films)
    info['_playback_detail'] = M16.patch_playback_detail(img, films)
    data, rep = img.build()
    open(ns.out, 'wb').write(data)

    sde = os.environ.get('SOURCE_DATE_EPOCH')
    when = datetime.datetime.fromtimestamp(int(sde), tz=datetime.timezone.utc).isoformat(timespec='seconds') \
        if sde else None
    info['_build'] = dict(stock=ns.stock, stock_sha256=hashlib.sha256(open(STOCK[ns.stock], 'rb').read()).hexdigest(),
                          out=os.path.abspath(ns.out), out_bytes=len(data),
                          out_sha256=hashlib.sha256(data).hexdigest(),
                          film_source=source, films=[f[0] for f in films])
    if preset_meta is not None:
        info['_build']['presets'] = preset_meta
    if when:
        info['_build']['when'] = when
    info['_build'].update(rep)
    info['_build']['test_candidate'] = True
    allocated = list(info['_code']['space']) + list(info['_multiaxial']['space'])
    seen = {int(address, 16) for _, address, _ in allocated}
    allocated += [(name, hex(address), size) for name, address, size in M15.FALLBACK[0].used
                  if address not in seen]
    info['_build']['allocations'] = [dict(name=name, start=int(address, 16),
                                         end=int(address, 16) + ((size + 3) & ~3))
                                      for name, address, size in allocated]
    info['_build']['storage'] = dict(append_start=hex(start), append_end=hex(end), growth=RTOS_GROWTH,
                                      data_spans=protect, code_spans=code_spans, ma_spans=ma_spans)
    if protect:
        info['_build'].update(preserve_cross_spans=[tuple(hex(a) for a in s) for s in protect],
                              refs_into_spans=len(refs_into_stock(STOCK[ns.stock], protect)))
    json.dump(info, open(ns.out + '.report.json', 'w'), indent=1, default=str)
    print(json.dumps(info, indent=1, default=str))
    print(rep)


if __name__ == '__main__':
    main()