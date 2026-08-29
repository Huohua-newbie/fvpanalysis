# Dissolve 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md)、[`syscall_spec.txt`](../spec/syscall_spec.txt) 与 rfvp 参考实现，Dissolve 分组当前包含 2 个 syscall：

1. `Dissolve`
2. `DissolveWait`

其注册位置可见于：

- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:35-36)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:695-696)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:738-739)

综合源码与脚本调用样例，这一组可以概括为：

> **画面转场启动与转场等待接口。**

其中：

- [`Dissolve`](#3-dissolve) 负责**发起转场**；
- [`DissolveWait`](#4-dissolvewait) 负责**查询或阻塞直到转场完成**。

---

## 2. 共享实现约定

## 2.1 Dissolve 的内部状态类型

rfvp 在 [`motion_manager/mod.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:39-48) 中定义了 `DissolveType`：

- `None = 0`
- `Static = 1`
- `ColoredFadeIn = 2`
- `ColoredFadeOut = 3`
- `MaskFadeIn = 4`
- `MaskFadeInOut = 5`
- `MaskFadeOut = 6`

这说明 FVP 的 dissolve 并不是单一效果，而是至少区分：

- **纯色淡入/淡出**
- **mask 图像转场**
- **静态保持态**

## 2.2 共享状态字段

`MotionManager` 中与 dissolve 直接相关的核心字段和接口包括：

- 颜色 dissolve 的 color id：[`set_dissolve_color_id()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:822)
- mask dissolve 的图像：[`set_dissolve_mask_graph()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:830)
- 启动 dissolve：[`start_dissolve()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:838)
- 每帧推进 dissolve：[`tick_dissolve()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:845)
- 当前 dissolve alpha：[`get_dissolve_alpha()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:888)

因此这组 syscall 的真正作用对象不是某个 prim，而是：

> **全局转场状态机。**

## 2.3 调度副作用

从 [`syscall_spec.txt`](../spec/syscall_spec.txt:29-30) 可见：

- `Dissolve`：无显式调度副作用
- `DissolveWait`：`yield,dissolve_wait`

这和源码一致：

- [`Dissolve`](#3-dissolve) 只设置状态，不直接阻塞线程
- [`DissolveWait`](#4-dissolvewait) 在非空参数模式下会向 [`thread_wrapper`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_wrapper.rs:49-50) 发出 `DissolveWait` 请求

---

## 3. `Dissolve`

### 3.1 参数与返回

- **参数个数**：7：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:35)
- **签名**：`Dissolve(duration, name_or_color, inout, x, y, w, h)`
- **返回值**：`Nil`：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:177-253)

### 3.2 参数语义总览

从 [`dissolve()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:177) 可归纳出：

- `arg0: Int`：持续时间，单位 ms，合法范围 `1..=300000`
- `arg1: String | ConstString | Int | 其他`：
  - 字符串：mask 文件路径
  - 整数：颜色槽 ID
  - 其他：走默认 colored fade-in 分支
- `arg2: Variant`：对 mask dissolve 而言决定模式；`Nil` 与非 `Nil` 含义不同
- `arg3..arg6: Int | Nil`：仅在颜色槽分支下作为矩形区域参数 `x, y, w, h`

### 3.3 分支一：mask dissolve

当 `arg1` 是字符串时：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:203-217)

1. 从 VFS 读取该路径文件：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:205)
2. 用 [`GraphBuff::load_mask()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:206-207) 加载 mask 图
3. 写入 [`set_dissolve_mask_graph()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:830)
4. 根据 `arg2` 的 `Nil / 非 Nil` 选择模式：
   - `Nil` -> `MaskFadeInOut`：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:213-215)
   - 非 `Nil` -> `MaskFadeIn`：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:215-216)

这说明在 mask 分支里，`arg2` **不是普通布尔方向位**，而是一个“模式选择器”。rfvp 注释也明确指出：

> 原引擎是通过判断 `args[2].Type == Nil` 来决定 wait=4 还是 wait=5 风格。

因此更稳妥的结论是：

> 当 `arg1` 为字符串时，`Dissolve` 表示 **按 mask 图像做转场**；`arg2 == Nil` 更接近“in-out 双相 mask 转场”，非空则是“单相 fade-in mask 转场”。

### 3.4 分支二：纯色 dissolve

当 `arg1` 是整数时：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:219-245)

1. 将其解释为 `color_id`
2. 要求范围 `1..=255`
3. 启动 `ColoredFadeOut`：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:221-224)
4. 调 [`set_dissolve_color_id()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:822)
5. 取得全屏 mask prim，并默认铺满全屏：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:228-232)
6. 若 `x/y/w/h` 为整数，则覆盖矩形区域：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:233-244)

