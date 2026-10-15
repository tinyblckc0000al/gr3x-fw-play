# Source build and self-tests

[中文](BUILD.md) | [English](BUILD.en.md)

[Overview](../../README.en.md)

Run commands from the repository root. Tested environment: Apple Silicon macOS, Python 3.14, Homebrew LLVM and the system `DIN Condensed Bold.ttf` font. Other environments are untested.

## Default firmware build and self-tests

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

### 3. Build default B2.4

Leave `presets.json` and `fits/` unchanged:

```sh
mkdir -p workspace/b2_iiix/out
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets.json workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

Outputs are the BIN and its `.report.json`. Do not use files left behind by a failed build.

### 4. Run self-tests

```sh
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

Checks cover file integrity, modified regions and allocation bounds, menu/playback mappings, ARM emulation regression, fault injection and deterministic rebuilding. All stages must report `PASS` with exit code 0; failure, timeout, skipped stages or interruption do not count as a pass.

- Reports: `workspace/b2_iiix/logs/qualification-*`.
- Default timeout is 1800 seconds per stage; adjust with `--timeout`.
- Do not use `python -O` or `PYTHONOPTIMIZE`, which disable assertions.
- See the [README checksum section](../../README.en.md#file-checksum); do not change the expected hash to bypass checks.

After default B2.4 passes, copy the output as `fwdc243b.bin` and follow the [installation instructions](../../README.en.md#firmware-installation). Computer-side checks do not replace camera self-tests.

### 5. Camera self-test reference

Check shortcut and MENU selection, RAW+JPEG with each preset, playback identification, file reading on a computer, factory presets and in-camera RAW development, plus repeated switching and power cycles. Retain configuration, reports and samples if problems occur.

These are personal-project self-test references, not a claim of full coverage. Current feedback comes from one standard IIIx; retained samples cover seven added presets. Other bodies and long-term stability are untested.

## Custom presets

### Configuration files and editable fields

`presets.json` only maps tone numbers to files in `fits/`. Each recipe file contains curves and color parameters; its `preset` block defines `name`, `icon_label`, `icon_rgb` and `full_curve`. Icon IDs are assigned by the build code.

- Keep keys `25–32` and eight slots; the configuration loader currently requires this exact range.
- Icon labels accept 1–4 printable ASCII characters; colors are three integers from 0 to 255. Changing the template shape requires source changes.
- Changes to names, colors or curves change the file hash. `verify_release.py` accepts only default B2.4; it is not a general custom-firmware verifier. Do not replace its expected hash to bypass checks.

### Editing icons and configuration

An icon ID is a lookup number in the code; its appearance is pixel data generated from the recipe. Shooting and playback use the same `ICON_IDS`. Changing a name, label or color does not require changing an ID.

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

This only generates a candidate. The default self-test entry point is frozen to B2.4 and rejects changed builds. Full custom-build checks remain incomplete; a successful build does not make it ready to install. New recipe creation and internal parameter editing are outside this guide's scope.

## Implementation and extension constraints

### How the implementation works

The implementation reuses the stock Image Control framework: selected legacy record slots become added preset records with their own color parameters, names, icons and mappings. The menu fix updates the `GetMaxCount` limit; the playback fix extends the three mappings from EXIF to playback enum, display tone and icon while retaining stock entries. Added code and data use designated space, then the firmware is repacked and its checksums updated, rather than appending data to the BIN.

### Adding more slots (advanced)

These notes apply to implementation changes or firmware ports; default eight-preset builds need no changes. Addresses identify locations used by the current patch, not generic file offsets. Recheck instructions and references when porting.

#### 1. Record slots and configuration

`make_slots15.py` uses these legacy slots, copying the shared Standard record and writing a separate color matrix for each added recipe:

```python
LEGACY_SLOTS = (1, 2, 3, 4, 5, 7, 9, 8, 6)
assert 1 <= n <= len(LEGACY_SLOTS)
```

These are only nine candidate positions listed by the underlying patch. `presets_config.py` currently accepts exactly eight presets with keys `25–32`. A ninth requires checking strings, icons, curve space and every mapping; the list does not establish that one more preset can simply be added. More than nine requires a new record-storage design.

#### 2. Icon resources and compatibility

```python
ICON_IDS = (0x05, 0x06, 0x07, 0x1D, 0x2D, 0x2E, 0x2A0, 0x2A1, 0x2A2)
NEW_ICON0, ICON_BOUND = 0x2A0, 0x29E
```

According to the existing source identification, the first six IDs reuse HDF on/off states, IIIx certification marks and TELE/71mm crop icons; the last three use added descriptors. Default eight-preset builds use the first eight IDs.

Patches route new IDs through three known consumers: icon width, height and drawing. Extensions must check other direct table indexing and upper-bound checks. HDF and other models may actively use the repurposed icons, so these changes cannot simply be copied over; effects can extend beyond the added preset icons.

#### 3. IDs, counts and playback

Custom 1/2 use display tones 23/24; added films start at 25. The default eight use photo ImageTone codes `0x10C–0x113` (268–275). Display tones, photo codes and icon IDs are distinct identifiers.

| Patch location | Purpose |
|---|---|
| `0x532C2ACC` | Count instruction within `GetCount` for the shooting list; not the function entry |
| `0x532C2B7C` | `GetMaxCount` for the MENU list |
| `0x53283C08` | RAW-development list count |

Count changes also require index↔tone tables, EXIF writing/parsing and the three playback mappings: EXIF → playback enum → display tone → icon. A count-only change may expose an entry without making selection or playback work. `12 + m` excludes the two Custom options; the corresponding full list count is `12 + m + 2`. Do not interchange these expectations.

#### 4. Space budget and packing

B2.4 defines two half-open `PRESERVE_SPANS` ranges:

| Range | Total capacity |
|---|---|
| `0x53D453F8–0x53D45CB0` | 2232 bytes |
| `0x53D39C8C–0x53D3A588` | 2300 bytes |

These are total capacities, **not remaining free space**. Three-channel knot curves take 198 bytes; three-channel `full_curve` data takes 1536 bytes. Tables, alignment and other allocations consume additional space. Hook code and icon pixels also have their own borrowed regions; their capacities cannot be pooled as freely interchangeable space. Use the build report and actual allocator results.

Stock code may read apparently empty regions. Do not enlarge the allocation areas without auditing references and read ranges. Builds preserve section layout through decoding, modification, repacking and checksums; equal file lengths do not establish valid contents.

#### 5. Factory-mode regression and verification

Added recipes use curve-table pointers. The preserve path restores shared pointers and retains the stock branch for tone 21 (Cross Process), preventing the previous film’s state from affecting later factory-mode rendering. After changes, check transitions from a film to Cross Process and then other factory modes, not just a single isolated render.

Extensions also require configuration-specific mapping, boundary, factory-mode and emulation tests. `verify_release.py` identifies default B2.4 by its fixed SHA256 and rejects changed builds. Editing expected counts or substituting a hash does not replace full custom-build verification.
