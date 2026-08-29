# 02 · HCB 文件格式详解

> **前置阅读**：[01 · FVP 引擎总览](./01-overview.md)

HCB 是 FVP 引擎的脚本文件。它不是"台词文本容器"，而是一个完整的**二进制字节码程序**，包含代码、内联字符串、运行配置和 syscall 导入表。

---

## 整体布局

```
┌──────────────────────────────────────┐  ← 文件偏移 0x00
│  sys_desc_offset  (4 bytes, LE u32)  │
├──────────────────────────────────────┤  ← 0x04
│                                      │
│         代码区 (code area)            │
│   字节码指令 + 内联字符串，连续存放       │
│                                      │
├──────────────────────────────────────┤  ← sys_desc_offset
│         系统描述区 (sys_desc)         │
│   entry_point / 全局变量数 / 窗口模式   │
│   游戏标题 / syscall 导入表            │
└──────────────────────────────────────┘  ← 文件末尾
```

文件第一个 4 字节是 `sys_desc_offset`（历史上曾被叫做 `opcodeLength`、`code_end_offset`、`header_offset`）。它同时标记了：

- 代码区结束位置（exclusive）
- 系统描述区起始位置

---

## 系统描述区详解

从 `sys_desc_offset` 处开始，按顺序排列：

| 偏移（相对 sys_desc） | 大小 | 字段 | 说明 | 可信度 |
|---|---:|---|---|---|
| `+0x00` | 4 | `entry_point` | 主入口函数在文件中的地址 | 已证实 |
| `+0x04` | 2 | `non_volatile_global_count` | 非易失全局变量数 | 高可信 |
| `+0x06` | 2 | `volatile_global_count` | 易失全局变量数 | 高可信 |
| `+0x08` | 1 | `game_mode` | 分辨率/窗口模式索引 | 高可信 |
| `+0x09` | 1 | `game_mode_reserved` | 保留，原样保留 | 高可信 |
| `+0x0A` | 1 | `title_len` | 游戏标题长度（含末尾 NUL） | 已证实 |
| `+0x0B` | `title_len` | `title` | 游戏窗口标题字符串 | 已证实 |
| 随后 | 2 | `syscall_count` | 导入 syscall 数量 | 已证实 |
| 随后 | 变长 | `syscall_table` | syscall 导入表（见下） | 已证实 |
| 最后 | 2 | `custom_syscall_count` | 自定义 syscall 数量，常为 0 | 高可信 |

### `game_mode` 分辨率映射

| 值 | 分辨率 |
|---:|---|
| 0 | 640×480 |
| 1 | 800×600 |
| 6 | 1024×576 |
| 8 | 1280×720 |
| 14 | 1920×1080 |
| 15 | 1920×1200 |

（完整表格见规范文档，此处只列常见值。）

---

## syscall 导入表结构

每条导入条目的二进制布局：

```c
struct HcbImportEntry {
    u8  arg_count;   // VM 执行 syscall 时从栈里弹出的参数个数
    u8  name_len;    // syscall 名称字节长度（含末尾 NUL）
    char name[name_len];
}
```

HCB 代码区里的 `syscall` 指令只存**序号**（导入表里的位置），不存名字本身。运行时由 VM 用序号查导入表，再用名字查宿主实现。这和 PE 文件的"导入表"思路完全一样。

---

## 代码区：字节码 + 内联字符串

代码区从偏移 `0x04` 开始，到 `sys_desc_offset` 结束。里面是连续的字节码流。

**关键特征**：字符串不在独立的字符串表里，而是直接内联在代码里，作为 `push_string` 指令的变长操作数：

```
opcode: 0x0E (push_string)
  u8 len       ← 字符串字节长度（含末尾 NUL）
  u8[len] data ← 字符串内容，Shift-JIS 编码
```

这个设计意味着：**一旦文本长度发生变化，其后所有代码地址都会连锁偏移**。汉化、编辑 HCB 时必须重新修正所有跳转目标，这是最核心的工程难点之一。

---

## 地址修正：哪些地方存着代码地址？

修改文本后必须重算的地址项：

1. **`sys_desc_offset`**（文件开头 4 字节）
2. **`entry_point`**（系统描述区第一个字段）
3. 所有 **`call`** 指令的目标地址（4 字节立即数）
4. 所有 **`jmp`** 指令的目标地址
5. 所有 **`jz`（条件跳转）** 指令的目标地址
6. **`ThreadStart` 前的 `push_i32`**（函数指针特例，见下）

### ThreadStart 特例

`ThreadStart` syscall 用于在另一个上下文里启动一个函数。脚本里的写法是：

```
push_i32  <函数地址>   ← 这个立即数是代码地址，不是普通整数！
syscall   ThreadStart
```

回封 HCB 时，必须识别这一模式，把这里的 `push_i32` 当成地址来修正，否则线程会跳到错误位置。

---

## 标题的特殊地位

游戏标题存在系统描述区里，**不是**普通的 `push_string`。很多早期"只扫 pushstring"的工具提取文本时会漏掉标题，回封时也需要单独处理。

修改标题时同样需要更新 `title_len` 字段，确保长度字段和实际字节数匹配。

---

## 长度字段的统一约定

FVP 里所有"字符串长度"字段，都是**含末尾 NUL 的字节长度**：

- `title_len`
- `push_string` 的长度字节
- syscall 导入表里的 `name_len`

换算方式：`len = strlen(bytes) + 1`，最大值 255（因为长度字段是 `u8`）。

---

## 关于 CHB

项目内部有时出现 `.chb` 扩展名。它**不是新格式**——结构与 HCB 完全相同，只是一个工作流约定，表示"按 GBK 编码处理的 HCB"。没有必要为它建立独立的格式理论。

---

## 一份完整的 HCB 结构图（C 伪代码）

```c
struct HcbFile {
    u32  sys_desc_offset;         // 代码区结束 + 系统描述区起始

    u8   code[sys_desc_offset-4]; // 字节码 + 内联字符串

    // ── 以下从 sys_desc_offset 处开始 ──
    u32  entry_point;
    u16  non_volatile_global_count;
    u16  volatile_global_count;
    u8   game_mode;
    u8   game_mode_reserved;

    u8   title_len;               // 含 NUL
    char title[title_len];

    u16  syscall_count;
    HcbImportEntry syscall_table[syscall_count];

    u16  custom_syscall_count;    // 常为 0
}

struct HcbImportEntry {
    u8   arg_count;
    u8   name_len;                // 含 NUL
    char name[name_len];
}
```

---

## 下一篇

[→ 03 · VM 与指令集](./03-vm-and-opcodes.md)
