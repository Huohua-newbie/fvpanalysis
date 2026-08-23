# LegacyCharacter 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../README.md)、[`syscall_spec.txt`](../syscall_spec.txt) 与 rfvp 参考实现，LegacyCharacter 分组当前包含 3 个 syscall：

1. `ChrAdd`
2. `ChrGetRGB`
3. `ChrGetVol`

其注册位置可见于：

- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:39-41)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:699-702)

综合实现细节与命名，可以把这组 syscall 概括为：

> **旧版角色信息表接口。**

它们并不直接控制立绘图元，也不直接播放语音，而是维护一张“角色描述表”，表项至少包含：

- 名字
- 颜色槽/实际 RGBA
- 语音音量
- 语音前缀

因此更准确地说，这组接口是：

> **面向旧版 FVP/兼容脚本的角色元数据注册与读取接口。**

---

## 2. 共享实现约定

## 2.1 存储位置

rfvp 在 [`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:14-18) 中维护了一个全局静态表：

- `LEGACY_CHR_TABLE: Mutex<Vec<LegacyChrEntry>>`

而表项结构 [`LegacyChrEntry`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:21-28) 包含：

- `_name: String`
- `_color_slot: u8`
- `rgba: [u8; 4]`
- `volume: i32`
- `_voice_prefix: String`

这里最关键的一点是：

> 这组 syscall 不是直接操纵“当前角色对象”，而是在维护一张**最多 32 项的兼容角色表**。

### 2.2 表项数量上限

[`chr_add()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:230-233) 明确限制：

- 只有当 `table.len() < 32` 时才 push 新条目

因此这张旧版角色表的设计上限是：

- **32 个角色条目**

### 2.3 颜色与语音并不是即时行为

从实现看：

- 颜色会在 `ChrAdd` 时从当前 `ColorManager` 槽位中取出并固化成 `rgba`：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:221-227)
- `ChrGetRGB` 只是把缓存好的 `rgba` 再写回某个颜色槽：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:253-257)
- `ChrGetVol` 只是返回缓存好的音量整数：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:261-272)

所以这组 syscall 的语义更像：

> **角色元数据的登记 / 查询 / 拷贝**，而不是即时角色演出控制。

---

## 3. `ChrAdd`

### 3.1 参数与返回

- **参数个数**：4：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:39)
- **签名**：`ChrAdd(name, color_slot, volume, voice_prefix)`
- **返回值**：`Nil`

### 3.2 参数语义

根据 [`chr_add()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:195-234)：

- `arg0: String`
  - 角色名
- `arg1: Int`
  - 颜色槽号，范围 `0..=255`
- `arg2: Int`
  - 音量，范围 `0..=100`
- `arg3: String`
  - 语音路径前缀

其中第 4 参数在写入前会经过 [`normalize_prefix()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:86-94) 处理：

- 反斜杠会转成 `/`
- 末尾若没有 `/`，会自动补上 `/`

因此 `voice_prefix` 的更准确语义是：

> **角色语音资源的标准化前缀路径。**

### 3.3 具体作用

`ChrAdd` 做的事情可以拆成：

1. 校验名字、颜色槽、音量、语音前缀参数是否合法：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:202-219)
2. 从 `ColorManager` 当前颜色槽中取出 RGBA 值：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:221)
3. 构造一条 `LegacyChrEntry`：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:222-227)
4. 若表未满，则 push 到 `LEGACY_CHR_TABLE`：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:230-233)

### 3.4 语义判断

因此 `ChrAdd` 的高置信度语义是：

> **把一个角色的“名字 + 颜色 + 语音音量 + 语音路径前缀”注册进旧版角色表。**

它不像 `PrimSet*` 那样直接作用当前帧，而更像一种：

- 兼容型角色数据库构建接口

### 3.5 颜色复制的特殊性

注意 `ChrAdd` 存下的不是“颜色槽编号本身的动态引用”，而是当时槽位中的实际 `rgba` 值：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:224-225)

因此后续就算原颜色槽被改掉，这个角色条目里缓存的颜色仍然不变。

这说明 `ChrAdd` 对颜色的行为是：

> **注册时拍快照，而不是延迟绑定。**

---

## 4. `ChrGetRGB`

### 4.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:40)
- **签名**：`ChrGetRGB(index, dst_slot)`
- **返回值**：`Nil`

