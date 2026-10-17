"""Offline GR IIIx 1.60 look-patch builder.

Port of gr3patch.py (written for GR III 2.10, fwdc239b.bin). The III/IIIx RTOS
sections are the same program at the same virtual addresses - the 148 sites the
film-mods patch code touches are byte-identical between GR III 2.10 and IIIx 1.60
(see workspace/verify_address_portability.py, log
workspace/logs/verify-address-20261013-040952.log), and the container section
layout is identical too (workspace/logs for the section dump). So the patch code
in make_slots15.py / make_slots16.py is used unchanged; this module only adapts
the stock image identity and re-uses the same container codec (gr4_editor).

Never touches a camera.
"""
import struct, hashlib
from pathlib import Path
import codec_path  # noqa: F401  (gr4_editor from third_party/gr-custom-tool)
from gr4_editor.codec.container import inspect_container, repair_last_word, sum32
from gr4_editor.codec.frames import decode_payload, section_rows, framed_container
from gr4_editor.firmware import _repack_frames

BASE, DSRC, DDST, DLEN = 0x53000000, 0x5407B540, 0x55000000, 0x3A080
EXPECT_SHA = '708e79f3b7b96a7e1581b4acf4c412233050a1832718ef7f06c8397db1b431c7'


class Image:
    def __init__(self, path):
        self.candidate = Path(path).read_bytes()
        if hashlib.sha256(self.candidate).hexdigest() != EXPECT_SHA:
            raise SystemExit('unexpected input firmware (addresses are for GR IIIx 1.60 fwdc243b.bin only)')
        info = inspect_container(self.candidate)
        self.original, _ = decode_payload(self.candidate[128:info['payload_end']], info['decoded_size'])
        rows = {r['name']: r for r in section_rows(self.original)}
        self.rtos0 = rows['RTOS']['start'] + 16
        self.rtos_end = rows['RTOS']['end']
        self.target = bytearray(self.original)
        self.sections = rows
        self.appended_span = None

    def off(self, addr):
        if DDST <= addr < DDST + DLEN:
            addr = DSRC + addr - DDST
        o = self.rtos0 + addr - BASE
        assert self.rtos0 <= o < self.rtos_end
        return o

    def _interval(self, addr, size):
        if not isinstance(size, int) or size < 0:
            raise ValueError('invalid memory interval size')
        if DDST <= addr < DDST + DLEN and addr + size > DDST + DLEN:
            raise ValueError('access crosses initialized RAM mapping')
        offset = self.off(addr)
        if offset + size > self.rtos_end:
            raise ValueError('access crosses RTOS end')
        return offset

    def read(self, addr, n):
        offset = self._interval(addr, n)
        return bytes(self.target[offset:offset + n])

    def write(self, addr, data):
        offset = self._interval(addr, len(data))
        self.target[offset:offset + len(data)] = data

    def word(self, addr): return struct.unpack('<I', self.read(addr, 4))[0]

    def append_rtos(self, size):
        """Grow the RTOS payload before patching; keep all existing runtime VAs."""
        if self.appended_span is not None or self.target != self.original:
            raise ValueError('RTOS must be reserved once, before patch writes')
        if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or size % 0x6000:
            raise ValueError('RTOS growth must be a positive multiple of 0x6000')
        start = BASE + self.rtos_end - self.rtos0
        if start + size >= DDST:
            raise ValueError('appended RTOS reaches initialized RAM')
        boundary = self.rtos_end
        self.target[boundary:boundary] = bytes(size)
        struct.pack_into('<I', self.target, self.rtos0 - 4, boundary - self.rtos0 + size)
        for name, row in self.sections.items():
            if row['start'] >= boundary:
                row['start'] += size
                row['end'] += size
            elif name == 'RTOS':
                row['end'] += size
                row['payload_bytes'] += size
        self.rtos_end += size
        self.appended_span = (start, start + size)
        return self.appended_span

    def rtos(self): return bytes(self.target[self.rtos0:self.rtos_end])

    def build(self):
        tgt = repair_last_word(bytes(self.target))
        assert sum32(tgt) == 0
        payload, report = _repack_frames(self.candidate, self.original, tgt, growth=self.appended_span is not None)
        out = framed_container(self.candidate, payload, tgt)
        return out, report


RECORDS = 0x55018D94                       # per-slot look record table (RAM, ROM-initialised)
SLOT = dict(standard=11, vivid=12, monotone=13, soft_mono=14, hard_mono=15, hicon_bw=16,
            positive=17, bleach=18, retro=19, hdr=20, cross=21, negative=25)


def set_look_matrix(img, slot, m):
    """m: 3x3 floats, rows=output R,G,B. Stored s16 Q13 row-major."""
    rec = img.word(RECORDS + 4 * slot)
    ptr = img.word(rec + 4)
    vals = [round(v * 8192) for row in m for v in row]
    assert all(-32768 <= v < 32768 for v in vals)
    img.write(ptr, struct.pack('<9h', *vals))
    return ptr