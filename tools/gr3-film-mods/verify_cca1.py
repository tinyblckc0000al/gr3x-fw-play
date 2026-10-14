"""Check a films build with --cca1 against v7-equivalent stock behaviour (FINDINGS §22g).

Emulates ImageTuningStill::Make in one session over a tone sequence (still and live view) for the plain build and the
CCA1 build: the R2Y blocks must be identical except info+0x1240..0x1251, which must hold the film's matrix (12-bit two's
complement, as the writer stores it) for the four film tones and identity for every other tone; CCA1 ctl stays 0.

Usage: verify_cca1.py plain.bin cca1.bin mats.json
"""
import sys, json, struct
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
from gr4_editor.codec.container import inspect_container
from gr4_editor.codec.frames import decode_payload, section_rows
import run_tuning

FILM = {12: 'ektar', 19: 'gold', 20: 'pro400h', 24: 'pro400h', 21: 'portra'}
SEQ = [12, 11, 21, 19, 20, 24, 13, 17, 21, 12, 11, 25, 19]


def rtos_of(p):
    c = open(p, 'rb').read(); info = inspect_container(c)
    o, _ = decode_payload(c[128:info['payload_end']], info['decoded_size'])
    r = {x['name']: x for x in section_rows(o)}['RTOS']
    return o[r['start'] + 16:r['end']]


if __name__ == '__main__':
    plain, cca, mats = rtos_of(sys.argv[1]), rtos_of(sys.argv[2]), json.load(open(sys.argv[3]))
    by = {k.split('/')[-1].split('_')[0]: v['q512'] for k, v in mats.items()}
    ok = True
    for stage in (1, 0):
        ea = run_tuning.setup(stage, rtos=plain); eb = run_tuning.setup(stage, rtos=cca)
        for tone in SEQ:
            a = run_tuning.make(*ea, tone, stage=stage); b = run_tuning.make(*eb, tone, stage=stage)
            got = [[v & 0xFFF for v in struct.unpack('<3H', b[0x1240 + 6 * r:0x1246 + 6 * r])] for r in range(3)]
            want = [[v & 0xFFF for v in row] for row in (by[FILM[tone]] if tone in FILM else
                                                          [[512, 0, 0], [0, 512, 0], [0, 0, 512]])]
            other = [k for k in range(0, 0x9000, 2) if a[k:k + 2] != b[k:k + 2] and not 0x1240 <= k < 0x1252]
            good = got == want and not other and b[0x1220] & 3 == 0
            ok &= good
            print('still' if stage else 'LV   ', tone, FILM.get(tone, '-'), 'OK' if good else f'FAIL got {got} other {other[:4]}')
    print('ALL OK' if ok else 'FAIL')
