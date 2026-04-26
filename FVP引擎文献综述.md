# FVP引擎文献综述：基于源码、逆向笔记与实验工具的综合分析

## 摘要

本文基于 `fvp_analysis/reference` 中收集的源码、逆向说明、工具工程与经验文档，并结合当前工作区中 `test`~`test6` 的实验性脚本，对 FAVORITE 社 FVP（Favorite View Point）引擎进行一轮面向“完全解析 HCB 脚本作用、最终支撑自由编辑与创作”的文献综述式总结。

本文重点论述四个方面：

1. **FVP 引擎的整体结构与运行方式**；
2. **HCB 脚本的文件结构、指令体系与运行逻辑**；
3. **BIN / HZC（NVSG）资源格式及其变体的结构解析**；
4. **参考资料中还能进一步推出的关键结论、歧义点与后续研究方向**。

本文的基本结论是：**FVP 本质上是一个“原生 EXE 内置 VM + 外置 HCB 字节码脚本 + 多类资源容器/外置目录覆盖 + 大量名字驱动型 syscalls”的视觉小说引擎体系**。要做到对 HCB 作用的“完全解析”，不能只停留在文本提取，而必须把以下四层同时打通：

- **HCB 文件层**：结构、地址修正、函数与控制流；
- **VM 执行层**：栈、线程、返回值、条件判断、表操作；
- **Syscall 语义层**：文本、图像、音频、动画、存档、线程、窗口等；
- **资源系统层**：BIN / HZC / 外置目录 / 编码与 locale / 文件名排序与查找规则。

---

## 0. 资料范围与方法

### 0.1 核心资料来源

本文主要参考以下资料簇：

### A. 直接源码类
- `reference/fvp-1.0/`：较早期的 FVP 工具源码，包含 HCB 解码/回封、NVSG(HZC) 转换。
- `reference/FVP-Yuki-1.0.2/`：图形化 HCB / BIN / HZC 工具，带较现代化的数据导出与重封逻辑。
- `reference/rfvp-0.3.0/`：Rust 重实现 FVP 引擎，提供最完整的“运行时视角”。
- `reference/my-sakura-moyu-main/`：包含 `fvp_vm`、`fptool` 等对 VM 与资源的再建模代码。
- `reference/GARbro-1.5.44/ArcFormats/Favorite/`：Favorite 格式在 GARbro 中的格式实现。
- `reference/FVPLoader-Ver0.7-re/`：用于在非日语系统上运行 FVP 游戏的 loader / hook 工程。

### B. 逆向说明与经验文档类
- `reference/FAVORITE引擎VM及脚本结构分析/FAVORITE引擎VM及脚本结构分析.txt`
- `reference/关于星空HD自制汉化的一些记录/关于星空HD自制汉化的一些记录（from lilith🍁）.docx`
- `reference/基于瞪眼法的F社资源文件解析/实操环节——以Wiz相关文件为例（上）.docx`
- `reference/基于瞪眼法的F社资源文件解析/实操环节——以Wiz相关文件为例（下）.docx`
- `reference/就算是笨蛋笨蛋也能用的星空的记忆HD汉化版制作指南/星空的记忆HD中文化攻略Plus.docx`

### C. 当前工作区的实验工具类
- `test/`：HCB 文本可视化编辑器
- `test2/`：HCB 完整脚本编辑器与脚本级重建器
- `test3/`：HZC / BIN 预览、封装与偏移导出工具
- `test4/`：TLG / PNG 互转与 SDS/TLG 分析工具
- `test5/`：TLG 型 HZC 重建为标准 HZC 的工具
- `test6/`：CHB/HCB 台词浏览导出工具

### 0.2 方法说明

本文采用的是**交叉印证**方法：

1. 先以 `rfvp-0.3.0` 与 `fvp-1.0` 提供“运行时”和“格式工具”两个核心视角；
2. 再用 `GARbro`、`FVP-Yuki` 与 `my-sakura-moyu-main` 对关键结构做横向验证；
3. 用民间文档与当前工作区 `test*` 工具总结其中的工程实践、歧义点与可验证结论；
4. 对仍有冲突的部分，明确标记为**命名歧义**或**待验证语义**，避免把现阶段猜测误写成铁律。

---

## 1. FVP 引擎的整体结构及运行方式

## 1.1 从部署形态看：FVP 不是“单文件脚本引擎”，而是一整套运行体系

综合 `FAVORITE引擎VM及脚本结构分析.txt`、`rfvp-0.3.0`、`星空HD中文化攻略Plus.docx` 与 `Wiz` 两篇实操文档，可以把典型 FVP 游戏目录概括为：

- 一个 **原生 Windows EXE**；
- 一个或多个 **`.hcb` 脚本文件**；
- 若干个 **`.bin` 资源包**，如 `graph.bin`、`voice.bin`、`bgm.bin`、`se_sys.bin`；
- 某些版本还存在**同名外置资源目录**，如 `graph/`、`graph_bs/`；
- 视频通常可直接以外部文件形式存在，如 `movie/` 目录中的 `wmv`。

也就是说，FVP 不是把所有内容打成一个巨大专有包，而是采取了：

> **EXE + HCB 字节码脚本 + BIN/HZC 等资源 + 外部文件覆盖**

的组合式架构。

这意味着：

- HCB 负责**叙事、控制流与资源调用**；
- BIN/HZC 负责**贴图、音频等资源承载**；
- EXE 负责**虚拟机与底层 syscall 实现**；
- 外置文件夹与同名 loose file 则提供了**天然的覆盖式 patch / mod 入口**。

---

## 1.2 启动过程：EXE 找 HCB，读头部，建导入表，再启动 VM 主线程

### 1.2.1 “第一个 HCB”规则

较早的逆向文档已指出：

- 引擎启动时，会以**找到的第一个 `.hcb` 文件**为准；
- 这意味着只要在目录里放一个新的、排序更靠前的 `.hcb`，就可能覆盖原来的主脚本入口。

这一点在 `reference/FAVORITE引擎VM及脚本结构分析/...txt` 有明确描述，而 `reference/rfvp-0.3.0/crates/rfvp/src/app.rs` 中 `App::find_hcb()` 的实现也与之呼应：它直接在游戏目录里 glob `*.hcb`，取第一个匹配结果。

这条规则对后续研究很重要，因为它说明：

- HCB 本身就是引擎的“程序入口描述物”；
- FVP 原生就具备某种程度的“脚本替换启动”特性；
- 将来做**独立原创工程**时，最小可行路径之一就是：先构造一个可启动的 HCB。

### 1.2.2 启动时读取 HCB 头部

