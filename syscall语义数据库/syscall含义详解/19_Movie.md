# Movie 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:99)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3251)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:79) 与 rfvp 参考实现，`Movie` 分组当前共有 4 个 syscall：

1. [`Movie`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252)
2. [`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300)
3. [`MovieState`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3349)
4. [`MovieStop`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3391)

### 总览

| syscall | 参数 | 返回 | 核心语义 | 置信度 |
|---|---:|---|---|---|
| [`Movie`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252) | 2 | `BoolLike` | 启动影片播放；`flag=nil` 为图层视频，非 `Nil` 为 modal 影片 | 高 |
| [`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300) | 2 | `BoolLike` | [`Movie`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252) 的 legacy 兼容名 | 高 |
| [`MovieState`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3349) | 1 | `BoolLike` | 查询影片播放/加载状态 | 高 |
| [`MovieStop`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3391) | 0 | `Nil` | 停止影片并清理资源 | 高 |

综合来看，`Movie` 组可以概括为：

> **围绕影片播放、状态查询与停止清理的一组时序媒体接口；其中 modal 影片会冻结脚本推进，而 layer 影片则作为叠加图层播放。**

---

## 2. 边界说明：`Movie` 与 legacy `MoviePlay`

自动规格表的显式注册项见 [`generated.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:82)，其中只有：

- [`Movie`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:82)
- [`MovieState`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:83)
- [`MovieStop`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:84)

而 [`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300) 是通过 legacy 注册链加入的：

- [`world.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:710)
- [`legacy.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:376)

其中 [`movie_play_legacy()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:376) 直接转调 [`movie_play()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:28)。

因此，当前 rfvp 语义下：

- `MoviePlay` 不是 stub；
- 它是 `Movie` 的 legacy 兼容名；
- 原始引擎中若存在细微差异，当前 reference 不足以把它与 `Movie` 完全拆分。

---

## 3. 共享实现约定

### 3.1 参数类型与真假规则

[`movie_play()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:28) 的参数规则是：

- `path`：脚本路径字符串，运行时接受 `String` 或 `ConstString`
- `flag`：`Variant`，但只按 **是否为 `Nil`** 判定模式

也就是说：

- `flag == Nil` => `layer/effect movie`，只播视频
- `flag != Nil` => `modal movie`，视频 + 音频，并冻结脚本推进

这不是整数真值判断，而是“参数存在性”判断：[`movie.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:34-35)

### 3.2 播放后端与资源层

[`VideoPlayerManager::start()`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:768) 会根据扩展名选择后端：

- `wmv` / `asf` -> WMV 管线
- `mpg` / `mpeg` / `m2v` / `ts` / `ps` / `vob` / `dat` -> MPEG 管线
- 其他 -> `mp4` 后端（若启用）

图层资源层使用保留槽位：

- [`MOVIE_GRAPH_ID = 4063`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:41)
- [`MOVIE_GROUP_PRIM_ID = 4095`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:46)
- [`MOVIE_SPRT_PRIM_ID = 4094`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:46)

[`ensure_layer()`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:927) 会把影片层挂到 root=0 的 prim 树上，并把 sprite 绑定到 movie 图层纹理。

### 3.3 调度副作用

modal 影片启动后会：

- [`game_data.set_halt(true)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:495)
- [`thread_wrapper.should_break()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:111)

因此它会打断当前脚本 context；layer 影片不做这一步。

---

## 4. `Movie`

### 4.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3255)
- **签名**：`Movie(path, flag)`
- **返回值**：`BoolLike`

### 4.2 入参语义

根据 [`movie_play()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:28)：

- `arg0 / path`
  - 类型：`String`（运行时也接受 `ConstString`）
  - 含义：影片路径
  - 非字符串时：直接返回 `Nil`
- `arg1 / flag`
  - 类型：`Variant`
  - 含义：模式开关
  - `Nil` => layer/effect movie
  - 非 `Nil` => modal movie

### 4.3 具体作用

[`Movie`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252) 的流程可以概括为：

1. 校验路径参数类型；
2. 按扩展名构造候选路径列表：[`movie_path_candidates()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:257)
3. 解析真实文件路径：
   - 游戏根目录直接命中
   - 否则查持久缓存
   - 再不行则从 VFS/包体抽取到缓存：[`resolve_movie_real_path()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:200)
4. 调用 [`VideoPlayerManager::start()`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:768)
5. 若是 modal 模式，则冻结脚本推进并让当前 context 退出当前轮次
6. 成功返回 `True`，失败返回 `Nil`

### 4.4 控制流与副作用

- `layer movie`：只播放，不冻结脚本
- `modal movie`：会影响 `GameData.halt`，并触发 break/yield 风格的调度切换
- 因此数据库里的 `yield=true`、`halt=true`、`conditional=true` 是合理的：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3278)

### 4.5 结论

> `Movie` 是 FVP 的核心影片启动接口，负责把影片资源接入视频播放后端，并根据 `flag` 决定是否进入 modal 阻塞模式。

---

## 5. `MoviePlay`

### 5.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3303)
- **签名**：`MoviePlay(path, flag)`
- **返回值**：`BoolLike`

### 5.2 当前 rfvp 语义

在当前 rfvp 中，[`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300) 通过 legacy 注册进入 syscall 表，但它并没有独立实现体，而是直接复用 [`movie_play()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:28)。

因此它的可确认语义与 [`Movie`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252) 一致：

- 同样接受影片路径与模式 flag
- 同样区分 layer / modal
- 同样返回 `True/Nil`
- 同样可能冻结脚本推进

### 5.3 兼容性说明

[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3344) 已明确把它标为旧版/兼容条目；这意味着：

- 它更像是历史脚本导入名；
- 现阶段可将其视作 `Movie` 的别名；
- 原始引擎是否存在额外差异，当前 reference 还不能独立验证。

### 5.4 结论

> `MoviePlay` 是 `Movie` 的 legacy 兼容入口，当前 rfvp 语义等同于 `Movie`。

---

## 6. `MovieState`

### 6.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3352)
- **签名**：`MovieState(mode)`
- **返回值**：`BoolLike`

### 6.2 入参语义

根据 [`movie_state()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:123)：

