# Save 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:101)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:2160-2270,4808-5316) 与 rfvp 参考实现，`Save` 分组当前包含 14 个 syscall：

1. `LoadFile`
2. `LoadQuick`
3. `LoadTitle`
4. `QuickCopy`
5. `QuickState`
6. `SaveCreate`
7. `SaveData`
8. `SaveFile`
9. `SaveLoadMenu`
10. `SaveName`
11. `SaveQuick`
12. `SaveThumbSize`
13. `SaveTitle`
14. `SaveWrite`

其中：

- [`SaveCreate`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:20) 、[`SaveData`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:75)、[`SaveThumbSize`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:285)、[`SaveWrite`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:301) 是现代存档实现的核心接口；
- [`LoadFile`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:339)、[`LoadQuick`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:428)、[`LoadTitle`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:362)、[`SaveFile`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:350)、[`SaveLoadMenu`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:444)、[`SaveName`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:450)、[`SaveQuick`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:435)、[`SaveTitle`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:371) 属于旧版/兼容接口。

`Save` 组的整体语义可以概括为：

> **围绕存档元数据准备、缩略图设置与读取、存档槽操作、快速存读档、旧版存档菜单以及异步写盘的一组接口。**

需要特别注意：[`Load`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:329) 在 `syscall_spec.json` 中属于独立的 `Load` 分组，因此本文不重复分析它；但 `LoadQuick`、`LoadFile`、`LoadTitle` 仍严格按数据库的 `group = Save` 纳入本文。

---

## 2. 存档模型与共享约定

### 2.1 存档槽范围

现代 [`SaveManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:1) 使用最多 1000 个槽位，当前 syscall 层统一接受：

- `slot = Int`
- 有效范围：`0..=999`

槽位既可以是玩家存档槽，也可以是脚本内部使用的中转/缓存槽。具体某个高编号槽位在单个游戏中的业务含义，需要结合调用方继续分析，不能仅凭 syscall 名称固定命名。

### 2.2 存档文件与缓存

[`SaveManager::refresh_all_savedata()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:606) 会扫描存档目录中的 `s数字.bin` 文件，并把成功解析的条目放入槽位缓存。单个槽位也可以通过 [`load_savedata()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:666) 刷新。

当前实现的存档系统至少包含：

- 存档头部元数据；
- 缩略图；
- 脚本内容；
- 可选的 rfvp 扩展状态块；
- 槽位缓存和当前存档状态。

### 2.3 保存是“两阶段”流程

现代保存不是单个 syscall 立即完成的同步写文件，而是分成两个阶段：

1. **准备阶段**：捕获当前画面缩略图、元数据以及可选运行时状态，形成内存中的 `local_saved`；
2. **提交阶段**：把已经准备好的内存存档写入目标槽位。

对应关系是：

- [`SaveCreate(3, value)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:49) 请求准备 `local_saved`；
- [`SaveWrite(slot)`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:301) 请求提交到指定槽位。

[`SaveManager::pending_save_capture()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:691) 会把截图请求交给宿主循环；[`finalize_local_savedata_prepare()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:738) 完成内存存档；之后 [`try_commit_local_savedata()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:768) 或 [`finalize_save_write()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:799) 执行写盘。

### 2.4 返回值约定

Save 组大部分修改型接口返回 `Nil`。查询型或分支型接口可能返回：

- `BoolLike`：`True/Nil`；
- `Int`：时间字段、状态或其他数值；
- `String`：标题、场景标题或脚本文本；
- `Mixed`：由 `fnid` 决定返回类型。

数据库中 [`SaveData`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4976) 记录为 `Mixed<Int|String|BoolLike|Nil>`，这是合理的；但部分 legacy 接口的完整原版返回语义仍不足以恢复。

---

## 3. `SaveCreate`

### 3.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4932)
- **签名**：`SaveCreate(fnid, value)`
- **返回值**：`Nil`

### 3.2 入参语义

- `fnid`
  - 类型：`Int`
  - 当前实现支持 `0..3`。
- `value`
  - 类型：`Variant`
  - 实际类型取决于 `fnid`。

### 3.3 `fnid` 分支

#### `fnid = 0`：设置存档标题

- `value`：`String | ConstString`
- 作用：写入 [`SaveManager::current_title`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:363)；
- 语义：当前游戏/作品标题。

#### `fnid = 1`：设置场景标题

- `value`：`String | ConstString`
- 作用：写入 [`current_scene_title`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:359)；
- 语义：当前场景、章节或对话段标题。

