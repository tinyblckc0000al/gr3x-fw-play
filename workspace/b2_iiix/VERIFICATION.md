# B2.4.2 verification

The default eight-preset GR IIIx 1.60 build uses a 24 KiB appended RTOS area.
B2.4.1's data spans overlap complete factory compensation-table read windows;
its historical reference-scan result is not clearance for those spans.

## Build and qualify

Run from the repository root after preparing the official firmware and dependencies
using the [build guide](../../docs/guides/BUILD.en.md).

```sh
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix workspace/b2_iiix/out/fwdc243b-b242.bin
venv/bin/python workspace/b2_iiix/qualify_storage_candidate.py workspace/b2_iiix/out/fwdc243b-b242.bin --output workspace/b2_iiix/logs/qualification-b242
```

Require final PASS and all five stages PASS with exit code zero:

| Stage | Checks |
|---|---|
| structure | Section contents, initialized-data mapping, complete protected windows, appended ownership and icon/playback mappings |
| mutations | Compensation-table changes and pointers escaping the appended area are rejected |
| unit_and_native_probes | Checker/release gate, alignment/bounds, section movement, icon preservation, original CPU upload buffers for all seven settings |
| regression | Menu, preset and processing emulation, including appended helper execution |
| deterministic_rebuild | Rebuilt BIN equals the qualified artifact byte for byte |

The native upload probe substitutes hardware helpers and compares submitted buffers;
it does not execute physical ISP transfers. Reports retain exact source fingerprints
and stage logs. A partial run or timeout is not complete qualification.

## Camera acceptance and release

[Camera feedback](hardware-b242.json) binds the tested BIN SHA256 and records the
user's 2026-10-17 confirmation: complete appended-area loading, power on/off and
actual RAW/JPEG capture. No new sample files were collected. Continuous shooting,
endurance, HDF/Urban-specific functions and all U-mode persistence paths are not
covered by that confirmation.

1. Complete qualification and review the changed consumers and allocations.
2. Record camera acceptance against the exact BIN and commit qualified sources.
3. Run the consistency gate:

```sh
venv/bin/python workspace/b2_iiix/check_release.py workspace/b2_iiix/out/fwdc243b-b242.bin --report workspace/b2_iiix/logs/qualification-b242/report.json --hardware workspace/b2_iiix/hardware-b242.json
```

4. Retain the gate receipt binding commit, qualification, BIN and camera record.
   Package that exact BIN, upload assets and verify downloaded hashes and ZIPs.

The gate checks evidence consistency, not camera safety or test completeness.
Any fingerprinted source change requires renewed qualification. A changed BIN
requires renewed camera acceptance. Identical BINs retain only the existing
camera confirmation's scope. Custom recipes, extra slots and other versions need
separate qualification; replacing expected hashes is not validation.

## Remaining resource limits

Factory crop/TELE IDs 0x2C–0x2E are preserved. IDs 0x05–0x07 still reuse HDF-state
resources; 0x1D reuses certification artwork and backing pixels. New IDs start at
0x2A0. This release does not restore those remaining reused resources or establish
HDF compatibility. Independent resources are recorded in TODO.

The automated report's hardware NOT_TESTED and publish_authorized false fields
refer to the offline runner; scoped human acceptance is recorded separately.
The allocation ledger is builder-derived. Preserving complete known stock tables
and original section contents is stronger than treating zero bytes as free space,
but does not establish universal firmware or model compatibility.

## Historical records

B2.4.1 qualification scripts and receipts remain available at its release tag.
Their frozen structure/reference stages target that historical BIN. B2.4.2 uses
qualify_storage_candidate.py; individual verify_release.py stages are diagnostic
helpers and are not a substitute for the complete five-stage qualification.
