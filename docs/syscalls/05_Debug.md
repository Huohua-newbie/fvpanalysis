# Debug 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md)、[`syscall_spec.txt`](../spec/syscall_spec.txt) 与 rfvp 参考实现，Debug 分组当前应整理为 2 个 syscall：

1. `BREAKPOINT`
2. `Debmess`

其中需要先说明一个**数据库来源差异**：

- 在自动生成表 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:27) 里，`BREAKPOINT` 的 `group` 被写成了 `BREAKPOINT`，`handler` 被写成了 `nullsub_2`
- 但在实际注册表 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:545) 中，`BREAKPOINT` 实际绑定到 [`BreakPoint`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:264)
- 同时在人类简表 [`syscall_spec.txt`](../spec/syscall_spec.txt:14) 里，`BREAKPOINT` 与 [`Debmess`](../spec/syscall_spec.txt:28) 都已被归并进 `Debug` 组

因此，本详解采用 **`syscall_spec.txt` 的人工归组结果**：把这两个 syscall 一并视为 Debug 分组成员。

综合源码与脚本调用样例，Debug 分组可以概括为：

> **面向日志/调试输出的软调试接口。**

它们不会直接改变 VM 控制流，也不会修改游戏状态核心数据；主要作用是：

- 输出调试信息
- 留下断点/调试标记

---

## 2. 共享实现约定

## 2.1 影响子系统

从 [`syscall_spec.txt`](../spec/syscall_spec.txt:14) 与 [`syscall_spec.txt`](../spec/syscall_spec.txt:28) 可以看到，两者影响子系统都被标注为：

- `logger/debug`

这和源码实现是一致的：

- [`debug_message()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:31) 通过 `log::info!` 输出信息
- [`break_point()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:48) 也只是 `log::info!("Break point")`

因此 Debug 分组的核心副作用不是资源层或渲染层，而是：

> **调试日志输出。**

## 2.2 返回值风格

从实现看：

- [`debug_message()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:31-45) 返回 `Nil`
- [`break_point()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:48-51) 返回 `Nil`

因此这组 syscall 的统一返回风格是：

- **`Nil`**

## 2.3 调度副作用

从 [`syscall_spec.txt`](../spec/syscall_spec.txt:14) 与 [`syscall_spec.txt`](../spec/syscall_spec.txt:28) 可见，这两个 syscall 的 `control_flow` 都是 `-`。

也就是说：

- 不 `yield`
- 不 `wait`
- 不 `sleep`
- 不 `halt`

因此可以高置信度判断：

> Debug 分组是**非调度型 syscall**。

---

## 3. `BREAKPOINT`

### 3.1 参数与返回

- **参数个数**：0：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:27)
- **签名**：`BREAKPOINT()`
- **返回值**：`Nil`：[`break_point()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:48-51)

### 3.2 rfvp 当前实现

rfvp 中，`BREAKPOINT` 的实际 handler 是 [`BreakPoint`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:264)，它调用 [`break_point()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:48)。

而 [`break_point()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:48) 的逻辑只有两步：

1. 输出日志 `"Break point"`
2. 返回 `Nil`

它没有：

- 抛异常
- 中断线程
- 进入宿主调试器
- 修改 `thread_wrapper`
- 设置任何等待/暂停标志

### 3.3 语义判断

对 rfvp 当前实现而言，`BREAKPOINT` 应理解为：

> **调试断点标记型 syscall；当前实现等价于只打一条日志的 no-op。**

这里必须保守说明：

- 从名字看，它在原引擎里**很可能曾被用于调试断点语义**
- 但 rfvp 当前实现并未还原出“真正中断执行”的行为

因此更稳妥的结论是：

> 在语义数据库里，应把 `BREAKPOINT` 记录为“**调试标记 / 断点占位接口**”，而不是“真正会停机的断点”。

### 3.4 可信度说明

由于：

- 自动生成表里把它写成了 `nullsub_2`：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:27)
- 但实际注册又绑定到 [`BreakPoint`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:264)

说明这个 syscall 的“原始定义”与“当前工程实现”之间存在一层人工修补。因此它的最终语义应标注为：

- **rfvp 现状：日志型 no-op**
- **原引擎真实断点行为：仍需实机校验**

---

## 4. `Debmess`

### 4.1 参数与返回

- **参数个数**：2：[`syscall_spec.txt`](../spec/syscall_spec.txt:28)
- **签名**：`Debmess(message, value)`
- **返回值**：`Nil`

### 4.2 实现链条

rfvp 中：

- [`Debmess`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:371) 的 `call()` 实际直接复用 [`DebugMessage`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:254) ：[`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:373-376)
- 真正逻辑在 [`debug_message()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:31)

[`debug_message()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:31-45) 的行为是：