#### `fnid = 2`：设置脚本内容

- `value`：`String | ConstString`
- 作用：写入 [`current_script_content`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:367)；
- 语义：保存时附带的脚本位置/脚本内容描述。

#### `fnid = 3`：准备内存存档

- `value`：通常是 `Nil` 或 `Int`；
- 作用：请求捕获当前画面与状态形成 `local_saved`；
- 若 `value` 是 `0..=999` 的整数，还会把它作为待提交槽位；
- 调用 [`thread_wrapper.should_break()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:64-65)，让宿主循环尽快执行截图/准备步骤。

### 3.4 具体作用

[`save_create()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:20-73) 是一个多功能准备接口，而不是单纯“创建空文件”：

- `0/1/2` 负责准备待写入的存档元数据；
- `3` 负责准备内存中的存档载荷；
- 真正写入磁盘通常由 [`SaveWrite`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:301) 完成。

### 3.5 控制流与结论

- `fnid=0/1/2`：不产生 VM 调度副作用；
- `fnid=3`：会请求 break/yield 风格的宿主切换；
- 所有分支返回 `Nil`。

> `SaveCreate` 是 **存档元数据设置与内存存档准备的多路复用接口**。

---

## 4. `SaveData`

### 4.1 参数与返回

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4979)
- **签名**：`SaveData(fnid, value, value2)`
- **返回值**：`Mixed<Int|String|BoolLike|Nil>`

### 4.2 参数语义

- `fnid`
  - 类型：`Int | Nil`
  - `Nil`：当前实现直接返回 `Nil`；
  - 整数：选择具体存档子操作。
- `value`
  - 类型：`Variant`
  - 通常是槽位号、源槽位或目标槽位。
- `value2`
  - 类型：`Variant`
  - 主要用于目标槽位或纹理 ID。

### 4.3 `fnid` 子操作表

| fnid | 名称 | `value` | `value2` | 返回值 | 作用 |
|---:|---|---|---|---|---|
| 0 | `RefreshAll` | 忽略 | 忽略 | `Nil` | 扫描并刷新全部存档槽缓存 |
| 1 | `TestSaveData` | `slot: Int` | 忽略 | `True/Nil` | 测试槽位是否存在 |
| 2 | `DeleteSaveData` | `slot: Int` | 忽略 | `Nil` | 删除槽位存档 |
| 3 | `CopySaveData` | 源 `slot` | 目标 `slot` | `Nil` | 复制存档槽 |
| 4 | `GetSaveTitle` | `slot: Int` | 忽略 | `String` | 读取作品标题 |
| 5 | `GetSaveSceneTitle` | `slot: Int` | 忽略 | `String` | 读取场景标题 |
| 6 | `GetScriptContent` | `slot: Int` | 忽略 | `String` | 读取脚本内容字段 |
| 7 | `GetYear` | `slot: Int` | 忽略 | `Int` | 读取保存年份 |
| 8 | `GetMonth` | `slot: Int` | 忽略 | `Int` | 读取保存月份 |
| 9 | `GetDay` | `slot: Int` | 忽略 | `Int` | 读取保存日期 |
| 10 | `GetDayOfWeek` | `slot: Int` | 忽略 | `Int` | 读取星期字段 |
| 11 | `GetHour` | `slot: Int` | 忽略 | `Int` | 读取保存小时 |
| 12 | `GetMinute` | `slot: Int` | 忽略 | `Int` | 读取保存分钟 |
| 13 | `LoadSaveThumbToTexture` | `slot: Int` | `texture_id: Int` | `Nil` | 读取缩略图并装入 graph/texture 槽 |

枚举映射见 [`SaveDataFunction`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:9-46)。

### 4.4 各类子操作的具体作用

#### 刷新与槽位管理：`fnid=0..3`

- [`RefreshAll`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:92-98) 刷新全部存档缓存；
- [`TestSaveData`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:151-162) 返回槽位存在性；
- [`DeleteSaveData`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:163-169) 删除存档；
- [`CopySaveData`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:170-185) 复制源槽位到目标槽位。

#### 元数据读取：`fnid=4..12`

这些分支会先尝试加载指定槽位，再读取字段：

- 标题；
- 场景标题；
- 脚本内容；
- 年、月、日、星期；
- 时、分。

