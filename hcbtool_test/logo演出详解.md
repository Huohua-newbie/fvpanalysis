# LOGO演出详解

## 1. 文档目的

本文在已有 [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md) 的基础上，进一步把 **HZC 资源内部自带的初始偏移信息** 纳入分析，给出更细的 LOGO 演出说明。

重点是回答两个问题：

1. 这些 `logo_*` 图层在原始脚本里是如何被装载与摆放的？
2. 若结合 HZC 内部偏移，初始位置与后续运动应如何理解？

---

## 2. 资源、脚本与测试脚本之间的关系

本次分析使用了 4 组材料：

- 原始演出脚本 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:1)
- 对应原始字节 [`f_00074DA5`](fvp_analysis/result/hcbtool_test/f_00074DA5)
- 动作语义参考 [`rfvp` motion / prim 实现](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/motion.rs:816)
- 新测试脚本 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py)

其中 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 的主要新增点是：

- 引入 [`LOGO_HZC_TOP_LEFT`](fvp_analysis/result/hcbtool_test/logo-test.py:67)
- 通过 [`anchor_center_from_top_left()`](fvp_analysis/result/hcbtool_test/logo-test.py:194) 把 **资源头记录的左上角偏移** 换算成当前演出脚本所用的中心锚点坐标
- 再把其余演出逻辑保持与原 [`logo演出.py`](fvp_analysis/result/hcbtool_test/logo演出.py) 近似一致

---

## 3. HZC 内部偏移数据

你给出的 HZC 资源头偏移如下：

| 资源名 | x(小端序) | y(小端序) | 十进制解释 |
|---|---|---|---|
| `logo_bg` | `00 00` | `00 00` | `(0, 0)` |
| `logo_favo` | `CF 01` | `04 01` | `(463, 260)` |
| `logo_favo_view` | `1B 02` | `96 01` | `(539, 406)` |
| `logo_favo_view_p1` | `6A 02` | `99 01` | `(618, 409)` |
| `logo_favo_view_p2` | `6A 02` | `94 01` | `(618, 404)` |
| `logo_favo_view_p3` | `6A 02` | `90 01` | `(618, 400)` |

这些值现在已经被写入 [`LOGO_HZC_TOP_LEFT`](fvp_analysis/result/hcbtool_test/logo-test.py:67)。

---

## 4. 为什么要把 HZC 内部偏移纳入初始位置

在之前的近似复现里，图层位置主要依据脚本中的：

- `PrimSetOP(252, 640, 360)`
- `PrimSetOP(254, 640, 360)`
- `PrimSetOP(255, 634, 413)`
- `PrimSetOP(256, 634, 413)`
- `PrimSetOP(257, 634, 413)`

但现在进一步阅读可发现，这些 `PrimSetOP` 更可能是：

> **sprite 的 OP / 锚点（anchor / pivot）设置**

而不一定是“图像左上角直接放在屏幕坐标 x,y”。

这一点可由 [`prim_set_op()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:204) 与 [`gpu_prim.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:559) 中的渲染逻辑佐证：

- `PrimSetOP` 写的是 `opx/opy`
- 渲染时当属性位 `0x02` 开启，会把它们当作 pivot 使用

也就是说，单靠 `PrimSetOP` 还不够，还需要图像资源本身给出的偏移信息，二者共同决定视觉上的摆放结果。

因此现在的思路是：

> **HZC 头中记录的 left/top 偏移 + 图像自身尺寸 -> 换算出初始中心锚点**

这一步在 [`anchor_center_from_top_left()`](fvp_analysis/result/hcbtool_test/logo-test.py:194) 中实现。

---

## 5. 初始位置如何换算

### 5.1 公式
当前测试脚本采用的换算方式是：

```python
center_x = left + image.width / 2
center_y = top + image.height / 2
```

对应实现：[`anchor_center_from_top_left()`](fvp_analysis/result/hcbtool_test/logo-test.py:194)

也就是把 HZC 中记录的“左上角偏移”变成复现脚本中的“中心锚点坐标”。

### 5.2 在脚本中的落点
在 [`build_layers()`](fvp_analysis/result/hcbtool_test/logo-test.py:199) 中：

- 先通过 [`load_image()`](fvp_analysis/result/hcbtool_test/logo-test.py:187) 读取图片
- 再通过 [`pos_for()`](fvp_analysis/result/hcbtool_test/logo-test.py:213) 调用 [`anchor_center_from_top_left()`](fvp_analysis/result/hcbtool_test/logo-test.py:194)
- 最后把换算结果写入各层的 `x/y`

因此，当前 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 中的初始层坐标，不再是手工居中，而是：

> **资源头偏移 + 图片宽高 -> 计算出的锚点中心**

---

## 6. 图层初始化阶段的更细解释

