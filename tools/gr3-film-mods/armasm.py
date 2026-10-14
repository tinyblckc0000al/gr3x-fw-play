"""Assemble a small ARM (A32) stub at a fixed address with llvm-mc (Homebrew llvm).

One instruction per line, optional 'label:' prefix, '@' comments. Branches to absolute firmware addresses are
written 'bl abs(0xADDR)' / 'b abs(0xADDR)' (also beq/bne/blo/bhs/bls/bhi) and encoded here; local labels are resolved by llvm-mc.
`.word` lines are allowed. Returns a list of 32-bit words (little-endian in the image).
"""
import os, re, subprocess, tempfile

LLVM = os.environ.get('LLVM_BIN', '/opt/homebrew/opt/llvm/bin/')
COND = {'b': 0xE, 'beq': 0x0, 'bne': 0x1, 'blo': 0x3, 'bhs': 0x2, 'bls': 0x9, 'bhi': 0x8}


def assemble(src, base):
    lines = [l.split('@')[0].rstrip() for l in src.strip().splitlines()]
    lines = [l for l in lines if l.strip()]
    fixed = []
    for i, l in enumerate(lines):
        at = base + 4 * i
        m = re.match(r'^\s*(\w+:\s*)?(bl|b|beq|bne|blo|bhs|bls|bhi)\s+abs\((0x[0-9a-fA-F]+)\)\s*$', l)
        if m:
            off = ((int(m.group(3), 16) - at - 8) >> 2) & 0xFFFFFF
            word = 0xEB000000 | off if m.group(2) == 'bl' else (COND[m.group(2)] << 28) | 0x0A000000 | off
            fixed.append(f'{m.group(1) or ""}.word {word:#x}')
        else:
            fixed.append(l)
    with tempfile.TemporaryDirectory() as d:
        s, o, b = (os.path.join(d, n) for n in ('a.s', 'a.o', 'a.bin'))
        open(s, 'w').write('.syntax unified\n.arm\n.text\n' + '\n'.join(fixed) + '\n')
        r = subprocess.run([LLVM + 'llvm-mc', '-triple=armv7a-none-eabi', '-filetype=obj', '-o', o, s],
                           capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError(r.stderr)
        subprocess.run([LLVM + 'llvm-objcopy', '-O', 'binary', '--only-section=.text', o, b], check=True)
        data = open(b, 'rb').read()
    assert len(data) == 4 * len(lines), (len(data), len(lines))
    return [int.from_bytes(data[i:i + 4], 'little') for i in range(0, len(data), 4)]
