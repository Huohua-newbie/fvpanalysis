# Window 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:112)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7940-7976) 与 rfvp 参考实现，`Window` 分组当前只有 1 个 syscall：

- `WindowMode`

其显式规格与注册位置见 [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:168) 与 [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:1)。

`WindowMode` 不是单纯的“切换窗口/全屏”接口，而是一个多模式窗口状态机：

> **根据 mode 参数设置或查询窗口呈现模式、独占全屏能力和首帧/焦点相关标志。**

---

## 2. `WindowMode`

### 2.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7943)
- **签名**：`WindowMode(mode)`
- **参数类型**：`Int`
- **有效范围**：`-1..=6`
- **返回值**：`Mixed<Int|BoolLike|Nil>`
- **控制流**：无 yield / wait / sleep / text_wait / dissolve_wait / halt。

### 2.2 共享状态

`WindowMode` 主要读写 [`GameData`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:147-152) 中的：

- `render_flag`：当前窗口/呈现模式；
- `can_fullscreen`：是否支持精确游戏分辨率独占全屏；
- `is_first_frame`：原版焦点/首帧兼容标志；
- `pending_render_flag`：等待宿主窗口后端实际应用的模式请求。

设置模式时，`set_render_flag()` 会同时写入当前 flag 和 pending request：[`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:408-416)。宿主 app 在后续窗口更新阶段读取 pending flag 并应用实际窗口状态。

---

## 3. mode 分支详解

## 3.1 `mode = 0`：窗口化

### 入参

- `mode`：`Int(0)`。

### 行为

设置内部 `render_flag = 0`，并请求宿主后端切换到窗口化模式：[`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:150-155)。

### 返回值

- 返回 `Int(0)`。

### 结论

> `WindowMode(0)` 请求窗口化显示。

---

## 3.2 `mode = 1`：普通全屏

### 入参

- `mode`：`Int(1)`。

### 行为

设置内部 `render_flag = 1`，表示非独占的普通全屏/全屏宿主表面模式：[`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:156-160)。

当前注释说明，该模式保持游戏画面的宽高比，不等同于精确游戏分辨率独占全屏。

### 返回值

- 返回 `Int(1)`。

### 结论

> `WindowMode(1)` 请求普通全屏模式。

---

## 3.3 `mode = -1`：精确游戏分辨率独占全屏

### 入参

- `mode`：`Int(-1)`。

### 行为

只有在 `GameData.can_fullscreen == true` 时，才设置内部 `render_flag = 2` 并请求精确游戏分辨率独占全屏。

如果当前平台不支持该模式，则不进入 `render_flag=2`，而是返回普通全屏语义 `Int(1)`：[`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:161-169)。

### 返回值

- 支持精确独占全屏：返回 `Int(-1)`；
- 不支持：返回 `Int(1)`。

### 平台应用

在宿主 app 中，如果实际应用 `render_flag=2` 失败，当前实现会记录错误并恢复窗口化模式：[`app.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/app.rs:668-681)。

### 结论

> `WindowMode(-1)` 请求精确游戏分辨率独占全屏；不支持时降级为普通全屏语义。

---

## 3.4 `mode = 2`：查询当前窗口模式

### 入参

- `mode`：`Int(2)`。

### 行为

读取内部 `render_flag` 并映射为脚本可见值：

| 内部 `render_flag` | 返回值 |
|---:|---:|
| `0` | `Int(0)` |
| `1` | `Int(1)` |
| `2` | `Int(-1)` |
| `3` | `Int(-2)` |
| 其他 | 原值 `Int` |

见 [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:170-179)。

### 结论

> `WindowMode(2)` 是当前窗口模式查询接口，而不是设置操作。

现有脚本样例明确使用：

```lua
__ret = __syscall("WindowMode", 2)
```

随后读取返回值并据此分支：[`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:750-761)。

### 关于返回 `-2`

当前代码保留了内部 `render_flag=3 -> -2` 的查询映射，但没有恢复 `render_flag=3` 的实际生产路径或呈现含义。因此 `-2` 应标记为兼容/待验证值，不应在当前文档中强行命名。

---

## 3.5 `mode = 3`：查询精确独占全屏能力

### 入参

- `mode`：`Int(3)`。

### 行为

读取 `GameData.can_fullscreen`：

- 支持精确游戏分辨率独占全屏：返回 `True`；
- 不支持：返回 `Nil`。

见 [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:180-187)。

### 能力来源

Windows 宿主初始化时会通过 `find_exact_game_video_mode()` 检查是否存在匹配的游戏分辨率模式：[`app.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/app.rs:2064-2067)。

移动平台则直接将 `can_fullscreen` 设为 `true`，因为移动宿主通常始终使用全屏表面：[`app.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/app.rs:2328-2331)。

### 结论

> `WindowMode(3)` 是 **查询平台是否支持精确游戏分辨率独占全屏的能力检测接口**。

---

## 3.6 `mode = 4`：设置首帧/焦点兼容标志为真

### 入参

- `mode`：`Int(4)`。

### 行为

