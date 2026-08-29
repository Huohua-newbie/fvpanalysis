# Cursor 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md) 的分组顺序、[`syscall_spec.txt`](../spec/syscall_spec.txt) 的简表，以及 rfvp 参考实现，Cursor 分组当前包含 3 个 syscall：

1. `CursorShow`
2. `CursorMove`
3. `CursorChange`

其注册位置可见于 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:31-33) 与 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:734-737)。

综合源码与脚本调用样例，Cursor 分组可以直接定性为：

> **游标 / 鼠标光标控制接口。**

它不是输入读取接口，而是**修改光标可见性、位置与样式**的一组控制 API。

---

## 2. 共享实现约定

## 2.1 作用对象

rfvp 的 Cursor 分组会同时影响三类状态：

- `window` 层的光标显示/位置/样式：[`cursor.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:13-18)、[`window.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/window.rs:74-83)
- `inputs_manager` 中的鼠标位置与“是否在窗口内”状态：[`cursor.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:43-46)
- `GameData` 中的当前 ANI 游标索引：[`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:463-485)

因此这组 syscall 的核心不是“询问鼠标在哪里”，而是：

> **把脚本层指定的光标状态同步到引擎与平台后端。**

## 2.2 返回值风格

这 3 个 syscall 都返回 `Nil`：

- [`CursorShow`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:9-19)
- [`CursorMove`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:22-50)
- [`CursorChange`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:53-80)

---

## 3. `CursorShow`

### 3.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:31-33)
- **签名**：`CursorShow(show)`
- **参数含义**：
  - `arg0: Variant`：光标显示开关；`Nil` 与非 `Nil` 有不同含义
- **返回值**：`Nil`

### 3.2 具体作用

[`CursorShow`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:9-19) 的实现非常直接：

1. 读取第一个参数，并将 `!is_nil` 作为显示布尔值：[`cursor.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:14)
2. 调 [`window.set_cursor_visible(show)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/window.rs:74-78)
3. 返回 `Nil`

### 3.3 语义判断

可概括为：

> **控制系统/平台层鼠标光标是否可见。**

注意它不是“光标样式切换”，也不是“光标位置移动”，只是可见性开关。

### 3.4 参数语义

- `Nil`：隐藏光标
- 非 `Nil`：显示光标

也就是说，`CursorShow` 使用的是 **Variant 的空/非空语义**，而不是普通的整数 0/1 语义。

### 3.5 脚本样例

- [`f_00079436()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00079436.lua:17-18) 调用 `CursorShow(nil)`
- 同函数后续又调用 `CursorShow(true)`：[`f_00079436.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00079436.lua:61-63)

这表明它常用于标题/界面切换阶段的光标显隐控制。

---

## 4. `CursorMove`

### 4.1 参数与返回

- **参数个数**：3：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:31-33)
- **签名**：`CursorMove(x, y, force)`
- **参数含义**：
  - `arg0: Int`：目标 X 坐标
  - `arg1: Int`：目标 Y 坐标
  - `arg2: Variant`：强制移动开关；非 `Nil` 时强制生效
- **返回值**：`Nil`

### 4.2 具体作用

[`CursorMove`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:22-50) 的逻辑是：

1. 读取 x / y，要求都是整数
2. `force = !args[2].is_nil()`
3. `allow = get_int_var(15) == 1`
4. 若 `allow || force` 成立，则：
   - [`inputs_manager.notify_mouse_move(x, y)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:43-46)
   - [`inputs_manager.set_mouse_in(true)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:44-46)
   - [`window.set_cursor_pos(x, y)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:45-46)

### 4.3 语义判断

可概括为：

> **把光标移动到指定虚拟坐标，并同步给输入层与窗口层。**

### 4.4 第三个参数语义

第三参数不是“坐标”，而是一个**强制开关**：

- `Nil`：仅在全局条件允许时移动
- 非 `Nil`：强制移动

rfvp 源码注释还明确指出：

- 只有当 `args[0]` 与 `args[1]` 都为整数时才移动
- 移动权限受全局 int var 15 控制，或者由 force 参数覆盖：[`cursor.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:25-29)

### 4.5 脚本样例

