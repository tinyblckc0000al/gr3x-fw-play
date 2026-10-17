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
camera. B2.4.1 has no new camera test evidence; B2.4 camera samples remain
historical evidence only. Linear reference scanning does not prove the absence
of indirect references, and the allocation ledger comes from the builder.
Some HDF-state and IIIx certification resources are still reused. The new fix
preserves crop indicators and does not establish HDF compatibility.
