"""Turn the Cross Process mode into a fitted film look (output of cube_fit.py).

Patches (data only, no code):
  * gives Cross Process (slot 21) its own look record: the unreachable legacy record of slot 2
    is overwritten with a copy of the shared Std/HDR/Cross record 0x5501900C, its look-matrix
    pointer kept on slot 2's own matrix 0x53DC2A54 (single-referenced), and table[21] repointed.
    Standard and HDR keep 0x5501900C untouched.
  * writes the fitted matrix there (s16 Q13, rows forced to sum to 8192).
  * replaces the 9 Cross Process curves: preset k (SI+0x797) uses library curves 3+3k..5+3k (R,G,B).

Usage: make_film.py fit.json fwdc239b.bin out.bin
"""
import sys, json, struct
import numpy as np
from gr3patch import Image, RECORDS

SHARED_REC, DONOR_SLOT, CROSS_SLOT, REC_LEN = 0x5501900C, 2, 21, 0x54
CURVE_LIB = 0x55037604


def q13_matrix(m):
    q = np.round(np.array(m) * 8192).astype(int)
    q[np.arange(3), np.arange(3)] += 8192 - q.sum(1)
    return q


def patch(img, fit):
    donor = img.word(RECORDS + 4 * DONOR_SLOT)
    donor_mat = img.word(donor + 4)
    rec = bytearray(img.read(SHARED_REC, REC_LEN))
    rec[4:8] = struct.pack('<I', donor_mat)
    img.write(donor, bytes(rec))
    img.write(RECORDS + 4 * CROSS_SLOT, struct.pack('<I', donor))
    q = q13_matrix(fit['matrix'])
    img.write(donor_mat, struct.pack('<9h', *q.ravel().tolist()))
    for k, preset in enumerate(fit['presets'][:3]):
        for c, curve in enumerate(preset['curves']):
            ptr = img.word(CURVE_LIB + 4 * (3 + 3 * k + c))
            img.write(ptr, struct.pack('<256H', *curve))
    return donor, donor_mat, q


if __name__ == '__main__':
    fit = json.load(open(sys.argv[1]))
    img = Image(sys.argv[2])
    donor, mat, q = patch(img, fit)
    out, rep = img.build()
    open(sys.argv[3], 'wb').write(out)
    print(f'cross record -> {donor:#x}, matrix @ {mat:#x} = {q.tolist()}')
    print(rep)
