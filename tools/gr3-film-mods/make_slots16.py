"""Films v16 (FINDINGS §33): v15 + MultiAxial hue sectors for every film.

MultiAxial works on GR III stills once its set carries the GR IV's control values (§29-30b): 12 hue sectors by the Cb/Cr
angle of the post-look-matrix signal, one 3x3 per sector (x 5 levels). Against v15:
  * one shared GR IV set (bounds, selectors, control from work/ma_probe5/gr4_std_ma.json) and a 7-word set struct per
    film (stock set words 0-5 + a pointer to the film's sector data; bit 0 = GR IV level scaling); the film's slot in
    the per-slot MultiAxial table 0x55018CF0 points at it. Stock slots keep the stock (inactive) set.
  * sector data: 12 x 9 int8 per film, matrix = 1024 I + 4 x data (diagonal stored as -(row's off-diagonals)), i.e.
    off-diagonals in steps of 4/1024 and rows summing to 1024.
  * MultiAxial Make 0x536E4470 -> new Make: calc + writer as stock, then for a film's set it rewrites the 60 matrix
    registers (regs + 0x100 + 128 sector + 20 level, 12-bit fields) from the sector data: films the same matrix at all
    5 levels; Cinema (GR IV sets) level l = level 0 x (16 - l) / 16, as the GR IV's own tables.
  * space: the stock 360-entry 10-bit table 0x53DC2BF8 (1440 B of zeros, only referenced by the object 0x55019848)
    moves to a run of zeros in read-only data (ZERO_SRC), freeing 1440 B for the above.
Fits carry 'hue_q10' (12 x 3 x 3, rows sum 1024) and optionally 'hue_gr4_levels'.

Playback RAW development with films (FINDINGS §34; broken since v13: RawDevelopmentModel keeps its own image-control
enum 0..12 and its conversions assert for tones >= 25, so a film fell back to Standard):
  * ConvertToRawDevelopmentModelImageControl 0x53288D5C: appended film k -> new enum 13+k, replacing film -> the enum of
    the stock mode it replaces (Bleach Bypass 9, Retro 10, Cross 12). The parameter accessors already map an enum
    outside 1..12 to cache 0 (as-shot values), so 13+ is memory-safe.
  * RAW-dev enum -> tone 0x53289058: 13+k -> film tone; enums 9/10/12 -> the replacing films.
  * GetBaseKindDetailControl (tone -> slider page layout) of RAW development 0x5318DEA0 and of shooting 0x531ACB1C:
    film -> its proxy's layout (as the 102 Set/Get switches) instead of an assertion.

Usage: make_slots16.py [--raw-nr-above ISO] out.bin key[@T]=fit.json ...   (as make_slots15)
"""
import sys, json, struct, os
import numpy as np
import make_slots15 as M15
from make_slots15 import Space, code, put, B, STOCK, FILMS, LEGACY_SLOTS
from gr3patch import Image

MA_TABLE = 0x55018CF0                # per-slot MultiAxial set pointers
STOCK_SET = 0x53DC2BA0
MATOBJ, TOBJ, YCC = 0x55019828, 0x55019848, 0x53DC3A40
OLD_TAB, TAB_LEN = 0x53DC2BF8, 1440  # 360 x int32 zeros (10-bit table)
ZERO_SRC = 0x53D36400                # inside a 5404 B zero run of read-only data (no pointers into it)
MAKE, CALC, WRITER = 0x536E4470, 0x536DF484, 0x536DF55C
G4 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'work/ma_probe5/gr4_std_ma.json')))


def sector_bytes(q10):
    q = np.array(q10, int).reshape(12, 3, 3)
    assert (q.sum(2) == 1024).all(), 'sector rows must sum to 1024'
    off = q.copy()
    for g in range(12):
        np.fill_diagonal(off[g], 0)
    assert (off % 4 == 0).all(), 'off-diagonals must be multiples of 4'
    raw = off // 4
    for g in range(12):
        for r in range(3):
            raw[g, r, r] = -(raw[g, r].sum())
    assert np.abs(raw).max() <= 127
    return raw.astype(np.int8).tobytes()


