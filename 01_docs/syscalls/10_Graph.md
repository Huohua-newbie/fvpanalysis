# Graph 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md)、[`syscall_spec.txt`](../spec/syscall_spec.txt) 与 rfvp 参考实现，Graph 分组当前包含 2 个 syscall：

1. `GraphLoad`
2. `GraphRGB`

其注册位置可见于：

- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:43-44)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:591-593)

综合源码与脚本调用样例，Graph 分组可以概括为：

> **图像资源槽的装载/卸载与色调调整接口。**

它们都更偏**资源层**而不是直接显示层：

- [`GraphLoad`](#3-graphload) 负责把图像资源装入 graph 槽，或从槽中卸载；
- [`GraphRGB`](#4-graphrgb) 负责对已装入图像做 RGB 色调修正。

---

## 2. 共享实现约定

## 2.1 Graph 槽与 Prim 槽不是一回事

这一组最容易误解的点是：

> **Graph 槽 ≠ Prim 槽。**

`GraphLoad` 只是把图像资源放进 `graph` / `GraphBuff` 侧缓存，并不会自动“上屏”。

这一点在现有分析里已有比较清楚的总结：

- [`Sakura.lua典型功能块讲解.md`](../reversals/Sakura.lua典型功能块讲解.md:393) 明确指出：单独 `GraphLoad` 更偏资源层；真正让内容显示出来的关键往往是 `PrimSetSprt` 一类调用。
- [`f_0005207E函数解析.md`](../../hcbtool_test/f_0005207E函数解析.md:357-358) 也显示常见模板是：先 `GraphLoad`，再 `PrimSetSprt` / `PrimGroupIn` 等。

因此，Graph 分组应理解为：

- `GraphLoad`：资源装载/卸载
- `GraphRGB`：资源调色
- `PrimSet*`：显示绑定/空间属性设置

## 2.2 Graph 槽编号范围

[`graph_load()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:861-896) 与 [`graph_rgb()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:900-961) 都要求 graph id 在：

- `0..4096`，也就是 `0..=4095`

所以 Graph 分组的第一个参数通常都是：

- **`Int` 类型的 graph 槽编号**
- 合法范围：`0..4095`

## 2.3 返回值风格

从实现看：

- [`GraphLoad`](#3-graphload) 返回 `Nil`
- [`GraphRGB`](#4-graphrgb) 返回 `Nil`

因此本组统一是：

- **控制类 / 资源类接口，返回 `Nil`**

---

## 3. `GraphLoad`

### 3.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:43)
- **签名**：`GraphLoad(id, path)`
- **参数含义**：
  - `arg0: Int`：graph 槽编号，范围 `0..4095`
  - `arg1: String | ConstString | Nil`：资源路径；`Nil` 表示卸载
- **返回值**：`Nil`：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:861-896)

### 3.2 具体作用

[`graph_load()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:861-896) 的逻辑是：

1. 校验 `id` 必须是 `Int` 且在 `0..4095`
2. 若 `path` 是字符串：
   - 从 VFS 读取文件：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:875-883)
   - 调 `motion_manager.load_graph(id, path, buff)`：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:878-880)
   - 再调 `refresh_prims(id)` 刷新依赖此 graph 的 prim：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:881-883)
3. 若 `path == Nil`：
   - 调 `motion_manager.unload_graph(id)`：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:885-889)
4. 返回 `Nil`

### 3.3 语义判断

因此它的精确语义可以写成：

> **把某个图像资源装入指定 graph 槽，或将该槽卸载；并在装载后刷新引用它的 prim。**

### 3.4 与 `GraphBuff` 的关系

虽然 `GraphLoad` 本身只是 syscall 封装，但从 [`graph_buff.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/graph_buff.rs:200-214) 可知，普通图像装入后会成为：

- `GraphBuffLoadKind::Texture`

这说明 `GraphLoad` 面向的是**普通纹理资源槽**，与 mask / gaiji glyph 等其他 load kind 分开。

### 3.5 常见脚本模板

#### 模板 1：卸载旧图再装新图

在 [`f_00037294.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037294.lua:60-64) 中能看到典型模板：

- 先 `GraphLoad(old_id, nil)`
- 再 `GraphLoad(new_id, path)`

这说明脚本常显式清理旧图，再装新资源，避免旧状态残留。

#### 模板 2：成组卸载

例如：

- [`f_0004770E.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004770E.lua:56-69)
- [`f_0008A94C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008A94C.lua:51-104)
- [`f_000927D8.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000927D8.lua:334-393)

这类代码会连续对多个 graph 槽执行 `GraphLoad(id, nil)`，明显属于：

> **批量卸载图像缓存槽。**

#### 模板 3：普通图像装载

在 [`f_00058B8C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00058B8C.lua:8945-8972) 中可以看到参数化的 `GraphLoad(id, path)` 用法，说明它是图像装载主力接口之一。

### 3.6 高置信度结论

- `GraphLoad(id, path)`：装入图像资源到 graph 槽
- `GraphLoad(id, nil)`：卸载该 graph 槽
- 它不会单独负责把图像显示出来

---

## 4. `GraphRGB`

### 4.1 参数与返回

- **参数个数**：4：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:44)
- **签名**：`GraphRGB(id, r, g, b)`
- **参数含义**：
  - `arg0: Int`：graph 槽编号，范围 `0..4095`
  - `arg1: Int`：红通道调整值
  - `arg2: Int`：绿通道调整值
  - `arg3: Int`：蓝通道调整值
- **返回值**：`Nil`：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:900-961)

### 4.2 具体作用

[`graph_rgb()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:900-961) 的逻辑是：

1. 校验 graph id 必须是 `Int(0..4095)`
2. 分别读取 `r/g/b` 三个通道参数
3. 若通道值越界（不在 `0..=200`），则回退为 `100`：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:914-954)
4. 调 `motion_manager.graph_color_tone(id, r, g, b)`：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:957-959)
5. 返回 `Nil`

### 4.3 参数尺度语义

rfvp 在 [`GraphRGB` 的注释](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1644-1688) 中已经给出了比较完整的尺度定义：

- `0`：完全变暗
- `100`：保持原色
- `101..200`：逐步变亮

因此可以把三个通道参数理解为：

> **每个 RGB 通道各自的 0..200 百分比色调缩放值，其中 100 为 no-op。**

### 4.4 语义判断

所以 `GraphRGB` 的准确作用是：

> **对指定 graph 槽中的已装载图像应用 RGB 色调调整。**

它不是替换贴图，也不是设置 prim 颜色，而是：

- **修改图像资源的色调**
- 作用对象是 graph 槽内容本身

### 4.5 常见脚本样例

#### 模板 1：按全局色调参数统一调整

在 [`f_00039C85.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00039C85.lua:300-301) 中可以看到：

- `GraphRGB(S0, G[1952], G[1953], G[1954])`

这说明很多脚本会把全局色调配置批量作用到图像上。

#### 模板 2：对指定 graph 做局部色调控制

例如：

- [`f_000520AB.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000520AB.lua:33-34)
- [`f_00096976.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00096976.lua:185-186)

这些位置显示 `GraphRGB` 常被当作高层包装函数里的“调色步骤”。

### 4.6 高置信度结论

- `GraphRGB` 是资源调色接口
- 三个通道参数范围是 `0..200`
- `100` 表示不变
- 超范围时当前实现回退为 `100`

---

## 5. Graph 分组的整体语义

把 [`GraphLoad`](#3-graphload) 与 [`GraphRGB`](#4-graphrgb) 合在一起看，Graph 分组可概括为：

> **对 graph 资源槽进行装载/卸载与色调加工的一组基础图像接口。**

它们最典型的工作流是：

1. `GraphLoad(id, path)`：装图
2. `GraphRGB(id, r, g, b)`：必要时调色
3. 由 `PrimSetSprt` / `PrimSetText` / 相关 prim 系统把图像真正绑定到显示对象上

---

## 6. 高置信度结论

以下结论比较稳：

- Graph 分组当前包含 `GraphLoad` 与 `GraphRGB` 两个 syscall。
- 两者第一个参数都是 graph 槽编号，合法范围 `0..4095`。
- `GraphLoad(path=nil)` 表示卸载 graph 槽。
- `GraphLoad` 只负责资源槽，不直接负责显示。
- `GraphRGB` 的三个通道参数范围是 `0..200`，其中 `100` 为原色。
- `GraphRGB` 作用于图像资源本身的色调，而不是 prim 的空间属性。

---

## 7. 仍需保守处理的点

1. `GraphLoad` 装载后具体如何与不同类型 prim 建立引用，仍需与 `PrimSetSprt`、`PrimSetText` 等链路合并分析。
2. `GraphRGB` 对具体像素格式的处理细节在不同图像负载类型下可能存在差异；当前文档以 rfvp 现实现和公开注释为准。
3. 某些游戏是否会把非标准资源也塞入 graph 槽并复用 `GraphLoad`，还需跨作品继续观察。

---

## 8. 证据来源

- [`README.md`](../README.md:29-44, 82-83)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:37-38)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:43-44)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:591-593)
- [`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:861-896)
- [`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:900-961)
- [`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1644-1688)
- [`graph_buff.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/graph_buff.rs:200-214)
- [`fvp_analysis项目规范文档.md`](../fvp_analysis项目规范文档.md:342-344)
- [`FVP引擎文献综述.md`](../FVP引擎文献综述.md:571-573)
- [`Sakura.lua典型功能块讲解.md`](../reversals/Sakura.lua典型功能块讲解.md:393-399)
- [`f_0005207E函数解析.md`](../../hcbtool_test/f_0005207E函数解析.md:357-358)
- [`f_00037294.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00037294.lua:60-64)
- [`f_00039C85.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00039C85.lua:300-301)
- [`f_00058B8C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00058B8C.lua:8945-8972)
- [`f_00096976.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00096976.lua:185-186)
- [`f_0008A94C.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008A94C.lua:51-104)
- [`f_000927D8.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000927D8.lua:334-393)