设置 `GameData.is_first_frame = true`，返回 `Nil`：[`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:188-192)。

源码注释将其关联到原版 `WM_ACTIVATEAPP` 焦点丢失兼容路径，但当前函数本身不直接操作 OS 窗口消息。

### 结论

> `WindowMode(4)` 是 **设置原版首帧/焦点兼容标志的接口**，不是窗口模式切换。

---

## 3.7 `mode = 5`：设置首帧/焦点兼容标志为假

### 入参

- `mode`：`Int(5)`。

### 行为

设置 `GameData.is_first_frame = false`，返回 `Nil`：[`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:193-197)。

### 结论

> `WindowMode(5)` 是 **清除原版首帧/焦点兼容标志的接口**。

---

## 3.8 `mode = 6`：查询首帧/焦点兼容标志

### 入参

- `mode`：`Int(6)`。

### 行为

读取 `GameData.is_first_frame`：

- 为真：返回 `True`；
- 为假：返回 `Nil`。

见 [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:198-204)。

### 结论

> `WindowMode(6)` 是 **查询首帧/焦点兼容标志的接口**。

---

## 4. 非法参数

### 4.1 类型错误

如果参数不是 `Int`：

- 当前实现记录错误日志；
- 返回 `Nil`；
- 不修改窗口状态。

### 4.2 数值越界

当前实现只接受：

```text
-1 <= mode <= 6
```

其他整数返回 `Nil`，不修改 `render_flag` 或 `is_first_frame`：[`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:118-131)。

---

## 5. 移动平台差异

在 iOS/Android 条件编译路径下，窗口模式不会完全沿用桌面平台的窗口/独占全屏概念：

- `mode=0/1/-1`：统一暴露为全屏语义，返回 `Int(1)`；
- `mode=2`：返回 `Int(1)`；
- `mode=3`：返回 `True`；
- 宿主窗口始终采用全屏 OS 表面，并保持游戏画面宽高比。

见 [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:133-147) 与 [`app.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/app.rs:2328-2331)。

因此脚本不能假设 `WindowMode` 在桌面和移动平台返回完全相同的模式编号。

---

## 6. WindowMode 与脚本状态机

已有 HCB 样例显示，脚本通常不会只调用一次 `WindowMode`，而是：

1. 把请求模式保存到全局变量；
2. 调用 `WindowMode(a2)` 设置或查询；
3. 调用 `WindowMode(2)` 查询当前结果；
4. 比较返回值；
5. 根据结果更新脚本层窗口状态。

见 [`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:702-784)。

典型抽象流程：

```text
requested_mode = a2
WindowMode(requested_mode)
actual_mode = WindowMode(2)
if actual_mode == 0 then
    // 按窗口化结果继续处理
else
    // 按全屏/其他结果继续处理
end
```

这说明 `WindowMode` 的主要脚本语义是一个“设置/查询/能力检测”状态机，而不是单向命令。

---

## 7. 高置信度结论

以下结论比较稳：

- `Window` 分组当前只有 1 个 syscall：`WindowMode`。
- `WindowMode` 接受一个 `Int` 参数，合法范围为 `-1..6`。
- `mode=0`：设置窗口化并返回 `Int(0)`。
- `mode=1`：设置普通全屏并返回 `Int(1)`。
- `mode=-1`：请求精确游戏分辨率独占全屏，能力不足时返回 `Int(1)`。
- `mode=2`：查询当前模式，内部 `2` 映射为脚本值 `-1`，内部 `3` 映射为 `-2`。
- `mode=3`：查询精确独占全屏能力，返回 `True/Nil`。
- `mode=4/5`：设置 `is_first_frame` 标志；`4` 为真，`5` 为假。
- `mode=6`：查询 `is_first_frame`，返回 `True/Nil`。
- `WindowMode` 不产生 VM yield/wait/sleep/text_wait/dissolve_wait/halt。
- 移动平台对窗口模式进行全屏语义归一化。

---

## 8. 仍需保守处理的点

1. 内部 `render_flag=3` 及脚本可见返回 `-2` 的生产路径和实际显示意义当前没有完全恢复。
2. `is_first_frame` 的准确原版业务名称可能与当前字段名不同；当前只能确认它参与兼容性状态管理。
3. 精确独占全屏的实际切换结果取决于平台可用显示模式，syscall 返回成功请求并不等同于宿主窗口最终一定切换成功。
4. 移动平台的返回值是脚本兼容映射，不应直接解释为桌面窗口状态。
5. 现有 HCB 样例显示脚本会把 WindowMode 结果保存到全局状态并进行二次判断，但具体全局变量的游戏业务含义属于调用方逻辑，不在 syscall 层固定命名。

---

## 9. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:112-114)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7940-7976)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:168)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:100-208)
- [`utils.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/utils.rs:325-333)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:147-152,297-320,408-420)
- [`app.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/app.rs:668-681,2064-2067,2328-2331)
- [`Sakura.lua典型功能块讲解.md`](fvp_analysis/result/hcbtool_test/Sakura.lua典型功能块讲解.md:702-784)
- [`fvp_analysis项目规范文档.md`](fvp_analysis/result/fvp_analysis项目规范文档.md:230-232,348-350)
- [`FVP引擎文献综述.md`](fvp_analysis/result/FVP引擎文献综述.md:299-301,577-579)
