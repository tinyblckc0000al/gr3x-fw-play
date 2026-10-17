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

### 3. Build default B2.4.1

Leave `presets.json` and `fits/` unchanged:

```sh
mkdir -p workspace/b2_iiix/out
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets.json workspace/b2_iiix/out/fwdc243b-b241.bin
```

Outputs are the BIN and its `.report.json`. Do not use files left behind by a failed build.

### 4. Run self-tests

```sh
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b241.bin
```

#### Test order

1. **Identify the target:** confirm the camera, stock version and exact BIN. For a source build, complete input validation and building above first. Modified configurations are not frozen B2.4.1 and cannot be cleared by its verifier.
2. **Run the single command above:** stages run as `selftest → structure → mutations → playback → crop_icons → references → rebuild → regression`. A failed stage stops the sequence; selected passing stages are not a complete result.
3. **Read the final report:** in the current run’s `report.json`, the top-level `status` and all eight `stages` must be `PASS`, with command exit code 0. One passing log line or a successful build is insufficient. `hardware: NOT_TESTED` means no camera testing was performed by the script.
4. **Stop on incomplete or failed results:** `FAIL`, `TIMEOUT`, `INCOMPLETE`, `NOT_RUN`, a remaining `RUNNING`, or no final report does not clear a file for installation. Read the first unsuccessful stage’s `.log`, resolve the cause and rerun the full sequence. Adjust timeouts if necessary; do not remove checks, change expected hashes or disable assertions.
5. **Check the actual card copy last:** after default B2.4.1 passes, follow the README to copy the BIN and verify its SHA256 on the card. Any subsequent configuration edit or regenerated file requires another verification run.

> Users installing the supplied release do not need a development environment to rerun emulation, but must check compatibility and the card’s BIN against the published hash. Download integrity is not a camera-safety guarantee.

The checks below target frozen B2.4.1; they do not establish safety for arbitrary modified builds.

| Check | Main failure it helps prevent | Implementation |
|---|---|---|
| Input hashes and original instruction bytes | Wrong firmware version or patch address | `prepare_inputs.py` and expected-byte checks before patch writes |
| Allocation bounds, overlaps, write ranges and protected regions | Overwriting stock code or ISP data, causing crashes, RAW corruption or image artifacts | `structure` and `rebuild` in `verify_release.py` |
| Stock address-reference scan | Treating referenced stock data as free space | `references`; linear scanning cannot rule out indirect references |
| Container checksums and section layout | Damaged packaging or changed layout preventing loading | `structure` |
| Menu counts, playback mappings and ARM emulation | Missing presets, blank icons, wrong branches or regressions in stock modes, including Cross Process | `playback`, `regression` |
| Fault injection and checker self-tests | Missed errors and false passes | `selftest`, `mutations`; limited to the injected cases |
| Deterministic rebuilding | Different results from identical configuration, or a release differing from the verified file | `rebuild`, compared with the frozen B2.4.1 hash |

All stages must report `PASS` with exit code 0; failure, timeout, skipped stages or interruption do not count as a pass. Allocation records come from the builder, and emulation covers selected paths rather than the full sensor, storage and real-time system. RAW/DNG integrity still requires camera capture and file inspection.

After downloading or copying to a card, use the README checksum instructions to check the BIN for a wrong or incomplete copy; this is separate from functional testing. The independent shutdown-image package requires separate checks of generated versus intended image bytes, format, dimensions, backup and repeat-execution protection. Readback and actual display must still be checked after installation.

