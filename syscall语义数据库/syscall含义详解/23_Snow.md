# Snow 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:104)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5319-5529)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:124-126) 与 rfvp 参考实现，`Snow` 分组当前包含 3 个 syscall：

1. `Snow`
2. `SnowStart`
3. `SnowStop`

其显式规格与注册位置见 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:118-120) 与 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:697-698)。

综合实现，`Snow` 组可以概括为：

> **围绕雪花粒子运动的参数配置、启动和停止的一组全局效果接口。**

这组 syscall 与 [`PrimSetSnow`](fvp_analysis/result/syscall语义数据库/syscall含义详解/21_Prim.md:699) 需要配合理解：

- `Snow` 配置的是雪花运动槽位本身；
- `SnowStart` / `SnowStop` 控制运动槽位是否启用；
- `PrimSetSnow` 创建用于显示某个雪花槽位的 snow prim。

---

## 2. Snow 运行模型

### 2.1 固定的两个 Snow motion 槽位

[`SnowMotionContainer::new()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:534-543) 创建 2 个 `SnowMotion`：

- `id = 0`
- `id = 1`

因此 `Snow`、`SnowStart`、`SnowStop` 的第一个参数都必须是 `Int(0)` 或 `Int(1)`。

这不是普通 prim id，也不是 graph id；它是雪花运动配置槽位编号。

### 2.2 配置、启动、显示的三层关系

一个完整雪花效果通常需要三个层次：

1. [`Snow(id, ...)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:258) 配置运动槽位；
2. [`SnowStart(id)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:543) 将该槽位的 `enabled` 设为 `true`；
3. [`PrimSetSnow(prim_id, mode, x, y)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:378) 创建显示 prim，并使其引用对应雪花槽位。

停止时调用：

- `SnowStop(id)`：只关闭该雪花 motion；
- 如果还需要移除显示对象，再另行使用 `PrimGroupOut` / `PrimSetNull` 等 Prim 组接口。

### 2.3 Snow 的实际更新链

[`MotionManager::update_snow_motions()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:195-197) 会把帧间 elapsed time 传给 [`SnowMotionContainer::exec_snow_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:608-612)。

每个 enabled 的 `SnowMotion` 会：