因此可概括为：

> 当 `arg1` 为整数时，`Dissolve` 表示 **使用某个颜色槽作为覆盖色，在全屏或指定矩形区域上执行纯色淡出转场**。

### 3.5 分支三：默认 colored fade-in

当 `arg1` 既不是字符串也不是整数有效色槽时，会走默认分支：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:247-250)

- 启动 `ColoredFadeIn`

因此这个分支更像：

> **退化型纯色淡入效果**。

但“使用哪一个颜色槽作为 fade-in 源”并不能仅从这一段完全确定，需要结合 render 路径与更高层状态补证，因此这里保守表述。

### 3.6 持续时间语义

[`dissolve()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:187-198) 强制要求时长在 `1..=300000`，单位就是毫秒。

而 [`start_dissolve()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:838-843) 会把它记录到 `dissolve_duration_ms`，每帧由 [`tick_dissolve()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:845-885) 按 elapsed ms 推进。

因此这个参数的高置信度含义是：

- **毫秒级转场时长**

### 3.7 脚本样例

- 最简单模板调用：[`f_0005599D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005599D.lua:89-96)
- 更复杂包装调用：[`f_00055D3D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055D3D.lua:828-835)
- 收尾片段讨论：[`f_0049F256收尾片段解析.md`](../../hcbtool_test/f_0049F256收尾片段解析.md:239-240)

这些样例说明：

> `Dissolve` 常被高层包装函数当作“真正发起过渡”的底层 syscall 使用。

---

## 4. `DissolveWait`

### 4.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:36)
- **签名**：`DissolveWait(mode)`
- **返回值**：
  - `arg0 == Nil`：`BoolLike`
  - `arg0 != Nil`：`Nil`，并可能触发阻塞

### 4.2 双模式语义

rfvp 注释已经直接给出它的双模式行为：[`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:396-398)

1. `DissolveWait(nil)`：
   - 若当前仍有转场在进行，则返回 `True`
   - 否则返回 `Nil`
2. `DissolveWait(non-nil)`：
   - 若当前仍有转场在进行，则让当前 context 进入 dissolve wait
   - 本次调用返回 `Nil`

### 4.3 判定依据

`DissolveWait` 内部用以下条件近似原引擎的 `dis_wait`：[`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:403-406)

- `dissolve_type != None && dissolve_type != Static`
- 或 `dissolve2_transitioning == true`

因此它等待的不仅是传统 dissolve1，还包括 dissolve2 内部过渡层。

### 4.4 阻塞如何实现

当 `arg0 != Nil` 且确实有转场进行中时，会调用：

- [`thread_wrapper.dissolve_wait()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_wrapper.rs:49-50)

随后在 VM 执行层：

- [`vm_runner.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:275-277) 把它登记为 `CONTEXT_STATUS_DISSOLVE_WAIT`
- [`vm_runner.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:227-236) 会在 dissolve 结束后恢复线程运行

因此可以高置信度判断：

> `DissolveWait(non-nil)` 是一个 **真正会挂起当前脚本上下文的等待型 syscall**。

