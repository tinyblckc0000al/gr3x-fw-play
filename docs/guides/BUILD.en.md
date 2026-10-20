# Source build and self-tests

[中文](BUILD.md) · [Project overview](../../README.en.md)

For installation, download the [latest release](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/latest). This page covers source builds; a source ZIP is not installable firmware. Run commands from the repository root. Tested environment: Apple Silicon macOS, Python 3.14, Homebrew LLVM and the system DIN Condensed Bold font.

### 1. Install dependencies

```sh
brew install python@3.14 llvm
"$(brew --prefix python@3.14)/bin/python3.14" -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Prepare inputs

Place the extracted official firmware at these paths, using the exact versions:

| File | Version |
|---|---|
| `firmware-inputs/fwdc243b.bin` | [GR IIIx 1.60](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html) |
| `firmware-inputs/fwdc248b.bin` | [GR IV 1.11](https://www.ricoh-imaging.co.jp/english/support/digital/gr4_s.html), for parameter extraction only |

```sh
venv/bin/python scripts/prepare_inputs.py --iiix firmware-inputs/fwdc243b.bin --iv firmware-inputs/fwdc248b.bin
```

Stop if input hashes do not match; do not substitute versions or bypass checks. Official firmware is not included in the source repository.

### 3. Build the default firmware

Keep the default `presets.json` and `fits/` unchanged:

```sh
mkdir -p workspace/b2_iiix/out
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix workspace/b2_iiix/out/fwdc243b.bin
```

Outputs are the BIN and `.report.json`. Do not use artifacts left by a failed build.

### 4. Complete qualification

```sh
venv/bin/python workspace/b2_iiix/qualify_storage_candidate.py workspace/b2_iiix/out/fwdc243b.bin --output workspace/b2_iiix/logs/qualification-current
```

The output directory must not already exist. Five stages check structure, negative mutations, unit/native probes, functional regression and deterministic rebuilding. Require every stage PASS and exit code zero; retain the report and all logs. Missing stages, timeouts and interruptions are not passes. Do not substitute expected hashes to bypass failures.

The [verification guide](../../workspace/b2_iiix/VERIFICATION.md) defines the current artifact, camera feedback and publication gate. The historical full verify_release.py procedure does not qualify the current appended layout. Requalify source/configuration changes; changed firmware bytes require renewed camera acceptance. Compare downloaded and card copies against checksums from the same release.

### 5. Camera self-test reference

Check boot/shutdown, factory and added presets, Fn crop icons, JPEG/RAW capture and playback. Extensions also require continuous shooting, restart persistence, U modes and affected model-specific functions. Record pass/fail/not-run per scenario with the firmware hash. Emulation does not replace whole-camera loading and capture.

The present camera confirmation covers complete appended-area loading, power on/off and actual RAW/JPEG capture; see the [feedback record](../../workspace/b2_iiix/hardware-b242.json).

## Custom presets

### Configuration files and editable fields

`presets.json` only maps tone numbers to files in `fits/`. Each recipe file contains curves and color parameters; its `preset` block defines `name`, `icon_label`, `icon_rgb` and `full_curve`. Icon IDs are assigned by the build code.

- Keep keys `25–32` and eight slots; the configuration loader currently requires this exact range.
- Icon labels accept 1–4 printable ASCII characters; colors are three integers from 0 to 255. Changing the template shape requires source changes.
- Changes to names, colors or curves change the file hash. The release qualification targets the default released artifact; it is not a general custom-firmware verifier. Do not replace its expected hash to bypass checks.

### Editing icons and configuration

An icon ID is a lookup number in the code; its appearance is pixel data generated from the recipe. Shooting and playback use the same `ICON_IDS`. When changing a name, label or color, **do not change the ID**.

For example, edit these fields within the existing `preset` block of a `fits/*.json` file, leaving other fields unchanged:

```json
{
  "name": "Classic Neg",
  "icon_label": "NC",
  "icon_rgb": [60, 90, 140]
}
```

`icon_rgb` controls the **label text color**, not the background. The 40×40 film-strip outline uses the stock Positive Film icon as a template and is drawn by `make_icons.py::render`. Background, outline or dimension changes require source edits. `full_curve` selects curve storage and affects space usage; do not toggle it as an appearance setting.

Back up recipes before editing and retain data structure, array dimensions and required fields. The loader checks JSON, values and some capacity limits; it does not establish correct color or camera behavior. A source ZIP can be used for building, but cannot be installed as firmware; provide the inputs and dependencies listed in this guide.

### Reorder the default presets

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

This only generates a candidate. The release qualification targets the default released artifact and rejects changed builds. Full custom-build checks remain incomplete; a successful build does not make it ready to install. New recipe creation and internal parameter editing are outside this guide's scope.

## Implementation and storage constraints

The stock Image Control record and mapping framework remains in use. Added recipe data, curves and helper code live in appended RTOS storage. The current build adds 24 KiB; 70 allocations total 6236 bytes. Remaining capacity has separate purpose partitions and alignment constraints and is not a general expansion budget. Complete factory compensation tables, the old random path and MA storage are preserved.

Added display tones are 25–32 and photo ImageTone codes are 0x10C–0x113. Menu counts, EXIF, playback mappings and icons must agree. Configuration currently requires exactly eight presets; changing a count alone does not add slots. HDF-state and certification resources remain reused; independent resources are listed in TODO.

See the internal audit record (not published), build allocation report and source for exact addresses and original consumers. The two compensation-table spans borrowed by the older build are occupied and must not be reused. Other models or firmware versions require fresh identification and validation.