- Reports: `workspace/b2_iiix/logs/qualification-*`.
- Default timeout is 1800 seconds per stage; adjust with `--timeout`.
- Do not use `python -O` or `PYTHONOPTIMIZE`, which disable assertions.
- See the [README checksum section](../../README.en.md#file-checksum); do not change the expected hash to bypass checks.

After default B2.4.1 passes, copy the output as `fwdc243b.bin` and follow the [installation instructions](../../README.en.md#firmware-installation). Computer-side checks do not replace camera self-tests.

#### Test reference

Paths below are relative to the repository root. “Runnable separately” does not mean a portable standalone file: apart from checker self-tests, most require repository modules, Python dependencies, specific firmware or recipes.

| File | What it investigates | Separate use and limits |
|---|---|---|
| `scripts/prepare_inputs.py` | Identity of the required IIIx / IV stock inputs and input preparation | **Runnable separately**; checks inputs, not the generated firmware |
| `workspace/b2_iiix/verify_release.py` | Complete computer-side checks and summary for default B2.4.1 | Preferred entry point; requires stock firmware, repository scripts and default recipes, and accepts only frozen B2.4.1 |
| `workspace/b2_iiix/check_release.py` | Release-evidence consistency check binding the complete report, committed sources, BIN and camera feedback | Run after qualification and committing; failures block publication. See [release sequence and resource policy](../../workspace/b2_iiix/VERIFICATION.md#release-sequence) |
| `workspace/b2_iiix/verification.py` | Reference, mapping, protected-region, allocation and write-range rules | Library without a standalone command; used by the verifier and unit tests |
| `workspace/b2_iiix/test_verification.py` | Whether constructed bounds, overlap and reference errors are detected | **Runnable separately** without a camera or firmware files; success validates only these checker test cases |
| `workspace/b2_iiix/test_icon_policy.py` / `test_release_gate.py` | Rejection of invalid builder resources and publication evidence | Included in the selftest stage; uses firmware inputs and a temporary Git repository |
| `workspace/b2_iiix/test_crop_icons.py` | Factory crop descriptors, dimensions and pixels; shared shooting/playback film icons | Requires the specified firmware and default B2.4.1; the full runner passes the actual candidate BIN |
| `workspace/b2_iiix/test_playback.py` | Playback parsing in the final BIN, with stock, added and boundary inputs | **Direct execution** uses the default B2.4.1 path in code; use the stage entry below for another path, not a BIN argument to unittest |
| `tools/gr3-film-mods/verify_slots16.py` | Emulated menu, icon, color-parameter, mode-transition and RAW-development regression | **Runnable directly** with stock BIN, candidate BIN and recipes in slot order; the complete entry point assembles these arguments. Direct runs require checking `FAIL` lines and final `ALL OK`, not exit code alone |
| `workspace/b2_iiix/verify_offline.py` | Additional container round-trip, change-distribution and selected stock/Cross Process render comparisons | Legacy diagnostic, not a complete gate. Samples only some modes; `FAILED` may not return a nonzero exit code, and some checksum calculations repair the checksum first, so they do not establish original-input checksum validity |

A passing `check_release.py` result establishes evidence consistency, not sufficient camera coverage. It does not replace manual impact review or camera acceptance. Use the corresponding tag to reproduce a published release. Changes to fingerprinted files in the current checkout, including `VERIFICATION.md`, require a new qualification report; do not reuse the archived report for changed sources.

To investigate a single stage, run from the repository root:

```sh
# Test the checker itself; the second command runs playback emulation only
venv/bin/python -m unittest discover -s workspace/b2_iiix -p 'test_verification.py'
# Diagnostic stage only: no complete report or other stages; partial success does not replace section 4
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b241.bin --stage playback
```

#### Minimum test coverage when extending or changing code

- **Files and writes:** input identity, original bytes, container/layout, every changed region, allocation bounds/alignment, protected regions and stock references.
- **Behavior and boundaries:** all added slots and stock modes; IDs/counts across shortcut, MENU, shooting, playback and in-camera RAW development; existing consumers of shared resources, such as Fn crop and status icons; valid limits, out-of-range inputs and state restoration when returning from film to stock modes.
- **Checker reliability and reproducibility:** deliberate corruption must be detected; identical inputs must rebuild identically; retain configuration, dependencies, BIN hashes and full logs.
- **Camera and file decoding:** follow the next section, capture RAW+JPEG for each preset, actually decode RAW files, and check playback, stock modes and power cycles. Computer-side tests cannot replace this step.

Adding slots, changing allocation layout or porting firmware requires reviewing addresses, capacity and expected results again. Record missing checks as uncovered; do not change a hash or reuse an old report to turn them into passes.

### 5. Camera self-test reference

Proceed in order and stop at the first abnormal result. Use a backed-up spare card and a full battery, and record existing settings first. Never interrupt power or remove the card during the firmware update.

| Order | Action | What to observe |
|---|---|---|
| 1 | After the update completes, start normally, open the shortcut and MENU → Image Control, and cycle Fn crop Off→50mm→71mm→Off | Both menus open and close; factory and added presets are selectable; crop icons remain complete and correct, without freezes or unexpected restarts |
| 2 | Capture one RAW+JPEG pair with a factory preset, review it and copy it to a computer | Both files open fully; actually decode the RAW rather than viewing only its embedded thumbnail |
| 3 | Capture one RAW+JPEG pair per added preset and record filenames and selections | Playback names, icons and visible parameters match; computer decoding shows no errors, obvious corrupt blocks or banding |
| 4 | Switch added preset → Cross Process → Standard and capture images; check in-camera RAW development | No obvious residual effects after returning to stock modes; development completes. Thumbnails or successful file writes alone are insufficient |
| 5 | Power off and on normally, then repeat menu entry and capture | Settings persist as intended, without recurring date setup, card errors or new freezes |

Keep configuration, reports, operation order and original problem files. Stop further capture tests on abnormalities and consult the README recovery section; do not interrupt an ongoing firmware update just because it seems slow. These observations detect only some problems and cannot establish completely clean RAW/DNG output or long-term stability.

These are personal-project self-test references, not a claim of full coverage. Historical B2.4 feedback comes from one standard IIIx; retained samples cover seven added presets. B2.4.1 received a user-reported camera pass for this icon fix on 2026-10-17, bound to the same BIN SHA256; individual results and new samples were not collected. Other bodies and long-term stability are untested.

### 6. Ask AI to help interpret results

Provide the camera and version, supplied release versus custom build, BIN SHA256, executed command, exit code, current `report.json` and the full log of the first unsuccessful stage. For camera issues, add the operation sequence, filenames and original RAW/JPEG files. Check logs for personal paths and images for metadata before sharing. A complete firmware upload is not needed initially; a single `PASS` screenshot is insufficient.

Suggested prompt:

```text
Analyze only the supplied reports, logs and corresponding code. Separate passed, failed, unexecuted and unconfirmed checks. First confirm that the camera, firmware hash and report refer to the same run, then identify the first abnormal result with evidence and suggest minimal diagnostic steps. Do not alter expected hashes, remove assertions or skip checks to manufacture a pass. Do not equate offline success with camera safety. If evidence is missing, list it rather than guessing the cause of hardware damage.
```

AI can help interpret evidence and investigate known problems, but cannot replace actual test execution. Camera testing still requires caution.

## Custom presets

### Configuration files and editable fields

`presets.json` only maps tone numbers to files in `fits/`. Each recipe file contains curves and color parameters; its `preset` block defines `name`, `icon_label`, `icon_rgb` and `full_curve`. Icon IDs are assigned by the build code.

- Keep keys `25–32` and eight slots; the configuration loader currently requires this exact range.
- Icon labels accept 1–4 printable ASCII characters; colors are three integers from 0 to 255. Changing the template shape requires source changes.
- Changes to names, colors or curves change the file hash. `verify_release.py` accepts only default B2.4.1; it is not a general custom-firmware verifier. Do not replace its expected hash to bypass checks.

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

This only generates a candidate. The default self-test entry point is frozen to B2.4.1 and rejects changed builds. Full custom-build checks remain incomplete; a successful build does not make it ready to install. New recipe creation and internal parameter editing are outside this guide's scope.

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
ICON_IDS = (0x05, 0x06, 0x07, 0x1D, 0x2A0, 0x2A1, 0x2A2, 0x2A3, 0x2A4)
NEW_ICON0, ICON_BOUND = 0x2A0, 0x29E
```

The current source still reuses HDF on/off states and the IIIx certification mark for the first four IDs; the remaining five use added descriptors. Default eight-preset builds use the first eight IDs. Old B2.4 used TELE/71mm IDs `0x2D/0x2E` for film icons, corrupting crop indicators; B2.4.1 preserves both factory resources.

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

B2.4.1 defines two half-open `PRESERVE_SPANS` ranges:

| Range | Total capacity |
|---|---|
| `0x53D453F8–0x53D45CB0` | 2232 bytes |
| `0x53D39C8C–0x53D3A588` | 2300 bytes |

These are total capacities, **not remaining free space**. Three-channel knot curves take 198 bytes; three-channel `full_curve` data takes 1536 bytes. Tables, alignment and other allocations consume additional space. Hook code and icon pixels also have their own borrowed regions; their capacities cannot be pooled as freely interchangeable space. Use the build report and actual allocator results.

Stock code may read apparently empty regions. Do not enlarge the allocation areas without auditing references and read ranges. Builds preserve section layout through decoding, modification, repacking and checksums; equal file lengths do not establish valid contents.

#### 5. Factory-mode regression and verification

Added recipes use curve-table pointers. The preserve path restores shared pointers and retains the stock branch for tone 21 (Cross Process), preventing the previous film’s state from affecting later factory-mode rendering. After changes, check transitions from a film to Cross Process and then other factory modes, not just a single isolated render.

Extensions also require configuration-specific mapping, boundary, factory-mode and emulation tests. `verify_release.py` identifies default B2.4.1 by its fixed SHA256 and rejects changed builds. Editing expected counts or substituting a hash does not replace full custom-build verification.

## If you are unsure, take it slowly: ask AI questions and cross-check the evidence. Unless replacing your GR is pocket change, caution pays off.
