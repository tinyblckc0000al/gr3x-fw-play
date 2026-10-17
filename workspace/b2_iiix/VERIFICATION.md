# B2.4.1 verification

The default eight-preset GR IIIx 1.60 build is frozen to SHA256
`88829723a3a1f8edfe70c0153c636d51fda2bdd2aac75641195142560b7e8128`.
The original firmware, default recipes and build dependencies are required.

From the repository root:

```sh
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets.json workspace/b2_iiix/out/fwdc243b-b241.bin
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b241.bin
```

The runner stops on failure and records eight stages: checker self-tests,
structure/checksums, semantic mutations, final-image playback, crop-icon
preservation, stock reference scanning, tracked deterministic rebuild and
functional regression. Success requires exit code 0, a final `PASS` report and
all eight stages marked `PASS`. A timeout or partial run is not a pass.

Independent playback expectations retain the factory mapping and require the
eight film icons `05, 06, 07, 1D, 2A0, 2A1, 2A2, 2A3`. The crop stage executes
the firmware's descriptor lookup and dimension getters, preserves factory
`2C/2D/2E` descriptors and pixels, checks all other factory descriptors except
the four intentionally reused resources, checks the complete ICONBIN change
range and compares shooting and final-image playback icon selection. It also
checks known ISP windows. These checks supplement the frozen hash rather than
merely changing the accepted fingerprint.

The default artifact is `out/fwdc243b-b241.bin`. Standalone crop tests can select
a different path with `GR3X_ICON_CANDIDATE`; the full runner binds the test class
to its actual candidate. Old B2.4 fails the new crop-resource checks. To
reproduce the old release and its old verifier, use its `b2.4` source tag.

Reports include candidate/input/source fingerprints and dependency versions.
Their `hardware: NOT_TESTED` field means the runner has not tested a physical
camera. Separate user feedback is recorded in [hardware-b241.json](hardware-b241.json):
the user reported a camera pass for this fix on 2026-10-17, after the supplied
BIN was copied to the card and its SHA256 verified. Individual checklist results
and new RAW/JPEG samples were not collected. B2.4 samples remain historical
evidence only. Linear reference scanning does not prove the absence
of indirect references, and the allocation ledger comes from the builder.
Some HDF-state and IIIx certification resources are still reused. The new fix
preserves crop indicators and does not establish HDF compatibility.

## Process correction: ownership, independent checks, evidence continuity

The B2.4 defect exposed three process gaps, not merely a missing crop test:
an occupied resource was treated as reusable across models; the checker accepted
the builder's mistaken interpretation; successful checks were not sufficient
to establish coverage of existing consumers. Address compatibility alone does
not establish resource ownership or runtime behavior.

| Invariant | Enforcement | Acceptance test |
|---|---|---|
| Factory resources are occupied by default | `make_slots15.validate_icon_ids` allows only the explicit exceptions below, rejects duplicate IDs and sparse added descriptors before patching | Legacy crop IDs, unrelated stock IDs, unknown IDs, duplicates, gaps and capacity errors must leave the image unchanged |
| Existing consumers remain intact | Independent stock comparison covers every factory catalog pointer and descriptor except documented exceptions; exhaustive ICONBIN range checking and actual lookup emulation remain required | Overwrite dimensions, pixel offsets or pointers for both crop and non-crop resources; the checker must reject them without relying on SHA/checksum failure |
| A result belongs to one artifact and source state | `check_release.py` requires all stages, matching BIN/stock hashes, a complete unchanged source inventory, committed sources and a matching camera record | Reject partial/failed runs, a different camera BIN, missing feedback, source drift and binary drift |

The old crop collision is one regression witness for these invariants. Do not
grow a list of allowed stock IDs simply to make a failing test pass. Any new
exception needs a documented original consumer, target model/version, affected
states and independent validation of those consumers. Unknown ownership blocks
reuse. Broader storage/code allocation audits remain governed by the existing
protected windows and allocation/reference checks, not by this icon policy.

### Current resource ownership (IIIx 1.60)

| Resource | Original owner / current policy |
|---|---|
| `0x05–0x07` | HDF state icons; existing explicit reuse exception, no HDF compatibility claim |
| `0x1D` | IIIx certification artwork; existing explicit reuse exception and backing pixels for added film icons |
| `0x2C–0x2E` | Crop/TELE indicators; preserved along with all other factory IDs |
| Other factory IDs through `0x29E`, and gap `0x29F` | No reuse approval; do not infer availability from lack of observed references |
| IDs from `0x2A0` | Added descriptors; must be unique and contiguous to fit the allocated table |

This records known exceptions rather than asserting they are harmless. Removing
HDF/certification reuse is separate work requiring a new allocation audit and
camera validation; this release does not change those resources further.

### Release sequence

1. Identify the changed resource and **all known old and new consumers**. Define
   invariants before implementation; derive preservation expectations from stock,
   not from the patcher's configuration. List unknowns rather than assuming them safe.
2. Run the complete `verify_release.py` command above. The self-test stage includes
   builder-policy and release-evidence tests; the icon stage includes deliberate
   failures on unrelated stock resources as well as the historical defect.
3. Copy the candidate to the card, verify its SHA256, and record camera feedback
   against that hash. Use [BUILD.md](../../docs/guides/BUILD.md#5-相机自测参考)
   for the baseline and add checks for affected existing consumers. Record each
   scenario as passed, failed or not run; overall feedback is not proof that every
   checklist item passed. Any BIN change invalidates prior camera acceptance.
4. Commit the qualified sources and camera record, then run (replace the report path):

   ```sh
   venv/bin/python workspace/b2_iiix/check_release.py workspace/b2_iiix/out/fwdc243b-b241.bin --report workspace/b2_iiix/logs/qualification-YYYYMMDD/report.json
   ```

   A nonzero exit blocks publication. A receipt binds source commit, firmware,
   qualification report and camera-record hashes. Source/config changes require
   requalification; unchanged BIN bytes retain the same scoped camera evidence.
5. Package that exact BIN, include the report/logs, camera record and gate receipt,
   generate SHA256SUMS, and tag the receipt's source commit. After upload,
   re-download all assets, verify their hashes/ZIP contents and compare the BIN
   to the accepted candidate. A report `PASS` is scoped evidence, not universal safety.

No new framework or broad refactor is required: these gates extend the existing
builder, independent checker and eight-stage runner.
