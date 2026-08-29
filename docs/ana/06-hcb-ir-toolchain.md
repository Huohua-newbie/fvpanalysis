# 06 · HCB 可逆转换工具链

> **前置阅读**：[02 · HCB 文件格式详解](./02-hcb-file-format.md)、[03 · VM 与指令集](./03-vm-and-opcodes.md)

本文介绍 `hcb可逆转换/` 目录下的工具链——它能把 HCB 转换成人类可读的形式，也能把编辑后的内容重新编译回 HCB。

---

## 设计目标

这套工具链的核心思路是：

> **HCB ↔ IR JSON（可逆的源事实） + CFG JSON（结构分析） + Lua-like 文本（人类阅读）**

它不是 `rfvp` 官方 Rust 工具链的复刻，而是为本项目建立的、更适合 Python 脚本处理、JSON 序列化和手工编辑的中间层。

---

## 数据流

```
HCB 文件
  │
  ▼ hcb_to_ir.py
  ├─ foo.ir.json    ← 可逆源事实（回编译依据）
  ├─ foo.cfg.json   ← 控制流图，用于结构分析
  └─ foo.lua        ← Lua-like 栈 IR，供人阅读
  │
  ▼ ir_to_hcb.py（编辑后）
  └─ rebuilt.hcb

  或者

  ▼ roundtrip_verify.py（验证）
  └─ 比对原始 HCB 与重建 HCB 是否二进制相同
```

---

## IR JSON 设计

`.ir.json` 是整个工具链的"单一事实来源"（source of truth）。它包含：

### 顶层字段

```json
{
  "sysdesc": { ... },        // 系统描述区（入口点、标题、导入表）
  "instructions": [ ... ],   // 扁平指令列表
  "functions": [ ... ],      // 函数划分（由 init_stack 启发式推断）
  "cfg": { ... }             // 控制流图
}
```

### 单条指令

```json
{
  "addr": 4,
  "opcode": 1,
  "mnemonic": "init_stack",
  "args": [3, 0],
  "size": 3,
  "raw_hex": "010300"
}
```

### 字符串指令的额外字段

对 `push_string`、游戏标题、syscall 名称，IR 同时保存原始字节和解码文本：

```json
{
  "mnemonic": "push_string",
  "args": { "text": "今日も晴れだ", "text_original": "今日も晴れだ" },
  "raw_hex": "0E0F..."
}
```

回编译时：若 `text` 与 `text_original` 相同（未修改），优先用 `raw_hex` 写回，确保 round-trip 一致；若已修改，则按指定编码重新编码字符串。

### ThreadStart 地址标记

当检测到以下模式时：

```
push_i32  <addr>
syscall   ThreadStart
```

该 `push_i32` 指令会被附加标记：

```json
"address_role": "thread_start_function_pointer"
```

回编译时，这类立即数参与地址重定位（不当普通整数处理）。

---

## CFG（控制流图）

`.cfg.json` 把代码划分为**基本块（basic block）**。

### 函数识别

以 `init_stack` 出现位置作为函数入口的启发式。这在实践中非常可靠，因为 FVP 脚本里几乎每个函数都以 `init_stack` 开头。

### 基本块分割

以下位置成为新基本块的起点（leader）：
- 函数入口
- `jmp` / `jz` 的目标地址
- `jmp` / `jz` / `ret` / `retv` 的后继指令

### 基本块数据

每个块包含：

```json
{
  "id": "BB_00000004",
  "start": 4,
  "end": 60,
  "instruction_addrs": [4, 7, 9, ...],
  "preds": [],
  "succs": ["BB_0000003D", "BB_00000034"],
  "term": "jz",
  "in_depth": 0,
  "out_depth": 0,
  "is_loop_header": false
}
```

其中 `is_loop_header` 通过检测**后向边**（back-edge，即 `jmp` 目标地址 < 当前地址）来标记循环头。

---

## Lua-like 栈 IR

`.lua` 文件是面向人类阅读的输出，不追求严格的 Lua 语法，而是用 Lua 语法**近似**表达栈机操作。