`rfvp` 的 `boot.rs` 和 `script/parser.rs` 显示，现代重实现的启动流程大致如下：

1. 找到游戏目录中的 HCB；
2. 读取 HCB 文件前 4 字节，得到**代码区结束偏移 / 系统描述区起始偏移**；
3. 从该偏移开始，读取：
   - `entry_point`
   - 全局变量区大小相关字段
   - 分辨率模式 `game_mode`
   - 标题字符串
   - syscall 导入表
4. 根据导入表把 syscall 名称映射到宿主实现；
5. 根据 `entry_point` 启动主线程（线程 0）；
6. 再由每帧循环推动 VM 和资源系统前进。

这说明：

> HCB 不是“单纯的台词容器”，而是一个包含“代码段 + 运行配置 + syscall 导入表”的完整脚本二进制。

---

## 1.3 从 `rfvp` 看 FVP 运行时的模块化分层

`reference/rfvp-0.3.0/crates/rfvp/src/` 基本给出了一个非常清晰的现代化重构图谱。若把原始 FVP 引擎抽象成模块，可分为：

### 1.3.1 VM 与脚本层
- `script/parser.rs`：读取 HCB 文件头与导入表
- `script/context.rs`：单个脚本线程/协程执行上下文
- `script/opcode.rs`：opcode 枚举
- `script/inst/*`：反汇编/指令对象表示
- `script/mod.rs`：`Variant`、`Table` 等 VM 值类型

### 1.3.2 线程调度层
- `subsystem/resources/thread_manager.rs`
- `vm_runner.rs`
- `vm_worker.rs`
- `subsystem/resources/thread_wrapper.rs`

这一层表明 FVP 的“线程”并不是 OS thread，而是**脚本协程/上下文**。`VmRunner` 每帧只推进可运行上下文，遇到 `Wait` / `Sleep` / `TextWait` / `DissolveWait` 等状态则让它们挂起。

### 1.3.3 资源与游戏状态层
- `subsystem/world.rs`：`GameData`
- `subsystem/resources/vfs.rs`：资源查找与 bin 读取
- `text_manager.rs`、`save_manager.rs`、`videoplayer.rs`、`parts_manager.rs`
- `graph_buff.rs`、`texture.rs`、`gaiji_manager.rs`

`GameData` 里聚合了 FVP 运行所需的绝大多数状态：

- 历史文本
- flag 变量
- motion manager
- input manager
- timer manager
- video manager
- save manager
- 音频 player
- cursor 与 window 状态
- VFS
- 当前线程信息

这说明要“自由创作”或“完整模拟” FVP，并不只是写一个 HCB 编译器就够，还必须有**完整的运行态对象模型**。

### 1.3.4 Syscall 层
`subsystem/components/syscalls/` 基本相当于“FVP 引擎 API 的实现表”，包括：

- `text.rs`：文本打印、字号、位置、速度、跳过等
- `graph.rs`：图片、图元、sprite、Gaiji
- `sound.rs`：音频/音效/BGM
- `movie.rs`：影片
- `thread.rs`：ThreadStart / Wait / Sleep 等
- `motion.rs`、`other_anm.rs`：运动、LipSync、Snow、Dissolve
- `saveload.rs`：存档/读档
- `flag.rs`、`history.rs`、`input.rs`、`timer.rs`、`parts.rs`
- `utils.rs`：WindowMode、ExitMode、随机数、调试等

对 HCB“具体作用”的完全解释，本质上就是要把：

> **opcode 层的控制流** + **syscall 层的宿主语义**

同时解释清楚。

---

## 1.4 每帧运行逻辑：FVP 是“脚本 VM + 场景/运动系统”并行推进的引擎

根据 `rfvp` 中 `app.rs`、`vm_runner.rs`、`anzu_scene.rs`，可以将 FVP 风格运行逻辑概括为：

```text
启动：
  读取 HCB -> 解析头部/导入表 -> 建立 VFS -> 启动主脚本线程(entry_point)

每帧：
  1. 更新输入、时间
  2. 执行场景 on_update
     - 更新位移/透明/缩放/旋转/V3D/雪/溶解等动画
  3. 执行 VM runner
     - 遍历所有可运行脚本上下文
     - 每个上下文持续 dispatch opcode
     - 遇到 Wait/Sleep/TextWait/DissolveWait/ThreadNext/ThreadExit 等请求则让出执行
  4. 执行场景 late_update
     - 主要处理文本逐字显示、文本完成后的线程恢复
  5. 渲染当前 prim / text / texture / movie 状态
  6. 重置本帧输入边沿状态
```

这是一种非常典型的**视觉小说状态机架构**：

- HCB 决定“做什么”；
- syscall 改写 `GameData`；
- 场景系统根据 `GameData` 推进动画和可视状态；
- 渲染器把 `GameData` 中的最终状态绘出来。

因此，**HCB 脚本并不是直接画图或直接播音**，它更像是“命令流”，通过 syscall 操作引擎状态，再由场景/渲染系统兑现成画面和声音。

---

## 1.5 资源查找顺序：外置目录/散文件优先，BIN 为后备

这一点在文档与源码之间形成了非常漂亮的互证。

### 文档侧结论
`星空HD中文化攻略Plus.docx` 与 `Wiz` 文档都反复强调：

- 同名文件夹可以和同名 `.bin` 被视为同一资源目录；
- 且**文件夹中的资源优先级高于 `.bin`**；
- 删除后缀的 loose 文件也可能被引擎直接读取；
- 这正是许多民间 patch 的工作基础。

### `rfvp` 源码侧结论
`reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/vfs.rs` 清楚实现了这一顺序：

1. 先尝试直接打开 `<game_root>/<path>`；
2. 若失败，再解析 `folder/name`，去 `<folder>.bin` 中找对应条目；
3. `VfsFile::open_stream()` 也先查 loose override，再回退到 pack entry。

因此可以把 FVP 的查找规则总结为：

> **Loose file / loose folder override > 同名 `.bin` 包内条目**

这意味着 FVP 具有很强的 patch 友好性。对你的最终目标来说，这一点非常重要：

- 在早期研究阶段，很多资源修改根本不需要完整重封；
- 只要放入外置目录/文件即可验证逻辑；
- 原创化阶段也可以先采用 loose 资源开发，再决定是否封回 `.bin`。

---

## 1.6 Locale / codepage 依赖：FVP 是高度日文 Windows 语境化的引擎

`FVPLoader-Ver0.7-re` 与 `星空HD中文化攻略Plus.docx`、`关于星空HD自制汉化的一些记录.docx` 共同表明：

FVP 原始引擎对以下内容存在明显的**日文 Windows 依赖**：

