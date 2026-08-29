# Parts 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:101)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3426-3780)、[`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:83-90) 与 rfvp 参考实现，`Parts` 分组当前包含 8 个 syscall：

1. `PartsAssign`
2. `PartsLoad`
3. `PartsMotion`
4. `PartsMotionPause`
5. `PartsMotionStop`
6. `PartsMotionTest`
7. `PartsRGB`
8. `PartsSelect`

其注册位置可见于 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:85-92) 与 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:673-681)。

综合源码与现有样例，`Parts` 分组可以概括为：

> **围绕部件资源加载、色调调整、prim 绑定、帧选择与部件 motion 控制的一组资源型接口。**

它和 [`Prim`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3784) 组不同：`Parts` 主要操作的是 `parts_manager` 与其 motion pool，而不是直接操作通用 prim 属性。

---

## 2. 边界说明：Parts 与 Prim / Motion / Graph 的分工

### 2.1 作用对象是 parts slot

`Parts` 组的核心资源层是 [`PartsManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:199-305)：

- `parts`：64 个部件槽
- `parts_motions`：8 个部件 motion 槽
- `allocation_pool`：固定槽位回收池

因此这组 syscall 的默认作用对象不是“任意 prim”，而是 `parts_id` 对应的部件槽。

### 2.2 与 Motion 的关系

`PartsMotion*` 不是 [`Motion`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3252) 组那套通用 prim 动画，而是部件专用 motion：

- 启动 / 停止 / 测试都走 [`MotionManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:495-514)
- 完成后由 [`tick_motions()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:307-345) 推进并回写结果

### 2.3 与 Graph 的关系

`PartsAssign` / `PartsSelect` 最终会影响纹理绘制，但并不是 Graph 组 syscall；它们通过 [`draw_parts_to_texture()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:520-553) 把部件条目绘制到与 `prim_id` 关联的纹理缓存里。

---

## 3. 共享实现约定

### 3.1 `parts_id` 统一是 0..=63

大多数 `Parts` 接口都要求 `parts_id` 为 `Int`，有效范围为 `0..64`。

例外是：

