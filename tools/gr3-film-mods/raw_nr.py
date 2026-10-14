"""Turn off the Bayer noise reduction applied to stills before the RAW is stored (FINDINGS §21).

The PPU (sensor front end: SLVS-EC RX, OB clamp, DPC, PDSP, NR) filters the Bayer data before the main pipeline
and the DNG writer see it. The still FE setup 0x5343322c sets the PPU NR unit enable (out+0x64 -> cfg+0x14 ->
enable-mask bit 3 in 0x53642e78) and the NR parameter mode (out+0x69 -> cfg+0x19 -> NRUnit mode 0 "on" / 3 "off"
in 0x53642b24) from a runtime config, unless the debug flags DISABLE_PPU_NR (0x77) / DISABLE_PPU_NR_PARAM (0x7c)
are set. This patch makes both behave as if those flags were set. The alternate capture path 0x53642a84 sets mask
bit 3 from cfg+2 on its own, so its `orrne r4, r3, #0x18` loses bit 3 too. Live view (0x5343f2ec) is untouched.
JPEG noise reduction (High-ISO NR menu, R2Y/CNR) is untouched.
"""
import math
import struct


def patch_raw_nr_off(img):
    def put(at, word, expect):
        assert img.word(at) == expect, f'{at:#x}: {img.word(at):#010x} != {expect:#010x}'
        img.write(at, struct.pack('<I', word))
    put(0x5343326C, 0xE3A06000, 0x02266001)   # mov r6,#0 (was eoreq r6,r6,#1): PPU NR unit off
    put(0x53433284, 0xE3A07000, 0x02277001)   # mov r7,#0 (was eoreq r7,r7,#1): PPU NR parameters off
    put(0x53642AC4, 0x13834010, 0x13834018)   # orrne r4,r3,#0x10 (was #0x18): alternate path, NR bit 3 off
    return ['0x5343326c', '0x53433284', '0x53642ac4']


B_TABLES = 0x550375EC          # NRUnit mode-0 ("on") B tables, one per variant: 144 x 20 bytes, byte 0 = NR enable
ISO_INDEX = lambda iso: round(8 * (math.log2(iso / 3.125) - 1))   # ISO 100 -> 32, 6400 -> 80


def above_index(iso):
    """First table index above a 1/3-stop ISO: midway to the next 1/3 stop (ISO 8000 = 82.7 -> 84, 10000 = 85.3)."""
    return round(8 * (math.log2(iso / 3.125) - 1) + 4 / 3)


def patch_raw_nr_min_iso(img, min_iso=6400, first=None):
    """Keep the stock RAW NR only from min_iso up (or from table index `first`): clear the enable byte of the mode-0
    B entries below it, so lower ISOs get the same parameters as stock ISO <= 125 (index < 36, enable 0). Strengths
    above are untouched."""
    first = ISO_INDEX(min_iso) if first is None else first
    changed = []
    for v in range(2):
        tab = img.word(B_TABLES + 4 * v)
        assert tab >> 16 == 0x53EF
        for i in range(first):
            e = tab + 20 * i
            if img.read(e, 1) != b'\0':
                assert img.read(e, 1) == b'\1'
                img.write(e, b'\0')
                changed.append(i)
    assert set(changed) == set(range(36, first))
    return f'NR enable cleared for ISO index 36..{first - 1}, 2 variants'
