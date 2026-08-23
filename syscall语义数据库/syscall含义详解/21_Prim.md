# Prim 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:101)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3784-4805)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:91-111) 与 rfvp 参考实现，`Prim` 分组当前包含 21 个 syscall：

1. `PrimExitGroup`
2. `PrimGroupIn`
3. `PrimGroupMove`
4. `PrimGroupOut`
5. `PrimHit`
6. `PrimSetAlpha`
7. `PrimSetBlend`
8. `PrimSetClip`
9. `PrimSetDraw`
10. `PrimSetNull`
11. `PrimSetOP`
12. `PrimSetRS`
13. `PrimSetRS2`
14. `PrimSetSnow`
15. `PrimSetSprt`
16. `PrimSetText`
17. `PrimSetTile`
18. `PrimSetUV`
19. `PrimSetWH`
20. `PrimSetXY`
21. `PrimSetZ`

其中：

- `PrimExitGroup`、`PrimGroupIn`、`PrimGroupMove`、`PrimGroupOut`、`PrimHit`、`PrimSetAlpha`、`PrimSetBlend`、`PrimSetDraw`、`PrimSetNull`、`PrimSetOP`、`PrimSetRS`、`PrimSetRS2`、`PrimSetSnow`、`PrimSetSprt`、`PrimSetText`、`PrimSetTile`、`PrimSetUV`、`PrimSetWH`、`PrimSetXY`、`PrimSetZ` 在 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:93-112) 中有显式规格，并在 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:569-590) 中注册；
- `PrimSetClip` 没有进入现代 `generated.rs` 的显式注册段，而是作为 legacy 兼容接口在 [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:380-397) 与 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:710-712) 中注册。

综合源码与已有 HCB 研究，`Prim` 分组可以概括为：

> **围绕 FVP 图元（primitive）的层级树组织、显示类型初始化、资源绑定、位置/尺寸/变换、透明度/混合/绘制开关、命中检测以及兼容裁剪设置的一组底层显示接口。**

---

## 2. Prim 的基础模型

### 2.1 Prim 是固定槽位的显示对象

[`PrimManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:304-345) 初始化时分配 4096 个 prim 槽位，编号范围为 `0..=4095`：

- `0` 通常作为根 group；
- 普通脚本对象通常使用 `1..=4095`；
- 大多数 Prim syscall 对普通目标限制为 `1..=4095`；
- 部分树操作允许父节点为 `0`；
- `PrimExitGroup` 允许把根设置为 `0..=4095`。

### 2.2 Prim 类型

[`PrimType`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:8-27) 当前包含：

| 类型 | 数值 | 作用 |
|---|---:|---|
| `PrimTypeNone` | 0 | 空 / 未使用 prim |
| `PrimTypeGroup` | 1 | 层级容器，不直接绘制 |
| `PrimTypeTile` | 2 | 纯色矩形 |
| `PrimTypeSprt` | 4 | 图像 / 纹理 sprite |
| `PrimTypeText` | 5 | 文本纹理占位对象 |
| `PrimTypeSnow` | 7 | 雪花粒子专用对象 |

### 2.3 Prim 的主要字段

[`Prim`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:32-61) 保存的关键状态包括：

- `typ`：prim 类型；
- `draw_flag`：是否参与绘制与树遍历；
- `alpha`：透明度；
- `blend`：混合模式字段；
- `parent / prev_sibling / next_sibling`：树关系；
- `x / y`：局部位置；
- `w / h`：绘制区域或矩形尺寸；
- `u / v`：纹理采样起点；
- `opx / opy`：OP pivot / 锚点；
- `rotation`：旋转值；
- `factor_x / factor_y`：缩放因子；
- `z`：Z / 深度相关值；
- `texture_id`：sprite 或 snow 使用的纹理 / 雪花 motion 槽；
- `tile`：tile prim 使用的颜色表槽位；
- `text_index`：text prim 对应的文本槽位；
- `attr`：采样矩形、pivot、投影模式和 dirty 等属性位。

### 2.4 属性位的已知语义

当前实现中可以较稳定确认：

- `attr & 0x01`：使用 prim 自身的 `u/v/w/h` 采样矩形；未设置时通常使用整张纹理；
- `attr & 0x02`：启用 `opx/opy` 作为 pivot；
- `attr & 0x04`：启用与虚拟 3D / 深度投影相关的变换路径；
- `attr & 0x40`：dirty / 状态发生变化，需要渲染器重新处理。

证据来自 [`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:280-319,532-563) 与 [`prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:487-525)。

---

## 3. 分组边界与常见调用链

### 3.1 Prim 与 Graph 的分工

[`GraphLoad`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:1840) / [`GraphRGB`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:1883) 更偏向资源槽位：

- `GraphLoad` 把图像装入 graph / texture 缓存；
- `GraphRGB` 修改图像色调。

而 `PrimSetSprt`、`PrimSetText`、`PrimSetTile` 等负责把资源绑定到具体显示对象。已有研究明确指出，单独 `GraphLoad` 不一定会上屏，通常还需要 `PrimSetSprt` 或其他 prim 初始化接口：[`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:393-400)。

