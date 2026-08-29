# Sound 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:104)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5535-5947) 与 rfvp 参考实现，`Sound` 分组当前包含 9 个 syscall：

1. `SoundLoad`
2. `SoundMasterVol`
3. `SoundPan`
4. `SoundPlay`
5. `SoundSilentOn`
6. `SoundStop`
7. `SoundType`
8. `SoundTypeVol`
9. `SoundVol`

其中：

- `SoundLoad`、`SoundMasterVol`、`SoundPlay`、`SoundSilentOn`、`SoundStop`、`SoundType`、`SoundTypeVol`、`SoundVol` 在 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:121-128) 中有显式规格，并在 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:604-611) 中注册；
- `SoundPan` 属于旧版/兼容接口，通过 [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:470-483,605) 注册，但当前仍有明确的声像设置实现。

`Sound` 分组的整体语义可以概括为：

> **围绕 SE/音效资源的加载、播放、停止、静音、声道音量、音效类型音量、类型绑定和主音量控制的一组音频接口。**

---

## 2. Sound 与 Audio 的边界

### 2.1 `Sound*` 操作 SE 播放器

当前 `Sound*` 实现主要通过 [`GameData::se_player_mut()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:1) 访问 SE 播放器：

- `SoundLoad`：向 `se_player` 加载音效资源；
- `SoundPlay`：在 SE 通道播放；
- `SoundStop`：停止 SE 通道；
- `SoundSilentOn`：静音 SE 通道；
- `SoundVol`：设置 SE 通道音量；
- `SoundType`：设置 SE 通道所属音效类型；
- `SoundTypeVol`：设置某个音效类型的整体音量。

`SoundMasterVol` 则通过 [`audio_manager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:308-323) 设置宿主音频总音量。

### 2.2 `Audio*` 不属于本次范围

`AudioLoad`、`AudioPlay`、`AudioStop`、`AudioVol` 等条目属于 `Audio` 分组，主要作用于 BGM/音频播放器和 `0..3` 的音频通道；本文件不重复分析。

因此，本组的关键边界是：

| 分组 | 主要后端 | 典型用途 | 通道范围 |
|---|---|---|---:|
| `Sound` | `se_player` | SE、语音、音效 | 通常 `0..255` |
| `Audio` | `bgm_player` | BGM、背景音频 | `0..3` |

### 2.3 `SoundPan` 的兼容性质

`SoundPan` 没有进入现代 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:1) 的 Sound 显式规格段，而是通过 legacy wrapper 注册。不过其实现并非 no-op：

- 接受声道 `0..31`；
- 接受声像值 `-100..100`；
- 转换为 `0..1`；
- 调用 SE 播放器的 `set_panning()`。

因此它应被描述为：

> **带有旧版 ABI 兼容性质的 SE 声像设置接口。**

---

## 3. 共享实现约定

### 3.1 Sound 通道范围并不完全统一

当前实现存在两种通道范围：

- `SoundLoad`、`SoundPlay`、`SoundSilentOn`、`SoundStop`、`SoundType`、`SoundVol`：`0..=255`；
- `SoundPan`：`0..=31`。

这可能反映不同 FVP 版本或不同底层接口的 ABI 差异。不能把所有 Sound 接口都机械地统一成一个通道范围。

### 3.2 音量统一使用 0..100 的脚本百分比

当前实现中的音量参数都要求：

- `Int`；
- `0..=100`；
- 内部换算为 `volume / 100.0`。

因此：

- `0`：静音级别；
- `100`：100% 音量；
- `50`：约 50% 音量。

### 3.3 淡入淡出单位为毫秒

`SoundPlay` 的 `fadein`、`SoundStop` 的 `fadeout`、`SoundVol` 的 `crossfade` 都按毫秒解释：

- 有效范围：`0..=300000`；
- 无效类型或越界值在当前实现中回退为 `0`，即立即切换或无过渡。

底层使用 [`kira::Tween`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:345-353,412-420,567-575) 表达过渡时间。

### 3.4 音效类型范围为 0..9

`SoundType` 与 `SoundTypeVol` 都把音效类型限制为：

- `0..=9`；
- 共 10 个类型槽位。

当前 reference 没有给出这 10 个数字对应的固定中文业务名称，因此本文只称为“音效类型槽位”。具体作品可能把它们映射为语音、系统音、环境音等不同类别，需要结合游戏配置或实机验证。

### 3.5 返回值与调度

Sound 组 9 条 syscall 当前全部返回 `Nil`，且数据库统一标记为：

- 不 yield；
- 不 wait；
- 不 sleep；
- 不进入 text wait/dissolve wait；
- 不启动或退出 VM context。

