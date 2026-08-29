# fvp_analysis项目规范文档

## 0. 文档目的

本文档是 **`fvp_analysis` 项目内部使用的统一规范文档**，用于把当前已收集的 FVP/FAVORITE 相关参考资料，整理成一套可持续扩展的、可直接指导后续工具开发与语义建模的项目规范。

本文档当前重点规范：

- HCB 头部结构
- opcode 二进制编码
- opcode 真实语义
- syscall 导入表结构
- BIN 结构
- HZC 结构与变体
- loose override 规则
- locale / 文件名排序规则

并补充若干对后续工程非常重要的基础约定：

- 术语统一
- 状态标记体系
- VM 值模型、真假语义、栈帧模型
- 地址修正规则
- 编码/NLS 约定
- 当前已知歧义点与待验证事项

---

## 1. 适用范围与规范层级

## 1.1 适用范围

本文档目前主要适用于：

- `fvp_analysis/reference/` 中已收集的 FVP/FAVORITE 相关资料
- 当前工作区中的实验工具：`test`、`test2`、`test3`、`test4`、`test5`、`test6`
- 后续将在 `fvp_analysis/result/` 下生成的规范、语义表、IR、编译/反编译工具文档

## 1.2 规范优先级

当多个资料存在冲突时，本项目内部采用如下优先级：

1. **`rfvp-0.3.0` 运行时语义**：优先级最高，作为“现代可执行语义基线”
2. **`fvp-1.0` / `FVP-Yuki` / `my-sakura-moyu-main` / `GARbro` 源码**：作为格式与工具层证据
3. **早期逆向文章与经验文档**：作为补充与历史解释
4. **本项目实验工具（`test*`）**：作为工程化实现与中间结论

## 1.3 状态标记

本文档对每条结论使用以下状态标签：

- **[规范采用]**：本项目当前正式采用的定义或写法
- **[已证实]**：有多份源码/文档交叉印证
- **[高可信]**：有较强源码证据，但仍可能存在引擎版本差异
- **[待验证]**：目前仅有单侧证据、历史命名冲突或语义仍需实机确认
- **[超出当前范围]**：与项目后续可能有关，但当前不纳入本轮规范主线

---

## 2. 统一术语

## 2.1 文件与区域术语

### 2.1.1 HCB
- **定义**：FVP 引擎的脚本字节码文件
- **[规范采用]**：本文档统一把 `.hcb` 视为“代码区 + 系统描述区”的二进制脚本文件

### 2.1.2 CHB
- **定义**：本项目工作流中的一个命名约定，结构上仍视为 HCB
- **[规范采用]**：CHB = **按 GBK 工作流处理的 HCB 命名变体**，不视为另一种独立格式

### 2.1.3 `sys_desc_offset`
- **定义**：HCB 第 0x00 处 4 字节 little-endian 值，指向系统描述区起始位置
- **历史别名**：`opcodeLength`、`code_end_offset`、`header_offset`
- **[规范采用]**：项目内部统一使用 `sys_desc_offset`

### 2.1.4 代码区（code area）
- **定义**：HCB 中 `[0x04, sys_desc_offset)` 范围
- **内容**：连续的字节码指令与内联字符串

### 2.1.5 系统描述区（system description area）
- **定义**：HCB 中从 `sys_desc_offset` 开始到文件结束的区域
- **内容**：入口点、全局变量规模、窗口模式、标题、syscall 导入表等

### 2.1.6 loose file / loose folder override
- **定义**：游戏目录下直接存在的散文件或同名目录，用于覆盖 `.bin` 中的资源条目
- **[规范采用]**：loose override 规则视为 FVP 资源系统的一级特性，而不是 patch 技巧

### 2.1.7 标准 HZC
- **定义**：`hzc1 + NVSG + zlib payload` 的常规图像容器

### 2.1.8 TLG-HZC
- **定义**：`hzc1 + NVSG` 头部不变，但 payload 为 `TLG5.0` / `TLG6.0` / `TLG0 SDS` 等 TLG 数据流的变体

### 2.1.9 simple BIN/FVP
- **定义**：最常见的 FVP `.bin` 资源包结构，即“文件数 + 名字表长度 + 12字节索引表 + 名字表 + payload”
- **[规范采用]**：当前项目所说的 `BIN` 默认都指这一类，除非另行注明

---

## 3. 统一 VM 模型约定

> 本节不是用户显式点名要求的主题，但它直接决定 opcode 语义解释，因此纳入规范正文。

## 3.1 值模型（Variant）

根据 `rfvp` 当前实现，项目内部统一采用如下值模型：

- `Nil`
- `True`
- `Int(i32)`
- `Float(f32)`
- `String(String)`
- `ConstString(String, addr)`
- `Table(Table)`
- `SavedStackInfo(...)`

