# FVP / Sakura 中 z 坐标与实际显示大小的关系分析

## 1. 结论

FVP 中需要区分两种 z：

1. **prim z**：某个 prim 自身的深度基准，由 [`PrimSetZ(id, z)`](../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:780) 设置。
2. **全局 V3D z**：所有启用 3D 投影的 prim 共用的全局投影状态，由 [`V3DSet(x, y, z)`](syscall语义数据库/syscall含义详解/31_V3D.md:68) 或 [`V3DMotion(...)`](syscall语义数据库/syscall含义详解/31_V3D.md:108) 设置。

对启用虚拟 3D 投影的 prim，当前参考渲染器使用：

```text
depth   = prim_z - v3d_z
scale_x = factor_x / depth
scale_y = factor_y / depth
```

实现见 [`gpu_prim.rs`](../reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:288-316)。

因此，图像大小由 **相对深度 `prim_z - v3d_z`** 决定，而不是由某一个 z 值单独决定。

在 `factor_x = factor_y = 1000` 且 `v3d_z = 0` 时：

```text
显示倍率 = 1000 / prim_z
```

| prim z | 显示倍率 |
|---:|---:|
| 500 | 2.0 倍 |
| 1000 | 1.0 倍 |
| 2000 | 0.5 倍 |
| 4000 | 0.25 倍 |

所以，在 V3D z 固定为 0 时：

> **prim z 越小，图像越大；prim z 越大，图像越小。**

如果固定 prim z、只改变 V3D z，则方向相反：

> **V3D z 越接近 prim z，图像越大；V3D z 越远离 prim z，图像越小。**

---

## 2. prim z 的含义

图片加载函数通常会在创建或装载 prim 后执行：

```lua
PrimSetZ(prim_id, z)
```

例如 [`f_0005074C()`](hcbtool_test/Sakura_hcb_ir/Sakura/f_0005074C.lua:105-115) 对背景 prim 186 设置 z。

根据 [`prim_set_z()`](../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:780-827)：

| z 参数 | 行为 |
|---|---|
| 整数 | 限制到 `100..10000`，写入 prim.z，开启 `attr & 0x04` |
| 浮点数 | 不修改原有 prim.z，但开启 `attr & 0x04` |
| `nil` 或其它类型 | 清除 `attr & 0x04`，退出 3D 投影路径 |

所以整数形式的 [`PrimSetZ()`](../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:800-805) 同时完成两件事：

1. 设置 prim 的深度基准；
2. 让 prim 进入虚拟 3D 变换路径。

`PrimSetZ(id, nil)` 不是把 z 设置为 0，而是关闭该 prim 的 3D 投影属性。

prim z 主要决定：

- 图元相对于全局 V3D 状态的深度差；
- 图元对 V3D z 运动的敏感程度；
- 同一镜头运动中不同图层的缩放幅度；
- 多层场景中的景深关系。

它不应直接命名为“图片大小参数”或“屏幕像素坐标”。

---

## 3. 全局 V3D z 的含义

主舞台镜头函数 [`f_000526A3()`](hcbtool_test/Sakura_hcb_ir/Sakura/f_000526A3.lua:223-236) 最终执行：

```lua
V3DMotion(dst_x, dst_y, dst_z, duration, type, reverse)
```

其中 `dst_z` 是全局 V3D z，不是某一张背景图片的 prim z。

全局 V3D 状态由 [`V3dMotionContainer`](../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/v3d.rs:151-157) 保存。它维护当前坐标、目标坐标、运动时长、运动类型和暂停状态。

典型剧情调用可以看到：

```lua
f_000526A3(0, 200, 300, 900, ...)
f_000526A3(0, 0, 300, 1000, ...)
f_000526A3(0, -30, 300, 1000, ...)
```

例如 [`f_000A2981.lua`](hcbtool_test/Sakura_hcb_ir/Sakura/f_000A2981.lua:1325-1337) 中的 `300` 是全局 V3D z，而不是背景 prim 的 z。

它会同时影响所有已经开启 `attr & 0x04` 的 prim，但每个 prim 的变化幅度不同，因为每个 prim 的 prim z 不同。

---

## 4. 普通 2D 路径与 3D 路径

### 4.1 普通 2D 路径

当 prim 没有设置 `attr & 0x04` 时，渲染器在 [`gpu_prim.rs`](../reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:317-325) 中使用：

```rust
scale_x = factor_x / 1000.0;
scale_y = factor_y / 1000.0;
```

