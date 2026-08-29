# 03 · VM 与指令集

> **前置阅读**：[02 · HCB 文件格式详解](./02-hcb-file-format.md)

FVP 的 VM 是一台**栈机**（stack machine）。理解它的关键不是死记每条指令，而是先建立正确的值模型和栈帧模型，然后再看指令如何在上面运作。

---

## 值类型（Variant）

VM 中的每个值都是以下类型之一：

| 类型 | 说明 |
|---|---|
| `Nil` | 假值，表示"无值"或"假" |
| `True` | 真值（注意：不是整数 1） |
| `Int(i32)` | 32 位有符号整数 |
| `Float(f32)` | 32 位浮点数 |
| `String(str)` | 普通字符串 |
| `ConstString(str, addr)` | 脚本内联字符串，额外携带其在代码区中的地址 |
| `Table(table)` | 关联表（类似 Lua table） |
| `SavedStackInfo(...)` | 栈帧保存信息（VM 内部用，脚本层不可见） |

### 真假语义

FVP 的布尔不是 C 风格的"0 为假"：

- **`Nil` = 假**
- **任何非 `Nil` 值 = 真**（包括整数 0！）

这点非常重要。`jz` 指令（条件跳转）弹出栈顶，若为 `Nil` 则跳转——不是判断值是否等于 0。比较指令（`set_e`、`set_g` 等）的返回值也规范为 `True` 或 `Nil`，而不是 1/0。

---

## 执行上下文（Context）

每个脚本"线程"对应一个 `Context` 对象，包含：

| 字段 | 说明 |
|---|---|
| `cursor` | 程序计数器（PC），指向当前要执行的字节 |
| `stack[256]` | 固定大小的操作数栈 |
| `cur_stack_base` | 当前帧的栈基址 |
| `cur_stack_pos` | 当前栈顶位置 |
| `return_value` | 最近一次 call/syscall 的返回值寄存区 |
| `state` | 线程状态位（RUNNING / WAIT / SLEEP / TEXT / DISSOLVE_WAIT） |

---

## 栈帧布局

调用一个函数（`call` 指令）时，VM 会在栈上压入 `SavedStackInfo` 来保存调用方的帧，然后跳入被调函数。被调函数开头的 `init_stack args locals` 负责：

1. 设置当前帧的参数个数
2. 在栈上为局部变量预留 `locals` 个 `Nil` 槽位

```
高地址方向
┌──────────────────┐
│   arg(n-1)       │
│   ...            │
│   arg(0)         │
│   SavedFrameInfo │  ← 调用者帧保存区，由 call 压入
│   local(0)       │  ← cur_stack_base
│   local(1)       │
│   ...            │
│   （操作数区）     │  ← 随指令执行动态变化
└──────────────────┘  ← cur_stack_pos (栈顶)
```

`push_stack -N` 用于读取当前帧里的参数（负偏移从 SavedFrameInfo 往前数到参数区）。

---

## 指令集全表

### 控制流 / 调用类

| Hex | 助记符 | 操作数 | 语义 |
|---|---|---|---|
| `00` | `nop` | — | 无操作 |
| `01` | `init_stack` | `i8 args, i8 locals` | 初始化当前函数帧 |
| `02` | `call` | `x32 addr` | 调用内部函数，压入 `SavedStackInfo` 后跳转 |
| `03` | `syscall` | `i16 id` | 按导入表序号调用宿主 syscall |
| `04` | `ret` | — | 无返回值返回；若返回地址为哨兵则线程退出 |
| `05` | `retv` | — | 以栈顶值为返回值返回 |
| `06` | `jmp` | `x32 addr` | 无条件跳转 |
| `07` | `jz` | `x32 addr` | 弹栈顶；若为 `Nil`（假）则跳转 |

> 历史别名：`init_stack` ← `initstack`；`jz` ← `jmpcond`；`retv` ← `ret1/ret2`

### 常量 / 读取类

| Hex | 助记符 | 操作数 | 语义 |
|---|---|---|---|
| `08` | `push_nil` | — | 压入 `Nil` |
| `09` | `push_true` | — | 压入 `True` |
| `0A` | `push_i32` | `i32` | 压入 32 位整数 |
| `0B` | `push_i16` | `i16` | 压入 16 位整数 |
| `0C` | `push_i8` | `i8` | 压入 8 位整数 |
| `0D` | `push_f32` | `x32` | 压入 32 位浮点数 |
| `0E` | `push_string` | `string` | 读取内联字符串，压入 `ConstString(text, addr)` |
| `0F` | `push_global` | `i16 idx` | 读取全局变量 `G[idx]`，未初始化则压 `Nil` |
| `10` | `push_stack` | `i8 idx` | 读取当前帧的参数或局部变量 |
| `11` | `push_global_table` | `i16 idx` | 弹 key，读取全局表 `GT[idx][key]` |
| `12` | `push_local_table` | `i8 idx` | 弹 key，读取局部表 `LT[idx][key]` |
| `13` | `push_top` | — | 复制当前栈顶 |
| `14` | `push_return` | — | 压入 `return_value`，然后清空它 |