### 说明
- **[规范采用]** `ConstString(String, addr)` 用于表示脚本内联字符串，`addr` 是该字符串在 HCB 代码区中的地址/偏移身份
- **[规范采用]** `SavedStackInfo` 是 VM 栈帧内部值，不属于脚本层可见数据类型

## 3.2 真假语义（truthiness）

### 3.2.1 规范定义
- **[规范采用]** `Nil` 视为假
- **[规范采用]** 任意非 `Nil` 值视为真

### 3.2.2 推论
- `jz` / `jmpcond` 的条件判断应基于“falsey = Nil”而非“整数 0”
- 比较类 opcode 的结果应规范为：
  - 真 -> `True`
  - 假 -> `Nil`

### 3.2.3 关于 0x08/0x09 的历史冲突
- 早期资料常写成 `push0 / push1` 或 `pushfalse / pushtrue`
- 本项目采用 `rfvp` 的统一做法：
  - `0x08 = push_nil`
  - `0x09 = push_true`
- **状态**：**[高可信]**，但保留历史别名记录

## 3.3 栈帧模型

### 3.3.1 规范布局
根据 `rfvp/script/context.rs`，项目内部统一采用如下抽象：

```text
高地址方向

arg(n)
...
arg(0)
SavedFrameInfo   <- 相对当前 frame base 的 -1
local(0)         <- cur_stack_base
local(1)
...
stack top
```

### 3.3.2 规范要点
- `call` 通过压入 `SavedStackInfo` 建立新栈帧
- `init_stack` 负责写入参数个数、分配 locals
- `ret` / `retv` 恢复旧帧并回到返回地址

## 3.4 线程/上下文模型

### 3.4.1 规范定义
- **[规范采用]** FVP 的“线程”按项目内部统一视为 **脚本上下文 / 协程（Context）**，不是 OS thread
- **[规范采用]** 默认上下文槽位数为 32（ID 范围 `0..31`）

### 3.4.2 状态位
项目内部统一采用：

- `CONTEXT_STATUS_NONE = 0`
- `CONTEXT_STATUS_RUNNING = 1`
- `CONTEXT_STATUS_WAIT = 2`
- `CONTEXT_STATUS_SLEEP = 4`
- `CONTEXT_STATUS_TEXT = 8`
- `CONTEXT_STATUS_DISSOLVE_WAIT = 16`

---

## 4. HCB 文件规范

## 4.1 总体结构

### 4.1.1 规范布局

```c
struct HcbFile {
    u32 sys_desc_offset;          // 代码区结束 / 系统描述区起始
    u8  code[sys_desc_offset-4];

    u32 entry_point;
    u16 non_volatile_global_count;
    u16 volatile_global_count;
    u8  game_mode;
    u8  game_mode_reserved;

    u8  title_len;                // 含结尾 NUL
    char title[title_len];

    u16 syscall_count;
    repeat syscall_count {
        u8  arg_count;
        u8  name_len;             // 含结尾 NUL
        char name[name_len];
    }

    u16 custom_syscall_count;
}
```

### 4.1.2 结构状态
- `sys_desc_offset`：**[已证实]**
- `entry_point`：**[已证实]**
- `non_volatile_global_count / volatile_global_count`：**[高可信]**
- `game_mode / game_mode_reserved`：**[高可信]**
- `title`：**[已证实]**
- `syscall_count + import entries`：**[已证实]**
- `custom_syscall_count`：**[高可信]**，但旧工具普遍忽略

## 4.2 HCB 头部字段表

| 偏移 | 大小 | 名称 | 说明 | 状态 |
|---|---:|---|---|---|
| `0x00` | 4 | `sys_desc_offset` | 系统描述区起始偏移 | 已证实 |
| `0x04` | `sys_desc_offset-4` | `code_area` | 字节码与内联字符串 | 已证实 |
| `sys_desc_offset+0x00` | 4 | `entry_point` | 主入口函数地址 | 已证实 |
| `+0x04` | 2 | `non_volatile_global_count` | 非易失全局变量数量 | 高可信 |
| `+0x06` | 2 | `volatile_global_count` | 易失全局变量数量 | 高可信 |
| `+0x08` | 1 | `game_mode` | 分辨率/窗口模式索引 | 高可信 |
| `+0x09` | 1 | `game_mode_reserved` | 保留字节 | 高可信 |
| `+0x0A` | 1 | `title_len` | 标题长度，含 NUL | 已证实 |
| `+0x0B` | `title_len` | `title` | 窗口标题字符串 | 已证实 |
| `...` | 2 | `syscall_count` | 导入 syscall 数量 | 已证实 |
| `...` | 变长 | `syscall_table` | syscall 导入表 | 已证实 |
| `...` | 2 | `custom_syscall_count` | 自定义 syscall 数量 | 高可信 |

## 4.3 标题与长度字段约定

### 4.3.1 标题长度
- **[规范采用]** `title_len` 视为 **包含结尾 `0x00` 的 C 字符串长度**
- 重建时按 `strlen(title_bytes) + 1` 写入

