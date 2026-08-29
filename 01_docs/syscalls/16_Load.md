# Load 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:1)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:55) 与 rfvp 参考实现，Load 分组当前只有 1 个 syscall：

- [`Load`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:399)

其注册位置可见于 [`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:61) 与 [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:689)。

综合源码与脚本调用样例，Load 分组可以概括为：

> **存档读入请求接口。**

它不是“立刻把 VM 状态切走”的同步调用，而是一个**延迟到安全点执行的读档请求**：

1. 脚本侧先登记要加载的槽位；
2. 同时启动一次过渡遮罩；
3. 当前 context 进入 `dissolve_wait + should_break`；
4. VM runner 在帧间安全点真正读文件、恢复头部信息，并在存在 RFVS 状态块时恢复 VM/运行时快照。

---

## 2. 共享实现约定

## 2.1 分组地位

在项目规范中，`Load` 被归入“存读档域”：[`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:347)。综述也一致把它和 `SaveWrite` 并列看作存读档核心接口：[`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md:576)。

这说明 `Load` 的职责不是普通资源读取，而是：

> **把宿主层持久化的 save slot 恢复到当前游戏运行态。**

## 2.2 与 `SaveManager` 的关系

`Load` 的实际请求目标是 [`SaveManager`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:851)。其中核心接口有：

- [`request_load()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:851)
- [`take_load_request()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:857)
- [`load_slot_into_current()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:865)
- [`load_slot_into_current_from_bytes()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:876)

这表明 `Load` 不是直接 open/parse 文件，而是先在 `SaveManager` 中挂起一个待处理请求。

## 2.3 安全点执行模型

[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:71) 写得很清楚：

- “Process deferred load requests at a safe point (between VM ticks).”

具体执行流程是：

1. 每个 VM tick 开始时检查 [`take_load_request()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:857)
2. 若有请求，则读出 save 文件字节：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:72-74)
3. 先把 save header 级信息恢复到当前 `SaveManager`：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:76-79)
4. 再尝试解析 RFVS 状态块：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:81-93)
5. 若本 tick 执行了读档，则**本帧不继续推进 context**：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:101-105)

因此 `Load` 的核心语义可以先下一个高置信度结论：

> **它是一个“登记请求 -> 帧间执行 -> 本帧不继续脚本”的延迟式读档 syscall。**

## 2.4 RFVS 状态块与 header-only load

`vm_runner` 还给出了一个很重要的分支：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:81-93)

- 如果存在 RFVS chunk，则应用 [`SaveStateSnapshotV1`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:82-85)
- 如果没有 RFVS chunk，则记一条 “header-only load” 警告：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:87-89)

这意味着：

- **完整 rfvp 存档**：可恢复 VM / 线程 / 运行时快照
- **仅原版头部存档或旧格式存档**：只能恢复标题、场景标题、脚本文本等头部字段

因此 `Load` 在“reference 语义数据库”里应明确分成：

1. **header 级恢复**
2. **RFVS 扩展状态恢复**

---

## 3. `Load`

## 3.1 参数与返回

- **参数个数**：1：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:61)
- **签名**：`Load(slot)`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:329)
- **参数类型**：`Int`
- **合法范围**：`0..=999`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:338)
- **当前 rfvp 实现返回值**：
  - 成功登记请求时返回 `True`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:360)
  - 参数非法时返回 `Nil`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:332-340)

这里要特别指出一个数据库偏差：

- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:55) 把 `Load` 记成 `return_type = Nil`
- 但当前 rfvp 实现其实更接近 `BoolLike|Nil`

因此本轮详解应以**源码实现**为准。

## 3.2 具体作用

[`load()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:329) 的核心逻辑是：

1. 校验槽位参数是否为 `0..=999` 的整数：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:330-340)
2. 向 `SaveManager` 登记 load 请求：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:347)
3. 启动一次 `dissolve2` 过渡遮罩：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:349-352)
4. 请求当前 context 进入 `dissolve_wait`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:354-355)
5. 请求当前 context `should_break()`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:357-358)
6. 返回 `True`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:360)

因此可概括为：

> **登记一个读档请求，并让当前脚本上下文在转场遮罩下尽快让出执行，等待宿主在安全点真正完成恢复。**

## 3.3 参数语义

`slot` 的业务意义很清楚：

- 是 **save slot 编号**
- 当前 rfvp 允许范围是 `0..999`

脚本中常见的槽位并不总是“玩家手选的普通位”，还包括一些内部中转位，例如：

- `900`：[`f_00037AC8.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037AC8.lua:16)
- `901`：[`f_00037849.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037849.lua:22)
- `902`：[`f_00037804.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037804.lua:15)
- `903`：[`f_00037A40.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037A40.lua:16)
- `906`：[`f_000378D9.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_000378D9.lua:14)
- `800`：[`f_0004770E.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_0004770E.lua:84)

因此在语义数据库中，`slot` 应表述为：

> **存档槽编号（既可是真正的玩家槽，也可被脚本当作内部缓存/中转槽使用）。**

## 3.4 读档后的直接恢复内容

从 [`SaveManager::load_slot_into_current_from_bytes()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:876) 可见，header 级恢复至少包括：