def make_src(sets, sets_len):
    return lambda at: f'''
        push {{r4-r10, lr}}
        mov r4, r0
        mov r5, r1
        mov r6, r2
        bl abs({CALC:#x})
        mov r0, r4
        mov r1, r6
        bl abs({WRITER:#x})
        ldr r3, [r5, #0xc]
        movw ip, #{sets & 0xFFFF:#x}
        movt ip, #{sets >> 16:#x}
        sub r3, r3, ip
        cmp r3, #{sets_len}
        bhs D
        add r3, r3, ip
        ldr r8, [r3, #24]
        and r9, r8, #1
        bic r8, r8, #1
        add r6, r6, #0x100
        mov r7, #12
    S:  mov r4, #0
    L:  mov r10, #16
        cmp r9, #0
        subne r10, r10, r4
        add r0, r4, r4, lsl #2
        add r0, r6, r0, lsl #2
        mov r5, #0
    E:  ldrsb r2, [r8, r5]
        tst r5, #3
        addeq r2, r2, #256
        mul r2, r2, r10
        asr r2, r2, #2
        add r3, r0, r5, lsl #1
        ldrh ip, [r3]
        bfi ip, r2, #0, #12
        strh ip, [r3]
        add r5, r5, #1
        cmp r5, #9
        blt E
        add r4, r4, #1
        cmp r4, #5
        blt L
        add r6, r6, #128
        add r8, r8, #9
        subs r7, r7, #1
        bne S
    D:  pop {{r4-r10, pc}}
    '''


def patch_ma(img, films):
    """films as make_slots15.patch; fit dicts carry hue_q10. Returns info."""
    # free the stock 10-bit table: its object reads the same zeros from ZERO_SRC
    assert img.read(OLD_TAB, TAB_LEN) == bytes(TAB_LEN) and img.read(ZERO_SRC, TAB_LEN) == bytes(TAB_LEN)
    assert struct.unpack('<8I', img.read(TOBJ, 32)) == (OLD_TAB,) * 8
    img.write(TOBJ, struct.pack('<8I', *[ZERO_SRC] * 8))
    sp = Space([(OLD_TAB, OLD_TAB + TAB_LEN)])
    alloc = lambda data, name: (lambda at: (img.write(at, data), at)[1])(sp.take(len(data), name))
    # shared GR IV set fields (stock layout: selectors, control directly behind)
    stock_block = bytearray(img.read(0x53DC2BB8, 0x48))
    blk = bytearray(stock_block)
    blk[:20] = bytes(G4['selectors'])
    blk[20:62] = struct.pack('<21H', *G4['control'])
    bounds = alloc(struct.pack('<16H', *G4['bounds']), 'MA bounds')
    blk_at = alloc(bytes(blk), 'MA selectors+control')
    data_at = {}
    for key, label, fit, repl in films:
        data_at[key] = alloc(sector_bytes(fit['hue_q10']), f'MA sectors {key}')
    n = len(films)
    sets = sp.take(28 * n, 'MA sets')
    for k, (key, label, fit, repl) in enumerate(films):
        flag = 1 if fit.get('hue_gr4_levels') else 0
        s = sets + 28 * k
        img.write(s, struct.pack('<7I', bounds, blk_at, MATOBJ, TOBJ, blk_at + 20, YCC, data_at[key] | flag))
        slot = LEGACY_SLOTS[k]
        assert img.word(MA_TABLE + 4 * slot) == STOCK_SET, (key, slot)
        img.write(MA_TABLE + 4 * slot, struct.pack('<I', s))
    at = code(sp, img, 'MA make', make_src(sets, 28 * n))
    put(img, MAKE, B(MAKE, at), 0xE1A0C00D)
    return dict(sets=hex(sets), make=hex(at), data={k: hex(v) for k, v in data_at.items()},
                space=[(nm, hex(a), sz) for nm, a, sz in sp.used], free_left=[(hex(a), b - a) for a, b in sp.free])


