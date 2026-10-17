# Verification guide

## Scope

This guide covers the default eight-preset GR IIIx 1.60 build. The current
verifier accepts only the frozen B2.4.1 BIN; custom recipes, additional slots and
other firmware versions require their own qualification. Do not replace the
expected hash to bypass a failing check.

Version-specific results, asset hashes and logs are available in the
[B2.4.1 release](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4.1).
The separate [camera record](hardware-b241.json) states the scope of user feedback.
Use the release tag to reproduce its original source and verification records.

## Run the checks

Prepare the stock firmware, default recipes and dependencies using the
[build guide](../../docs/guides/BUILD.en.md). Run from the repository root:

```sh
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets.json workspace/b2_iiix/out/fwdc243b-b241.bin
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b241.bin
```

The verifier prints the report path under `workspace/b2_iiix/logs/qualification-*`.
Keep `report.json` and every stage log. The report records firmware and source
fingerprints, dependency versions and eight stages:

| Stage | Checks |
|---|---|
| `selftest` | Checker, builder-resource policy and release-evidence rejection tests |
| `structure` | Frozen artifact identity, checksums, mappings and allowed change ranges |
| `mutations` | Deliberate instruction, mapping and protected-region errors are rejected |
| `playback` | Playback parsing and icon selection in the final BIN |
| `crop_icons` | Factory icon preservation, lookup/dimension emulation, film-icon consistency and fault injection on crop and non-crop resources |
| `references` | Bounded stock reference scan of reserved spans |
| `rebuild` | Byte-identical rebuild with tracked allocations and writes |
| `regression` | Functional emulation of menus, presets and processing paths |

Diagnostic `--stage` runs do not produce complete qualification. A timeout,
missing stage or partial run is a failure to qualify.

## Acceptance criteria

| Evidence | Required condition | Assessed by |
|---|---|---|
| Automated qualification | Exit code 0, final report `PASS`, all eight stages `PASS` | `verify_release.py` |
| Change-impact review | Identify changed resources, known existing/new consumers, preservation requirements and unresolved assumptions | Maintainer; not inferred by the tools |
| Camera acceptance | Test the affected behavior and existing consumers on the exact BIN; record model, date, hash, results and untested scenarios | Tester and maintainer; not performed by the emulator |
| Evidence consistency | Complete qualification, unchanged qualified sources, committed source/feedback records and matching artifact hashes | `check_release.py` |

Use the [camera checklist](../../docs/guides/BUILD.en.md#5-camera-self-test-reference)
as a baseline and add scenarios identified by the impact review. Record each
scenario as passed, failed or not run. An overall user-reported pass does not
establish that every checklist item was exercised. The maintainer must assess
whether the evidence is sufficient for the stated release scope.

### Release sequence

1. Complete the impact review, automated qualification and scoped camera acceptance.
2. Commit the qualified sources and camera record. Run the consistency check,
   replacing the report path with the one printed by the verifier:

   ```sh
   venv/bin/python workspace/b2_iiix/check_release.py workspace/b2_iiix/out/fwdc243b-b241.bin --report workspace/b2_iiix/logs/qualification-YYYYMMDD/report.json
   ```

3. Require exit code 0 and retain the JSON receipt. It binds the source commit,
   BIN, report and camera-record hashes. It checks consistency and the presence
   of feedback; it does **not** assess test completeness or camera safety.
4. Package the exact accepted BIN with checksums and evidence, then tag the
   receipt's commit. Re-download uploaded assets and verify hashes, ZIP contents
   and equality with the accepted BIN before announcing completion.

Changes to fingerprinted sources/configuration require new qualification.
This guide itself is fingerprinted: editing it makes an earlier report stale
for the new checkout, but does not invalidate the archived release at its tag.
Any BIN change requires renewed camera acceptance; an identical BIN retains
only the scope of its existing camera evidence.

## Resource policy and limitations

Factory icon resources are occupied by default. The builder rejects unapproved
reuse, duplicate IDs and gaps in added descriptors before patching. The verifier
compares factory pointers/descriptors against stock independently of the
builder's ID list and checks the complete ICONBIN change range.

| Resource, IIIx 1.60 | Policy |
|---|---|
| `0x05–0x07` | Existing HDF-state reuse exception; HDF behavior remains unverified |
| `0x1D` | Existing certification-artwork reuse exception, including backing pixels for added icons |
| Remaining factory IDs through `0x29E`, plus gap `0x29F` | No reuse approval; crop/TELE indicators `0x2C–0x2E` must be preserved |
| Added IDs from `0x2A0` | Unique and contiguous within the allocated descriptor table |

An exception records an existing tradeoff, not proof of harmlessness. New reuse
requires reviewing original consumers, model/version and affected states;
unknown ownership is not approval. Matching addresses across models does not
establish equivalent resource use. Broader memory checks retain their separate
allocation, protected-window and reference-scan requirements.

The report's `hardware: NOT_TESTED` describes the automated runner; camera
feedback is separate. Linear scanning cannot exclude all indirect references,
and the allocation ledger is builder-derived. Offline success does not prove
RAW/DNG cleanliness, HDF/Urban compatibility or long-term stability. Preserve
these boundaries in release claims.
