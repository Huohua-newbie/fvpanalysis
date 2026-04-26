# 基于HCB字节码逆向的FVP引擎LOGO演出研究

## ——以 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 为中心的个案分析

## 摘要

FAVORITE 社 FVP 引擎的 [`HCB`](fvp_analysis/result/fvp_analysis项目规范文档.md) 文件并非单纯的“文本脚本容器”，而是同时承担控制流描述、内部函数调用、syscall 宿主接口调用以及资源调度的脚本字节码系统。对于研究者而言，真正困难的问题并不是“把 HCB 反编译成某种可读文本”，而是进一步回答：**某一段 HCB 在运行时究竟对画面、资源与状态做了什么操作**。本文以 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 为核心研究对象，围绕 Sakura 项目中的 LOGO 演出函数展开个案研究，尝试建立一条从原始字节、Lua-like 反编译文本、syscall 语义、资源偏移信息到外部语言复现的完整分析链路。

本文首先从背景层面说明 HCB 解释问题的本质，即 HCB 研究必须同时打通字节码控制流层、syscall 语义层与资源系统层，而不能只停留在“台词提取”层面。随后，本文说明研究过程：研究中综合使用了 [`rfvp-0.3.0`](rfvp-0.3.0)、[`fvp-1.0`](fvp-1.0)、[`FVP-Yuki-1.0.2`](FVP-Yuki-1.0.2)、项目内的 [`hcb_ir_core.py`](fvp_analysis/result/hcbtool_test/hcb_ir_core.py:130)、[`hcb_to_ir.py`](fvp_analysis/result/hcbtool_test/hcb_to_ir.py)、[`ir_to_hcb.py`](fvp_analysis/result/hcbtool_test/ir_to_hcb.py) 等参考与工具，并借助对话式 AI 工具完成模式归纳、逐条对照整理、候选语义生成与中间文档组织；所有关键结论则通过原始字节、Lua-like 导出、宿主源码与脚本重放结果进行交叉验证。

