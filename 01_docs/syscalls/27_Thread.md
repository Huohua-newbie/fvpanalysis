# Thread 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:107)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7325-7555) 与 rfvp 参考实现，`Thread` 分组当前包含 6 个 syscall：

1. `ThreadExit`
2. `ThreadNext`
3. `ThreadRaise`
4. `ThreadSleep`
5. `ThreadStart`
6. `ThreadWait`

其显式规格与注册位置见 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:153-158) 与 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:648-659)。

综合项目规范、VM 实现和脚本样例，`Thread` 分组可以概括为：

> **围绕 FVP 脚本 Context 的启动、退出、主动让出、定时等待和休眠/唤醒的一组协作式调度接口。**

这里的“thread”不是操作系统线程。项目规范明确将 FVP 的线程统一理解为：

> **脚本上下文 / 协程（Context）**，不是 OS thread。

见 [`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:164-178)。

---

## 2. FVP Thread 的运行模型

### 2.1 Context 槽位

[`ThreadManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:8-39) 初始化 32 个 Context：

- Context ID 范围：`0..31`；
- `0` 通常是主脚本 context；
- `1..31` 可由脚本启动并行 context；
- 每个 Context 保存自己的 PC、栈、返回值、状态位和等待时间。

### 2.2 状态位

[`Context::ThreadState`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/script/context.rs:53-63) 定义：

| 状态 | 数值 | 含义 |
|---|---:|---|
| `CONTEXT_STATUS_NONE` | 0 | 空闲/未运行 |
| `CONTEXT_STATUS_RUNNING` | 1 | 可执行 |
| `CONTEXT_STATUS_WAIT` | 2 | 定时等待 |
| `CONTEXT_STATUS_SLEEP` | 4 | 休眠/被动阻塞 |
| `CONTEXT_STATUS_TEXT` | 8 | 文本显示等待 |
| `CONTEXT_STATUS_DISSOLVE_WAIT` | 16 | 转场等待 |

一个 context 可以同时具有多个非互斥状态位，但 `WAIT` / `SLEEP` / `TEXT` 等阻塞状态通常会清除 `RUNNING` 位。

### 2.3 syscall 请求不是立即直接切换

Thread syscall 首先向 [`ThreadWrapper`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_wrapper.rs:26-79) 写入 `ThreadRequest`：

```text
ThreadStart -> Start(id, addr)
ThreadWait  -> Wait(time)
ThreadSleep -> Sleep(time)
ThreadRaise -> Raise(time)
ThreadNext  -> Next()
ThreadExit  -> Exit(id?)
```

之后 VM runner 在安全的调度阶段取出请求并交给 [`ThreadManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:106-180) 处理：[`vm_runner.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:267-321)。

因此，Thread syscall 的核心不是返回值，而是：

1. 写入调度请求；
2. 标记当前 context 或目标 context 的状态；
3. 在 VM runner 的帧边界让出执行；
4. 后续由定时器、输入、文本系统或其他请求恢复。

---

## 3. `ThreadStart`

### 3.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7477)
- **签名**：`ThreadStart(thread_id, addr)`
- **返回值**：`Nil`
- **控制流**：启动/替换一个脚本 Context，但当前调用者不必因此阻塞。

### 3.2 入参语义

- `thread_id`
  - 类型：`Int`；
  - 有效范围：`0..31`；
  - 含义：目标脚本 Context 槽位。
- `addr`
  - 类型：`Int`；
  - 含义：HCB 代码区中的函数/入口地址；
  - 在 HCB 语义上不是普通业务整数，而是脚本执行地址。

项目规范明确指出，常见字节码模式是：

```text
push_i32 <function_addr>
syscall ThreadStart
```

这个立即数需要参与地址重定位：[`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:297-302)。

### 3.3 具体作用

[`thread_start()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/thread.rs:64-90) 会：

1. 校验 `thread_id` 和地址类型；
2. 校验 `thread_id` 在 `0..31`；
3. 向 `ThreadWrapper` 写入 `Start(id, addr)` 请求；
4. VM runner 处理请求时调用 `ThreadManager::thread_start()`；
5. 创建新的 `Context::new(addr, id)`；
6. 将目标状态设置为 `CONTEXT_STATUS_RUNNING`。

