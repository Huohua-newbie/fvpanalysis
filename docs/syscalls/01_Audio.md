# Audio 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md)、[`syscall_spec.txt`](../spec/syscall_spec.txt) 与 rfvp 参考实现，Audio 分组当前包含 7 个 syscall：

1. `AudioLoad`
2. `AudioPlay`
3. `AudioSilentOn`
4. `AudioState`
5. `AudioStop`
6. `AudioType`
7. `AudioVol`

其中，分组统计与参数个数基线来自 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:20) 与 [`syscall_spec.txt`](../spec/syscall_spec.txt:7)。

综合源码与脚本调用样例，Audio 分组可以暂时定性为：

> **FVP 中面向 4 路长音频槽位的控制组**。

这里的“长音频槽位”比“BGM 专用”更准确。原因是：

- rfvp 的实现把这组 syscall 路由到 [`BgmPlayer`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:38)；
- 但在 Sakura 实际脚本中，`AudioLoad` 的路径既有 `BGM/073` 这类 BGM，也有 `voice/00000000` 这类语音路径：例如 [`f_000822DA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000822DA.lua:64)、[`f_000553AA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:53)。

因此，本组更合适的语义名称是：

> **多槽位长音频/语音/BGM 控制接口**。

---

## 2. 共享约定

## 2.1 统一槽位范围

rfvp 在 [`bgm_player.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:16) 中定义：

- `BGM_SLOT_COUNT = 4`

并且 [`audio_load()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:10)、[`audio_play()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:46)、[`audio_stop()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:80)、[`audio_state()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:140)、[`audio_type()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:161)、[`audio_vol()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:228) 都显式校验 `0..4`。

所以 Audio 分组的第一个参数在绝大多数情况下都应理解为：

- **`Int` 类型的音频槽位号**
- 合法范围：`0..3`

## 2.2 返回值风格

从源码实现看：

- 除 [`AudioState`](#54-audiostate) 外，其余 6 个 Audio syscall 都返回 `Nil`
- [`AudioState`](#54-audiostate) 返回 `True / Nil`

因此这个分组的返回值模式很稳定：

- **控制类接口：`Nil`**
- **状态查询类接口：`BoolLike`（`True/Nil`）**

## 2.3 音量单位

[`audio_vol()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:244) 与 [`audio_vol_legacy_aw()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:200) 都把输入整数 `0..100` 归一化成 `0.0..1.0`。

因此脚本层看到的音量参数语义应为：

- **百分比整数音量**，范围通常是 `0..100`

## 2.4 类型桶（sound type）

[`bgm_player.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:18) 定义：

- `SOUND_TYPE_COUNT = 10`

[`audio_type()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:179) 也显式限制 `sound_type` 在 `0..10`。这说明 `AudioType` 的第二参数不是布尔位，而是：

- **0~9 的类型桶编号**

这个类型桶随后会参与有效音量计算：[`effective_volume_for_slot()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:104)。

---

## 3. 脚本侧可观测的典型槽位约定

以 Sakura 为例，可以观察到几组稳定用法：

- [`f_0005534C()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005534C.lua:23) 把 `G[218] = 2`、`G[217] = 3`
- 同函数把 `0`、`1`、`G[218]`、`G[217]` 都设置过 `AudioType` 与 `AudioVol`：[`f_0005534C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005534C.lua:5)
- [`f_000822DA()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000822DA.lua:64) 用一个槽位加载 `BGM/073` 并立即播放
- [`f_000553AA()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:53) 用 `voice/` 前缀拼接语音路径，再经 `AudioLoad/AudioPlay` 播放

所以在 Sakura 中，Audio 槽位很可能被这样使用：

- 一部分槽位偏向 BGM
- 一部分槽位偏向 voice
- 但底层 syscall 语义并不区分“只能 BGM”或“只能 voice”

这一点对逆向时很重要：

> **不要把 `Audio*` 机械理解成“BGM 专用接口”；它更像 4 路通用长音频槽。**

---

## 4. 逐条详解

## 4.1 `AudioLoad`

### 4.1.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:20)
- **签名**：`AudioLoad(channel, path)`
- **参数含义**：
  - `arg0: Int`：槽位号，范围 `0..3`
  - `arg1: String | ConstString | Nil`：资源路径；`Nil` 为特殊分支
- **返回值**：`Nil`：[`audio_load()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:31)

### 4.1.2 具体作用

[`audio_load()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:10) 的逻辑是：

