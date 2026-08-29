# Input 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md)、[`syscall_spec.txt`](../spec/syscall_spec.txt) 与 rfvp 参考实现，Input 分组当前包含 11 个 syscall：

1. `InputFlash`
2. `InputGetCursIn`
3. `InputGetCursX`
4. `InputGetCursY`
5. `InputGetDown`
6. `InputGetEvent`
7. `InputGetRepeat`
8. `InputGetState`
9. `InputGetUp`
10. `InputGetWheel`
11. `InputSetClick`

其注册位置可见于 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:47-57) 与 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:648-659)。

综合源码与脚本调用样例，Input 分组可以概括为：

> **对当前帧输入状态、输入事件队列、鼠标光标位置与脚本侧点击模式进行访问/控制的一组接口。**

它们大体可分成三类：

- **状态位读取**：`InputGetState`、`InputGetDown`、`InputGetUp`、`InputGetRepeat`、`InputGetWheel`
- **鼠标/光标读取**：`InputGetCursIn`、`InputGetCursX`、`InputGetCursY`
- **输入系统控制**：`InputFlash`、`InputGetEvent`、`InputSetClick`

---

## 2. 共享实现约定

## 2.1 底层作用对象

Input 分组统一操作 [`InputManager`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:104-180)。

这个管理器内部维护了至少以下几类状态：

- `input_state`：当前按键状态位图：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:159, 246-248)
- `input_down`：本帧按下边沿：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:157, 215-217)
- `input_up`：本帧释放边沿：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:158, 250-252)
- `input_repeat`：本帧重复键：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:160, 242-244)
- `wheel_value`：滚轮值：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:164, 254-256)
- `cursor_in / cursor_x / cursor_y`：鼠标是否在窗口内与虚拟坐标：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:161-163, 203-213)
- `press_items`：64 项事件环形缓冲：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:156, 219-229, 346-367)
- `click`：脚本侧点击模式：[`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:173, 258-261)

因此本组 syscall 的核心语义应理解为：

> **读取或影响 InputManager 中的“本帧输入快照 + 事件队列 + 鼠标状态”。**

## 2.2 键码位图约定

rfvp 在 [`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:157-187) 与 [`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:67-101) 中给出了 FVP 的键码定义：

- `Shift = 0`
- `Ctrl = 1`
- `LeftClick = 2`（虚拟左键，鼠标左键或 Enter）
- `RightClick = 3`（虚拟右键，鼠标右键或 Esc）
- `MouseLeft = 4`
- `MouseRight = 5`
- `Esc = 6`
- `Enter = 7`
- `Space = 8`
- `UpArrow = 9`
- `DownArrow = 10`
- `LeftArrow = 11`
- `RightArrow = 12`
- `F1..F12 = 13..24`
- `Tab = 25`

而 `input_state` 等字段用的是：

- `1u32 << keycode`

因此 `InputGetState`、`InputGetDown`、`InputGetUp`、`InputGetRepeat` 返回的 **不是单一键码，而是按键位图/位掩码整数**。

## 2.3 事件项结构

[`PressItem`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:40-64) 含有：

- `keycode: u8`
- `in_screen: bool`
- `x: i32`
- `y: i32`

而 [`InputGetEvent`](#37-inputgetevent) 对外只暴露三元表：

- `{ keycode, x, y }`：[`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:39-50)

### 2.4 帧边界行为

rfvp 在 [`app.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/app.rs:347-349, 531-539) 中强调：

- `begin_frame()` 会在 VM 执行前刷新输入快照
- `frame_reset()` 会在 VM 有机会观察到边沿状态之后再清空瞬时信号

因此：

- `InputGetDown` / `InputGetUp` / `InputGetRepeat` / `InputGetWheel`
  - 更偏**本帧瞬时边沿/增量**
- `InputGetState`
  - 更偏**当前持续状态**

---

## 3. `InputFlash`

### 3.1 参数与返回

- **参数个数**：0：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:47)
- **返回值**：`Nil`

### 3.2 具体作用

[`input_flash()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:10-14) 只调用：

- [`inputs_manager.set_flash()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:184-195)

而 [`set_flash()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:184-195) 会清空：

- 事件环写读指针
- `new_input_state`
- `input_repeat`
- `input_state`
- `input_down`
- `input_up`

因此它的语义是：

> **刷新/清空当前输入瞬时状态与事件队列。**

### 3.3 脚本样例

- [`f_000744EB.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000744EB.lua:152-154)
- [`f_00071990.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00071990.lua:58-60)
- [`f_00077EFF.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00077EFF.lua:379-381)

它常见于：

- UI/菜单切换
- 模态流程进入前
- 防止旧点击/旧键沿污染下一段逻辑

---

## 4. `InputGetCursIn`

### 4.1 参数与返回

- **参数个数**：0
- **返回值**：`BoolLike`

### 4.2 具体作用

[`input_get_curs_in()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:17-25) 返回：