### 4.3.2 `pushstring` 长度
- **[规范采用]** `pushstring` 的长度字节也视为 **包含结尾 `0x00` 的长度**

### 4.3.3 syscall 名称长度
- **[规范采用]** syscall 导入表中的 `name_len` 也视为 **包含结尾 `0x00` 的长度**

## 4.4 分辨率模式 `game_mode`

根据 `rfvp` 当前实现，项目内部当前采用以下映射：

| `game_mode` | 分辨率 |
|---:|---|
| 0 | 640x480 |
| 1 | 800x600 |
| 2 | 1024x768 |
| 3 | 1280x960 |
| 4 | 1600x1200 |
| 5 | 640x480 |
| 6 | 1024x576 |
| 7 | 1024x640 |
| 8 | 1280x720 |
| 9 | 1280x800 |
| 10 | 1440x810 |
| 11 | 1440x900 |
| 12 | 1680x945 |
| 13 | 1680x1050 |
| 14 | 1920x1080 |
| 15 | 1920x1200 |

**状态**：**[高可信]**，当前以 `rfvp` 为项目基线。

## 4.5 HCB 编码/NLS 约定

### 4.5.1 统一 NLS 枚举
- **[规范采用]** 本项目内部统一只使用以下三个 NLS 标识：
  - `sjis`
  - `gbk`
  - `utf8`

### 4.5.2 默认策略
- 原始日文脚本默认优先按 `sjis` 解释
- 中文回封工作流默认优先按 `gbk` 解释
- `utf8` 仅作为扩展工作流使用，不假定原始引擎天然支持

## 4.6 HCB 地址修正规范

当 HCB 中任意 `pushstring` 或标题字符串发生长度变化时，项目内部统一规定必须重算以下地址：

1. `sys_desc_offset`
2. `entry_point`
3. 所有 `call` 目标
4. 所有 `jmp` 目标
5. 所有 `jz/jmpcond` 目标
6. `pushint + syscall ThreadStart` 形式中的函数指针地址

### 4.6.1 ThreadStart 特例
- **[规范采用]** 若一个 `push_i32/pushint(32)` 后紧接 `syscall ThreadStart`，则该立即数按代码地址处理，而不是普通整数
- **状态**：**[已证实]**

---

## 5. syscall 导入表规范

## 5.1 二进制结构

### 5.1.1 规范定义

```c
struct HcbImportEntry {
    u8  arg_count;
    u8  name_len;     // 含 NUL
    char name[name_len];
}
```

### 5.1.2 说明
- `arg_count` 表示该 syscall 调用时应从 VM 栈中弹出的参数个数
- HCB 中 `0x03 syscall` 指令的操作数是 **导入表索引**，不是名字本身
- 名字解析由宿主引擎完成

## 5.2 运行时分发规则

### 5.2.1 规范流程
1. HCB 头部解析导入表
2. `syscall id` 在运行时查 `id -> import entry`
3. VM 按 `arg_count` 从栈中弹参数
4. 参数顺序反转为脚本调用顺序
5. 通过 `name` 在 syscall 宿主表中查找实现
6. 结果写入 `return_value`

### 5.2.2 项目内宿主语义基线
- **[规范采用]** 当前 syscall 真正语义以 `rfvp` 的 `GameData::do_syscall()` 与 `SYSCALL_TBL` 为基线

## 5.3 当前项目关注的 syscall 域

本项目当前将 syscall 按功能分为：

- 文本域：`TextPrint`、`TextSize`、`TextSpeed` 等
- 图像域：`GraphLoad`、`PrimSet*`、`GraphRGB`、`GaijiLoad`
- 音频域：`AudioLoad`、`AudioPlay`、`SoundPlay`
- 线程域：`ThreadStart`、`ThreadWait`、`ThreadSleep`、`ThreadNext`、`ThreadExit`
- 动画域：`Motion*`、`Dissolve`、`Snow*`、`LipSync`
- 影片域：`Movie`、`MovieState`、`MovieStop`
- 存档域：`SaveWrite`、`Load`
- 生命周期/窗口域：`WindowMode`、`ExitMode`、`ExitDialog`
- 其他域：`Flag*`、`History*`、`Input*`、`Timer*`、`Parts*`

---

## 6. opcode 编码规范

## 6.1 统一命名原则

为避免历史工具命名冲突，本项目对 opcode 采用：

- **二进制级 canonical mnemonic**：统一英文 snake_case
- **兼容别名**：保留旧工具写法，用于导入/反汇编兼容

例如：
- `init_stack` 兼容 `initstack`
- `push_i32` 兼容 `pushint`(32)
- `jz` 兼容 `jmpcond`
- `push_nil` 兼容 `push0/pushfalse`

## 6.2 操作数编码类型

