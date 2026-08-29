# Title 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:110)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7684-7719) 与 rfvp 参考实现，`Title` 分组当前只有 1 个 syscall：

- `TitleMenu`

其规格位于 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:162)，运行时实现位于 [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:214-216)，注册位置见 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:745)。

当前 reference 能够高置信度确认的只有：

- 参数数量为 1；
- 参数在数据库中暂时是 `Variant` generic；
- 返回值为 `Nil`；
- 当前 rfvp 实现直接 no-op；
- 不产生 yield、wait、sleep、text_wait、dissolve_wait 或 halt。

因此，Title 分组的最保守结论是：

> **Title 组是标题菜单相关的兼容接口层；当前 rfvp 没有恢复 `TitleMenu` 的具体业务逻辑。**

---

## 2. `TitleMenu`

### 2.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7687)
- **签名**：`TitleMenu(arg0)`
- **参数类型**：`Variant`，当前数据库 `confidence=generic`
- **返回值**：`Nil`
- **数据库影响子系统**：`title/menu state`
- **数据库控制流**：无调度副作用

### 2.2 当前 rfvp 实现

当前函数定义为：

```rust
pub fn title_menu(_game_data: &mut GameData, _title: &Variant) -> Result<Variant> {
    Ok(Variant::Nil)
}
```

见 [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:214-216)。

因此当前实现的实际行为是：

- 不读取参数内容；
- 不写入标题菜单状态；
- 不创建标题菜单 prim；
- 不修改输入系统；
- 不启动或退出 Context；
- 不改变窗口、场景或存档状态；
- 直接返回 `Nil`。

### 2.3 入参语义

数据库目前只记录 `arg0: Variant`，没有给出具体类型和含义：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7688-7694)。

从函数参数名 `_title` 和 syscall 名称 `TitleMenu` 可以保守推测，`arg0` 可能与以下内容之一有关：

- 标题菜单模式；
- 标题菜单状态；
- 标题菜单编号或入口；
- 标题画面切换参数；
- 旧版标题 UI 的菜单对象/状态标志。

但是，当前 reference 没有证明它是：

- 标题字符串；
- 整数模式；
- 菜单选择结果；
- 菜单显示开关；
- 标题菜单资源 ID。

因此本项目当前不应把 `arg0` 强行细化为某一种类型。

### 2.4 具体作用：当前实现与原版推断分离

#### 当前 rfvp 行为

当前 rfvp 中，`TitleMenu(arg0)` 等价于一个安静的兼容占位：

```text
读取参数：否
修改状态：否
产生返回：Nil
产生调度：否
```

#### 原版业务推断

`TitleMenu` 的名称显然指向标题菜单系统，但这只能作为低到中等可信度的命名证据。原版可能使用该 syscall：

- 初始化标题菜单；
- 进入标题菜单状态；
- 切换标题菜单与剧情/游戏模式；
- 通知宿主显示旧式标题菜单；
- 设置标题菜单的某种模式或状态。

这些可能性都需要通过原版二进制逆向、HCB 调用样例或实机行为进一步验证。

### 2.5 结论

> `TitleMenu` 是一个与标题菜单相关的单参数兼容接口；当前 rfvp 实现为 no-op，参数的具体类型、返回前置条件和原版菜单动作均尚未恢复。

---

## 3. TitleMenu 与现有标题菜单构建链的边界

### 3.1 标题菜单并不等于一个 syscall

