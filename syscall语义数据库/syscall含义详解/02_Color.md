# Color 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../README.md) 的分组顺序、[`syscall_spec.txt`](../syscall_spec.txt) 的简表，以及 rfvp 参考实现，Color 分组当前只有 1 个 syscall：

- `ColorSet`

其注册位置可见于 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:28) 与 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:621-623)。

综合源码与脚本调用样例，Color 分组可以直接定性为：

> **颜色槽 / 调色板槽写入接口。**

它不直接负责绘制，而是向共享颜色表写入 RGBA 值；后续 `TextColor`、prim 绘制、样式装配等路径再按颜色槽 ID 读取这些值。

---

## 2. 共享实现约定

## 2.1 颜色表结构

rfvp 的颜色系统在 [`ColorManager`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:73-97) 中维护：

- 总共 256 个颜色条目：[`color_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:75-83)
- 颜色条目类型为 RGBA：[`color_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:4-8)
- 默认情况下：
  - 1 号槽为黑色：[`color_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:85)
  - 2 号槽为白色：[`color_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:86)

`ColorSet` 的效果就是修改这个共享颜色表里的某一个条目。

## 2.2 读者/消费者

颜色槽写入后，常见消费者包括：

- 文本颜色路径：[`text.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:97-106)
- prim / 图元绘制路径：[`gpu_prim.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:756-758)

也就是说，ColorSet 不是“立刻画出来”，而是**先写表、再由别的系统按颜色 ID 取值使用**。

---

## 3. `ColorSet`

### 3.1 参数与返回

- **参数个数**：5：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:28)
- **签名**：`ColorSet(id, r, g, b, a)`
- **返回值**：`Nil`：[`color.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/color.rs:15-48)

### 3.2 参数语义

- `arg0: Int`：颜色槽 ID
  - 常规语义范围：`0..255`
  - 实现层先把它按 `u8` 处理，因此脚本里写 `-1` 会落到 `255` 号槽：这一点可由 [`f_00002025.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00002025.lua:11) 的实际调用看出
- `arg1: Int`：红色分量 `0..255`
- `arg2: Int`：绿色分量 `0..255`
- `arg3: Int`：蓝色分量 `0..255`
- `arg4: Int`：透明度分量 `0..255`

### 3.3 具体作用

[`color_set()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/color.rs:8-48) 的核心逻辑是：

1. 读取颜色槽 ID
2. 找到 `motion_manager.color_manager` 对应条目：[`color.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/color.rs:31)
3. 若某个 RGBA 参数是 `Int`，就写入对应分量：[`color.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/color.rs:32-46)
4. 返回 `Nil`

因此它的实际含义非常明确：

> **把指定颜色槽写成一个 RGBA 值。**

### 3.4 类型细节

- 槽位 ID：`Int`
- RGBA：`Int`
- 非 `Int` 分量不会写入（会保持原值不变）：[`color.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/color.rs:32-46)

这意味着 `ColorSet` 更像一个**“按分量覆盖”的颜色槽写入器**，而不是必须每次都完整重写的强制赋值接口。

---

## 4. 脚本中的典型用法

## 4.1 调色板初始化

[`f_00002025()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00002025.lua:1) 是一段非常典型的 ColorSet 批量初始化代码，既有分析已确认它一共包含 51 次 `ColorSet` 调用：[`f_00002025逐条反汇编对照.md`](../../hcbtool_test/f_00002025逐条反汇编对照.md:9-12)。

这类代码表明：

> `ColorSet` 经常被用于启动时一次性填充调色板槽。

并且其中可见脚本直接使用了 `-1` 作为槽位 ID：[`f_00002025.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00002025.lua:11)。

这与实现层的 `u8` 处理方式相互印证：

> **脚本中的 `-1` 实际等价于 255 号颜色槽。**

## 4.2 文本/样式颜色装配

[`f_0008CC08()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008CC08.lua:1) 会把全局变量中的 RGB 组合写入不同颜色槽，再交给 `TextColor` 使用。其开头一组分支都在做 `ColorSet(..., ..., ..., ..., 255)`：[`f_0008CC08.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008CC08.lua:10-15)。

这说明 ColorSet 不只是“画面底色”，也会作为：

> **文本样式 / UI 样式的颜色槽装配基础。**

## 4.3 启动期 UI 颜色槽

[`f_0008E47D()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008E47D.lua:1) 在启动时也会给一组固定槽位写入颜色：

- 220
- 221
- 222
- 223
- 224
- 225

对应的 `ColorSet` 片段可见于 [`f_0008E47D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008E47D.lua:131-162)。

这说明 ColorSet 还经常用于：

> **启动期系统/UI 预设颜色槽的统一装载。**

---

## 5. 可成立的整体语义

把 rfvp 实现与 Sakura 脚本用法合起来看，Color 分组可以概括为：

> **向共享颜色管理器写入 RGBA 条目的接口。**

它的典型用途包括：

1. 启动时初始化调色板；
2. 装配文本颜色与 UI 样式颜色；
3. 为后续 `TextColor`、prim 绘制、样式装配提供颜色槽数据。

---

## 6. 高置信度结论

以下结论比较稳：

- `ColorSet` 是 Color 分组唯一的 syscall。
- 它的参数个数是 5，返回值是 `Nil`。
- 第 1 个参数是颜色槽 ID，后 4 个参数是 RGBA。
- 颜色槽总数为 256；默认槽 1 黑、槽 2 白：[`color_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:75-87)
- `ColorSet` 的效果是改写 `ColorManager` 的某个槽位，不是直接绘制。
- 脚本里 `-1` 写法会落到 255 号槽。

---

## 7. 证据来源

- [`README.md`](../README.md:29-44)
- [`syscall_spec.txt`](../syscall_spec.txt:18-19)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:28)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:621-623)
- [`color.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/color.rs:8-48)
- [`color_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:73-97)
- [`text.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:97-106)
- [`gpu_prim.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:756-758)
- [`f_00002025逐条反汇编对照.md`](../../hcbtool_test/f_00002025逐条反汇编对照.md:9-12)
- [`f_00002025.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00002025.lua:11)
- [`f_0008CC08.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008CC08.lua:10-15)
- [`f_0008E47D.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008E47D.lua:131-162)
- [`f_00002025逐条反汇编对照.md`](../../hcbtool_test/f_00002025逐条反汇编对照.md:12)