它们是即时音频控制接口，音频播放本身由宿主音频后端异步推进，但 syscall 不会因此让脚本上下文主动等待。

---

## 4. `SoundLoad`

### 4.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5538)
- **签名**：`SoundLoad(channel, path)`
- **返回值**：`Nil`

### 4.2 入参语义

- `channel`
  - 类型：`Int`；
  - 有效范围：`0..=255`；
  - 含义：SE 播放器中的音效通道。
- `path`
  - 类型：`String | ConstString | Nil`；
  - `String/ConstString`：从 VFS 加载指定音效；
  - `Nil`：停止并卸载/清空该通道当前音效；
  - 其他类型：无效，返回 `Nil`。

### 4.3 具体作用

[`sound_load()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:272-306) 的流程是：

1. 校验通道范围；
2. 若为路径字符串，调用 [`vfs_load_file()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:287-292) 读取音频字节；
3. 调用 `se_player.load_named(channel, path, data)` 将音效绑定到通道；
4. 若 `path == Nil`，调用 SE 播放器的 `stop()` 清理通道。

当前函数只负责“装载/卸载”，不会自动开始播放；开始播放由 [`SoundPlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5668) 完成。

### 4.4 结论

> `SoundLoad` 是 **SE 音效通道的资源加载与卸载接口**。

常见工作流是：

```text
SoundLoad(channel, path)
SoundPlay(channel, looped, fadein)
```

---

## 5. `SoundPlay`

### 5.1 参数与返回

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5671)
- **签名**：`SoundPlay(channel, looped, fadein)`
- **返回值**：`Nil`

### 5.2 入参语义

- `channel`
  - 类型：`Int`；
  - 有效范围：`0..=255`；
  - 含义：要播放的 SE 通道。
- `looped`
  - 类型：任意 `Variant`；
  - 通过 [`Variant::canbe_true()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/script/mod.rs:118) 判断；
  - 真值表示循环播放，假值表示非循环播放。
- `fadein`
  - 类型：`Int | Nil`；
  - 有效范围：`0..=300000` 毫秒；
  - 无效或缺省时按 `0` 处理。

### 5.3 具体作用

[`sound_play()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:326-365) 会：

- 将 `looped` 转换为宿主循环标志；
- 将 `fadein` 转换为毫秒级 tween；
- 调用 `se_player.play(channel, looped, 1.0, 0.5, fade_in)`。

当前实现传给底层的初始音量为 `1.0`，另一个参数固定为 `0.5`；该固定参数在当前 syscall 层没有进一步命名，应视为音频后端内部播放参数。

### 5.4 结论

> `SoundPlay` 是 **在指定 SE 通道开始播放已加载音效的接口，支持循环和淡入**。

---

## 6. `SoundStop`

### 6.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5763)
- **签名**：`SoundStop(channel, fadeout)`
- **返回值**：`Nil`

### 6.2 入参语义

- `channel`
  - 类型：`Int`；
  - 有效范围：`0..=255`；
  - 含义：要停止的 SE 通道。
- `fadeout`
  - 类型：`Int | Nil`；
  - 有效范围：`0..=300000` 毫秒；
  - 无效或缺省时按 `0` 处理。

### 6.3 具体作用

[`sound_stop()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:393-425) 构造 fade-out tween，并调用 `se_player.stop(channel, fade_out)`。

- `fadeout = 0`：立即停止；
- `fadeout > 0`：在指定毫秒内淡出停止。

### 6.4 结论

> `SoundStop` 是 **停止指定 SE 通道并可选择淡出的接口**。

它不影响其他通道，也不改变该通道所属的音效类型配置。

---

## 7. `SoundSilentOn`

### 7.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5723)
- **签名**：`SoundSilentOn(channel)`
- **返回值**：`Nil`

### 7.2 入参语义

- `channel`
  - 类型：`Int`；
  - 有效范围：`0..=255`；
  - 含义：要静音的 SE 通道。

### 7.3 具体作用