- `CompareStringA` / `lstrcmpiA` 的 locale 比较结果；
- `CreateFontA` / `EnumFontFamiliesExA` 的字体 charset；
- `GetGlyphOutlineA` 的字符转 glyph 过程；
- 某些窗口与菜单 API 的 A/W 版本行为；
- 脚本与资源名字的 Shift-JIS 解码结果。

`FVPLoader` 的 Hook 方向非常有代表性：

- 把字符串比较固定到日文 locale `0x411`；
- 将字体创建改为宽字符/指定 charset；
- 在 `GetGlyphOutline` 中按 codepage 932 做转换；
- 把窗口类与消息也转换到宽字符路径。

这说明：

> FVP 的“编码问题”不只是台词乱码问题，而是**资源查找、字体匹配、排序比较、UI API 调用**都会被 locale 影响。

这也是为何“直接把引擎改成 GBK 读脚本”往往会导致：

- 中文能显示；
- 但立绘名、资源名、比较逻辑、字体逻辑开始崩。

---

## 2. 脚本结构及脚本运行逻辑

## 2.1 HCB 文件的归一化结构

综合 `FAVORITE引擎VM及脚本结构分析.txt`、`fvp-1.0/hcbrebuilder.cpp`、`rfvp/script/parser.rs`、`my-sakura-moyu-main/binary/fvp_vm/src/VmEnv.cpp`，可把 HCB 结构统一表达为：

```c
struct HcbFile {
    u32 code_end_offset;          // 也是系统描述区起始偏移 / 旧文所称 HcbHeader 偏移
    u8  code[code_end_offset-4];  // 从文件偏移 0x04 开始到 header 前结束

    // 以下从 code_end_offset 开始：
    u32 entry_point;              // 主入口函数在文件中的偏移
    u16 non_volatile_global_count;
    u16 volatile_global_count;
    u8  game_mode;                // 分辨率/窗口模式索引
    u8  game_mode_reserved;       // 保留字节

    u8  title_len;                // 含结尾 NUL
    char title[title_len];

    u16 syscall_count;
    repeat syscall_count {
        u8  arg_count;
        u8  name_len;             // 含结尾 NUL
        char name[name_len];
    }

    u16 custom_syscall_count;     // 常见为 0，旧工具往往忽略
}
```

### 关于“中间那 6 个字节”的统一解释

较早期工具 `fvp-1.0/hcbrebuilder.cpp` 在重建脚本时，把 `entry_point` 之后的 6 字节笼统当作：

- `BIN = xx xx xx xx xx xx`

不做语义解释，只要求原样保留。

而 `rfvp/script/parser.rs` 则明确把这 6 字节解释为：

- `u16 non_volatile_global_count`
- `u16 volatile_global_count`
- `u8 game_mode`
- `u8 game_mode_reserved`

因此可以认为：

- **旧工具知道这 6 字节必须保留，但没完全命名；**
- **新重实现已经给出了更清晰的解释。**

### `game_mode` 的作用

`rfvp` 还把 `game_mode` 映射为分辨率，例如：

- `1 -> 800x600`
- `6 -> 1024x576`
- `7 -> 1024x640`
- `14 -> 1920x1080`

这证明 HCB 头部里不只存剧情入口，也存**窗口/分辨率信息**。

---

## 2.2 HCB 不是“字符串表”，而是内联文本的字节码文件

HCB 最大的特征之一是：

> **台词字符串直接作为 `pushstring` 指令的操作数，嵌在代码段内部。**

也就是说，HCB 更像是：

- 一段连续的 VM bytecode；
- 字符串不是单独的表，而是某些 opcode 的变长操作数。

这也是为什么一旦文本长度变化：

- 其后代码地址整体偏移；
- `call` / `jmp` / `jmpcond` 以及特殊的 `ThreadStart` 函数指针都必须一起修正。

这点在以下资料中高度一致：

- `reference/关于星空HD自制汉化的一些记录/repack.py`
- `reference/fvp-1.0/hcbrebuilder.cpp`
- `reference/FVP-Yuki-1.0.2/.../src/hcb.cpp`
- `test2/hcb_script_core.py`

---

## 2.3 VM 运行时数据结构：从旧文档的 `ScriptObject` 到 `rfvp` 的 `Context`

### 2.3.1 旧逆向资料中的 `ScriptObject`

`FAVORITE引擎VM及脚本结构分析.txt` 给出了一个早期逆向得到的 `ScriptObject` 轮廓，核心字段包括：

- `scriptBuffer`
- `StackEntry st[0x100]`
- `scriptPos`（当前执行位置）
- `stackDepth`
- `curStackBase`
- `temp`（临时返回值/寄存位置）

### 2.3.2 `rfvp` 中的 `Context`

`rfvp/script/context.rs` 的 `Context` 几乎提供了现代化等价物：

- `cursor`：程序计数器 PC
- `stack: Vec<Variant>`：固定栈（长度 0x100）
- `cur_stack_pos`
- `cur_stack_base`
- `return_value`
- `state`：线程状态位
- `wait_ms` / `sleep_ms`
- `should_exit` / `should_break`

因此可以把 FVP 的脚本执行单元理解为：

> **一个带固定栈、局部帧基址、程序计数器、返回寄存区和状态位的轻量级协程上下文。**

### 2.3.3 值类型 `Variant`

`rfvp/script/mod.rs` 把 VM 值抽象为：

- `Nil`
- `True`
- `Int(i32)`
- `Float(f32)`
- `String(String)`
- `ConstString(String, addr)`
- `Table(Table)`
- `SavedStackInfo(...)`

这非常关键，因为它解释了：

- 为什么部分 opcode 是“真假值风格”而不是 C 风格整数布尔；
- 为什么 `pushstring` 需要保留**脚本内偏移地址**；
- 为什么 0x11/0x12/0x17/0x18 最终会落到“表访问”语义上；
- 为什么 `call` / `ret` 实际上是用 `SavedStackInfo` 维护栈帧。

---

## 2.4 指令体系：HCB 是一套小型栈机指令集

综合 `fvp-1.0/hcb_opcodes.h`、旧逆向说明、`rfvp/script/opcode.rs` 与 `my-sakura-moyu-main/binary/fvp_vm/include/VmInst.h`，FVP 常见 opcode 可按功能分组如下。

## 2.4.1 控制流 / 调用类

- `0x01 initstack`：初始化当前函数帧，声明参数数与局部变量数
- `0x02 call`：调用内部函数（跳转到 HCB 代码区内地址）
- `0x03 syscall`：按导入表序号调用系统函数
- `0x04 ret`：无返回值返回
- `0x05 ret1 / retv`：带返回值返回
- `0x06 jmp`：无条件跳转
- `0x07 jmpcond / jz`：条件跳转（按栈顶真假决定）