1. 读取槽位参数，要求是 `Int(0..3)`
2. 若 `path` 为字符串：
   - 通过 VFS 读文件：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:27)
   - 调 [`load_named()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:91) 记录名字并装入数据
3. 若 `path == Nil`：
   - 走“特殊卸载/停用”分支：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:33)
   - 当前 rfvp 实现是对该槽位执行一次 [`stop()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:178)

### 4.1.3 语义判断

可以把它概括为：

> **向指定 Audio 槽位装入一个音频资源，并记录资源名。**

当第二参数为 `Nil` 时，rfvp 的实现更接近：

> **停止并撤销当前槽位的活动播放句柄。**

但这里要保守：源码注释写的是“unload channel”，而实现只明确做了 `stop`，并未同步清空 `bgm_datas` / `bgm_names`。因此更稳妥的表述是：

> `path = Nil` 时具有**停用/卸载式语义**，但“是否完全清空缓存数据”仍需原引擎实机再核实。

### 4.1.4 脚本样例

- 加载 BGM：[`f_000822DA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000822DA.lua:64)
- 加载 voice：[`f_000553AA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:76)
- 用 `Nil` 取消槽位：[`f_00055646.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055646.lua:6)

---

## 4.2 `AudioPlay`

### 4.2.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:21)
- **签名**：`AudioPlay(channel, looped)`
- **参数含义**：
  - `arg0: Int`：槽位号，范围 `0..3`
  - `arg1: Variant`：按 `canbe_true()` 解释的布尔样值
- **返回值**：`Nil`：[`audio_play()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:76)

### 4.2.2 具体作用

[`audio_play()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:46) 会：

1. 校验槽位号
2. 对第二参数执行 `canbe_true()`：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:64)
3. 调 [`BgmPlayer::play()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:108)

而 [`play()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:108) 内部会：

- 读取已装入的数据
- 记录 `repeat / volume / pan`
- 根据 `repeat` 决定是否设置 loop region：[`bgm_player.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:132)
- 如果这个槽位原来已有播放句柄，会先停掉旧句柄：[`bgm_player.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:144)

### 4.2.3 语义判断

可概括为：

> **播放指定槽位中已经装入的音频资源。第二参数控制是否循环播放。**

### 4.2.4 第二参数语义

- `true`：循环播放
- `nil`：不循环
- 其他能被 `canbe_true()` 判真的值：倾向循环

### 4.2.5 脚本样例

- BGM 循环播放：[`f_000822DA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000822DA.lua:72)
- voice 非循环/按参数播放：[`f_000553AA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:84)
- [`f_0005511C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005511C.lua:86) 中 `a3 == 1 or nil` 走 `true`，否则走 `nil`

---

## 4.3 `AudioSilentOn`

### 4.3.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:22)
- **签名**：`AudioSilentOn(channel)`
- **参数含义**：
  - `arg0: Int`：槽位号，范围 `0..3`
- **返回值**：`Nil`：[`audio_silent_on()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:130)

### 4.3.2 具体作用

[`audio_silent_on()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:116) 会调用 [`silent_on()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:168)。

而 [`silent_on()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:168) 会：

- 把 `bgm_muted[slot] = true`：[`bgm_player.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:171)
- 如果当前有播放句柄，则立即把音量设为 `0.0`：[`bgm_player.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:173)

### 4.3.3 语义判断

这是一个**一次开启、持续生效**的静音开关，而不是普通的“瞬时音量设 0”。

因为后续有效音量计算都会检查 `bgm_muted[slot]`：[`effective_volume_for_slot()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:104)、[`set_volume()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:152)、[`set_type()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:201)、[`set_type_volume()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:214)。

因此可概括为：

> **永久性地把指定槽位切入 muted 状态。**

### 4.3.4 不确定点

当前没有看到与之对称的 `AudioSilentOff`。因此“原引擎是否存在别的方式解除 muted”还需后续核实。

### 4.3.5 脚本样例

- [`f_0004DE8C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004DE8C.lua:60) 对 `G[217]` 执行 `AudioSilentOn`

---

## 4.4 `AudioState`

### 4.4.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:23)
- **签名**：`AudioState(channel)`
- **参数含义**：
  - `arg0: Int`：槽位号，范围 `0..3`
- **返回值**：`BoolLike`：`True / Nil`：[`audio_state()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:154)

### 4.4.2 具体作用

[`audio_state()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:140) 内部调用 [`is_playing()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:188)。