其中前三项返回 `String`，时间字段返回 `Int`。若槽位无效或读取失败，当前实现通常返回 `Nil` 或默认字段值；具体失败分支需要结合 [`SaveManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:471-578) 的字段默认值理解。

#### 缩略图加载：`fnid=13`

- `value`：存档槽位 `0..=999`；
- `value2`：目标纹理槽位 `0..=4095`；
- 前提：必须先调用 [`SaveThumbSize`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:285) 设置非零缩略图尺寸；
- 作用：从存档取出缩略图，调用 [`load_texture_from_buff()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/motion_manager/mod.rs:1) 写入目标 graph/texture 槽，再刷新相关 prim。

### 4.5 控制流与结论

大多数 `SaveData` 子操作不需要 yield；数据库把 `conditional=true` 标记为保守描述，主要是因为某些保存准备/资源操作会触发宿主侧处理。当前具体的 `SaveData` 函数体没有统一的 `should_break()` 路径。

> `SaveData` 是 **存档槽管理、存档元数据读取、时间字段读取和缩略图装载的 fnid 多路复用接口**。

---

## 5. `SaveThumbSize`

### 5.1 参数与返回

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5199)
- **签名**：`SaveThumbSize(width, height)`
- **返回值**：`Nil`

### 5.2 入参语义

- `width`
  - 类型：`Int`
  - 有效范围：`20..=200`
- `height`
  - 类型：`Int`
  - 有效范围：`15..=150`

无效类型或超范围参数不会更新当前设置。

### 5.3 具体作用

[`save_thumb_size()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:285-298) 设置 [`SaveManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:353-356) 后续截图/缩略图的目标尺寸。

它本身不捕获缩略图，也不写入存档；它只是为后续：

- `SaveCreate(3, ...)`；
- `SaveWrite(slot)`；
- `SaveData(13, slot, texture_id)`；

提供尺寸配置。

### 5.4 结论

> `SaveThumbSize` 是 **设置存档缩略图宽高的准备接口**。

---

## 6. `SaveWrite`

### 6.1 参数与返回

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5281)
- **签名**：`SaveWrite(slot)`
- **返回值**：`Nil`

### 6.2 入参语义

- `slot`
  - 类型：`Int`
  - 有效范围：`0..=999`
  - 含义：目标存档槽。

### 6.3 具体作用

[`save_write()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:301-327) 的行为是请求写盘，而不是在 syscall 函数体中同步完成全部写入：

1. 校验目标槽位；
2. 如果还没有 `local_saved`，则请求先准备内存存档，并让当前 context break；
3. 设置 `savedata_requested=true`；
4. 设置 `current_save_slot=slot`；
5. 由宿主循环在后续帧执行截图、构造文件并写盘。

如果已有 `local_saved`，则可以跳过再次捕获当前画面，直接把准备好的内存存档提交到目标槽位：[`try_commit_local_savedata()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:768-796)。

### 6.4 控制流与结论

数据库将其标为无 yield，但实现存在“没有 local_saved 时请求准备并 `should_break()`”的条件路径。因此更准确的描述是：

- 正常已有内存存档：只登记写入请求；
- 没有内存存档：可能触发一次宿主切换。

> `SaveWrite` 是 **把内存存档提交到指定槽位的异步写盘请求接口**。

---

## 7. Quick 兼容接口

## 7.1 Quick 槽范围

legacy quick 接口通过 [`get_quick_slot()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:163-168) 解析槽位：

- `Int(0..3)`：使用对应 quick slot；
- `Nil`：默认使用 quick slot 0；
- 其他类型：无效，返回 `Nil`。

因此 quick 接口的槽位范围不是现代普通存档的 `0..=999`，而是专门的 `0..=3`。

## 7.2 `QuickCopy`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4811)
- **签名**：`QuickCopy(src, dst)`
- **返回值**：`Nil`

### 入参语义

- `src`：`Int`，范围 `0..=3`；源 quick slot；
- `dst`：`Int`，范围 `0..=3`；目标 quick slot；
- `src == dst`：无效，不执行复制。

### 具体作用

[`quick_copy()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:400-414) 会先载入源槽位，再调用 [`copy_savedata()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:592-604) 复制到目标槽位。

> `QuickCopy` 是 **四个 quick slot 之间的存档复制接口**。

## 7.3 `QuickState`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:4859)
- **签名**：`QuickState(slot)`
- **返回值**：`BoolLike`

### 入参与作用

- `slot`：`Int(0..3)` 或 `Nil`；
- 返回 `True`：对应 quick slot 有存档；
- 返回 `Nil`：没有存档或参数无效。

具体实现见 [`quick_state()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:417-425)。

> `QuickState` 是 **quick slot 存在性查询接口**。