[`sound_silent_on()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:367-385) 调用 `se_player.silent_on(channel, Tween::default())`。

源码注释明确说明，这个操作启用后会保持通道静音：

> **它是静音状态设置，而不是停止播放。**

也就是说，`SoundSilentOn` 与 `SoundStop` 的区别是：

- `SoundStop` 结束当前通道播放；
- `SoundSilentOn` 保留播放状态，但把通道输出静音。

当前 reference 没有对应的 `SoundSilentOff` syscall；如何解除静音需要结合音频播放器内部 API、重载/重启通道或原版脚本继续验证。

### 7.4 结论

> `SoundSilentOn` 是 **使指定 SE 通道进入持续静音状态的接口**。

---

## 8. `SoundMasterVol`

### 8.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5584)
- **签名**：`SoundMasterVol(volume)`
- **返回值**：`Nil`

### 8.2 入参语义

- `volume`
  - 类型：`Int`；
  - 有效范围：`0..=100`；
  - 含义：宿主音频系统的总音量百分比。

### 8.3 具体作用

[`sound_master_vol()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:308-323) 将 `volume` 除以 `100.0` 后调用 [`AudioManager::master_vol()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/audio.rs:1)。

该接口作用于音频系统总输出级别，和 `SoundVol(channel, ...)` 的单通道音量不同，也和 `SoundTypeVol(type, ...)` 的类型组音量不同。

### 8.4 结论

> `SoundMasterVol` 是 **设置宿主音频总音量的接口**。

当前实现没有淡入淡出参数，属于立即更新。

---

## 9. `SoundVol`

### 9.1 参数与返回

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5901)
- **签名**：`SoundVol(channel, volume, crossfade)`
- **返回值**：`Nil`

### 9.2 入参语义

- `channel`
  - 类型：`Int`；
  - 有效范围：`0..=255`；
  - 含义：SE 通道。
- `volume`
  - 类型：`Int`；
  - 有效范围：`0..=100`；
  - 含义：目标通道音量百分比。
- `crossfade`
  - 类型：`Int | Nil`；
  - 有效范围：`0..=300000` 毫秒；
  - 含义：音量变化的过渡时间；无效或缺省时按 `0` 处理。

### 9.3 具体作用

[`sound_volume()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:533-581) 将音量换算为 `0.0..1.0`，构造 tween 后调用 `se_player.set_volume(channel, volume, cross_fade)`。

- `crossfade=0`：立即设置；
- `crossfade>0`：在指定时间内平滑过渡。

### 9.4 与 `SoundMasterVol` 的区别

| 接口 | 作用范围 |
|---|---|
| `SoundVol` | 单个 SE 通道 |
| `SoundTypeVol` | 一个音效类型的全部通道/声音 |
| `SoundMasterVol` | 整个宿主音频输出 |

### 9.5 结论

> `SoundVol` 是 **设置指定 SE 通道音量并支持交叉淡化的接口**。

---

## 10. `SoundType`

### 10.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5809)
- **签名**：`SoundType(channel, sound_type)`
- **返回值**：`Nil`

### 10.2 入参语义

- `channel`
  - 类型：`Int`；
  - 有效范围：`0..=255`；
  - 含义：SE 通道。
- `sound_type`
  - 类型：`Int`；
  - 有效范围：`0..=9`；
  - 含义：音效类型槽位。

### 10.3 具体作用

[`sound_type()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:427-461) 调用 `se_player.set_type(channel, sound_type)`，把某个 SE 通道归入指定类型。

之后该通道会受到对应类型音量设置的影响，例如：

```text
SoundType(channel, 3)
SoundTypeVol(3, 50)
```

### 10.4 结论

> `SoundType` 是 **把 SE 通道绑定到音效类型槽位的接口**。

类型编号的固定业务名称当前 reference 未提供，需要结合游戏配置或样本进一步确认。

---

## 11. `SoundTypeVol`

### 11.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5855)
- **签名**：`SoundTypeVol(sound_type, volume)`
- **返回值**：`Nil`

### 11.2 入参语义

- `sound_type`
  - 类型：`Int`；
  - 有效范围：`0..=9`；
  - 含义：音效类型槽位。
- `volume`
  - 类型：`Int`；
  - 有效范围：`0..=100`；
  - 含义：该类型的整体音量百分比。

### 11.3 具体作用

[`sound_type_vol()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:464-501) 把音量换算为 `0.0..1.0`，再调用 `se_player.set_type_volume(sound_type, volume, Tween::default())`。

当前实现立即设置类型音量，不接受淡入淡出参数。类型音量是组级控制，具体是否影响已播放声音、后续声音或两者，最终由 `se_player` 后端决定；当前 syscall 层没有进一步分支。

### 11.4 结论

> `SoundTypeVol` 是 **设置某个音效类型整体音量的接口**。

---

## 12. `SoundPan`

### 12.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5624)
- **签名**：`SoundPan(channel, pan)`
- **返回值**：`Nil`
- **实现类别**：legacy / 兼容接口。

### 12.2 入参语义

- `channel`
  - 类型：`Int`；
  - 当前实现有效范围：`0..=31`；
  - 含义：旧版 SE 通道。