| 名称 | 大小 | 说明 |
|---|---:|---|
| `null` | 0 | 无参数 |
| `i8` | 1 | little-endian 1字节有符号整数 |
| `i16` | 2 | little-endian 2字节整数（语义上常作 index/id） |
| `i32` | 4 | little-endian 4字节有符号整数 |
| `x32` | 4 | little-endian 4字节地址/无符号值 |
| `i8i8` | 2 | 两个连续的 i8 |
| `string` | 变长 | `u8 len` + `len` 字节（含末尾 NUL） |

## 6.3 全表（本项目 canonical）

### 6.3.1 控制流/调用类

| Hex | Canonical | 兼容别名 | 操作数 | 规范语义 | 状态 |
|---|---|---|---|---|---|
| `00` | `nop` | `nop` | `null` | 无操作 | 已证实 |
| `01` | `init_stack` | `initstack`, `entr` | `i8i8` | 读取参数个数与局部变量个数，初始化当前帧并分配 locals | 已证实 |
| `02` | `call` | `call`, `jal` | `x32` | 压入 `SavedStackInfo`，跳入内部函数 | 已证实 |
| `03` | `syscall` | `syscall`, `func` | `i16` | 按导入表序号调用宿主 syscall | 已证实 |
| `04` | `ret` | `ret`, `jr` | `null` | 无返回值返回；若返回地址为初始哨兵则线程退出 | 已证实 |
| `05` | `retv` | `ret2`, `ret1`, `jrt` | `null` | 以栈顶值为返回值返回 | 高可信 |
| `06` | `jmp` | `jmp`, `j` | `x32` | 无条件跳转到代码地址 | 已证实 |
| `07` | `jz` | `jmpcond`, `jc` | `x32` | 弹栈；若值为 falsey(`Nil`) 则跳转 | 高可信 |

### 6.3.2 常量/读取类

| Hex | Canonical | 兼容别名 | 操作数 | 规范语义 | 状态 |
|---|---|---|---|---|---|
| `08` | `push_nil` | `push0`, `pushfalse`, `lc0` | `null` | 压入 `Nil` | 高可信 |
| `09` | `push_true` | `push1`, `pushtrue`, `lc1` | `null` | 压入 `True` | 高可信 |
| `0A` | `push_i32` | `pushint`, `ll` | `i32` | 压入 32 位整数 | 已证实 |
| `0B` | `push_i16` | `pushint`, `lh` | `i16` | 压入 16 位整数 | 已证实 |
| `0C` | `push_i8` | `pushint`, `lb` | `i8` | 压入 8 位整数 | 已证实 |
| `0D` | `push_f32` | `pushfloat`, `lflt` | `x32` | 压入 32 位浮点数 | 已证实 |
| `0E` | `push_string` | `pushstring`, `lx` | `string` | 读取内联字符串并压入 `ConstString(text, addr)` | 已证实 |
| `0F` | `push_global` | `pushglobal`, `lr` | `i16` | 压入全局变量值，未初始化则压 `Nil` | 高可信 |
| `10` | `push_stack` | `pushstack`, `lf` | `i8` | 读取局部/栈变量并压栈 | 已证实 |
| `11` | `push_global_table` | `unk_11`, `lra` | `i16` | 弹出 key，从全局表读取 `global[idx][key]`，失败则 `Nil` | 高可信 |
| `12` | `push_local_table` | `unk_12`, `lfa` | `i8` | 弹出 key，从局部表读取 `local[idx][key]`，失败则 `Nil` | 高可信 |
| `13` | `push_top` | `pushtop`, `dup` | `null` | 复制当前栈顶 | 已证实 |
| `14` | `push_return` | `pushtemp`, `lt` | `null` | 压入 `return_value`，然后清空 `return_value` | 高可信 |

### 6.3.3 写入/表操作类

| Hex | Canonical | 兼容别名 | 操作数 | 规范语义 | 状态 |
|---|---|---|---|---|---|
| `15` | `pop_global` | `popglobal`, `sr` | `i16` | `global[idx] = pop()` | 已证实 |
| `16` | `pop_stack` | `copystack`, `sf` | `i8` | `local[idx] = pop()` | 已证实 |
| `17` | `pop_global_table` | `unk_17`, `sra` | `i16` | `value=pop(); key=pop();` 若 key 为 int，则确保全局目标为表后写入；否则清空为 `Nil` | 高可信 |
| `18` | `pop_local_table` | `unk_18`, `sfa` | `i8` | `value=pop(); key=pop();` 若 key 为 int，则确保局部目标为表后写入；否则清空为 `Nil` | 高可信 |

### 6.3.4 算术/逻辑/比较类