## 7.4 `SaveQuick`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5157)
- **签名**：`SaveQuick(slot)`
- **返回值**：`Nil`

### 入参与作用

- `slot`：`Int(0..3)` 或 `Nil`；
- `Nil` 默认使用 quick slot 0；
- 内部转调 [`save_write()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:301)。

它不是另一套独立存档格式，而是把 quick slot 解析后复用普通异步保存路径。

> `SaveQuick` 是 **旧版 quick-save 入口**。

## 7.5 `LoadQuick`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:2198)
- **签名**：`LoadQuick(slot)`
- **返回值**：`Nil`

### 入参与作用

- `slot`：`Int(0..3)` 或 `Nil`；
- `Nil` 默认 quick slot 0；
- 内部转调 [`load()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:329)。

因此它会继承普通 [`Load`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:329) 的 deferred load、dissolve 和 context break 语义，但使用 quick slot 兼容映射。

> `LoadQuick` 是 **旧版 quick-load 入口**。

---

## 8. legacy 菜单与标题接口

## 8.1 `LoadFile`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:2163)
- **签名**：`LoadFile()`
- **返回值**：`Nil`

[`load_file()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:336-342) 会：

- 写入待处理的 [`LegacySaveLoadRequest::LoadFile`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:70-75)；
- 标记旧版存档/读档菜单可见；
- 调用 `thread_wrapper.should_break()`。

当前 rfvp 没有完整的原版槽位选择 UI 消费者，因此这个 syscall 的主要确认语义是“发起旧版读档 UI 请求”。

> `LoadFile` 是 **legacy 文件读档菜单请求接口**。

## 8.2 `SaveFile`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5032)
- **签名**：`SaveFile()`
- **返回值**：`Nil`

[`save_file()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:346-354) 会：

- 请求准备 `local_saved`；
- 写入待处理的 `SaveFile` UI 请求；
- 调用 `should_break()`。

槽位选择留给宿主侧旧 UI / 兼容层处理。

> `SaveFile` 是 **legacy 文件存档菜单请求接口**。

## 8.3 `SaveLoadMenu`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5067)
- **签名**：`SaveLoadMenu(flag)`
- **返回值**：`Nil`

当前 [`save_load_menu()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:442-445) 是 no-op：

- 不读取 `flag` 的实际内容；
- 不打开现代槽位 UI；
- 不改变 VM 调度；
- 直接返回 `Nil`。

从命名与 legacy 逆向注释看，它原本可能用于切换旧 native 菜单壳层，但当前完整业务语义未恢复。

> `SaveLoadMenu` 是 **旧版存读档菜单壳层兼容接口，当前 rfvp 实现为空操作**。

## 8.4 `SaveName`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5109)
- **签名**：`SaveName(left, right)`
- **返回值**：`Nil`

### 入参语义

- `left`：`String | ConstString`，保存标题；
- `right`：`String | ConstString`，场景标题；
- 非字符串值会被当作缺省，不写入对应字段。

[`save_name()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:450-468) 会：

- 保存到 legacy UI 状态；
- 同步写入 `SaveManager.current_title`；
- 同步写入 `SaveManager.current_scene_title`。

> `SaveName` 是 **legacy 保存界面的双标题设置接口**。

## 8.5 `LoadTitle`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:2240)
- **签名**：`LoadTitle()`
- **返回值**：`Nil`

当前 [`load_title()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:358-363) 直接返回 `Nil`，不会打开槽位读档 UI。

逆向注释认为原版该接口可能切换 title-state 模式，让主循环恢复已经缓存的 title snapshot；当前 rfvp 没有独立 title-state cache，因此完整原版效果未实现。

> `LoadTitle` 是 **旧版标题状态恢复兼容接口，当前实现为 no-op**。

## 8.6 `SaveTitle`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:5246)
- **签名**：`SaveTitle()`
- **返回值**：`Nil`

当前 [`save_title()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:367-372) 直接返回 `Nil`。

逆向注释认为原版该接口可能把当前状态写入 title-state cache，并更新 native 菜单项；当前 rfvp 没有独立 title-state cache/menu shell，因此不能把它等同于普通 `SaveWrite`。

> `SaveTitle` 是 **旧版标题状态保存兼容接口，当前实现为 no-op**。

---

## 9. Save 组整体工作流

### 9.1 普通存档工作流

```text
SaveThumbSize(width, height)       // 设置缩略图尺寸
SaveCreate(0, title)               // 设置作品标题
SaveCreate(1, scene_title)         // 设置场景标题
SaveCreate(2, script_content)      // 设置脚本内容
SaveCreate(3, slot)                 // 请求准备 local_saved
SaveWrite(slot)                     // 请求提交到目标槽位
```

