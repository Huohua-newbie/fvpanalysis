# Lip 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../README.md)、[`syscall_spec.txt`](../syscall_spec.txt) 与 rfvp 参考实现，Lip 分组当前包含 2 个 syscall：

1. `LipAnim`
2. `LipSync`

其注册位置可见于：

- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:59-60)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:692-694)

综合源码与脚本调用样例，Lip 分组可以概括为：

> **口型/唇形动画与语音同步接口。**

它们不是一般的图元动画，而是专门围绕“角色嘴型是否跟语音同步变化”这一业务场景设计的一组接口。

---

## 2. 共享实现约定

## 2.1 作用对象

Lip 分组最终作用在 [`MotionManager`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:51-75) 的唇形子系统上：

- `LipAnim` 负责配置/启动唇形动画参数
- `LipSync` 负责对某个 prim 启用/关闭唇形同步

在实现层，这些信息被传给：

- [`set_lip_motion()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:130-139)
- [`set_lip_sync()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:167-173)

## 2.2 输入约定

这组 syscall 的第一个参数通常都是：

- **prim id**，范围 `1..=4095`

这是因为唇形动画是绑定在具体角色/图元上的。

## 2.3 依赖 BGM 播放状态

Lip 动画并不是孤立运行的。`lip_anim()` 的参数里会指定 BGM 槽，并由 `LipSync` 与当前 BGM 播放状态共同驱动：

- [`lip_anim()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:17-141)
- [`lip_sync()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:144-173)

因此该组更准确地说是：

> **角色嘴型跟语音/音频槽联动的控制接口。**

---

## 3. `LipAnim`

### 3.1 参数与返回

- **参数个数**：8：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:59)
- **签名**：`LipAnim(id, typ, id2, duration, id3, duration2, id4, duration3)`
- **返回值**：`Nil`

### 3.2 参数语义总览

根据 [`lip_anim()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:17-141)：

- `arg0: Int`：prim id，范围 `1..=4095`
- `arg1: Variant`：BGM 槽号或 `Nil`
- `arg2: Int`：第二阶段目标/控制编号，范围 `1..=4095`
- `arg3: Int`：第二阶段持续时间，范围 `1..=300000`
- `arg4: Int`：第三阶段目标/控制编号，范围 `1..=4095`
- `arg5: Int`：第三阶段持续时间，范围 `1..=300000`
- `arg6: Int|Nil`：第四阶段目标/控制编号，范围 `0..=4095`
- `arg7: Int`：第四阶段持续时间，范围 `1..=300000`

### 3.3 具体作用

[`lip_anim()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:17-141) 的逻辑较长，但本质可以分两种情况：

#### 情况 A：`typ == Nil`

- 视为停止该 prim 的口型动画：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:40-53)
- 调用 `stop_lip_motion(prim_id)`

#### 情况 B：`typ` 是 `0..=3` 的整数

- 视为指定一个 BGM 槽：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:41-48)
- 校验后把多阶段口型配置存入 [`set_lip_motion()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:129-139)

### 3.4 语义判断

因此可概括为：

> **给指定 prim 注册一套唇形动画参数，并绑定到某个 BGM 槽；若 `typ` 为 Nil，则停止唇形动画。**

### 3.5 参数角色

从实现看，`id2/id3/id4/duration/duration2/duration3` 这些参数更像是口型动画内部的多阶段配置，而不是普通坐标或颜色参数。

因此在当前阶段，建议数据库里把它们保守记成：

- **多阶段唇形动画控制参数**

而不要强行命名成具体的“嘴巴开合帧”之类术语，除非后续再结合更多实机动画行为做专项确认。

---

## 4. `LipSync`

### 4.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:60)
- **签名**：`LipSync(id, sync)`
- **返回值**：`Nil`

### 4.2 参数语义

根据 [`lip_sync()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:144-173)：

- `arg0: Int`：prim id，范围 `1..=4095`
- `arg1: Variant`：同步开关
  - `Int(0)` -> false
  - `Int(nonzero)` -> true
  - `True` -> true
  - `Nil` -> false

### 4.3 具体作用

[`lip_sync()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:144-173) 的逻辑是：

1. 解析 prim id
2. 将 `sync` 解释成布尔开关
3. 若关闭同步，则调用 [`update_lip_motions(-1, false, &bgm_playing_slots)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:167-171)
4. 调 [`set_lip_sync(prim_id, enable)`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:172)

### 4.4 语义判断

因此它的高置信度语义是：

> **切换某个 prim 的口型与音频播放之间的同步开关。**

### 4.5 关闭同步的特殊行为

实现里明确说明：

- 当关闭同步时，原引擎会把动画重置到第一帧：[`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:167-171)

这说明 `LipSync` 不只是一个“开/关标志”，而是会影响当前口型动画状态机的。

### 4.6 脚本样例

Sakura 的已检索结果中，LipAnim/LipSync 直接调用样例较少，但从代码路径可以明确它们用于：

- 角色说话时的口型同步
- 关闭后恢复普通静态表情/首帧状态

---

## 5. Lip 分组的整体语义

把 [`LipAnim`](#3-lipanim) 与 [`LipSync`](#4-lipsync) 放在一起看，Lip 分组可以概括为：

> **角色唇形/口型动画的注册与同步控制接口。**

它和普通 Motion* 的区别在于：

- 它的核心对象是**嘴型与语音的联动**
- 它依赖 BGM 播放槽，参与对话演出节奏

---

## 6. 高置信度结论

以下结论比较稳：

- Lip 分组当前包含 `LipAnim` 与 `LipSync` 两个 syscall。
- 两者都绑定到 `prim id (1..4095)`。
- `LipAnim` 在 `typ == Nil` 时表现为停止唇形动画；在 `typ` 为 `0..=3` 时绑定 BGM 槽并注册多阶段口型配置。
- `LipSync` 是口型与音频的同步开关。
- 关闭 `LipSync` 时会触发口型动画重置逻辑。

---

## 7. 仍需保守处理的点

1. `LipAnim` 的多阶段参数 `id2/id3/id4/duration*` 在源码里属于动画配置，但具体动画阶段业务命名仍需继续通过实机行为补证。
2. 已检索到的 Sakura 脚本里，LipAnim/LipSync 直接调用样本较少，因此当前更依赖 rfvp 实现和注释归纳。
3. 不同游戏对 lip 动画阶段数量与参数组合可能并不完全一致，后续应按作品继续校验。

---

## 8. 证据来源

- [`README.md`](../README.md:29-44, 94-96)
- [`syscall_spec.txt`](../syscall_spec.txt:53-54)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:59-60)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:692-694)
- [`other_anm.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:17-173)
- [`motion_manager/mod.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:134-135)
- [`FVP引擎文献综述.md`](../FVP引擎文献综述.md:177-180, 574-576)
- [`f_00049D4E.lua`](../../hcbtool_ir/Sakura/f_00049D4E.lua:1-53)
- [`f_00049D4E.lua`](../../hcbtool_ir/Sakura/f_00049D4E.lua:5-53)