RD_CONV, RD_TONE, RD_TONE_DEF, RD_KIND, SH_KIND = 0x53288D5C, 0x53289058, 0x53289070, 0x5318DEA0, 0x531ACB1C
# maker-note ImageTone (Pentax tag 0x4F): writer 0x535C7814 searches a {u8 tone, u8 0, u16 code} vector built by the
# static constructor 0x53599DF8 from 12 entries at 0x53D2B6F4 (unknown tone -> 0x100 Standard); playback reads the tag
# back in 0x535BF7A8 (code - 0x101 <= 10 -> u8 table 0x53D2D920, else 11). Films get codes 0x10C + k both ways.
EXIF_CTOR, EXIF_PAIRS, EXIF_READ, EXIF_READ_TAB, EXIF_CODE0 = 0x53599DF8, 0x53D2B6F4, 0x535BF7D0, 0x53D2D920, 0x10C
RD_COUNT = 0x53283C08
# RAW-dev parameter screen, Image Control row (RawDevelopmentParameterSetController case 8; the list the user sees):
# options = [as shot (if the file has one, model+5)] + enum table 0x53B5A988 (1..12) + develop settings 1, 2.
# count 0x53283358 (15/14), option -> slot 0x532834D0 and option -> enum 0x532834F0 via slot table 0x53B5ACB4,
# capacity (largest option count of all rows, list items allocated) 0x532833BC (15).
RD_OPT_COUNT, RD_OPT_MAX, RD_OPT_ENUMS, RD_OPT_SLOTS = 0x53283358, 0x532833BC, 0x53B5A988, 0x53B5ACB4
RD_OPT_SLOT_FN, RD_OPT_ENUM_FN = 0x532834D0, 0x532834F0   # RawDevelopmentModel image-control value count `mov r0,#0xc; bx lr` (RAW-dev list length)


def mov_imm(word):
    assert word & 0xFFFFF000 == 0xE3A00000, hex(word)
    return word & 0xFF


def jump_table(img, at, n):
    """`cmp rX,#n-1; ldrls pc,[pc,rX,lsl #2]; b default` at `at`: case -> mov r0,#imm result."""
    return [mov_imm(img.word(img.word(at + 12 + 4 * i))) for i in range(n)]


