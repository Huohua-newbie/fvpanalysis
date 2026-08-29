# Utils 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:112)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:1324-1359,1954-1995,4898-4926) 与 rfvp 参考实现，`Utils` 分组当前包含 3 个 syscall：

1. `FloatToInt`
2. `IntToText`
3. `Rand`

其显式规格与注册位置见 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:41,58,113) 与 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:543-546)。

三条接口都属于 VM 层工具：

- 不访问 `GameData` 的业务子系统；
- 不修改图像、音频、文本、线程或存档状态；
- 不产生 yield、wait、sleep、text_wait、dissolve_wait 或 halt；
- 主要通过返回值为脚本提供类型转换、数字格式化和随机数。

`Utils` 分组可以概括为：

> **FVP VM 层的基础数值转换、格式化和随机数工具接口。**

---

## 2. Utils 组的共同特征

### 2.1 作用范围是 VM 值

三条 syscall 都不依赖 `GameData` 状态：

- `FloatToInt`：读取 `Variant::Float` 并生成 `Variant::Int`；
- `IntToText`：读取 `Variant::Int` 和宽度，生成 `Variant::String`；
- `Rand`：直接生成 `Variant::Float`。

因此它们与 `Prim`、`Text`、`Timer` 等资源/状态型 syscall 的边界非常清楚：

> **Utils 只计算或转换值，不主动推进引擎状态。**

### 2.2 返回值比副作用更重要

`Utils` syscall 的主要语义都在返回寄存器：

| syscall | 返回类型 | 核心结果 |
|---|---|---|
| `FloatToInt` | `Int` | 浮点数转整数 |
| `IntToText` | `String\|Nil` | 整数左侧补零字符串 |
| `Rand` | `Float` | 随机浮点数 |

### 2.3 错误处理采用软失败

当前实现不会抛出 VM 异常：

- `FloatToInt` 参数不是 Float 时返回 `Int(0)`；
- `IntToText` 参数类型不正确时返回 `Nil`；
- `Rand` 没有参数，因此不存在参数校验失败分支。

这体现了 FVP syscall 常见的“记录日志 + 返回 Variant”兼容风格。

---

## 3. `FloatToInt`

### 3.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:1327)
- **签名**：`FloatToInt(value)`
- **参数类型**：`Float`
- **返回值**：`Int`
- **控制流**：无 VM 调度副作用

### 3.2 入参语义

- `value`
  - 类型：`Variant::Float`；
  - 含义：待转换的浮点数。

当前实现只接受 `Float`：

```rust
if let Variant::Float(value) = value {
    *value as i32
}
```

如果传入 `Int`、`Nil`、字符串或其他 Variant，当前实现不会尝试通用转换，而是记录警告并返回 `Int(0)`：[`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:53-61)。

### 3.3 转换规则

Rust 的 `as i32` 转换在当前实现中承担浮点到整数的截断转换：

- 正数：去除小数部分，例如 `3.9 -> 3`；
- 负数：向零截断，例如 `-3.9 -> -3`；
- 返回结果为 VM 的 `Int`。

本文按当前 Rust 实现描述“向零截断”；不同原版 ABI 是否存在四舍五入或其他边界处理，需要以实机验证为准。

### 3.4 具体作用

`FloatToInt` 适合用于：

- 把 `Rand` 等产生的浮点结果转换为整数；
- 将计算结果用于 prim 坐标、尺寸、计时或索引；
- 在 HCB 脚本中把 VM 浮点值转换成整型 syscall 所需参数。

### 3.5 结论

> `FloatToInt` 是 **将 Float Variant 转换为 Int Variant 的 VM 工具接口，当前采用向零截断语义**。

---

## 4. `IntToText`

### 4.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:1957)
- **签名**：`IntToText(value, width)`
- **参数类型**：`Int`, `Int`
- **返回值**：`String | Nil`
- **控制流**：无 VM 调度副作用

### 4.2 入参语义

- `value`
  - 类型：`Int`；
  - 含义：待格式化的整数。
- `width`
  - 类型：`Int`；
  - 含义：输出字符串的最小宽度；不足时在左侧补零。

### 4.3 具体作用

[`int_to_text()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:64-82) 使用格式化模板：

```text
format!("{:0width$}", value, width = width as usize)
```

例如：

```text
IntToText(7, 3)    -> "007"
IntToText(42, 5)   -> "00042"
IntToText(1234, 2) -> "1234"
```

`width` 是最小宽度，不会截断已经超过该宽度的数字。

### 4.4 负数行为

当前实现直接使用 Rust 的零填充格式化，因此负数的具体补零位置由格式化器决定。对于负数、极端宽度和非正宽度，原版脚本兼容性不应仅凭函数名推断，建议结合实际调用样本验证。