## 2.4.2 常量 / 取值类

- `0x08`：假值压栈（旧资料有 `push0`，`rfvp` 用 `PushNil` 建模）
- `0x09`：真值压栈
- `0x0A / 0x0B / 0x0C`：压入 32/16/8 位整数
- `0x0D`：压入浮点数
- `0x0E pushstring`：压入脚本内联字符串
- `0x0F pushglobal`：读取全局变量
- `0x10 pushstack`：读取局部/栈变量
- `0x11 / 0x12`：旧资料未明；`rfvp` 解释为全局/局部表读取
- `0x13 pushtop`：复制栈顶
- `0x14 pushtemp / push_return`：读取最近 syscall/call 返回值

## 2.4.3 赋值 / 存储类

- `0x15 popglobal`：写全局变量
- `0x16 copystack / local_copy`：写局部变量
- `0x17 / 0x18`：旧资料未明；`rfvp` 解释为全局/局部表写入

## 2.4.4 算术 / 逻辑 / 比较类

- `0x19 neg`
- `0x1A add`
- `0x1B sub`
- `0x1C mul`
- `0x1D div`
- `0x1E mod`
- `0x1F bitTest`
- `0x20 and`
- `0x21 or`
- `0x22 eq`
- `0x23 neq`
- `0x24 gt`
- `0x25`、`0x27`：比较助记符在不同实现中存在命名翻转/误名
- `0x26 lt`

### 关于 0x08 / 0x09 与 0x25 / 0x27 的命名歧义

这一点必须单独强调，因为它直接影响未来做“规范化 HCB IR”的准确性。

#### 0x08 / 0x09
- 旧逆向说明倾向于：`0x08 = false/0`，`0x09 = true/1`
- `fvp-1.0/hcbdecoder.cpp` 的注释名却出现了 `pushtrue/pushfalse` 的反向命名
- `rfvp` 最终采用的是：`0x08 -> Nil(falsey)`，`0x09 -> True(truthy)`

从 `jz`/`jmpcond` 的实际条件使用方式看，`rfvp` 的理解更接近“条件真假语义”。

#### 0x25 / 0x27
- 传统助记符常写成 `le / ge`
- 但 `rfvp` 明确指出历史命名与真实运算存在错位
- 因为栈机弹栈顺序和“a op b”的构造方式会影响对 `>=`/`<=` 的直观命名

因此，**未来构建标准 IR 时，不应机械继承旧助记符，而应以实际执行语义为准。**

---

## 2.5 函数、栈帧与返回机制

`rfvp/script/context.rs` 对 FVP 函数调用机制给出了非常清晰的现代解释：

### 2.5.1 `initstack`
`initstack` 读取两个 `i8`：

- `args_count`
- `locals_count`

然后：

- 更新当前帧的参数个数；
- 在栈上为 locals 预留 `Nil` 空间。

这与旧文档中“函数起始几乎总以 InitStack 开头”的经验高度吻合，因此：

> 用 `InitStack` 扫描函数边界，仍是识别函数的有效启发式。

### 2.5.2 `call`
`call` 的逻辑是：

1. 读取目标地址；
2. 在栈上压入 `SavedStackInfo`，保存：
   - 旧 `stack_base`
   - 旧 `stack_pos`
   - `return_addr`
   - 参数个数（稍后由 `initstack` 补齐）
3. 切换 `cur_stack_base` 与 `cur_stack_pos`
4. 把 PC 跳到目标地址。

### 2.5.3 `ret / retv`
返回时：

- 恢复 `SavedStackInfo` 中的栈帧信息；
- 恢复返回地址；
- 弹出参数；
- 若返回地址是 `usize::MAX`，则表示线程真正结束。

这说明 FVP 函数调用本质上就是**小型解释器中的手工栈帧切换**。

---

## 2.6 Syscall：HCB 与引擎宿主世界的连接点

### 2.6.1 导入表机制

HCB 文件尾部带一个 syscall 导入表。脚本里的 `0x03 syscall i16` 只存**导入序号**，不直接存函数名。

因此执行过程是：

1. `Parser` 从 HCB 头部解析出导入表；
2. VM 执行到 `syscall` 时，通过 `id -> name` 找到导入名；
3. 再把 `name` 交给宿主侧的 syscall 实现表。

这与 PE/ELF 的“导入表/符号表”思想很像，所以旧文档才会说：

> HCB 最后那部分“很像一个 PE 的输入表”。

### 2.6.2 `rfvp` 中的 syscall 分发

`world.rs` 中 `GameData` 实现了 `VmSyscall`：

- `do_syscall(name, args)`
- 再通过 `SYSCALL_TBL` 找到对应的 `Syscaller` 对象

这表明 syscall 的最终本质是：

> **根据名字，把 VM 参数转交给引擎宿主状态对象 `GameData`，从而改变引擎状态。**

### 2.6.3 syscall 的主要功能域

从 `rfvp` 的 syscall 注册表可见，FVP syscall 至少覆盖这些域：

- **文本域**：`TextPrint`、`TextFont*`、`TextSpeed`、`TextSize`、`TextPause`
- **图像域**：`GraphLoad`、`GraphRGB`、`PrimSet*`、`GaijiLoad`
- **音频域**：`AudioLoad`、`AudioPlay`、`SoundPlay`
- **线程域**：`ThreadStart`、`ThreadWait`、`ThreadSleep`、`ThreadNext`、`ThreadExit`
- **动画域**：`Motion*`、`Dissolve`、`SnowStart`、`LipSync`
- **影片域**：`Movie`、`MovieState`、`MovieStop`
- **存读档域**：`SaveWrite`、`Load` 等
- **窗口/生命周期域**：`WindowMode`、`ExitMode`、`ExitDialog`
- **输入/标志/历史/计时/部件** 等。

所以从分析角度说，HCB 对游戏“具体做了什么”，最终都可以归结为：

- 控制流跳转到哪里；
- 压了哪些参数；
- 调了哪个 syscall；
- 这些 syscall 修改了 `GameData` 的哪些子系统。

---

## 2.7 FVP 的“线程”其实是脚本协程

### 2.7.1 线程数量与结构

`rfvp/subsystem/resources/thread_manager.rs` 直接初始化了 32 个 `Context`。这和旧工具及民间脚本中广泛出现的“线程 ID 范围 0..31”高度一致。

### 2.7.2 `ThreadStart` 的特殊性

