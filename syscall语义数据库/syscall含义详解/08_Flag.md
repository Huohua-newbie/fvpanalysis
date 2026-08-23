# Flag 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../README.md)、[`syscall_spec.txt`](../syscall_spec.txt) 与 rfvp 参考实现，Flag 分组当前包含 2 个 syscall：

1. `FlagGet`
2. `FlagSet`

其注册位置可见于：

- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:39-40)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:561-563)

综合源码与脚本调用样例，Flag 分组可以概括为：

> **脚本侧对 2048 个位标志位进行读写的接口。**

它不是对 Lua 全局变量 `G[...]` 的操作，而是单独维护的一套 **bit-packed flag 存储区**，适合表达：

- 开关状态
- 某选项是否已达成
- 多路选择结果
- 章节/收集要素解锁位

---

## 2. 共享实现约定

## 2.1 底层存储结构

rfvp 把 flag 存在 [`FlagManager`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/flag_manager.rs:5-39) 中：

- 顶层容器是 `HashMap<u8, u8>`：[`flag_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/flag_manager.rs:5-8)
- 每个 `u8 key` 对应 1 个字节的 flag 桶
- 每个字节中再用 8 个 bit 表示 8 个独立布尔位

这说明 FVP 的 flag 语义不是“稀疏字符串键”，而是：

> **编号化的位标志系统。**

## 2.2 统一编号规则

[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:54-60) 给出了明确约定：

- 参数名是 `id_bit_pos`
- 合法范围：`0..2047`
- 高 8 位用于字节桶 ID
- 低 3 位用于字节内 bit 位置

源码里的实际换算是：

- `id = id_bit_pos / 8`：[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:24,44)
- `bits = id_bit_pos & 7`：[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:25,45)

因此这组 syscall 的核心输入不是“flag 名称”，而是：

> **线性编号后的 flag 位索引。**

## 2.3 返回值风格

- [`FlagSet`](#4-flagset) 返回 `Nil`：[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:27-28)
- [`FlagGet`](#3-flagget) 返回 `True / Nil`：[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:47-51)

因此本组统一表现为：

- 写操作：`Nil`
- 读操作：`BoolLike`

---

## 3. `FlagGet`

### 3.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:39)
- **签名**：`FlagGet(id_bit_pos)`
- **参数含义**：
  - `arg0: Int`：flag 位索引，范围 `0..2047`
- **返回值**：
  - `True`：该 flag 位被置 1
  - `Nil`：该 flag 位未置 1 或参数非法

### 3.2 具体作用

[`flag_get()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:31-51) 的逻辑是：

1. 参数必须是 `Int`：[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:32-37)
2. 索引必须在 `0..=2047`：[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:39-42)
3. 把线性索引拆成：
   - `id = idx / 8`
   - `bits = idx & 7`
4. 调 [`flag_manager.get_flag(id, bits)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/flag_manager.rs:29-37)
5. 若结果为真，则返回 `True`，否则返回 `Nil`

### 3.3 语义判断

可概括为：

> **读取某个编号 flag 位是否已被置位。**

它不是返回 `0/1 Int`，而是标准 FVP 布尔风格：

- 真 -> `True`
- 假 -> `Nil`

### 3.4 脚本样例

在 [`WA_funta.lua`](../../hcbtool_test/WA_funta_hcb_ir/WA_funta.lua:110053-110073) 中可以看到一段典型模式：

- 先取 `G[77]`
- 然后连续执行：
  - `FlagGet(G[77])`
  - `FlagGet(G[77] + 1)`
  - `FlagGet(G[77] + 2)`
  - `FlagGet(G[77] + 3)`

这说明脚本作者会把一组相邻 flag 位当作**四路状态组**来批量查询。

在后续代码 [`WA_funta.lua`](../../hcbtool_test/WA_funta_hcb_ir/WA_funta.lua:113045-113063) 中，这些返回值会和 `true` 比较后决定后续分支，进一步印证：

> `FlagGet` 的结果就是标准布尔位查询结果。

---

## 4. `FlagSet`

### 4.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:40)
- **签名**：`FlagSet(id_bit_pos, on)`
- **参数含义**：
  - `arg0: Int`：flag 位索引，范围 `0..2047`
  - `arg1: Variant`：按 `canbe_true()` 解释的开关值
- **返回值**：`Nil`

### 4.2 具体作用

[`flag_set()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:9-29) 的逻辑是：