- 更新每个雪花的位置与周期；
- 根据边界条件重置越界雪花；
- 按周期排序雪花指针；
- 在渲染阶段由 [`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:668-751) 逐个绘制。

`SnowStart` / `SnowStop` 本身不推进粒子，也不重新生成参数；它们只切换 `enabled`。

---

## 3. `Snow` 参数总表

### 3.1 签名与返回

- **参数个数**：18：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5322)
- **签名**：`Snow(id, width, height, texture_id, flake_w, flake_h, variant_count, period_min, period_max, flake_count, base_y, base_x, accel, jitter, color_r, color_g, time_override, color_b)`
- **返回值**：`Nil`
- **控制流**：不 yield、不 wait、不 sleep、不改变 VM context

### 3.2 参数详细映射

下表按脚本 syscall 参数位置列出。实现中的内部字段名与参数名并不完全一致，因此同时给出 `SnowMotion` 字段名。

| 参数 | 内部字段 | 类型 | 当前有效范围 | 含义 |
|---|---|---|---|---|
| `arg0: id` | motion slot | `Int` | `0..=1` | 雪花运动槽位 |
| `arg1: width` | `game_w_override` | `Int` | `0..=4096` | 雪花运动使用的游戏宽度覆盖值；`0` 表示使用当前游戏宽度 |
| `arg2: height` | `game_h_override` | `Int` | `0..=4096` | 雪花运动使用的游戏高度覆盖值；`0` 表示使用当前游戏高度 |
| `arg3` | `texture_id` | `Int` | `0..=4095` | 雪花基础纹理 / graph 起始编号 |
| `arg4` | `flake_w` | `Int` | `2..=64` | 单个雪花图块的配置宽度 |
| `arg5` | `flake_h` | `Int` | `2..=64` | 单个雪花图块的配置高度 |
| `arg6` | `variant_count` | `Int` | `1..=16` | 雪花纹理变体数量 |
| `arg7` | `period_min` | `Int` | `10..=10000` | 雪花周期下限 |
| `arg8` | `period_max` | `Int` | `10..=10000` | 雪花周期上限 |
| `arg9` | `flake_count` | `Int` | `1..=1024` | 雪花数量 |
| `arg10` | `base_y_per_period` | `Int` | `-4096..=4096` | 每周期的基础 Y 方向运动量 |
| `arg11` | `base_x_per_period` | `Int` | `-4096..=4096` | 每周期的基础 X 方向运动量 |
| `arg12` | `accel_param` | `Int` | `0..=1024` | 周期/运动加速度相关参数 |
| `arg13` | `jitter_amplitude` | `Int` | `0..=255` | 抖动/随机扰动幅度参数 |
| `arg14` | `color_r` | `Int` | `0..=255` | 雪花透明度插值的第一颜色/阶段值，当前作为 R 字段保存 |
| `arg15` | `color_g` | `Int` | `0..=255` | 雪花透明度插值的第三颜色/阶段值，当前作为 G 字段保存 |
| `arg16` | `time_override` | `Int` | `10..=10000` | 雪花周期颜色/透明度插值中间时间点 |
| `arg17` | `color_b` | `Int` | `0..=255` | 雪花透明度插值的第二阶段值，当前字段名为 `color_b_or_extra` |

参数范围和校验来自 [`snow()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:279-511)，字段写入来自 [`SnowMotion::set_snow()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:488-531)。

### 3.3 关于颜色参数顺序的特别说明

脚本参数的最后三个值在实现中并不是简单按 `R,G,B` 直观顺序参与渲染：

- `arg14` -> `color_r`
- `arg15` -> `color_g`
- `arg16` -> `time_override`
- `arg17` -> `color_b_or_extra`

渲染阶段读取为：

```text
p0 = period_min
p1 = time_override
p2 = period_max

alpha at p0 -> color_r
alpha at p1 -> color_b_or_extra
alpha at p2 -> color_g
```

具体代码见 [`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:678-703)。

因此，当前更稳妥的表述不是“RGB 颜色”，而是：

> **雪花透明度随周期变化的三个阶段值，以及其中间插值时间点。**

字段名 `color_r/color_g/color_b_or_extra` 体现了逆向过程中的历史命名，不能直接当作最终脚本语义。

---

## 4. `Snow` 具体作用

### 4.1 参数校验

[`snow()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:279-511) 对 18 个参数全部进行整数类型和范围检查：

- 任意参数类型不符合要求时返回 `Nil`；
- 任意参数超出范围时返回 `Nil`；
- 不会部分应用一组不完整配置。

### 4.2 初始化运动槽位

校验通过后，`Snow` 调用 [`MotionManager::set_snow_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:381-409)，再进入 [`SnowMotionContainer::push_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:549-594)。

`SnowMotion::set_snow()` 会：

1. 保存所有雪花配置参数；
2. 根据当前屏幕尺寸初始化雪花位置；
3. 为每个雪花生成随机变体、周期和初始坐标；
4. 将 `enabled` 设为 `false`。

这意味着：

> `Snow()` 配置完成后，雪花通常还没有开始显示运动；还需要 `SnowStart(id)`。

### 4.3 雪花粒子生成

[`init_snow_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:467-486) 会为 `flake_count` 个雪花生成初始状态：

- `variant_idx`：随机选择 `0..variant_count-1` 的纹理变体；
- `period`：在 `period_min..period_max` 范围内随机选择；
- `x/y`：在屏幕范围及雪花尺寸边界外扩区域内随机选择。

### 4.4 运动含义

更新阶段会根据以下参数影响雪花：

- `base_x_per_period`：X 方向运动；
- `base_y_per_period`：Y 方向运动；
- `accel_param`：周期变化和加速修正；
- `jitter_amplitude`：当前结构中保存了随机扰动参数，但具体使用路径需要结合更多逆向样本继续确认；
- `period_min/max`：运动周期和透明度阶段区间；
- `time_override`：透明度插值中间节点。

