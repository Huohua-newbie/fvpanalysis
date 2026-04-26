# HCB 可逆转换说明（fvp_analysis 阶段三）

## 1. 目标

本目录提供一套面向 `fvp_analysis` 项目的 **HCB -> CFG -> IR -> HCB 可逆转换脚本**。

设计目标参考 `rfvp-0.3.0` 工作区中的：

- `crates/hcb2lua_decompiler`
- `crates/lua2hcb_compiler`
- `crates/rfvp/src/script/*`

但不直接复刻其内部 Rust 数据结构，而是为本项目建立一套：

- 更易于 JSON 序列化
- 更便于脚本处理
- 更利于人工编辑与后续 DSL/IR 扩展

的项目内中间表示。

---

## 2. 目录结构

- `hcb_ir_core.py`：核心库，负责 HCB 解码、IR/CFG 构建、Lua-like IR 输出、IR 回编译 HCB
- `hcb_to_ir.py`：命令行入口，执行 `HCB -> IR JSON + CFG JSON + Lua-like IR`
- `ir_to_hcb.py`：命令行入口，执行 `IR JSON -> HCB`
- `roundtrip_verify.py`：命令行入口，执行 `HCB -> IR -> HCB` 二进制回环验证
- `README.md`：本说明文档
- `指令与指令块功能对照表.md`：供人类阅读的功能对照说明

---

## 3. 数据流设计

### 3.1 转换链

```text
HCB
  -> decode flat instructions
  -> split functions
  -> build CFG (basic blocks, preds/succs, approximate stack depth)
  -> emit project IR JSON
  -> emit human-readable Lua-like stack IR
  -> edit IR JSON
  -> reassemble HCB
```

### 3.2 产物文件

对输入 `foo.hcb`，默认输出：

- `foo.ir.json`
- `foo.cfg.json`
- `foo.lua`

其中：

#### `foo.ir.json`
作为**可逆源事实（source of truth）**，包含：

- `sysdesc`
- 扁平 `instructions`
- `functions`
- `cfg`
- 原始字符串 raw hex（用于未修改时尽量保持原字节）

#### `foo.cfg.json`
用于：

- 控制流分析
- 函数/块结构观察
- 后续做结构化反编译、模式识别

#### `foo.lua`
用于：

- 给人类快速理解脚本行为
- 观察栈机表达式如何还原成近似可读逻辑
- 不是严格回编译输入，而是“面向阅读的 Lua-like 输出”

---

## 4. 当前 IR 的设计特点

## 4.1 扁平指令表

IR 中保留一个扁平 `program.instructions` 列表，每条指令包含：

- `addr`
- `opcode`
- `mnemonic`
- `args`
- `size`
- `raw_hex`

这样做的理由：

1. 最接近原始 HCB 二进制；
2. 最适合做回编译；
3. CFG 和函数划分都可由它派生；
4. 可以很方便地做地址修正与 round-trip 验证。

## 4.2 保留原始字符串字节

对于：

- `push_string`
- `game_title`
- syscall 名称

IR 中都同时保存：

- `text/name`
- `text_original/name_original`
- `raw_hex`

回编译时若文本未修改，则优先使用 `raw_hex`，以提高 round-trip 一致性。

## 4.3 ThreadStart 地址角色标记

若发现：

```text
push_i32 <addr>
syscall ThreadStart
```

则会给该 `push_i32` 附加：

```json
"address_role": "thread_start_function_pointer"
```

回编译时，该立即数也参与地址重定位。

---

## 5. CFG 设计

当前 CFG 采用基本块模型：

- 以函数起始 `init_stack` 为函数入口启发式
- 以以下目标建立 leader：
  - 函数起始
  - `jmp/jz` 目标
  - `jmp/jz/ret/retv` 后继指令
- 每个 block 记录：
  - `id`
  - `start`
  - `end`
  - `instruction_addrs`
  - `preds`
  - `succs`
  - `term`
  - `in_depth`
  - `out_depth`
  - `is_loop_header`

### 5.1 栈深度

当前 `in_depth/out_depth/max_depth` 是一种**近似静态求值**：

- 根据 opcode 的栈增减量传播
- `call` 的弹参个数依据函数起点的 `args_count`
- `syscall` 的弹参个数依据导入表里的 `arg_count`

这足以支撑当前阶段的：

- Lua-like 栈变量命名
- 基本块可读输出
- 后续的结构化分析

但还不是严谨的抽象解释器。

---

## 6. Lua-like IR 设计

### 6.1 目的

本项目输出的 `.lua` 文件不是“原始 Lua 源码恢复”，而是：

> 用 Lua 语法近似表达 HCB 栈机行为的可读文本。

### 6.2 主要特征

- 使用 `S0`, `S1`, ... 表示 operand stack 槽位
- 使用 `a0`, `a1`, ... 表示函数参数
- 使用 `l0`, `l1`, ... 表示局部变量
- 使用 `G[idx]` 表示全局变量
- 使用 `GT[idx][key]` / `LT[idx][key]` 表示表访问
- 使用 `__ret` 表示 call/syscall 返回寄存区
- 使用 `__syscall("Name", ...)` 表示 syscall
- 使用 `goto BB_xxx` 表示块间跳转