def patch_rawdev(img, films, info15):
    used = {nm: int(a, 16) for nm, a, _ in info15['_code']['space']}
    proxy_tab = used['proxy table']
    t0, n = M15.FIRST_TONE, len(films)
    sp = M15.FALLBACK[0]
    # stock tables: tone 11..22 -> enum (ConvertToRD), enum 1..12 -> tone (RD -> tone)
    assert img.word(RD_CONV) == 0xE241100B and img.word(RD_CONV + 0x14) == 0xE351000B
    to_enum = dict(zip(range(11, 23), jump_table(img, RD_CONV + 0x14, 12)))
    assert img.word(RD_TONE + 0x10) == 0xE351000C
    enum_tone_at = {e: img.word(RD_TONE + 0x1C + 4 * e) for e in range(1, 13)}
    enums, nxt = [], 13
    for key, label, fit, repl in films:
        if repl is None:
            enums.append(nxt); nxt += 1
        else:
            e = to_enum[repl]; enums.append(e)
            at = enum_tone_at[e]
            put(img, at, 0xE3A00000 | (t0 + len(enums) - 1), 0xE3A00000 | repl)   # enum e -> the replacing film
    tab = sp.take(n, 'RAW dev film enums')
    img.write(tab, bytes(enums))
    conv = code(sp, img, 'RAW dev tone->enum', lambda at: f'''
        sub ip, r1, #{t0}
        cmp ip, #{n}
        bhs S
        movw r0, #{tab & 0xFFFF:#x}
        movt r0, #{tab >> 16:#x}
        ldrb r0, [r0, ip]
        bx lr
    S:  sub r1, r1, #0xb
        b abs({RD_CONV + 4:#x})''')
    put(img, RD_CONV, B(RD_CONV, conv), 0xE241100B)
    m = nxt - 13                                   # appended films: enums 13..13+m-1 -> tones t0..t0+m-1
    first_app = [k for k, f in enumerate(films) if f[3] is None]
    assert first_app == list(range(m))
    back = code(sp, img, 'RAW dev enum->tone', lambda at: f'''
        sub r0, r1, #13
        cmp r0, #{m}
        addlo r0, r0, #{t0}
        blo abs({RD_TONE + 0x54:#x})
        b abs({RD_TONE + 0xC0:#x})''')
    assert img.word(RD_TONE + 0x54) == 0xE24BD00C                       # sub sp, fp, #0xc (common return)
    assert img.word(RD_TONE_DEF) == B(RD_TONE_DEF, RD_TONE + 0xC0)       # b default (assertion)
    put(img, RD_TONE_DEF, B(RD_TONE_DEF, back), img.word(RD_TONE_DEF))
    # RAW-dev parameter screen Image Control options: append the new enums 13..12+m before the two develop settings
    assert bytes(img.read(RD_OPT_ENUMS, 12)) == bytes(range(1, 13))
    assert bytes(img.read(RD_OPT_SLOTS, 16)) == bytes(13) + bytes([1, 2, 0])
    et = sp.take(12 + m, 'RAW dev option enums')
    img.write(et, bytes(range(1, 13 + m)))
    st = sp.take(16 + m, 'RAW dev option slots')
    img.write(st, bytes(13 + m) + bytes([1, 2, 0]))
    for at, old, new in ((0x532834D8, RD_OPT_SLOTS, st), (0x532834F4, RD_OPT_SLOTS, st), (0x532835C8, RD_OPT_ENUMS, et),
                         (0x532835DC, RD_OPT_ENUMS, et)):
        put(img, at, M15.movw(3, new), M15.movw(3, old))
    for at, old, new in ((0x532834DC, RD_OPT_SLOTS, st), (0x53283510, RD_OPT_SLOTS, st), (0x53283564, RD_OPT_SLOTS, st),
                         (0x532835CC, RD_OPT_ENUMS, et), (0x532835E4, RD_OPT_ENUMS, et)):
        put(img, at, M15.movt(3, new), M15.movt(3, old))
    put(img, RD_OPT_COUNT + 8, 0x13A00000 | (15 + m), 0x13A0000F)      # movne r0,#15 (with as shot)
    put(img, RD_OPT_COUNT + 12, 0x03A00000 | (14 + m), 0x03A0000E)     # moveq r0,#14
    put(img, RD_OPT_MAX, 0xE3A00000 | (15 + m), 0xE3A0000F)            # list item capacity
    # the RAW-dev Image Control list (RawDevelopmentImageControlDetailSetController 0x53190108) takes its length from
    # this hard-wired 12, not from ImageControlModel's count; rows map through the patched index -> tone table
    assert img.word(RD_COUNT + 4) == 0xE12FFF1E
    put(img, RD_COUNT, 0xE3A00000 | (12 + m), 0xE3A0000C)
    kind = code(sp, img, 'RAW dev detail kind', lambda at: f'''
        sub ip, r1, #{t0}
        cmp ip, #{n}
        subhs r1, r1, #0xb
        bhs abs({RD_KIND + 4:#x})
        movw ip, #{(proxy_tab - t0) & 0xFFFF:#x}
        movt ip, #{(proxy_tab - t0) >> 16:#x}
        ldrb r1, [ip, r1]
        b abs({RD_KIND + 4:#x})''')
    put(img, RD_KIND, B(RD_KIND, kind), 0xE241100B)
    # shooting: the `sub r4,r4,#0xb` at 0x531ACB00 sits between a compare and its conditional use, so the film
    # mapping goes on the later `cmp r4,#0xb` (r4 = tone - 11 there; flags are set by the stub's own compare)
    sh = code(sp, img, 'shooting detail kind', lambda at: f'''
        sub ip, r4, #14
        cmp ip, #{n}
        bhs C
        movw ip, #{(proxy_tab - 14) & 0xFFFF:#x}
        movt ip, #{(proxy_tab - 14) >> 16:#x}
        ldrb r4, [ip, r4]
    C:  cmp r4, #0xb
        bx lr''')
    put(img, SH_KIND, M15.BL(SH_KIND, sh), 0xE354000B)
    return dict(enums={f[0]: e for f, e in zip(films, enums)}, conv=hex(conv), back=hex(back), kind=hex(kind))


