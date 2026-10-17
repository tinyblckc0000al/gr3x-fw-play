# gr3x-fw-play

[中文](README.md) | [English](README.en.md)

**22 Image Controls on the GR IIIx: 12 factory presets + 2 custom options + 8 extra film looks.** All original modes are retained, and the eight added preset slots can be replaced. Use the default recipes or rebuild the firmware with a different configuration. Shutdown-image customization is a separate feature.

- **Use the eight presets**: download the [ready-made firmware](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4.1) and follow the [installation steps](#firmware-installation). No development tools needed.
- **Change only the shutdown image**: use the [separate image package](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0). Installed separately; the camera’s built-in script execution feature (Script) must be enabled first. Copying an image to the card alone will not install it.
- **Change recipes, names or icons**: see [custom presets](docs/guides/BUILD.en.md#custom-presets) for rebuilding instructions and custom-build verification limits.
- **Build or explore the code**: see [source build and self-tests](docs/guides/BUILD.en.md).

### What's new here

Built on gr3-film-mods, this project adapts the preset expansion to **GR IIIx 1.60**, fixes added-preset selection and playback identification, and provides configurable builds with repeatable self-checks. Upstream code and data sources are listed in [Open-source references](#open-source-references).

## Features

**B2.4.1 is based on stock GR IIIx firmware 1.60.** The added film presets are Portra 400, Ektar 100, Gold 200, Pro 400H, Vision3 250D, Classic Negative, Vision3 500T and Velvia 50. Select them from the shooting shortcut or MENU → Image Control, shoot in-camera JPEGs and identify the preset in playback. Names describe color targets; exposure, white balance and the scene also affect results.

### How it works

- **Store recipes:** legacy record slots hold the added color parameters and curves, which the camera’s existing image-processing pipeline uses to produce JPEGs.
- **Connect the interface:** expanded menu counts and ID mappings make added presets selectable and resolve their playback icons.

This extends Image Control without using U1/U2/U3. Changing recipes requires rebuilding the firmware; direct LUT import from an SD card is not supported.

### See it in action

[![Eight presets — camera demo](docs/images/presets-video-cover.jpg)](https://xhslink.cn/o/34w09ZlOEgY)

[Watch the camera demo on Xiaohongshu](https://xhslink.cn/o/34w09ZlOEgY)

![Casual camera JPEGs, no post-processing](docs/images/preset-samples.jpg)

## Camera and firmware compatibility

These instructions target a **standard GR IIIx on stock firmware 1.60**. Earlier B2.4 testing used one camera; B2.4.1 has computer-side validation only and has not been retested on a camera. Check MENU → Setup → About This Device → Firmware Info / Options (wording varies by language).

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

[Download BIN](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4.1/fwdc243b.bin) · [Download ZIP](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4.1/gr3x-film-slots-b2.4.1.zip) · [Release notes](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4.1)

For standard GR IIIx 1.60. Prepare the B2.4.1 ready-made package, a card reader, an SD card and a fully charged camera. No development tools are needed. The steps below use a Mac.

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

**Why does the camera still show 1.60?** Stock version fields are retained to avoid introducing untested update behavior; do not change them manually. B2.4.1 is the project release version, and [SHA256](#file-checksum) identifies the downloaded file. The camera’s 1.60 display cannot identify the specific modified build.

After checking, format the update card in-camera to remove the update file before everyday use; back up any test photos you want to keep first. Stop using the modified firmware if you encounter flickering, crashes or abnormal files, and retain samples for troubleshooting.

## Restoring official firmware

**Reinstalling stock firmware is an option only if the camera can still enter its updater; it is not a guaranteed rescue from every failure. This project has not tested the full recovery procedure.**

1. Download stock GR IIIx 1.60 from [Ricoh](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html) and extract `fwdc243b.bin`. It has the same filename as the modified build, so confirm its source.
2. Use a clean spare card containing only the stock BIN, without modified firmware or startup scripts such as `startup.ttl`. Follow the [installation steps above](#firmware-installation), with a full battery; do not interrupt power or remove the card during the update.
3. If the camera accepts the update and reports completion, remove the update card and check factory presets, shooting and playback. The version still reads 1.60; that number alone does not confirm recovery.

If the updater cannot be reached, rejects a same-version update or problems persist, stop and seek repair support. Do not alter version fields to force installation. Reinstalling firmware does not restore all internal data; a separately installed shutdown image requires separate handling.

## File checksum

Compare the result with [SHA256SUMS.txt](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4.1/SHA256SUMS.txt). Replace the example path with your firmware file:

- Mac: `shasum -a 256 /path/fwdc243b.bin`
- Windows PowerShell: `Get-FileHash -Algorithm SHA256 "E:\fwdc243b.bin"`.

## Customization and development

- [Source build and self-tests](docs/guides/BUILD.en.md): default builds, configuration, self-tests and extension constraints.
- **Shutdown image replacement:** [Download the separate image package](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0). The camera runs the included `.ttl` scripts to write the image; this has been confirmed on the test camera. B2.4.1 does not itself enable script execution. The package covers installation and cleanup after that feature is enabled; see its `README.txt`. First-time enablement instructions are still pending.

![Custom shutdown image on the camera (separate installation)](docs/images/shutdown-camera.jpg)

## Self-tests and known limitations

B2.4.1 fixes film icons replacing the factory TELE/71mm crop indicators in the Fn menu. The default eight-preset build passes all eight computer-side stages, including 91 functional checks, 5 icon/mapping tests and a deterministic rebuild.

This version has not been retested on a camera. Earlier single-camera B2.4 testing confirmed menu entry, preset selection and playback information; nine retained RAW+JPEG pairs cover seven added presets. Those historical samples do not validate B2.4.1. Some HDF-state and certification resources remain reused; this release fixes crop icons and does not expand model compatibility.

### Applicability to other cameras and brands

- **Other IIIx variants and versions:** HDF and Urban [share the stock update package](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html), so some patches may transfer, but edition-specific functions still need testing. New firmware may move code and data; addresses cannot simply be reused.
- **GR III and other GR models:** upstream already has a III slot-expansion implementation, providing a useful starting point, but it needs a separate build. This project has no adaptation evidence for IV or II; membership in the GR family alone proves nothing.
- **Some Nikon models:** official support for importing NX Studio Custom Picture Controls through an SD card may allow recipe conversion and management without firmware modification. GR parameters cannot be copied directly; color would need to be fitted again.
- **Compatible Fujifilm models:** X RAW STUDIO uses the camera processor to develop RAW files, which may support recipe preview and comparison. It does not establish that extra Film Simulation slots can be added; that requires separate firmware research. [Official description](https://www.fujifilm-x.com/en-us/products/software/x-raw-studio/)

Recipe management, color fitting and comparison methods are more likely to transfer across brands. Extra slots, independent recipe settings, crops and shutdown images depend on each firmware. These are feasibility observations, not supported features or installation advice, and no implementation is promised.

## Modding ideas / TODO (wish these were official features!)

- [ ] **Preset editing and preview:** select recipes, edit names/icons and preview results on a computer.
- [ ] **Independent recipe settings:** investigate storing white balance, grain and other settings per preset to reduce repeated adjustments.
- [ ] **More aspect ratios:** explore wide-format framing guides and crops for in-camera images.

## Open-source references

Thanks to the projects that provided tools and research foundations:

| Project | Role in this project | License / notice |
|---|---|---|
| [gr3-film-mods](https://github.com/idontknownihil/gr3-film-mods) | Main source of [`tools/gr3-film-mods/`](tools/gr3-film-mods/); `make_slots*.py`, `verify_slots16.py` and related files adapt upstream implementations; `gr3patch_iiix.py` ports upstream `gr3patch.py` | [MIT](tools/gr3-film-mods/LICENSE) |
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