研究结果表明：[`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 并非普通剧情控制函数，而是一段完整的启动 LOGO / 品牌演出脚本。其执行流程可划分为“显示状态初始化—多图层资源装入—图元属性配置—分层淡入与旋转/缩放/位移/纵深运动—输入跳过检测—统一淡出与状态回收”六个阶段。进一步地，本文识别出 `logo_bg`、`logo_favo`、`logo_favo_view` 与 `logo_favo_view_p1/p2/p3` 等图层的具体运动方式，并将 HZC 资源自带偏移信息纳入定位模型，构建了 [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py) 与 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 两套外部复现脚本，实现了对该 LOGO 演出的近似重放。本文认为，这一研究路径证明了：**FVP 的 HCB 功能并非不可解释；只要建立“字节码—Lua-like—syscall—资源—可执行复现”的闭环，便能够把原始脚本作用从“黑箱”逐步还原成具有可验证性的运行过程描述。**

**关键词：** FVP 引擎；HCB；逆向工程；LOGO 演出；syscall 语义；HCB 重建；资源偏移；AI 辅助分析

---

## 1. 引言

### 1.1 研究背景

根据 [`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md:1) 与 [`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:1) 的总结，FVP 本质上是一套“原生 EXE + HCB 字节码脚本 + BIN/HZC 资源 + 外置目录覆盖”的视觉小说运行体系。脚本层并不直接“画图”或“播音”，而是通过内部函数调用与 syscall 调用改写运行时状态，再由场景系统和渲染系统将这些状态兑现为图像、文本、音频与动画。因此，HCB 的真正解释问题并不是“代码如何写成 Lua-like 文本”，而是“代码究竟在运行时做了什么”。

在这一背景下，LOGO 演出函数是一类非常适合开展个案研究的对象。它既不像复杂剧情分支那样依赖大量 flag 与对话状态，也不像底层图形 syscall 那样只有局部意义，而是一个相对封闭、可观察、同时又包含典型图元装载与动画控制操作的功能块。通过对这类函数展开研究，可以较清楚地验证：HCB 的控制流层、资源层和运动层是如何协同工作的。

### 1.2 背景问题

本文所面对的背景问题可以概括为：

> **如何从 HCB 原始字节出发，解释某个函数具体进行了什么操作，并进一步将其还原为可验证的演出流程？**

这一问题至少包含三层含义：

1. **字节码层**：必须识别 opcode、栈行为、调用关系与控制流；
2. **宿主语义层**：必须知道 [`syscall`](fvp_analysis/result/hcb可逆转换/指令与指令块功能对照表.md:73) 以及内部函数在做什么；
3. **资源层**：必须理解图像资源本身包含的尺寸、分片和偏移信息，否则“脚本参数”会被错误理解为最终屏幕坐标。

### 1.3 研究目标与问题陈述

本文围绕以下三个研究问题展开：

- **RQ1：** [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 在 HCB 运行时究竟执行了哪些具体步骤？
- **RQ2：** 该函数中涉及的 `logo_bg`、`logo_favo`、`logo_favo_view`、`logo_favo_view_p1/p2/p3` 等图层分别做了什么运动？
- **RQ3：** 在结合 HZC 图片自带偏移信息后，能否用外部语言近似复现这段演出，并据此反向验证既有结论？

### 1.4 研究贡献

本文的主要贡献如下：

1. 将 HCB 功能解释问题从“反编译文本可读化”推进到“运行时操作可验证化”；
2. 给出一套以 [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:1)、[`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:1)、[`logo演出详解.md`](fvp_analysis/result/hcbtool_test/logo演出详解.md:1) 为核心的分层分析产物；
3. 识别出 LOGO 演出的阶段化结构与各图层的具体运动方式；
4. 将 HZC 内部偏移参数引入复现模型，构建 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 作为更接近原始资源布局的验证脚本；
5. 说明 AI 工具在逆向研究中的适当位置：作为归纳与组织辅助，而非替代证据本身。

---

## 2. 相关工作与资料基础

### 2.1 FVP 与 HCB 的既有研究基础

本文的研究建立在三类基础资料之上。

第一类是引擎整体与脚本体系研究。[`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md:1) 已对 FVP 的整体结构、HCB 文件、VM 运行方式和资源系统做了系统性梳理；[`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:1) 进一步将 `sys_desc_offset`、VM 值模型、真假语义、栈帧布局与 opcode 编码规范化，为后续逐条反汇编提供了统一语义基线。

第二类是 HCB 指令级研究。[`指令与指令块功能对照表.md`](fvp_analysis/result/hcb可逆转换/指令与指令块功能对照表.md:1) 将 `init_stack`、`call`、[`syscall`](fvp_analysis/result/hcb可逆转换/指令与指令块功能对照表.md:73)、`jz`、`push_*`、`pop_*` 以及 `add/sub/...` 等指令做了功能对照，为从原始字节段恢复控制流提供了最小解释单元。

第三类是宿主实现与运行时源码。以 [`rfvp-0.3.0`](rfvp-0.3.0) 为代表的现代重实现工程，提供了 `MotionAlpha`、`MotionMove`、`MotionMoveR`、`MotionMoveS2`、`MotionMoveZ`、`PrimSetOP`、`PrimSetSprt` 等关键 syscall 的参数顺序和实现逻辑。这些内容分别散见于：

- [`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:816)
- [`graph.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:204)
- [`prim.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:487)
- [`gpu_prim.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:266)

### 2.2 与本文直接相关的先行个案研究

本文并不是在空白地带上直接解释 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584)。在此之前，项目已围绕其他典型函数建立了一套个案研究方法。例如：

