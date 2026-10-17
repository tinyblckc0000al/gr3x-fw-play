# 源码构建与自测

[English](BUILD.en.md) · [返回项目说明](../../README.md)

直接安装请下载[最新版本](https://github.com/tinyblckc0000al/gr3x-fw-play/releases/latest)。本页面向源码构建；源码 ZIP 不能直接刷入。以下命令从仓库根目录运行。已验证环境为 Apple Silicon macOS、Python 3.14、Homebrew LLVM 和系统 DIN Condensed Bold 字体。

### 1. 安装依赖

```sh
brew install python@3.14 llvm
"$(brew --prefix python@3.14)/bin/python3.14" -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. 准备输入

将解压后的官方固件放入以下位置，必须使用指定版本：

| 文件 | 版本 |
|---|---|
| `firmware-inputs/fwdc243b.bin` | [GR IIIx 1.60](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html) |
| `firmware-inputs/fwdc248b.bin` | [GR IV 1.11](https://www.ricoh-imaging.co.jp/english/support/digital/gr4_s.html)，仅用于提取参数 |

```sh
venv/bin/python scripts/prepare_inputs.py --iiix firmware-inputs/fwdc243b.bin --iv firmware-inputs/fwdc248b.bin
```

输入 SHA256 不匹配时停止；不要替换为其他版本或跳过检查。官方固件不随源码提供。

### 3. 构建默认固件

保持默认 `presets.json` 和 `fits/` 不变：

```sh
mkdir -p workspace/b2_iiix/out
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix workspace/b2_iiix/out/fwdc243b.bin
```

输出为 BIN 和 `.report.json`，不要使用失败构建留下的产物。

### 4. 完整验证

```sh
venv/bin/python workspace/b2_iiix/qualify_storage_candidate.py workspace/b2_iiix/out/fwdc243b.bin --output workspace/b2_iiix/logs/qualification-current
```

输出目录必须尚不存在。五阶段依次检查结构、错误注入、单元与原生探针、功能回归、确定性重建；要求全部 `PASS` 且退出码为 0。保留完整报告和日志。阶段缺失、超时或中断都不算通过。不要替换预期哈希来绕过失败。

[验证指南](../../workspace/b2_iiix/VERIFICATION.md)记录当前发布产物的检查规则、真机反馈和发布门禁。`verify_release.py` 的历史完整流程针对旧版，不用于放行当前追加区布局。改动源码或配置后重新验证；固件字节改变后重新真机验收。下载和卡内文件均应与同一次发布的校验表一致。

### 5. 相机自测参考

检查启动与关机、原厂及新增预设选择、Fn 裁切图标、JPEG／RAW 拍摄与回放；扩展改动还应覆盖连拍、重启恢复、U 模式及相应专属功能。逐项记录通过、失败或未测，并绑定固件哈希。仿真不能替代整机加载和实际成像。

本次真机确认仅覆盖追加区完整加载、开关机、实际 RAW／JPEG 成像，详见[反馈记录](../../workspace/b2_iiix/hardware-b242.json)。

## 自定义预设

### 配置文件与可修改内容

`presets.json` 只定义 tone 编号与 `fits/` 文件的对应关系；配方文件保存曲线和色彩参数，其 `preset` 块定义 `name`、`icon_label`、`icon_rgb`、`full_curve`。图标 ID 由构建代码分配。

- 保留键 `25–32` 和八个槽位；当前配置加载器固定要求此范围。
- 图标标签为 1–4 个可打印 ASCII 字符，颜色为三个 0–255 整数。模板形状需修改源码。
- 名称、颜色和曲线等改动都会改变文件指纹。当前发布验证入口针对默认发布产物，不能作为自定义固件的通用校验入口，也不要改掉预期指纹来绕过检查。

### 图标与配置编辑

图标 ID 是代码中的查找编号，图标外观是根据配方生成的像素，两者分开处理。拍摄屏与回放使用同一组 `ICON_IDS`；想改名称、标签或颜色时，**不要改 ID**。

例如，在某个 `fits/*.json` 中修改现有 `preset` 块里的这些字段，其他字段保持原值：

```json
{
  "name": "Classic Neg",
  "icon_label": "NC",
  "icon_rgb": [60, 90, 140]
}
```

`icon_rgb` 控制**标签文字颜色**，不是底色。40×40 胶片轮廓以原厂 Positive Film 图标为模板，由 `make_icons.py::render` 绘制；修改底色、轮廓或尺寸属于源码改动。`full_curve` 决定曲线存储方式，影响空间占用，不要作为外观设置随意切换。

编辑前备份配方，保留数据结构、数组维度和必需字段；配置加载器检查 JSON、数值及部分容量限制，但不证明色彩正确或真机行为正常。源码 ZIP 可用于构建，不能当固件直接刷入；需配齐构建指南中的输入和依赖。

### 调整默认预设顺序

`presets.json` 指定八个槽位对应的 `fits/` 文件。复制配置后交换文件名即可调整顺序，保持键 `25–32` 和八套预设不变。例如交换前两套：

```json
{
  "25": "ektar100.json",
  "26": "portra400.json",
  "27": "gold200.json",
  "28": "pro400h.json",
  "29": "vision3-250d.json",
  "30": "classic-negative.json",
  "31": "vision3-500t.json",
  "32": "velvia50.json"
}
```

保存为 `workspace/b2_iiix/presets-example.json`：

```sh
venv/bin/python workspace/b2_iiix/presets_config.py workspace/b2_iiix/presets-example.json
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets-example.json workspace/b2_iiix/out/fwdc243b-example.bin
```

这只生成候选文件。默认发布验证入口固定检查发布产物，会拒绝修改后的产物；自定义完整检查流程尚未补齐，不应将构建成功视为可以刷入。新配方制作和内部参数编辑不在本说明范围内。

## 实现与空间约束

保留原厂影像控制框架中的记录与映射机制，新增配方数据、曲线和辅助代码存入 RTOS 追加区。当前构建追加 24 KiB；70 项分配共占 6236 字节。剩余容量包含按用途划分的空间和对齐约束，不能直接当作任意扩展预算。完整原厂补偿表、旧随机路径和 MA 区域保持原样。

新增显示 tone 为 25–32，照片 ImageTone 为 0x10C–0x113；菜单计数、EXIF、回放编号与图标必须同步。配置目前要求恰好八套配方，不能只改计数增加槽位。图标仍复用 HDF 状态及认证资源，独立资源改造在 TODO 中。

具体地址、分配账本及原厂区域用途见[补充审计](../research/storage-audit-20261017/followup/report.md)、构建报告与源码。旧版借用的两段补偿表区域已经确认占用，不得重新用于分配。跨型号或固件版本必须重新定位与验证。