`ThreadStart` 在 FVP 生态里是一个非常关键的 syscall，因为它常通过如下方式传入代码地址：

- 先执行 `pushint` 压入函数地址；
- 紧接着 `syscall ThreadStart`。

因此在 HCB 回封时，不能只修普通 `call/jmp/jmpcond` 的地址；还必须修：

> **“紧邻 `syscall ThreadStart` 的 `pushint` 立即数地址”**

这一点在：

- `reference/关于星空HD自制汉化的一些记录/repack.py`
- `reference/FVP-Yuki-1.0.2/.../src/hcb.cpp`
- `test2/hcb_script_core.py`

中都是明确逻辑。

### 2.7.3 线程状态机

`rfvp/script/context.rs` 和 `thread_manager.rs` 给出的状态位有：

- `RUNNING`
- `WAIT`
- `SLEEP`
- `TEXT`
- `DISSOLVE_WAIT`

而 `VmRunner.tick()` 每帧只推进 `RUNNING` 且不在这些阻塞态中的上下文。

这说明 FVP 线程模型本质上是：

> **协作式、事件驱动式的多上下文调度**，而不是抢占式多线程。

因此理解 HCB 的关键不是“它开了几个系统线程”，而是：

- 哪个上下文在跑；
- 它何时因文本、等待、动画、存档而挂起；
- 又何时被场景系统/输入系统恢复。

---

## 2.8 文本、标题、语音与资源名在脚本中的角色

## 2.8.1 `pushstring` 就是文本本体

HCB 中文本最直接的来源是 `0x0E pushstring`。`rfvp/context.rs` 在执行它时：

- 先读长度字节；
- 再读对应编码字符串；
- 压入 `ConstString(text, addr)`。

这里保留 `addr` 的原因很重要：

- 原始 FVP 引擎会把脚本内字符串偏移当作一种稳定身份；
- 某些 syscall 不只是“拿到字符串内容”，还会依赖它在脚本缓冲区中的位置。

## 2.8.2 标题在头部，不在普通代码流里

多份资料一致表明：

- 游戏标题不是普通 `pushstring` 文本；
- 它位于 HCB header 区域，位置大约是 `opcodeLength + 10` 开始；
- 回封时必须单独处理。

这也是很多早期“只扫 `pushstring`”的工具需要额外补标题编辑的原因。

## 2.8.3 脚本中还包含资源名

`星空HD中文化攻略Plus.docx` 很强调一点：

- HCB 中不仅有台词，也包含大量资源名；
- 比如人物立绘名、背景名、音乐名、graph/graph_bs 路径项。

这与运行逻辑是完全一致的：HCB 并不是“纯文本剧本”，而是**带资源调度的演出脚本**。

## 2.8.4 语音 ID 的经验性提取

`FVP-Yuki/src/hcb.cpp` 采用一种很有价值的工程性启发：

- 在扫描 HCB 时，如果遇到 `0x0A pushint` 且数值很大（如大于一百万），就暂时把它记为 `lastVoice`；
- 当后面紧跟着 `pushstring` 时，把这个 `lastVoice` 绑定到该文本；
- 从而导出 `voice_map.json`，并把它映射到 `voice.bin` 中的 `voice_id.ogg`。

这未必是严格的语言学/编译学结论，但它是一个非常实用的**剧情-语音对位启发式**，对后续做自动分析、对照导出、语音回放很有价值。

---

## 2.9 HCB 提取与回封的关键规则

### 2.9.1 文本长度变化会造成地址连锁偏移

这是 HCB 回封最核心的事实：

- 代码段不是“指令区”和“字符串表”分离；
- 字符串本身嵌在代码里；
- 一旦替换文本导致长度变化，其后的所有地址都可能变。

### 2.9.2 必须修正的地址项

根据 `repack.py`、`hcb.cpp`、`hcb_script_core.py`，至少要修：

- 文件头第 0 字节处的 `code_end_offset/opcodeLength`
- 头部里的 `entry_point`
- 所有 `call`
- 所有 `jmp`
- 所有 `jmpcond/jz`
- 特殊的 `pushint + syscall ThreadStart` 函数指针地址

### 2.9.3 导入表、标题、尾部元数据要保留

HCB 回封并不是“把字符串换掉”就结束，必须保证：

- `TITLE`
- `ENTRYPOINT`
- “那 6 个头部字节”
- `NUM_IMPORTS`
- import 列表
- `custom_syscall_count`

都保持正确或原样回写。

因此在工程上，`test2/hcb_script_core.py` 所采用的“完整脚本视图 + 属性区重建”思路，比简单文本替换更接近将来真正的**可编译 HCB IR**。

---

## 3. BIN 及 HZC 资源文件的结构解析

## 3.1 常见 FVP `.bin` 资源包格式

最常见的 FVP `.bin`（如 `graph.bin`、`voice.bin`、`bgm.bin`）结构，在 `Wiz` 文档、`GARbro ArcBIN.cs`、`rfvp/vfs.rs`、`my-sakura-moyu-main/fptool/package.cpp` 中高度一致。

可归纳为：

```c
struct FvpBin {
    u32 file_count;
    u32 name_table_size;
    repeat file_count {
        u32 name_offset;   // 相对文件名表起点
        u32 data_offset;   // 相对整个 bin 文件起点
        u32 data_size;
    }
    char names[name_table_size]; // NUL 分隔
    byte payloads[];             // 按各 offset/size 存储
}
```

### 关键结论

- **文件名前缀表与数据表分离**；
- 每个条目固定占 12 字节；
- 名字表是 NUL 分隔字符串区；
- 数据本体可能是：
  - `hzc1` / `NVSG`
  - `OggS`
  - `RIFF`
  - `PNG/JPG/BMP`
  - 其他二进制。

`GARbro` 的 `ArcBIN.cs` 也会按数据签名去猜测条目类型。

---

## 3.2 BIN 中的文件名排序不是随意的：它带有日文 locale 特征

`my-sakura-moyu-main/fptool/src/package.cpp` 中一个非常关键、但常被忽略的细节是：

- 包内文件名集合是用 `CompareStringA(0x411, NORM_IGNORECASE, ...)` 进行比较排序的。

这说明至少在一部分 FVP 生态工具链/引擎逻辑里：

> **文件名顺序与“日文 locale 排序规则”有关。**

这与 `星空HD中文化攻略Plus.docx` 中对 `CompareString` / `lstrcmpiA` 引发的文件查找崩溃现象形成了互证：

- 资源名字不是单纯的“字节相等”问题；
- 排序、二分查找、区分大小写/locale 比较都可能参与资源定位；
- 因而重新打包 `.bin` 时，**文件名顺序最好复现原规则**，否则可能出现“包能打开但游戏崩”的情况。

