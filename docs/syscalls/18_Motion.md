# Motion 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:78)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:60) 与 rfvp 参考实现，Motion 分组当前包含 19 个 syscall：

1. `MotionAlpha`
2. `MotionAlphaStop`
3. `MotionAlphaTest`
4. `MotionAnim`
5. `MotionAnimStop`
6. `MotionAnimTest`
7. `MotionMove`
8. `MotionMoveR`
9. `MotionMoveRStop`
10. `MotionMoveRTest`
11. `MotionMoveS2`
12. `MotionMoveS2Stop`
13. `MotionMoveS2Test`
14. `MotionMoveStop`
15. `MotionMoveTest`
16. `MotionMoveZ`
17. `MotionMoveZStop`
18. `MotionMoveZTest`
19. `MotionPause`

其注册位置可见于 [`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:63) 到 [`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:81)，以及 [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:598) 到 [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:614)、[`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:741) 到 [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:743)。

综合源码与现有成果，Motion 分组可以概括为：

> **围绕 prim 的透明度、平移、旋转、缩放、Z 深度、帧动画与暂停状态进行控制的一组时间型动画接口。**

这组 syscall 的共同点是：

- 大多以某个 prim id 为作用对象；
- 大多带有毫秒级时长参数；
- 大多分成 `启动 / Stop / Test` 三联形式；
- `Test` 常用于脚本轮询动画是否结束。

---

## 2. 边界说明：Motion 与 V3D 的区分

虽然 [`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:683) 同时实现了 `V3DMotion*`，但根据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:112) 的分组统计，`V3D` 是单独分组，不属于本次 Motion 组范围。

因此本文只覆盖：

- `Motion*`
- 不覆盖：`V3DMotion / V3DMotionPause / V3DMotionStop / V3DMotionTest / V3DSet`

---

## 3. 共享实现约定

## 3.1 作用对象统一是 prim

除 [`MotionPause`](#9-motionpause) 外，大多数 Motion syscall 都要求：

- `prim id` 范围为 `1..=4095`

可直接从各实现中看到：

- [`MotionAlpha`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:40)
- [`MotionMove`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:160)
- [`MotionMoveR`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:284)
- [`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:399)
- [`MotionMoveZ`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:543)

因此这组接口默认都是：

> **对单个 prim 的时间推进动画。**

## 3.2 时长单位统一为毫秒

所有主要动画启动接口都要求 `duration` 在：

- `1..=300000`

例如：

- [`MotionAlpha`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:71)
- [`MotionMove`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:193)
- [`MotionMoveR`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:307)
- [`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:452)
- [`MotionMoveZ`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:576)

因此可高置信度判断：

> **Motion 组所有持续时间参数都以毫秒为单位。**

## 3.3 `typ` 是运动类型 / easing 枚举

对 `MotionMove`、`MotionMoveR`、`MotionMoveS2`、`MotionMoveZ` 来说，`typ` 会被解释为对应的 *MotionType 枚举，并在非法值时回退到 `Linear`：

- [`MoveMotionType`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:201-209)
- [`RotationMotionType`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:315-323)
- [`ScaleMotionType`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:460-468)
- [`ZMotionType`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:584-592)

这些枚举在现实现里至少包括：

- `Linear`
- `Accelerate`
- `Decelerate`
- `Rebound`
- `Bounce`

因此 `typ` 的保守统一语义可写成：

> **运动插值类型 / easing 模式。**

## 3.4 `reverse` 是存在性布尔位

各类 Motion 启动函数都把 `reverse` 按“是否为 `Nil`”解释：

- `reverse = !matches!(reverse, Variant::Nil)`

例如：

- [`MotionAlpha`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:92)
- [`MotionMove`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:219)
- [`MotionMoveR`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:331)
- [`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:478)
- [`MotionMoveZ`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:600)

因此：

> `reverse` 不是普通 0/1 整数，而是一个“参数存在即真”的布尔开关。

## 3.5 `Stop` / `Test` 的统一结构

Motion 组里大多数动画都有：

- `XxxStop(id)`：停止对应动画容器中的该条记录
- `XxxTest(id)`：查询该动画是否仍在运行

但要注意返回值并不完全统一：

- `MotionAlphaTest / MotionMoveTest / MotionMoveRTest / MotionMoveS2Test / MotionMoveZTest`
  - 返回 `True/Nil`
- `MotionAnimTest`
  - 返回 `Int(1/0)`：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1213-1214)

所以数据库里必须分开记录。

---

## 4. `MotionAlpha` 家族

### 4.1 `MotionAlpha`

#### 参数与返回

- **参数个数**：6：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:63)
- **签名**：`MotionAlpha(id, src_alpha, dst_alpha, duration, typ, reverse)`
- **返回值**：`Nil`

#### 参数语义

根据 [`motion_alpha()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:23-96)：

- `arg0: Int`：prim id，范围 `1..=4095`
- `arg1: Int | Nil`：起始 alpha；若缺省则取当前 `prim.alpha`
- `arg2: Int | Nil`：目标 alpha；若缺省则取当前 `prim.alpha`
- `arg3: Int`：持续时间 ms
- `arg4: Int | Nil`：alpha motion 类型
- `arg5: Variant`：reverse 存在性开关

#### 具体作用

`MotionAlpha` 会向 alpha motion container 注册一条记录：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:86-93)

