"""Offline GR III fw 2.10 look-patch builder (proof of concept, never touches a camera)."""
import sys, struct, hashlib
import codec_path  # noqa: F401  (gr4_editor from the gr-custom-tool submodule)
from gr4_editor.codec.container import inspect_container, repair_last_word, sum32
from gr4_editor.codec.frames import decode_payload, section_rows, framed_container
from gr4_editor.firmware import _repack_frames

BASE, DSRC, DDST, DLEN = 0x53000000, 0x5407B540, 0x55000000, 0x3A080
EXPECT_SHA = 'd6a3c9c288d784080e7b283222ecdd8752adfeed6faa36dab44f73115354bfd4'

class Image:
    def __init__(self, path):
        self.candidate = open(path, 'rb').read()
        if hashlib.sha256(self.candidate).hexdigest() != EXPECT_SHA:
            raise SystemExit('unexpected input firmware (addresses are for GR III 2.10 fwdc239b.bin only)')
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

# --- look helpers -------------------------------------------------------
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

if __name__ == '__main__':
    img = Image(sys.argv[1])
    # demo: warm, slightly muted "portra-like" matrix on the Retro slot
    m = [[1.10, -0.05, -0.05], [0.02, 0.95, 0.03], [-0.04, 0.02, 0.92 + 0.10]]
    p = set_look_matrix(img, SLOT['retro'], m)
    out, rep = img.build()
    open(sys.argv[2], 'wb').write(out)
    print('patched matrix at', hex(p), rep)