def patch_exif_tone(img, films):
    t0, n = M15.FIRST_TONE, len(films)
    sp = M15.FALLBACK[0]
    pairs = bytes(img.read(EXIF_PAIRS, 48))
    assert [struct.unpack_from('<BBH', pairs, 4 * i) for i in range(12)] == [(11 + i, 0, 0x100 + i) for i in range(12)]
    new = pairs + b''.join(struct.pack('<BBH', t0 + k, 0, EXIF_CODE0 + k) for k in range(n))
    tab = sp.take(len(new), 'ImageTone pairs')
    img.write(tab, new)
    c = EXIF_CTOR
    sz = 4 * (12 + n)
    assert sz < 256
    put(img, c - 4, 0xE3A00000 | sz, 0xE3A00030)                      # mov r0,#0x30 (new size)
    put(img, c + 0x28, M15.movw(12, tab), M15.movw(12, EXIF_PAIRS))
    put(img, c + 0x34, M15.movt(12, tab), M15.movt(12, EXIF_PAIRS))
    put(img, c + 0x38, 0xE2801000 | sz, 0xE2801030)                   # add r1,r0,#0x30 (capacity end)
    put(img, c + 0x54, 0xE3530000 | (12 + n), 0xE353000C)             # cmp r3,#0xc (copy count)
    put(img, c + 0x68, 0xE2800000 | sz, 0xE2800030)                   # add r0,r0,#0x30 (end)
    rd_tab = bytes(img.read(EXIF_READ_TAB, 11))
    assert list(rd_tab) == list(range(12, 23))
    rtab = sp.take(11 + n, 'ImageTone read table')
    img.write(rtab, rd_tab + bytes(range(t0, t0 + n)))
    r = EXIF_READ
    put(img, r, 0xE3500000 | (10 + n), 0xE350000A)                     # cmp r0,#0xa
    ls = lambda wd: (wd & 0x0FFFFFFF) | 0x90000000                       # condition LS
    put(img, r + 4, ls(M15.movw(3, rtab)), ls(M15.movw(3, EXIF_READ_TAB)))   # movwls r3, table
    put(img, r + 0xC, ls(M15.movt(3, rtab)), ls(M15.movt(3, EXIF_READ_TAB)))
    return dict(pairs=hex(tab), read_table=hex(rtab), codes={films[k][0]: EXIF_CODE0 + k for k in range(n)})