- `current_save_slot`：[`save_manager.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:878)
- `current_title`：[`save_manager.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:879)
- `current_scene_title`：[`save_manager.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:880)
- `current_script_content`：[`save_manager.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:881)
- `slots[slot]` 缓存更新：[`save_manager.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:882-884)

因此至少可以高置信度说明：

> **即使没有 RFVS 状态块，`Load` 也会恢复存档头部元数据。**

## 3.5 RFVS 状态恢复语义

在 [`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:81-93) 中：

- 若能解析出 RFVS chunk，则调用 `s.apply(game, &mut self.tm)`：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:82-85)

因此只有在带有 rfvp 扩展状态块时，`Load` 才能恢复：

- VM 线程/上下文
- 更多运行时资源快照

这也是为什么它比“单纯读 save header”更重。

## 3.6 调度副作用

`Load` 是一个典型的**强调度副作用 syscall**：

- `thread_wrapper.dissolve_wait()`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:354-355)
- `thread_wrapper.should_break()`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:357-358)

并且 `vm_runner` 明确规定：

- 一旦本 tick 在安全点执行了 load，请**本帧不再推进 context**：[`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:101-105)

因此本 syscall 的 `control_flow` 更准确地写法应是：

- `yield`
- `dissolve_wait`
- `break_current_context`
- `safe_point_restore`

## 3.7 与 `dissolve2` 的关系

当前 rfvp 在 load 请求登记后，会启动：

- `start_dissolve2_in_out(DISSOLVE2_LOAD_COLOR_ID, DISSOLVE2_LOAD_DURATION_MS)`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:349-352)

常量来自：

- `DISSOLVE2_LOAD_COLOR_ID = 1`
- `DISSOLVE2_LOAD_DURATION_MS = 600`：[`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:10-12)

因此当前实现还附带一个高置信度结论：

> **Load 会主动用一层 600ms 的 dissolve2 过渡去遮蔽状态切换过程。**

## 3.8 脚本样例

在 Sakura 中，`Load` 常见于一组包装函数：

- [`f_00037849.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037849.lua:22)
- [`f_00037804.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037804.lua:15)
- [`f_000378D9.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_000378D9.lua:14)
- [`f_00037A40.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037A40.lua:16)
- [`f_00037AC8.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037AC8.lua:16)
- [`f_00037B07.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037B07.lua:14)
- [`f_0004770E.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_0004770E.lua:84)
- [`f_0009140C.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_0009140C.lua:18)

从这些样例能看出：

- `Load` 并不只面向玩家手动读档界面
- 它也被脚本用于内部“状态页切换 / 中间槽恢复 / 特殊流程回跳”

---

## 4. Load 分组的整体语义

由于本分组当前只有一个 syscall，所以整体语义就是它本身：

> **以安全点方式申请并执行一次存档恢复。**

和很多普通 syscall 不同，它的核心不在“函数体直接干了什么”，而在：

1. 先登记请求；
2. 立即让当前上下文退出；
3. 由宿主主循环/VM runner 在帧间执行真正恢复；
4. 根据存档是否包含 RFVS 状态块，决定恢复深度。

---

## 5. 高置信度结论

以下结论比较稳：

- `Load` 只有 1 个参数：`slot`，必须是 `0..=999` 的整数。
- 当前 rfvp 实现里，合法调用会返回 `True`，非法参数返回 `Nil`。
- `Load` 不直接同步恢复，而是通过 `SaveManager` 挂起一个 deferred load request。
- 真正的文件读取与状态应用发生在 [`VmRunner.tick()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:53) 的安全点。
- 若 save 文件中有 RFVS chunk，则会恢复扩展状态；没有则是 header-only load。
- `Load` 会主动配合一次 dissolve2 过渡，并使当前 context `dissolve_wait + should_break`。

---

## 6. 仍需保守处理的点

1. 目前 `syscall_spec.txt` 仍把 `Load` 记为 `Nil` 返回，但源码实现是成功时 `True`；后续数据库总表应统一修正。
2. `900/901/902/903/906/800` 这类槽位在具体游戏里的业务含义还需逐个函数链继续归纳，不宜在 syscall 层强行命名。
3. “header-only load” 在原引擎中的真实恢复深度，仍需更多原版实机验证；rfvp 当前只恢复它能明确解析的 save header 字段。

---

## 7. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:97)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:55)
- [`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:61)
- [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:689-690)
- [`saveload.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:329-360)
- [`save_manager.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:851-885)
- [`vm_runner.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/vm_runner.rs:71-105)
- [`legacy_save_load_ui.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/legacy_save_load_ui.rs:18-19)
- [`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md:576-578)
- [`Sakura_entry_point功能分析.md`](fvp_analysis/result/hcbtool_test/Sakura_entry_point功能分析.md:321-322)
- [`f_00037849.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037849.lua:22)
- [`f_00037804.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037804.lua:15)
- [`f_000378D9.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_000378D9.lua:14)
- [`f_00037A40.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037A40.lua:16)
- [`f_00037AC8.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037AC8.lua:16)
- [`f_00037B07.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_00037B07.lua:14)
- [`f_0004770E.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_0004770E.lua:84)
- [`f_0009140C.lua`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_0009140C.lua:18)