对应原始脚本 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:1) 的开头部分。

### 6.1 背景层：`logo_bg` / prim 250
脚本：

- [`f_000373A5(250, "logo_bg", 5, nil)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:19)

含义：

1. [`f_00037294()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118776) 负责拼接资源路径并 `GraphLoad`
2. [`f_00037345()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118845) 负责 `PrimSetSprt`
3. 第四参数 `5` 传给 [`f_00037476()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119048)，把该图元加入 group 5

由于 `logo_bg` 的 HZC 内偏移是 `(0,0)`，说明：

- 这张图本身就是“以左上角对齐为基础”的背景图
- 它更像是完整背景底板，而不是需要中心定位的对象

### 6.2 主体 LOGO：`logo_favo` / prim 252
脚本：

- [`f_000373A5(252, "logo_favo", 5, nil)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:24)
- [`PrimSetZ(252, 1000)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:27)
- [`PrimSetOP(252, 1280/2, 720/2)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:35)
- [`PrimSetAlpha(252, 0)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:38)

结合 HZC 偏移 `(463,260)`：

- 资源本身并不是“图像中心天然就在屏幕中心”的素材
- 而是有一个设计好的图像边界与左上角偏移
- `PrimSetOP(640,360)` 更像在指定它围绕哪个点发生后续运动/旋转/缩放

所以主体层的真实视觉位置应理解为：

> 图像资源自带矩形范围先落在 `(463,260)`，然后围绕脚本设定的 `(640,360)` 这个 OP / pivot 参与后续 Z 运动与 alpha 变化。

### 6.3 前景层：`logo_favo_view` / prim 254
脚本：

- [`f_000373A5(254, "logo_favo_view", 5, nil)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:43)
- [`PrimSetAlpha(254, 0)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:46)
- [`PrimSetZ(254, 1000)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:49)
- [`PrimSetOP(254, 640, 360)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:57)

结合 HZC 偏移 `(539,406)`：

- 这层素材天然比 `logo_favo` 更靠右、更靠下
- 如果单纯拿脚本的 `(640,360)` 强行居中，就会让它贴得太近
- 用 HZC 偏移后，它和主体层之间自然形成一层错位关系

这也是你之前观察到“`logo_favo.png` 和 `logo_favo_view.png` 间距过近”的根本原因之一：

> 仅靠脚本中的中心式参数，忽略了资源头的内建偏移，导致两层被错误叠得过近。

### 6.4 分片层：`logo_favo_view_p1/p2/p3`
脚本分别对应：

- [`f_000373A5(255, "logo_favo_view_p1", 5, nil)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:62)
- [`f_000373A5(256, "logo_favo_view_p2", 5, nil)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:74)
- [`f_000373A5(257, "logo_favo_view_p3", 5, nil)`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:86)

三者的 HZC 偏移分别是：

- p1: `(618,409)`
- p2: `(618,404)`
- p3: `(618,400)`

可以看出：

- 三者 x 相同
- y 呈现 `409 / 404 / 400` 的细微阶梯差

这说明它们不是完全重合的三张图，而是：

> 在资源阶段就已经设计好上下微小错位的三片结构

所以后续再叠加旋转收束动画时，视觉上会更有“分层碎片聚合”的感觉。

---

## 7. 启动动画阶段的更细解释

对应 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:94) 之后。

### 7.1 三个分片：p1 / p2 / p3
在 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py:392)～[`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py:408) 中，三片分别执行：

- `MotionAlpha`: `0 -> 255`
- `MotionMoveR`: 
  - p1: `3600 -> 0`
  - p2: `3600 -> 0`
  - p3: `-3600 -> 0`
- `MotionMoveS2`: `5000 -> 1000`（宽高都如此）

这里有两个层次：

#### 资源层面的错位
HZC 本身就给了：

- p1 更靠下
- p2 居中
- p3 更靠上

#### 动画层面的收束
脚本又让它们：

- 同时淡入
- 从不同旋转角度收束到 `0°`
- 从放大状态逐渐恢复到正常比例

因此最终效果不是“单块图片转一圈”，而是：

> 三个本来就略有上下错位的碎片，在放大 + 旋转的状态下进入，然后一起收束到正常位置与正常比例。

### 7.2 主体层 `logo_favo`
在 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py:410)～[`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py:412) 中：

- `MotionMoveZ(750 -> 1000, 1800ms)`
- `MotionAlpha(0 -> 255, 1800ms)`

由于主体层的 HZC 偏移是 `(463,260)`，它原本就不是以图片几何中心贴在 `(640,360)` 的方式构图；而是：

- 素材区域先放在一个设计好的左上角偏移上
- 然后以脚本中的 OP / pivot 参与 Z 轴推进

因此更准确的理解是：

