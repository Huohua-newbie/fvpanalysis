# Timer 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:110)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7558-7681) 与 rfvp 参考实现，`Timer` 分组当前包含 3 个 syscall：

1. `TimerGet`
2. `TimerSet`
3. `TimerSuspend`

其显式规格与注册位置见 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:159-161) 与 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:663-666)。

`Timer` 分组可以概括为：

> **围绕 16 个独立计时槽的初始化、经过时间读取和全局暂停的一组基础计时接口。**

它与 [`ThreadWait`](fvp_analysis/result/syscall语义数据库/syscall含义详解/27_Thread.md:345) 的差异是：

- `ThreadWait` 直接阻塞当前脚本 Context；
- `TimerSet/TimerGet` 只维护和读取独立计时值，不会自动阻塞脚本；
- 脚本通常通过 `TimerGet` 轮询计时结果，再配合 `ThreadNext` 或其他调度接口让出执行。

---

## 2. Timer 运行模型

### 2.1 16 个 Timer 槽位

[`TimerManager::new()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/timer_manager.rs:56-61) 创建 16 个 [`TimerItem`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/timer_manager.rs:3-42)：

- Timer ID 范围：`0..15`；
- 每个槽位独立保存：
  - `enabled`：是否启用；
  - `elapsed`：累计经过时间；
  - `resolution`：该计时器的换算基准。

### 2.2 帧循环推进

Timer 并不是由 syscall 调用时主动增加，而是由宿主主循环在每帧推进：

```rust
gd.timer_manager.tick(frame_ms)
```

见 [`app.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/app.rs:525-527)。

[`TimerManager::tick()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/timer_manager.rs:99-114) 的行为是：

- 如果全局 `suspend=true`，不推进任何计时器；
- 如果 `delta_ms=0`，不推进；
- 对每个 `enabled` 的 Timer，执行 `elapsed += delta_ms`；
- 使用饱和加法，避免整数溢出回绕。

### 2.3 Timer 不改变 VM 调度

`TimerSet`、`TimerGet` 和 `TimerSuspend` 都：

- 返回 `Nil` 或 `Int`；
- 不设置 Context 的 WAIT/SLEEP/TEXT 状态；
- 不调用 `ThreadWrapper`；
- 不产生 yield/wait/sleep/halt。

因此 Timer 是“被动计时资源”，不是调度等待原语。

---

## 3. `TimerSet`

### 3.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7605)
- **签名**：`TimerSet(id, resolution)`
- **返回值**：`Nil`

### 3.2 入参语义

- `id`
  - 类型：`Int`；
  - 有效范围：`0..15`；
  - 含义：Timer 槽位编号。
- `resolution`
  - 类型：`Int`；
  - 有效范围：`1..=100000`；
  - 含义：计时器的换算分辨率/基准值。

### 3.3 具体作用

[`timer_set()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/timer.rs:8-41) 会：

1. 校验 Timer ID；
2. 校验 resolution 为正整数且不超过 100000；
3. 将该 Timer 的 `elapsed` 重置为 `0`；
4. 写入新的 `resolution`；
5. 将 `enabled` 设置为 `true`。

因此，`TimerSet` 不是单纯修改分辨率，而是一个“重置并启动”操作。

### 3.4 与重复设置的关系

如果对同一个 `id` 再次调用 `TimerSet`：

- 经过时间会被清零；
- resolution 会被替换；
- Timer 会重新启用。

因此脚本可以用它作为重新开始计时的接口。

### 3.5 结论

> `TimerSet` 是 **重置指定 Timer、设置其 resolution 并启动计时的接口**。

---

## 4. `TimerGet`

### 4.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7561)
- **签名**：`TimerGet(id, default_or_scale)`
- **返回值**：数据库记录为 `Int`；非法类型或无效分支当前可能返回 `Nil`。

### 4.2 入参语义

- `id`
  - 类型：`Int`；
  - 有效范围：`0..15`；
  - 含义：要读取的 Timer 槽位。
- `default_or_scale`
  - 类型：`Variant`；
  - 若为 `Int(1..10000)`：作为比例换算基准，同时也是 Timer 未启用时的默认返回值；
  - 若不是该范围的整数：进入原始 elapsed 读取路径。

### 4.3 未提供有效整数时：读取原始 elapsed

当第二参数不是 `Int(1..10000)` 时：

- Timer 已启用：返回 `elapsed`，单位为毫秒；
- Timer 未启用：返回 `Int(0)`。

源码路径见 [`timer_get()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/timer.rs:57-74)。

### 4.4 提供有效整数时：按 resolution 换算

当第二参数为 `default_value = Int(1..10000)` 时：

- Timer 已启用：

```text
result = default_value * elapsed / resolution
```

- Timer 未启用：返回 `default_value`。

因此第二参数既像“目标刻度上限/换算比例”，也兼具“Timer 未启用时的默认值”作用。

例如：

```text
TimerSet(0, 1000)
TimerGet(0, 100)  -> elapsed * 100 / 1000
```

如果 elapsed 已达到 resolution，结果约为 100；如果 elapsed 为 resolution 的一半，结果约为 50。

### 4.5 具体作用

`TimerGet` 适合用于：

- 读取实际经过的毫秒数；
- 将一个 Timer 映射到指定刻度；
- 在脚本中实现百分比进度或阶段进度；
- 与 `ThreadNext` 配合实现非阻塞轮询。

### 4.6 结论

> `TimerGet` 是 **读取 Timer 经过时间或按 resolution 换算进度值的接口**。

需要注意它不是布尔状态查询；返回值通常是整数时间/比例值。

---

## 5. `TimerSuspend`

### 5.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7649)
- **签名**：`TimerSuspend(on)`
- **返回值**：`Nil`

### 5.2 入参语义

- `on`
  - 类型：任意 `Variant`；
  - 通过 [`Variant::canbe_true()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/script/mod.rs:118) 判断。

