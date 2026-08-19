# 08 · 案例：LOGO 演出分析

> **前置阅读**：[04 · Syscall 系统](./04-syscall-system.md)

本文以 `f_00074DA5`（一个 LOGO 演出函数）为例，演示如何从 HCB 字节码逐步还原出"多图层、多运动、协同演出"的完整动画逻辑。

---

## 对象

函数地址：`0x00074DA5`  
功能：播放品牌 LOGO 动画，包含背景、主体 LOGO、前景框、三个旋转分片的组合演出

相关资源推测：
- `logo_bg`：背景底图
- `logo_favo`：主体 LOGO
- `logo_favo_view`：前景遮罩/框体
- `logo_favo_view_p1/p2/p3`：三个分片

---

## 图层对应关系

| prim ID | 资源名（推测） | 作用 |
|---:|---|---|
| 250 | `logo_bg` | 背景底板 |
| 252 | `logo_favo` | 主体 LOGO |
| 254 | `logo_favo_view` | 前景框体 |
| 255 | `logo_favo_view_p1` | 旋转分片 1 |
| 256 | `logo_favo_view_p2` | 旋转分片 2 |
| 257 | `logo_favo_view_p3` | 旋转分片 3 |

---

## 演出分解

### 阶段一：初始摆位

在动画开始前，脚本先装载并初始化所有图层的初始状态。

#### prim 252 / `logo_favo`（主体 LOGO）

```lua
__syscall("PrimSetZ", 252, 1000)
__syscall("PrimSetOP", 252, 640, 360)
__syscall("PrimSetAlpha", 252, 0)
```

- 位于屏幕中心 `(640, 360)`
- 初始完全透明（`alpha = 0`）
- Z 层级 `1000`

#### prim 254 / `logo_favo_view`（前景框）

```lua
__syscall("PrimSetAlpha", 254, 0)
__syscall("PrimSetZ", 254, 1000)
__syscall("PrimSetOP", 254, 640, 360)
```

- 同样位于中心
- 初始完全透明
- 与主体在同一深度附近

#### prim 255/256/257（三个分片）

```lua
__syscall("PrimSetAlpha", 255, 0)
__syscall("PrimSetOP", 255, 634, 413)

__syscall("PrimSetAlpha", 256, 0)
__syscall("PrimSetOP", 256, 634, 413)

__syscall("PrimSetAlpha", 257, 0)
__syscall("PrimSetOP", 257, 634, 413)
```

- 三个分片的锚点完全相同：`(634, 413)`
- 都从完全透明开始
- 它们的视觉差异来自后续的**运动参数**，而不是初始坐标

---

### 阶段二：启动主动画

统一时长变量：`l0 = 2000`（2000 毫秒）

#### prim 257 / 分片 3

```lua
__syscall("MotionAlpha", 257, 0, 255, 2000, nil, nil)
__syscall("MotionMoveR", 257, -3600, 0, 2000, 3, nil)
__syscall("MotionMoveS2", 257, 5000, 1000, 5000, 1000, 2000, 3, nil)
```

解读：

1. **`MotionAlpha(257, 0, 255, 2000)`**：2 秒内从透明淡入到完全不透明
2. **`MotionMoveR(257, -3600, 0, 2000)`**：旋转从 `-3600`（-360°）到 `0`（旋转单位是 0.1°）
   - 即：从**逆时针旋转一整圈**收束到正位
3. **`MotionMoveS2(257, 5000, 1000, 5000, 1000, 2000)`**：缩放参数起止相同
   - 推测：维持一个固定的非等比缩放形态（横向拉伸？），而不是从 A 缩放到 B

#### prim 256 / 分片 2

```lua
__syscall("MotionAlpha", 256, 0, 255, 2000, nil, nil)
__syscall("MotionMoveR", 256, 3600, 0, 2000, 3, nil)
__syscall("MotionMoveS2", 256, 5000, 1000, 5000, 1000, 2000, 3, nil)
```

解读：

