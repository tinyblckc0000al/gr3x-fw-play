#!/usr/bin/env python3
"""Normalise a LUTSmith-bridged fit.json so the film-mods pipeline and its
verifier see exactly the same schema as the native v16 fits.

Only change: if the fit has no post-matrix, write an explicit identity
post_q512. In make_slots15.py an absent post matrix and the identity matrix are
the same thing (`if P is not None and P != identity: posts[rec] = P`), so this
is a no-op for the built bytes; it only makes the key explicit (the upstream
verifier, verify_slots16.py, reads post_q512 unconditionally).

Usage: normalize_bridged_fit.py FIT.json
"""
import json, sys

IDENTITY = [[512, 0, 0], [0, 512, 0], [0, 0, 512]]

p = sys.argv[1]
fit = json.load(open(p))
if fit.get('post_q512') is None and fit.get('cca1_q512') is None:
    fit['post_q512'] = IDENTITY
    fit['_normalisation'] = 'added explicit identity post_q512 (absent == identity in make_slots15)'
    json.dump(fit, open(p, 'w'), indent=2)
    print('normalised', p)
else:
    print('post matrix already present in', p)