### 4.5 与 fast-forward 的关系

[`anzu_scene.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/anzu_scene.rs:159-176) 明确说明：

- 在 Ctrl/ControlPulse fast-forward 模式下
- dissolve 会被用 `u32::MAX` 立即推进到终态：[`anzu_scene.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/anzu_scene.rs:164-166)

因此 `DissolveWait` 的等待通常也能被快进快速解除。

### 4.6 脚本样例

#### 阻塞模式

大量高层包装函数使用：

- [`f_0004A608.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004A608.lua:452-453)
- [`f_00050EDB.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00050EDB.lua:158-159)
- [`f_00055A57.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055A57.lua:17-18)
- [`f_00055D3D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055D3D.lua:865-875)

这些都传了 `true`，说明：

> 脚本里最常见的是“发起转场后强制等待其完成”的阻塞模式。

#### 轮询模式

在标题控制函数 [`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:209-211) 中，则是：

- `DissolveWait(nil)`
- 若返回 `True` 就继续每帧轮询：[`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:212-230)

这说明：

> `DissolveWait(nil)` 常被用作“当前转场是否仍在进行”的查询谓词。

---

## 5. Dissolve 分组的整体工作流

脚本里的典型模板通常是：

1. 先调用 [`Dissolve`](#3-dissolve) 发起转场
2. 然后：
   - 要么立刻用 [`DissolveWait(true)`](#4-dissolvewait) 阻塞等待
   - 要么用 [`DissolveWait(nil)`](#4-dissolvewait) 在循环中轮询

因此这一组本质上是：

> **转场发起器 + 转场完成同步器**。

---

## 6. 高置信度结论

以下结论比较稳：

- Dissolve 分组当前包含 `Dissolve` 与 `DissolveWait` 两个 syscall。
- `Dissolve` 有 7 个参数，返回 `Nil`，负责启动转场。
- `Dissolve` 的第一个参数是毫秒级持续时间。
- `Dissolve` 的第二参数决定进入 mask 分支、纯色分支或默认分支。
- `DissolveWait(nil)` 是查询谓词，返回 `True/Nil`。
- `DissolveWait(non-nil)` 是阻塞等待接口，会让当前脚本上下文进入 dissolve wait 状态。
- 快进状态会快速推进 dissolve，从而更快解除 `DissolveWait`。

---

## 7. 仍需保守处理的点

1. `Dissolve` 默认分支（第二参数既非字符串也非有效整数）对应的具体视觉效果，在 rfvp 中被建模为 `ColoredFadeIn`，但原引擎是否完全一致仍需实机核验。
2. mask dissolve 中 `arg2` 的业务命名仍应保守；目前只能可靠地说它用于区分 `MaskFadeIn` 与 `MaskFadeInOut`。
3. 颜色 dissolve 的矩形参数 `x/y/w/h` 在某些游戏里是否会配合特殊 prim/局部区域做更复杂效果，还需要更多脚本样本补充。

---

## 8. 证据来源

- [`README.md`](../manual/syscall-db.md:61-72)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:29-30)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:35-36)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:695-696)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:738-739)
- [`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:176-253)
- [`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:391-417)
- [`motion_manager/mod.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:39-48)
- [`motion_manager/mod.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:822-885)
- [`thread_wrapper.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_wrapper.rs:49-50)
- [`vm_runner.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:227-236)
- [`vm_runner.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:275-277)
- [`anzu_scene.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/anzu_scene.rs:159-176)
- [`f_0005599D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005599D.lua:89-96)
- [`f_00055D3D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055D3D.lua:828-835)
- [`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:209-211)
- [`f_0049F256收尾片段解析.md`](../../hcbtool_test/f_0049F256收尾片段解析.md:211-214)
- [`f_000104E8函数链作用总结.md`](../../hcbtool_test/f_000104E8函数链作用总结.md:94-96)