此时 z 不参与大小计算。

例如：

| factor | 2D 显示倍率 |
|---:|---:|
| 500 | 0.5 倍 |
| 1000 | 1.0 倍 |
| 1500 | 1.5 倍 |
| 2000 | 2.0 倍 |

### 4.2 虚拟 3D 路径

当 `attr & 0x04` 已设置时，使用：

```text
depth   = prim_z - v3d_z
scale_x = factor_x / depth
scale_y = factor_y / depth
```

因此分析 z 之前，必须先确认 prim 是否启用了 `attr & 0x04`。

如果没有启用，修改 z 可能不会改变图像大小；如果已启用，才需要计算 `prim_z - v3d_z`。

---

## 5. prim z 与显示大小

假设：

```text
v3d_z = 0
factor_x = factor_y = 1000
其它缩放 = 1.0
```

此时：

```text
显示倍率 = 1000 / prim_z
```

| prim z | 显示倍率 | 视觉效果 |
|---:|---:|---|
| 100 | 10.0 倍 | 极大 |
| 200 | 5.0 倍 | 很大 |
| 500 | 2.0 倍 | 放大 |
| 800 | 1.25 倍 | 略大 |
| 1000 | 1.0 倍 | 基准 |
| 1500 | 0.667 倍 | 缩小 |
| 2000 | 0.5 倍 | 半尺寸 |
| 4000 | 0.25 倍 | 很小 |
| 10000 | 0.1 倍 | 极小 |

这解释了为什么很多初始化函数使用 `z=1000`：在默认 `v3d_z=0`、`factor=1000` 时，它接近 1 倍显示。

但 `1000` 不是固定的像素大小，也不是图片尺寸参数，而是常用的投影深度基准。

---

## 6. V3D z 与显示大小

假设：

```text
prim_z = 1000
factor_x = factor_y = 1000
其它缩放 = 1.0
```

此时：

```text
显示倍率 = 1000 / (1000 - v3d_z)
```

| V3D z | 相对深度 | 显示倍率 |
|---:|---:|---:|
| -1000 | 2000 | 0.5 倍 |
| -500 | 1500 | 0.667 倍 |
| 0 | 1000 | 1.0 倍 |
| 200 | 800 | 1.25 倍 |
| 300 | 700 | 1.43 倍 |
| 500 | 500 | 2.0 倍 |
| 800 | 200 | 5.0 倍 |
| 900 | 100 | 10.0 倍 |

因此，主舞台把 V3D z 从 0 推向正值时，通常表现为镜头推进和场景放大；向负值运动时，通常表现为镜头拉远和场景缩小。

---

## 7. 为什么会产生景深效果

假设同一次镜头运动把全局 V3D z 从 0 移动到 300：

| 图层 | prim z | 初始倍率 | 结束倍率 |
|---|---:|---:|---:|
| 近景 | 500 | 2.00 | 5.00 |
| 中景 | 1000 | 1.00 | 1.43 |
| 远景 | 2000 | 0.50 | 0.59 |
| 更远景 | 4000 | 0.25 | 0.27 |

近景层的相对深度较小，对同一段 V3D z 运动更加敏感；远景层的相对深度较大，变化更加缓慢。

因此：

> **不同 prim z 的图层共享同一个 V3D z 运动，但会产生不同的缩放幅度，这就是 FVP 多层景深和推拉镜头的来源。**

---

## 8. 图片加载函数中的最终大小

图片初始化通常组合使用：

```lua
PrimSetOP(id, opx, opy)
PrimSetXY(id, x, y)
PrimSetZ(id, z)
PrimSetRS(id, rotation, scale)
PrimSetAlpha(id, alpha)
```

以 [`f_0005074C()`](hcbtool_test/Sakura_hcb_ir/Sakura/f_0005074C.lua:88-118) 为例：

- `PrimSetOP` 设置 pivot / 锚点；
- `PrimSetXY` 设置相对父节点的局部位置；
- `PrimSetZ` 设置 prim 深度并开启 3D 投影；
- `PrimSetRS` 设置旋转和显式缩放；
- `PrimSetAlpha` 设置透明度。

在 3D 路径中，最终尺寸可近似写为：

```text
最终宽度
≈ 原始宽度
× RS_scale / 1000
× factor_x / (prim_z - v3d_z)

最终高度
≈ 原始高度
× RS_scale / 1000
× factor_y / (prim_z - v3d_z)
```