现有标题菜单研究表明，标题界面通常由多个系统共同构建，而不是完全由一个 `TitleMenu` syscall 完成。例如 [`f_00075195逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00075195逐条反汇编对照.md:15-81) 显示，标题菜单相关函数会处理：

- 多个菜单/按钮 prim；
- 图像资源加载；
- group 层级；
- `PrimSetDraw`；
- `PrimSetAlpha`；
- `PrimSetZ`；
- `PrimSetOP`；
- `PrimSetRS`；
- `MotionAnim` 等动画。

因此：

> **现有研究中标题菜单的可见表现主要来自 Prim、Motion、Input、Text 等组的组合，而不是当前已实现的 `TitleMenu` 函数体。**

### 3.2 与 `MenuMessSkip` 的边界

[`MenuMessSkip`](fvp_analysis/result/syscall语义数据库/syscall含义详解/17_Menu.md:5-19) 属于 `Menu` 分组，当前也是兼容占位；[`TitleMenu`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7684) 则属于 `Title` 分组。

两者不应混淆：

- `MenuMessSkip`：名称偏向菜单消息跳过；
- `TitleMenu`：名称偏向标题菜单；
- 当前两者都没有完整业务实现，但分组语义不同。

### 3.3 与 `SaveTitle` / `LoadTitle` 的边界

`SaveTitle` / `LoadTitle` 属于 `Save` 分组，不是 `Title` 分组：

- `TitleMenu`：可能涉及标题菜单 UI 状态；
- `SaveTitle` / `LoadTitle`：旧版标题状态存取兼容接口。

当前三者都存在一定 legacy/兼容性质，但不能在 syscall 数据库中合并。

---

## 4. Title 组整体语义

由于本分组只有一个 syscall，且当前实现为空操作，整体语义只能分成两层：

### 4.1 当前 rfvp 语义

```text
TitleMenu(arg0) -> Nil
```

不修改任何可观察状态。

### 4.2 原版可能的语义范围

从名称和数据库影响子系统 `title/menu state` 看，它大概率属于：

- 标题菜单状态通知；
- 标题菜单初始化/切换；
- 标题菜单宿主 UI 兼容入口。

但目前不能确定其具体动作。

因此 Title 组的整体结论是：

> **Title 组目前只能作为“标题菜单相关兼容符号”记录，不能作为已经完成语义恢复的标题菜单控制总线。**

---

## 5. 高置信度结论

以下结论比较稳：

- `Title` 分组当前只有 1 个 syscall：`TitleMenu`。
- `TitleMenu` 有 1 个参数。
- 当前数据库把参数记录为 `Variant` generic，尚未细化。
- 当前实现直接返回 `Nil`。
- 当前实现不读取参数、不修改状态、不改变 VM 调度。
- 数据库将其影响子系统记录为 `title/menu state`。
- 现有标题菜单的实际显示和动画主要通过 Prim、Motion、Text、Input 等组组合完成。
- `TitleMenu` 与 `MenuMessSkip`、`SaveTitle`、`LoadTitle` 属于不同分组，不能混为同一接口。

---

## 6. 仍需保守处理的点

1. `TitleMenu` 的参数是否为整数模式、字符串、菜单编号、状态开关或其他 Variant，当前没有证据确认。
2. 原版 `TitleMenu` 是“显示标题菜单”“初始化标题菜单”“切换标题状态”还是“通知宿主菜单系统”，当前无法区分。
3. 当前 rfvp 的 no-op 行为不等价于原引擎一定无副作用；它可能只是兼容实现未完成。
4. 当前已检索到的标题菜单研究主要分析 Prim/Motion/输入/文本组合，没有找到可直接绑定 `TitleMenu` 参数和行为的稳定 HCB 调用样例。
5. 后续如要恢复该接口，应优先从含有 `TitleMenu` 导入项的原版 HCB、旧版主循环或标题菜单 native UI 入口进行逆向。

---

## 7. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:110-112)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7684-7719)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:162)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:745)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:214-216)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:349-357)
- [`17_Menu.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/17_Menu.md:109-121)
- [`21_Prim.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/21_Prim.md:1-937)
- [`18_Motion.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/18_Motion.md:439-520)
- [`f_00075195逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00075195逐条反汇编对照.md:15-81)
- [`Sakura_entry_point功能分析.md`](fvp_analysis/result/hcbtool_test/Sakura_entry_point功能分析.md:7-9,115-133,389-391)
