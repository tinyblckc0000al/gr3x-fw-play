"""Films v10 code: per-film post-gamma 3x3 through the RGB->YCbCr matrix, and a fifth film whose curves are stored as
knots (FINDINGS §22l).

Why: photo-v8/photo-v9 show that CCA1 is applied in the *linear* domain, right after CCA0 (camera = curves(base(C M L)),
dE 0.6 vs. camera), not after the gamma curves as v8/v9 assumed (dE 1.8). The post-gamma matrix the joint fits want is
therefore put into the CSP (RGB->YCbCr, 9 x 9-bit signed, 256 = 1.0, info+0x1180), which JPEG decoding inverts with
the standard BT.601 matrix: decoded RGB = P * curves(...). CCA1 stays at its stock identity.

Pieces (all in dead code, see below):
  * CSP stub: YCbCrMatrix Make 0x536E4760 calls it instead of its calc 0x536E4720. It runs the calc (hue-rotated
    BT.601 matrix H in obj[0..8], 19-bit two's complement), looks up the look record [ctx+8] in a table and, for a
    film, replaces H by round(H P) (P: int16 x/512). Hue adjustment keeps working on top of the film matrix.
  * Fill: the ctx fill tail (0x536DD454) branches here. Per tone it writes library curve pointers 6..11 (stock, HDR
    = curves 0-2 in 6-8, Bleach = knot tables in 9-11) and the curve-set selector SI+0x38A98 (12/18 -> 4, 19/20 -> 3,
    21 -> 2, else 0). Replaces the v4..v9 in-place chain at 0x536DD4B8 (now holds the three pointer sets).
  * Getter stub: the composite 0x536E8668 calls it instead of the curve-pointer getter 0x536EEDF0. A pointer that
    falls inside the knot tables is expanded (33 knots, step 8, linear, as `expand`) into g+0xA08.. (the packed gamma
    tables, rewritten from the composite later in the same call, emulated) and replaced by that buffer.

Dead code used: the Cross "random" curve-set case of 0x536EF148 (jump-table entry 0, selector 1, never set by the
film builds): 0x536EF618 becomes `b 0x536EF6DC` (the fixed-preset case, live, 0x536EF6DC..0x536EF6F8 untouched),
0x536EF61C..0x536EF6D8 (area A) and 0x536EF6FC..0x536EF994 (area B) are free. The stock Cross-preset chain
0x536DD4B8..0x536DD50C is only reached from 0x536DD454.
"""
import struct
import numpy as np
from armasm import assemble

B = lambda at, to, cond=0xE: (cond << 28) | 0x0A000000 | (((to - at - 8) >> 2) & 0xFFFFFF)
BL = lambda at, to: 0xEB000000 | (((to - at - 8) >> 2) & 0xFFFFFF)

CURVE_LIB = 0x55037604
RANDOM, PRESET = 0x536EF618, 0x536EF6DC
AREA_A, AREA_A_END = 0x536EF61C, 0x536EF6DC
AREA_B, AREA_B_END = 0x536EF6FC, 0x536EF998
SETS, SETS_END = 0x536DD4B8, 0x536DD510
FILL_AT = 0x536DD454                               # stock beq 0x536DD4B8 (v4..v9: cmp r1,#20)
CSP_CALL, CSP_CALC = 0x536E4774, 0x536E4720        # bl calc inside YCbCrMatrix Make 0x536E4760
GET_CALL, GETTER = 0x536E87C4, 0x536EEDF0          # bl getter inside the composite 0x536E8668
STEP, N_KNOTS = 8, 33
KNOT_BYTES = 3 * 2 * N_KNOTS


def fill_src(sets, selectors, ret):
    """sets: SETS address; selectors: [(tone, sel)]; ret: the function's epilogue word (stock 0x536DD464).
    r1 = tone, r3 = ShootingInfo base (ldr at 0x536DD450)."""
    lib6 = CURVE_LIB + 24
    sel = '\n'.join(f'cmp r1, #{t}\nmoveq r2, #{s}' for t, s in selectors)
    return f'''
        movw r0, #{sets & 0xFFFF:#x}
        movt r0, #{sets >> 16:#x}
        cmp r1, #20
        addeq r0, r0, #24          @ HDR: curves 0-2 in slots 6-8
        cmp r1, #18
        addeq r0, r0, #48          @ Bleach: knot tables in slots 9-11
        ldm r0, {{r4, r5, r7, r8, r9, r10}}
        movw r0, #{lib6 & 0xFFFF:#x}
        movt r0, #{lib6 >> 16:#x}
        stm r0, {{r4, r5, r7, r8, r9, r10}}
        add r3, r3, #0x38000
        mov r2, #0
        {sel}
        strb r2, [r3, #0xa98]
        .word {ret:#x}             @ ldm sp, {{r3-r10, fp, sp, pc}}
    '''


