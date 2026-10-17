# GR IIIx B2.4.1 存储审计资料

[审计报告](report.md) · [结构化清单](audit-manifest.json)

日期：2026-10-17。范围：指定官方 IIIx 1.60 与 B2.4.1 BIN 的静态研究。未新增真机验证，不证明所有运行路径安全。

## 文件

| ID／文件 | 内容 | 限制 |
| --- | --- | --- |
| E1 / [ghidra.log](ghidra.log) | 原厂选定函数反编译、只读执行记录 | 初始数据库XREF覆盖不足；其0值不能证明无引用 |
| E2 / [arm-census.json](arm-census.json) | ARM直接分支、PC相对读取、对齐指针统计 | 线性解码可能把数据当成指令；未覆盖全部引用形态 |
| E3 / [comparison.json](comparison.json) | 输入哈希、边界字节、MA指针迁移 | 仅比较列出的字段／区域 |
| E4 / [data-references.log](data-references.log) | 两段数据区的有限引用扫描结果 | 不是间接引用穷尽证明 |
| [StorageAudit.java](StorageAudit.java) | Ghidra分析脚本 | 依赖正确的原厂RTOS、处理器、基址和项目 |
| [scan.py](scan.py)、[compare.py](compare.py) | E2／E3生成脚本原件 | 保留原研究工作区路径，不是本仓库根目录可直接运行的工具 |

证据与脚本的SHA256登记在manifest中。哈希用于发现文件变化，不保证分析结论正确。官方固件、解码RTOS、Ghidra项目及Python环境不包含在本目录。

## 路径与输入

原研究工作区布局如下，manifest的 `path_from_workspace_root` 字段和脚本路径均以该目录为基准：

```text
<research-root>/
  venv/
  tools/gr3-film-mods/work/fw/rtos_iiix.bin
  workspace/publishing/gr3x-fw-play/   # 本仓库checkout
    firmware/official-v160/fwdc243b.bin
    workspace/b2_iiix/out/fwdc243b-b241.bin
  workspace/storage-audit-20261017/   # 本目录脚本的原执行位置
```

如果只克隆本仓库，必须显式调整研究脚本的输入路径，或恢复上述外层布局；不要在缺少输入时替换为其他版本继续执行。E2读取外层解码RTOS，E3从本仓库checkout下的BIN解包；两者原厂RTOS的SHA已核对一致。

## 复现

以下命令在原研究工作区根目录执行；Python环境需已有Capstone与仓库固件解码依赖。先核对manifest中输入哈希，保存原证据后再运行。命令覆盖研究输出，不修改固件：

```sh
venv/bin/python workspace/storage-audit-20261017/scan.py > workspace/storage-audit-20261017/arm-census.json
venv/bin/python workspace/storage-audit-20261017/compare.py > workspace/storage-audit-20261017/comparison.json
```

E4从本仓库根目录调用当时的验证器：

```sh
python -c 'import sys;sys.path.insert(0,"workspace/b2_iiix");import verify_release as v;v.references(v.STOCK)'
```

验证器后续可能变化；复现时应记录代码提交及工具版本，不能把新输出视为旧快照的原始结果。

### Ghidra

本次使用Ghidra 12.1.4、OpenJDK 27、既有raw-binary项目，处理器为 `ARM:LE:32:v7`，基址 `0x53000000`。REA对原始RTOS的格式识别有限制，本次直接运行Ghidra，不是REA端到端分析。

在独立研究项目导入哈希匹配的原厂RTOS后，设置本机对应的路径与项目名，按以下方式执行；不要直接复制占位符：

```text
analyzeHeadless <project-dir> <project-name>
  -process rtos_iiix.bin -readOnly -noanalysis
  -scriptPath <audit-script-dir> -postScript StorageAudit.java
```

`-readOnly`应使临时反汇编／函数定义更改被丢弃，日志末尾应出现 `Discarding changes`。`-noanalysis`表明未运行完整自动分析。函数边界、失败处理函数和间接跳转仍需人工核对。

## 更新原则

新固件或新分析结果建立独立快照，保留本次输入身份和原始证据。同步更新区域、依赖、证据哈希及未完成项；不得把静态PASS提升为相机安全PASS。本目录不记录当前刷机或发布状态。
