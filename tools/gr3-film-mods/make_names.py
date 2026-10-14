"""Rename the replaced Image Control modes in every UI language (equal size, in place).

String table: RAM 0x55002BAC[lang] (21 languages) -> u32[0x311] entry pointers; entry =
{u8 chars incl. NUL, u8 1, u16 0, u32 -> UTF-16LE text}. Tone -> string id from 0x532922B4:
Vivid 0x10C, Retro 0x114, HDR Tone 0x115, Cross Processing 0x116, Bleach Bypass 0x113 (each text/entry
single-referenced).
The new name is written over the longest existing translation of that id that can hold it, and
all 21 language entries are pointed at it.
"""
import struct
from gr3patch import Image

STRINGS = 0x55002BAC
N_LANG = 21
STRING_ID = dict(vivid=0x10C, retro=0x114, hdr=0x115, cross=0x116, bleach=0x113)
NAMES = dict(cross='Portra 400', vivid='Ektar 100', retro='Gold 200', hdr='Pro 400H')
NAMES_V10 = dict(NAMES, bleach='Vision3 250D')
NAMES_V12 = dict(NAMES, bleach='Classic Neg')


def text(img, addr):
    out = bytearray()
    while True:
        ch = img.read(addr + len(out), 2)
        if ch == b'\0\0':
            return out.decode('utf-16le')
        out += ch


def patch_names(img, names=NAMES):
    done = {}
    for mode, new in names.items():
        sid = STRING_ID[mode]
        entries = [img.word(img.word(STRINGS + 4 * lang) + 4 * sid) for lang in range(N_LANG)]
        texts = [img.word(e + 4) for e in entries]
        host = max(texts, key=lambda t: len(text(img, t)))
        room = len(text(img, host))
        assert len(new) <= room, (mode, new, room)
        img.write(host, (new + '\0' * (room - len(new) + 1)).encode('utf-16le'))
        for e in entries:
            img.write(e, struct.pack('<BBHI', len(new) + 1, 1, 0, host))
        done[mode] = (hex(sid), new, hex(host))
    return done


if __name__ == '__main__':
    import sys
    img = Image(sys.argv[1])
    print(patch_names(img))