def getter_src(exp):
    return f'''
        push {{r4, r5, r6, r7, r8, lr}}
        mov r4, r1
        mov r5, r2
        mov r6, r3
        bl abs({GETTER:#x})
        ldr r7, [r11, #-0x44]      @ gamma object g (caller frame)
        add r7, r7, #0xa00
        add r7, r7, #8             @ scratch g+0xa08 (3 x 512 B)
        mov r0, r4
        bl abs({exp:#x})
        mov r0, r5
        bl abs({exp:#x})
        mov r0, r6
        bl abs({exp:#x})
        pop {{r4, r5, r6, r7, r8, pc}}
    '''


def expand_src(knots):
    return f'''
        ldr r1, [r0]               @ curve pointer
        movw r2, #{knots & 0xFFFF:#x}
        movt r2, #{knots >> 16:#x}
        subs r2, r1, r2
        bxlo lr
        cmp r2, #{KNOT_BYTES}
        bxhs lr
        str r7, [r0]
        mov r2, #0
    E:  lsr r3, r2, #3
        add r3, r1, r3, lsl #1
        ldrh r12, [r3]
        ldrh r3, [r3, #2]
        sub r3, r3, r12
        and r8, r2, #7
        mul r3, r8, r3
        add r12, r12, r3, asr #3
        strh r12, [r7], #2
        add r2, r2, #1
        cmp r2, #256
        bne E
        bx lr
    '''


def csp_src(table):
    return f'''
        push {{r0, r1, r4, r5, r6, r7, r8, lr}}
        bl abs({CSP_CALC:#x})
        ldr r0, [sp]               @ YCbCrMatrix object: 9 coefficients
        ldr r1, [sp, #4]
        ldr r3, [r1, #8]           @ look record
        movw r4, #{table & 0xFFFF:#x}
        movt r4, #{table >> 16:#x}
    L:  ldr r12, [r4]
        cmp r12, #0
        beq D
        cmp r12, r3
        addne r4, r4, #24
        bne L
        add r4, r4, #4             @ P, int16 row-major, 512 = 1.0
        sub sp, sp, #36
        mov r12, #0
    C:  ldr lr, [r0, r12]
        lsl lr, lr, #13
        asr lr, lr, #13            @ sign-extend 19 bits
        str lr, [sp, r12]
        add r12, r12, #4
        cmp r12, #36
        bne C
        mov r5, #0                 @ row i * 12
    O:  mov r6, #0                 @ column j * 2
    I:  ldr r7, [sp, r5]
        ldrsh r8, [r4, r6]
        mul lr, r7, r8
        add r2, r5, #4
        ldr r7, [sp, r2]
        add r2, r6, #6
        ldrsh r8, [r4, r2]
        mla lr, r7, r8, lr
        add r2, r5, #8
        ldr r7, [sp, r2]
        add r2, r6, #12
        ldrsh r8, [r4, r2]
        mla lr, r7, r8, lr
        add lr, lr, #256
        asr lr, lr, #9
        lsl lr, lr, #13
        lsr lr, lr, #13
        str lr, [r0], #4
        add r6, r6, #2
        cmp r6, #6
        bne I
        add r5, r5, #12
        cmp r5, #36
        bne O
        add sp, sp, #36
    D:  pop {{r0, r1, r4, r5, r6, r7, r8, pc}}
    '''


def knots_of(curve):
    """Least-squares 33-knot fit of a 256-entry curve under `expand`'s interpolation; ints, monotone, 0..16383."""
    i = np.arange(256); k, f = i // STEP, (i % STEP) / STEP
    A = np.zeros((256, N_KNOTS)); A[i, k] += 1 - f; A[i, k + 1] += f
    kn = np.linalg.lstsq(A, np.asarray(curve, float), rcond=None)[0]
    kn = np.maximum.accumulate(np.clip(np.round(kn), 0, 16383)).astype(int)
    return kn