| Hex | Canonical | 兼容别名 | 操作数 | 规范语义 | 状态 |
|---|---|---|---|---|---|
| `19` | `neg` | `neg` | `null` | 对栈顶数值取负 | 已证实 |
| `1A` | `add` | `add` | `null` | 弹两值做加法 | 高可信 |
| `1B` | `sub` | `sub` | `null` | 弹两值做减法 | 高可信 |
| `1C` | `mul` | `mul` | `null` | 弹两值做乘法 | 高可信 |
| `1D` | `div` | `div` | `null` | 弹两值做除法 | 高可信 |
| `1E` | `mod` | `mod` | `null` | 弹两值做取模 | 高可信 |
| `1F` | `bit_test` | `test`, `bsel`, `bitTest` | `null` | 判断 `a` 的第 `b` 位是否置位，结果为 `True/Nil` | 高可信 |
| `20` | `and` | `logand`, `land` | `null` | 两值都非 `Nil` 则 `True`，否则 `Nil` | 高可信 |
| `21` | `or` | `logor`, `lor` | `null` | 任一值非 `Nil` 则 `True`，否则 `Nil` | 高可信 |
| `22` | `set_e` | `eq`, `seq` | `null` | 相等则 `True`，否则 `Nil` | 高可信 |
| `23` | `set_ne` | `neq`, `sne` | `null` | 不相等则 `True`，否则 `Nil` | 高可信 |
| `24` | `set_g` | `gt`, `sgt` | `null` | 大于则 `True`，否则 `Nil` | 高可信 |
| `25` | `set_ge` | `le`, `sge`（历史命名冲突） | `null` | **项目规范统一解释为 `>=`** | 高可信 |
| `26` | `set_l` | `lt`, `slt` | `null` | 小于则 `True`，否则 `Nil` | 高可信 |
| `27` | `set_le` | `ge`, `sle`（历史命名冲突） | `null` | **项目规范统一解释为 `<=`** | 高可信 |

## 6.4 关于 0x25 / 0x27 的规范裁定

为避免未来 IR/编译器继续传播旧命名混乱：

- **[规范采用]** `0x25` canonical 记为 `set_ge`
- **[规范采用]** `0x27` canonical 记为 `set_le`

原因：当前 `rfvp` 已明确指出历史命名存在反置问题，并已按语义修正助记符映射。

## 6.5 算术与比较的精确类型矩阵

- **[高可信]** 数值类运算主要作用于 `Int/Float`
- **[高可信]** 逻辑与比较结果规范为 `True/Nil`
- **[待验证]** 某些跨类型算术/比较的原始引擎精确矩阵仍需补充实机验证
- **[规范采用]** 当前工程语义基线默认跟随 `rfvp/script/mod.rs` 的 `Variant` 实现

---

## 7. BIN 结构规范

## 7.1 simple BIN/FVP 结构

### 7.1.1 规范布局

```c
struct FvpBin {
    u32 file_count;
    u32 name_table_size;

    repeat file_count {
        u32 name_offset;   // 相对名字表起点
        u32 data_offset;   // 相对 bin 文件起点
        u32 data_size;
    }

    char names[name_table_size]; // NUL 分隔
    byte payload[];
}
```

### 7.1.2 状态
- `file_count`：**[已证实]**
- `name_table_size`：**[已证实]**
- 单条目 12 字节：**[已证实]**
- 名字表 NUL 分隔：**[已证实]**

## 7.2 BIN 条目规则

### 7.2.1 名字字段
- **[规范采用]** 当前项目默认把 simple BIN 的名字字段视为 **Shift-JIS 字节串**
- 解码失败时允许回退到 `errors=replace` 形式的宽松策略，但不得覆盖原始字节

### 7.2.2 条目类型推断
本项目允许按前导签名猜测资源类型，例如：

- `hzc1` -> HZC
- `OggS` -> OGG
- `RIFF` -> WAV
- `\x89PNG` -> PNG
- `\xFF\xD8\xFF` -> JPG
- `BM` -> BMP
- `TLG5.0` / `TLG6.0` -> TLG

### 7.2.3 同目录 loose 覆盖
见第 9 节 VFS/override 规则。

## 7.3 BIN 重建排序规则

### 7.3.1 规范建议
- **[规范采用]** 若做无损重建，应优先保持原条目顺序
- **[规范采用]** 若从目录新建 BIN，文件名排序应优先模拟日文 locale 比较（见第 10 节）
- **[高可信]** 与原引擎/旧工具兼容时，包内文件名顺序可能影响某些比较/查找路径

## 7.4 旧格式 ACPX/XPK

`GARbro` 还实现了 Favorite 旧式 `ACPX/XPK` 归档：

- 签名 `ACPX` / `XPK01`
- 索引项固定 0x28 字节
- 数据可经 LZW 解压

### 规范态度
- **[超出当前范围]** 本项目当前规范主线不把它纳入“BIN 默认结构”
- 需要时应单列为“旧世代 Favorite 归档格式规范”

---

## 8. HZC / NVSG 结构规范

## 8.1 基本定位