[`is_playing()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:188) 只检查：

- `bgm_slots[slot].is_some()`

因此该 syscall 的语义非常直接：

> **判断指定槽位当前是否有活动播放句柄。**

### 4.4.3 语义边界

它并不是“判断是否还有剩余样本没播完”的更细粒度查询，而是较粗的：

- 有句柄 -> `True`
- 无句柄 -> `Nil`

### 4.4.4 脚本样例

- 语音等待轮询：[`f_00055453.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055453.lua:94)
- 其他轮询点：[`f_0004D7A6.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004D7A6.lua:224)

---

## 4.5 `AudioStop`

### 4.5.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:24)
- **签名**：`AudioStop(channel, fadeout_ms)`
- **参数含义**：
  - `arg0: Int`：槽位号，范围 `0..3`
  - `arg1: Int | Nil`：淡出时长（毫秒）
- **返回值**：`Nil`：[`audio_stop()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:108)

### 4.5.2 具体作用

[`audio_stop()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:80) 会：

1. 校验槽位
2. 读取 `fadeout`，合法范围 `0..=300000`：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:98)
3. 生成一个 `Tween(duration=fadeout_ms)`：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:103)
4. 调 [`stop()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:178)

### 4.5.3 语义判断

可概括为：

> **停止指定槽位的播放，并可选地做一段毫秒级淡出。**

当第二参数为 `Nil` 或非法值时，按源码实现会退化成：

- **0 ms 立即停止**

### 4.5.4 脚本样例

- 立即停止：[`f_00039C85.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00039C85.lua:750)
- 100 ms 淡出：[`f_0005511C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005511C.lua:56)
- 2000 ms 淡出：[`f_000553AA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:50)

---

## 4.6 `AudioType`

### 4.6.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:25)
- **签名**：`AudioType(channel, sound_type)`
- **参数含义**：
  - `arg0: Int`：槽位号，范围 `0..3`
  - `arg1: Int`：类型桶编号，范围 `0..9`
- **返回值**：`Nil`：[`audio_type()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:192)

### 4.6.2 具体作用

[`audio_type()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:161) 会把 `sound_type` 存入对应槽位：

- [`set_type()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:201)

在 [`set_type()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:201) 中，这个类型桶会参与有效音量计算：

- `actual_volume = slot_volume × type_volume`

### 4.6.3 语义判断

可概括为：

> **把某个 Audio 槽位归类到一个 0~9 的音量类型桶中。**

它本身不直接播放、不直接停音，但会影响之后该槽位的实际输出音量。

### 4.6.4 脚本样例

- 启动默认配置：[`f_0005534C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005534C.lua:5)
- 加载 BGM 前设类型：[`f_0005511C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005511C.lua:59)

### 4.6.5 进一步说明

在 Sakura 中可以看到：

- `AudioType(0, 1)`、`AudioType(1, 1)`：[`f_0005534C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005534C.lua:5)
- `AudioType(G[218], 0)`、`AudioType(G[217], 0)`：[`f_0005534C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005534C.lua:27)

这说明不同槽位可能被归到不同类型桶，以便区分 BGM、voice 或其他长音频类别的统一调音策略。

---

## 4.7 `AudioVol`

### 4.7.1 参数与返回

- **标准参数个数**：3：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:26)
- **标准签名**：`AudioVol(channel, volume_percent, crossfade_ms)`
- **参数含义**：
  - `arg0: Int`：槽位号，范围 `0..3`
  - `arg1: Int`：音量百分比，范围 `0..100`
  - `arg2: Int | Nil`：交叉淡变时长（毫秒），合法范围 `0..300000`
- **返回值**：`Nil`：[`audio_vol()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:264)

### 4.7.2 具体作用

[`audio_vol()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:228) 的逻辑是：

1. 校验槽位号
2. 校验音量百分比 `0..100`
3. 读取第三参数作为 crossfade 毫秒数，非法则按 0：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:251)
4. 把百分比换算成 `0.0..1.0`：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:258)
5. 调 [`set_volume()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:152)

[`set_volume()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:152) 内部又会考虑：

- 若槽位被 `muted`，实际音量强制为 `0.0`
- 否则实际音量为 `slot_volume × type_volume`

### 4.7.3 语义判断

可概括为：

> **设置指定 Audio 槽位的基础音量，并可选择用毫秒级 tween 平滑过渡。**

### 4.7.4 脚本样例

- 默认满音量：[`f_0005534C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005534C.lua:15)
- 500 ms 调整到 58 / 70 / 100：[`f_000552D8.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000552D8.lua:35)
- 语音播放前设置音量：[`f_000553AA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:72)