- [`f_00002025逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00002025逐条反汇编对照.md:1) 说明了如何把原始字节段恢复为有组织的 syscall 调用序列；
- [`f_00002403逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00002403逐条反汇编对照.md:1) 展示了如何从具体资源名出发，把包装函数识别为 CG 引入入口；
- [`f_000019E0样式表提取补充.md`](fvp_analysis/result/hcbtool_test/f_000019E0样式表提取补充.md:1) 则提供了把样式映射函数抽象为表格式数据的先例。

这些工作共同说明：FVP 的 HCB 功能块虽然表面上是离散的字节流，但通过合适的中间形式与文档化手段，可以逐步形成“可验证的语义模型”。

---

## 3. 研究对象与方法

### 3.1 研究对象

本文聚焦于 Sakura 工程中的 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584)。该函数的 Lua-like 文本被单独导出为 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:1)，其原始字节段被单独保存为 [`f_00074DA5`](fvp_analysis/result/hcbtool_test/f_00074DA5)。

从资源名看，该函数涉及：

- `logo_bg`
- `logo_favo`
- `logo_favo_view`
- `logo_favo_view_p1`
- `logo_favo_view_p2`
- `logo_favo_view_p3`

从语义直觉上看，它明显与标题 / 品牌演出有关，但若要严谨论证，仍需回到字节、调用链与资源偏移三方面进行交叉分析。

### 3.2 研究流程

本文采用如下分析流程：