- [`PartsMotionStop`](#8-partsmotionstop)
- [`PartsMotionTest`](#9-partsmotiontest)

它们只接受 `1..64`，也就是 `1..=63`：[`parts.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:234-263)

### 3.2 `duration` 统一按毫秒

`PartsMotion` 的 `duration` 必须是 `1..=300000`：[`parts.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:188-195)

### 3.3 `entry_id` 是部件条目 / 帧索引

`PartsMotion` 与 `PartsSelect` 都把 `entry_id` 当作条目索引使用：

- `PartsMotion`：`0..=255`
- `PartsSelect`：`0..=255`

这与部件资源内部的 texture 条目数量一致：[`parts.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:107-125, 179-201)、[`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:520-553)

### 3.4 `PartsRGB` 的通道范围

`PartsRGB` 的 `r/g/b` 不是任意整数：

- 只有 `Int` 且 `0..=200` 才会被采纳
- 否则默认回退为 `100`

见 [`parts.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:75-94)

### 3.5 `PartsMotionPause` 是暂停开关

`PartsMotionPause(id, on)` 的 `on` 语义是：

- `0`：恢复推进
- `1`：暂停推进

虽然内部字段名叫 `running`，但 [`tick_motions()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:315-326) 明确把它当成“暂停标志”使用。

### 3.6 `PartsAssign` / `PartsSelect` / `PartsLoad` 会回收 motion 槽

这三个接口都会在动作后调用 [`next_free_id()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:255-261)：

- [`PartsLoad`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:41-54)
- [`PartsAssign`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:144-159)
- [`PartsSelect`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:107-126)

这意味着它们除了“设置状态”，还会顺带清理对应 parts 的 motion 占用。

### 3.7 `PartsMotionTest` 返回 `Int(1/0)`

它不是 `BoolLike`，而是明确返回整数：[`parts.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:250-263)

---

## 4. `PartsAssign`

### 4.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3429)
- **签名**：`PartsAssign(parts_id, prim_id)`
- **返回值**：`Nil`

### 4.2 入参语义

根据 [`parts_assign()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:130-160)：

- `parts_id`
  - 类型：`Int`
  - 有效范围：`0..63`
- `prim_id`
  - 类型：`Int`
  - 有效范围：`0..4095`
  - 作用：把该 parts 槽绑定到某个 prim

### 4.3 具体作用

[`PartsAssign`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3426) 会把 `parts_id` 对应的部件槽绑定到指定 `prim_id`：

- 绑定成功后，后续 `PartsSelect` / 部件绘制会落到这个 prim 关联的纹理槽上
- 无论绑定是否成功，都会回收该 parts 的 motion 槽

### 4.4 结论

> `PartsAssign` 的本质是 **部件槽与 prim 的绑定接口**。

---

## 5. `PartsLoad`

### 5.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3473)
- **签名**：`PartsLoad(id, path)`
- **返回值**：`Nil`

### 5.2 入参语义

根据 [`parts_load()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:8-57)：

- `id`
  - 类型：`Int`
  - 有效范围：`0..63`
- `path`
  - 类型：`Nil | String | ConstString`
  - 含义：
    - `Nil`：卸载该 parts 的已解码像素数据，但保留名字 / 元数据
    - `String / ConstString`：从 VFS 加载该 parts 资源
    - 其他类型：no-op

### 5.3 具体作用

[`PartsLoad`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3470) 负责 parts 资源的装载与卸载：

- 加载时调用 [`load_parts()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:218-221)
- 卸载时调用 [`unload_parts_keep_name()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:223-230)
- 这与源码注释所说的原引擎行为一致：`PartsLoad(id, nil)` 只释放像素数据，不抹掉名字

### 5.4 结论

> `PartsLoad` 是 **部件资源加载 / 卸载接口**。

---

## 6. `PartsMotion`

### 6.1 参数与返回

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3517)
- **签名**：`PartsMotion(id, entry_id, duration)`
- **返回值**：`Nil`

### 6.2 入参语义

根据 [`parts_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:164-201)：

- `id`
  - 类型：`Int`
  - 有效范围：`0..63`
- `entry_id`
  - 类型：`Int`
  - 有效范围：`0..255`
  - 含义：部件条目 / 帧索引
- `duration`
  - 类型：`Int`
  - 有效范围：`1..=300000`
  - 含义：运动持续时间（毫秒）

### 6.3 具体作用

[`PartsMotion`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3514) 会为指定 parts 启动一条时间型 motion：

- `set_parts_motion()` 进入固定的 8 槽 motion pool：[`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:495-506)
- 到达持续时间后，完成项会被 `tick_motions()` 收集并回写到纹理：[`parts_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:307-345)

换句话说：

> `PartsMotion` 是 **按时间切换部件条目的动画接口**。

### 6.4 结论

`PartsMotion` 适合做立绘表情、部件切换、分段过渡等效果。

---

## 7. `PartsMotionPause`

### 7.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3567)
- **签名**：`PartsMotionPause(id, on)`
- **返回值**：`Nil`

### 7.2 入参语义

根据 [`parts_motion_pause()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:204-232)：

- `id`
  - 类型：`Int`
  - 有效范围：`0..63`
- `on`
  - 类型：`Int`
  - 只接受 `0` 或 `1`
  - `1`：暂停
  - `0`：恢复

### 7.3 具体作用

它设置的是部件 motion 的暂停状态，而不是停止状态：

- 内部通过 `parts.set_running(on != 0)` 写入标志
- `tick_motions()` 遇到该标志时会跳过推进

因此它更像：

> **部件 motion 的暂停 / 继续开关。**

### 7.4 结论

`PartsMotionPause` 适合用于临时冻结部件动画，而不丢失 motion 进度。

---

## 8. `PartsMotionStop`

### 8.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3611)
- **签名**：`PartsMotionStop(id)`
- **返回值**：`Nil`

### 8.2 入参语义

根据 [`parts_motion_stop()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:234-248)：

- `id`
  - 类型：`Int`
  - 有效范围：`1..63`

### 8.3 具体作用

[`PartsMotionStop`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3608) 会停止对应 parts 的 motion，并回收 motion 槽：

- 内部调用 [`stop_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:301-305)
- 该函数会卸载该 parts 对应的 running motion，并归还槽位

### 8.4 结论

> `PartsMotionStop` 是 **部件 motion 的终止接口**。

---

## 9. `PartsMotionTest`

### 9.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3649)
- **签名**：`PartsMotionTest(id)`
- **返回值**：`Int(1/0)`

### 9.2 入参语义

根据 [`parts_motion_test()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:250-263)：

- `id`
  - 类型：`Int`
  - 有效范围：`1..63`

### 9.3 具体作用

[`PartsMotionTest`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3646) 用于轮询该 parts 是否仍有 motion 在运行：

- `1`：仍在运行
- `0`：没有运行中的 motion

本质上它对应 [`PartsManager::test_motion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:295-299) 的结果。

### 9.4 结论

> `PartsMotionTest` 是 **部件 motion 的轮询查询接口**。

---

## 10. `PartsRGB`

### 10.1 参数与返回

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3687)
- **签名**：`PartsRGB(id, r, g, b)`
- **返回值**：`Nil`

### 10.2 入参语义

根据 [`parts_rgb()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:59-94)：

- `id`
  - 类型：`Int`
  - 有效范围：`0..63`
- `r/g/b`
  - 类型：`Int`
  - 有效范围：`0..=200`
  - 超范围或非 `Int` 时默认值为 `100`

### 10.3 具体作用

[`PartsRGB`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3684) 会修改 parts 的色调 / 染色参数：

- 底层调用 [`set_color_tone()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:89-94)
- 适合做灰化、偏色、强调等效果

