# FVP syscall 语义数据库说明

本目录由 `fvp_analysis` 阶段二生成，用于建立可供后续工程引用的 syscall 语义数据库。

## 文件说明

- `syscall_spec.json`：机器可读数据库，供后续脚本、IR、反编译器、编辑器引用。
- `syscall_spec.txt`：人类快速浏览用简表。
- `README.md`：本说明文档。

## 数据来源

主要依据：

1. `rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs` 中的 `SYSCALL_SPECS`。
2. `rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs` 中的 `SYSCALL_TBL` 注册表。
3. `rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/*.rs` 的实际实现。
4. `fvp_analysis/result/fvp_analysis项目规范文档.md` 与前期综述结论。

## JSON 顶层结构

```json
{
  "metadata": { ... },
  "syscalls": [ ... ]
}
```

## 单条 syscall 字段

| 字段 | 含义 |
|---|---|
| `name` | syscall 名称，即 HCB 导入表中的符号名。 |
| `group` | 功能分组，如 Text、Graph、Sound、Thread。 |
| `handler` | rfvp 中对应的 handler struct。 |
| `arg_count` | 参数数量。来自 generated.rs 或人工补充。 |
| `parameter_types` | 参数类型与含义；`confidence=generic` 表示仍需细化。 |
| `return_type` | 返回值类型。`BoolLike` 表示 `True/Nil`。 |
| `affected_game_data_subsystems` | 影响的 GameData 子系统。 |
| `control_flow` | 是否 yield / wait / sleep / text_wait / halt 等。 |
| `implementation_status` | 当前 rfvp 实现状态。 |
| `verification_status` | 语义可信度与待验证状态。 |
| `evidence_sources` | 证据来源文件。 |
| `notes` | 额外说明。 |

## 重要约定

### 1. 参数类型分级

本数据库目前采用两级参数信息：

- `confidence=known`：已依据源码或人工归纳填写具体类型。
- `confidence=generic`：仅依据参数数量生成 `Variant` 占位，后续需要逐项细化。

### 2. 返回值类型

- `Nil`：无有效返回或失败返回。
- `BoolLike`：FVP VM 风格布尔值，即 `True/Nil`。
- `Mixed<...>`：根据 `fnid` / `mode` 等分支返回不同类型。

### 3. 调度副作用

`control_flow` 字段用于后续 HCB 语义分析时判断该 syscall 是否会改变 VM 调度：

- `yield`：当前 context 可能让出执行。
- `wait`：进入计时等待。
- `sleep`：进入 sleep 状态。
- `text_wait`：进入文本显示等待。
- `dissolve_wait`：等待画面转场完成。
- `starts_context`：启动另一个脚本 context。
- `exits_context`：退出 context。
- `halt`：暂停宿主游戏推进，如 modal movie。

## 统计

- syscall 条目总数：`174`

### 按分组统计

| group | count |
|---|---:|
| Audio | 7 |
| Color | 1 |
| Control | 2 |
| Cursor | 3 |
| Debug | 2 |
| Dissolve | 2 |
| Exit | 2 |
| Flag | 2 |
| Gaiji | 1 |
| Graph | 2 |
| History | 2 |
| Input | 11 |
| LegacyCharacter | 3 |
| LegacyConfig | 4 |
| Lip | 2 |
| Load | 1 |
| Menu | 1 |
| Motion | 19 |
| Movie | 4 |
| Parts | 8 |
| Prim | 21 |
| Save | 14 |
| Snow | 3 |
| Sound | 9 |
| System | 2 |
| Text | 27 |
| Thread | 6 |
| Timer | 3 |
| Title | 1 |
| Utils | 3 |
| V3D | 5 |
| Window | 1 |

## 当前限制

1. 不是所有 syscall 的参数类型都已精确化；`generic` 参数需要在下一轮逐项细化。
2. 部分旧版/兼容 syscall 来自 `legacy.rs`，其语义可能只覆盖某些早期 FVP 游戏。
3. `stub_or_noop` 项不能视为完整原引擎语义。
4. 本数据库以 `rfvp` 为当前语义基线，后续仍需用原引擎实机行为校验。

## 后续建议

下一步建议基于 `syscall_spec.json` 继续生成：

- syscall 参数类型精修表。
- HCB 反编译器使用的 syscall effect model。
- 可视化脚本编辑器中的 syscall 自动补全/说明。
- 游戏创作 DSL 的标准库函数映射。

