# History 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](../README.md)、[`syscall_spec.txt`](../syscall_spec.txt) 与 rfvp 参考实现，History 分组当前包含 2 个 syscall：

1. `HistoryGet`
2. `HistorySet`

其注册位置可见于：

- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:45-46)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:565-567)

综合源码与脚本调用样例，History 分组可以概括为：

> **文本历史记录（history/backlog）读写接口。**

它们不是普通数组访问，也不是全局变量槽，而是专门围绕“历史文本记录”进行结构化存取的一组 syscall。

---

## 2. 共享实现约定

## 2.1 作用对象

History 分组直接作用于 `history_manager`：

- `set_name(...)`
- `set_content(...)`
- `set_voice(...)`
- `push()`
- `get_name(idx)`
- `get_content(idx)`
- `get_voice(idx)`
- `len()`

这些接口都通过 [`history_set()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:9-60) 与 [`history_get()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:62-110) 被调用。

这说明它们操作的是一套**专门的历史记录管理器**，而不是任意 KV 容器。

## 2.2 历史记录的三元结构

从 [`history_set()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:23-56) 与 [`history_get()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:90-107) 可看出，History 系统的核心字段至少有三类：

- `Name`
- `Content`
- `Voice`

因此每条历史记录可以近似理解为：

> **说话人名字 + 正文内容 + 语音编号/语音句柄标识** 的组合。

这与视觉小说常见 backlog 设计高度一致。

## 2.3 返回值风格

