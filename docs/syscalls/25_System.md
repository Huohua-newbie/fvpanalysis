# System 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:112)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5950-6029) 与 rfvp 参考实现，`System` 分组当前包含 2 个 syscall：

1. `SysAtSkipName`
2. `SysProjFolder`

其显式规格位于 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:129-130)，运行时注册位于 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:543-546)。

当前两条接口都由 [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:88-98) 提供实现，但实现体均为直接返回 `Nil` 的兼容占位：

- 不读取参数值；
- 不写入 `GameData`；
- 不修改 VFS 或项目路径；
- 不改变 VM 调度；
- 不产生 yield、wait、sleep 或 halt。

因此，当前 rfvp 可确认的整体语义是：

> **System 组是一个面向系统路径/项目配置兼容性的接口分组；当前 reference 只能确认接口存在、参数数量和 no-op 行为，原版业务语义尚未恢复。**

---

## 2. System 组的证据等级与边界

### 2.1 当前实现证据高，但原版业务语义低

两条 syscall 的 `implementation_status` 在数据库中都是 `implemented_explicitly_in_rfvp`，说明 rfvp 运行时确实注册了对应 handler；但 `verification_status` 都是 `needs_runtime_verification`，说明：

- 当前行为“调用后返回 Nil”是可以确认的；
- 名称所暗示的原版业务动作不能直接视为已恢复；
- 还需要原版实机、更多 HCB 调用样例或旧版逆向结果补证。

### 2.2 与 `Sys` / `Utils` 分组的边界

System 组只覆盖数据库中 `group = System` 的两条：

- [`SysAtSkipName`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5950)
- [`SysProjFolder`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5994)

不把名称中可能涉及路径、项目或跳过逻辑的其他接口强行并入。例如：

- `SysProjFolder` 不等同于 `SysProjFolder` 之外的 VFS 资源加载接口；
- `SysAtSkipName` 也不能直接等同于 `ControlMask`、`TextSkip` 或菜单跳过接口。

---

## 3. `SysProjFolder`

### 3.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5997)
- **签名**：`SysProjFolder(arg0)`
- **返回值**：`Nil`
- **数据库影响子系统**：`system/path`
- **数据库控制流**：无 yield / wait / sleep / halt

### 3.2 入参语义

数据库当前仅记录：

- `arg0`
  - 类型：`Variant`；
  - 含义：`arg1`；
  - `confidence=generic`。

当前源码函数签名是 [`system_project_dir(_game_data, _dir)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:88)，参数名 `_dir` 是一个有用但不足以定论的线索：

> 参数很可能与项目目录、工程目录或路径前缀有关，但当前实现没有读取其类型和值，因此不能确认它是字符串、路径 ID、开关还是其他系统参数。

### 3.3 当前 rfvp 具体作用

当前实现只有：

```rust
pub fn system_project_dir(_game_data: &mut GameData, _dir: &Variant) -> Result<Variant> {
    Ok(Variant::Nil)
}
```

因此可高置信度确认：

- 该调用不会设置项目目录；
- 不会改变 `app_base_path()`；
- 不会修改 VFS 根目录或映射表；
- 不会读取参数；
- 总是返回 `Nil`。

### 3.4 名称层面的保守推断

`SysProjFolder` 可以拆解为：

- `Sys`：系统层接口；
- `Proj`：project / project configuration；
- `Folder`：文件夹 / 目录。

因此它原版可能用于：

- 设置或切换项目目录；
- 指定工程资源的基础文件夹；
- 兼容某些旧版游戏启动器或开发工具的项目路径初始化；
- 读取/登记某个项目目录参数。

但是，当前 reference 中没有：

- 参数具体类型说明；
- 返回路径的实现；
- `GameData` 中对应的项目目录字段；
- VFS 根路径变更调用；
- 可交叉验证的脚本调用样例。

所以不能把它写死为“设置项目目录”或“返回项目目录”。

### 3.5 结论

> `SysProjFolder` 是一个与项目目录/系统路径相关的兼容接口；当前 rfvp 实现为 no-op，具体原版作用未知。

---

## 4. `SysAtSkipName`

### 4.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5953)
- **签名**：`SysAtSkipName(arg0, arg1)`
- **返回值**：`Nil`
- **数据库影响子系统**：`system/path`
- **数据库控制流**：无 yield / wait / sleep / halt

### 4.2 入参语义

数据库当前仅记录：

- `arg0`
  - 类型：`Variant`；
  - 含义：`arg1`；
  - `confidence=generic`。
- `arg1`
  - 类型：`Variant`；
  - 含义：`arg2`；
  - `confidence=generic`。

源码函数签名是 [`system_at_skipname(_game_data, _arg0, _arg1)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:92-98)，参数命名同样没有揭示具体类型。

从名字看，`AtSkipName` 可能与以下概念有关：

- `skip name`：跳过名称；
- 某种路径名/文件名过滤；
- 资源枚举时的名称跳过规则；
- 脚本执行或系统文件处理时的特殊名称登记。