现实现已明确的类型至少有：

- `Linear`
- `Immediate`

并且底部注释给了非常直接的语义说明：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:816-852)

可概括为：

> **对 prim 的 alpha 做一段时长可控的淡入/淡出/立即设值动画。**

#### 脚本样例

- [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:33-37)
- [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:81-146)

---

### 4.2 `MotionAlphaStop`

- **参数个数**：1
- **签名**：`MotionAlphaStop(id)`
- **返回值**：`Nil`
- **作用**：停止指定 prim 的 alpha 动画：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:98-115)

---

### 4.3 `MotionAlphaTest`

- **参数个数**：1
- **签名**：`MotionAlphaTest(id)`
- **返回值**：`BoolLike`
- **作用**：查询该 prim 是否仍有 alpha 动画在运行：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:117-138)

在现有研究里，它是最典型的轮询接口之一，例如：

- [`f_000104E8函数链作用总结.md`](fvp_analysis/result/hcbtool_test/f_000104E8函数链作用总结.md:91-93)
- [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:42-44)

---

## 5. `MotionMove` 家族（二维位移）

### 5.1 `MotionMove`

#### 参数与返回

- **参数个数**：8：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:69)
- **签名**：`MotionMove(id, src_x, src_y, dst_x, dst_y, duration, typ, reverse)`
- **返回值**：`Nil`

#### 参数语义

根据 [`motion_move()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:141-223)：

- `arg0: Int`：prim id
- `arg1: Int | Nil`：起始 x；缺省取当前 x
- `arg2: Int | Nil`：起始 y；缺省取当前 y
- `arg3: Int | Nil`：目标 x；缺省取当前 x
- `arg4: Int | Nil`：目标 y；缺省取当前 y
- `arg5: Int`：持续时间 ms
- `arg6: Int | Nil`：位移动画类型
- `arg7: Variant`：reverse 存在性开关

#### 具体作用

> **对 prim 做平面坐标位移动画。**

现有研究中，logo 与 CG/背景过场都大量使用这一接口：

- [`基于HCB字节码逆向的FVP引擎LOGO演出研究.md`](fvp_analysis/result/hcbtool_test/基于HCB字节码逆向的FVP引擎LOGO演出研究.md:214-216)
- [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:140-146)
- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:264-267)

---

### 5.2 `MotionMoveStop`

- **参数个数**：1
- **返回值**：`Nil`
- **作用**：停止二维位移动画：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:225-242)

---

### 5.3 `MotionMoveTest`

- **参数个数**：1
- **返回值**：`BoolLike`
- **作用**：查询二维位移动画是否仍在运行：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:244-265)

典型用途：

- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:108-112)
- [`f_000A2981结尾返回段解析.md`](fvp_analysis/result/hcbtool_test/f_000A2981结尾返回段解析.md:101-103)

---

## 6. `MotionMoveR` 家族（旋转）

### 6.1 `MotionMoveR`

- **参数个数**：6：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:70)
- **签名**：`MotionMoveR(id, src_r, dst_r, duration, typ, reverse)`
- **返回值**：`Nil`

根据 [`motion_move_r()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:267-335)：

- `src_r` / `dst_r` 缺省时取当前 `rotation`
- `duration` 为 ms
- `typ` 为旋转 motion type
- `reverse` 为存在性开关

高置信度语义：

> **对 prim 的旋转值做一段时长可控的插值动画。**