- `True`：`cursor_in == true`
- `Nil`：否则

而 `cursor_in` 在事件层由 [`event_handler.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/event_handler.rs:61-108) 维护，语义是：

- 鼠标是否位于**游戏虚拟内容区域**内，而不是窗口任意位置

### 4.3 语义判断

> **判断鼠标当前是否处于游戏可交互内容区内。**

---

## 5. `InputGetCursX` / `InputGetCursY`

### 5.1 参数与返回

- **参数个数**：0
- **返回值**：`Int`

### 5.2 具体作用

- [`InputGetCursX`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:27-29) 返回 `cursor_x`
- [`InputGetCursY`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:31-33) 返回 `cursor_y`

这些值由 [`event_handler.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/event_handler.rs:61-102) 从窗口物理像素坐标映射到**游戏虚拟分辨率坐标系**。

### 5.3 语义判断

> **读取当前鼠标在游戏虚拟坐标系中的 X/Y。**

### 5.4 脚本样例

- [`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:680-707)
- [`f_000744EB.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000744EB.lua:276-327)
- [`f_0006D13F.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0006D13F.lua:1791-1795)

这些调用普遍用于：

- 命中测试
- 菜单项 hover
- 拖动/定位 UI

---

## 6. `InputGetDown`

### 6.1 参数与返回

- **参数个数**：0
- **返回值**：`Int`

### 6.2 具体作用

[`input_get_down()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:35-37) 返回：

- `inputs_manager.get_input_down() as i32`

也就是：

> **本帧新按下的按键/按钮位图。**

### 6.3 语义判断

脚本侧通常会立刻与按键掩码做 `&`：

- `& 1`：Ctrl
- `& 3`：Ctrl/Shift 或虚拟点击混合判断（具体要看代码上下文）
- 其他位同理

因此它不是“最近一次按下的单个键码”，而是：

- **边沿位图**

### 6.4 脚本样例

- [`f_00074DA5.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00074DA5.lua:228-257)
- [`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:144-223)
- [`f_00089A85.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00089A85.lua:16-18)

这些都表明 `InputGetDown` 是：

> **按钮点击/跳过/确认动作的主判断来源之一。**

---

## 7. `InputGetEvent`

### 7.1 参数与返回

- **参数个数**：0
- **返回值**：`Table|Nil`

### 7.2 具体作用

[`input_get_event()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:39-50) 会：

1. 从 [`get_event()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:219-229) 弹出一个事件
2. 组装成表：
   - `[0] = keycode`
   - `[1] = x`
   - `[2] = y`
3. 无事件则返回 `Nil`

### 7.3 语义判断

> **从输入事件环形队列中取出下一条离散事件。**

这和 `InputGetState` 的区别是：

- `InputGetState`：当前持续状态
- `InputGetEvent`：离散事件流

### 7.4 事件来源

事件队列由：

- [`notify_keydown()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:370-403)
- [`notify_mouse_down()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:431-467)
- [`notify_mouse_up()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:470-506)

通过 [`record_keydown_or_up()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:346-367) 写入 64 项环形缓冲。

---

## 8. `InputGetRepeat`

### 8.1 参数与返回

- **参数个数**：0
- **返回值**：`Int`

### 8.2 具体作用

[`input_get_repeat()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:52-54) 返回：

- `input_repeat`

它表示：

> **本帧处于 repeat 状态的按键位图。**

### 8.3 语义判断

这更适合：

- 长按菜单导航
- 连续滚动/持续按键推进

### 8.4 脚本样例

- [`f_0008916F.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008916F.lua:118-120)
- [`f_0008AC48.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008AC48.lua:5-7)
- [`f_00095855.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00095855.lua:60-62)

---

## 9. `InputGetState`

### 9.1 参数与返回

- **参数个数**：0
- **返回值**：`Int`

### 9.2 具体作用

[`input_get_state()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:56-58) 返回当前的：

- `input_state`

它表示：

> **当前这一时刻所有按键/按钮的持续按下位图。**

### 9.3 与 `InputGetDown` 的区别

- `InputGetDown`：0→1 的边沿，本帧新按下
- `InputGetState`：持续保持为 1 的按下状态

### 9.4 脚本样例

- [`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:698-699)
- [`f_0004CF35.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004CF35.lua:183-185)
- [`f_0004A5DE.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004A5DE.lua:9-10)

通常被用于：

- 是否持续按住跳过键
- 是否持续按住方向键/确认键

---

## 10. `InputGetUp`

### 10.1 参数与返回

- **参数个数**：0
- **返回值**：`Int`

### 10.2 具体作用

[`input_get_up()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:60-62) 返回：

- `input_up`

也就是：

> **本帧新释放的按键/按钮位图。**

### 10.3 脚本样例