### 3.2 Prim 与 Motion 的分工

`PrimSetXY`、`PrimSetRS`、`PrimSetZ` 等是立即写入属性的接口；`MotionMove`、`MotionMoveR`、`MotionMoveS2`、`MotionMoveZ` 则是在这些属性上注册时间型动画。已有立绘与 LOGO 分析中，常见顺序是：

1. 创建或绑定 prim；
2. 设置 OP、XY、Z、RS、Alpha、Blend；
3. 再使用 Motion syscall 做淡入、移动、旋转、缩放或深度动画。

例如 [`BGimageLoading函数共性总结.md`](fvp_analysis/result/hcbtool_test/BGimageLoading函数共性总结.md:237-243) 与 [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:40-63)。

### 3.3 常见显示对象初始化链

#### Sprite 图像

```text
GraphLoad(graph_id, path)
PrimSetSprt(prim_id, graph_id, x, y)
PrimSetUV(prim_id, u, v)       // 可选
PrimSetWH(prim_id, w, h)       // 可选
PrimSetOP(prim_id, opx, opy)   // 可选
PrimSetZ(prim_id, z)
PrimSetAlpha(prim_id, alpha)
PrimSetBlend(prim_id, blend)
PrimGroupIn(prim_id, parent_id)
```

#### 文本对象

```text
TextBuff / TextPrint 等文本接口
PrimSetText(prim_id, text_slot, x, y)
PrimGroupIn(prim_id, parent_id)
```

#### 纯色矩形

```text
PrimSetTile(prim_id, color_slot, x, y, w, h)
PrimSetAlpha(prim_id, alpha)
PrimGroupIn(prim_id, parent_id)
```

---

## 4. 层级树相关 syscall

## 4.1 `PrimExitGroup`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3787)
- **签名**：`PrimExitGroup(root_id)`
- **返回值**：`Nil`

### 入参语义

- `root_id`
  - 类型：`Int`
  - 有效范围：`0..=4095`
  - 含义：新的场景根 prim / 渲染遍历根。

### 具体作用

[`prim_exit_group()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:9-29) 同时更新：

- `GameData` 保存的 prim root；
- [`PrimManager::custom_root_prim_id`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:322-332)。

它不是“退出 group”的销毁操作；名称容易造成误解。更准确的解释是：

> **把渲染 / 场景遍历的根 prim 切换到指定槽位。**

### 证据与限制

当前 rfvp 明确把它作为 root 设置接口处理；原引擎名称中 `ExitGroup` 的历史命名来源仍需更多版本样本验证。

---

## 4.2 `PrimGroupIn`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3827)
- **签名**：`PrimGroupIn(child_id, parent_id)`
- **返回值**：`Nil`

### 入参语义

- `child_id`
  - 类型：`Int`
  - 有效范围：`1..=4095`
  - 含义：要加入层级树的子 prim。
- `parent_id`
  - 类型：`Int`
  - 有效范围：`0..=4095`
  - 含义：目标父 prim；必要时会被初始化为 group。

### 具体作用

[`prim_group_in()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:33-50) 最终调用 [`set_prim_group_in()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:434-484)：

- 把父节点初始化为 `PrimTypeGroup`；
- 先从原父节点和兄弟链中解绑 child；
- 把 child 追加到父节点子链表末尾；
- 更新 parent / prev_sibling / next_sibling / first_child / last_child；
- 标记 child dirty。

### 结论

> `PrimGroupIn` 是 **把一个 prim 插入另一个 prim 的子节点列表** 的接口。

已有图像加载链通常是 `PrimSetSprt` 后再用 `PrimGroupIn` 接入 group：[`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:357-360)。