因此，z 只是影响最终大小的一个因素，还必须检查：

- [`PrimSetRS()`](syscall语义数据库/syscall含义详解/21_Prim.md:474)；
- [`PrimSetRS2()`](syscall语义数据库/syscall含义详解/21_Prim.md:509)；
- [`PrimSetWH()`](syscall语义数据库/syscall含义详解/21_Prim.md:760)；
- [`PrimSetOP()`](syscall语义数据库/syscall含义详解/21_Prim.md:420)；
- `PrimSetXY()`；
- 父 group 的变换；
- prim 的 factor_x / factor_y。

### 8.1 z 与 RS 缩放的补偿

例如：

```lua
PrimSetRS(186, 0, 2000)
PrimSetZ(186, 2000)
```

在 `v3d_z=0`、`factor=1000` 时：

```text
RS 缩放       = 2000 / 1000 = 2.0
z 投影缩放     = 1000 / 2000 = 0.5
最终倍率       = 2.0 × 0.5 = 1.0
```

所以不能看到 `z=2000` 就直接断言图像变成半尺寸。脚本可能使用 RS scale 或父组变换进行补偿。

### 8.2 z 与 WH 的区别

[`PrimSetWH(id,w,h)`](syscall语义数据库/syscall含义详解/21_Prim.md:760) 改变图像采样/绘制区域的宽高；z 改变的是 3D 相对深度及其投影倍率。

二者都可能影响最终尺寸，但机制不同：

```text
PrimSetWH -> 改变图像区域或基准宽高
PrimSetRS -> 改变显式缩放
PrimSetZ  -> 改变相对深度和 3D 投影缩放
```

---

## 9. pivot 与 XY 对视觉结果的影响

### 9.1 pivot

[`PrimSetOP(id,opx,opy)`](syscall语义数据库/syscall含义详解/21_Prim.md:420) 设置缩放和旋转的参考点。

- pivot 在画面中心：z 变化通常像镜头推近或拉远；
- pivot 在图像中心：图像围绕自身中心缩放；
- pivot 在左上角：缩放时会伴随明显的右下方向位移。

因此，z 改变后看到的位置变化，不一定是 z 直接修改了 XY，也可能是图像相对于 pivot 的偏移被整体缩放。

### 9.2 XY

[`PrimSetXY(id,x,y)`](syscall语义数据库/syscall含义详解/21_Prim.md:534) 设置相对父节点的局部位置。它不直接改变 z，但 z 引起的整体缩放会同时放大或缩小 XY 到 pivot 的距离。

---

## 10. z 与遮挡顺序

z 有深度含义，但不能简单等同于普通 2D 绘制顺序。

“谁盖住谁”还可能受到以下因素影响：

1. prim 树和父子 group 结构；
2. 绘制遍历顺序；
3. alpha；
4. blend 模式；
5. 是否启用 `attr & 0x04`；
6. 具体渲染后端。

因此应区分：

```text
z 对大小的作用 -> 主要由 prim_z - v3d_z 决定
z 对透视的作用 -> 由 3D 投影路径决定
z 对遮挡的作用 -> 还需结合 prim 树和后端验证
```

---

## 11. 危险边界

### 11.1 `prim_z` 接近 `v3d_z`

当：

```text
prim_z - v3d_z ≈ 0
```

理论缩放倍率会非常大。当前渲染器使用保护：

```rust
if depth.abs() < 1e-3 {
    depth = 1.0;
}
```

见 [`gpu_prim.rs`](../reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:302-305)。

虽然可以避免除零，但画面仍可能突然巨大。镜头和新场景注入时，应避免 V3D z 接近主要 prim 的 z。

### 11.2 `prim_z < v3d_z`

此时 depth 为负，`scale_x` 和 `scale_y` 也会变成负值，可能导致：

- X/Y 方向翻转；
- 镜像；
- 位置反向；
- 裁剪或显示异常。

所以不能把超过 prim z 理解为“继续正常放大”，而应视为负深度特殊区域。

---

## 12. 对新场景注入的建议

### 12.1 普通 2D 图片

如果不需要景深，不要让 prim 进入 3D 投影路径，或使用：

```lua
PrimSetZ(id, nil)
```

此时大小主要由：

```text
factor / 1000
RS scale / 1000
PrimSetWH 的宽高
```

决定。

### 12.2 需要景深的图片

可以给不同层设置不同的 prim z：

```text
近景：500..800
中景：1000..2000
远景：3000..5000
```

