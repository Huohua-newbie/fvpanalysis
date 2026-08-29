# Menu 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:78)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:59) 与 rfvp 参考实现，Menu 分组当前只有 1 个 syscall：

- `MenuMessSkip`

其来源可见于：

- [`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:62)
- [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:739)
- [`utils.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:438)

综合当前证据，Menu 分组最稳妥的定性是：

> **旧版菜单/消息跳过相关的占位兼容接口。**

在 rfvp 当前实现中，它是一个**无副作用的 no-op**：被调用时仅返回 `Nil`，不改变游戏状态、不影响线程调度，也没有观察到 Sakura 中的实际调用样例。

---

## 2. 证据现状与限制

与前面多数分组不同，Menu 分组当前证据非常稀少：

1. 自动规格表只告诉我们：
   - 名称是 `MenuMessSkip`
   - 分组是 `Menu`
   - 参数个数是 `1`：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:62)
2. rfvp 运行时注册表确实把它注册进了 syscall 表：[`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:739)
3. 当前实现函数体是空操作：[`utils.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:438-445)
4. 目前在已检索到的 [`Sakura_hcb_ir`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir) 中**没有直接调用样例**。

因此，这一条目必须采取非常保守的写法：

> 目前能高置信度确认的是“接口存在 + 1 参数 + 当前 rfvp 实现为空”，而**原引擎中的完整菜单语义尚未恢复**。

---

## 3. `MenuMessSkip`

## 3.1 参数与返回

- **参数个数**：1：[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:59)
- **签名**：`MenuMessSkip(arg0)`
- **返回值**：`Nil`

### 3.2 当前 rfvp 实现

rfvp 中的实现定义在 [`utils.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:438-445)：

- 结构体：[`MenuMessSkip`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:440)
- `call()` 本体：直接 `Ok(Variant::Nil)`：[`utils.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:441-443)

也就是说，在 rfvp 当前版本里：

- 不读取参数内容
- 不写 `GameData`
- 不写线程请求
- 不进入 `yield/wait/sleep/halt`
- 不做日志输出

它只是一个安静返回的空接口。

## 3.3 语义判断

从名字字面上可以拆成两部分：

- `Menu`
- `MessSkip`（很像 `Message Skip`）

因此从命名直觉上，它大概率和：

- 菜单中的消息跳过选项
- 消息跳过模式切换
- 菜单层的 skip 设置

存在关联。

但由于当前：

- rfvp 没有实现其业务逻辑
- 脚本样例中也没有找到直接调用
- 参考文档中没有进一步说明

所以本数据库里不应把它写死成“消息跳过开关”，更保守的说法应是：

> **与菜单层消息跳过行为相关的兼容保留接口；当前 rfvp 中未实现具体语义。**

---

## 4. 为什么会被归到 Menu 分组

自动规格表把它单独归到 `Menu`：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:62)，而不是 `Text` 或 `Input`。这至少说明在原始 syscall 名表的抽象里，它更接近：

- 菜单层行为
- 或菜单系统中的一项设置/动作

而不是底层输入轮询或文本打印行为本身。

因此数据库中可以保留如下高层标签：

- **功能域**：菜单系统
- **可能业务面向**：消息跳过相关

---

## 5. 与 `TitleMenu` 的边界说明

需要特别说明的是：

- `MenuMessSkip` 在自动规格中属于 `Menu`：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:62)
- `TitleMenu` 则被自动规格单独归为 `Title`：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:162)

因此，虽然它们名字都带“菜单”意味，但在数据库里不应混为一类：

- `MenuMessSkip`：偏菜单消息跳过
- `TitleMenu`：偏标题菜单

当前这次只分析 `Menu` 分组，因此只覆盖 `MenuMessSkip`。

---

## 6. 高置信度结论

以下结论比较稳：

- Menu 分组当前只有 1 个 syscall：`MenuMessSkip`。
- 它有 1 个参数，返回 `Nil`。
- 它在 rfvp 当前实现中是纯 no-op。
- 从命名看，它很可能与“菜单层消息跳过”有关。
- 但在没有脚本调用样例与原引擎进一步证据前，不能把其业务行为写死。

---

## 7. 仍需保守处理的点

1. `MenuMessSkip` 的参数含义目前完全未知；只能确认它“有 1 个参数”，但当前实现未消费。
2. 其原始语义可能存在于更早期 FVP 或某个未覆盖的菜单系统中，需要后续靠原版实机或更多脚本样例补证。
3. 当前 `syscall_spec.txt` 里把其 `affected_subsystems` 标成 `unknown`、`needs_runtime_verification`：[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:59)，这与我们的结论一致，应保留这种低确定性标签。

---

## 8. 数据库建议写法

若后续回写到机器可读数据库，建议本条目的关键字段采用：

- `name = "MenuMessSkip"`
- `group = "Menu"`
- `arg_count = 1`
- `parameter_types = [Variant(generic)]`
- `return_type = Nil`
- `affected_game_data_subsystems = unknown`
- `implementation_status = stub_or_noop / needs_runtime_verification`
- `notes = menu/message-skip related legacy placeholder; current rfvp implementation is no-op`

---

## 9. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:78-113)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:59)
- [`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:62)
- [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:739)
- [`utils.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:438-445)