---

## 4.3 `PrimGroupMove`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3871)
- **签名**：`PrimGroupMove(reference_id, target_id)`
- **返回值**：`Nil`

### 入参语义

- `reference_id`
  - 类型：`Int`
  - 有效范围：`1..=4095`
  - 含义：目标插入位置的参考 sibling。
- `target_id`
  - 类型：`Int`
  - 有效范围：`1..=4095`
  - 含义：要移动的 prim。

### 具体作用

[`prim_group_move()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:53-67) 调用 [`prim_move()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:405-431)：

1. 从原父节点解绑 target；
2. 读取 reference 所在的父节点；
3. 把 target 插入 reference 后面；
4. 修正兄弟链和父节点的 last child。

### 结论

> `PrimGroupMove` 是 **在同一父节点下调整 prim 绘制 / 遍历顺序** 的接口。

`reference_id` 不是新父节点，而是 target 要插入其后的参考节点。

---

## 4.4 `PrimGroupOut`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3916)
- **签名**：`PrimGroupOut(id)`
- **返回值**：`Nil`

### 入参语义

- `id`
  - 类型：`Int`
  - 有效范围：`1..=4095`
  - 含义：要从层级树中移除的 prim。

### 具体作用

[`prim_group_out()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:70-79) 调用 [`unlink_prim()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:373-403)：

- 从 parent 的 child 链表中摘除 prim；
- 修正前后 sibling；
- 清除 prim 自身的 parent / sibling 指针；
- 不释放 prim 槽位，也不重置其显示属性。

### 结论

> `PrimGroupOut` 是 **从场景树摘除 prim，但保留 prim 对象和属性状态** 的接口。

若需要真正重置槽位，应使用 `PrimSetNull`。

---

## 5. 命中检测 syscall

## 5.1 `PrimHit`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3955)
- **签名**：`PrimHit(id, flag)`
- **返回值**：按 [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3970) 记录为 `Nil`；但当前实现实际返回 `True/Nil`，数据库返回类型需要后续修正。

### 入参语义

- `id`
  - 类型：`Int`
  - 有效范围：`1..=4095`
  - 含义：要检测的 prim。
- `flag`
  - 类型：`Variant`
  - 含义：是否忽略目标 prim 自身的 `draw_flag` 限制。
  - `Nil`：若 prim 不可绘制则直接不命中；
  - 非 `Nil`：允许继续做几何 / 像素命中测试，即使目标 prim 的 draw flag 为关闭。

这里按参数“是否为 Nil”判断，不是按整数 `0/1` 真值判断：[`prim_hit()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:845-857)。

### 具体作用

[`MotionManager::prim_hit()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:692-730) 使用当前输入系统的：

- 光标是否在窗口内；
- 光标 X；
- 光标 Y。

然后根据 prim 类型检测：

- `Group`：递归检查子节点；
- `Tile`：检查光标是否位于矩形区域内，且 alpha 不为 0；
- `Sprt`：先检查矩形范围，再根据 UV 映射检查纹理像素 alpha 是否非 0；
- 其他类型：当前实现返回未命中。

父节点的坐标会累加到子节点位置；不可绘制的祖先会导致命中失败：[`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:583-690)。

### 结论

> `PrimHit` 是 **基于当前光标位置对 prim 做几何 / 透明像素命中检测的输入查询接口**。

### 重要数据库差异

当前实现明确返回：

- 命中 -> `True`
- 未命中 -> `Nil`

因此 `syscall_spec.json` 中该条目的 `return_type = Nil` 与实现不一致，本文按源码记录实际语义，并把数据库字段差异列为待修正项。

---

## 6. 基础显示属性 syscall

## 6.1 `PrimSetAlpha`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4000)
- **签名**：`PrimSetAlpha(id, alpha)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`，目标 prim。
- `alpha`：`Int`，范围 `0..=255`，透明度。
  - `0`：完全透明；
  - `255`：完全不透明；
  - 中间值：半透明。

### 具体作用

调用 [`PrimManager::prim_set_alpha()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:527-530) 写入 prim alpha。渲染阶段把 alpha 转换为颜色的透明通道：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:556-557)。

### 结论