- `mode = 0`：查询“当前是否正在播放影片”
- `mode = 1`：查询“当前是否没有加载任何影片资源”
- 其他值：返回 `Nil`

### 6.3 具体作用

`MovieState` 是影片播放的查询接口，不修改播放状态，只读判断：

- `0` -> `game_data.video_manager.is_playing()`
- `1` -> `!game_data.video_manager.is_loaded()`

其中 [`is_loaded()`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:757) 直接对应 `playback.is_some()`。

源码注释还指出：`MovieState(1)` 常用于判断是否可以重新启动循环效果影片：[`movie.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:117-122)

### 6.4 控制流与副作用

- 不会改变 `halt`
- 不会触发 yield/wait
- 只是返回布尔型结果

### 6.5 结论

> `MovieState` 是影片系统的状态轮询接口，最可靠的语义是“是否在播”和“是否已卸载”。

---

## 7. `MovieStop`

### 7.1 参数与返回

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3394)
- **签名**：`MovieStop()`
- **返回值**：`Nil`

### 7.2 具体作用

[`MovieStop`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3391) 会调用：

- [`VideoPlayerManager::stop()`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:905)
- 并清除 `GameData.halt`：[`movie.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:147-151)

`stop()` 的具体清理动作包括：

- 置 `playing=false`
- 置 `modal=false`
- 隐藏并解绑 movie 图层 prim
- 清理音频句柄

### 7.3 控制流与副作用

[`MovieStop`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3404) 在数据库里没有被标记为 yield 型控制流；这与实现一致：

- 它不会主动挂起脚本
- 它的作用是“结束影片并恢复运行”
- 即使当前没有影片，也通常是幂等地清理并返回 `Nil`

### 7.4 结论

> `MovieStop` 是影片播放的收尾接口，负责停止播放、回收图层资源，并解除 modal 影片造成的暂停状态。

---

## 8. `Movie` 组整体语义

把 4 个 syscall 放在一起看，它们构成了一个完整的影片生命周期：

1. [`Movie`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252) / [`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300) 启动播放
2. [`MovieState`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3349) 轮询状态
3. [`MovieStop`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3391) 停止并清理

因此，`Movie` 分组的整体语义可以概括为：

> **FVP 中针对影片播放、影片状态与影片生命周期控制的一组接口。**

典型脚本模式通常是：

- 先启动影片；
- 在需要同步时轮询 [`MovieState()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:123)；
- 结束时调用 [`MovieStop()`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:147)。

---

## 9. 高置信度结论

以下结论比较稳：

- `Movie` 分组当前共有 4 个条目，包含 legacy 入口 [`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300)。
- [`Movie`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252) 与 [`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300) 在当前 rfvp 中复用同一实现。
- `Movie` 的第 2 参数不是整数真假，而是 `Nil / 非Nil` 模式位。
- `Movie` / `MoviePlay` 成功返回 `True`，失败返回 `Nil`。
- `MovieState(0)` 表示“是否正在播放”。
- `MovieState(1)` 表示“是否没有加载影片”。
- `MovieStop()` 返回 `Nil`，并清理播放资源与暂停状态。

---

## 10. 仍需保守处理的点

1. [`MoviePlay`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3300) 的原始引擎独立语义，当前 reference 只能确认它是兼容别名，无法证明是否曾有细微差异。
2. [`MovieState`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3349) 里除了 `0/1` 以外的 `mode` 值，当前源码只确认会返回 `Nil`，但其历史设计意图未完全恢复。
3. `Movie` 的路径候选与缓存抽取逻辑属于当前 rfvp 的运行实现细节，未必等同于原版引擎内部实现，只能作为行为层参考。
4. [`MovieStop`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3391) 会解除 `halt`，但数据库仍将其视为非 yield 型接口；这点适合保留为“恢复动作”而非“调度阻塞”。

---

## 11. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:78-113)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3251-3424)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:79-82)
- [`generated.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:82-84)
- [`world.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:668-671)
- [`world.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:710)
- [`legacy.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:376-378)
- [`movie.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:18-152)
- [`movie.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/movie.rs:155-292)
- [`videoplayer.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:41-49)
- [`videoplayer.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:757-825)
- [`videoplayer.rs`](rfvp-0.3.0/crates/rfvp/src/subsystem/resources/videoplayer.rs:905-953)
