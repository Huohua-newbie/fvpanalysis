# Control 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md) 的分组顺序、[`syscall_spec.txt`](../spec/syscall_spec.txt) 的简表，以及 rfvp 参考实现，Control 分组当前包含 2 个 syscall：

1. `ControlPulse`
2. `ControlMask`

其注册位置可见于 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:29-30) 与 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:659-661)。

综合源码与脚本调用样例，Control 分组可以直接定性为：

> **AVG 类文本推进/快进控制接口。**

它不是常规输入读取接口，而是对“当前帧是否立即推进”“Ctrl/Shift 是否参与文本快速显示”这两类控制状态进行切换。

---

## 2. 共享实现约定

## 2.1 统一控制语义

rfvp 在 [`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:304-331) 给 Control 分组写了非常直接的注释：

- [`ControlPulse`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:304-312) ：“Skip mode in AVG games”，无参数
- [`ControlMask`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:318-331) ：启用/禁用 control 与 shift 键，用于加速文本显示

因此，Control 分组应理解为：

> **与 AVG 文本快进/跳过有关的控制面。**

## 2.2 作用对象

这组 syscall 直接作用于 `inputs_manager`：

- [`set_control_pulse()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:520-541)
- [`set_control_mask()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:545-547)

而 `ControlPulse` 的效果会被场景更新循环和文本管理器共同消费：

- 场景更新中把当前帧转成 fast-forward：[`anzu_scene.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/anzu_scene.rs:23-53)
- 文本揭示逻辑里把当前行一次性揭示：[`text_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:1792-1819)

因此，它是一个**跨系统的调度控制信号**，不是单一输入按键读取函数。

---

## 3. `ControlPulse`

### 3.1 参数与返回

- **参数个数**：0：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:29-30)
- **签名**：`ControlPulse()`
- **返回值**：`Nil`：[`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:308-312)

### 3.2 具体作用

[`control_pulse()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:79-83) 的实现极短：

1. 调 [`inputs_manager.set_control_pulse()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:520-522)
2. 返回 `Nil`

而 [`set_control_pulse()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:520-522) 会把 `control_is_pulse` 置为 `true`。

随后这个标志会在同一帧/下一帧被消费：

- [`peek_control_pulse()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:523-531)：只观察不消费
- [`take_control_pulse()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:533-542)：消费并清零

### 3.3 语义判断

可以把它概括为：

> **向引擎发送一次“控制快进/立即推进”脉冲。**

它不是永久状态切换，而是：

- **单帧脉冲**
- **一次性生效**
- 被后续帧更新立即消费

这与 rfvp 在 [`anzu_scene.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/anzu_scene.rs:23-53) 中的说明完全一致：

- `Ctrl` 按下或 `ControlPulse` 为真时，会把 `elapsed` 取反
- 负 `elapsed` 被视作 fast-forward 信号

### 3.4 文本系统中的影响

文本管理器明确写道：

> holding Ctrl（or issuing ControlPulse）makes the current line render immediately.

对应实现见 [`text_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:1792-1819)。

因此，`ControlPulse` 的更精确语义是：

> **促使当前文本/演出在本帧快速完成或立即揭示。**

### 3.5 脚本样例

- [`f_00037B6A()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037B6A.lua:5) 直接调用 `ControlPulse()`
- [`f_0003793C()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0003793C.lua:33) 在标题/界面流程中调用 `ControlPulse()`
- [`f_00076122()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:156) 与大量标题/菜单状态机代码中也反复调用 `ControlPulse()`

这些例子共同说明：

> 它通常被放在“等待用户推进 / 用户选择 / 快进跳过”的分支中，而不是资源装载分支中。

---

## 4. `ControlMask`

### 4.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:29-30)
- **签名**：`ControlMask(mask)`
- **参数含义**：
  - `arg0: Variant`：掩码开关；`Nil` / 非 `Nil` 具有不同语义
- **返回值**：`Nil`：[`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:323-331)

### 4.2 具体作用

[`control_mask()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:85-92) 的实现逻辑是：

