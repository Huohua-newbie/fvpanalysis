# LegacyConfig 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:94)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:19) 与 rfvp 参考实现，LegacyConfig 分组当前包含 4 个 syscall：

1. `ConfigDisplay`
2. `ConfigEtc`
3. `ConfigSet`
4. `ConfigSound`

其注册位置可见于 [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:703) 到 [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:706)，而实际实现集中在 [`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:275)。

综合源码与注释，LegacyConfig 分组可以概括为：

> **旧版 FVP / AngelWish 风格配置界面的“分阶段暂存 + 一次性提交”接口。**

它不是直接改全局系统设置，而是：

- 先把参数写入一个兼容配置暂存结构
- 再通过 [`ConfigSet`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:312) 一次性桥接到引擎级配置

---

## 2. 共享实现约定

## 2.1 统一暂存结构

这组 syscall 的核心状态保存在 [`LegacyConfigState`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:47) 中。它包含三块：

- `display: [i32; 9]`：[`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:47)
- `etc: [i32; 3]`：[`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:57)
- `sound: [i32; 5]`：[`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:63)
- 以及 `configured: bool`：[`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:65)

这说明这四个 syscall 的语义是**强耦合的**，必须整体理解：

- [`ConfigDisplay`](#3-configdisplay) 写 `display`
- [`ConfigEtc`](#4-configetc) 写 `etc`
- [`ConfigSound`](#5-configsound) 写 `sound`
- [`ConfigSet`](#6-configset) 读取以上暂存值并真正应用

## 2.2 One-shot 语义

`LegacyConfigState` 里专门有：

- `configured: bool`：[`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:65-67)

而 [`ConfigSet`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:314-318) 会在第一次成功执行后把它置为 `true`，以后再次调用直接返回。

因此这一组有个很重要的共享语义：

> **`ConfigSet()` 是 one-shot 提交器，不是可反复应用的普通 setter。**

## 2.3 当前已确认的直接副作用

rfvp 在 [`ConfigSet()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:302-311) 的注释中已经说明：

- 反向结论来自 AngelWish 旧版逻辑
- 当前已直接确认的运行时副作用，是把 `sound` 槽 9..13 对应的值应用到活动的 BGM/SE 类型音量

而代码中确实做了：

- [`bgm_player_mut().set_type_volume(...)`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:325-327)
- [`se_player_mut().set_type_volume(...)`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:328-330)

因此在本阶段，能高置信度落地的“真正生效语义”主要是：

> **配置里的声音分组音量会被一次性应用到活动音频类型。**

而 display / etc 更多还是“兼容状态暂存”，不宜过度命名其业务含义。

---

## 3. `ConfigDisplay`

### 3.1 参数与返回

- **参数个数**：9：[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:19)
- **返回值**：`Nil`

### 3.2 具体作用

[`config_display()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:275-281) 会遍历 9 个参数，并逐项调用 [`sanitize_config_display_value()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:132-143)，写入 `state.display`。

### 3.3 参数槽位约束

从 [`sanitize_config_display_value()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:132-143) 可知：

- 槽 0、1：`0..=10`
- 槽 2、4：`0..=1`
- 槽 3：`0..3`
- 槽 5..8：`0..=255`
- 非法值统一回落到 `0`

### 3.4 语义判断

结合 [`LegacyConfigState`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:48-56) 的注释，可以保守总结为：

> **向旧版显示配置暂存区写入 9 个分槽值。**

其中较高置信度可描述为：

- 前 2 槽像滑条值
- 中间若干槽像布尔/枚举值
- 后 4 槽像颜色预览或 RGB(A) 类分量

但除范围外，不宜在当前阶段强行命名所有槽位。

---

## 4. `ConfigEtc`

### 4.1 参数与返回

- **参数个数**：3：[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:20)
- **返回值**：`Nil`

### 4.2 具体作用

[`config_etc()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:284-290) 会遍历 3 个参数，并逐项调用 [`sanitize_config_etc_value()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:145-152)，写入 `state.etc`。

### 4.3 参数约束

- 3 个槽都只接受 `0` 或 `1`
- 非法值回落为 `0`

### 4.4 语义判断