### 10.4 结论

> `PartsRGB` 是 **部件颜色调整接口**，更准确地说是色调参数设置，而不是纯粹的 RGB 像素运算。

---

## 11. `PartsSelect`

### 11.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3743)
- **签名**：`PartsSelect(id, entry_id)`
- **返回值**：`Nil`

### 11.2 入参语义

根据 [`parts_select()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:97-127)：

- `id`
  - 类型：`Int`
  - 有效范围：`0..63`
- `entry_id`
  - 类型：`Int`
  - 有效范围：`0..255`
  - 含义：要选中的部件条目 / 帧索引

### 11.3 具体作用

[`PartsSelect`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3740) 会把指定条目直接绘制到 parts 绑定的纹理中：

- 只有 `entry_id < 256` 时才尝试绘制
- 绘制失败不是致命错误
- 无论成功与否，都会回收该 parts 的 motion 槽

这与 `PartsManager::draw_parts_to_texture()` 的 best-effort 策略一致：[`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:520-553)

### 11.4 脚本样例

现有样例中，[`f_00058B8C立绘引入参数解析.md`](fvp_analysis/result/hcbtool_test/f_00058B8C立绘引入参数解析.md:126-139) 已把 `PartsSelect` 解释为：

> **细粒度表情 / 部件编号的选择值。**

这说明它在实际脚本里通常对应“切换某个立绘细分表情或部件帧”。

### 11.5 结论

`PartsSelect` 是 **立即选帧并绘制到纹理的接口**。

---

## 12. `Parts` 组整体语义

把 8 个 syscall 放在一起，可以看到清晰的子职责结构：

1. **部件资源装载**
   - `PartsLoad`
2. **部件色调调整**
   - `PartsRGB`
3. **部件与 prim 绑定**
   - `PartsAssign`
4. **部件帧切换 / 动画**
   - `PartsMotion / PartsMotionPause / PartsMotionStop / PartsMotionTest`
5. **部件条目立即绘制**
   - `PartsSelect`

因此，`Parts` 分组的整体语义可以概括为：

> **FVP 里负责“部件资源生命周期 + 部件动画 + 绑定到 prim”的接口总线。**

典型工作流通常是：

1. [`PartsLoad()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:8-57) 装载资源
2. [`PartsAssign()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:130-160) 绑定到 prim
3. [`PartsSelect()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:97-127) 选择并绘制某个条目
4. [`PartsMotion()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:164-201) 启动时间型切换
5. 需要同步时轮询 [`PartsMotionTest()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:250-263)
6. 需要冻结时使用 [`PartsMotionPause()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:204-232)
7. 结束时用 [`PartsMotionStop()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:234-248)

---

## 13. 高置信度结论

以下结论比较稳：

- `Parts` 分组当前共有 8 个 syscall。
- 它们都只影响 `parts_manager` / `motion_manager`，不属于通用 `Prim` 组。
- `PartsLoad(id, nil)` 是卸载，但保留名字 / 元数据。
- `PartsMotion` 是带持续时间的部件条目切换。
- `PartsMotionPause` 的 `1` 是暂停，`0` 是恢复。
- `PartsMotionStop` / `PartsMotionTest` 只接受 `1..63`。
- `PartsMotionTest` 返回 `Int(1/0)`，不是 `BoolLike`。
- `PartsSelect` 是立即选帧 + 绘制，且带 best-effort 容错。
- `PartsAssign` / `PartsLoad` / `PartsSelect` 都会顺带回收 motion 槽。

---

## 14. 仍需保守处理的点

1. `PartsSelect` 在部分作品里的业务含义可能是“表情编号”或“部件编号”，当前较稳妥的写法是“细粒度部件条目选择”。
2. `PartsMotionPause` 的内部字段名与外部语义并不完全同名，文档应以 tick 逻辑为准，而不是以字段名直译。
3. `PartsLoad` / `PartsAssign` / `PartsSelect` 的参数类型在 `syscall_spec.json` 中仍有较多 `generic` 占位；本文件已结合实现细化，但后续仍可继续做脚本层交叉验证。
4. `PartsMotion` 的条目完成后如何与具体脚本语义对齐，仍建议结合更多实机样本继续细化。

---

## 15. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:101-103)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:3426-3780)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:83-90)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:85-92)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:673-681)
- [`parts.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/parts.rs:8-263)
- [`parts_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/parts_manager.rs:199-345)
- [`motion_manager/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:495-553)
- [`f_00058B8C立绘引入参数解析.md`](fvp_analysis/result/hcbtool_test/f_00058B8C立绘引入参数解析.md:126-139)
