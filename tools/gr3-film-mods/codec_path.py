"""Puts gr-custom-tool (github.com/DoYitNow/gr-custom-tool, GPL-2.0) on sys.path for its `gr4_editor` firmware
container codec. Default: the git submodule third_party/gr-custom-tool next to this file; override with
$GR_CUSTOM_TOOL. Import it before any `gr4_editor` import."""
import os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PATH = os.environ.get('GR_CUSTOM_TOOL', os.path.join(ROOT, 'third_party', 'gr-custom-tool'))
if not os.path.isdir(os.path.join(PATH, 'gr4_editor')):
    raise SystemExit(f'gr4_editor not found in {PATH}: run `git submodule update --init` or set GR_CUSTOM_TOOL')
if PATH not in sys.path:
    sys.path.insert(0, PATH)