- [`HistorySet`](#4-historyset) 返回 `Nil`
- [`HistoryGet`](#3-historyget) 返回值是混合型：
  - `Int`
  - `String`
  - `Nil`

这与 [`syscall_spec.txt`](../syscall_spec.txt:39-40) 中的记载一致：

- `HistoryGet | Mixed<Int|String|Nil>`
- `HistorySet | Nil`

---

## 3. `HistoryGet`

### 3.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:45)
- **签名**：`HistoryGet(kind, idx)`
- **返回值**：`Mixed<Int|String|Nil>`

### 3.2 双模式语义

[`history_get()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:62-110) 明确有两种模式：

#### 模式 A：`kind == nil`

- 直接返回历史记录总数：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:66-68)
- 返回类型为 `Int`

因此：

> `HistoryGet(nil, anything)` 表示 **查询当前历史记录条数**。

#### 模式 B：`kind != nil`

`kind` 被解释为字段类型：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:70-107)

- `0 = Name`
- `1 = Content`
- `2 = Voice`

而 `idx` 表示历史记录序号：

- `0 = 最新一条`
- `1 = 倒数第二条`
- 以此类推：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:115-118)

### 3.3 字段映射与返回类型

根据实现：

- `kind = 0` -> `get_name(idx)` -> `String | Nil`
- `kind = 1` -> `get_content(idx)` -> `String | Nil`
- `kind = 2` -> `get_voice(idx)` -> `Int | Nil`

因此可整理为：

| kind | 语义 | 返回类型 |
|---:|---|---|
| `nil` | 历史总条数 | `Int` |
| `0` | 名字 | `String|Nil` |
| `1` | 正文 | `String|Nil` |
| `2` | 语音 | `Int|Nil` |

### 3.4 参数边界

- `kind` 必须是 `nil` 或可转成 `Int`
- `idx` 必须可转成 `Int`
- `idx < 0` 直接返回 `Nil`：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:86-88)

因此它不是“越界抛错型”接口，而是：

> **弱失败、返回 `Nil` 的读取接口。**

### 3.5 脚本样例

#### 样例 1：按字段读最新历史项

[`f_0008B9B5.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008B9B5.lua:24-37) 很典型：

- `HistoryGet(0, a2)` -> 名字
- `HistoryGet(1, a2)` -> 正文
- `HistoryGet(2, a2)` -> 语音

然后：

- 用名字控制 backlog 项图元显示：[`f_0008B9B5.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008B9B5.lua:39-68)
- 用正文做 [`TextPrint`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008B9B5.lua:82-84)

这说明 `HistoryGet` 直接服务于**历史回看 UI**。

#### 样例 2：读取最新 voice 并派生音频路径

[`f_000505FA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000505FA.lua:11-28) 中：

- `HistoryGet(0, 0)` 先取最新一条历史记录的某个字段
- 结果被送入后续字符串/音频处理函数

虽然从局部看还需结合上游判定具体字段语义，但至少可以确认：

> 历史记录不仅用于文字显示，也会被拿来恢复语音播放上下文。

---

## 4. `HistorySet`

### 4.1 参数与返回

- **参数个数**：2：[`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:46)
- **签名**：`HistorySet(fnid, value)`
- **返回值**：`Nil`

### 4.2 双模式语义

[`history_set()`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:9-60) 也有两种模式：

#### 模式 A：`fnid == nil`

- 调 `history_manager.push()`：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:10-13)
- 返回 `Nil`

这说明：

> `HistorySet(nil, anything)` 表示 **提交/压入当前历史记录条目**。

也就是说，名字、内容、语音等字段往往是先分别设置，再统一 `push()` 入历史列表。

#### 模式 B：`fnid != nil`

`fnid` 被解释为字段 ID：

- `0 = Name`
- `1 = Content`
- `2 = Voice`

对应实现分别调用：

- `set_name(...)`：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:23-33)
- `set_content(...)`：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:34-43)
- `set_voice(...)`：[`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:44-53)

### 4.3 参数类型

根据实现：

- `fnid = 0/1` 时，`value` 需要是 `String`
- `fnid = 2` 时，`value` 需要是 `Int`

因此可整理为：

| fnid | 语义 | value 类型 |
|---:|---|---|
| `nil` | push 当前历史项 | 忽略/任意 |
| `0` | 设置名字 | `String` |
| `1` | 设置正文 | `String` |
| `2` | 设置语音 | `Int` |

### 4.4 脚本样例

[`f_0004CF35.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004CF35.lua:156-163) 中有很标准的三连写：

- `HistorySet(0, G[234])`
- `HistorySet(1, G[231])`
- `HistorySet(2, G[293])`

这正好对应：

- 名字
- 正文
- 语音

随后通常还会在别处调用 `HistorySet(nil, nil)` 或等价路径把这条记录真正压入 backlog。虽然当前这段局部未直接显示 `push()`，但从 `history_set()` 的设计可以清楚推出这一阶段性工作流。

### 4.5 语义判断

因此 `HistorySet` 的本质是：

> **构建或提交一条历史记录。**

更细一点说，它分成两类职责：

1. **写字段**：名字/正文/语音
2. **提交条目**：`fnid = nil` 时 `push()`

---

## 5. History 分组的整体工作流

从源码与脚本模式看，History 分组的典型流程是：

1. `HistorySet(0, name)`
2. `HistorySet(1, content)`
3. `HistorySet(2, voice_id)`
4. `HistorySet(nil, nil)` 把当前条目提交到 history list
5. 之后在 backlog UI 里用 `HistoryGet(kind, idx)` 读取并显示

因此这组 syscall 的整体语义可以概括为：

> **面向 backlog/历史文本系统的结构化记录接口。**

---

## 6. 高置信度结论

以下结论比较稳：

- History 分组当前包含 `HistoryGet` 与 `HistorySet` 两个 syscall。
- `HistoryGet(nil, _)` 返回历史记录总数。
- `HistoryGet(0/1/2, idx)` 分别返回 名字/正文/语音。
- `HistorySet(0/1/2, value)` 分别设置 名字/正文/语音。
- `HistorySet(nil, _)` 用于把当前组装好的条目 `push()` 进历史列表。
- `idx = 0` 表示最新一条历史记录。
- 这组 syscall 的消费者主要是 backlog UI 与语音恢复逻辑。

---

## 7. 仍需保守处理的点

1. `history_manager.push()` 的精确时机与“是否在每句文本结束后自动触发”还需要继续从更多脚本路径补证。
2. `Voice` 字段在不同游戏里可能是语音编号、语音槽索引或可拼接路径片段；当前只能高置信度说它是 `Int` 型语音关联字段。
3. Sakura 的历史系统调用点多被包装函数包裹，若要做更细的“字段业务含义标注”，仍需逐函数链扩展。

---

## 8. 证据来源

- [`README.md`](../README.md:29-44)
- [`syscall_spec.txt`](../syscall_spec.txt:39-40)
- [`generated.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:45-46)
- [`world.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:565-567)
- [`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:9-60)
- [`history.rs`](../../../reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/history.rs:62-110)
- [`FVP引擎文献综述.md`](../FVP引擎文献综述.md:156-180)
- [`f_0004CF35.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004CF35.lua:156-163)
- [`f_000505FA.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_000505FA.lua:11-28)
- [`f_0008B9B5.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008B9B5.lua:24-37)
- [`f_0008B9B5.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008B9B5.lua:82-84)
- [`f_0008A465.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0008A465.lua:176-177)
- [`f_0004D3E2.lua`](../../hcbtool_test/Sakura_hcb_ir/Sakura/f_0004D3E2.lua:226-227)