1. **原始字节抽取与基址确认**：确定字节段起止地址与函数边界；
2. **Lua-like 文本对照**：将原始字节与 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:1) 中的语句进行一一对应；
3. **关键内部函数追踪**：分析 [`f_000373A5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118905)、[`f_00037294()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118776)、[`f_00037345()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118845)、[`f_00037476()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119048) 的作用；
4. **syscall 语义绑定**：以 [`MotionAlpha`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:854)、[`MotionMove`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:914)、[`MotionMoveR`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:959)、[`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1000)、[`MotionMoveZ`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1053)、[`PrimSetOP`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1232) 等宿主语义为依据，确定参数顺序与效果；
5. **资源偏移补充**：把 HZC 图片自带偏移值纳入初始定位模型；
6. **外部脚本复现**：用 [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py) 与 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 构造可执行复现版本；
7. **反向核验**：根据复现结果修正对初始位置、分片缩放与 view 层间距的认识。

### 3.3 AI 工具的使用方式

本文研究过程中，AI 工具被用于以下任务：

- 协助从大段 Lua-like 文本中归纳模式；
- 协助把原始字节、指令序列与高层函数结构整理成表格与文档；
- 协助提出候选解释，例如“该函数是否是包装函数”“某组 syscall 是否可理解为 LOGO 演出流程”；
- 协助生成验证脚本与参数化复现原型。

但本文并不把 AI 输出视为直接证据。所有关键结论均以以下材料交叉验证：

- 原始字节段；
- Lua-like 反编译文本；
- 宿主源码；
- 资源头偏移数据；
- 复现脚本运行结果。

因此，AI 在本研究中的角色是：

> **分析辅助器、模式归纳器与文档组织器，而不是替代证据链本身的“结论来源”。**

### 3.4 验证策略

研究中的验证分为两类：

1. **字节—文本一致性验证**：通过 [`_decode_f00074DA5.py`](fvp_analysis/result/hcbtool_test/_decode_f00074DA5.py:1) 生成 [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:1)，确保原始字节与 Lua-like 文本逐条对齐；
2. **语义—视觉一致性验证**：通过 [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py) 与 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 把运动参数转译为可观察动画，利用实际视觉效果回检对偏移、层次与运动语义的解释是否合理。

---

## 4. 背景问题：如何解释 HCB 文件到底做了什么

### 4.1 HCB 不是“文本文件”，而是“动作描述程序”

从 [`指令与指令块功能对照表.md`](fvp_analysis/result/hcb可逆转换/指令与指令块功能对照表.md:21) 可以看出，HCB 是典型的栈机字节码系统。单条 [`syscall`](fvp_analysis/result/hcb可逆转换/指令与指令块功能对照表.md:73) 指令本身并不显露“高层功能名”，只有在结合前序 `push_*` 指令、返回值与控制流之后，才能还原出对应的高层操作。因此，当研究者问“这一段 HCB 到底做了什么”时，真正的问题并不是“它的反编译长什么样”，而是：

- 压栈的数据是什么？
- 调用了哪个内部函数？
- 调用了哪个 syscall？
- 这些参数在宿主里如何解释？
- 它们最终如何改变图元、文本、声音或全局状态？

### 4.2 单靠 Lua-like 反编译仍然不够

Lua-like 导出能把字节码改写成较易读的形式，但仍然存在两类局限：

1. **参数名与运行时对象并不完全等价**。例如 `S0`、`S1`、`a1` 只是中间变量名，并不自动说明这些值是“中心坐标”“旋转角度”还是“资源 ID”；
2. **宿主语义缺失时，函数名也不等于完整含义**。例如 `MotionMoveS2`、`PrimSetOP` 这样的名字看似直观，但若不知道参数顺序与实现细节，就很容易误把“锚点”看成“位置”，或者误把“起止缩放参数”看成“单一缩放值”。

因此，本研究将 HCB 解释问题视为一个跨层问题：

> **只有把“字节码—函数—syscall—资源”四层打通，才能解释 HCB 的具体操作。**

---

## 5. 研究过程

### 5.1 从函数定位到原始字节确认

首先，通过 Sakura 的整体 IR 导出文件，定位到 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 的函数定义；随后，读取单独导出的 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:1) 与对应字节段 [`f_00074DA5`](fvp_analysis/result/hcbtool_test/f_00074DA5)。

在此基础上，编写 [`_decode_f00074DA5.py`](fvp_analysis/result/hcbtool_test/_decode_f00074DA5.py:1)，利用 [`hcb_ir_core.py`](fvp_analysis/result/hcbtool_test/hcb_ir_core.py:130) 读取 syscall 描述表，并将原始字节逐条切分为指令。该工具输出了：

- [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:1)
- [`f_00074DA5逐条反汇编.tsv`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编.tsv)

这一步的作用，是把“原始字节是否真的对应 Lua-like 文本”这一基础问题彻底落实。

### 5.2 追踪关键内部函数

在 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 中，最关键的内部函数包括：

- [`f_00037E50()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120324)：切换显示相关全局标志；
- [`f_0005261B()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:165942)：执行一轮 V3D 运动/场景重置；
- [`f_000373A5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118905)：组合资源加载与 sprite 初始化；
- [`f_00055946()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:172695)：执行与 V3D 动作同步的等待 / 启动逻辑；
- [`f_00037F11()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120423)：切换辅助图元与输入相关状态；
- [`f_0003769F()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119287)：其本质仅为 `ThreadNext`；
- [`f_00037708()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119357)：等待超时或输入事件。

其中，最关键的是 [`f_000373A5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118905)。继续追踪可见：

- [`f_00037294()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118776) 负责根据图像类型拼接路径并执行 `GraphLoad`；
- [`f_00037345()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118845) 负责 `PrimSetSprt`；
- [`f_00037476()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119048) 负责 `PrimGroupIn` 与 group 体系接入。

这样，LOGO 演出函数中的“装载图层”就不再只是抽象描述，而是能落实为明确的底层动作链。

### 5.3 绑定 syscall 语义

在动作解释阶段，本文主要依赖 [`rfvp`](rfvp-0.3.0) 中的宿主实现。关键对应关系如下：

- [`MotionAlpha`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:854)
  - `arg1 = prim id`
  - `arg2 = src_alpha`
  - `arg3 = dst_alpha`
  - `arg4 = duration`
  - `arg5 = type`
  - `arg6 = reverse`
- [`MotionMove`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:914)
  - `src_x, src_y, dst_x, dst_y, duration, type, reverse`