def expand(kn):
    """Exactly what the stub computes."""
    i = np.arange(256); k, f = i // STEP, i % STEP
    kn = np.asarray(kn, np.int64)
    return kn[k] + ((kn[k + 1] - kn[k]) * f >> 3)


def csp_entry(key, P):
    flat = [int(v) for row in P for v in row]
    assert len(flat) == 9 and all(-32768 <= v < 32768 for v in flat)
    return struct.pack('<I9hH', key, *flat, 0)


def patch_cave(img, selectors, bleach_knots, post_by_record):
    """selectors: [(tone, curve-set selector)]; bleach_knots: 3 x 33 ints (R,G,B);
    post_by_record: {look record: 3x3 int (512 = 1.0)} applied after the gamma curves via the CSP matrix."""
    def put(at, word, expect=None):
        if expect is not None:
            assert img.word(at) == expect, f'{at:#x}: {img.word(at):#010x} != {expect:#010x}'
        img.write(at, struct.pack('<I', word))

    def place(at, end, words_or_bytes):
        data = words_or_bytes if isinstance(words_or_bytes, bytes) else struct.pack(f'<{len(words_or_bytes)}I', *words_or_bytes)
        assert at + len(data) <= end, (hex(at), len(data), hex(end))
        img.write(at, data)
        return at + ((len(data) + 3) & ~3)

    lib = [img.word(CURVE_LIB + 4 * i) for i in range(12)]
    assert all(a >> 16 == 0x53EF for a in lib)
    # area B: CSP stub, its table, the knot expander, the knots
    csp_at = AREA_B
    n_csp = len(assemble(csp_src(0), csp_at))
    table_at = csp_at + 4 * n_csp
    table = b''.join(csp_entry(k, P) for k, P in post_by_record.items()) + csp_entry(0, [[512, 0, 0], [0, 512, 0], [0, 0, 512]])
    exp_at = table_at + len(table)
    n_exp = len(assemble(expand_src(0), exp_at))
    knots_at = exp_at + 4 * n_exp
    kn = np.asarray(bleach_knots, int)
    assert kn.shape == (3, N_KNOTS)
    cur = place(csp_at, AREA_B_END, assemble(csp_src(table_at), csp_at))
    assert cur == table_at
    cur = place(table_at, AREA_B_END, table)
    assert cur == exp_at
    cur = place(exp_at, AREA_B_END, assemble(expand_src(knots_at), exp_at))
    cur = place(knots_at, AREA_B_END, struct.pack(f'<{3 * N_KNOTS}H', *kn.ravel().tolist()))
    end_b = cur
    # area A: fill + getter stub
    fill_at = AREA_A
    ret = img.word(0x536DD464)
    assert ret == 0xE89DAFF8, hex(ret)
    fill = assemble(fill_src(SETS, selectors, ret), fill_at)
    get_at = fill_at + 4 * len(fill)
    cur = place(fill_at, AREA_A_END, fill)
    end_a = place(get_at, AREA_A_END, assemble(getter_src(exp_at), get_at))
    # pointer sets for library slots 6..11
    knot_ptrs = [knots_at + 2 * N_KNOTS * c for c in range(3)]
    sets = [lib[6:12], lib[0:3] + lib[9:12], lib[6:9] + knot_ptrs]
    place(SETS, SETS_END, struct.pack('<18I', *[p for s in sets for p in s]))
    # hooks
    put(RANDOM, B(RANDOM, PRESET), 0xEDDF0BE0)                    # was vldr d16,[pc,#0x380]
    put(FILL_AT, B(FILL_AT, fill_at), B(FILL_AT, SETS, 0x0))                # was beq 0x536DD4B8
    put(CSP_CALL, BL(CSP_CALL, csp_at), BL(CSP_CALL, CSP_CALC))
    put(GET_CALL, BL(GET_CALL, get_at), BL(GET_CALL, GETTER))
    return dict(fill=hex(fill_at), getter=hex(get_at), area_a_used=end_a - AREA_A, csp=hex(csp_at), csp_table=hex(table_at),
                expand=hex(exp_at), knots=hex(knots_at), area_b_used=end_b - AREA_B, sets=hex(SETS))