其中 `SaveCreate(3, ...)` 和 `SaveWrite(slot)` 可能跨越多个 VM tick，由宿主循环完成截图与写盘。

### 9.2 存档菜单读取工作流

```text
SaveData(0, nil, nil)              // 刷新全部槽位缓存
SaveData(1, slot, nil)              // 测试槽位
SaveData(4, slot, nil)              // 读取标题
SaveData(5, slot, nil)              // 读取场景标题
SaveData(13, slot, texture_id)     // 读取缩略图到纹理
```

### 9.3 Quick 工作流

```text
SaveQuick(slot_or_nil)
QuickState(slot_or_nil)
LoadQuick(slot_or_nil)
QuickCopy(src, dst)
```

Quick 接口只提供旧版 `0..3` 槽位映射，实际保存/读取仍复用 `SaveManager` 和普通存档路径。

### 9.4 Legacy 菜单工作流

```text
SaveFile() / LoadFile()
SaveName(left, right)
SaveLoadMenu(flag)
SaveTitle() / LoadTitle()
```

这些接口主要面向旧版 native 菜单、标题状态和兼容层。当前 rfvp 能确认请求登记与字段映射，但不能保证拥有完整原版 UI 行为。

---

## 10. 高置信度结论

以下结论比较稳：

- `Save` 分组当前共有 14 个 syscall。
- 普通存档槽位范围为 `0..=999`。
- Quick 槽位范围为 `0..=3`，`Nil` 通常代表 quick slot 0。
- `SaveCreate(0/1/2, value)` 分别设置作品标题、场景标题和脚本内容。
- `SaveCreate(3, value)` 请求准备内存中的 `local_saved`，必要时记录目标槽位并让当前 context break。
- `SaveWrite(slot)` 是异步提交/写盘请求，不应理解为 syscall 函数体内立即完成全部文件写入。
- `SaveThumbSize` 必须先设置有效宽高，缩略图捕获和 `SaveData(fnid=13)` 才有可靠尺寸配置。
- `SaveData` 是 `fnid` 多路复用接口，支持刷新、测试、删除、复制、元数据读取、时间读取和缩略图加载。
- `QuickCopy`、`QuickState`、`SaveQuick`、`LoadQuick` 是旧版 quick slot 兼容接口。
- `LoadFile` / `SaveFile` 主要负责登记 legacy UI 请求并让当前 context 让出执行。
- `SaveName` 把两个字符串映射到当前作品标题和场景标题。
- `SaveLoadMenu`、`LoadTitle`、`SaveTitle` 当前都是兼容性较强的接口，部分实现为 no-op。
- [`Load`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:329) 不属于本文的 Save 组，而属于独立 Load 组；`LoadQuick` 通过它复用读档路径。

---

## 11. 仍需保守处理的点

1. `SaveCreate(fnid=3)` 的 `value` 在不同原版脚本中可能表示目标槽位、空值或 UI 状态参数；当前 rfvp 只确认整数槽位会被记录，不能据此覆盖所有旧版语义。
2. `SaveData` 各元数据读取分支在槽位不存在、文件损坏和字段缺失时的原版返回差异，仍需更多实机验证。
3. `SaveData(fnid=13)` 的缩略图纹理槽位与具体 UI prim 的绑定关系属于调用方逻辑，不宜在 syscall 层固定某个纹理编号。
4. `SaveFile` / `LoadFile` 的 native 槽位选择 UI 当前没有完整 Rust 消费层，文档只能确认“请求登记 + context break”。
5. `SaveTitle` / `LoadTitle` 原版 title-state cache 的具体数据内容没有在当前 rfvp 中恢复，不能把它们简单等同于普通槽位存读档。
6. 数据库中部分 legacy Save 条目的 `affected_game_data_subsystems` 统一列出 `motion_manager` / `vfs`，但实际某些 no-op 分支并不访问这些子系统；本文按数据库字段保留，同时按源码实际行为补充说明。

---

## 12. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:101-104)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:2160-2270,4808-5316)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:55-59,112-123)
- [`saveload.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/saveload.rs:1-407)
- [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:336-468)
- [`save_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:1-46)
- [`save_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:353-407)
- [`save_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:461-606)
- [`save_manager.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/save_manager.rs:691-816)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:683-691,700-717)
- [`16_Load.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/16_Load.md:1-272)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:1-16)