如果 `id == 0`，[`ThreadManager::thread_start()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:106-121) 会重置全部 Context，然后重新启动主 context。这说明 `ThreadStart(0, addr)` 具有主脚本重启/重建语义，不能简单当作启动普通子线程。

### 3.4 与 HCB 重定位的关系

`ThreadStart` 的第二参数是 FVP 反编译、重建和场景插入时的重要特殊地址：

- 它需要和 `call/jmp/jz` 一样参与代码移动后的地址修正；
- FVP Studio 和 HCB 可逆转换工具都把 `push_i32 + syscall ThreadStart` 作为地址指针模式识别。

见 [`hcb可逆转换/README.md`](fvp_analysis/result/hcb可逆转换/README.md:119-127) 与 [`FVP Studio 在现有 HCB 上插入新场景/字节码的逻辑分析.md`](fvp_analysis/result/FVP Studio 在现有 HCB 上插入新场景/字节码的逻辑分析.md:325-332)。

### 3.5 结论

> `ThreadStart` 是 **在指定 Context 槽位启动/替换一段 HCB 脚本入口的接口**。

---

## 4. `ThreadExit`

### 4.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7328)
- **签名**：`ThreadExit(thread_id_or_nil)`
- **返回值**：`Nil`
- **控制流**：请求目标 Context 退出。

### 4.2 入参语义

- `thread_id_or_nil`
  - 类型：`Int | Nil`；
  - `Int(0..31)`：退出指定 Context；
  - `Nil`：退出当前 Context；
  - 其他整数：无效，返回 `Nil`，不登记退出请求。

数据库已明确记录：

> `thread id; nil means current`

### 4.3 具体作用

[`thread_exit()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/thread.rs:8-24) 将目标 ID 包装为 `Option<u32>`，再写入 `ThreadWrapper::thread_exit()`。

VM runner 处理 `Exit` 请求后调用 [`ThreadManager::thread_exit()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:167-180)：

- `Some(id)`：退出指定 Context；
- `None`：退出当前 Context；
- 退出后将 context 状态设为 `CONTEXT_STATUS_NONE`，并标记退出/中断状态。

如果目标 ID 为 `0`，当前实现会重置全部 Context：

- 主 context 退出通常意味着整个脚本推进停止；
- 其他 context 也会被清空。

### 4.4 脚本样例

现有 HCB 研究中，常见收尾结构是：

```lua
ThreadNext()
ThreadExit(0)
```

例如 [`f_00037BF7逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00037BF7逐条反汇编对照.md:267-271) 与 [`f_00010271逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00010271逐条反汇编对照.md:354-388)。

### 4.5 结论

> `ThreadExit` 是 **终止指定或当前脚本 Context 的接口**；`Nil` 参数表示当前 Context。

---

## 5. `ThreadNext`

### 5.1 参数与返回

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7367)
- **签名**：`ThreadNext()`
- **返回值**：`Nil`
- **控制流**：yield 当前 Context，让出当前调度轮次。

### 5.2 具体作用

[`thread_next()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/thread.rs:26-30) 写入 `ThreadRequest::Next`。

VM runner 处理后调用 [`ThreadManager::thread_next()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:163-165)，把当前 Context 的 `should_break` 设置为 `true`，并让当前帧执行循环在边界处停止继续 dispatch：[`vm_runner.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:287-321)。

它不会：

- 设置 WAIT 状态；
- 设置 SLEEP 状态；
- 等待固定毫秒数；
- 退出当前 Context。

它只是让当前 Context 结束本次调度机会，下一轮仍可继续运行。

### 5.3 实际用途

`ThreadNext` 常用于：

- 动画轮询中的“每帧让出”；
- 文本/图像刷新循环；
- 等待 `Motion*Test` 条件变化；
- 避免脚本在单帧内忙循环阻塞宿主。

现有研究明确把 [`f_0003769F()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_0003769F.lua:1) 识别为 `ThreadNext` 包装函数，并将其解释为“让出一帧”：[`f_00010271逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00010271逐条反汇编对照.md:219-230)。

### 5.4 结论

> `ThreadNext` 是 **协作式调度中的单轮次让出接口**，相当于“执行到这里，下一次调度再继续”。

---

## 6. `ThreadWait`

### 6.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7523)
- **签名**：`ThreadWait(duration_ms)`
- **返回值**：`Nil`
- **控制流**：yield + WAIT。

### 6.2 入参语义

- `duration_ms`
  - 类型：`Int`；
  - 有效范围：当前实现要求 `>=0`；
  - 含义：定时等待时长，单位为毫秒；
  - 负数：非法，返回 `Nil`，不进入等待。

