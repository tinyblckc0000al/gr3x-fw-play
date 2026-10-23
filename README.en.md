# gr3x-fw-play

## 2026-10-23 update: switch to the plugin route

### Installation

1. Flash stock GR IIIx 1.60 first.
   - This removes modifications in the project's B2.4.x firmware (added presets, icons/ratios, etc.). To keep those effects, reflash B2.4.x; it cannot coexist with the plugin build.
2. Download [GRPlay plugin v0.2](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/plugin-v0.2), extract it and copy the package to the SD card root.
3. Power off, hold MENU and press Power; wait for Complete and automatic shutdown.
4. Power on normally and wait 30-60 s.
5. After the indicator blinks continuously, press ADJ; the added menu should appear.

Notes:

- The new route does not depend on B2.4.x; the two cannot coexist.
  - B2.4.2 appended blob: 0x540B55C0..0x540C9604; GRKit appended area: 0x540B6000..0x540BE000. They overlap.
- B2.4.x remains available as a separate flash; old packages are kept, not overwritten or deleted.

### What is added compared with the project's previous firmware (B2.4.x)

- 9:16 / 3:4 / XPan ratios, composition guides, date stamp and grain;
- five soft-focus levels and four glow levels, adjusted with a Fn slider;
- 18 in-camera film effects (including the previous 8 presets);
- improved menu key interaction;
- the stock Clarity table is restored at install time; the stock firmware is not modified.

### Source and advantages