结合注释：[`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:57-62)

可以保守总结为：

> **向旧版“杂项配置”暂存区写入 3 个布尔位。**

其中一个槽与 message-skip 菜单标签切换有关，但当前工程未进一步落实完整宿主行为，因此先按布尔配置项处理最稳妥。

---

## 5. `ConfigSound`

### 5.1 参数与返回

- **参数个数**：5：[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:22)
- **返回值**：`Nil`

### 5.2 具体作用

[`config_sound()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:293-299) 会遍历 5 个参数，并逐项调用 [`sanitize_config_sound_value()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:155-160)，写入 `state.sound`。

### 5.3 参数约束

- 每个参数都必须是 `0..=100`
- 非法值回落为 `0`

### 5.4 语义判断

这一条最容易落地：

> **向旧版声音配置暂存区写入 5 个分组音量值。**

由于后续 [`ConfigSet`](#6-configset) 会把它们应用给 `bgm_player` 与 `se_player` 的 type volume，所以这 5 槽基本可以高置信度理解为：

- **5 路旧版声音类别音量配置**

具体对应哪 5 类（BGM / voice / SE / system SE / environment SE 等）仍需结合更多旧版脚本与 UI 线索再细化。

---

## 6. `ConfigSet`

### 6.1 参数与返回

- **参数个数**：0：[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:21)
- **返回值**：`Nil`

### 6.2 具体作用

[`config_set()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:312-333) 的逻辑是：

1. 读取并检查 `LegacyConfigState.configured`
2. 如果已经配置过，则立即返回：[`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:314-317)
3. 否则把 `configured = true`
4. 取出 `sound` 这 5 个槽位
5. 把每个值 clamp 到 `0..100`
6. 转成 `0.0..1.0`
7. 对每个声音类型执行：
   - [`bgm_player_mut().set_type_volume(...)`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:325-327)
   - [`se_player_mut().set_type_volume(...)`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:328-330)

### 6.3 语义判断

因此 `ConfigSet` 的高置信度语义可以写成：

> **把前面暂存在 `ConfigDisplay` / `ConfigEtc` / `ConfigSound` 中的旧版配置一次性提交，并将声音配置真正应用到当前音频类型音量。**

这里要特别强调：

- 它是**提交器/桥接器**，不是简单 getter/setter
- 它是 **one-shot**

### 6.4 当前已直接确认的生效范围

目前源码中真正执行的宿主效果只有：

- `ConfigSound` 五槽 -> BGM/SE 类型音量

而 `display` 与 `etc` 虽然被完整暂存，但在 rfvp 当前这部分实现里没有看到同等明确的宿主副作用调用链。因此数据库里应保守写成：

- **display / etc：已确认暂存，最终 UI/宿主效果仍待补证**
- **sound：已确认提交并生效**

---

## 7. LegacyConfig 分组的整体语义

把这 4 个 syscall 放在一起，可以把它们归纳成一个两阶段旧版配置协议：

1. **分槽写入阶段**
   - [`ConfigDisplay`](#3-configdisplay)
   - [`ConfigEtc`](#4-configetc)
   - [`ConfigSound`](#5-configsound)
2. **一次性提交阶段**
   - [`ConfigSet`](#6-configset)

因此 LegacyConfig 分组的整体语义可概括为：

> **旧版配置界面的 staged config ABI。**

这也解释了为什么这四个接口应该一起理解，而不是分散当作独立配置函数看待。

---

## 8. 高置信度结论

以下结论比较稳：

- LegacyConfig 分组当前包含 `ConfigDisplay`、`ConfigEtc`、`ConfigSet`、`ConfigSound` 4 个 syscall。
- 它们统一作用于 [`LegacyConfigState`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:47-68) 这个兼容配置暂存结构。
- `ConfigDisplay` 写 9 槽显示配置。
- `ConfigEtc` 写 3 槽布尔配置。
- `ConfigSound` 写 5 槽 `0..100` 音量配置。
- `ConfigSet` 是 one-shot 提交器。
- 当前已明确确认的提交副作用，是把 5 路旧版音量槽映射到活动的 BGM/SE 类型音量。

---

## 9. 仍需保守处理的点

1. `ConfigDisplay` 的 9 个槽位虽然范围明确，但除“滑条/布尔/枚举/颜色预览分量”外，尚不能完全逐槽命名。
2. `ConfigEtc` 3 个槽位里，只有部分注释可提示其大概 UI 含义，不能在数据库里过度确定化。
3. `ConfigSet` 在原引擎里可能还会驱动更多 native 配置树、窗口与预览效果；rfvp 当前只落实了声音类型音量的宿主作用。

---

## 10. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:94)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:19)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:20)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:21)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:22)
- [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:703-706)
- [`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:47-68)
- [`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:132-160)
- [`legacy.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:275-333)
- [`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md:179-181)
- [`01_Audio.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/01_Audio.md:443)