典型样例：

- [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:86-113)
- [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:33-36)

---

### 6.2 `MotionMoveRStop`

- **参数个数**：1
- **返回值**：`Nil`
- **作用**：停止旋转动画：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:337-354)

---

### 6.3 `MotionMoveRTest`

- **参数个数**：1
- **返回值**：`BoolLike`
- **作用**：查询旋转动画是否仍在运行：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:356-377)

典型样例：

- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:288-291)

---

## 7. `MotionMoveS2` 家族（缩放）

### 7.1 `MotionMoveS2`

- **参数个数**：8：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:73)
- **签名**：`MotionMoveS2(id, src_w_factor, src_h_factor, dst_w_factor, dst_h_factor, duration, typ, reverse)`
- **返回值**：`Nil`

根据 [`motion_move_s2()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:379-482) 与底部 wrapper [`MotionMoveS2`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1000-1024)：

- `src_*` / `dst_*` 都是缩放系数
- 合法范围 `100..=10000`
- 非法或缺省时回退到当前 prim 的 `factor_x / factor_y`
- `duration` 为 ms
- `typ` 为缩放 motion type
- `reverse` 为存在性开关

高置信度语义：

> **对 prim 的宽/高缩放因子做时间插值。**

典型样例：

- [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:91-106)
- [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:35-36)

---

### 7.2 `MotionMoveS2Stop`

- **参数个数**：1
- **返回值**：`Nil`
- **作用**：停止缩放动画：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:484-501)

---

### 7.3 `MotionMoveS2Test`

- **参数个数**：1
- **返回值**：`BoolLike`
- **作用**：查询缩放动画是否仍在运行：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:503-524)

典型样例：

- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:300-303)

---

## 8. `MotionMoveZ` 家族（Z 深度）

### 8.1 `MotionMoveZ`

- **参数个数**：6：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:78)
- **签名**：`MotionMoveZ(id, src_z, dst_z, duration, typ, reverse)`
- **返回值**：`Nil`

根据 [`motion_move_z()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:526-604)：

- `src_z` / `dst_z` 缺省时取当前 prim z
- `duration` 为 ms
- `typ` 为 Z motion type
- `reverse` 为存在性开关

高置信度语义：

> **对 prim 的 Z 深度值做时间插值。**

典型样例：

- [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:123-145)
- [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:36-37)
- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:276-279)

---

### 8.2 `MotionMoveZStop`

- **参数个数**：1
- **返回值**：`Nil`
- **作用**：停止 Z 动画：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:606-623)

---

### 8.3 `MotionMoveZTest`

- **参数个数**：1
- **返回值**：`BoolLike`
- **作用**：查询 Z 动画是否仍在运行：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:625-646)

典型样例：

- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:277-279)

---

## 9. `MotionPause`

### 9.1 参数与返回

- **参数个数**：2：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:81)
- **签名**：`MotionPause(id, pause)`
- **返回值**：`Int|Nil`

### 9.2 具体作用

[`motion_pause()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:648-681) 的逻辑是：

- `id` 范围允许 `0..=4096`
- 若 `pause` 是 `Int`：
  - `0` -> 取消暂停
  - 非 `0` -> 设为暂停
  - 返回 `Nil`
- 若 `pause == Nil`：
  - 返回当前 prim 的暂停状态 `Int(0/1)`

因此它的高置信度语义是：

> **设置或查询某个 prim 的暂停状态。**

它不是“暂停某一类 motion 容器”，而是修改 prim 上的 paused 标志，进而影响多种动画 updater 是否继续推进。

---

## 10. `MotionAnim` 家族（帧动画）

### 10.1 `MotionAnim`

- **参数个数**：4：[`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:66)
- **签名**：`MotionAnim(prim_id, sprt_prim_id, time, mode_or_nil)`
- **返回值**：`Nil`

根据 [`MotionAnim`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1171-1194)：

- `arg0: Int`：目标 prim id
- `arg1: Int`：sprite prim id / 帧源 prim id
- `arg2: Int`：时长 ms
- `arg3: Variant`：模式参数

其内部行为是：

- `mode <= 1` -> `set_anim_motion(..., 1)`
- `mode <= 2` -> `set_anim_motion(..., 2)`
- 否则 -> `append_anim_motion(...)`

因此高置信度语义可写成：

> **为 prim 挂接一段基于 sprite/帧源的帧动画，并根据模式选择替换式或追加式注册。**