### 命名约定

| 写法 | 含义 |
|---|---|
| `S0`, `S1`, ... | 操作数栈槽位 |
| `a0`, `a1`, ... | 函数参数（`push_stack -N` 读到的） |
| `l0`, `l1`, ... | 局部变量 |
| `G[idx]` | 全局变量 |
| `GT[idx][key]` | 全局表访问 |
| `LT[idx][key]` | 局部表访问 |
| `__ret` | call/syscall 返回寄存区 |
| `__syscall("Name", ...)` | syscall 调用 |
| `goto BB_xxxxxxxx` | 基本块间跳转 |

### 示例输出

```lua
function f_00000004(a0, a1, a2)
  local S0, S1, S2
  ::BB_00000004::
  -- init_stack args=3 locals=0
  S0 = 1
  G[227] = S0
  S0 = G[227]
  __ret = f_000019E0(S0)
  S0 = G[2001]
  S1 = 0
  S0 = (S0 == S1)
  if __is_nil(S0) then goto BB_0000003D end
  ::BB_00000034::
  S0 = G[2001]
  S1 = 1
  S0 = (S0 + S1)
  G[2001] = S0
  ::BB_0000003D::
  -- ...
end
```

当前 `.lua` 输出保留 basic block 标签和 `goto`，而不尝试还原 `if/while` 结构。这是有意为之的——优先保证可追踪和可验证，结构化分析留给后续阶段。

---

## 命令行用法

### HCB → IR / CFG / Lua

```bash
python hcb_to_ir.py input.hcb --nls sjis
# 或指定输出目录和前缀
python hcb_to_ir.py input.hcb --nls gbk -o output_dir --prefix sample
```

输出：`sample.ir.json`、`sample.cfg.json`、`sample.lua`

### IR → HCB（回编译）

```bash
python ir_to_hcb.py sample.ir.json -o rebuilt.hcb
# 覆盖编码（如改为 GBK）
python ir_to_hcb.py sample.ir.json -o rebuilt.hcb --nls gbk
```

### Round-trip 验证

```bash
python roundtrip_verify.py input.hcb --nls sjis
# 写出重建文件以便比对
python roundtrip_verify.py input.hcb --nls sjis --write-rebuilt rebuilt.hcb
```

---

## 回编译规则

### 地址重定位

回编译时，先计算每条指令编码后的新地址，然后：

1. 更新 `sys_desc_offset`（文件头 4 字节）
2. 更新 `entry_point`
3. 修正所有 `call` / `jmp` / `jz` 的目标地址
4. 修正所有带 `address_role = "thread_start_function_pointer"` 的 `push_i32` 立即数

### 字符串重编码

- 未修改的字符串：优先用 `raw_hex` 写回，避免 round-trip 损失；
- 已修改的字符串：按 IR 中指定的 `nls`（`sjis`/`gbk`/`utf8`）编码为 C-string（含 NUL），长度 ≤ 255。

---

## 推荐分析工作流

1. 用 `hcb_to_ir.py` 生成三份输出文件；
2. 读 `.cfg.json` 了解函数划分和基本块跳转关系；
3. 读 `.lua` 理解每个基本块做了什么；
4. 查 `syscall_spec.json` 了解遇到的 syscall 的参数和副作用；
5. 若需要修改，编辑 `.ir.json` 中的字符串或其他字段；
6. 用 `ir_to_hcb.py` 重新编译；
7. 用 `roundtrip_verify.py` 确认未修改的部分保持二进制一致。

---

## 当前局限

1. **没有结构化 `if/while` 还原**：`.lua` 输出是带 `goto` 的扁平形式；
2. **没有独立高层 DSL**：当前源事实仍是 IR JSON，作者语言层留给后续阶段；
3. **只覆盖常见 opcode**（`0x00`–`0x27`）和主流 HCB 变体，旧版/特殊游戏可能需要扩展。

---

## 下一篇

[→ 07 · 案例：SPEAK 函数族分析](./07-case-study-speak-functions.md)