### 8.1.1 规范定义
- **[规范采用]** 当前项目所说 “HZC” 默认指 `hzc1 + NVSG` 头部的图像容器
- **[补充说明]** 在某些工具实现中，`hzc1` 也被当作外层 deflate 包装标识；但本项目图像规范默认以内层存在 `NVSG` 为图像判断前提

## 8.2 标准头部结构

### 8.2.1 典型头部（44字节）

当 `header_size = 0x20` 时：

| 偏移 | 大小 | 名称 | 说明 | 状态 |
|---|---:|---|---|---|
| `0x00` | 4 | `magic` | 固定 `hzc1` | 已证实 |
| `0x04` | 4 | `uncompressed_size` | 解压后 raster 大小 | 已证实 |
| `0x08` | 4 | `header_size` | 常见为 `0x20` | 已证实 |
| `0x0C` | 4 | `payload_magic` | 固定 `NVSG` | 已证实 |
| `0x10` | 2 | `unknown1` | 常见 `0x0100` 等 | 高可信 |
| `0x12` | 2 | `type` / `bpp_flag` | 图像模式标志 | 已证实 |
| `0x14` | 2 | `width` | 宽度 | 已证实 |
| `0x16` | 2 | `height` | 高度 | 已证实 |
| `0x18` | 2 | `offsetX` | 游戏内显示偏移 X | 已证实 |
| `0x1A` | 2 | `offsetY` | 游戏内显示偏移 Y | 已证实 |
| `0x1C` | 2 | `unknown2` | 保留/未知 | 高可信 |
| `0x1E` | 2 | `unknown3` | 保留/未知 | 高可信 |
| `0x20` | 4 | `image_count` / `part_count` | 多帧/差分帧数，0 常视为 1 | 高可信 |
| `0x24` | 8 | padding/reserved | 直到总头长 44 字节 | 高可信 |

### 8.2.2 偏移字段类型
- **[规范采用]** `offsetX`、`offsetY` 统一按 **signed int16** 解释

## 8.3 `type` 字段规范

| 值 | canonical 名称 | 说明 | 状态 |
|---:|---|---|---|
| `0` | `rgb24` | 单帧 BGR24 图像 | 已证实 |
| `1` | `rgba32` | 单帧 BGRA32 图像 | 已证实 |
| `2` | `rgba32_multi` | 多帧/差分帧组 | 高可信 |
| `3` | `gray8` | 8位灰度 | 高可信 |
| `4` | `gray1_or_indexed_bw` | 黑白/二值近似类型 | 高可信 |

## 8.4 标准 payload 规范

### 8.4.1 标准 zlib 型
- **[规范采用]** 若 payload 以 zlib 流开头，则按 zlib 解压为 raw raster 数据
- `rgb24` -> `BGR`
- `rgba32` / `rgba32_multi` -> `BGRA`
- `gray8` -> 单通道
- `gray1_or_indexed_bw` -> 当前按基础黑白/索引近似支持

### 8.4.2 多帧型
- **[规范采用]** `type == 2` 时，`frame_size = width * height * 4`
- **[规范采用]** 若 `image_count > 0`，优先按该值切帧
- 若头部帧数与实际解压长度不匹配：
  - **[规范采用]** 可按 `len(raw) / frame_size` 自动修正，但必须记录修正行为

## 8.5 TLG-HZC 变体规范

### 8.5.1 识别规则
若 `hzc1 + NVSG` 头部后 payload 不是 zlib，而出现以下签名之一，则归类为 TLG-HZC：

- `TLG5.0`
- `TLG6.0`
- `TLG0.0\0sds\x1a`
- 对应 SDS 包裹变体

### 8.5.2 规范态度
- **[规范采用]** TLG-HZC 与标准 zlib HZC 视为同一外层家族的两个 payload 分支
- **[规范采用]** 工程上必须先识别 payload 类型，再决定解码路径
- **[高可信]** 对这类文件，可采用“提取 TLG -> 解码/合成 -> 重建为标准 HZC”的工作流

## 8.6 HZC 重建规则

### 8.6.1 必须保留的头部信息
- `type / bpp_flag`
- `width / height`
- `offsetX / offsetY`
- 多帧计数
- 必要的保留字段/原始 payloadHeader（如果目标是近似无损原样重建）

### 8.6.2 压缩等级
- **[高可信]** 对标准 zlib 型 HZC，使用压缩等级 9 常能复现原始 `0x78 0xDA` 风格输出
- **[规范采用]** 项目内部默认压缩等级使用 `9`

### 8.6.3 图像行序
- 早期经验文档常以“BMP 去头 + 行反转”理解标准 HZC
- **[规范采用]** 本项目在实现层统一以 **raw raster（BGR/BGRA）** 为基准表达，不再把 BMP 行序当规范本身

---

## 9. loose override / VFS 规则规范

## 9.1 总原则

### 9.1.1 规范结论
- **[已证实]** 同名外置目录/散文件与同名 `.bin` 可被视为同一资源命名空间
- **[已证实]** 外置 loose 文件/目录优先级高于 `.bin` 中对应条目

