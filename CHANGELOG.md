# 更新记录 / Changelog

按版本记录用户可见变更、验证结果与已知限制；执行步骤见[验证指南](workspace/b2_iiix/VERIFICATION.md)。
Version history records changes, validation and limitations. See the [verification guide](workspace/b2_iiix/VERIFICATION.md) for the procedure.

## 插件路线 — 2026-10-23 / Plugin route — 2026-10-23

[发布包 / Release](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/plugin-v0.1)

从修改固件转向原厂 1.60 + SD 卡插件。安装前必须刷回原厂；项目之前的 B2.4.x 固件和本插件版不能同时存在，旧包继续保留。

Switches from firmware patching to stock 1.60 plus an SD-card plugin. Flashing stock first is required; the project's previous B2.4.x firmware and this plugin cannot coexist. Old packages remain available.

- 新增独立 ADJ 插件菜单，以及 Image Control / Framing / Guides / Date / Grain 页面。
- 新增拍摄比例、构图辅助线、日期戳、颗粒，以及柔焦和柔光多档调节。
- 提供 18 套机内胶片效果，包含之前的 8 套预设。
- 安装时恢复原厂 Clarity 表；不修改原厂固件。
- 已验证：Soft Focus host 96 case、Glow 四档 host 测试、Soft OFF/STRONG 同场景对照、Glow DIAGALL 执行/完成标志、grkit build/package/verify 通过。
- 未完成：设置重启持久化、原生菜单体验、柔焦/柔光调整、GR2 色彩。

- Adds an independent ADJ plugin menu and Image Control / Framing / Guides / Date / Grain pages.
- Adds aspect ratios, composition guides, date stamp, grain, and multi-level soft focus/glow.
- Ships 18 in-camera film effects, including the previous 8 presets.
- Restores the stock Clarity table at install time; stock firmware is not modified.
- Verified: 96-case Soft Focus host sweep, Glow four-level host test, same-scene Soft OFF/STRONG comparison, Glow DIAGALL entry/completion flags, and grkit build/package/verify.
- Not done: settings persistence, native menu experience, soft focus/glow tuning, GR2 color.

## B2.4.2 — 2026-10-17

[发布包 / Release](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4.2)

修复 B2.4.1 配方数据与原厂补偿表的布局冲突：原检查仅保护 452 字节，实际读取窗口为 3584 字节。新增 24 KiB RTOS 追加区，70 项分配共占 6236 字节；新增配方、曲线与补丁代码迁入该区，恢复完整补偿表及此前借用的随机路径和 MA 区域。同步修正分配对齐、曲线展开范围和增长后的图标段定位，保留 Fn 裁切图标修复。

五阶段离线验证通过，含 92 项功能回归、七档补偿参数的原厂提交缓冲区逐字节对比、保护区错误注入和确定性重建。2026-10-17 用户确认“真机确认了，追加区能完整加载，开关机、实际 RAW／JPEG 成像都没问题”。连续拍摄、长期稳定性及 HDF／Urban 专属功能不在本次确认范围内，未收集新样片。

Fixes the B2.4.1 overlap between added preset data and factory compensation tables: the old check covered 452 bytes instead of the complete 3584-byte read window. A 24 KiB appended RTOS area holds 70 allocations totaling 6236 bytes, restoring the stock compensation tables, random path and MA storage. Allocation alignment, curve-expansion ranges and shifted icon-section offsets are corrected; the crop-icon fix is retained.

Five automated stages pass, including 92 functional checks, stock upload-buffer equality for seven compensation settings, negative mutations and deterministic rebuilding. User-reported camera acceptance covers full append loading, power on/off and actual RAW/JPEG capture. No new samples were collected; burst/endurance and HDF/Urban-specific functions remain outside this confirmation.

- BIN SHA256: `f2c86157bd440d3db20da90af05d770d93b2588878139ab813e4353a0ca9cb74`
- [Camera feedback](workspace/b2_iiix/hardware-b242.json)
- [Verification guide](workspace/b2_iiix/VERIFICATION.md)

## B2.4.1 — 2026-10-17

> 后续审计确认布局冲突，由 B2.4.2 修复；以下为历史发布记录。Superseded by B2.4.2 after a confirmed storage-layout conflict.

[发布包 / Release](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4.1)

### 中文

**修复**：Fn 裁切菜单的 71mm 图标显示为半截 NC 预设图标。恢复原厂 TELE／71mm 资源，预设图标使用新增编号。八套胶片配方不变。

**开发流程**：构建前拒绝未经批准的原厂图标复用；独立对照原厂资源，以裁切及非裁切资源的错误注入检验检查器；发布前核对测试报告、源码、固件及真机反馈的一致性。覆盖是否充分仍需人工评审。

**验证**：八阶段通过，包括 91 项功能回归、14 项检查器／资源策略／发布证据自测、6 项图标资源测试、最终回放链和确定性重建。2026-10-17 测试用户反馈“真机测试没问题”；未收集逐项结果或新 RAW+JPEG 样片。发布 BIN 与送测文件逐字节一致。

**范围与限制**：目标为普通版 GR IIIx 1.60。HDF／Urban 未新增实测覆盖；部分 HDF 状态与认证资源仍复用。本次不含新增画幅或关机图片。

### English

**Fix:** The 71mm crop indicator in the Fn menu appeared as a partial NC preset icon. Factory TELE/71mm resources are restored; film icons use added IDs. The eight film recipes are unchanged.

**Development process:** Reject unapproved factory-icon reuse before patching; compare against stock independently and inject faults into crop and non-crop resources to test the checker; verify consistency across qualification reports, sources, firmware and camera feedback before publication. Coverage adequacy still requires human review.

**Validation:** All eight stages passed, including 91 functional checks, 14 checker/resource-policy/release-evidence self-tests, 6 icon-resource tests, final-image playback and deterministic rebuild. On 2026-10-17 the test user reported a camera pass for the fix; individual checklist results and new RAW+JPEG samples were not collected. The released BIN is byte-identical to the supplied test file.

**Scope and limitations:** Targets the standard GR IIIx on firmware 1.60. No new HDF/Urban test coverage; some HDF-state and certification resources remain reused. Added aspect ratios and shutdown images are not included.

### 版本证据 / Release evidence

- [SHA256SUMS.txt](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4.1/SHA256SUMS.txt)
- [验证报告与日志 / Reports and logs](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4.1/verification-b2.4.1.zip)
- [真机反馈 / Camera feedback](https://github.com/tinyblckc0000al/gr3x-fw-play/blob/b2.4.1/workspace/b2_iiix/hardware-b241.json)
- [归档验证说明 / Archived verification notes](https://github.com/tinyblckc0000al/gr3x-fw-play/blob/b2.4.1/workspace/b2_iiix/VERIFICATION.md)

## 更早版本 / Earlier releases

[B2.4 发布记录 / B2.4 release notes](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4)。更早版本沿用原发布记录，不追补未经核实的验证结论。Earlier versions retain their original release records; no unverified validation claims are added retrospectively.
