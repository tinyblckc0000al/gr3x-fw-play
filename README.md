# gr3x-fw-play

[中文](README.md) | [English](README.en.md)

**让 GR IIIx 拥有 22 套影像控制：12 套原厂预设＋2 套自定义＋8 套新增胶片预设。** 原有模式全部保留，新增的八个预设槽位可替换。可以使用默认配方，也可以更换配方后重新生成固件。项目另提供独立的关机图片自定义方案。

- **直接使用八套预设**：下载成品固件，按[安装步骤](#直接固件安装)操作，无需开发工具。
- **只更换关机图片**：下载[独立图片包](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0)，独立安装，当前包要求已启用 Script。
- **自行构建或研究代码**：阅读[源码构建与自测](docs/guides/BUILD.md)。

## 功能概述

**B2.4 基于 GR IIIx 原厂 1.60**，将影像控制从 14 套扩展到 22 套，新增 8 套胶片预设（Portra 400、Ektar 100、Gold 200、Pro 400H、Vision3 250D、Classic Negative、Vision3 500T、Velvia 50）。安装后，可在拍摄快捷菜单和 MENU → 影像控制中选择，拍摄对应风格的 JPEG，并在回放时识别预设。名称表示色彩模拟目标，实际效果也受曝光、白平衡和场景影响。

ps:
- 新增的是影像控制选项，不是自定义拍摄模式 U1/U2/U3。
- 更换配方需在电脑上重新生成、检查固件，再更新相机，暂不支持外卡预设直接导入 LUT（后续可能考虑优化）。
- 关机图片使用独立脚本包，不包含在 B2.4 中。

<a href="https://xhslink.cn/o/34w09ZlOEgY"><img src="docs/images/presets-video-cover.jpg" width="280" alt="八套预设真机演示"></a>

[看真机演示 · 小红书视频](https://xhslink.cn/o/34w09ZlOEgY)

## 适用机型与版本

本教程适用于**普通版 GR IIIx、原厂固件 1.60**，实测来自一台设备。可在 MENU → 设置 → 关于本机 → 固件信息／选项查看版本（名称以相机语言为准），并确认机身是否为 HDF 或 Urban。

| 相机当前情况 | 是否适用本教程 |
|---|---|
| 普通版 IIIx，原厂 1.60 | 可以按下面步骤核对文件并安装 |
| 普通版 IIIx，低于 1.60 | 先按官方说明更新至原厂 1.60，确认正常拍摄后再继续 |
| 高于 1.60 | 暂不适用，不要为安装本项目自行降级 |
| HDF、Urban 或其他机型 | 未实测，不直接套用；可行性讨论见下文 |
| 已有其他修改固件，或不清楚修改历史 | 先确认已有修改和恢复方式，不能只看“1.60”判断 |

⚠️ 本项目非理光官方软件，可能出现死机、照片损坏或需要维修。操作前备份照片；虽然理论上可以刷官方1.60恢复，但在此不作任何实操保证。

---
## 直接固件安装

[下载 BIN](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4/fwdc243b.bin) · [下载 ZIP](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4/gr3x-film-slots-b2.4.zip) · [版本说明](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/b2.4)

适用于普通版 GR IIIx 1.60。准备 B2.4 成品包、读卡器、存储卡和充满电的相机，无需安装开发工具。下面以 Mac 为例。

### 1. 将固件放到存储卡

先备份卡上的照片，准备一张相机能正常识别的存储卡，最好是空的无用的，用读卡器连接电脑。需要格式化时，在相机内操作；**格式化会删除卡内全部文件**。

发布的固件文件名为 **`fwdc243b.bin`**，不用改名。根据下载的文件类型操作：

- **下载的是 `.bin` 文件：** 可以直接保存到存储卡。
- **下载的是 `.zip` 压缩包：** 先双击解压，再把里面的 `fwdc243b.bin` 复制到存储卡。**不要把 ZIP 直接放进卡里更新。**

文件要放在存储卡的**第一层**，即打开存储卡后直接能看到的位置，不要放进 `DCIM` 或解压出来的文件夹。卡内应类似这样：

```text
存储卡/
├── DCIM/
└── fwdc243b.bin
```

确认下载或复制已完成，卡上没有关机图片安装脚本，再点击 Finder 侧栏中存储卡旁的弹出按钮，等卡消失后取出。请下载项目提供的成品固件；GitHub 的 **Code → Download ZIP** 是源码，不能刷机。

### 2. 在相机上更新

1. 相机保持关机，装好充满电的电池，插入存储卡。
2. **按住 MENU，再按电源键开机。** 出现固件更新界面后，选择执行并确认。
3. 等待 **Update completed／更新完成**，再关机。更新期间不要关机、拔卡或取电池。

如果没有出现更新界面，或提示存储卡异常，先停止，检查卡和文件。更新按键参考[理光官方说明](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html)。

### 3. 确认效果并清理

正常开机，进入 **MENU → 影像控制**，确认共 22 套影像控制：12 套原厂预设、2 套自定义及新增的 8 套胶片预设；选一套拍照，检查照片和回放图标。

**为什么仍显示 1.60？** 本项目保留原厂版本字段，未验证修改这些字段对更新、恢复流程的影响，因此不要为了标识修改版而随意改号。**B2.4 是项目发布版本**；下载包按发布版本区分，具体固件以 [SHA256 文件指纹](#文件校验)确认。机内显示的 1.60 无法区分原厂与修改版；新增预设可用于检查功能是否生效，但不能代替文件指纹确认具体构建。

确认后，在相机内格式化更新卡，清除更新文件，再用于日常拍摄；刚拍的测试照片如果要保留，先备份。出现闪屏、死机或照片异常时停止使用，并保留样片反馈。

---

## 文件校验

计算结果与 [SHA256SUMS.txt](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/download/b2.4/SHA256SUMS.txt) 对照：

- Mac：`shasum -a 256 /路径/fwdc243b.bin`
- Windows PowerShell：`Get-FileHash -Algorithm SHA256 "E:\fwdc243b.bin"`。

## 自定义与开发文档

- [源码构建与自测](docs/guides/BUILD.md)：包含环境准备、默认构建、自测和预设顺序调整。

- **关机图片**：[下载独立图片包](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/tag/shutdown-v1.0)。已在本机确认效果，与预设固件分开安装。当前脚本只用于已启用 Script 的测试机，首次安装说明尚未完善，恢复原图也未实测。不要混用 Urban 流程或在卡上同时放置更新固件与图片脚本。安装是否成功需核对读回图片，不能只看完成提示；确认后移除启动脚本并关闭 Script。

<img src="docs/images/shutdown-camera.jpg" width="360" alt="自定义关机画面实拍（独立安装）">

## 自测情况与已知限制

默认 B2.4 通过了修改区域、菜单与回放映射检查及 91 项回归检查，可重建出指纹一致的文件。真机已确认 MENU 进入、预设选择和回放信息正常；现有九组 RAW+JPEG 样片覆盖七套新增预设。

### 其他机型和品牌参考价值

- **IIIx 的其他版本**：HDF、Urban [共用原厂更新包](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html)，沿用部分补丁的可能性较大，但专属功能仍要实测；新版固件可能移动代码和数据位置，需要重新定位，不能直接复用地址。
- **GR III 与其他 GR**：III 已有上游扩槽方案，适配基础较好，但必须单独构建。IV、II 尚无本项目的适配证据，不能仅凭同属 GR 就判断可行。
- **尼康部分机型**：官方支持把 NX Studio 制作的自定义 Picture Control 通过存储卡导入。因此，配方转换与管理可能直接利用官方入口，不一定需要修改固件；但 GR 的参数不能直接照搬，需重新拟合色彩。
- **富士兼容机型**：X RAW STUDIO 能调用相机处理器显影 RAW，可作为配方预览与对比的基础；这不代表能新增胶片模拟槽位，后者仍需单独研究固件。[官方说明](https://www.fujifilm-x.com/en-us/products/software/x-raw-studio/)

更容易跨品牌复用的是配方管理、色彩拟合和对比方法；机内扩槽、独立参数记忆、画幅裁切和关机图片都依赖具体固件，需要分别研究。以上仅是可行性分析，不代表已支持，不构成安装建议，也不承诺后续实现。

## 魔改思路TODO（最好官方就能做，可恶）

- [ ] **预设编辑与预览**：更方便地选择配方、修改名称和图标，在电脑上预览效果。
- [ ] **独立配方记忆**：研究能否为每套预设分别保存白平衡、颗粒等设置，切换风格时减少重复调整。
- [ ] **更多画幅比例**：探索宽幅构图辅助与裁切，让机内直出有更多构图选择。
  ......

## 开源项目参考

感谢以下项目提供的工具与研究基础：

| 项目 | 在本项目中的用途 | 许可与说明 |
|---|---|---|
| [gr3-film-mods](https://github.com/idontknownihil/gr3-film-mods) | 预设扩槽、色彩处理与 ARM 仿真的主要基础 | [MIT](tools/gr3-film-mods/LICENSE) |
| [gr3x-fw-hack](https://github.com/hhornbacher/gr3x-fw-hack) | IIIx 系统结构与固件分析的研究参考 | 工具／研究参考 |
| [gr_unpack](https://github.com/yeahnope/gr_unpack) | 理解固件解包结构的研究参考 | 工具／研究参考 |
| [gr-custom-tool](https://github.com/DoYitNow/gr-custom-tool) | 构建中使用的固件容器编解码工具 | [GPL-2.0-only](tools/gr3-film-mods/third_party/gr-custom-tool/LICENSE) |
| [GR3-LUTSmith](https://github.com/lemonadesaltbagel/GR3-LUTSmith) | 色彩拟合工具，相关数据衔接到本项目的预设构建流程 | 工具／研究参考 |
| [ricoh-gr3-shutdown-image](https://github.com/AlexMimi/ricoh-gr3-shutdown-image) | 独立关机图片功能的工具基础 | 工具／研究参考 |
| [spektrafilm / Andrea Volpato](https://github.com/andreavolpato/spektrafilm) | Portra、Ektar、Gold、Pro400H、两套 Vision3 预设数据 | [CC BY-SA 4.0](tools/gr3-film-mods/LICENSES/SPEKTRAFILM_LICENSE.txt) |
| [FujifilmCameraProfiles / abpy](https://github.com/abpy/FujifilmCameraProfiles) | Classic Negative 预设数据 | [CC BY-NC-SA 4.0](tools/gr3-film-mods/LICENSES/CC-BY-NC-SA-4.0.txt) |

**本项目在这些基础上完成 GR IIIx 1.60 适配、MENU 与回放信息修复、八套预设的配置化构建，以及可重复运行的自测检查。** 分析和构建还使用了 Unicorn、Capstone、LLVM 与 Pillow。
保留原版权、许可及上游[数据修改记录](tools/gr3-film-mods/LICENSES/CHANGELOG.txt)；本项目另作 IIIx 适配、修复和预设配置元数据调整。Velvia 授权尚未核清，不纳入公开分发。引用不表示上游作者审核或背书。

感谢 [OpenCode](https://opencode.ai/) 在项目开发过程中提供的能力。

## 许可

原创构建与自测代码采用 **GPL-2.0-only**；第三方代码和预设数据保留各自许可。详见 [LICENSE](LICENSE)及[适用范围](LICENSING.md)。