Built on [GRKit v1.0.0](https://github.com/ahonn/grkit):

- Linux TTL/Script installer writes the private tail through /dev/mem;
- RTOS fixed tail, private ADJ menu and picture.encode chain;
- SD packages, build/verification and per-plugin enable/disable.

Advantages of the approach:

- no firmware flashing and low recovery cost;
- reuses the stock RTOS menu, image processing and JPEG encoder;
- fixed tail plus a few hooks keeps the change small;
- plugins can be enabled, disabled and rolled back independently;
- Linux already provides the filesystem, eMMC and script entry points.

### Other options dropped

#### Why firmware patching stopped

B2.4.x modified the firmware directly, tying features to a firmware version and storage layout; every official update needed re-adaptation, and recovery after a flash was not controllable.

The plugin route does not modify firmware, installs from SD and restores on reboot; features can be tested and rolled back individually.

The B2.4.x patch layer and modified RTOS image were dropped. Reused from the B2.4.x work:

- curves/matrices/parameters for the 8 presets;
- image-processing, storage-layout and effect-verification experience;
- installation, rollback and camera-test procedures.

Direct RTOS attempts included B2.4.x firmware images, preset slots, icons and storage layout, plus clarity/parameter and internal-storage calls.

A full RTOS replacement requires extensive per-version reverse engineering, with no controllable recovery path; the stock RTOS already provides the menu and image processing, so replacement has low benefit.

Final layout:

- Linux handles installation, the filesystem and rollback;
- RTOS only hosts the menu and necessary hooks such as picture.encode;
- image processing still runs in the stock RTOS.

#### Why internal-storage persistence is deferred

The stock I: volume has a file service, but calling it during installation interrupts the installer; create/truncate/append semantics, power-loss sync and path boundaries are unverified.

Direct writes risk losing photos or damaging the system area. Settings remain in RAM and reset on reboot; SD configuration comes first, and internal storage will only be probed under control.

### Possible future improvements (not promised)

- [ ] settings persistence across reboots
- [x] native menu experience (v0.2)
- [x] soft focus / glow tuning (v0.2)
- [ ] GR2 color

## Previous firmware (B2.4.2)

> **B2.4.2 storage repair:** added recipes and helper code now use a separate appended area, restoring factory compensation tables. Automated checks and user-reported camera loading, power cycling and RAW/JPEG capture passed. B2.4.1 has a layout conflict; use this release.


[中文](README.md) | [English](README.en.md)

**22 Image Controls on the GR IIIx: 12 factory presets + 2 custom options + 8 extra film looks.** All original modes are retained, and the eight added preset slots can be replaced. Use the default recipes or rebuild the firmware with a different configuration. Shutdown-image customization is a separate feature.

- **Use the eight presets**: download the [ready-made firmware](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/latest) and follow the [installation steps](#firmware-installation). No development tools needed.
- **Change only the shutdown image**: use the [separate image package](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0). Installed separately; the camera’s built-in script execution feature (Script) must be enabled first. Copying an image to the card alone will not install it.
- **Change recipes, names or icons**: see [custom presets](docs/guides/BUILD.en.md#custom-presets) for rebuilding instructions and custom-build verification limits.
- **Build or explore the code**: see [source build and self-tests](docs/guides/BUILD.en.md).

### What's new here

Built on gr3-film-mods, this project adapts the preset expansion to **GR IIIx 1.60**, fixes added-preset selection and playback identification, and provides configurable builds with repeatable self-checks. Upstream code and data sources are listed in [Open-source references](#open-source-references).

## Features

**The current firmware is based on stock GR IIIx firmware 1.60.** The added film presets are Portra 400, Ektar 100, Gold 200, Pro 400H, Vision3 250D, Classic Negative, Vision3 500T and Velvia 50. Select them from the shooting shortcut or MENU → Image Control, shoot in-camera JPEGs and identify the preset in playback. Names describe color targets; exposure, white balance and the scene also affect results.

### How it works

- **Store recipes:** appended RTOS storage holds the added color parameters, curves and helper code, which the camera’s existing image-processing pipeline uses to produce JPEGs.
- **Connect the interface:** expanded menu counts and ID mappings make added presets selectable and resolve their playback icons.

This extends Image Control without using U1/U2/U3. Changing recipes requires rebuilding the firmware; direct LUT import from an SD card is not supported.

### See it in action

[![Eight presets — camera demo](docs/images/presets-video-cover.jpg)](https://xhslink.cn/o/34w09ZlOEgY)

[Watch the camera demo on Xiaohongshu](https://xhslink.cn/o/34w09ZlOEgY)

![Casual camera JPEGs, no post-processing](docs/images/preset-samples.jpg)

## Camera and firmware compatibility

These instructions target a **standard GR IIIx on stock firmware 1.60**. B2.4.2 passed automated qualification; on 2026-10-17 the tester confirmed appended-area loading, power on/off and actual RAW/JPEG capture. Check MENU → Setup → About This Device → Firmware Info / Options (wording varies by language).

| Current setup | Applicability |
|---|---|
| Standard IIIx, stock 1.60 | Follow the file and installation steps below |
| Standard IIIx, older than 1.60 | Update to stock 1.60 using Ricoh's instructions and confirm normal shooting first |
| Newer than 1.60 | Not covered; do not downgrade to install this project |
| HDF, Urban or another model | Untested; do not apply these instructions directly; see the discussion below |
| Another modified firmware or unknown modification history | Check existing modifications and recovery options; a “1.60” display alone is insufficient |

⚠️ This is unofficial software and carries risks. Back up photos and important data before use. See [restoring official firmware](#restoring-official-firmware) for the recovery route and its limits.

## Firmware installation

Before installing, read [test order and result interpretation](docs/guides/BUILD.en.md#4-run-self-tests): check compatibility and file hashes for the supplied release; source builds require computer-side checks before gradual camera self-tests.

[Download BIN](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/latest/download/fwdc243b.bin) · [Download ZIP](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/latest/download/gr3x-film-slots.zip) · [Release notes](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/latest)

For standard GR IIIx 1.60. Prepare the latest ready-made package, a card reader, an SD card and a fully charged camera. No development tools are needed. The steps below use a Mac.

### 1. Put the firmware on the card

Back up photos and use a card the camera recognizes, preferably an empty spare card. Connect it through a card reader. If formatting is needed, format in-camera; **formatting deletes every file on the card**.

The distributed firmware is named **`fwdc243b.bin`**; no renaming is needed.

- **BIN download:** save it directly to the card.
- **ZIP download:** double-click to extract it, then copy the enclosed `fwdc243b.bin` to the card. **Do not put the ZIP on the card as an update.**

Place the file at the **top level** of the card, not inside `DCIM` or the extracted folder:

```text
SD card/
├── DCIM/
└── fwdc243b.bin
```

Wait for the download or copy to finish, check that no shutdown-image installation scripts are on the card, then click its eject button in Finder and wait for it to disappear before removing it. Use the project's ready-made firmware; GitHub's **Code → Download ZIP** contains source code and cannot be installed on the camera.

### 2. Update the camera

1. With the camera off, insert the fully charged battery and the prepared card.
2. **Hold MENU, then press the power button.** In the firmware-update screen, select Execute and confirm.
3. Wait for **Update completed**, then turn off. Do not power off, remove the card or remove the battery during updating.

If the update screen does not appear or a card error is shown, stop and check the card and file. See [Ricoh's update instructions](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html).

### 3. Check the result and clean up

Power on normally and open **MENU → Image Control**. Confirm that the added presets are selectable. Take a photo with one preset and check the image and playback icon.

**Why does the camera still show 1.60?** Stock version fields are retained to avoid introducing untested update behavior; do not change them manually. Numbers such as B2.4.2 identify project releases, and [SHA256](#file-checksum) identifies the downloaded file. The camera’s 1.60 display cannot identify the specific modified build.

After checking, format the update card in-camera to remove the update file before everyday use; back up any test photos you want to keep first. Stop using the modified firmware if you encounter flickering, crashes or abnormal files, and retain samples for troubleshooting.

## Restoring official firmware

**Reinstalling stock firmware is an option only if the camera can still enter its updater; it is not a guaranteed rescue from every failure. This project has not tested the full recovery procedure.**

1. Download stock GR IIIx 1.60 from [Ricoh](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html) and extract `fwdc243b.bin`. It has the same filename as the modified build, so confirm its source.
2. Use a clean spare card containing only the stock BIN, without modified firmware or startup scripts such as `startup.ttl`. Follow the [installation steps above](#firmware-installation), with a full battery; do not interrupt power or remove the card during the update.
3. If the camera accepts the update and reports completion, remove the update card and check factory presets, shooting and playback. The version still reads 1.60; that number alone does not confirm recovery.

If the updater cannot be reached, rejects a same-version update or problems persist, stop and seek repair support. Do not alter version fields to force installation. Reinstalling firmware does not restore all internal data; a separately installed shutdown image requires separate handling.

## File checksum

Compare the result with [SHA256SUMS.txt](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/latest/download/SHA256SUMS.txt). Replace the example path with your firmware file:

- Mac: `shasum -a 256 /path/fwdc243b.bin`
- Windows PowerShell: `Get-FileHash -Algorithm SHA256 "E:\fwdc243b.bin"`.

## Customization and development

- [Changelog](CHANGELOG.md): version changes, validation results and known limitations.
- [Source build and self-tests](docs/guides/BUILD.en.md): default builds, configuration, self-tests and extension constraints.
- **Shutdown image replacement:** [Download the separate image package](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0). The camera runs the included `.ttl` scripts to write the image; this has been confirmed on the test camera. B2.4.2 does not itself enable script execution. The package covers installation and cleanup after that feature is enabled; see its `README.txt`. First-time enablement instructions are still pending.

![Custom shutdown image on the camera (separate installation)](docs/images/shutdown-camera.jpg)

## Self-tests and known limitations

B2.4.2 fixes the preset-data overlap with factory compensation tables and retains the Fn crop-icon repair. Five automated stages pass, including 92 functional checks, complete compensation-table protection, stock submission-buffer comparisons for all seven settings, icon preservation and deterministic rebuilding.

Camera feedback is bound to the same firmware SHA256 and covers appended-area loading, power on/off and actual RAW/JPEG capture. No new sample files were collected; continuous shooting and endurance were not included. Some HDF-state and certification resources remain reused; model compatibility is unchanged.

### Applicability to other cameras and brands

- **Other IIIx variants and versions:** HDF and Urban [share the stock update package](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html), so some patches may transfer, but edition-specific functions still need testing. New firmware may move code and data; addresses cannot simply be reused.
- **GR III and other GR models:** upstream already has a III slot-expansion implementation, providing a useful starting point, but it needs a separate build. This project has no adaptation evidence for IV or II; membership in the GR family alone proves nothing.
- **Some Nikon models:** official support for importing NX Studio Custom Picture Controls through an SD card may allow recipe conversion and management without firmware modification. GR parameters cannot be copied directly; color would need to be fitted again.
- **Compatible Fujifilm models:** X RAW STUDIO uses the camera processor to develop RAW files, which may support recipe preview and comparison. It does not establish that extra Film Simulation slots can be added; that requires separate firmware research. [Official description](https://www.fujifilm-x.com/en-us/products/software/x-raw-studio/)

Recipe management, color fitting and comparison methods are more likely to transfer across brands. Extra slots, independent recipe settings, crops and shutdown images depend on each firmware. These are feasibility observations, not supported features or installation advice, and no implementation is promised.

## Development status

Research notes and development plans are not published. This repository keeps only the released builds, usage guidance and verification records; unchecked items are not supported features.

## Open-source references

Thanks to the projects that provided tools and research foundations:

| Project | Role in this project | License / notice |
|---|---|---|
| [gr3-film-mods](https://github.com/idontknownihil/gr3-film-mods) | Main source of [`tools/gr3-film-mods/`](tools/gr3-film-mods/); `make_slots*.py`, `verify_slots16.py` and related files adapt upstream implementations; `gr3patch_iiix.py` ports upstream `gr3patch.py` | [MIT](tools/gr3-film-mods/LICENSE) |
| [GRKit v1.0.0](https://github.com/ahonn/grkit) | Plugin startup base: installer/loader, fixed tail, ADJ menu host, modules/pages, picture.encode, processing/framing hooks, GRF effect registry, SD packaging and CLI | [MIT](https://github.com/ahonn/grkit/blob/main/LICENSE) |
| [gr3x-fw-hack](https://github.com/hhornbacher/gr3x-fw-hack) | Reference for IIIx system and firmware research | Tool / research reference |
| [gr_unpack](https://github.com/yeahnope/gr_unpack) | Reference for understanding firmware unpacking | Tool / research reference |
| [gr-custom-tool](https://github.com/DoYitNow/gr-custom-tool) | [`tools/gr3-film-mods/third_party/gr-custom-tool/`](tools/gr3-film-mods/third_party/gr-custom-tool/) retains the container codec subset required by the build | [GPL-2.0-only](tools/gr3-film-mods/third_party/gr-custom-tool/LICENSE) |
| [GR3-LUTSmith](https://github.com/lemonadesaltbagel/GR3-LUTSmith) | Color-fitting tooling whose data is connected to the preset build workflow | Tool / research reference |
| [ricoh-gr3-shutdown-image](https://github.com/AlexMimi/ricoh-gr3-shutdown-image) | Foundation for the shutdown-image workflow; tooling is supplied in the separate image package | Tool / research reference |
| [spektrafilm / Andrea Volpato](https://github.com/andreavolpato/spektrafilm) | Source of the Portra, Ektar, Gold, Pro400H and both Vision3 preset data in [`workspace/b2_iiix/fits/`](workspace/b2_iiix/fits/) | [CC BY-SA 4.0](tools/gr3-film-mods/LICENSES/SPEKTRAFILM_LICENSE.txt) |
| [FujifilmCameraProfiles / abpy](https://github.com/abpy/FujifilmCameraProfiles) | Source of the preset data in [`workspace/b2_iiix/fits/classic-negative.json`](workspace/b2_iiix/fits/classic-negative.json) | [CC BY-NC-SA 4.0](tools/gr3-film-mods/LICENSES/CC-BY-NC-SA-4.0.txt) |
| Project-added code | Build, configuration, bridging and self-test scripts in `scripts/` and `workspace/b2_iiix/`; the `tools/gr3-film-mods/asm_util.py` helper | See [license scope](LICENSING.md) |

Analysis and builds also use Unicorn, Capstone, LLVM and Pillow.
Original copyright notices, licenses and upstream [data modification records](tools/gr3-film-mods/LICENSES/CHANGELOG.txt) are retained. References do not imply upstream review or endorsement.

Thanks to [OpenCode](https://opencode.ai/) for its capabilities during development.

## License

Project-authored build and self-test code: **GPL-2.0-only**. Third-party code and preset data retain their respective licenses. See [LICENSE](LICENSE) and [scope](LICENSING.md).