## 9.2 当前项目采用的查找顺序

### 9.2.1 文件级路径解析
给定逻辑路径 `folder/name` 或直接路径 `path` 时：

1. 先查 `<game_root>/<path>`
2. 若不存在，再拆成 `folder + entry_name`
3. 查 `<game_root>/<folder>/<entry_name>`（loose 目录覆盖）
4. 若仍不存在，则查 `<game_root>/<folder>.bin` 中的条目 `entry_name`

### 9.2.2 规范表述
- **[规范采用]** `loose > pack`
- **[规范采用]** `same-name folder` 与 `same-name .bin` 属同一资源域
- **[规范采用]** 所有新工具必须显式支持 override 顺序，而不能默认只读 `.bin`

## 9.3 项目建议

- 研究与创作初期优先使用 loose 资源覆盖进行快速验证
- 只有在需要产出最终分发资源时再考虑封回 `.bin`

---

## 10. locale / 文件名排序规则规范

## 10.1 统一结论

FVP 不是纯字节透明引擎，而是明显受日文 Windows locale 影响。

## 10.2 主要影响点

### 10.2.1 字符串比较
- **[已证实]** 某些工具/流程中，文件名排序或查找依赖 `CompareStringA(0x411, ...)`
- **[已证实]** 某些原始引擎行为会受 `lstrcmpiA` / `CompareString` 的 locale 影响

### 10.2.2 字体与 glyph
- **[已证实]** 字体创建与字形获取依赖 A/W API、charset 与 codepage
- 非日语系统下常需 loader/hook 修正

### 10.2.3 资源名解码
- **[已证实]** 若脚本按错误 codepage 解码，资源名字会发生错码，进而导致找图失败/崩溃

## 10.3 项目内部排序规范

### 10.3.1 BIN 重建排序
- **[规范采用]** 如需从目录新建或重建 `.bin`，应优先使用“日文 locale、忽略大小写”的排序语义
- 若运行环境无法直接调用 Win32 `CompareStringA(0x411, NORM_IGNORECASE, ...)`：
  - **[规范采用]** 优先保留原条目顺序
  - **[次优方案]** 才使用稳定的字节序/文件名字典序代替，并标注为兼容性降级

### 10.3.2 文件名编码
- **[规范采用]** simple BIN 中的名字表默认视为 Shift-JIS 字节串
- **[规范采用]** 任何“重命名资源”的操作都必须记录：
  - 原始字节名
  - 解码后文本名
  - 当前工作流目标名

---

## 11. 本项目建议增加的规范内容

## 11.1 HCB 文本替换规范

- `push_string` 字符串替换时，必须同时保留：
  - 字符串槽位顺序
  - 标题在尾部元数据中的独立位置
  - 地址修正表
- **[规范采用]** 标题不并入普通 `push_string` 序列处理

## 11.2 语音对位规范

- **[高可信]** 当扫描 HCB 时，若某个 `push_i32` 值远大于一般小整数且紧邻文本区域，允许把它暂记为语音 ID 候选
- **[规范采用]** 此类信息只能标注为“对位启发式”，不能在格式层写死成强约束

## 11.3 sys_desc 区原样保留原则

对当前尚未完全理解的字段：

- `game_mode_reserved`
- `custom_syscall_count`
- HZC 头部中的 `unknown1/2/3`

**[规范采用]**：

> 若当前工具没有充分理由改写这些字段，则应优先原样保留。

---

## 12. 当前待验证事项清单

以下内容暂不写死为绝对语义：

1. `0x11 / 0x12 / 0x17 / 0x18` 在不同引擎版本中的一致性
2. `0x25 / 0x27` 在旧版本引擎中的真实比较方向
3. `custom_syscall_count` 的真实用途
4. `type == 4` 的精确像素语义
5. TLG-HZC 在不同 HD/Steam 作品中的底图/差分关联编码方式
6. 老式 `ACPX/XPK` 归档是否应并入统一 Favorite 资源规范主文
7. HCB 原始开发语言与当前反汇编/IR 是否可完全一一对应

---

## 13. 本项目当前工程约定

## 13.1 文件命名约定

- 规范文档放在 `fvp_analysis/result/`
- 项目内部规范文档后续统一使用 Markdown
- 当前文档文件名：`fvp_analysis项目规范文档.md`

## 13.2 opcode 命名约定

- 规范文档中使用 canonical mnemonic
- 工具兼容层可接受历史别名
- 未来若建立 IR/DSL，默认也应复用 canonical mnemonic

## 13.3 NLS 约定

- 统一只写 `sjis` / `gbk` / `utf8`
- 不再混用 `shift-jis`、`ShiftJIS`、`gb2312` 等展示名作为规范名
- 若工具支持别名输入，应在解析层做映射，而不是在规范层扩散名字