> `push_string` 的 `ConstString` 携带地址（`addr`）是因为某些 syscall 会用字符串在脚本中的偏移位置作为唯一标识，而不只是内容。

### 写入 / 表操作类

| Hex | 助记符 | 操作数 | 语义 |
|---|---|---|---|
| `15` | `pop_global` | `i16 idx` | `G[idx] = pop()` |
| `16` | `pop_stack` | `i8 idx` | `local[idx] = pop()` |
| `17` | `pop_global_table` | `i16 idx` | `value=pop(); key=pop(); GT[idx][key]=value` |
| `18` | `pop_local_table` | `i8 idx` | `value=pop(); key=pop(); LT[idx][key]=value` |

### 算术 / 逻辑 / 比较类

| Hex | 助记符 | 语义 |
|---|---|---|
| `19` | `neg` | 栈顶取负 |
| `1A` | `add` | 弹两值做加法 |
| `1B` | `sub` | 弹两值做减法 |
| `1C` | `mul` | 弹两值做乘法 |
| `1D` | `div` | 弹两值做除法 |
| `1E` | `mod` | 弹两值做取模 |
| `1F` | `bit_test` | 判断 `a` 的第 `b` 位是否置位，结果 `True/Nil` |
| `20` | `and` | 两值都非 `Nil` → `True`，否则 `Nil` |
| `21` | `or` | 任一非 `Nil` → `True`，否则 `Nil` |
| `22` | `set_e` | 相等 → `True`，否则 `Nil` |
| `23` | `set_ne` | 不等 → `True`，否则 `Nil` |
| `24` | `set_g` | 大于 → `True`，否则 `Nil` |
| `25` | `set_ge` | 大于等于 → `True`，否则 `Nil` |
| `26` | `set_l` | 小于 → `True`，否则 `Nil` |
| `27` | `set_le` | 小于等于 → `True`，否则 `Nil` |

> **⚠️ 0x25 / 0x27 历史命名陷阱**：旧工具里这两个助记符经常写反（`le/ge` 对调）。本项目规范：`0x25 = set_ge`，`0x27 = set_le`。

---

## 操作数编码格式

| 类型 | 字节数 | 说明 |
|---|---:|---|
| `null` | 0 | 无操作数 |
| `i8` | 1 | 有符号 1 字节整数 |
| `i16` | 2 | little-endian 2 字节整数（常用于 id/index） |
| `i32` | 4 | little-endian 4 字节有符号整数 |
| `x32` | 4 | little-endian 4 字节地址或无符号值 |
| `i8i8` | 2 | 两个连续的 `i8`（`init_stack` 用） |
| `string` | 变长 | `u8 len` + `len` 字节字符串（含末尾 NUL） |

---

## 函数调用机制详解

### `call` 流程

1. 读取 4 字节目标地址；
2. 在栈上压入 `SavedStackInfo`（保存旧帧基址、旧栈顶、返回地址、参数个数占位）；
3. 更新 `cur_stack_base` 和 `cur_stack_pos`；
4. PC 跳转到目标地址。

### `init_stack args locals` 流程

被调函数开头执行：
1. 记录参数个数 `args`；
2. 在栈上预留 `locals` 个 `Nil` 作为局部变量初始值。

因此，**`init_stack` 是识别函数边界的可靠启发式**——几乎所有函数都以它开头。

### `ret / retv` 流程

1. 从栈上弹出 `SavedStackInfo`，恢复旧帧；
2. 恢复返回地址；
3. 清理调用者压入的参数；
4. `retv` 额外把返回值写入 `return_value`；
5. 若返回地址为 `usize::MAX`（哨兵），则线程真正退出。

### syscall 调用流程

1. 读取 2 字节导入序号；
2. 查导入表得到 `arg_count` 和函数名；
3. 从栈里弹出 `arg_count` 个参数（顺序反转为调用顺序）；
4. 通过名字查宿主 syscall 表，执行；
5. 结果写入 `return_value`（调用方若需要，用 `push_return` 取出）。

---

## 一个完整的函数调用示例

脚本里调用 `TextPrint(0, "今日も晴れだ")` 的字节码序列：

```
0C 00          push_i8 0              // 第 1 个参数：text buffer id
0E 0F 今日も晴れだ\0  push_string "今日も晴れだ"  // 第 2 个参数
03 XX XX       syscall <TextPrint_id>  // 调用 TextPrint
```

Lua-like 近似表达：

```lua
S0 = 0
S1 = "今日も晴れだ"
__ret = __syscall("TextPrint", S0, S1)
```

---

## 下一篇

[→ 04 · Syscall 系统](./04-syscall-system.md)
