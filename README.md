# fvp_analysis — 文档仓库

这里的内容绝大部分是 AI 撰写的，作为最终目标「**HCB 自由编辑**」的前置分析材料存在；只要达到「开发者能读懂」的程度即可。

> 说明：`docs` 是一个 git 子模块（指向 `Huohua-newbie/fvpanalysis`）。本仓库在下一次 `git submodule update` 之前请保持此目录作为子模块引用。

---

## 目录总览

整理后的 `docs` 按「**文档 / 工具 / 数据 / 产物**」四大类组织：

```
docs/
├── 01_docs/            # 文档（可读的 .md/.typ 分析、规范、说明、论文）
├── 02_tools/           # 工具 / 脚本（.py 工具链、GUI、依赖提取）
├── 03_data/            # 数据（源样本 .hcb / 裸二进制、静态 .json 数据）
├── 04_outputs/         # 产物（反汇编 .lua/.tsv/.txt、IR、依赖图、复现脚本）
└── README.md           # 本索引
```

### 01_docs / 文档

| 目录 | 内容 |
|---|---|
| `01_docs/overview/` | 顶层综述与规范：`fvp_analysis项目规范文档`、`FVP引擎文献综述`、`z坐标具体含义分析` |
| `01_docs/ana/` | 博客式 FVP 逆向分析笔记（`ana_v2` 全套，01~09） |
| `01_docs/reversals/` | 逐函数反汇编对照 / 详细解析 / 典型功能块讲解 / LOGO 演出研究 |
| `01_docs/syscalls/` | syscall 语义详解（分组 01~32） |
| `01_docs/manual/` | 工具说明 / 教程类手册（可逆转换、SPEAK 编辑器、syscall 数据库、依赖图） |
| `01_docs/spec/` | 人类可读简表（`syscall_spec.txt`） |

### 02_tools / 工具

| 目录 | 内容 |
|---|---|
| `02_tools/hcb_ir/` | HCB 可逆转换工具链核心（`hcb_ir_core`、`hcb_to_ir`、`ir_to_hcb`、`roundtrip_verify`） |
| `02_tools/decode/` | 逐条反汇编 / 解码脚本（`_decode_*`、`_generate_syscall_db` 等） |
| `02_tools/rebuild/` | SPEAK 功能块 GUI、CG 显示等重建工具 |
| `02_tools/dep/` | 依赖图提取 / HTML 构建脚本 |

### 03_data / 数据

| 目录 | 内容 |
|---|---|
| `03_data/hcb_samples/` | 源样本：`Sakura.hcb`、`WA_funta.hcb`、`Sakura_SPEAK` |
| `03_data/fragments/` | 裸二进制片段（`f_*` 无扩展名） |
| `03_data/cfg/` | 静态配置 / IR 数据（`*.cfg.json`、`*.ir.json`） |
| `03_data/syscall_db/` | 机器可读 syscall 数据库（`syscall_spec.json`） |

### 04_outputs / 产物

| 目录 | 内容 |
|---|---|
| `04_outputs/lua_ir/` | Lua-like IR（`Sakura.lua`、`WA_funta.lua`、`f_*` 分段） |
| `04_outputs/disasm/` | 逐条反汇编 TSV / TXT |
| `04_outputs/diagrams/` | 依赖图（dot / html / json / csv） |
| `04_outputs/export/` | SPEAK 编辑器导出产物（`.lua` / `.tmp`） |
| `04_outputs/`（根） | 复现脚本（`logo演出.py`、`logo-test.py`、`*.rpy`） |

---

## 历史整理说明

本仓库原为扁平混杂结构（工具脚本、分析文档、样本、产物混在 `hcbtool_test/` 等目录）。本次已按上表重组，并用脚本领迁已同步修正各 `.md` / `.typ` 内的相对路径交叉引用。