1. `arg0` 必须是 `Int`
2. 索引范围必须在 `0..=2047`
3. 对 `arg1` 执行 `canbe_true()`：[`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:17)
4. 拆分 `id = idx / 8`、`bits = idx & 7`
5. 调 [`flag_manager.set_flag(id, bits, on)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/flag_manager.rs:11-27)

而 [`set_flag()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/flag_manager.rs:11-27) 会：

- `on == true` 时置位：`flag |= 1 << pos`
- `on == false` 时清位：`flag &= !(1 << pos)`

### 4.3 语义判断

可概括为：

> **把某个编号 flag 位设为 1 或清为 0。**

它并不只是“置 true”，而是完整的 set/clear 接口；只是脚本中更常见的是设为真。

### 4.4 第二参数语义

由于实现使用的是 `canbe_true()`，所以：

- `true`：置位
- `nil`：清位
- 其他可判真的值：通常也会置位

因此第二参数最好记录为：

- `Variant / BoolLike`
- 经 `canbe_true()` 解释成布尔意义

### 4.5 脚本样例

在 [`WA_funta.lua`](../../hcbtool_test/WA_funta_hcb_ir/WA_funta.lua:112982-113014) 中，脚本根据 `G[74]` 的不同值，把 `l0/l1/l2/l3` 其中一个 flag 位设为 `true`：

- `FlagSet(l0, true)`
- `FlagSet(l1, true)`
- `FlagSet(l2, true)`
- `FlagSet(l3, true)`

这非常像：

> **把某个多选菜单/章节选择结果编码进 4 个连续 flag 位中的某一位。**

因此可以看出 `FlagSet` 在实际脚本里常被当作：

- 章节状态记录器
- 路线/选项结果记录器
- 条件达成位写入器

---

## 5. Flag 分组的整体语义

把 [`FlagSet`](#4-flagset) 与 [`FlagGet`](#3-flagget) 放在一起看，Flag 分组就是一套：

> **面向 2048 个 bit 标志位的紧凑布尔状态存储接口。**

这和 `G[...]` 全局变量不同：

- `G[...]` 更像脚本运行时的普通全局槽
- `Flag*` 更像专门的“长期条件/事件位表”

在脚本工程层面，它非常适合：

- 存储是否看过某事件
- 是否解锁某菜单项
- 多路选择结果
- 条件累计后的布尔判据

---

## 6. 高置信度结论

以下结论比较稳：

- Flag 分组当前包含 `FlagGet` 与 `FlagSet` 两个 syscall。
- 它们的编号空间是 `0..2047`，总计 2048 个 bit 位。
- 每个线性索引会被拆成：
  - 字节桶 `id = idx / 8`
  - 位序号 `bits = idx & 7`
- `FlagGet` 返回 `True/Nil`。
- `FlagSet` 第二参数通过 `canbe_true()` 判真，既可置位也可清位。
- 这组 syscall 操作的是独立的 `FlagManager`，不是 `G[...]` 全局变量区。

---

## 7. 仍需保守处理的点

1. Sakura 当前拆出的 [`Sakura_hcb_ir`](../../hcbtool_test/Sakura_hcb_ir) 中几乎没有直接出现 `FlagGet/FlagSet`，说明不同 FVP 游戏对这组 syscall 的依赖强弱差异较大；本结论更多基于 rfvp 源码与 [`WA_funta.lua`](../../hcbtool_test/WA_funta_hcb_ir/WA_funta.lua:110053-110073) 的样例。
2. 线性编号空间虽然明确是 2048 bit，但具体哪些编号在游戏设计层分别代表什么，还需要逐游戏专项标注，不能在 syscall 层泛化命名。

---

## 8. 证据来源

- [`README.md`](../README.md:29-44)
- [`syscall_spec.txt`](../syscall_spec.txt:33-34)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:39-40)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:561-563)
- [`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:9-29)
- [`flag.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/flag.rs:31-51)
- [`flag_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/flag_manager.rs:11-37)
- [`FVP引擎文献综述.md`](../FVP引擎文献综述.md:156-180)
- [`WA_funta.lua`](../../hcbtool_test/WA_funta_hcb_ir/WA_funta.lua:110053-110073)
- [`WA_funta.lua`](../../hcbtool_test/WA_funta_hcb_ir/WA_funta.lua:112982-113014)
- [`WA_funta.lua`](../../hcbtool_test/WA_funta_hcb_ir/WA_funta.lua:113045-113063)