但这些都只是命名推断，不是当前实现已经证实的语义。

### 4.3 当前 rfvp 具体作用

当前实现只有：

```rust
pub fn system_at_skipname(
    _game_data: &mut GameData,
    _arg0: &Variant,
    _arg1: &Variant,
) -> Result<Variant> {
    Ok(Variant::Nil)
}
```

因此可以高置信度确认：

- 两个入参都不会被读取；
- 不会登记 skip-name 表；
- 不会修改 VFS 路径或文件过滤规则；
- 不会影响 TextSkip、ControlMask 或其他跳过系统；
- 不会改变 VM 控制流；
- 总是返回 `Nil`。

### 4.4 与文本/流程跳过功能的边界

虽然 `skip name` 的名称容易让人联想到“跳过文本”或“快进”，但当前没有证据表明它对应：

- `TextSkip` 的文字跳过；
- `ControlMask` 的控制屏蔽；
- 菜单消息跳过；
- 场景标签跳过；
- 函数名或脚本标签过滤。

数据库将其归为 `system/path`，这更支持它可能属于系统名称或路径处理，而不是直接的文本显示控制。

### 4.5 结论

> `SysAtSkipName` 是一个名称上可能与系统路径/名称跳过规则有关的双参数兼容接口；当前 rfvp 实现为 no-op，原版具体语义未知。

---

## 5. 两条接口的共同特征

### 5.1 都是即时返回的兼容接口

两条 syscall 都满足：

- 返回 `Nil`；
- 不产生资源加载；
- 不产生文件系统写入；
- 不改变当前 context 状态；
- 不需要等待宿主系统返回结果。

### 5.2 都没有已确认的输出值

虽然 `SysProjFolder` 的名称可能让人期待返回路径，`SysAtSkipName` 的名称可能让人期待返回匹配结果，但当前实现没有任何 `String`、`Int` 或 `BoolLike` 返回路径：

- `SysProjFolder` 不返回目录字符串；
- `SysAtSkipName` 不返回匹配/跳过状态；
- 两者都固定返回 `Nil`。

### 5.3 对脚本兼容性的实际意义

这类 no-op handler 的工程意义可能是：

1. 保留旧 HCB 导入表中的符号；
2. 让脚本能够继续运行，而不会因为找不到 syscall 直接失败；
3. 暂时忽略当前 rfvp 尚未实现的宿主系统功能；
4. 为后续真实实现保留接口位置。

因此不能把“当前返回 Nil”误认为“原版 syscall 本来就没有作用”。更准确的说法是：

> **当前 rfvp 选择以兼容 no-op 方式承接这两个系统接口。**

---

## 6. System 组整体语义

System 组只有两条接口，且当前均为 no-op，因此无法像 Prim、Sound、Save 等组一样恢复出完整的运行时工作流。

按名称和数据库影响子系统，最保守的整体描述是：

> **FVP 中用于承接旧版系统路径、项目目录和名称过滤相关脚本调用的兼容接口层。**

当前可确认的调用流程只有：

```text
SysProjFolder(arg0)    -> Nil
SysAtSkipName(arg0, arg1) -> Nil
```

没有证据证明它们之间存在调用顺序依赖，也没有证据证明某条调用会为另一条设置共享状态。

---

## 7. 高置信度结论

以下结论比较稳：

- `System` 分组当前共有 2 个 syscall。
- 两条分别是 `SysAtSkipName` 和 `SysProjFolder`。
- `SysProjFolder` 有 1 个参数，`SysAtSkipName` 有 2 个参数。
- 两条 syscall 的数据库参数目前都是 `Variant` generic 占位。
- 两条 syscall 当前都返回 `Nil`。
- 两条 syscall 当前都不产生 VM 调度副作用。
- [`SysProjFolder`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:88-90) 当前不修改任何项目目录或路径状态。
- [`SysAtSkipName`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:92-98) 当前不登记或处理任何名称跳过规则。
- 数据库把两条接口影响子系统标为 `system/path`，但其具体原版路径语义仍需运行时验证。

---

## 8. 仍需保守处理的点

1. `SysProjFolder` 的参数是否应该是字符串路径、路径 ID、布尔开关或其他 Variant 类型，当前没有证据确认。
2. `SysProjFolder` 原版是设置目录、查询目录、登记目录，还是通知宿主切换目录，当前无法区分。
3. `SysAtSkipName` 的两个参数分别代表名称、路径、索引、模式或开关，当前均未知。
4. `SysAtSkipName` 中 `skipname` 的“跳过”对象可能是文件名、资源名、脚本名或其他名称，当前不能强行命名。
5. 当前 rfvp 的 no-op 行为不等同于原引擎无副作用；后续应通过旧版二进制逆向、HCB 调用样例或实机追踪恢复其真实作用。

---

## 9. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:112-113)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5950-6029)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:136-137)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:129-130)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:543-546)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:88-98)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:303-322)
- [`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:39-56)
- [`README.md`](fvp_analysis/reference/rfvp-0.3.0/setsumei/README.md:1)
