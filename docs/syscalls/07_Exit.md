# Exit 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md)、[`syscall_spec.txt`](../spec/syscall_spec.txt) 与 rfvp 参考实现，Exit 分组当前包含 2 个 syscall：

1. `ExitDialog`
2. `ExitMode`

其注册位置可见于 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:37-38) 与 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:739-740, 550-551)。

综合源码与脚本调用样例，Exit 分组可以直接定性为：

> **脚本层的退出 / 关闭请求控制接口。**

它们并不直接“立刻杀掉进程”，而是通过设置引擎的退出/锁定状态，让主循环和宿主在合适时机结束。

---

## 2. 共享实现约定

## 2.1 作用对象

Exit 分组直接影响 `GameData` 的生命周期标志：

- `close_pending`
- `close_immediate`
- `lock_scripter`
- `main_thread_exited`
- `last_current_thread`

这些字段的访问器位于 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:424-453, 440-445)。

## 2.2 调度副作用

这组 syscall 的主要副作用是改变宿主循环退出条件，而不是资源层效果。rfvp 注释与实现可以直接印证：

- [`ExitMode(3)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:140-147) 会在“主脚本上下文真正退出”后让宿主循环结束
- [`ExitDialog`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:421-435) 会触发确认退出请求，并让线程循环中断

因此，Exit 分组应理解为：

> **生命周期/退出调度接口。**

---

## 3. `ExitDialog`

### 3.1 参数与返回

- **参数个数**：0：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:37)
- **签名**：`ExitDialog()`
- **返回值**：`Nil`

### 3.2 具体作用

rfvp 在 [`ExitDialog`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:421-435) 中明确说明：

- 原版引擎会弹出原生 MessageBox Yes/No
- rfvp 当前**不再弹窗**，而是视作“已确认退出请求”

实现行为是：

1. 调 [`request_exit_dialog()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:19-25)
2. 调 [`game_data.thread_wrapper.should_break()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:430-433)
3. 返回 `Nil`

### 3.3 语义判断

可概括为：

> **发起一次“退出对话框/退出确认”请求，并让当前脚本执行尽快停止。**

这里要保守说明：

- 它并不直接等价于“立即关闭程序”
- 更像是把退出请求交给宿主主循环处理

### 3.4 宿主侧消费

[`app.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/app.rs:541-543) 会在每帧检查 `take_pending_exit_dialog_request()`，若为真则打开退出确认 UI。

这说明 `ExitDialog` 的行为链是：

1. 脚本发起请求
2. 宿主侧在帧循环中观察并弹出确认 UI
3. 再由主循环决定是否真正退出

### 3.5 脚本样例

目前在 Sakura 的已检索片段里，`ExitDialog` 的直接脚本样例较少；它更常以 `ExitMode` + 退出演出链的方式配合出现。故该 syscall 更适合先记作：

> **退出确认请求接口**。

---

## 4. `ExitMode`

### 4.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:38)
- **签名**：`ExitMode(mode)`
- **参数含义**：
  - `arg0: Int`：退出/关闭模式号
- **返回值**：
  - 绝大多数分支返回 `Nil`
  - 在 mode=0 且检测到 close_pending 时返回 `True`

### 4.2 实现分支

[`exit_mode()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:219-251) 的行为如下：

#### mode = 0

- 如果 `close_pending` 已经置位：
  - 清掉 `close_pending`
  - 返回 `True`
- 否则什么也不做，返回 `Nil`

#### mode = 1

- 设置 `close_immediate = true`

#### mode = 2

- 设置 `close_immediate = false`

#### mode = 3

- `lock_scripter = true`
- 记录当前线程为 `last_current_thread`
- `main_thread_exited = false`
- 调 `thread_wrapper.should_break()`

#### mode = 4

- `lock_scripter = false`
- `main_thread_exited = false`

### 4.3 语义判断

可概括为：

> **控制引擎退出生命周期的模式切换接口。**

它的关键点不是“退出”本身，而是**设置退出流程的不同阶段状态**。

### 4.4 mode=3 的核心语义

mode=3 是最关键的分支，因为 rfvp 注释与 `vm_runner` / `app` 的逻辑都表明：

- 它先锁住脚本调度器
- 再等待“最后一个主线程上下文真正退出”
- 然后宿主主循环才会终止：[`vm_runner.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:140-147)、[`app.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/app.rs:476-483)

因此 mode=3 可以理解为：

> **“脚本逻辑已经结束，宿主可在主脚本上下文真正退出后终止”的锁定模式。**

### 4.5 mode=0 的轮询语义

[`ExitMode(0)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:228-232) 并不是普通设置，而是一个“查询并清除 pending close”的轮询接口：