### 4.5 参数错误

- `value` 不是 `Int`：返回 `Nil`；
- `width` 不是 `Int`：返回 `Nil`；
- 当前实现没有额外限制 `width` 的正负范围；
- 过大的宽度可能产生较长字符串，应由调用方保证合理。

### 4.6 具体用途

`IntToText` 常用于：

- 生成带前导零的编号；
- 生成时间、章节、槽位、资源编号等固定宽度显示文本；
- 把数字拼接进路径或文本内容。

### 4.7 结论

> `IntToText` 是 **按照指定最小宽度把整数转换为左侧零填充字符串的 VM 工具接口**。

---

## 5. `Rand`

### 5.1 参数与返回

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4901)
- **签名**：`Rand()`
- **参数类型**：无
- **返回值**：`Float`
- **控制流**：无 VM 调度副作用

### 5.2 具体作用

[`rand()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:84-86) 直接调用随机数库：

```rust
Ok(Variant::Float(rand::random()))
```

因此当前实现返回一个随机 `Float`，不写入 `GameData`，也不接受种子、范围或精度参数。

### 5.3 返回范围

当前代码没有显式限定范围，实际范围由 Rust `rand::random::<f32>()` 的实现决定。通常可以按随机浮点值理解，但不能把当前 syscall 的接口层语义写成：

- 固定返回整数；
- 固定返回 `0..100`；
- 固定返回闭区间或开区间；
- 支持传入上下界。

这些都不是当前接口提供的能力。

### 5.4 典型组合

如果脚本需要整数随机值，可组合：

```text
FloatToInt(Rand())
```

如果需要映射到某个范围，脚本还需要自行完成乘法、加法和截断。

### 5.5 确定性与种子

当前 `Rand()` 没有暴露种子设置接口，也没有在 syscall 层记录随机状态。因此：

- 当前实现的跨运行复现性不能由 syscall 本身保证；
- 存档/读档是否恢复随机序列，需要结合更高层 VM 或宿主随机数状态确认；
- 不能把 `Rand()` 视为带有游戏存档确定性的伪随机接口。

### 5.6 结论

> `Rand` 是 **无参数生成随机 Float 的 VM 工具接口**。

---

## 6. Utils 组整体语义

三条接口构成一个简单的 VM 辅助链：

1. `Rand()` 生成浮点随机值；
2. `FloatToInt(value)` 把浮点值转成整数；
3. `IntToText(value, width)` 把整数格式化为显示字符串。

典型组合：

```text
random_float = Rand()
random_int = FloatToInt(random_float * 10)
random_text = IntToText(random_int, 2)
```

需要注意，以上组合中的乘法和数值范围映射由脚本自身完成，不是 `Rand` 或 `FloatToInt` 自动提供的功能。

因此，`Utils` 分组的整体语义可以概括为：

> **为 HCB 脚本提供最小化的数值类型转换、整数格式化和随机数生成能力。**

---

## 7. 高置信度结论

以下结论比较稳：

- `Utils` 分组当前共有 3 个 syscall。
- `FloatToInt` 接受 Float，返回 Int；当前实现按 Rust `as i32` 进行向零截断。
- `FloatToInt` 传入非 Float 时返回 `Int(0)`。
- `IntToText` 接受 Int 与宽度 Int，返回左侧零填充的 String。
- `IntToText` 的 width 是最小宽度，不会截断超出宽度的整数。
- `IntToText` 参数类型错误时返回 `Nil`。
- `Rand` 无参数，返回 `Float`。
- 三条 Utils syscall 都只影响 VM 值，不访问业务 GameData 子系统。
- 三条 Utils syscall 都不产生调度副作用。

---

## 8. 仍需保守处理的点

1. `FloatToInt` 的极端浮点值、NaN、无穷大等边界行为应以当前 Rust 编译目标和原版实机分别验证。
2. `IntToText` 的负数补零位置、负 width、超大 width 等边界格式化行为不宜在 syscall 数据库中写死。
3. `Rand` 的实际数值分布、种子初始化、跨存档恢复和跨平台一致性当前没有在 syscall 层确认。
4. `Rand` 不提供上下界参数，脚本中的范围转换逻辑需要在调用方函数中继续分析。
5. Utils syscall 的错误处理采用软失败，调用方若依赖返回值区分“转换失败”和“合法结果”，需要特别检查 `Int(0)` 与 `Nil` 的差异。

---

## 9. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:112-114)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:1324-1359,1954-1995,4898-4926)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:35,52,114)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:41,58,113)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:543-546)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:53-86)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:274-302)
- [`script/mod.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/script/mod.rs:101-128)