> `PrimSetAlpha` 是 **prim 透明度设置接口**，也是淡入淡出 motion 的最终属性落点。

已有演出样例中常用 `PrimSetAlpha(..., 0)` 先隐藏对象，再通过 `MotionAlpha` 做入场：[`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:40-63)。

---

## 6.2 `PrimSetBlend`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4045)
- **签名**：`PrimSetBlend(id, blend)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，当前实现允许 `0..=4095`。
- `blend`：`Int`，范围 `0..=1`。
  - `0`：普通 / 逆源颜色相关混合模式；
  - `1`：加法混合模式。

该语义来自 [`graph.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1170-1180) 的原引擎注释与 [`PrimManager::prim_set_blend()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:532-535)。

### 当前实现限制

当前 `gpu_prim.rs` 中没有检索到 `get_blend()` 参与 GPU pipeline 选择的代码，`blend` 主要作为 prim 状态保留。因此：

- syscall 层的 0/1 取值与历史混合模式含义有源码依据；
- 在当前 rfvp 渲染后端中，这个字段是否完整影响最终混合状态，仍需运行时或实机验证。

### 结论

> `PrimSetBlend` 是 **设置 prim 混合模式标志的接口**；其原引擎语义为普通 / 加法混合切换，但当前 rfvp 渲染消费链仍需补证。

---

## 6.3 `PrimSetDraw`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4130)
- **签名**：`PrimSetDraw(id, draw)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `draw`：`Int`，范围 `0..=1`。
  - `0`：关闭绘制 / 从树遍历中阻断；
  - `1`：允许绘制。

### 具体作用

[`PrimManager::prim_set_draw()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:537-540) 设置 `draw_flag`。渲染遍历开始时会检查该标志：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:460-462)。命中检测也会检查它，除非 `PrimHit` 的第二参数非 `Nil`：[`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:700-703)。

### 结论

> `PrimSetDraw` 是 **prim 可见 / 可遍历状态开关**。

它与 `PrimSetAlpha(id, 0)` 不完全等价：alpha 置零仍可能保留树遍历，而 `draw=0` 会直接阻断绘制链。

---

## 6.4 `PrimSetNull`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4175)
- **签名**：`PrimSetNull(id)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。

### 具体作用

[`prim_set_null()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:82-95) 把指定 prim 重新初始化为 `PrimTypeNone`。底层 [`prim_init_with_type()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:346-371) 会在类型改变时处理旧 group 的子节点，并重新标记状态。

### 结论

> `PrimSetNull` 是 **清空 / 回收 prim 槽位，使其回到可复用空状态的接口**。

与 `PrimGroupOut` 仅解绑不同，`PrimSetNull` 会改变 prim 类型并清理其作为显示对象的用途。

---

## 7. 变换与锚点 syscall

## 7.1 `PrimSetOP`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4214)
- **签名**：`PrimSetOP(id, opx, opy)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`，且当前实现只对 `PrimTypeSprt` 生效。
- `opx`：`Int | Nil`，X 方向 pivot / 锚点；`Nil` 表示本次不修改。
- `opy`：`Int | Nil`，Y 方向 pivot / 锚点；`Nil` 表示本次不修改。

### 具体作用

[`prim_set_op()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:204-242) 调用 [`prim_set_op_partial()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:500-525)：

- 只修改非 `Nil` 的 OP 分量；
- 至少有一个分量被修改时设置 `attr & 0x02`；
- 设置 dirty 位 `0x40`。

渲染阶段若 `attr & 0x02`，就使用 `opx/opy` 作为 pivot；否则使用图像资源的默认偏移 / UV 起点：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:557-576)。

已有 LOGO 研究也指出，`PrimSetOP(640,360)` 等值更接近旋转 / 缩放参考点，而不是普通屏幕坐标：[`logo演出详解.md`](fvp_analysis/result/hcbtool_test/logo演出详解.md:257-269)。

### 结论

> `PrimSetOP` 是 **设置 sprite 变换 pivot / 锚点的接口**，不是普通 XY 位置设置。

---