- [`f_0004EF3D.lua`](../../hcbtool_ir/Sakura/f_0004EF3D.lua:52-54)
- [`f_0006D13F.lua`](../../hcbtool_ir/Sakura/f_0006D13F.lua:1674-1676)
- [`f_00076122.lua`](../../hcbtool_ir/Sakura/f_00076122.lua:641-666)
- [`f_00076E4C.lua`](../../hcbtool_ir/Sakura/f_00076E4C.lua:136-138)

这些调用几乎都采用 `CursorMove(x, y, nil)` 或 `CursorMove(x, y, true)` 的形式，说明它多用于：

- 菜单光标停靠
- 标题项选中位置调整
- 屏幕内鼠标坐标同步

### 4.6 语义边界

`CursorMove` 不等于“改变当前光标样式”；样式切换属于 [`CursorChange`](#5-cursorchange)。

---

## 5. `CursorChange`

### 5.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:31-33)
- **签名**：`CursorChange(id)`
- **参数含义**：
  - `arg0: Int`：游标样式/动画索引，合法范围 `0..3`
- **返回值**：`Nil`

### 5.2 具体作用

[`CursorChange`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:53-80) 会：

1. 读取 `id`，要求是整数
2. 限制范围 `0..4`（即 0~3）
3. 若 `id == 0`：
   - 设置当前 cursor index 为 0
   - 将窗口游标 kind 置 0：[`cursor.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:66-69)
4. 若该 index 存在 ANI 游标：
   - 调 [`switch_cursor(index)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:472-480)
5. 否则：
   - 只更新当前 cursor index
   - 并让窗口层使用 fallback kind：[`cursor.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:72-78)

### 5.3 语义判断

可概括为：

> **切换当前使用的游标样式/游标动画索引。**

这里它不是“显示/隐藏”，而是“换成哪一种 cursor”。

### 5.4 脚本样例

- [`entry_point.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/entry_point.lua:316-317) 初始化时设为 `0`
- [`entry_point.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/entry_point.lua:633-635) 根据 [`G[1990]`](../../hcbtool_test/Sakura_hcb_ir/Sakura/entry_point.lua:633) 恢复当前 cursor
- [`entry_point.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/entry_point.lua:653-655) 返回标题循环前再次归位
- [`f_0008E5FC.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008E5FC.lua:48-50) 也会调用 `CursorChange(G[1990])`
- [`f_00039C85.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00039C85.lua:1131-1133) 在界面/菜单流程中调用 `CursorChange(a2)`

### 5.5 语义边界

`CursorChange(0)` 在实现中表示“默认光标”。

---

## 6. Cursor 分组的整体工作流

从脚本常见调用模板看，Cursor 分组通常按以下顺序组合出现：

1. [`CursorShow`](#3-cursorshow) 控制可见性
2. [`CursorChange`](#5-cursorchange) 选择游标样式
3. [`CursorMove`](#4-cursormove) 同步光标位置

这说明 Cursor 分组是一个完整的**光标状态管理链**：

- `CursorShow` 决定“看不看得见”
- `CursorChange` 决定“长什么样”
- `CursorMove` 决定“放在哪里”

---

## 7. 高置信度结论

以下结论比较稳：

- Cursor 分组当前包含 3 个 syscall：`CursorShow`、`CursorMove`、`CursorChange`。
- `CursorShow` 1 参，返回 `Nil`，语义是控制光标可见性。
- `CursorMove` 3 参，返回 `Nil`，语义是同步光标坐标；第三参是强制开关。
- `CursorChange` 1 参，返回 `Nil`，语义是切换游标样式/索引。
- 这组 syscall 会同时影响 `window` 与 `inputs_manager` 的状态。
- `CursorMove` 是否实际生效，受全局 int var 15 与 force 参数双重影响。

---

## 8. 证据来源

- [`README.md`](../manual/syscall-db.md:29-44)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:25-27)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:31-33)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:463-485, 734-737)
- [`cursor.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/cursor.rs:9-80)
- [`window.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/window.rs:74-83)
- [`input_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/input_manager.rs:520-547)
- [`entry_point.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/entry_point.lua:316-317, 633-635, 653-655)
- [`f_00079436.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00079436.lua:17-18, 61-63)
- [`f_0008E5FC.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008E5FC.lua:48-50)
- [`f_00039C85.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00039C85.lua:1131-1133)
- [`f_0004EF3D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004EF3D.lua:52-54)
- [`f_00076122.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076122.lua:641-666)
- [`f_00076E4C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00076E4C.lua:136-138)
- [`f_000744EB.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000744EB.lua:264-265)