这是后续做“原创资源包生成器”时必须正视的问题。

---

## 3.3 GARbro 中还存在另一类旧格式：`ACPX/XPK` 变体

`reference/GARbro-1.5.44/ArcFormats/Favorite/ArcFVP.cs` 显示，Favorite 体系里还存在一种更老的归档格式：

- 文件头签名 `ACPX` / `XPK01`（或 `_PCA` / `_PK.1`）
- 索引项大小 0x28
- 条目可以带 LZW 压缩

这说明 FVP 资源归档并非全程只有一种 `.bin` 结构，而是至少存在：

1. **现代常见的 simple BIN/FVP**（`file_count + name_table + 12-byte entries`）
2. **更旧的 ACPX/XPK 层级式归档**

就你当前的研究目标而言，应优先聚焦第一类；但做“完整 FVP 家族工具”时，需要把第二类留作扩展对象。

---

## 3.4 标准 HZC / NVSG 图像结构

### 3.4.1 头部结构

综合 `GARbro/ImageHZC.cs`、`fvp-1.0/nvsgconverter.cpp`、`test3/nvsg_image_core.py`、`test5/rebuild_hzc.py`、`FVP-Yuki/src/hzc1.cpp`，常见 zlib 型 HZC 文件可归一化为：

| 偏移 | 大小 | 含义 |
|---|---:|---|
| `0x00` | 4 | `"hzc1"` |
| `0x04` | 4 | 解压后数据大小（raw raster size） |
| `0x08` | 4 | header size，常见 `0x20` |
| `0x0C` | 4 | `"NVSG"` |
| `0x10` | 2 | 固定/未知字段，常见 `0x0100` 或等效值 |
| `0x12` | 2 | 类型/位深标志 `type` |
| `0x14` | 2 | 宽度 |
| `0x16` | 2 | 高度 |
| `0x18` | 2 | `offsetX` |
| `0x1A` | 2 | `offsetY` |
| `0x1C` | 2 | 保留/未知 |
| `0x1E` | 2 | 保留/未知 |
| `0x20` | 4 | 帧数 / part count（0 视为单帧） |
| `0x24` | ... | 剩余保留到 `0x0C + header_size` |
| 数据区 | 变长 | 通常为 zlib 压缩的像素数据，或某些变体中的 TLG 负载 |

当 `header_size = 0x20` 时，整个文件头总长就是：

- `12 + 0x20 = 44` 字节。

### 3.4.2 `type` 字段的常见取值

`GARbro/ImageHZC.cs` 与 `test3/nvsg_image_core.py` 的对应关系大致为：

- `0`：24 位 BGR
- `1`：32 位 BGRA
- `2`：32 位多帧 / 差分帧
- `3`：8 位灰度
- `4`：1bit/黑白 或简化二值映射

其中最常见的是：

- `0`：背景/UI 等不带 alpha 的图
- `1`：立绘/按钮等带 alpha 的图
- `2`：表情差分、多帧帧组

### 3.4.3 `offsetX / offsetY` 的作用

多份文档与源码一致证明：

- 这两个字段表示图像在游戏中的显示偏移；
- 它们不是“图片内容的一部分”，而是**场景合成参数**；
- 替换图片时必须保留，否则画面位置会错。

这也是为何很多 HZC 重建工具都要求：

- 不能只根据 PNG 本身重新猜头；
- 必须读取原始 HZC 头部并继承偏移字段。

---

## 3.5 标准 zlib HZC 的像素负载语义

### 3.5.1 更稳妥的现代解释：解压后是原始 raster

较新的工具源码（`fvp-1.0/nvsgconverter.cpp`、`FVP-Yuki/hzc1.cpp`、`test3`、`test5`）都更倾向于把 HZC 理解为：

- zlib 压缩的**原始像素栅格数据**；
- 24 位时按 `BGR`；
- 32 位时按 `BGRA`；
- 灰度/二值按对应通道解释。

这比早期民间“BMP 去头 + 行反转”的描述更适合程序实现。

### 3.5.2 为什么旧文档常说“像去掉 BMP 头再反转行序”

`Wiz` 的下篇文档把标准 HZC 理解为“无头 BMP 数据 + 行倒序 + zlib 压缩”，其实也不算错，只是它使用了 BMP 作为中介来理解数据。

本质上二者等价于：

- 若你把 HZC 解压数据直接当 BMP 像素阵列来拼文件头，可能需要额外处理行序；
- 若你直接把它当原始 BGR/BGRA raster，则只需按相应通道方式交给图像库即可。

就今天的工程实践来说，推荐采用后一种解释。

---

## 3.6 多帧 / 差分 HZC

`type == 2` 的 HZC 是研究中必须重点注意的对象。

### 3.6.1 帧切分

`GARbro/ArcHZC.cs` 的做法是：

- 读取 `count = file.ReadInt32(0x20)`；
- 若为 0 则按 1 帧；
- 用 `frame_size = unpacked_size / count` 来切出多个 frame。

`test3/nvsg_image_core.py` 与 `test5/rebuild_hzc.py` 也采用了类似思路。

### 3.6.2 差分资源的两种处理视角

在民间文档与实际工具中，对这类资源至少有两种视角：

1. **逐帧视角**：把每个 frame 当作独立图像，用于预览和分析；
2. **差分合成视角**：把某些 frame 当作叠加到底图的差分图，用于最终显示/重建。

`test5/rebuild_hzc.py` 就是在做后一类工作：

- 识别 TLG 型 HZC；
- 若带差分底图关系，则自动合成；
- 最终重建为“普通标准 HZC”。

因此，后续若要做到“完全创作”，你需要在资源管线中把 `type == 2` 分为：

- **只是多帧容器**
- **真正依赖底图的差分集**

而不是简单一概而论。

---

## 3.7 非标准 HZC：TLG 负载变体

这是近年来 HD / Steam 相关 FVP 资源分析中非常关键的一块。

### 3.7.1 现象

在一些较新资源里，HZC 文件头仍然是：

- `hzc1`
- `NVSG`

但到了 payload 开头，出现的不是 zlib 常见的 `0x78 xx`，而是：

- `TLG5.0`
- `TLG6.0`
- `TLG0.0\0sds\x1a`

即：**把 TLG 图像流塞进了 HZC 外壳里。**

### 3.7.2 证据来源

- `基于瞪眼法...Wiz下.docx` 的“非常规 hzc 文件”部分
- `test3/nvsg_image_core.py`
- `test4/tlg_png_converter.py`
- `test5/rebuild_hzc.py`