## 7.2 `PrimSetRS`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4265)
- **签名**：`PrimSetRS(id, rotation, scale)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `rotation`：`Int | Nil`。
  - 单位为十分之一度；
  - `0..3599` 对应 `0..359.9°`；
  - 由实现按 `rotation % 3600` 归一化；
  - `Nil` 或非整数表示保持当前旋转。
- `scale`：`Int | Nil`。
  - `Nil` 或非整数表示保持当前 X 缩放；
  - 当前实现有效接受范围为 `0..=10000`，越界回退到 `1000`；
  - 实际渲染按 `scale / 1000.0` 换算，因此 `1000` 为 100%，`2000` 为 200%。

### 具体作用

[`prim_set_rs()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:247-304) 设置：

- `rotation`；
- X/Y 相同的 uniform scale；
- dirty 位 `0x40`。

### 结论

> `PrimSetRS` 是 **设置 prim 旋转与等比缩放的立即变换接口**。

已有脚本样例中经常使用 `PrimSetRS(id, nil, scale)`，只调整缩放而保持旋转：[`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:448-500)。

---

## 7.3 `PrimSetRS2`

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4316)
- **签名**：`PrimSetRS2(id, rotation, scale_x, scale_y)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `rotation`：`Int | Nil`，单位十分之一度；`Nil` 保持当前值。
- `scale_x`：`Int | Nil`，X 缩放因子；`Nil` 保持当前值。
- `scale_y`：`Int | Nil`，Y 缩放因子；`Nil` 保持当前值。

缩放值当前实现接受 `0..=10000`，越界回退 `1000`；渲染按除以 `1000.0` 解释：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:317-319)。

### 具体作用