再使用统一的 [`V3DMotion()`](syscall语义数据库/syscall含义详解/31_V3D.md:108) 改变全局 V3D z。

### 12.3 安全条件

建议保证：

```text
100 <= prim_z <= 10000
v3d_z < 主要 3D prim 的 prim_z
prim_z - v3d_z 不要接近 0
```

### 12.4 分析时必须记录的参数

只记录一个 z 值无法还原最终大小。至少应记录：

```text
prim_z
v3d_z
factor_x / factor_y
RS scale
WH
pivot
父 group 变换
attr 是否包含 0x04
```

---

## 13. 建议实验

### 实验 A：只改变 prim z

固定：

```text
V3D = (0,0,0)
factor = 1000
RS scale = 1000
```

测试 `prim_z = 500, 1000, 2000, 4000`，预期倍率为：

```text
2.00, 1.00, 0.50, 0.25
```

### 实验 B：只改变 V3D z

固定：

```text
prim_z = 1000
factor = 1000
RS scale = 1000
```

测试 `v3d_z = -500, 0, 200, 500, 800`，预期倍率约为：

```text
0.667, 1.000, 1.250, 2.000, 5.000
```

### 实验 C：验证景深

准备两个启用 3D 投影的 prim：

```text
prim A z = 500
prim B z = 2000
```

将全局 V3D z 从 0 移动到 300。预期：

```text
A: 2.00 倍 -> 5.00 倍
B: 0.50 倍 -> 0.59 倍
```

### 实验 D：验证 3D 属性开关

1. 调用 [`PrimSetZ(id,1000)`](syscall语义数据库/syscall含义详解/21_Prim.md:556)；
2. 改变 V3D z，观察大小；
3. 调用 [`PrimSetZ(id,nil)`](syscall语义数据库/syscall含义详解/21_Prim.md:556)；
4. 再次改变 V3D z；
5. 比较两次结果。

预期是：整数 z 开启 3D 路径后会随 V3D z 改变大小，`nil` 清除属性后回到普通 2D 路径。

---

## 14. 最终结论

1. prim z 是单个图元的投影深度基准。
2. 全局 V3D z 是所有 3D prim 共用的投影状态。
3. 3D 路径中，`depth = prim_z - v3d_z`。
4. 显示大小与相对深度成反比。
5. 固定 V3D z 时，prim z 越大，图像越小。
6. 固定 prim z 时，V3D z 越接近 prim z，图像越大。
7. `prim_z=1000、v3d_z=0、factor=1000` 是常见的约 1 倍投影基准。
8. 主舞台把 V3D z 从 0 推向正值时，通常表现为推近和放大；向负值运动时，通常表现为拉远和缩小。
9. 普通 2D 路径不使用 `prim_z-v3d_z`，大小主要由 factor 和 RS scale 决定。
10. 最终大小还受到 WH、pivot、父组变换和图像尺寸影响。
11. z 与遮挡顺序不完全等价，遮挡还要结合 prim 树、alpha、blend 和渲染后端。
12. 注入时应避免 `prim_z` 接近或小于 `v3d_z`。

> **一句话概括：FVP 虚拟 3D 路径中的图像大小由 `prim_z - v3d_z` 决定，并与这个相对深度成反比；prim z 是图元深度，V3D z 是全局镜头/投影状态。**

## 15. 证据索引

- [`gpu_prim.rs`](../reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:288-326)
- [`graph.rs`](../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:780-827)
- [`v3d.rs`](../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/v3d.rs:151-394)
- [`31_V3D.md`](syscall语义数据库/syscall含义详解/31_V3D.md:1)
- [`21_Prim.md`](syscall语义数据库/syscall含义详解/21_Prim.md:474-583)
- [`f_000526A3.lua`](hcbtool_test/Sakura_hcb_ir/Sakura/f_000526A3.lua:1)
- [`f_0005074C.lua`](hcbtool_test/Sakura_hcb_ir/Sakura/f_0005074C.lua:1)
- [`f_00074DA5.lua`](hcbtool_test/Sakura_hcb_ir/Sakura/f_00074DA5.lua:1)
- [`f_000A2981.lua`](hcbtool_test/Sakura_hcb_ir/Sakura/f_000A2981.lua:1)
- [`f_000526A3详细解析.md`](hcbtool/f_000526A3详细解析.md:1)
- [`BGimageLoading函数共性总结.md`](hcbtool_test/BGimageLoading函数共性总结.md:1)