- [`MotionMoveR`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:959)
  - `src_r, dst_r, duration, type, reverse`
- [`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1000)
  - `src_w_factor, src_h_factor, dst_w_factor, dst_h_factor, duration, type, reverse`
- [`MotionMoveZ`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1053)
  - `src_z, dst_z, duration, type, reverse`
- [`PrimSetOP`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1232)
  - 在脚本侧表现为 `x, y`
  - 在实现侧会写入 `opx/opy`，并在渲染时作为 pivot 使用

特别需要强调的是 [`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/s2_move.rs:149) 与 [`PrimSetOP`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:559)。前者决定了缩放参数的真实顺序，后者证明了 OP 在渲染阶段被视作 pivot。这两点直接修正了研究初期对“图片拉伸方式”和“位置参数含义”的误读。

### 5.4 引入 HZC 自带偏移信息

在初步复现阶段，研究中曾把 `logo_favo` 与 `logo_favo_view` 的位置直接按脚本中的 `(640,360)` 理解，结果导致两层图像间距过近，且某些图层出现不自然的拉伸与错位。对此，进一步引入了 HZC 图片头部偏移研究结论，并把如下偏移写入 [`LOGO_HZC_TOP_LEFT`](fvp_analysis/result/hcbtool_test/logo-test.py:67)：

- `logo_bg`: `(0, 0)`
- `logo_favo`: `(463, 260)`
- `logo_favo_view`: `(539, 406)`
- `logo_favo_view_p1`: `(618, 409)`
- `logo_favo_view_p2`: `(618, 404)`
- `logo_favo_view_p3`: `(618, 400)`

随后通过 [`anchor_center_from_top_left()`](fvp_analysis/result/hcbtool_test/logo-test.py:194) 将资源头中的 left/top 偏移与图片本身尺寸结合，换算成中心锚点坐标，并在 [`build_layers()`](fvp_analysis/result/hcbtool_test/logo-test.py:199) 中用作初始位置。这一步是本研究的重要修正，因为它表明：

> **资源布局并不完全由脚本决定，资源文件本身也携带版面信息。**

### 5.5 以可执行复现反向验证认识

基于以上认识，研究中先构造了通用复现脚本 [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py)，随后在引入 HZC 偏移后构造了增强版 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py)。

这两个脚本共同承担了“外部语言复现”的验证任务：

