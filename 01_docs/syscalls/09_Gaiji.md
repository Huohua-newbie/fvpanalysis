# Gaiji 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../manual/syscall-db.md)、[`syscall_spec.txt`](../spec/syscall_spec.txt) 与 rfvp 参考实现，Gaiji 分组当前只有 1 个 syscall：

- `GaijiLoad`

其注册位置可见于 [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:42) 与 [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:595-596)。

综合源码与脚本调用样例，Gaiji 分组可以直接定性为：

> **外字 / 外部字形加载接口。**

它的作用不是“普通图片显示”，而是把一个字符或符号映射到一张外部字形图像，让文字系统在渲染该字符时改为绘制 gaiji bitmap。

---

## 2. 共享实现约定

## 2.1 作用对象

Gaiji 资源最终进入：

- [`GaijiManager`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/gaiji_manager.rs:46-92)
- [`TextManager`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:792-835, 1284-1315, 1593-1599)

它们的协作方式是：

1. 先通过 `GaijiLoad` 注册某个字符 -> 某个 size slot -> 某个 gaiji 图像
2. 文本系统在测量与绘制时查询是否存在匹配的 gaiji
3. 若存在，则直接使用外部 glyph 的 alpha mask 绘制，而不是字体轮廓

因此，Gaiji 分组本质上是：

> **给文本系统提供“外部字形替换表”。**

## 2.2 底层图像类型

gaiji 图像在 [`GraphBuff`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/graph_buff.rs:219-239) 中被加载为：

- `GraphBuffLoadKind::GaijiGlyph`

而 [`text_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:1284-1315) 在绘制时会从 `GraphBuff` 导出 alpha mask，并按 mask 绘制到文本缓冲。

所以它并不是普通 RGBA 贴图，而是更偏向：

> **单色覆盖/轮廓掩码型字形资源。**

---

## 3. `GaijiLoad`

### 3.1 参数与返回

- **参数个数**：3：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:42)
- **签名**：`GaijiLoad(code, size, path)`
- **返回值**：`Nil`

### 3.2 参数语义

rfvp 在 [`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1705-1725) 的注释中直接写明：

- `arg0: String`：要被替换的字符或符号
- `arg1: Int`：size slot，范围 12..64
- `arg2: String`：NVSG gaiji glyph 的资源路径

因此参数语义可以整理为：

- `code: String`
  - 目标字符/符号，例如 “怒”“汗”“♪”
- `size: Int`
  - 字号槽位；合法范围 `12..=64`
- `path: String`
  - gaiji 图像文件路径

### 3.3 具体作用

[`gaiji_load()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:965-1007) 的逻辑是：

1. 校验 `path` 必须是字符串
2. 校验 `size` 必须在 `12..=64`
3. 校验 `code` 必须是非空字符串
4. 从 VFS 读取 `path` 对应文件：[`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:1000)
5. 调 [`motion_manager.set_gaiji()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:803-807)
6. 由 [`GaijiManager.set_gaiji()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/gaiji_manager.rs:63-66) 按 `code + size` 建立索引

因此其语义可概括为：

> **注册一个“字符 -> 外部字形图像”的替换关系。**

### 3.4 绘制链路

当文本系统渲染字符串时：

- 先在 [`measure_special_unit_advance()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:822-836) 查询是否有对应 gaiji
- 若命中，则在 [`draw_gaiji_unit()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:1284-1315) 用 alpha mask 绘制
- [`GraphBuff::export_alpha_mask()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/graph_buff.rs:126-165) 会把图像转换成 8-bit coverage mask

这说明 `GaijiLoad` 的作用并不止于“载入图片”，而是：

> **为文本渲染器提供一个可替换的外字 glyph。**

---

## 4. 脚本中的典型用法

Sakura 中最典型的 gaiji 初始化函数是 [`f_00049D4E()`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00049D4E.lua:1)。

它做了非常规律的批量注册：

- 字符 “怒” / “汗” / “汁” / “ハ”
- 三个字号槽：`28`、`39`、`17`
- 对应资源路径：
  - `graph/gaiji_ikari`
  - `graph/gaiji_ase`
  - `graph/gaiji_shiru`
  - `graph/gaiji_heart`
  - 以及 `156` / `68` 版本路径

这表明 `GaijiLoad` 常见用途是：

- 感叹词图标
- 情绪符号
- 形象化拟声/表情外字

其用途更像是：

> **把特定字符替换成图像化的外字资源。**

---

## 5. Gaiji 分组的整体语义

把 rfvp 实现与 Sakura 脚本用法合起来看，Gaiji 分组可以概括为：

> **文本外字（外部字形）注册接口。**

它的典型用途包括：

1. 给特殊字符建立外字图像映射；
2. 支持情绪符号、拟声符号、装饰性字符；
3. 与文字系统配合，在渲染时替换字体 glyph。

---

## 6. 高置信度结论

以下结论比较稳：

- Gaiji 分组当前只有 `GaijiLoad` 1 个 syscall。
- `GaijiLoad` 的参数个数是 3，返回值是 `Nil`。
- 第 1 参数是要替换的字符/符号。
- 第 2 参数是 size slot，合法范围 `12..=64`。
- 第 3 参数是 gaiji 图像路径。
- 它的实际消费方是文本渲染器，而不是普通 sprite/graph 绘制。
- 底层使用的是 alpha mask 型 gaiji glyph。

---

## 7. 仍需保守处理的点

1. `GaijiLoad` 的资源格式在实现里依赖 NVSG/单色 glyph 路径；不同游戏是否都使用同一种打包格式，还需要继续归纳。
2. 某些脚本会给 `GaijiLoad` 配置不同的字号槽，具体哪些 size slot 组合代表何种 UI 语义，还需要按游戏补充。
3. 目前已见样例主要集中在情绪外字与装饰符号，其他字符类别仍待扩展。

---

## 8. 证据来源

- [`README.md`](../README.md:29-44, 89-90)
- [`syscall_spec.txt`](../spec/syscall_spec.txt:36)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:42)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:20-22, 595-596)
- [`graph.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/graph.rs:965-1007, 1705-1739)
- [`gaiji_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/gaiji_manager.rs:46-92)
- [`text_manager.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:822-836, 1284-1315, 1593-1599)
- [`graph_buff.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/graph_buff.rs:126-165, 219-239)
- [`f_00049D4E.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00049D4E.lua:1-53)
- [`FVP引擎文献综述.md`](../FVP引擎文献综述.md:997-1004)
- [`f_00049D4E.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_00049D4E.lua:5-53)