### 4.2 参数语义

根据 [`chr_get_rgb()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:237-259)：

- `arg0: Int`
  - 角色表索引，必须 `>= 0`
- `arg1: Int`
  - 目标颜色槽，范围 `0..=255`

### 4.3 具体作用

`ChrGetRGB` 会：

1. 从 `LEGACY_CHR_TABLE` 中取出 `index` 对应角色：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:248-250)
2. 取出该角色登记时缓存的 `rgba`：[`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:253-257)
3. 把这些颜色分量写入 `dst_slot` 对应的 `ColorManager` 条目：
   - `set_r`
   - `set_g`
   - `set_b`
   - `set_a`

### 4.4 语义判断

可概括为：

> **把旧版角色表中某角色缓存的 RGBA 颜色复制到指定颜色槽。**

这意味着它不是“返回颜色值”，而是一个：

- **角色颜色 -> 颜色槽** 的写回接口

### 4.5 与 ColorSet 的关系

若从更高层看，它相当于做了一个角色驱动的颜色槽写入，其效果近似于：

- 根据角色索引决定 RGBA
- 再把 RGBA 灌进 `ColorManager`

所以它可以视为旧版脚本里对 [`ColorSet`](../syscall含义详解/02_Color.md:44) 的一种角色包装接口。

---

## 5. `ChrGetVol`

### 5.1 参数与返回

- **参数个数**：1：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:41)
- **签名**：`ChrGetVol(index)`
- **返回值**：`Int|Nil`

### 5.2 参数语义

根据 [`chr_get_vol()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:261-272)：

- `arg0: Int`
  - 角色表索引，必须 `>= 0`

### 5.3 具体作用

`ChrGetVol` 会：

1. 在 `LEGACY_CHR_TABLE` 中取出指定索引的角色条目
2. 返回其中缓存的 `volume`
3. 若索引非法或不存在，则返回 `Nil`

### 5.4 语义判断

可概括为：

> **读取旧版角色表中某个角色登记的默认语音音量。**

它不会直接调音频子系统，只是把数值拿出来供上层脚本使用。

---

## 6. LegacyCharacter 分组的整体语义

把三者合起来看：

- `ChrAdd`：向旧版角色表注册一条记录
- `ChrGetRGB`：从角色表取颜色并写回颜色槽
- `ChrGetVol`：从角色表取默认音量

因此这一组最准确的整体语义应写成：

> **旧版角色元数据表的登记与查询接口。**

它更偏“兼容层/数据表层”，而不是运行时演出层。

---

## 7. 高置信度结论

以下结论比较稳：

- LegacyCharacter 分组当前包含 `ChrAdd`、`ChrGetRGB`、`ChrGetVol` 三个 syscall。
- 底层存储在 `LEGACY_CHR_TABLE` 中，容量上限为 32 条。
- `ChrAdd` 会把颜色槽里的当前 RGBA 拍快照保存，而不是保存动态引用。
- `ChrGetRGB` 会把角色条目缓存的 RGBA 写回目标颜色槽。
- `ChrGetVol` 返回角色条目的默认音量整数。
- `voice_prefix` 在注册时会被规范化为以 `/` 结尾的路径前缀。

---

## 8. 仍需保守处理的点

1. 当前检索到的工程与脚本样本里，`ChrAdd/ChrGetRGB/ChrGetVol` 的直接 HCB 调用样例较少；本组结论主要依赖 rfvp 源码，因此应标为**legacy compatibility high confidence, runtime sample still sparse**。
2. `voice_prefix` 目前只看到被缓存，没有在本段附近直接消费；它极可能是供其他旧版语音打印/播放链条使用，但仍需顺着 `legacy.rs` 的其他函数继续补证。
3. 该组接口更偏早期 FVP/兼容 ABI，并不一定是 Sakura 这类后期脚本的主路径。

---

## 9. 证据来源

- [`README.md`](../README.md:29-44, 93-96)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:39-41)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:699-702)
- [`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:14-28)
- [`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:86-100)
- [`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:195-234)
- [`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:237-259)
- [`legacy.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:261-272)
- [`FVP引擎文献综述.md`](../FVP引擎文献综述.md:156-180)
- [`Sakura首个function说话人名显示详解.md`](../../hcbtool_test/Sakura首个function说话人名显示详解.md:433-435)