[`prim_set_rs2()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:307-375) 设置旋转及独立 X/Y 缩放，并标记 dirty。

### 结论

> `PrimSetRS2` 是 **设置旋转与非等比缩放的立即变换接口**。

---

## 7.4 `PrimSetXY`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4715)
- **签名**：`PrimSetXY(id, x, y)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `x`：`Int | Nil`，局部 X 坐标；`Nil` 保持当前 X。
- `y`：`Int | Nil`，局部 Y 坐标；`Nil` 保持当前 Y。

### 具体作用

[`prim_set_xy()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:672-721) 将坐标写入 prim 局部位置，并设置 dirty 位。渲染时父节点位置会累加到子节点：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:466-467,819-820)。

### 结论

> `PrimSetXY` 是 **设置 prim 相对父节点局部坐标的接口**，不是始终意义上的绝对屏幕坐标。

---

## 7.5 `PrimSetZ`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4766)
- **签名**：`PrimSetZ(id, z)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `z`：`Int | Float | Nil`。
  - `Int`：限制到 `100..=10000`，写入 prim 的 Z，并设置 attr `0x04`；
  - `Float`：当前实现不写入 prim.z，但仍设置 attr `0x04`；
  - `Nil` 或其他类型：清除 attr `0x04`；
  - 所有路径都会设置 dirty `0x40`。

### 具体作用

[`prim_set_z()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:780-827) 控制 prim 的深度 / 投影相关状态。当前渲染器在 `attr & 0x04` 时使用：

- prim Z 与 V3D Z 的差值作为 depth；
- X/Y 缩放因子参与深度投影；
- 虚拟画布中心和相机偏移参与最终模型矩阵：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:288-316)。

在普通非 3D 路径下，Z 的主要影响仍应理解为 prim 的深度 / 层级相关参数；具体绘制顺序在不同后端仍需运行时验证。

### 结论

> `PrimSetZ` 是 **设置 prim 深度并控制 Z / 3D 投影属性位的接口**。

已有演出分析中，`PrimSetZ(..., 1000)` 常和 `PrimSetOP`、`PrimSetRS`、`PrimSetAlpha` 一起构成图像图层初始化：[`f_00074DA5逐条反汇编对照.md`](fvp_analysis/result/hcbtool_test/f_00074DA5逐条反汇编对照.md:23-24,98-110)。

---

## 8. Prim 类型初始化与资源绑定 syscall

## 8.1 `PrimSetSprt`

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4430)
- **签名**：`PrimSetSprt(id, src_id, x, y)`
- **返回值**：`Nil`

### 入参语义

- `id`
  - 类型：`Int`
  - 有效范围：`1..=4095`
  - 含义：目标 sprite prim。
- `src_id`
  - 类型：`Int`
  - 当前实现有效范围：`-2..=4095`
  - `>=0`：graph / texture 槽位；
  - `-1`：原引擎注释中的特殊内置纹理；
  - `-2`：动态 movie-to-texture 绑定。
- `x / y`
  - 类型：`Int`，但当前实现非整数时默认 `0`；
  - 含义：初始局部位置。

### 具体作用

[`prim_set_sprt()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:444-512) 会：

1. 初始化目标为 `PrimTypeSprt`；
2. 设置默认 OP、alpha、blend、rotation、scale、UV、尺寸、Z；
3. 写入 `texture_id = src_id`；
4. 将 attr 初始化为 0。

原始注释对 `-1/-2` 的特殊来源有说明：[`graph.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1332-1353)。不过当前 `gpu_prim.rs` 明确处理的是普通 graph id 与 `-2` movie graph，`-1` 的完整内置纹理路径没有在当前渲染代码中找到，因此应保守标记为兼容 / 待验证语义。

### 结论

> `PrimSetSprt` 是 **创建 sprite prim 并把它绑定到图像资源的核心显示接口**。

已有研究明确将它视作“真正让 GraphLoad 资源上屏”的关键步骤：[`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:380-400)。

---

## 8.2 `PrimSetText`

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4487)
- **签名**：`PrimSetText(id, text_id, x, y)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`，目标文本 prim。
- `text_id`：`Int`，范围 `0..=31`，文本系统槽位。
- `x / y`：任意 `Variant`，整数有效时作为位置，否则默认 `0`。

### 具体作用

[`prim_set_text()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:515-567) 会：

- 初始化为 `PrimTypeText`；
- 设置 alpha=255、blend=0；
- 设置局部位置；
- 绑定 `text_index`；
- 清除大部分属性位。

渲染器将 text slot `0..=31` 映射到 graph `4064 + slot`：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:594-599)。

### 结论

> `PrimSetText` 是 **创建文本显示 prim，并把它绑定到文本系统槽位的接口**。

它不负责写入实际字符串；文本内容由 Text 组 syscall 管理。

---

## 8.3 `PrimSetTile`

- **参数个数**：6：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4544)
- **签名**：`PrimSetTile(id, tile_id, x, y, w, h)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `tile_id`：`Int | Nil`，有效范围 `-1..=255`；无效或缺省时使用默认 `255`。
- `x / y / w / h`：任意 `Variant`，整数有效时使用，否则默认 `0`。

`tile_id` 在当前渲染器中实际作为 [`ColorManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/color_manager.rs:1) 颜色表槽位使用，而不是外部图像纹理编号：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:753-764)。

### 具体作用

[`prim_set_tile()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:570-623) 会：

- 初始化为 `PrimTypeTile`；
- 设置 alpha=255、blend=0；
- 设置位置和宽高；
- 设置颜色表槽位。

渲染时它绘制一个由 `w/h` 决定尺寸的纯色矩形，颜色来自 `tile_id` 对应的 color entry：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:753-792)。

### 结论

> `PrimSetTile` 是 **创建纯色矩形 prim 的接口**。

常见用途包括 UI 面板、背景色块、遮罩和简单色彩覆盖。

---

## 8.4 `PrimSetSnow`

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4373)
- **签名**：`PrimSetSnow(id, mode, x, y)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`，目标 snow prim。
- `mode`：`Int`，只接受 `0` 或 `1`。
- `x / y`：任意 `Variant`，整数有效时作为初始局部位置，否则默认为 `0`。

### 具体作用

[`prim_set_snow()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:378-441) 会：

- 初始化为 `PrimTypeSnow`；
- 设置 OP、alpha、blend、rotation、scale、UV、尺寸、位置、Z；
- 将 attr 清零。

当前实现中 `mode` 只做 `0/1` 范围校验，函数体没有基于 `mode` 的进一步分支。因此：

- 可以确认它是雪花 prim 初始化时的模式参数；
- 不能仅凭当前 syscall 层确认 `0` / `1` 的业务名称；
- 雪花的纹理、数量、周期、速度、颜色等实际运动参数由独立的 snow motion 数据结构配置，见 [`SnowMotion::set_snow()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:488-531)。

渲染器会根据 snow motion 的 `texture_id`、flake 数量、变体和周期绘制雪花粒子：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:668-751)。

### 结论

> `PrimSetSnow` 是 **创建雪花粒子显示 prim 的接口**；`mode` 的具体业务差异目前仍待原版脚本或实机验证。

---

