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
import codec_path  # noqa: F401  (gr4_editor from third_party/gr-custom-tool)
from gr4_editor.codec.container import inspect_container, repair_last_word, sum32
from gr4_editor.codec.frames import decode_payload, section_rows, framed_container
from gr4_editor.firmware import _repack_frames

BASE, DSRC, DDST, DLEN = 0x53000000, 0x5407B540, 0x55000000, 0x3A080
EXPECT_SHA = '708e79f3b7b96a7e1581b4acf4c412233050a1832718ef7f06c8397db1b431c7'


class Image:
    def __init__(self, path):
        self.candidate = open(path, 'rb').read()
        if hashlib.sha256(self.candidate).hexdigest() != EXPECT_SHA:
            raise SystemExit('unexpected input firmware (addresses are for GR IIIx 1.60 fwdc243b.bin only)')
        info = inspect_container(self.candidate)
        self.original, _ = decode_payload(self.candidate[128:info['payload_end']], info['decoded_size'])
        rows = {r['name']: r for r in section_rows(self.original)}
        self.rtos0 = rows['RTOS']['start'] + 16
        self.rtos_end = rows['RTOS']['end']
        self.target = bytearray(self.original)

    def off(self, addr):
        if DDST <= addr < DDST + DLEN:
            addr = DSRC + addr - DDST
        o = self.rtos0 + addr - BASE
        assert self.rtos0 <= o < self.rtos_end
        return o

    def read(self, addr, n): o = self.off(addr); return bytes(self.target[o:o + n])
    def write(self, addr, data): o = self.off(addr); self.target[o:o + len(data)] = data
    def word(self, addr): return struct.unpack('<I', self.read(addr, 4))[0]

    def rtos(self): return bytes(self.target[self.rtos0:self.rtos_end])

    def build(self):
        tgt = repair_last_word(bytes(self.target))
        assert sum32(tgt) == 0
        payload, report = _repack_frames(self.candidate, self.original, tgt, growth=False)
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