### 4.7.5 兼容分支

源码还保留了一个旧 ABI：[`audio_vol_legacy_aw()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:200)。

其注释明确写道：

- AngelWish 早期 ABI 用的是 `AudioVol(channel, volume)` 两参数形式：[`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:197)
- 语义与后来的 `AudioVol` 基本相同，但**没有 crossfade 参数**

因此应记录一个兼容结论：

> **当前数据库以 3 参为标准，但早期 FVP/AngelWish 系可能存在 2 参 AudioVol 旧 ABI。**

---

## 5. Audio 分组的整体工作流

从脚本常见调用模板看，Audio 分组通常按以下顺序组合出现：

1. [`AudioStop`](#45-audiostop)
2. [`AudioType`](#46-audiotype)
3. [`AudioVol`](#47-audiovol)
4. [`AudioLoad`](#41-audioload)
5. [`AudioPlay`](#42-audioplay)
6. 需要等待时用 [`AudioState`](#44-audiostate) 轮询

例如：[`f_0005511C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005511C.lua:56)、[`f_000553AA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:50)、[`f_00055453.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055453.lua:74)。

这说明 Audio 分组是一个相对完整的槽位控制链，而不是零散接口。

---

## 6. 当前高置信度结论

以下结论可以认为比较稳：

- Audio 分组统一面向 **4 个长音频槽位**。
- 槽位参数统一是 `Int(0..3)`。
- [`AudioLoad`](#41-audioload) 负责装入路径对应的音频资源。
- [`AudioPlay`](#42-audioplay) 第二参数控制循环播放与否。
- [`AudioStop`](#45-audiostop) 第二参数是毫秒级淡出时间。
- [`AudioState`](#44-audiostate) 返回的是 `True/Nil`，语义是“该槽位当前是否在播放”。
- [`AudioType`](#46-audiotype) 负责把槽位挂到 `0..9` 类型桶上。
- [`AudioVol`](#47-audiovol) 用 `0..100` 百分比设置槽位音量，第三参数控制平滑过渡时长。
- [`AudioSilentOn`](#43-audiosilenton) 不是瞬时静音，而是持续生效的 `muted` 标志。

---

## 7. 仍需保守处理的点

1. `AudioLoad(channel, Nil)` 在原引擎中是否真的“完全卸载缓存数据”，仍需原版实机验证；rfvp 当前实现更接近“停止并停用当前播放”。
2. 虽然 rfvp 用 [`BgmPlayer`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:38) 承载 Audio 分组，但 Sakura 脚本又明确用它播放 voice，因此不宜把本组过度简化成“BGM 接口”。
3. `AudioType` 对应的 10 个类型桶在游戏设计层分别叫什么，还需要继续从配置界面与系统设置链条补证。

---

## 8. 本组条目速查表

| syscall | argc | 入参语义 | 返回 | 作用摘要 |
|---|---:|---|---|---|
| `AudioLoad` | 2 | `channel:int(0..3)`, `path:string|nil` | `Nil` | 向槽位装入音频资源；`nil` 表示停用/卸载式分支 |
| `AudioPlay` | 2 | `channel:int`, `looped:boollike` | `Nil` | 播放槽位中已装入的音频；可循环 |
| `AudioSilentOn` | 1 | `channel:int` | `Nil` | 把槽位永久切入静音状态 |
| `AudioState` | 1 | `channel:int` | `BoolLike` | 查询槽位是否在播放 |
| `AudioStop` | 2 | `channel:int`, `fadeout_ms:int|nil` | `Nil` | 停止槽位播放，可淡出 |
| `AudioType` | 2 | `channel:int`, `sound_type:int(0..9)` | `Nil` | 把槽位挂到音量类型桶 |
| `AudioVol` | 3 | `channel:int`, `volume:int(0..100)`, `crossfade_ms:int|nil` | `Nil` | 设置槽位基础音量，可平滑过渡 |

---

## 9. 证据来源

- [`README.md`](../manual/syscall-db.md:82)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:7)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:20)
- [`sound.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/sound.rs:10)
- [`bgm_player.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/audio_player/bgm_player.rs:16)
- [`f_0005534C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005534C.lua:5)
- [`f_0005511C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0005511C.lua:56)
- [`f_000553AA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000553AA.lua:50)
- [`f_00055453.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00055453.lua:74)
- [`f_000552D8.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000552D8.lua:35)
- [`f_0004DE8C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004DE8C.lua:60)
- [`f_000822DA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000822DA.lua:64)