- [`f_0004D7A6.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004D7A6.lua:312-314)
- [`f_0008B6FC.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008B6FC.lua:11-13)
- [`f_00094B59.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00094B59.lua:29-31)

这说明它常用于：

- 松键触发
- 鼠标释放判定
- 菜单拖动结束/抬起确认

---

## 11. `InputGetWheel`

### 11.1 参数与返回

- **参数个数**：0
- **返回值**：`Int`

### 11.2 具体作用

[`input_get_wheel()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:64-66) 返回：

- `wheel_value`

并且源码注释明确说明：

- wheel 值通常会在每帧更新后归零：[`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:272-276)

因此它应理解为：

> **本帧滚轮增量。**

### 11.3 脚本样例

- [`f_000487BE.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000487BE.lua:126-133)
- [`f_0006D13F.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0006D13F.lua:2830-2832)
- [`f_00094C58.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00094C58.lua:9-11)

这说明它主要用于：

- backlog 滚动
- 菜单分页
- 轮盘选择

---

## 12. `InputSetClick`

### 12.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:57)
- **签名**：`InputSetClick(clicked)`
- **返回值**：`Nil`

### 12.2 具体作用

[`input_set_click()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:68-76) 只接受：

- `Variant::Int(0)`
- `Variant::Int(1)`

并把值写入 [`inputs_manager.set_click()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:258-261)。

而这个 `click` 模式随后会影响：

- [`notify_mouse_down()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:454-466)
- [`notify_mouse_up()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:493-505)

即：

- `click == 1` 时，鼠标按下事件会被记录
- `click == 0` 时，鼠标抬起事件会被记录

### 12.3 语义判断

可概括为：

> **控制脚本侧把鼠标点击事件记录在“按下沿”还是“抬起沿”。**

这不是简单的“模拟点击”，而更像：

- **切换鼠标事件触发策略**

### 12.4 脚本解释

源码注释自己也写得较保守：

> Maybe this is used to simulate mouse clicks in certain scenarios.

结合 `notify_mouse_down/up()` 的实现，我认为更准确的归纳是：

> **它控制鼠标事件进入 PressItem 队列的边沿时机。**

---

## 13. Input 分组的整体语义

把这 11 个 syscall 放在一起，可以归纳出一套非常清晰的输入模型：

1. **状态位图层**
   - `InputGetState`
   - `InputGetDown`
   - `InputGetUp`
   - `InputGetRepeat`
   - `InputGetWheel`
2. **鼠标位置层**
   - `InputGetCursIn`
   - `InputGetCursX`
   - `InputGetCursY`
3. **离散事件层**
   - `InputGetEvent`
4. **输入系统控制层**
   - `InputFlash`
   - `InputSetClick`

因此 Input 分组的整体语义可以概括为：

> **脚本层对“当前帧输入快照 + 鼠标位置 + 离散事件队列”的统一访问接口。**

---

## 14. 高置信度结论

以下结论比较稳：

- Input 分组当前包含 11 个 syscall。
- `InputGetState/Down/Up/Repeat` 返回的是位图整数，不是单一键码。
- `InputGetEvent` 返回 `{keycode, x, y}` 表结构或 `Nil`。
- `InputGetCursX/Y` 返回的是虚拟分辨率坐标，不是窗口物理像素。
- `InputGetWheel` 返回本帧滚轮增量。
- `InputFlash` 会清空瞬时输入状态与事件队列。
- `InputSetClick` 用于控制鼠标事件记录在按下沿还是抬起沿。

---

## 15. 仍需保守处理的点

1. `InputSetClick` 在不同游戏里的业务层目的可能不同；当前可高置信度说明其底层效果，但不宜在语义数据库里过度命名为“模拟点击”。
2. 各个位图位在脚本层具体代表哪些快捷逻辑，还需要结合更多游戏的输入判断模式继续归纳。
3. `InputGetRepeat` 在不同平台/宿主下的 repeat 节律可能略有差异；当前语义以 rfvp 为基线。

---

## 16. 证据来源

- [`README.md`](../manual/syscall-db.md:29-44)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:41-51)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:47-57)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:648-659)
- [`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:10-76)
- [`input.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/input.rs:95-299)
- [`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:40-64)
- [`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:151-266)
- [`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:346-367)
- [`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:370-518)
- [`event_handler.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/event_handler.rs:6-120)
- [`f_00074DA5逐条反汇编对照.md`](../reversals/f_00074DA5逐条反汇编对照.md:44-46)
- [`newfvplogo逐条反汇编对照.md`](../../hcbtool_test/newfvplogo逐条反汇编对照.md:37-39)
- [`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:144-223, 680-707)
- [`f_000744EB.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000744EB.lua:152-154, 276-327)
- [`f_00071990.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00071990.lua:58-60, 512-582)
- [`f_0004CF35.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004CF35.lua:183-189)
- [`f_000487BE.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000487BE.lua:126-133, 352-381)