- [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py) 更强调把已逆向出的逻辑完整转译成可播放流程；
- [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 则进一步把 HZC 内部偏移纳入初始定位模型，验证“资源自带偏移 + 脚本 pivot + motion 参数”这一组合解释是否更符合原始表现。

在这一过程中，脚本表现出的错误（例如初期图层过近或放置在左上角）反过来推动了对 HCB 与资源语义的再阅读，最终形成更稳定的结论。这也说明了：

> **HCB 逆向研究并非单向阅读源码，而是“解释—复现—观察—修正”的迭代过程。**

---

## 6. 研究成果

### 6.1 成果一：识别出 LOGO 演出函数的完整阶段结构

通过 [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:14) 与 [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:14)，本文将 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 的流程识别为四个连续阶段：

1. **初始化阶段**：清理显示状态、重置 V3D 状态；
2. **装载与配置阶段**：装入 6 个 logo 图层，配置 Z、OP、alpha；
3. **主演出阶段**：多层淡入、旋转收束、缩放收束、Y 方向滑入与 Z 推进；
4. **等待与收尾阶段**：检测跳过输入、统一淡出、回收图元状态。

这说明 HCB 中的一个函数完全可以承载一整段品牌演出的调度逻辑，而不仅仅是“调用某张图”。

### 6.2 成果二：识别出各图层的具体运动方式

综合 [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:71) 与 [`logo演出详解.md`](fvp_analysis/result/hcbtool_test/logo演出详解.md:188)，可以把每层运动概括如下。

#### 6.2.1 `logo_bg`
- 角色：背景底板
- 初始：由资源头偏移 `(0,0)` 决定
- 动作：基本静止，后续参与统一淡出

#### 6.2.2 `logo_favo`
- 角色：主体 LOGO
- 初始：资源头偏移 `(463,260)`
- 动作：[`MotionMoveZ`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:187) 的同类 Z 推进 + [`MotionAlpha`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:196) 淡入
- 解释：在既定版面位置上“向镜头靠近”并显现

#### 6.2.3 `logo_favo_view`
- 角色：前景观察窗 / 覆盖层
- 初始：资源头偏移 `(539,406)`
- 动作：Y 方向 `+50 -> 0` 的滑入、`Z 750 -> 1000` 的推进、`Alpha 0 -> 255` 的淡入
- 解释：从下方微移入场，与主体形成层次差

#### 6.2.4 `logo_favo_view_p1/p2/p3`
- 角色：三块前景分片
- 初始偏移：
  - p1 `(618,409)`
  - p2 `(618,404)`
  - p3 `(618,400)`
- 动作：
  - 全部执行 `Alpha 0 -> 255`
  - p1/p2 执行 `+3600 -> 0` 的旋转收束
  - p3 执行 `-3600 -> 0` 的旋转收束
  - 还执行宽高从放大状态回到正常比例的 `MotionMoveS2`
- 解释：三片不是完全重合的同层贴图，而是带微小上下错位的碎片，在旋转和缩放收束中形成“拼合式徽标聚拢”效果。

### 6.3 成果三：识别出 HZC 内部偏移在复现中的关键作用

本文的一个重要成果是把 HZC 内部偏移从“资源格式细节”提升为“演出定位模型”的组成部分。若不考虑这些偏移，只依据脚本里的 `PrimSetOP(640,360)`、`PrimSetOP(634,413)` 等参数，就很容易把：

- `logo_favo`
- `logo_favo_view`
- 各个分片

错误地叠放在一起，导致间距失真、层次关系不自然。引入 HZC 头偏移后，初始位置可以理解为：

> **资源文件给出素材矩形应当落在何处，脚本再给出围绕哪个点进行 pivot 与 motion 变换。**

### 6.4 成果四：实现外部语言复现

本文最终将上述认识落实为可执行复现脚本：

- [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py)
- [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py)

其中：

- 前者主要复现演出流程本身；
- 后者进一步纳入 HZC 偏移参数，使初始布局更接近原资源版面。

这说明，即便不在原始 FVP 引擎内部执行，也可以基于逆向结果在 Python 层面实现近似重放。这一成果不仅验证了本研究的解释路径，也为后续“可编辑、可实验、可创作”的外部工具开发提供了直接样例。

---

## 7. 讨论

### 7.1 为什么这个个案具有代表性

LOGO 演出函数虽然规模有限，但它几乎涵盖了 HCB 解释问题的几个关键环节：

- 资源装载；
- 图元初始化；
- pivot / OP 设置；
- alpha / 旋转 / 缩放 / 位移 / Z 轴运动；
- 输入打断；
- 收尾与状态回收。

因此，这个个案不仅说明“这一段 LOGO 是怎么播的”，更重要的是说明：

> **FVP 的 HCB 函数可以作为“完整动作程序”来解释，而不是只能被视为文本脚本残片。**

### 7.2 AI 辅助研究的价值与边界

本研究中，AI 辅助在以下方面显示出明显价值：

- 快速把大段 Lua-like 文本整理为阶段结构；
- 把字节、函数、syscall、图层关系组织成文档和表格；
- 协助生成验证脚本，加快“猜想—复现—修正”的循环。

但 AI 也存在明显边界：

- 它可能错误推断参数语义；
- 它可能把“资源头偏移”和“脚本 pivot”混为一谈；
- 它生成的复现脚本必须再经运行结果回检。

因此，本研究的经验是：

> **AI 可以显著提升逆向研究的整理效率，但只有在原始字节、宿主源码和实际复现结果的约束下，其输出才具有研究价值。**

### 7.3 研究局限

本文仍存在若干局限：

1. 复现脚本目前仍是近似实现，而非原始 FVP 渲染管线逐像素重建；
2. 对 `MotionMoveZ` 的视觉解释仍带有一定近似性，尽管其参数方向与宿主实现已较清楚；
3. 对 `PrimSetOP` 与 HZC 偏移的关系，目前是通过源码和表现交叉推断，仍可进一步通过更多资源样本检验；
4. 本文聚焦于单个演出函数，尚未将该方法推广到整套标题流程或更多开场动画函数族。

---

## 8. 结论

本文围绕 FVP 引擎中 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 这一 LOGO 演出函数，回答了“HCB 文件具体进行了什么操作”这一更高层的问题。研究表明：

1. HCB 解释问题必须跨越字节码、内部函数、syscall 语义与资源布局四个层面；
2. [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584) 的确是一段完整的品牌 LOGO 演出程序，而不是简单的图片装载函数；
3. 该函数通过多图层资源装载、OP 设置、alpha / rotation / scale / move / z-motion 控制，形成具有明显层次与节奏的开场演出；
4. HZC 资源头中的自带偏移信息对初始布局具有实质性影响，必须与脚本层参数联合解释；
5. 基于上述认识，可以在外部语言中构造近似复现脚本，并以此作为对逆向结论的反向验证。

从更广的意义看，本文所建立的方法论说明：

> **对 HCB 的研究不应止于“读懂反编译文本”，而应进一步形成“证据链驱动的运行时过程解释”与“可执行复现验证”。**

这一路径不仅适用于 LOGO 演出，也适用于 CG 引入、名字栏样式、文本显示、系统 UI 以及更多 FVP 功能块的研究与重建。

---

## 参考文献

[1] [`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md)

[2] [`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md)

[3] [`指令与指令块功能对照表.md`](fvp_analysis/result/hcb可逆转换/指令与指令块功能对照表.md)

[4] [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md)

[5] [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md)

[6] [`logo演出详解.md`](fvp_analysis/result/hcbtool_test/logo演出详解.md)

[7] [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py)

[8] [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py)

[9] [`hcb_ir_core.py`](fvp_analysis/result/hcbtool_test/hcb_ir_core.py)

[10] [`hcb_to_ir.py`](fvp_analysis/result/hcbtool_test/hcb_to_ir.py)

[11] [`ir_to_hcb.py`](fvp_analysis/result/hcbtool_test/ir_to_hcb.py)

[12] [`rfvp-0.3.0`](rfvp-0.3.0)

[13] [`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs)

[14] [`graph.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs)

[15] [`prim.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs)

[16] [`gpu_prim.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs)

---

## 附录：本文直接讨论的关键函数与文件

- [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:229584)
- [`f_000373A5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118905)
- [`f_00037294()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118776)
- [`f_00037345()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118845)
- [`f_00037476()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119048)
- [`f_00037E50()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120324)
- [`f_0005261B()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:165942)
- [`f_00055946()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:172695)
- [`f_00037F11()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120423)
- [`f_0003769F()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119287)
- [`f_00037708()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119357)
- [`MotionAlpha`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:854)
- [`MotionMove`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:914)
- [`MotionMoveR`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:959)
- [`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1000)
- [`MotionMoveZ`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1053)
- [`PrimSetOP`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1232)
- [`prim_set_op()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:204)
- [`build_draw_model()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:266)
- [`LOGO_HZC_TOP_LEFT`](fvp_analysis/result/hcbtool_test/logo-test.py:67)
- [`anchor_center_from_top_left()`](fvp_analysis/result/hcbtool_test/logo-test.py:194)
- [`build_layers()`](fvp_analysis/result/hcbtool_test/logo-test.py:199)