> 主体 LOGO 在其资源头定义好的版面位置上，做“向镜头靠近式”的推进与淡入。

### 7.3 前景层 `logo_favo_view`
在 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py:414)～[`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py:418) 中：

- `MotionMoveZ(750 -> 1000)`
- `MotionY(view_base_y + 50 -> view_base_y)`
- `MotionAlpha(0 -> 255)`

这里的关键是：

- `view_base_y` 已经不再是手工写死的 `360` 或 `410`
- 而是从 HZC 偏移 `(539,406)` 与图片高度换算出来的基础位置

所以这个前景层的正确理解应为：

> 先以资源头自带的位置为静态基准，再从其下方 50 像素滑回该位置，同时完成淡入与 Z 推进。

这比之前“直接把它摆在中心附近滑回中心”更接近原设计。

---

## 8. `PrimSetOP` 与 HZC 偏移的关系

这一点非常关键。

### 8.1 `PrimSetOP` 不是单纯的屏幕坐标
从 [`prim_set_op()`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:204) 和 [`gpu_prim.rs`](rfvp-0.3.0/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:559) 可知：

- `PrimSetOP` 写入的是 `opx/opy`
- 当属性位开启时，这些值会参与 pivot 计算
- 它更像“变换参考点”而不只是纯位置

### 8.2 HZC 偏移决定素材矩形放在哪里
而 HZC 内部偏移：

- 更像图像在原始设计稿/画布中的天然落点
- 决定“这张素材矩形最初应该从哪开始”

因此二者叠加起来才更合理：

- **HZC 偏移**：定义素材静态落点
- **脚本 OP / motion 参数**：定义围绕何处做动画和变换

这也是为什么现在要把 HZC 偏移纳入到 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 的初始定位中，而不是手工写死居中。

---

## 9. 当前 `logo-test.py` 的含义

当前测试脚本里的位置逻辑可概括为：

1. 从图片文件读取真实尺寸
2. 使用 [`LOGO_HZC_TOP_LEFT`](fvp_analysis/result/hcbtool_test/logo-test.py:67) 给出的 left/top
3. 通过 [`anchor_center_from_top_left()`](fvp_analysis/result/hcbtool_test/logo-test.py:194) 换算出中心坐标
4. 把这个中心坐标作为复现脚本的初始锚点
5. 再叠加：
   - alpha 动画
   - rotation 动画
   - scale 动画
   - z 动画
   - view 层额外的 Y 滑入

所以它的本质不是“原封不动模拟 FVP 内部渲染器”，而是：

> **把 HZC 自带偏移纳入初始布局，再在其上叠加已逆向出的脚本运动参数。**

---

## 10. 更细的逐层说明

### `logo_bg`
- HZC 偏移：`(0,0)`
- 作用：背景底板
- 动作：基本静止，后续淡出

### `logo_favo`
- HZC 偏移：`(463,260)`
- 脚本 OP：`(640,360)`
- 动作：`Z 750 -> 1000`，`Alpha 0 -> 255`
- 解读：主体 LOGO 在其资源布局位置上完成靠近 + 显现

### `logo_favo_view`
- HZC 偏移：`(539,406)`
- 脚本 OP：`(640,360)`
- 动作：`Y +50 -> 0`、`Z 750 -> 1000`、`Alpha 0 -> 255`
- 解读：前景/观察窗层从下方微移入场，同时推进与淡入

### `logo_favo_view_p1`
- HZC 偏移：`(618,409)`
- 动作：`R 3600 -> 0`、`Scale 5000 -> 1000`、`Alpha 0 -> 255`
- 解读：偏下分片，从放大 + 正向整周旋转状态收束到正常

### `logo_favo_view_p2`
- HZC 偏移：`(618,404)`
- 动作：同 p1
- 解读：中间分片，与 p1/p3 形成层间错位

### `logo_favo_view_p3`
- HZC 偏移：`(618,400)`
- 动作：`R -3600 -> 0`、`Scale 5000 -> 1000`、`Alpha 0 -> 255`
- 解读：偏上分片，从反向整周旋转状态收束到正常

---

## 11. 总结

把 HZC 内部偏移正式纳入之后，这套 LOGO 演出的理解比之前更完整：

- 不是简单地把所有图层“居中摆好再做动画”
- 而是每张图原本就带有资源头里定义好的版面落点
- 脚本中的 `PrimSetOP` 和后续 motion syscall，则是在这些版面落点之上定义变换参考点与运动过程

因此这套演出的正确理解应该是：

> **资源层先决定每个 logo 图块在画面中的天然基准位置，脚本层再围绕这些基准位置施加淡入、旋转、缩放、滑入与纵深变化。**

这也是为什么 [`logo-test.py`](fvp_analysis/result/hcbtool_test/logo-test.py) 比纯手工居中版更接近原始表现。