def patch_playback_detail(img, films):
    """Extend the *playback detail* chain for appended films (B2.4, Bug B).

    The playback info page parses the maker-note ImageTone tag through a different path than the still
    disp/shooting path (0x535BF7A8, already extended by patch_exif_tone). It has three stages, each with a
    hard-wired factory range and a small read-only table; all three must be extended, keeping the factory
    rows byte-identical (the playback "display tone" is NOT the image-control tone enum):

      1. 0x535C24EC CommonShootingInformationExtractor: EXIF code 0x100..0x10B -> enum 1..12
         cmp r0,#0xb @0x535C2514, table 0x53D2DD64 (12 B, identity)
      2. 0x532B44BC PlaybackDataModel: enum 1..12 -> display tone (8..22, permuted)
         cmp r0,#0xb @0x532B44DC, table 0x53B5CBC4 (12 B)
      3. 0x532B6EEC PlaybackDataDispModel: display tone-8 -> icon id (u16), tones 8..22
         cmp r3,#0xe @0x532B6F3C, table 0x53B5B2F0 (15 u16)

    Films: EXIF 0x10C+k -> enum 13+k -> display tone 25+k (FIRST_TONE+k) -> the film's own icon id
    (the same ids the shooting screen shows, M15.ICON_IDS[k]); the playback widget draws them through the
    same (already patched) icon catalog.
    """
    sp = M15.FALLBACK[0]
    n = len(films)
    t0 = M15.FIRST_TONE
    ls = lambda wd: (wd & 0x0FFFFFFF) | 0x90000000                       # force condition LS

    # --- 1. EXIF code -> playback enum -------------------------------------------------------------------
    cmp1, movw1, movt1 = 0x535C2514, 0x535C2518, 0x535C2520
    tab1_old = 0x53D2DD64
    old1 = bytes(img.read(tab1_old, 12))
    assert old1 == bytes(range(1, 13)), old1
    tab1 = sp.take(12 + n, 'pb EXIF->enum')
    img.write(tab1, old1 + bytes(range(13, 13 + n)))
    put(img, cmp1, 0xE3500000 | (11 + n), 0xE350000B)                    # cmp r0,#0xb -> #11+n
    put(img, movw1, ls(M15.movw(3, tab1)), ls(M15.movw(3, tab1_old)))    # movwls r3, table
    put(img, movt1, ls(M15.movt(3, tab1)), ls(M15.movt(3, tab1_old)))    # movtls r3, table

    # --- 2. playback enum -> display tone ----------------------------------------------------------------
    cmp2, movw2, movt2 = 0x532B44DC, 0x532B44E4, 0x532B44EC
    tab2_old = 0x53B5CBC4
    old2 = bytes(img.read(tab2_old, 12))
    assert old2 == bytes([11, 12, 10, 14, 15, 16, 17, 8, 19, 20, 21, 22]), old2
    tab2 = sp.take(12 + n, 'pb enum->tone')
    img.write(tab2, old2 + bytes(range(t0, t0 + n)))
    put(img, cmp2, 0xE3500000 | (11 + n), 0xE350000B)
    put(img, movw2, M15.movw(3, tab2), M15.movw(3, tab2_old))
    put(img, movt2, M15.movt(3, tab2), M15.movt(3, tab2_old))

    # --- 3. display tone -> icon -------------------------------------------------------------------------
    cmp3, movw3, movt3 = 0x532B6F3C, 0x532B6F40, 0x532B6F4C
    tab3_old = 0x53B5B2F0
    old3 = bytes(img.read(tab3_old, 30))
    assert old3 == struct.pack('<15H', 0x15A, 0x000, 0x162, 0x166, 0x224, 0x000, 0x165, 0x15E,
                               0x160, 0x0E8, 0x000, 0x164, 0x15F, 0x032, 0x017), old3
    need = (t0 + n - 1) - 8 + 1                                          # highest index is tone t0+n-1 -> -8
    need = max(need, 15)
    tab3 = sp.take(2 * need, 'pb tone->icon')
    buf = bytearray(old3) + bytes(2 * need - len(old3))
    icons = M15.ICON_IDS[:n] if hasattr(M15, 'ICON_IDS') else ()
    for k in range(n):
        off = 2 * ((t0 + k) - 8)
        if off + 2 <= len(buf):
            struct.pack_into('<H', buf, off, icons[k] if k < len(icons) else 0)
    img.write(tab3, bytes(buf))
    put(img, cmp3, 0xE3530000 | (need - 1), 0xE353000E)                  # cmp r3,#0xe -> #need-1
    put(img, movw3, ls(M15.movw(2, tab3)), ls(M15.movw(2, tab3_old)))
    put(img, movt3, ls(M15.movt(2, tab3)), ls(M15.movt(2, tab3_old)))

    return dict(exif_enum=hex(tab1), enum_tone=hex(tab2), tone_icon=hex(tab3),
                film_icons=[hex(i) for i in icons[:n]])



if __name__ == '__main__':
    args = sys.argv[1:]
    raw_nr_above = None
    if '--raw-nr-above' in args:
        i = args.index('--raw-nr-above')
        raw_nr_above = int(args[i + 1])
        del args[i:i + 2]
    out = args[0]
    films = []
    for a in args[1:]:
        key, path = a.split('=', 1)
        key, repl = (key.split('@') + [None])[:2]
        films.append((key, FILMS[key], json.load(open(path)), int(repl) if repl else None))
    img = Image(STOCK)
    info = M15.patch(img, films, raw_nr_above)
    info['_multiaxial'] = patch_ma(img, films)
    info['_rawdev'] = patch_rawdev(img, films, info)
    info['_exif_tone'] = patch_exif_tone(img, films)
    info['_playback_detail'] = patch_playback_detail(img, films)
    data, rep = img.build()
    open(out, 'wb').write(data)
    for k, v in info.items():
        print(k, v)
    print(rep)