当雪花越过屏幕边界或周期超出限制时，会重新随机初始化：[`snow.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:228-440)。

### 4.5 结论

> `Snow` 是 **创建并初始化一个雪花粒子运动槽位的配置接口**。它负责保存资源、尺寸、数量、周期、运动和透明度参数，但不会直接开启显示。

---

## 5. `SnowStart`

### 5.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5462)
- **签名**：`SnowStart(id)`
- **返回值**：`Nil`

### 5.2 入参语义

- `id`
  - 类型：`Int`
  - 有效范围：`0..=1`
  - 含义：要启用的雪花运动槽位。

### 5.3 具体作用

[`snow_start()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:543-560) 调用 [`start_snow_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:596-602)，只做一件事：

```text
enabled = true
```

它不会：

- 重新读取纹理；
- 重新设置雪花数量；
- 重置所有粒子位置；
- 创建 Prim。

如果没有对应的 [`PrimSetSnow`](fvp_analysis/result/syscall语义数据库/syscall含义详解/21_Prim.md:699) 显示 prim，启动 motion 本身可能没有可见结果。

### 5.4 结论

> `SnowStart` 是 **启用指定雪花运动槽位的开关接口**。

---

## 6. `SnowStop`

### 6.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5500)
- **签名**：`SnowStop(id)`
- **返回值**：`Nil`

### 6.2 入参语义

- `id`
  - 类型：`Int`
  - 有效范围：`0..=1`
  - 含义：要停止的雪花运动槽位。

### 6.3 具体作用

[`snow_stop()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:562-579) 调用 [`stop_snow_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:604-606)，将：

```text
enabled = false
```

停止后：

- 帧更新不再推进该槽位的雪花运动；
- 渲染器的 Snow 分支因 `sm.enabled == false` 不再绘制雪花；
- 粒子数组和参数仍保留，可以再次 `SnowStart(id)`。

### 6.4 结论

> `SnowStop` 是 **关闭指定雪花运动和渲染的接口，但不会销毁配置或显示 prim**。

---

## 7. 与 `PrimSetSnow` 的边界

`PrimSetSnow` 属于 [`Prim`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4370) 分组，不属于本文的 Snow 分组；但实际显示时必须把两者结合起来理解。

### 7.1 `Snow` 侧负责什么

- 选择 motion slot `0/1`；
- 设置雪花纹理起点；
- 设置雪花图块尺寸；
- 设置变体数量；
- 设置数量、周期和运动速度；
- 设置透明度阶段参数；
- 启动或停止更新。

### 7.2 `PrimSetSnow` 侧负责什么

当前 `PrimSetSnow(id, mode, x, y)`：

- 创建 `PrimTypeSnow`；
- 设置显示 prim 的位置和默认属性；
- 但当前源码没有在 `PrimSetSnow` 中显式写入 snow motion slot 的 `texture_id`。

因此，`PrimSetSnow` 的 `mode` 与 Snow motion slot 的对应关系，当前 reference 尚未完全恢复。文档只能确认它是雪花显示 prim 的初始化参数，不能把 `mode=0/1` 直接断言为 Snow motion slot 0/1。

### 7.3 当前实现中的注意点

渲染器绘制 `PrimTypeSnow` 时读取 prim 的 `texture_id` 作为 snow motion slot：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:668-675)。而 `PrimSetSnow` 当前只把 prim 初始化为 `PrimTypeSnow`，并未在函数体中显式调用 `prim_set_texture_id()`：[`graph.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:414-441)。

因此：

- 原版脚本如何把 snow prim 绑定到 motion slot，仍需更多调用样本；
- `mode` 很可能参与了原引擎内部绑定或显示模式选择，但当前 rfvp 代码没有完整保留该分支；
- 本文不把 `Snow` 组与 `PrimSetSnow` 的绑定关系写死。

---

## 8. Snow 渲染语义

### 8.1 纹理变体

渲染器使用：

```text
graph_id = texture_id + (flake.variant_idx % variant_count)
```

因此 `texture_id` 是一组连续 snow 图像的起始 graph 编号，而不是单个雪花图像的唯一编号：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:684-710)。

### 8.2 雪花尺寸与缩放

渲染时使用：