## 9. 纹理采样区域 syscall

## 9.1 `PrimSetUV`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4613)
- **签名**：`PrimSetUV(id, u, v)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `u`：`Int`，纹理采样起始 X。
- `v`：`Int`，纹理采样起始 Y。

### 具体作用

[`prim_set_uv()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:627-670) 写入 prim 的 UV 起点，并设置：

- attr `0x01`：使用矩形采样模式；
- dirty `0x40`。

单独设置 UV 只是确定采样矩形的左上角；采样宽高通常由 `PrimSetWH` 决定。渲染器使用 `u/v/w/h` 计算纹理 UV：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:532-555)。

### 结论

> `PrimSetUV` 是 **设置 sprite/text 纹理采样区域起点的接口**。

---

## 9.2 `PrimSetWH`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4664)
- **签名**：`PrimSetWH(id, w, h)`
- **返回值**：`Nil`

### 入参语义

- `id`：`Int`，范围 `1..=4095`。
- `w`：`Int | Nil`，采样 / 绘制宽度；`Nil` 保持当前值。
- `h`：`Int | Nil`，采样 / 绘制高度；`Nil` 保持当前值。

### 具体作用

[`prim_set_wh()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:724-777) 写入宽高，并设置：

- dirty `0x40`；
- attr `0x01`，启用矩形采样。

与 `PrimSetUV` 联合时，完整采样矩形为：

```text
(U, V, W, H)
```

### 结论

> `PrimSetWH` 是 **设置纹理采样矩形宽高 / sprite 显示区域的接口**。

它不同于 `PrimSetRS`：`WH` 改变的是采样矩形，`RS` 改变的是变换缩放。

---

## 10. legacy 兼容接口

## 10.1 `PrimSetClip`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4090)
- **签名**：`PrimSetClip(id)`
- **返回值**：`Nil`
- **实现类别**：legacy / 兼容接口。

### 入参语义

- `id`
  - 类型：`Int`
  - 当前 legacy 实现有效范围：`1..=1023`
  - 含义：目标 prim。

### 具体作用

[`prim_set_clip_legacy()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:383-397) 将目标 prim 的当前裁剪 / 采样矩形映射为整个虚拟屏幕：

- `UV = (0, 0)`；
- `WH = (screen_width, screen_height)`；
- 设置 dirty 位 `0x40`。