### 6.3 具体作用

[`thread_wait()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/thread.rs:92-110) 写入 `ThreadRequest::Wait(time)`。

VM runner 处理后调用 [`ThreadManager::thread_wait()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:123-131)：

1. 设置当前 Context 的 `should_break`；
2. 写入 `waiting_time`；
3. 增加 `CONTEXT_STATUS_WAIT`；
4. 清除 `CONTEXT_STATUS_RUNNING`。

在后续帧，VM runner 递减等待时间；时间到期后：

- 清除 WAIT；
- 恢复 RUNNING；
- 允许 Context 继续 dispatch。

相关恢复逻辑见 [`vm_runner.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:197-211)。

### 6.4 与 `ThreadNext` 的区别

| 接口 | 阻塞状态 | 时间语义 |
|---|---|---|
| `ThreadNext()` | 无固定阻塞状态 | 只让出当前轮次 |
| `ThreadWait(ms)` | `WAIT` | 等待指定毫秒后自动恢复 |
| `ThreadSleep(token)` | `SLEEP` | 休眠，等待计时或 Raise 机制 |

### 6.5 结论

> `ThreadWait` 是 **按毫秒计时、到期自动恢复的协作式等待接口**。

---

## 7. `ThreadSleep`

### 7.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7438)
- **签名**：`ThreadSleep(token_or_duration)`
- **返回值**：`Nil`
- **控制流**：yield + SLEEP。

### 7.2 入参语义

- 参数类型：`Int`；
- 当前 syscall 层直接转换为 `u32`；
- 负数在 Rust 转换后会变成很大的无符号值，因此脚本层应避免传入负数；
- 数据库将它保守写为 `sleep token/duration`，因为当前实现同时保留时间字段和 Raise 机制。

### 7.3 具体作用

[`thread_sleep()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/thread.rs:48-62) 写入 `ThreadRequest::Sleep(time)`。

VM runner 处理后调用 [`ThreadManager::thread_sleep()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:142-150)：

1. 设置当前 Context 的 `should_break`；
2. 写入 `sleeping_time`；
3. 设置 `CONTEXT_STATUS_SLEEP`；
4. 清除 `CONTEXT_STATUS_RUNNING`。

VM runner 还会像处理 WAIT 一样递减 `sleeping_time`，时间到期后恢复 RUNNING：[`vm_runner.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:213-223)。

### 7.4 与 `ThreadWait` 的区别

从当前实现的状态位设计看：

- WAIT 更像标准的“等待指定毫秒”；
- SLEEP 是较旧的休眠/阻塞机制；
- `ThreadRaise` 试图通过 token 匹配来恢复 SLEEP context。

但当前实现存在一个重要不一致：

- `ThreadSleep` 写入的是 `sleeping_time`；
- `ThreadRaise` 的实现却检查 `get_waiting_time() == time`：[`thread_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:152-160)。

因此 `ThreadRaise` 与 `ThreadSleep` 的 token 唤醒路径在当前 rfvp 中可能无法按预期匹配。本文保留源码实际行为，不将其错误描述为已完全验证的可靠唤醒机制。

### 7.5 结论

> `ThreadSleep` 是 **把当前 Context 放入 SLEEP 状态的休眠接口**；其与 `ThreadRaise` 的精确配合关系在当前实现中仍存在待修正问题。

---

## 8. `ThreadRaise`

### 8.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7400)
- **签名**：`ThreadRaise(token)`
- **返回值**：`Nil`
- **控制流**：数据库标记为无直接调度副作用，但其目的在于恢复符合条件的休眠 Context。

### 8.2 入参语义

- `token`
  - 类型：`Int`；
  - 当前 syscall 层直接转为 `u32`；
  - 含义：用于匹配待唤醒 Context 的 token/时间值。

### 8.3 具体作用

[`thread_raise()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/thread.rs:32-46) 写入 `ThreadRequest::Raise(time)`。