已有研究中，标题菜单动画大量依赖这一接口：

- [`f_00075195逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00075195逐条反汇编对照.md:20-22, 75-77)

---

### 10.2 `MotionAnimStop`

- **参数个数**：1
- **返回值**：`Nil`
- **作用**：停止帧动画：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1196-1205)

典型样例：

- [`f_00075195逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00075195逐条反汇编对照.md:869-878)

---

### 10.3 `MotionAnimTest`

- **参数个数**：1
- **返回值**：`Int(1/0)`
- **作用**：查询帧动画是否仍在运行：[`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:1207-1214)

注意它和其它 `Motion*Test` 不同，不返回 `True/Nil`，而是返回：

- `1`
- `0`

因此数据库中必须单独标注为：

- `return_type = Int|Nil?` 更准确应写 **`Int(0/1)`**

---

## 11. Motion 分组的整体语义

把 19 个 syscall 放在一起，可以看出非常鲜明的子家族结构：

1. **透明度动画**
   - `MotionAlpha / Stop / Test`
2. **二维平移动画**
   - `MotionMove / Stop / Test`
3. **旋转动画**
   - `MotionMoveR / Stop / Test`
4. **缩放动画**
   - `MotionMoveS2 / Stop / Test`
5. **Z 深度动画**
   - `MotionMoveZ / Stop / Test`
6. **暂停控制**
   - `MotionPause`
7. **帧动画**
   - `MotionAnim / Stop / Test`

因此，Motion 分组的整体语义可以概括为：

> **FVP 里针对 prim 的时序动画接口总线。**

脚本通常的工作流是：

1. 启动某类 motion
2. 在需要同步时不断 `Test`
3. 用 [`ThreadNext`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura/f_0003769F.lua:1) 或包装等待函数轮询
4. 在切场或回收时 `Stop`

---

## 12. 高置信度结论

以下结论比较稳：

- Motion 分组当前共有 19 个 syscall，不包含 `V3D*`。
- 大多数 motion 启动接口都以 prim id + duration + typ + reverse 为核心骨架。
- `duration` 统一为毫秒，合法范围 `1..=300000`。
- `typ` 统一扮演 easing / motion type 枚举角色，非法值回退到 `Linear`。
- `reverse` 在实现上统一是“非 Nil 即真”的存在性开关。
- `Stop` 统一返回 `Nil`。
- `Alpha/Move/MoveR/MoveS2/MoveZ` 的 `Test` 统一返回 `BoolLike`；`MotionAnimTest` 例外，返回 `Int(0/1)`。
- `MotionPause(nil)` 是查询；`MotionPause(int)` 是设置暂停状态。

---

## 13. 仍需保守处理的点

1. `typ` 的具体数值到枚举值映射，在不同 motion 子类中虽都能落到 `Linear/Accelerate/Decelerate/Rebound/Bounce`，但脚本层是否对每个数字都稳定使用，还需要更多跨作品样本。
2. `MotionAnim` 的 mode `1/2/append` 语义在当前源码中可见调用分流，但其业务含义（替换、聚焦、首帧模式等）仍建议结合实机表现继续细化。
3. `MotionPause` 对 `id=0/4096` 这类边界值的实际游戏意义还需额外样本验证。

---

## 14. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:98-103)
- [`generated.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:63-81)
- [`world.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:598-614, 741-743)
- [`motion.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:23-1216)
- [`motion_manager/mod.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:130-168)
- [`基于HCB字节码逆向的FVP引擎LOGO演出研究.md`](fvp_analysis/result/hcbtool_test/基于HCB字节码逆向的FVP引擎LOGO演出研究.md:67, 206-226, 445-450)
- [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:81-146, 190-243)
- [`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:33-44, 180-395)
- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:108-314, 444-532)
- [`f_00075195逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00075195逐条反汇编对照.md:20-22, 75-78, 869-879)
- [`f_000104E8函数链作用总结.md`](fvp_analysis/result/hcbtool_test/f_000104E8函数链作用总结.md:91-93)
- [`Sakura_entry_point功能分析.md`](fvp_analysis/result/hcbtool_test/Sakura_entry_point功能分析.md:281-283)
- [`f_000A2981结尾返回段解析.md`](fvp_analysis/result/hcbtool_test/f_000A2981结尾返回段解析.md:101-103, 319-320)