1. 第一个参数 `message` 必须是 `String` 或 `ConstString`：[`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:36-41)
2. 第二个参数 `var` 不做类型限制，直接按 `{:?}` 调试格式打印：[`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:44)
3. 返回 `Nil`

### 4.3 参数语义

因此可以较高置信度归纳：

- `arg0: String | ConstString`
  - 含义：调试消息前缀 / 标题
- `arg1: Variant`
  - 含义：要附带输出的调试值
  - 类型：可为 `Int / String / Nil / BoolLike / Table-like` 等 VM 变体

换言之，`Debmess` 实际更接近：

> **一个“字符串标签 + 任意 VM 值”的调试打印接口。**

### 4.4 具体作用

从实现上看，它会输出类似：

```text
DEBUG => <message>: <value_debug_repr>
```

因此它的本质作用是：

> **把脚本中的某个调试字符串与变量值一并打印到日志。**

### 4.5 非法参数行为

如果第一个参数不是字符串，则会：

1. 输出错误日志 `debug_message: Invalid message type`
2. 返回 `Nil`

这说明 `Debmess` 对第一参数的类型要求是**严格字符串型**，但对第二参数比较宽松。

### 4.6 脚本样例

Sakura 脚本中 `Debmess` 出现频率明显高于 `BREAKPOINT`，而且用途非常一致，几乎全是调试文本输出。

#### 样例 1：字符串 + 任意变量

在 [`f_00037FD2.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037FD2.lua:143) 可以看到，脚本先构造字符串：

- `"[ Prim Count ] Over"`：[`f_00037FD2.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037FD2.lua:143)

随后调用 `Debmess(S0, a0)`：[`f_00037FD2.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037FD2.lua:144-145)

这说明 `Debmess` 非常适合：

> **打印“某个错误标题 + 某个变量值”**。

#### 样例 2：表项文本 + 索引值

在 [`f_00089E1F.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00089E1F.lua:383-385) 中，脚本先从表 `GT[1733]` 中取一段字符串，再交给 `Debmess`。

而在同一函数后续搜索结果中，还能看到：

- `"No BUTTON cmd target"`
- `"No BUTTON cmd TableCount"`

配合 `a1` 或 `G[1711]` 一起输出：[`search result`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00089E1F.lua:384)

这进一步说明：

> `Debmess` 在脚本里主要用于**异常路径、按钮分发表缺项、计数不匹配**之类的问题定位。

#### 样例 3：第二参数可为 `Nil`

例如 [`f_000478BC.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000478BC.lua:182-183) 就把第二参数直接传成 `Nil`。

这与源码完全吻合：第二参数是任意 `Variant`，可以为 `Nil`。

---

## 5. Debug 分组的整体语义

把 `BREAKPOINT` 与 `Debmess` 合起来看，Debug 分组可以总结为：

1. **`BREAKPOINT`**：调试断点占位符 / 断点标记
2. **`Debmess`**：调试消息输出器

二者都不参与正式资源控制，不直接改写显示、音频、输入或线程状态；它们的作用主要是：

> **为脚本作者或逆向者提供可观测的调试输出点。**

---

## 6. 高置信度结论

以下结论比较稳：

- Debug 分组当前应包含 `BREAKPOINT` 与 `Debmess` 两个 syscall。
- 两者返回值都是 `Nil`。
- `BREAKPOINT` 当前 rfvp 实现只会记一条 `Break point` 日志，不会打断执行。
- `Debmess` 的第一参数必须是字符串，第二参数可以是任意 `Variant`。
- `Debmess` 的本质是“字符串标签 + 调试值”输出接口。
- 两者的主要影响子系统都是 `logger/debug`。
- 两者都没有可观察的调度副作用。

---

## 7. 仍需保守处理的点

1. `BREAKPOINT` 在原始 FVP 引擎里是否曾真正触发中断/调试器，目前无法仅凭 rfvp 的日志型实现下结论。
2. `generated.rs` 中把 `BREAKPOINT` 标成 `group=BREAKPOINT, handler=nullsub_2`，说明自动提取结果与运行时人工修补之间存在差异；数据库编写时应优先信任实际注册表与实现。
3. `Debmess` 在原版宿主中输出到哪里（控制台、调试器、文件、消息窗）还需实机补证；rfvp 当前是走日志系统。

---

## 8. 证据来源

- [`README.md`](../manual/syscall-db.md:29-44)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:14)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:28)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:27)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:34)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:545-547)
- [`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:31-45)
- [`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:48-51)
- [`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:264-269)
- [`utils.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:369-376)
- [`f_00037FD2.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037FD2.lua:143-145)
- [`f_00089E1F.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00089E1F.lua:383-385)
- [`f_000478BC.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000478BC.lua:182-183)
- 以及 `Sakura` 中多处 `Debmess` 调用的搜索结果：[`search result`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00089E1F.lua:384)