## 13.4 HCB 工作流约定

- 原始脚本：优先视为 `HCB`
- 中文工作流脚本：可命名为 `CHB`，但底层格式按 HCB 处理
- 回封时必须区分：
  - 文本内容替换
  - 标题替换
  - 地址修正
  - ThreadStart 特殊地址修正

---

## 14. 规范摘要（供实现时快速查阅）

### HCB
- 第 0 字是 `sys_desc_offset`
- 代码区在 `[0x04, sys_desc_offset)`
- 系统描述区从 `sys_desc_offset` 开始
- `title_len` / `pushstring len` / `import name_len` 都按“含 NUL”处理
- `pushstring` 直接内联在代码区
- 文本改长短 -> 必修正地址

### opcode
- canonical：`push_nil`, `push_true`, `push_i32`, `push_string`, `jz`, `set_ge`, `set_le` 等
- 条件真假：`Nil` 为假，非 `Nil` 为真
- `ThreadStart` 前的函数地址 `push_i32` 需要参与重定位

### syscall 导入表
- `u8 arg_count + u8 name_len + name[name_len]`
- `syscall` 指令按索引调用，不直接带名字

### BIN
- `u32 file_count + u32 name_table_size + N*12 entry + names + payload`
- 当前项目默认名字表为 Shift-JIS
- 优先保留原条目顺序；新建包时优先按日文 locale 排序

### HZC
- 外层：`hzc1`
- 常见图像负载头：`NVSG`
- 典型总头长 44 字节
- `offsetX/offsetY` 必须保留
- `type 0/1/2/3/4` 分别对应 RGB24 / RGBA32 / 多帧 / 灰度 / 黑白近似
- payload 可能是 zlib，也可能是 TLG 变体

### override / locale
- loose file / folder > `.bin`
- 同名 folder 与同名 `.bin` 属同一资源域
- 文件名比较、排序、字体、资源查找会受日文 locale/codepage 影响

---

## 15. 后续文档衔接建议

建议在本规范基础上继续输出以下规范型文档：

1. `FVP syscall语义规范文档`
2. `HCB IR中间表示规范文档`
3. `BIN与HZC重建验证规范文档`
4. `FVP资源作者工作流规范文档`
5. `FVP原创最小工程模板规范文档`

---

## 16. 参考资料（本规范主要依据）

- `../reference/FAVORITE引擎VM及脚本结构分析/FAVORITE引擎VM及脚本结构分析.txt`
- `../reference/fvp-1.0/hcb_opcodes.h`
- `../reference/fvp-1.0/hcbdecoder.cpp`
- `../reference/fvp-1.0/hcbrebuilder.cpp`
- `../reference/fvp-1.0/nvsgconverter.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/hcb.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/hzc1.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/archive.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/text_codec.cpp`
- `../reference/rfvp-0.3.0/crates/rfvp/src/script/parser.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/script/context.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/script/opcode.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/vfs.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs`
- `../reference/GARbro-1.5.44/ArcFormats/Favorite/ArcBIN.cs`
- `../reference/GARbro-1.5.44/ArcFormats/Favorite/ArcFVP.cs`
- `../reference/GARbro-1.5.44/ArcFormats/Favorite/ArcHZC.cs`
- `../reference/GARbro-1.5.44/ArcFormats/Favorite/ImageHZC.cs`
- `../reference/my-sakura-moyu-main/binary/fvp_vm/include/VmBin.h`
- `../reference/my-sakura-moyu-main/binary/fvp_vm/include/VmInst.h`
- `../reference/my-sakura-moyu-main/binary/fvp_vm/include/VmEnv.h`
- `../reference/my-sakura-moyu-main/binary/fvp_vm/src/VmEnv.cpp`
- `../reference/my-sakura-moyu-main/binary/fvp_vm/src/VmInst.cpp`
- `../reference/my-sakura-moyu-main/fptool/include/fvp/package.h`
- `../reference/my-sakura-moyu-main/fptool/include/fvp/image.h`
- `../reference/my-sakura-moyu-main/fptool/src/package.cpp`
- `../reference/FVPLoader-Ver0.7-re/source/FVPKernel/FVPKernel.cpp`
- `../reference/关于星空HD自制汉化的一些记录/关于星空HD自制汉化的一些记录（from lilith🍁）.docx`
- `../reference/基于瞪眼法的F社资源文件解析/实操环节——以Wiz相关文件为例（上）.docx`
- `../reference/基于瞪眼法的F社资源文件解析/实操环节——以Wiz相关文件为例（下）.docx`
- `../reference/就算是笨蛋笨蛋也能用的星空的记忆HD汉化版制作指南/星空的记忆HD中文化攻略Plus.docx`
- `../../test/README.md`
- `../../test2/README.md`
- `../../test3/README.md`
- `../../test4/README.md`
- `../../test5/README.md`
- `../../test6/README.md`