### 3.7.3 含义

这说明 HZC 在实践中至少分成两大类：

1. **标准 zlib/NVSG 型 HZC**
2. **TLG 负载型 HZC**

因此，如果未来要做“统一资源编辑器”，就不能把“看见 hzc1 就直接 zlib 解压”写死。

---

## 3.8 `hzc1` 与 `NVSG` 需要概念区分

`my-sakura-moyu-main/fptool/package.cpp` 给出一个很有启发性的现象：

- 它把 `hzc1` 当成一种通用压缩包装头（`Z_SIGNATURE`）；
- 再在内部 `info header` 里判断真正的资源签名是否为 `NVSG` 图像；
- 若内部是 `NVSG`，才进一步按图像解释。

这提示我们：

> **严格说，`hzc1` 更像“压缩/包装容器标识”，`NVSG` 才是常见图像负载标识。**

在大多数 F 社图像工作流里，这二者几乎绑定出现，所以常常被混称；但从格式抽象上最好还是分开：

- `hzc1`：外层容器/压缩头
- `NVSG`：图像负载头

这有助于后续扩展到音频原始条目、非图像 payload、或更复杂容器分析。

---

## 3.9 其他资源类型：音频、视频、Gaiji

### 3.9.1 音频

BIN 里的音频常见为：

- `OggS` -> OGG
- `RIFF` -> WAV

`voice.bin`、`bgm.bin`、`se_sys.bin` 等在工具与文档中都非常常见。

### 3.9.2 视频

`星空HD中文化攻略Plus.docx` 明确指出：

- 游戏目录下常有 `movie/` 文件夹；
- 其中 OP 直接以 `wmv` 等外部格式存在。

`rfvp` 中也专门实现了 `na_wmv_player`、`movie` syscall、视频播放器资源管理，说明视频不是旁枝，而是 FVP 运行时的一等资源。

### 3.9.3 Gaiji

`rfvp/graph.rs` 中的 `GaijiLoad` 表明：

- FVP 支持把特定字符映射到外部字形图像；
- 这对特殊符号、情绪图标、表情文字等很关键。

也就是说，文字系统并不只依赖系统字体，它还可与图像资源耦合。

---

## 4. 参考资料还能进一步推出的关键结论与研究方向

## 4.1 FVP 的“文本问题”本质上是“编码 + 资源名 + locale + 字体”的联动问题

从各种汉化文档可以清楚看到一个常见误区：

- 以为只要把台词改成 GBK/UTF-8，就完成了“汉化引擎适配”。

实际上 FVP 的 Shift-JIS 依赖贯穿：

- 文本显示
- 资源名读取
- 文件名比较
- 字体枚举
- 字形提取
- UI/菜单 A/W API

所以“能显示中文”与“能稳定运行中文化工程”之间差得非常远。

这对未来自由创作也很重要：

- 若你准备做一个**真正脱离原始日文环境的 FVP 创作链**，
- 就必须在引擎层或兼容层解决 locale 与编码分离，而不只是回封文本。

---

## 4.2 FVP 是一种非常适合做 patch / mod 的引擎

多个来源共同表明它具备这些“天生适合补丁化”的特征：

1. **第一个 HCB 即入口**
2. **同名外置文件/目录优先于 BIN**
3. **脚本中资源名是明文可见的**
4. **视频等资源可以外置**
5. **图片、音频容器结构并不复杂**

这意味着：

- 对民间汉化非常友好；
- 对资源替换实验非常友好；
- 对将来“做自己的 FVP 内容工程”也非常友好。

你最终的自由创作目标，并不是逆着引擎设计走，而是在很大程度上顺着它原本就留出的“开发/覆盖接口”走。

---

## 4.3 现有资料其实已经形成三层工具链雏形

从当前 reference 与 `test*` 目录可看到非常清楚的技术演进层次：

### 第一层：格式封解包工具
- `fvp-1.0`
- `GARbro`
- `FVP-Yuki`
- `test3` / `test4` / `test5`

关注点：
- HCB 文本抽取与回填
- BIN 封解包
- HZC / TLG 预览与重建

### 第二层：脚本结构分析与重建工具
- `fvp-1.0/hcbdecoder.cpp`
- `my-sakura-moyu-main/binary/fvp_vm`
- `test2/hcb_script_core.py`
- `rfvp` 工作区中的 `assembler / disassembler / hcb2lua / lua2hcb`

关注点：
- 函数索引
- 标签化控制流
- 反汇编 / 伪代码 / Lua IR
- 回编译 / round-trip

### 第三层：完整运行时重实现
- `rfvp-0.3.0`

关注点：
- 真正执行 HCB
- 真正管理音频/图像/动画/输入/存档/窗口
- 让游戏整体跑起来

这说明你当前的最终目标——**“完全解析 HCB 具体作用，并实现自由的 FVP 游戏编辑创作”**——并不是没有路径，而是已经能被拆成一条很清晰的技术路线。

---

## 4.4 要实现“完全解析 HCB 作用”，真正缺的不是 opcode 表，而是 syscall 语义全覆盖

单看 opcode，FVP 的指令集其实并不大，核心就 0x00~0x27。

真正困难的是：

- `TextPrint` 到底如何改动 text buffer 与 reveal 队列；
- `GraphLoad` 与 `PrimSet*` 怎样映射到纹理和图元状态；
- `Motion*` 如何改变 prim 的空间参数；
- `ThreadWait` / `DissolveWait` 如何与场景时序配合；
- `SaveWrite` / `Load` 如何把 VM 与资源状态一起序列化；
- `Movie` / `AudioPlay` / `GaijiLoad` 对宿主系统提出何种要求。

换言之：

> HCB 的“作用”不是由字节码单独决定的，而是由“字节码 + syscall 语义 + 当前 GameData 状态”共同决定的。

所以你的下一阶段如果要从“看懂文本与控制流”走向“完全解释剧情动作”，最应该做的是：

- 建立**syscall 语义目录**；
- 对每个 syscall 标注：
  - 参数数量
  - 参数类型
  - 修改哪些状态
  - 是否引发线程切换
  - 是否引发渲染/音频/存档副作用

---

## 4.5 `.chb` 更像工作流命名，不像全新格式

`test6/README.md` 已明确说明：

- `.chb` 是在当前工作流中的命名约定；
- 结构上与 HCB 相同；
- 主要区别是按 `GBK` 解析。

这说明今后完全可以把 CHB 看成：

> **“GBK 工作流下的 HCB 变体命名”**

而不需要为它单独构造另一套格式理论。

---

## 4.6 当前仍存在的歧义与待验证点

