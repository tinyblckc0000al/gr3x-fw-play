# 源码构建与自测

[中文](BUILD.md) | [English](BUILD.en.md)

[返回首页](../../README.md)

以下命令在仓库根目录执行。已验证环境为 Apple Silicon macOS、Python 3.14、Homebrew LLVM，并使用系统字体 `DIN Condensed Bold.ttf`。其他环境未验证。

## 默认固件构建与自测

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

### 3. 构建默认 B2.4

保持 `presets.json` 和 `fits/` 不变：

```sh
mkdir -p workspace/b2_iiix/out
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets.json workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

输出为 BIN 及同名 `.report.json`。构建报错后留下的文件不能使用。

### 4. 运行自测

```sh
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

检查覆盖文件完整性、修改范围与空间边界、菜单与回放映射、ARM 仿真回归、故障注入及确定性重建。所有阶段 `PASS`、退出码为 0 才算完成；失败、超时、跳过或中断均不算通过。

- 报告：`workspace/b2_iiix/logs/qualification-*`。
- 默认每阶段超时 1800 秒，可用 `--timeout` 调整。
- 不使用 `python -O` 或 `PYTHONOPTIMIZE`，避免禁用断言检查。
- [文件指纹见首页](../../README.md#文件校验)，不要修改预期值来绕过检查。

默认 B2.4 通过后，将输出文件复制并命名为 `fwdc243b.bin`，按[首页安装说明](../../README.md#固件直接安装步骤)操作。电脑端检查不能代替相机自测。

### 5. 相机自测参考

相机上检查快捷菜单与 MENU 选择、逐套 RAW+JPEG 拍摄、回放识别、电脑读取、原厂预设与机内 RAW 显影，以及反复切换和开关机。出现异常时保留配置、报告和样片。

这些是个人项目的自测参考，不代表全部已覆盖。当前仅有单台普通 IIIx 的反馈，留存样片覆盖七套新增预设；其他机型和长期稳定性未验证。

## 自定义预设

### 配置文件与可修改内容

`presets.json` 只定义 tone 编号与 `fits/` 文件的对应关系；配方文件保存曲线和色彩参数，其 `preset` 块定义 `name`、`icon_label`、`icon_rgb`、`full_curve`。图标 ID 由构建代码分配。

- 保留键 `25–32` 和八个槽位；当前配置加载器固定要求此范围。
- 图标标签为 1–4 个可打印 ASCII 字符，颜色为三个 0–255 整数。模板形状需修改源码。
- 名称、颜色和曲线等改动都会改变文件指纹。现有 `verify_release.py` 只接受默认 B2.4，不能作为自定义固件的通用校验入口，也不要改掉预期指纹来绕过检查。

### 图标与配置编辑

图标 ID 是代码中的查找编号，图标外观是根据配方生成的像素，两者分开处理。拍摄屏与回放使用同一组 `ICON_IDS`；只改名称、标签和颜色时，不要改 ID。

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

这只生成候选文件。默认自测入口固定检查 B2.4，会拒绝修改后的产物；自定义完整检查流程尚未补齐，不应将构建成功视为可以刷入。新配方制作和内部参数编辑不在本说明范围内。

## 实现原理与扩展约束

### 实现原理

实现上复用原厂影像控制框架：将选定的旧记录槽位改造成新增预设记录，写入各自的色彩参数，并补充名称、图标和相关映射。菜单修复补上 `GetMaxCount` 的数量限制；回放修复扩展“EXIF → 播放枚举 → 显示 tone → 图标”三层映射，保留原厂条目。新增代码和数据放在指定空间内，最后重新打包固件并更新校验值，而不是直接向 BIN 末尾追加内容。

### 扩展槽位数量（进阶）

以下用于修改扩槽实现或移植固件；默认八套构建无需调整。地址是当前补丁的定位参考，不是通用文件偏移，移植时需重新确认指令和引用。

#### 1. 记录槽位与配置入口

`make_slots15.py` 使用以下旧记录槽位，为新增配方复制共享的 Standard 记录，并写入各自的色彩矩阵：

```python
LEGACY_SLOTS = (1, 2, 3, 4, 5, 7, 9, 8, 6)
assert 1 <= n <= len(LEGACY_SLOTS)
```

这只是底层列出的九个候选位置。当前 `presets_config.py` 固定接收八套、键为 `25–32`；第九套还要检查字符串、图标、曲线空间及所有映射，不能由此认定“还可以直接加一套”。超过九套则需重新设计记录存储。

#### 2. 图标资源与兼容性

```python
ICON_IDS = (0x05, 0x06, 0x07, 0x1D, 0x2D, 0x2E, 0x2A0, 0x2A1, 0x2A2)
NEW_ICON0, ICON_BOUND = 0x2A0, 0x29E
```

按现有源码的资源识别，前六个 ID 复用 HDF 开关状态、IIIx 认证标志及 TELE/71mm 裁切图标；后三个使用新增描述符。默认八套使用前八个 ID。

新 ID 通过补丁接入图标宽度、高度和绘制三个已知消费点。扩展时需检查其他直接索引图标表或判断上界的代码。HDF 等机型可能实际使用这些被复用的图标，不能直接套用；影响不限于新增预设自己的显示。

#### 3. 编号、计数与回放链路

Custom 1/2 使用显示 tone 23/24，新增胶片从 25 开始；默认八套的照片 ImageTone 编码为 `0x10C–0x113`（268–275）。显示 tone、照片编码和图标 ID 不是同一个编号。

| 补丁位置 | 用途 |
|---|---|
| `0x532C2ACC` | `GetCount` 内的数量指令，供拍摄列表使用；不是函数入口 |
| `0x532C2B7C` | `GetMaxCount`，供 MENU 列表使用 |
| `0x53283C08` | RAW 显影列表计数 |

修改数量时还需同步 index↔tone 表、EXIF 写入/解析和回放的“EXIF → 播放枚举 → 显示 tone → 图标”三层映射。只改计数可能让列表出现选项，却无法正确选择或回放。菜单计数中 `12 + m` 不含两套 Custom，相关列表总数为 `12 + m + 2`；不要把这些期望值混用。

#### 4. 空间预算与打包

B2.4 的 `PRESERVE_SPANS` 为两段半开区间：

| 区间 | 总容量 |
|---|---|
| `0x53D453F8–0x53D45CB0` | 2232 字节 |
| `0x53D39C8C–0x53D3A588` | 2300 字节 |

这些是区域总容量，**不是当前剩余空间**。普通三通道 knot 曲线占 198 字节，`full_curve` 三通道完整曲线占 1536 字节，此外还有表、对齐及其他分配开销。钩子代码和图标像素也有各自的借用区域，不能把所有容量相加当成任意可用空间。应以构建报告和分配器实际结果为准。

原厂可能读取看似空白的区域，不能未经引用和读取范围审计就扩大空间。构建保持 section 布局，经解码、修改、重新打包和校验；文件长度相同不等于内容有效。

#### 5. 原厂模式回归与验证

新增配方会使用曲线表指针。preserve 路径恢复共享指针，并保留 tone 21（Cross Process）的原厂分支，防止上一套胶片状态影响后续原厂模式。改动后应检查“胶片 → Cross Process → 其他原厂模式”的切换，不只是单独渲染一张照片。

扩展还需补齐配置对应的映射、边界、原厂模式与仿真测试。现有 `verify_release.py` 通过固定 SHA256 验证默认 B2.4，会拒绝新的构建；修改计数期望或替换指纹都不能代替完整的自定义验证。
