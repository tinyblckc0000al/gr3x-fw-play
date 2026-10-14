#!/usr/bin/env python3
"""Disassemble B2.2 / stock RTOS regions and cross-references via a lightweight capstone helper."""
import sys, struct, numpy as np
from pathlib import Path

TOOL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TOOL_DIR.parents[1]
sys.path.insert(0, str(TOOL_DIR))
import codec_path  # noqa
from gr4_editor.codec.container import inspect_container
from gr4_editor.codec.frames import decode_payload
from capstone import Cs, CS_ARCH_ARM, CS_MODE_ARM

BASE = 0x53000000
RT0 = 0x10870
RT_END = 0x10c5e30
SRC, DST, LEN = 0x5407b540, 0x55000000, 0x3a080

cache = {}


def load(path):
    if path in cache:
        return cache[path]
    d = open(path, 'rb').read()
    i = inspect_container(d)
    dec, _ = decode_payload(d[128:i['payload_end']], i['decoded_size'])
    rt = bytes(dec[RT0:RT_END])
    cache[path] = rt
    return rt


def off(a):
    if DST <= a < DST + LEN:
        a = SRC + a - DST
    return a - BASE


def w(rt, a):
    return struct.unpack('<I', rt[off(a):off(a) + 4])[0]


def rd(rt, a, n):
    o = off(a)
    return rt[o:o + n]


def dis(rt, a, n=50, text=True):
    o = off(a)
    md = Cs(CS_ARCH_ARM, CS_MODE_ARM)
    out = []
    for ins in md.disasm(rt[o:o + 4 * n], a):
        out.append(f'{ins.address:#x}: {ins.mnemonic} {ins.op_str}')
    return '\n'.join(out) if text else out


def movw_movt_targets(rt):
    W = np.frombuffer(rt[:len(rt) // 4 * 4], '<u4')
    imm = lambda v: ((v >> 16) & 0xF) << 12 | (v & 0xFFF)  # noqa
    movw = (W & 0x0FF00000) == 0x03000000
    movt = (W & 0x0FF00000) == 0x03400000
    wi = np.flatnonzero(movw); ti = np.flatnonzero(movt)
    wreg = (W[wi] >> 12) & 0xF
    treg = (W[ti] >> 12) & 0xF
    targs, wids = [], []
    for k in range(len(ti)):
        j0 = int(np.searchsorted(wi, ti[k] - 8)); j1 = int(np.searchsorted(wi, ti[k]))
        for j in range(j0, j1):
            if wreg[j] == treg[k]:
                targs.append((imm(int(W[ti[k]])) << 16) | imm(int(W[wi[j]])))
                wids.append(int(ti[k]))
                break
    return targs, wids


def bl_callers(rt, target):
    W = np.frombuffer(rt[:len(rt) // 4 * 4], '<u4')
    isbl = (W & 0x0F000000) == 0x0B000000
    imm = (W & 0x00FFFFFF).astype(np.int64)
    imm = np.where(imm & 0x800000, imm - 0x1000000, imm)
    dest = BASE + np.arange(len(W)) * 4 + 8 + imm * 4
    return [BASE + 4 * int(i) for i in np.flatnonzero(isbl & (dest == target))]


def xrefs_movw(rt, target):
    targs, wids = movw_movt_targets(rt)
    return [BASE + 4 * int(i) for t, i in zip(targs, wids) if t == target]


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'b22'
    B22 = PROJECT_ROOT / 'workspace/b2_iiix/out/fwdc243b-8presets-protect-b22.bin'
    path = B22 if which == 'b22' else PROJECT_ROOT / 'firmware/official-v160/fwdc243b.bin'
    rt = load(path)
    addrs = [int(a, 16) for a in sys.argv[2:]]
    for a in addrs:
        size = 40 if len(addrs) == 1 else 16
        print(f'=== {a:#x} ===')
        print(dis(rt, a, size))
        print()