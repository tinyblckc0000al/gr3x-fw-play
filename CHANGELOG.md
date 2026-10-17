# 更新记录 / Changelog

按版本记录用户可见变更、验证结果与已知限制；执行步骤见[验证指南](workspace/b2_iiix/VERIFICATION.md)。
Version history records changes, validation and limitations. See the [verification guide](workspace/b2_iiix/VERIFICATION.md) for the procedure.

## B2.4.1 — 2026-10-17

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
