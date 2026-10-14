# 源码构建与自测
 [English](BUILD.en.md)

以下命令在仓库根目录执行。已验证环境为 Apple Silicon macOS、Python 3.14、Homebrew LLVM，并使用系统字体 `DIN Condensed Bold.ttf`。其他环境未验证。

## 1. 安装依赖

```sh
brew install python@3.14 llvm
"$(brew --prefix python@3.14)/bin/python3.14" -m venv venv
venv/bin/pip install -r requirements.txt
```

## 2. 准备输入

将解压后的官方固件放入以下位置，必须使用指定版本：

| 文件 | 版本 |
|---|---|
| `firmware-inputs/fwdc243b.bin` | [GR IIIx 1.60](https://www.ricoh-imaging.co.jp/english/support/digital/gr3x_s.html) |
| `firmware-inputs/fwdc248b.bin` | [GR IV 1.11](https://www.ricoh-imaging.co.jp/english/support/digital/gr4_s.html)，仅用于提取参数 |

```sh
venv/bin/python scripts/prepare_inputs.py --iiix firmware-inputs/fwdc243b.bin --iv firmware-inputs/fwdc248b.bin
```

输入 SHA256 不匹配时停止；不要替换为其他版本或跳过检查。官方固件不随源码提供。

## 3. 构建默认 B2.4

保持 `presets.json` 和 `fits/` 不变：

```sh
mkdir -p workspace/b2_iiix/out
venv/bin/python workspace/b2_iiix/build_iiix.py --stock iiix --presets workspace/b2_iiix/presets.json workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

输出为 BIN 及同名 `.report.json`。构建报错后留下的文件不能使用。

## 4. 运行自测

```sh
venv/bin/python workspace/b2_iiix/verify_release.py workspace/b2_iiix/out/fwdc243b-b24-playback.bin
```

检查覆盖文件完整性、修改范围与空间边界、菜单与回放映射、ARM 仿真回归、故障注入及确定性重建。所有阶段 `PASS`、退出码为 0 才算完成；失败、超时、跳过或中断均不算通过。

- 报告：`workspace/b2_iiix/logs/qualification-*`。
- 默认每阶段超时 1800 秒，可用 `--timeout` 调整。
- 不使用 `python -O` 或 `PYTHONOPTIMIZE`，避免禁用断言检查。

通过后按[首页安装说明](../../README.md#直接固件安装)操作。电脑端检查不能代替相机自测。

## 自测参考

相机上检查快捷菜单与 MENU 选择、逐套 RAW+JPEG 拍摄、回放识别、电脑读取、原厂预设与机内 RAW 显影，以及反复切换和开关机。出现异常时保留配置、报告和样片。

这些是个人项目的自测参考，不代表全部已覆盖。当前仅有单台普通 IIIx 的反馈，留存样片覆盖七套新增预设、缺 Gold 200；其他机型和长期稳定性未验证。

## 调整默认预设顺序

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