尽管现有资料已经很多，但要达到“完全解析”仍有若干空白：

### 4.6.1 opcode 语义歧义
- `0x08/0x09` 真值/假值命名冲突
- `0x25/0x27` 比较助记符冲突
- `0x11/0x12/0x17/0x18` 旧资料长期未明，现代实现解释为 table ops，但仍建议做实机验证

### 4.6.2 引擎版本差异
- `Wiz` 时代的旧版 FVP
- HD / Steam 时代的较新版 FVP
- `ACPX/XPK` 与 simple BIN 两种包格式
- 标准 zlib HZC 与 TLG HZC 并存

### 4.6.3 “脚本原语言”仍未真正恢复

目前能做到的多是：

- 反汇编成伪汇编；
- 还原成一定程度可编辑的 IR；
- 或转成 Lua 风格中间语言。

但这离原始 FVP 开发脚本语言是否完全等价，仍是未知的。

因此“自由创作”大概率不会是恢复原始官方 DSL，而是：

- 设计你自己的**高层作者语言 / IR**；
- 再编译到 HCB。

---

## 5. 对“完全解析 HCB、实现自由创作”的建议路线

结合现有资料，建议把后续工作拆成五个阶段：

## 阶段一：建立统一规范文档（现在最该做）

输出一份“规范型文档”，把以下内容全部定死：

- HCB 头部结构
- opcode 二进制编码
- opcode 真实语义
- syscall 导入表结构
- BIN 结构
- HZC 结构与变体
- loose override 规则
- locale / 文件名排序规则

本文可以视作这份规范的综述版前置材料。

## 阶段二：建立 syscall 语义数据库

目标产物建议为：

- `syscall_spec.yaml/json`

字段可包括：

- 名称
- 参数数
- 参数类型
- 返回值类型
- 影响的 `GameData` 子系统
- 是否 yield / wait / sleep / text wait
- 证据来源
- 待验证状态

## 阶段三：建立 HCB -> IR 的可逆转换

建议目标不是“只做文本提取”，而是：

- HCB -> 控制流图 CFG
- CFG -> 可读 IR / Lua-like IR
- IR -> HCB 可回编译

这一块你已经有多份现成基础：

- `test2/hcb_script_core.py`
- `reference/rfvp-0.3.0/crates/hcb2lua_decompiler`
- `reference/rfvp-0.3.0/crates/lua2hcb_compiler`
- `my-sakura-moyu-main/binary/fvp_vm`

## 阶段四：建立资源作者管线

建议拆成：

- PNG/TLG/HZC 双向
- loose folder 直投测试
- BIN 最终打包
- 偏移与差分元数据保留
- 资源名规范与排序规范

你当前的 `test3`、`test4`、`test5` 已经基本构成雏形。

## 阶段五：建立最小原创工程模板

最终目标可以是：

- 一个最小可启动 HCB
- 一组最小资源目录 `graph/`、`voice/`、`bgm/`
- 一套最小 syscall 使用约定
- 可以在 `rfvp` 上跑通

一旦“最小原创模板”跑起来，FVP 自由创作就从逆向问题进入真正的内容工程问题了。

---

## 6. 结论

综合现有源码、工具与文档，可以对 FVP 引擎下一个相对稳固的定义：

> **FVP 是一个以 HCB 字节码为控制核心、以 EXE 内建 VM 与 syscall 实现为宿主、以 BIN/HZC/外置目录为资源系统、并强依赖日文 Windows locale/编码环境的视觉小说引擎体系。**

进一步地：

### 已经可以基本确认的内容
- HCB 的总体文件结构
- 主要 opcode 集
- VM 的栈机本质
- 协作式多线程/多上下文调度模型
- syscall 导入表机制
- BIN 的基本结构
- 标准 zlib HZC/NVSG 结构
- loose file/folder 覆盖优先于 `.bin`
- locale / CompareString / 字体接口对引擎稳定性的决定性影响

### 已能进入工程落地的内容
- HCB 文本提取与回封
- HCB 脚本级重建
- BIN 封解包
- 标准 HZC 预览与重建
- TLG 型 HZC 识别与转标准 HZC
- CHB/HCB 浏览与导出

### 当前真正的瓶颈
不是“看不懂 HCB 文件长什么样”，而是：

- **如何把 syscall 的宿主语义系统化地建模出来；**
- **如何把低层 HCB 提升成一种适合编辑与创作的高层 IR / DSL。**

如果把你的最终目标概括为一句话，那么最准确的说法应该是：

> 你接下来不是单纯地“继续逆向 HCB”，而是在构建一套 **FVP 字节码—引擎语义—资源系统—作者工具链** 的完整知识与工程体系。

---

## 附录：本文主要参考文件索引

### 直接核心参考
- `../reference/FAVORITE引擎VM及脚本结构分析/FAVORITE引擎VM及脚本结构分析.txt`
- `../reference/fvp-1.0/hcb_opcodes.h`
- `../reference/fvp-1.0/hcbdecoder.cpp`
- `../reference/fvp-1.0/hcbrebuilder.cpp`
- `../reference/fvp-1.0/nvsgconverter.cpp`
- `../reference/fvp-1.0/parser.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/hcb.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/hzc1.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/archive.cpp`
- `../reference/FVP-Yuki-1.0.2/FVP-Yuki-1.0.2/src/text_codec.cpp`
- `../reference/rfvp-0.3.0/crates/rfvp/src/script/parser.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/script/context.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/vfs.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs`
- `../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/*.rs`
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

### 文档与经验参考
- `../reference/关于星空HD自制汉化的一些记录/关于星空HD自制汉化的一些记录（from lilith🍁）.docx`
- `../reference/基于瞪眼法的F社资源文件解析/实操环节——以Wiz相关文件为例（上）.docx`
- `../reference/基于瞪眼法的F社资源文件解析/实操环节——以Wiz相关文件为例（下）.docx`
- `../reference/就算是笨蛋笨蛋也能用的星空的记忆HD汉化版制作指南/星空的记忆HD中文化攻略Plus.docx`

### 当前工作区实验工具参考
- `../../test/README.md`
- `../../test2/README.md`
- `../../test3/README.md`
- `../../test4/README.md`
- `../../test5/README.md`
- `../../test6/README.md`

---

## 后记

这篇文档的定位不是“最终标准”，而是：

- 为后续建立 **FVP 统一规范文档** 提供底稿；
- 为下一步整理 **syscall 语义表** 和 **HCB IR** 提供公共前提；
- 为你最终实现“完整解析 HCB 作用、自由编辑与创作 FVP 游戏”提供一个可持续扩展的研究框架。
