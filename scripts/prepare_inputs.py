#!/usr/bin/env python3
"""Prepare ignored runtime inputs from user-supplied official firmware."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
FM = ROOT / 'tools/gr3-film-mods'
sys.path.insert(0, str(FM))
import codec_path
from gr4_editor.codec.container import inspect_container
from gr4_editor.codec.frames import decode_payload, section_rows

EXPECTED = {
 'iiix': '708e79f3b7b96a7e1581b4acf4c412233050a1832718ef7f06c8397db1b431c7',
 'iv': 'a2f664dfca034059eb0fd6e18ab08684c326b4a034d85c164dad7e1ec9b5655f',
}

def decode_checked(path, model):
 raw = path.read_bytes()
 if hashlib.sha256(raw).hexdigest() != EXPECTED[model]:
  raise ValueError(f'Unexpected {model} firmware SHA256; no files written')
 info = inspect_container(raw)
 decoded, _ = decode_payload(raw[128:info['payload_end']], info['decoded_size'])
 return decoded

def main():
 parser = argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--iiix', type=Path, required=True, help='Official GR IIIx 1.60 BIN')
 parser.add_argument('--iv', type=Path, required=True, help='Official GR IV 1.11 BIN for shared MA data')
 args = parser.parse_args()
 three = decode_checked(args.iiix, 'iiix')
 four = decode_checked(args.iv, 'iv')
 row = next(r for r in section_rows(three) if r['name'] == 'RTOS')
 values = struct.unpack_from('<37H', four, 0x1061A8C)
 g4 = {'bounds':list(values[:16]), 'control':list(values[16:]),
       'selectors':[0,1,2,2,2,3,4,5,5,5,6,7,8,8,8,9,10,11,11,11]}
 outputs = {FM/'work/fw/rtos.bin': three[row['start']+16:row['end']],
            FM/'work/ma_probe5/gr4_std_ma.json': json.dumps(g4).encode(),
            ROOT/'firmware/official-v160/fwdc243b.bin': args.iiix.read_bytes()}
 for path, data in outputs.items():
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_bytes(data)
 print('Prepared verified local inputs; firmware and extracted data remain git-ignored.')

if __name__ == '__main__':
 main()