- 有 pending close -> 返回 `True`
- 没有 -> 返回 `Nil`

这意味着它可以被脚本用于：

> **检查宿主是否已经进入关闭流程。**

### 4.6 脚本样例

- [`entry_point.lua`](../../hcbtool_ir/Sakura/entry_point.lua:646-647) 调用 `ExitMode(2)`
- [`f_000744EB.lua`](../../hcbtool_ir/Sakura/f_000744EB.lua:150-152) 调用 `ExitMode(3)`
- [`f_000744EB.lua`](../../hcbtool_ir/Sakura/f_000744EB.lua:825-827) 调用 `ExitMode(4)`
- [`f_000794AE.lua`](../../hcbtool_ir/Sakura/f_000794AE.lua:44-46, 101-103) 调用 `ExitMode(0)`

这些例子表明：

> `ExitMode` 被用于标题/菜单流程与退出收尾流程中，作为宿主退出状态的控制开关。

---

## 5. Exit 分组的整体工作流

脚本里的常见模式是：

1. 先通过 [`ExitMode`](#4-exitmode) 切换退出阶段状态
2. 如果是确认退出，再由 [`ExitDialog`](#3-exitdialog) 发起确认请求
3. 宿主侧在主循环中消费这些状态：
   - 退出确认 UI：[`app.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/app.rs:541-543)
   - 主线程真正退出后终止主循环：[`app.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/app.rs:476-483)

因此，Exit 分组更准确的整体语义是：

> **把“我要退出”转换成一组宿主可消费的生命周期状态。**

---

## 6. 高置信度结论

以下结论比较稳：

- Exit 分组当前包含 `ExitDialog` 与 `ExitMode` 两个 syscall。
- `ExitDialog` 无参，返回 `Nil`，语义是发起退出确认请求。
- `ExitMode` 1 参，返回值多为 `Nil`，但 mode=0 在 pending close 触发时可返回 `True`。
- `ExitMode(3)` 是最关键分支：锁住脚本调度，并等待主线程上下文真正退出后终止宿主循环。
- 这组 syscall 直接修改 `GameData` 的退出/生命周期标志，而不是直接销毁进程。

---

## 7. 仍需保守处理的点

1. `ExitDialog` 在原版引擎里到底是如何弹出 native MessageBox 的，rfvp 仅以“确认退出请求”方式近似，原始 UI 细节仍需实机补证。
2. `ExitMode` 各个 mode 的完整历史含义可能与不同游戏版本、宿主平台有关；当前结论以 rfvp 与已观察脚本为准。
3. mode=1/2 的“立即退出/取消立即退出”语义是源码层明确的，但脚本层上层语义仍需结合更多调用点观察。

---

## 8. 证据来源

- [`README.md`](../manual/syscall-db.md:61-72)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:31-32)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:37-38)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:550-551, 739-740)
- [`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:219-251)
- [`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:421-435)
- [`vm_runner.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:140-147)
- [`app.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/app.rs:476-483, 541-543)
- [`global_savedata.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/global_savedata.rs:92-94)
- [`entry_point.lua`](../../hcbtool_ir/Sakura/entry_point.lua:646-647)
- [`f_000744EB.lua`](../../hcbtool_ir/Sakura/f_000744EB.lua:150-152, 825-827)
- [`f_000794AE.lua`](../../hcbtool_ir/Sakura/f_000794AE.lua:44-46, 101-103)
- [`f_00037BF7逐条反汇编对照.md`](../reversals/f_00037BF7逐条反汇编对照.md:16-17)
- [`f_000104E8逐条反汇编对照.md`](../../hcbtool_test/f_000104E8逐条反汇编对照.md:22)