- 淡入逻辑相同
- 旋转从 **`+3600`**（+360°）到 `0`
  - 即：从**顺时针旋转一整圈**收束到正位
- 缩放参数与分片 3 一致

#### prim 255 / 分片 1

```lua
__syscall("MotionAlpha", 255, 0, 255, 2000, nil, nil)
__syscall("MotionMoveR", 255, 3600, 0, 2000, 3, nil)
__syscall("MotionMoveS2", 255, 5000, 1000, 5000, 1000, 2000, 3, nil)
```

与分片 2 几乎完全相同（都是从 `+360°` 转回）。

#### prim 252 / 主体 LOGO

```lua
__syscall("MotionMoveZ", 252, 750, 1000, 1800, 3, nil)
__syscall("MotionAlpha", 252, 0, 255, 1800, nil, nil)
```

- 时长 `1800ms`（= `l0 - 200`，比分片略短）
- Z 轴从 `750` 推进到 `1000`（纵深靠近感）
- 同步淡入

#### prim 254 / 前景框

```lua
__syscall("MotionMoveZ", 254, 750, 1000, 2000, 3, nil)
__syscall("MotionMove", 254, nil, 50, nil, 0, 2000, 3, nil)
__syscall("MotionAlpha", 254, 0, 255, 2000, nil, nil)
```

解读：

1. Z 轴推进（与主体类似）
2. **`MotionMove(254, nil, 50, nil, 0, 2000)`**
   - `src_x = nil`, `dst_x = nil`：X 不变
   - `src_y = 50`, `dst_y = 0`：Y 从偏移 `50` 滑回 `0`
   - 效果：从下方向上滑入
3. 同步淡入

---

### 阶段三：等待与跳过逻辑

```lua
repeat
  __syscall("MotionAlphaTest", 252)
  if __ret ~= nil then break end
  __syscall("ControlPulse")
  if __ret ~= nil then break end
until false
```

脚本循环检查：

- **`MotionAlphaTest(252)`**：主体 LOGO 的 alpha 动画是否完成
- **`ControlPulse`**：玩家是否按键跳过

若未跳过，背景层执行一次较长淡出（`3500ms`）。

---

### 阶段四：收尾统一淡出

```lua
__syscall("MotionAlpha", 253, nil, 0, 2500, nil, nil)
__syscall("MotionAlpha", 252, nil, 0, 2500, nil, nil)
__syscall("MotionAlpha", 254, nil, 0, 2500, nil, nil)
__syscall("MotionAlpha", 255, nil, 0, 2500, nil, nil)
__syscall("MotionAlpha", 256, nil, 0, 2500, nil, nil)
__syscall("MotionAlpha", 257, nil, 0, 2500, nil, nil)
```

所有图层都淡出到 `alpha = 0`，时长 `2500ms`。

最后再执行一轮快速清零（`100ms`）确保完全消失。

---

## 演出总结

这个 LOGO 演出的视觉语言可以概括为：

> **背景稳住，主体推进，前景滑入，三分片旋转聚合，最后整体消隐。**

关键技法：

1. **多图层并行动画**：6 个 prim 同时运动，各自独立却协调一致
2. **相反方向的旋转收束**：分片 3 从 `-360°`，分片 1/2 从 `+360°`，制造"碎片拼合"视觉
3. **Z 轴推进 + 淡入**：不只是平面淡入，还有纵深靠近感
4. **前景滑入**：Y 偏移动画营造"框体从下方滑上"的效果
5. **统一淡出**：收尾时所有图层一起消失，干净利落

---

## 从 HCB 到运动的映射

单看字节码，我们只能看到一串 `push_i32`、`syscall MotionAlpha` 之类的指令。但结合：

- prim ID 与资源名的映射
- `MotionAlpha` / `MotionMoveR` / `MotionMove` / `MotionMoveZ` 的参数语义
- 旋转单位 `0.1°` 的换算
- Z 轴的推进方向

就能完整还原出"6 个图层、12+ 个并发动画、2+ 秒演出"的全貌。

---

## 下一篇

[→ 09 · 研究路线图](./09-roadmap.md)