源码注释说明，原版有独立的 legacy clip rectangle；当前 rfvp 没有保留独立 clip 字段，因此使用 UV/WH 组合做效果等价映射：[`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:380-382)。

### 结论

> `PrimSetClip` 是 **旧版接口中将 prim 裁剪区域恢复为完整虚拟屏幕的兼容映射**。

它不是现代 Prim 组中用于设置任意裁剪矩形的完整通用接口；当前实现只实现了“重置到全屏区域”。

---

## 11. `Prim` 组整体语义

把 21 个 syscall 放在一起，可以看到以下职责结构：

1. **场景树根与层级关系**
   - `PrimExitGroup`
   - `PrimGroupIn`
   - `PrimGroupMove`
   - `PrimGroupOut`
2. **显示属性**
   - `PrimSetAlpha`
   - `PrimSetBlend`
   - `PrimSetDraw`
   - `PrimSetNull`
3. **变换与空间**
   - `PrimSetOP`
   - `PrimSetRS`
   - `PrimSetRS2`
   - `PrimSetXY`
   - `PrimSetZ`
4. **显示类型初始化与资源绑定**
   - `PrimSetSprt`
   - `PrimSetText`
   - `PrimSetTile`
   - `PrimSetSnow`
5. **纹理采样区域**
   - `PrimSetUV`
   - `PrimSetWH`
6. **输入交互**
   - `PrimHit`
7. **旧版兼容**
   - `PrimSetClip`

因此，`Prim` 分组的整体语义可以概括为：

> **FVP 显示系统的基础对象接口层：先创建并绑定 prim，再把 prim 接入层级树，随后配置采样区域、位置、锚点、缩放、旋转、深度、透明度和绘制状态，最后由渲染器按 prim 树完成显示。**

典型图像显示流程为：

```text
GraphLoad
  -> PrimSetSprt
  -> PrimSetUV / PrimSetWH（可选）
  -> PrimSetOP / PrimSetXY / PrimSetZ / PrimSetRS
  -> PrimSetAlpha / PrimSetBlend / PrimSetDraw
  -> PrimGroupIn
  -> Motion*（需要动态演出时）
```

---

## 12. 高置信度结论

以下结论比较稳：

- `Prim` 分组当前共有 21 个条目。
- Prim 槽位总数为 4096，普通对象主要使用 `1..=4095`，根节点可使用 `0`。
- `PrimGroupIn` 负责插入子节点，`PrimGroupOut` 负责解绑，`PrimGroupMove` 负责调整兄弟顺序。
- `PrimExitGroup` 实际上是切换渲染 / 场景遍历根，而不是销毁 group。
- `PrimSetNull` 将 prim 重置为 `PrimTypeNone`，与单纯 `PrimGroupOut` 不同。
- `PrimSetSprt` 是图像资源真正绑定到显示对象的核心接口。
- `PrimSetText` 只绑定文本槽位，不负责写入文本内容。
- `PrimSetTile` 创建纯色矩形，`tile_id` 当前对应 color manager 槽位。
- `PrimSetSnow` 创建雪花专用 prim，但 `mode` 的具体业务分支尚未恢复。
- `PrimSetOP` 设置的是 pivot / 锚点，不是普通屏幕坐标。
- `PrimSetRS` 是等比缩放，`PrimSetRS2` 是独立 X/Y 缩放。
- 缩放内部基准为 `1000`，渲染时按 `factor / 1000.0` 计算。
- `PrimSetUV + PrimSetWH` 共同构成纹理采样矩形。
- `PrimSetXY` 设置的是相对父节点的局部位置。
- `PrimSetAlpha` 使用 `0..255` 的透明度值。
- `PrimSetDraw` 控制是否参与渲染树遍历。
- `PrimHit` 当前实现返回 `True/Nil`，但 `syscall_spec.json` 目前错误记录为 `Nil`，需要后续回写修正。
- `PrimSetClip` 是 legacy 兼容接口，当前映射为把 UV/WH 重置到全屏虚拟区域。

---

## 13. 仍需保守处理的点

1. `PrimSetBlend` 的原引擎 0/1 混合模式含义有源码注释依据，但当前 rfvp GPU 渲染路径没有发现 `get_blend()` 的直接消费点，最终视觉效果需要实机验证。
2. `PrimSetSprt` 的 `src_id=-1` 特殊内置纹理路径只在源码注释中明确，当前渲染器中没有找到完整实现；`src_id=-2` 的 movie 绑定则有明确实现。
3. `PrimSetSnow` 的 `mode=0/1` 只在 syscall 层做范围校验，当前实现没有分支解释其业务含义。
4. `PrimSetZ` 的普通 2D 绘制顺序与 `attr=0x04` 下的虚拟 3D 投影路径已经部分恢复，但不同作品 / 后端的最终深度表现仍需更多样本。
5. `PrimHit` 的数据库返回类型与当前源码不一致；本文以源码实际行为为准，但机器可读数据库应在后续维护中修正。
6. `PrimSetClip` 的原版独立 clip rectangle 在当前 rfvp 中没有对应字段，UV/WH 映射属于效果近似而不是数据结构一一对应。
7. `PrimSetTile` 的 `tile_id` 在当前 rfvp 中被解释为 color manager 槽位；不同历史版本是否使用过其他 tile 资源表，需要进一步交叉验证。

---

## 14. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:101-112)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3784-4805)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:91-111)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:93-112)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:569-590)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:710-712)
- [`graph.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:9-858)
- [`graph.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1010-1621)
- [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:380-397)
- [`prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:8-61)
- [`prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/prim.rs:304-616)
- [`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:583-730)
- [`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:280-319)
- [`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:450-827)
- [`motion_manager/snow.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/snow.rs:467-531)
- [`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:338-500)
- [`f_0005207E函数解析.md`](fvp_analysis/result/hcbtool_test/f_0005207E函数解析.md:338-360)
- [`BGimageLoading函数共性总结.md`](fvp_analysis/result/hcbtool_test/BGimageLoading函数共性总结.md:237-270)
- [`LOGO演出解析.md`](fvp_analysis/result/hcbtool_test/LOGO演出解析.md:40-69)
- [`logo演出详解.md`](fvp_analysis/result/hcbtool_test/logo演出详解.md:257-269)