- `pan`
  - 类型：`Int`；
  - 有效范围：`-100..=100`；
  - 含义：左右声像位置。

当前实现采用：

```text
normalized_pan = (pan + 100) / 200
```

因此：

- `-100` -> `0.0`：最左；
- `0` -> `0.5`：中间；
- `100` -> `1.0`：最右。

### 12.3 具体作用

[`sound_pan()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:470-483) 调用 `se_player.set_panning(channel, normalized, Tween::default())`。

### 12.4 兼容边界

数据库把 `SoundPan` 归为 `Sound` 组，但它不在现代 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:1) 的显式 Sound 条目中，而是由 legacy 表注册：[`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:605)。

因此当前结论是：

- 参数范围和归一化逻辑有明确实现依据；
- 它确实影响 SE 声像；
- 原版不同版本的通道数量和 pan 数值方向仍应通过更多样本验证。

### 12.5 结论

> `SoundPan` 是 **旧版兼容的 SE 左右声像设置接口**。

---

## 13. Sound 组整体语义

9 条 syscall 可以划分为以下子家族：

1. **资源加载**
   - `SoundLoad`
2. **播放与停止**
   - `SoundPlay`
   - `SoundStop`
3. **通道静音与音量**
   - `SoundSilentOn`
   - `SoundVol`
4. **全局与分类音量**
   - `SoundMasterVol`
   - `SoundTypeVol`
5. **通道分类**
   - `SoundType`
6. **声像控制**
   - `SoundPan`

典型 SE 播放流程可以概括为：

```text
SoundLoad(channel, path)
SoundType(channel, sound_type)
SoundVol(channel, volume, crossfade)
SoundPlay(channel, looped, fadein)

// 需要时：
SoundPan(channel, pan)
SoundStop(channel, fadeout)
```

对于分类音量，还可以使用：

```text
SoundTypeVol(sound_type, volume)
```

对于所有音频输出，则使用：

```text
SoundMasterVol(volume)
```

因此，`Sound` 分组的整体语义可以概括为：

> **FVP 的 SE/音效控制总线：将音效资源装入通道，按通道播放并控制其停止、静音、音量、类别和左右声像。**

---

## 14. 高置信度结论

以下结论比较稳：

- `Sound` 分组当前共有 9 个 syscall。
- `Sound*` 主要操作 `se_player`，而 `Audio*` 主要操作 `bgm_player`，两者不应混淆。
- `SoundLoad` 的路径参数接受 `String/ConstString/Nil`，`Nil` 用于停止/卸载通道。
- `SoundPlay` 的通道范围为 `0..255`，支持循环和毫秒级淡入。
- `SoundStop` 的通道范围为 `0..255`，支持毫秒级淡出。
- `SoundSilentOn` 是持续静音，不等价于停止播放。
- `SoundVol` 使用 `0..100` 的通道音量，并支持毫秒级过渡。
- `SoundMasterVol` 使用 `0..100` 的宿主总音量。
- `SoundType` 的音效类型范围为 `0..9`。
- `SoundTypeVol` 使用 `0..100` 设置类型组音量。
- `SoundPan` 接受 `-100..100`，并归一化为 `0..1` 后设置 SE 声像。
- 所有 Sound syscall 都不直接改变 VM 调度状态，返回值均为 `Nil`。

---

## 15. 仍需保守处理的点

1. `SoundType` 的 10 个类型编号没有在当前 reference 中恢复固定业务名称，本文只把它们描述为类型槽位。
2. `SoundSilentOn` 在当前 syscall 表中没有对应的解除静音接口，解除方式可能依赖播放器内部逻辑、重新加载或其他未覆盖接口。
3. `SoundPan` 只有 `0..31` 的 legacy 通道范围，而其他 Sound 通道接口允许 `0..255`；这可能体现旧版 ABI 差异，仍需跨作品验证。
4. `SoundPlay` 中传给底层播放器的固定参数 `1.0` 与 `0.5` 在当前 syscall 层没有明确名称，其精确后端含义暂不展开。
5. 具体音效文件格式、解码器能力和资源包路径解析由 VFS 与音频后端决定，不能仅依据 syscall 层确定。
6. `SoundTypeVol` 对已经播放中的声音和后续新播放声音的具体作用时机，仍应结合 `se_player` 实现和实机行为验证。

---

## 16. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:104-106)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5535-5947)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:127-135)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:121-128)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:569-611)
- [`sound.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:272-581)
- [`sound.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:584-836)
- [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:470-483,605)
- [`script/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/script/mod.rs:118-128)
- [`23_Snow.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/23_Snow.md:1)
- [`22_Save.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/22_Save.md:1)