VM runner 处理后调用 [`ThreadManager::thread_raise()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:152-160)：

- 遍历全部 Context；
- 找出具有 `SLEEP` 状态的 Context；
- 如果其等待时间等于传入 token，则清除 SLEEP 并恢复 RUNNING。

### 8.4 当前实现的限制

源码注释明确写着：

> `both sleep and raise are never used`

此外，当前字段匹配存在疑点：

- `ThreadSleep` 设置 `sleeping_time`；
- `ThreadRaise` 检查 `waiting_time`。

因此，当前可以确认的是“接口设计意图和请求处理逻辑”，但不能确认当前 rfvp 中实际存在稳定可用的 `Sleep -> Raise` 配对。

### 8.5 结论

> `ThreadRaise` 是 **按 token 尝试唤醒休眠 Context 的兼容调度接口**；当前 reference 表明它属于旧/少用机制，且与 `ThreadSleep` 的字段匹配存在待修正问题。

---

## 9. Thread 组整体语义

6 条 syscall 可以分为以下职责：

1. **Context 生命周期**
   - `ThreadStart`
   - `ThreadExit`
2. **协作式让出**
   - `ThreadNext`
3. **定时阻塞**
   - `ThreadWait`
4. **休眠与唤醒兼容机制**
   - `ThreadSleep`
   - `ThreadRaise`

典型并行演出流程：

```text
push function_addr
ThreadStart(thread_id, function_addr)
```

典型动画轮询流程：

```text
MotionMove(...)
while MotionMoveTest(prim_id) do
    ThreadNext()
end
```

典型时序流程：

```text
ThreadWait(duration_ms)
```

典型收尾流程：

```text
ThreadNext()
ThreadExit(nil)       // 退出当前 Context
```

因此，`Thread` 分组的整体语义可以概括为：

> **FVP VM 的协作式 Context 调度原语：启动并行脚本、主动让出当前轮次、定时等待、休眠/唤醒以及终止脚本 Context。**

---

## 10. 高置信度结论

以下结论比较稳：

- `Thread` 分组当前共有 6 个 syscall。
- FVP 的 Thread 实际是 32 个脚本 Context 槽位，不是 OS 线程。
- `ThreadStart(id, addr)` 在 `0..31` 槽位启动/替换 Context，第二参数是 HCB 代码地址。
- `ThreadStart(0, addr)` 会重置并重新启动主 Context 相关状态。
- `ThreadExit(nil)` 退出当前 Context，传整数则请求退出指定 Context。
- `ThreadNext()` 只设置当前 Context 的 break，让出当前调度轮次。
- `ThreadWait(ms)` 设置 WAIT 状态并在计时结束后自动恢复。
- `ThreadSleep(token_or_duration)` 设置 SLEEP 状态，并由宿主循环进行睡眠时间推进。
- `ThreadRaise(token)` 设计目标是按 token 唤醒休眠 Context。
- 所有 Thread syscall 都返回 `Nil`。
- Thread syscall 的主要可观察结果在 Context 状态和 VM 调度，而不是返回值。

---

## 11. 仍需保守处理的点

1. `ThreadRaise` 的 token 是纯粹的唤醒标识、时间值还是旧版内部句柄，当前 reference 没有给出稳定命名。
2. `ThreadSleep` 与 `ThreadRaise` 在当前实现中存在 `sleeping_time / waiting_time` 字段不匹配，可能是遗留 bug 或未使用的旧机制。
3. `ThreadWait(0)` 的具体调度表现取决于 VM runner 如何处理零时长 WAIT，不能简单等同于 `ThreadNext`。
4. `ThreadExit(0)` 会影响全部 Context 的重置路径，实际脚本是否把它作为“退出主线程”还是“结束整个脚本系统”，需结合调用方继续确认。
5. `ThreadStart` 对已有 Context 槽位的替换语义在原版不同版本中可能存在差异；当前 rfvp 采用重新创建 Context 的方式。
6. Thread syscall 的请求先进入 `ThreadWrapper` 队列，再由 VM runner 消费；直接分析 syscall 函数体而忽略请求队列会低估其真实调度副作用。

---

## 12. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:107-109)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7325-7555)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:153-158)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:648-659)
- [`thread.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/thread.rs:1-175)
- [`thread_wrapper.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_wrapper.rs:1-80)
- [`thread_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/thread_manager.rs:8-180)
- [`context.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/script/context.rs:33-79)
- [`vm_runner.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:129-236)
- [`vm_runner.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:267-321)
- [`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:164-178,297-302)
- [`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md:203-207,595-605)
- [`指令与指令块功能对照表.md`](fvp_analysis/result/hcb可逆转换/指令与指令块功能对照表.md:376-425)
- [`f_00010271逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00010271逐条反汇编对照.md:219-230,354-388)
- [`f_00037BF7逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00037BF7逐条反汇编对照.md:267-271)
- [`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:614-681)
