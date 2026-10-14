# gr3x-fw-play

[中文](README.md) | [English](README.en.md)

**22 Image Controls on the GR IIIx: 12 factory presets + 2 custom options + 8 extra film looks.** All original modes are retained, and the eight added preset slots can be replaced. Use the default recipes or rebuild the firmware with a different configuration. Shutdown-image customization is a separate feature.

- **Use the eight presets**: download the ready-made firmware and follow the [installation steps](#firmware-installation). No development tools needed.
- **Change only the shutdown image**: use the [separate image package](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0). Installed separately; Script must already be enabled.
- **Build or explore the code**: see [source build and self-tests](docs/guides/BUILD.en.md).

## Features

**B2.4 is based on stock GR IIIx firmware 1.60.** It expands Image Controls from 14 to 22, adding Portra 400, Ektar 100, Gold 200, Pro 400H, Vision3 250D, Classic Negative, Vision3 500T and Velvia 50. Select them from the shooting shortcut or MENU → Image Control, shoot in-camera JPEGs and identify the preset in playback. Names describe color targets; exposure, white balance and the scene also affect results.

- These are Image Control options, not additional U1/U2/U3 custom shooting modes.
- Changing recipes requires rebuilding and checking the firmware on a computer, then updating the camera. Direct LUT import from an SD card is not supported; this may be explored later.
- Shutdown images use a separate script package and are not included in B2.4.

<a href="https://xhslink.cn/o/34w09ZlOEgY"><img src="docs/images/presets-video-cover.jpg" width="280" alt="Eight presets — camera demo"></a>

[Watch the camera demo on Xiaohongshu](https://xhslink.cn/o/34w09ZlOEgY)

## Camera and firmware compatibility

These instructions apply to a **standard GR IIIx on stock firmware 1.60**, tested on one camera. Check MENU → Setup → About This Device → Firmware Info / Options (wording varies by language), and confirm whether the body is HDF or Urban.

| Current setup | Applicability |
|---|---|
| Standard IIIx, stock 1.60 | Follow the file and installation steps below |
| Standard IIIx, older than 1.60 | Update to stock 1.60 using Ricoh's instructions and confirm normal shooting first |
| Newer than 1.60 | Not covered; do not downgrade to install this project |
| HDF, Urban or another model | Untested; do not apply these instructions directly; see the discussion below |
| Another modified firmware or unknown modification history | Check existing modifications and recovery options; a “1.60” display alone is insufficient |

⚠️ This is unofficial software. Crashes, damaged photos or repairs may be possible. Back up photos first. Reinstalling stock 1.60 is a theoretical recovery route, not a tested recovery guarantee here.

## Firmware installation

[Download BIN](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4/fwdc243b.bin) · [Download ZIP](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4/gr3x-film-slots-b2.4.zip) · [Release notes](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4)

For standard GR IIIx 1.60. Prepare the B2.4 ready-made package, a card reader, an SD card and a fully charged camera. No development tools are needed. The steps below use a Mac.

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

Power on normally and open **MENU → Image Control**. Confirm that all 22 Image Controls are available: 12 factory presets, 2 custom options and 8 added film presets. Take a photo with one preset and check the image and playback icon. The camera still reports **1.60**, which is expected.

After checking, format the update card in-camera to remove the update file before everyday use; back up any test photos you want to keep first. Stop using the modified firmware if you encounter flickering, crashes or abnormal files, and retain samples for troubleshooting.

## File checksum

Compare the result with [SHA256SUMS.txt](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4/SHA256SUMS.txt). Replace the example path with your firmware file:
Mac: `shasum -a 256 /path/fwdc243b.bin`; Windows PowerShell: `Get-FileHash -Algorithm SHA256 "E:\fwdc243b.bin"`.

## Customization and development

- **Shutdown image:** [Download the separate image package](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0). Confirmed on the test camera and installed separately. Current scripts assume Script is already enabled; first-time instructions are incomplete and restoring the original image has not been camera-tested. Do not substitute the Urban workflow or mix firmware updates and image scripts on one card. Confirm installation by comparing the read-back image, not just a completion message; then remove the startup script and disable Script.
- [Source build and self-tests](docs/guides/BUILD.en.md): environment setup, default builds, self-checks and preset reordering.

<img src="docs/images/shutdown-camera.jpg" width="360" alt="Custom shutdown image on the camera (separate installation)">

## Self-tests and known limitations

Default B2.4 passed checks for modified regions, menu/playback mappings and 91 regression checks, and can be rebuilt with an identical hash. On the camera, menu entry, preset selection and playback information have been confirmed. Nine retained RAW+JPEG pairs cover seven added presets, excluding Gold 200.

Cross-device and long-term stability remain untested. Full custom-preset self-checks and first-time shutdown-image installation/restoration workflows remain incomplete.

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
| [gr3-film-mods](https://github.com/idontknownihil/gr3-film-mods) | Foundation for preset slots, color processing and ARM emulation | [MIT](tools/gr3-film-mods/LICENSE) |
| [gr3x-fw-hack](https://github.com/hhornbacher/gr3x-fw-hack) | Reference for IIIx system and firmware research | Tool / research reference |
| [gr_unpack](https://github.com/yeahnope/gr_unpack) | Reference for understanding firmware unpacking | Tool / research reference |
| [gr-custom-tool](https://github.com/DoYitNow/gr-custom-tool) | Firmware container codec used by the build | [GPL-2.0-only](tools/gr3-film-mods/third_party/gr-custom-tool/LICENSE) |
| [GR3-LUTSmith](https://github.com/lemonadesaltbagel/GR3-LUTSmith) | Color-fitting tooling whose data is connected to the preset build workflow | Tool / research reference |
| [ricoh-gr3-shutdown-image](https://github.com/AlexMimi/ricoh-gr3-shutdown-image) | Foundation for the separate shutdown-image workflow | Tool / research reference |
| [spektrafilm / Andrea Volpato](https://github.com/andreavolpato/spektrafilm) | Portra, Ektar, Gold, Pro400H and both Vision3 preset targets | [CC BY-SA 4.0](tools/gr3-film-mods/LICENSES/SPEKTRAFILM_LICENSE.txt) |
| [FujifilmCameraProfiles / abpy](https://github.com/abpy/FujifilmCameraProfiles) | Classic Negative preset target | [CC BY-NC-SA 4.0](tools/gr3-film-mods/LICENSES/CC-BY-NC-SA-4.0.txt) |

**This project adds GR IIIx 1.60 adaptation, MENU/playback fixes, configurable eight-preset builds and repeatable self-checks.** Analysis and builds also use Unicorn, Capstone, LLVM and Pillow.
Original copyright notices, licenses and upstream [data modification records](tools/gr3-film-mods/LICENSES/CHANGELOG.txt) are retained; this project adds IIIx adaptations, fixes and preset configuration metadata. Velvia authorization remains unresolved and its data is excluded from public distribution. References do not imply upstream review or endorsement.

Thanks to [OpenCode](https://opencode.ai/) for its capabilities during development.

## License

Project-authored build and self-test code: **GPL-2.0-only**. Third-party code and preset data retain their respective licenses. See [LICENSE](LICENSE) and [scope](LICENSING.md).