```text
scale = 1000 / flake.period
width  = (flake_w - 1) * scale
height = (flake_h - 1) * scale
```

因此 `flake_w` / `flake_h` 是雪花图块配置尺寸，实际绘制尺寸还会受到当前粒子周期影响：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:720-745)。

### 8.3 透明度阶段

雪花透明度根据当前 `flake.period` 在三个阶段值之间插值：

- `period <= period_min`：使用 `color_r`；
- `period_min < period <= time_override`：从 `color_r` 插值到 `color_b_or_extra`；
- `time_override < period <= period_max`：从 `color_b_or_extra` 插值到 `color_g`；
- 超出范围：使用 `color_g`。

这说明最后三类颜色参数实际上承担的是雪花透明度曲线控制，而不一定是普通 RGB 着色。

---

## 9. Snow 组整体语义

3 个 syscall 构成一个清晰的生命周期：

1. `Snow(id, ...)`：配置并初始化槽位；
2. `SnowStart(id)`：开始更新与绘制；
3. `SnowStop(id)`：停止更新与绘制。

典型抽象流程为：

```text
Snow(0, width, height, texture_id, ...)
PrimSetSnow(prim_id, mode, x, y)
SnowStart(0)

// 运行期间由引擎帧循环自动更新

SnowStop(0)
```

因此，Snow 分组的整体语义可以概括为：

> **FVP 的雪花粒子效果控制总线：负责定义粒子资源与运动参数，并通过启停开关控制其持续更新。**

---

## 10. 高置信度结论

以下结论比较稳：

- `Snow` 分组当前共有 3 个 syscall。
- 雪花 motion slot 固定为 `0` 和 `1`。
- `Snow` 有 18 个参数，且参数均要求 `Int` 并进行范围校验。
- `Snow` 配置完成后会初始化随机雪花，但将 `enabled` 设为 `false`。
- `SnowStart(id)` 将指定槽位的 `enabled` 设置为 `true`。
- `SnowStop(id)` 将指定槽位的 `enabled` 设置为 `false`。
- 启停接口不 yield、不 wait、不 sleep，也不改变 VM context。
- 雪花数量上限为 `1024`；纹理变体数量当前限制为 `1..=16`。
- 雪花图块尺寸当前限制为 `2..=64`。
- 周期下限和上限当前限制为 `10..=10000`。
- X/Y 基础运动参数允许负值，因此可以表达左右、上下不同方向的运动。
- `texture_id` 是雪花变体纹理序列的起始 graph 编号。
- `PrimSetSnow` 属于 Prim 组，Snow 组只负责 motion 配置和启停。

---

## 11. 仍需保守处理的点

1. `Snow` 参数中的 `jitter_amplitude` 当前在配置结构中保存，但在已读取的更新路径中没有看到明确的独立扰动使用，具体原版效果仍需继续追踪。
2. `color_r/color_g/color_b_or_extra` 是逆向字段名；当前渲染逻辑显示它们更像透明度曲线阶段值，而不是普通 RGB 颜色，具体历史命名来源仍需验证。
3. `time_override` 的具体业务名称尚未恢复，目前只能确认它是透明度/周期插值的中间时间点。
4. `PrimSetSnow` 的 `mode` 与 Snow motion slot `0/1` 的绑定关系，当前 rfvp 实现没有完整体现，不能仅凭名字或参数范围下定论。
5. 当前 reference 没有检索到足够的 Snow 脚本调用样例，因此参数的“业务视觉名称”仍应以字段/运动公式描述为主。
6. `SnowStop` 会停止渲染，但不会从 prim 树中移除雪花对象；若原版脚本把 stop 与 prim 回收绑定使用，需要结合调用方继续确认。

---

## 12. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:104-106)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5319-5529)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:124-126)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:118-120)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:697-698)
- [`other_anm.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/other_anm.rs:258-579)
- [`snow.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:23-72)
- [`snow.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:125-185)
- [`snow.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:467-531)
- [`snow.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:534-612)
- [`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:95-110,195-197,381-421)
- [`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:668-751)
- [`graph.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:378-441)
- [`21_Prim.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/21_Prim.md:699-727)