当前实现使用：

```text
suspend = !on.canbe_true()
```

因此实际效果是：

- `on` 为真：`suspend=false`，恢复 Timer 推进；
- `on` 为假：`suspend=true`，暂停 Timer 推进。

这与函数名 `TimerSuspend(on)` 的直觉参数命名存在反向关系，应以实现为准。

### 5.3 具体作用

[`timer_suspend()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/timer.rs:80-85) 修改的是 [`TimerManager::suspend`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/timer_manager.rs:44-69) 全局标志：

- 不清零任何 Timer；
- 不改变 `enabled`；
- 不改变 `elapsed`；
- 只影响后续 `TimerManager::tick()` 是否累加时间。

### 5.4 例子

```text
TimerSet(0, 1000)
TimerSuspend(nil)    // canbe_true=false -> 全局暂停
TimerGet(0, nil)     // elapsed 保持不变
TimerSuspend(true)   // 恢复所有 Timer 推进
```

### 5.5 结论

> `TimerSuspend` 是 **全局暂停/恢复 TimerManager 时间推进的接口**，不是单个 Timer 的暂停接口。

---

## 6. Timer 与 ThreadWait 的边界

| 特征 | Timer | ThreadWait |
|---|---|---|
| 作用对象 | 16 个独立 Timer 槽 | 当前脚本 Context |
| 是否阻塞脚本 | 否 | 是 |
| 时间推进 | 宿主每帧累加 elapsed | Context 状态进入 WAIT |
| 读取方式 | `TimerGet` 主动查询 | 等待结束后自动恢复 |
| 暂停方式 | `TimerSuspend` 全局暂停 | 不由 Timer 控制 |
| 典型用途 | 进度、计时、轮询 | 脚本时序等待 |

二者可以组合使用：

```text
TimerSet(0, 1000)
while TimerGet(0, 100) < 100 do
    ThreadNext()
end
```

这类模式下 Timer 负责记录时间，ThreadNext 负责避免当前 context 忙循环占满 VM。

---

## 7. Timer 组整体语义

3 条 syscall 构成一个简单的计时器生命周期：

1. `TimerSet(id, resolution)`：清零、设置基准并启用；
2. `TimerGet(id, default_or_scale)`：读取原始 elapsed 或换算值；
3. `TimerSuspend(on)`：暂停/恢复全部 Timer 的帧推进。

因此，Timer 分组的整体语义可以概括为：

> **FVP 的脚本可见计时资源接口，用于提供不直接阻塞 VM 的独立时间基准。**

典型使用流程：

```text
TimerSet(0, 1000)

// 每帧或每轮询周期读取
progress = TimerGet(0, 100)

// 需要暂停所有计时器时
TimerSuspend(nil)

// 恢复所有计时器
TimerSuspend(true)
```

---

## 8. 高置信度结论

以下结论比较稳：

- `Timer` 分组当前共有 3 个 syscall。
- TimerManager 固定维护 16 个计时槽，ID 为 `0..15`。
- `TimerSet` 会清零 elapsed、设置 resolution 并启用 Timer。
- resolution 的有效范围为 `1..=100000`。
- `TimerGet(id, 非有效整数)` 返回启用 Timer 的原始 elapsed 毫秒值；未启用时返回 0。
- `TimerGet(id, default_value)` 在有效整数 `1..=10000` 时返回 `default_value * elapsed / resolution`；未启用时返回 default_value。
- Timer 每帧由宿主 `app.rs` 调用 `TimerManager::tick()` 推进。
- `TimerSuspend` 修改的是全局暂停标志，不是某个 Timer 的 enabled 状态。
- 当前 `TimerSuspend` 的参数语义是“参数为真则恢复、参数为假则暂停”，因为实现使用 `!on.canbe_true()`。
- 3 条 Timer syscall 都不直接改变 VM Context 调度状态。

---

## 9. 仍需保守处理的点

1. `TimerGet` 第二参数在原版命名上可能是默认值、目标分辨率、缩放系数或显示刻度；当前实现同时表现出“换算基准”和“未启用默认返回值”两种作用。
2. `TimerGet` 在启用 Timer 且 resolution 为合法值时使用整数除法，具体边界舍入行为应以整数运算为准。
3. `TimerSuspend` 的参数命名与实现逻辑方向相反，可能是原版 ABI 的特殊约定，也可能是当前实现沿用了反向调用语义；需要更多脚本样例验证。
4. 当前未在已有 HCB 分析文档中找到足够的 TimerGet/TimerSuspend 直接调用样例，因此 Timer 的实际游戏业务用途仍应结合更多作品样本确认。
5. Timer 只记录 elapsed，不提供独立的“完成”状态；脚本若需要阶段完成判断，应自行比较 `TimerGet` 返回值。

---

## 10. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:110-112)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7558-7681)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:159-161)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:663-666)
- [`timer.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/timer.rs:8-133)
- [`timer_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/timer_manager.rs:1-115)
- [`app.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/app.rs:525-527)
- [`27_Thread.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/27_Thread.md:345-390)
- [`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:164-178)