### 6.3 与 rfvp hcb2lua 的关系

与 `rfvp` 官方 `hcb2lua_decompiler` 相比：

- 相同点：
  - 都遵循 stack-machine reconstruction 思路
  - 都使用 `__ret`
  - 都把 syscall 映射成名字调用
- 不同点：
  - 本项目当前更强调“可逆与 JSON 配套”
  - 输出更直接保留 basic block 标签
  - 暂不追求完整结构化 `if/while` 还原，而优先保证可追踪与可验证

---

## 7. HCB 回编译规则

## 7.1 地址重定位

回编译时，按新编码后的指令长度重算：

- 所有指令新地址
- `sys_desc_offset`
- `entry_point`
- `call/jmp/jz` 目标地址
- `ThreadStart` 前的 `push_i32` 地址立即数

## 7.2 字符串重编码

- 若字符串文本未改，且保留了 `raw_hex`，优先直接写回原字节
- 若字符串文本已改，则按指定 `nls` 编码为 C-string（含 NUL）
- 长度必须 <= 255

## 7.3 当前已支持的对象

- HCB 头部 `sysdesc`
- syscall 导入表
- 常见 opcode `0x00..0x27`
- 函数切分与地址修正

---

## 8. 命令行用法

## 8.1 HCB -> IR/CFG/Lua

```bat
python fvp_analysis\result\hcb可逆转换\hcb_to_ir.py input.hcb --nls sjis
```

可选参数：

```bat
python fvp_analysis\result\hcb可逆转换\hcb_to_ir.py input.hcb --nls gbk -o output_dir --prefix sample
```

输出：

- `sample.ir.json`
- `sample.cfg.json`
- `sample.lua`

## 8.2 IR -> HCB

```bat
python fvp_analysis\result\hcb可逆转换\ir_to_hcb.py sample.ir.json -o rebuilt.hcb
```

可选覆盖编码：

```bat
python fvp_analysis\result\hcb可逆转换\ir_to_hcb.py sample.ir.json -o rebuilt.hcb --nls gbk
```

## 8.3 Round-trip 验证

```bat
python fvp_analysis\result\hcb可逆转换\roundtrip_verify.py input.hcb --nls sjis
```

可把重建文件写出来：

```bat
python fvp_analysis\result\hcb可逆转换\roundtrip_verify.py input.hcb --nls sjis --write-rebuilt rebuilt.hcb
```

---

## 9. 当前局限

## 9.1 还未直接支持“结构化 CFG -> if/while 还原”

当前 `.lua` 输出主要是：

- basic block
- goto
- 栈变量表达式

它是**便于读懂与追踪**的中间形态，而不是最终的高级结构化伪代码。

## 9.2 还未建立独立 DSL / 高级 IR

当前可逆源事实仍然是：

- `IR JSON`

而不是一套专门的“作者语言”。这符合阶段三目标：先建立可逆转换与可验证中间层。

## 9.3 未覆盖所有历史变体

当前实现主要面向：

- `fvp_analysis` 当前参考资料中的常见 HCB
- 以 `rfvp` 语义为基线的 opcode 映射

某些旧版/特殊游戏若存在：

- opcode 含义差异
- sysdesc 变体
- 自定义 syscall

则需要进一步扩展。

---

## 10. 推荐工作流

### 10.1 分析型工作流

1. `hcb_to_ir.py` 生成 `.ir.json/.cfg.json/.lua`
2. 读 `.cfg.json` 看函数和 basic block
3. 读 `.lua` 理解栈机行为
4. 查 `syscall语义数据库` 理解 syscall 效果
5. 若需要，再手改 `.ir.json`
6. 用 `ir_to_hcb.py` 回编译
7. 用 `roundtrip_verify.py` 验证未修改情况下是否一致

### 10.2 面向后续 DSL 的工作流

后续若进入更高层阶段，建议新增：

- `ir_to_structured.py`：CFG -> 结构化 IR
- `structured_to_ir.py`：结构化 IR -> 扁平 IR
- `dsl_to_ir.py`：作者语言 -> IR

当前目录的脚本则作为最底层稳定转换层保留。

---

## 11. 与后续阶段的衔接

本目录是阶段三的基础，可直接支撑后续：

### 11.1 syscall effect model
- `.lua` / `.cfg.json` 可与 `syscall_spec.json` 联动，给 call 点添加语义注释

### 11.2 模式识别
- 识别常见文本打印块
- 识别资源装载块
- 识别线程启动块
- 识别等待/分支/循环块

### 11.3 作者语言/原创工程
- IR JSON 可作为最初的“目标码层”
- 高层 DSL 只需最终编译到本 IR，再由 `ir_to_hcb.py` 落地

---

## 12. 总结

本目录当前已经建立了一套可运行的项目内基础转换链：

- `HCB -> IR JSON`
- `IR JSON -> CFG`
- `IR JSON -> Lua-like stack IR`
- `IR JSON -> HCB`
- `HCB -> IR -> HCB` 回环验证

其定位不是替代 `rfvp` 官方 Rust 工具链，而是：

> 为 `fvp_analysis` 项目提供一套更适合研究、文档化、手工编辑与后续 DSL 扩展的中间层。
