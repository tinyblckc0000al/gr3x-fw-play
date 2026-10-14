# Source build and self-tests

[中文](BUILD.md) | [English](BUILD.en.md)

[Overview](../../README.en.md)

Run commands from the repository root. Tested environment: Apple Silicon macOS, Python 3.14, Homebrew LLVM and the system `DIN Condensed Bold.ttf` font. Other environments are untested.

## 1. Install dependencies

```sh
brew install python@3.14 llvm
"$(brew --prefix python@3.14)/bin/python3.14" -m venv venv
venv/bin/pip install -r requirements.txt
```

## 2. Prepare inputs

Place the extracted official firmware at these paths, using the exact versions:

| File | Version |
|---|---|
| `firmware-inputs/fwdc243b.bin` | [GR IIIx 1.60](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html) |
| `firmware-inputs/fwdc248b.bin` | [GR IV 1.11](https://www.ricoh-imaging.co.jp/english/support/digital/gr4_s.html), for parameter extraction only |

```sh
venv/bin/python scripts/prepare_inputs.py --iiix firmware-inputs/fwdc243b.bin --iv firmware-inputs/fwdc248b.bin
```

Stop if input hashes do not match; do not substitute versions or bypass checks. Official firmware is not included in the source repository.

## 3. Build default B2.4

Leave `presets.json` and `fits/` unchanged:

```sh
mkdir -p workspace/b2_iiix/out
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets.json workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

Outputs are the BIN and its `.report.json`. Do not use files left behind by a failed build.

## 4. Run self-tests

```sh
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

Checks cover file integrity, modified regions and allocation bounds, menu/playback mappings, ARM emulation regression, fault injection and deterministic rebuilding. All stages must report `PASS` with exit code 0; failure, timeout, skipped stages or interruption do not count as a pass.

- Reports: `workspace/b2_iiix/logs/qualification-*`.
- Default timeout is 1800 seconds per stage; adjust with `--timeout`.
- Do not use `python -O` or `PYTHONOPTIMIZE`, which disable assertions.
- See the [README checksum section](../../README.en.md#file-checksum); do not change the expected hash to bypass checks.

After passing, follow the [installation instructions](../../README.en.md#firmware-installation). Computer-side checks do not replace camera self-tests.

## Camera self-test reference

Check shortcut and MENU selection, RAW+JPEG with each preset, playback identification, file reading on a computer, factory presets and in-camera RAW development, plus repeated switching and power cycles. Retain configuration, reports and samples if problems occur.

These are personal-project self-test references, not a claim of full coverage. Current feedback comes from one standard IIIx; retained samples cover seven added presets. Other bodies and long-term stability are untested.

## Reorder the default presets

`presets.json` maps eight slots to files in `fits/`. Copy the configuration and swap filenames, keeping keys `25–32` and the same eight presets. For example, swap the first two:

```json
{
  "25": "ektar100.json",
  "26": "portra400.json",
  "27": "gold200.json",
  "28": "pro400h.json",
  "29": "vision3-250d.json",
  "30": "classic-negative.json",
  "31": "vision3-500t.json",
  "32": "velvia50.json"
}
```

Save as `workspace/b2_iiix/presets-example.json`:

```sh
venv/bin/python workspace/b2_iiix/presets_config.py workspace/b2_iiix/presets-example.json
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets-example.json workspace/b2_iiix/out/fwdc243b-example.bin
```

This only generates a candidate. The default self-test entry point is frozen to B2.4 and rejects changed builds. Full custom-build checks remain incomplete; a successful build does not make it ready to install. New recipe creation and internal parameter editing are outside this guide's scope.