1. 令 `masked = mask.is_nil()`：[`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:86-89)
2. 调 [`inputs_manager.set_control_mask(masked)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:545-547)
3. 返回 `Nil`

也就是说：

- `mask == Nil` -> `masked = true`
- `mask != Nil` -> `masked = false`

### 4.3 语义判断

rfvp 源码注释已经把其意图说明得很清楚：

> Enable/disable control and shift keys, which are used to speed up text display in AVG games.

因此可概括为：

> **控制 Ctrl/Shift 是否参与 AVG 文本加速。**

再结合 `input_manager` 的注释：

- `set_control_mask(mask)`：忽略 control 和 shift 键：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:544-547)

因此其实际效果是：

- `Nil`：启用 mask（禁用 Ctrl/Shift 快进）
- 非 `Nil`：关闭 mask（允许 Ctrl/Shift 快进）

### 4.4 脚本样例

- [`f_00037E46()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037E46.lua:5) 调用 `ControlMask(S0)`，而其上游常把 `S0` 设成 `Nil`
- [`f_00037BF7逐条反汇编对照.md`](../reversals/f_00037BF7逐条反汇编对照.md:20) 已将其总结为“屏蔽/冻结用户控制输入”

这里需要稍作区分：

> `ControlMask` 并不是把所有输入都冻结，而是主要控制 **Ctrl/Shift 快进能力**。

如果原脚本把它用于更宽泛的“冻结控制”场景，那是其上层业务语义；底层 syscall 语义仍然是控制按键 mask。

---

## 5. Control 分组的整体工作流

从脚本常见调用模板看，Control 分组通常出现在以下两类场景：

1. **开启/关闭文本快进能力**
   - [`ControlMask`](#4-controlmask)
2. **主动发出一帧快进/立即揭示脉冲**
   - [`ControlPulse`](#3-controlpulse)

它们的关系可以理解为：

- `ControlMask` 控“允许不允许快进”
- `ControlPulse` 控“这一帧要不要立刻快进”

这使得 Control 分组成为 AVG 文本/演出控制链中非常核心的调度接口。

---

## 6. 高置信度结论

以下结论比较稳：

- Control 分组当前只有 2 个 syscall：`ControlPulse`、`ControlMask`。
- `ControlPulse` 无参，返回 `Nil`，语义是发出一次快进/立即推进脉冲。
- `ControlMask` 1 参，返回 `Nil`，语义是控制 Ctrl/Shift 是否参与文本快进。
- 两者都直接作用于 `inputs_manager`。
- `ControlPulse` 会在场景更新中作为 fast-forward 信号被消费。
- `ControlPulse` 也会使文本揭示立即完成。

---

## 7. 脚本侧可见的调用位置

- [`f_00037E46()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037E46.lua:1)：`ControlMask`
- [`f_00037B6A()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037B6A.lua:1)：`ControlPulse`
- [`f_0003793C()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0003793C.lua:1)：`ControlPulse`
- [`f_00076122()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:1)：标题/菜单状态机中多处 `ControlPulse`

---

## 8. 证据来源

- [`README.md`](../manual/syscall-db.md:29-44)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:23-24)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:29-30)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:659-661)
- [`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:304-331)
- [`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:520-547)
- [`anzu_scene.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/anzu_scene.rs:23-53)
- [`text_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:1792-1819)
- [`f_00037E46.lua`](../../hcbtool_ir/Sakura/f_00037E46.lua:1)
- [`f_00037B6A.lua`](../../hcbtool_ir/Sakura/f_00037B6A.lua:1)
- [`f_0003793C.lua`](../../hcbtool_ir/Sakura/f_0003793C.lua:1)
- [`f_00076122.lua`](../../hcbtool_ir/Sakura/f_00076122.lua:1)
- [`f_00037BF7逐条反汇编对照.md`](../reversals/f_00037BF7逐条反汇编对照.md:20)
- [`f_00074DA5逐条反汇编对照.md`](../reversals/f_00074DA5逐条反汇编对照.md:44-46)
