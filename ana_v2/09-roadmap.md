# 09 · 研究路线图

> 本文总结当前已知的内容、仍存在的歧义点，以及通向"完整解析 HCB 并自由创作 FVP 游戏"目标的建议技术路线。

---

## 已经可以基本确认的内容

### HCB 层

- [x] 文件总体结构（`sys_desc_offset`、代码区、系统描述区）
- [x] 系统描述区全部字段（`entry_point`、全局变量数、`game_mode`、标题、导入表）
- [x] 所有 opcode `0x00`–`0x27` 的二进制编码与运行时语义
- [x] 函数调用/返回机制（`call`/`init_stack`/`ret`/`retv`）
- [x] 栈帧布局与局部变量访问
- [x] `push_string` 内联字符串与地址身份的关系
- [x] 地址修正规则（`sys_desc_offset`、`entry_point`、`call/jmp/jz`、ThreadStart 特例）
- [x] CHB = GBK 工作流下的 HCB 命名约定，非独立格式

### VM 层

- [x] 值类型 `Variant`（`Nil`/`True`/`Int`/`Float`/`String`/`ConstString`/`Table`）
- [x] 真假语义：`Nil` 为假，非 `Nil` 为真（非 C 风格整数布尔）
- [x] 32 个协作式调度的脚本上下文
- [x] 上下文状态位（RUNNING/WAIT/SLEEP/TEXT/DISSOLVE_WAIT）
- [x] 每帧循环：VM runner + 场景 update + 渲染

### Syscall 层

- [x] 导入表机制（序号 → 名字 → 宿主实现）
- [x] 174 个 syscall 的分组与基本语义（见 `syscall_spec.json`）
- [x] 控制流副作用分类（yield/wait/sleep/text_wait/…）
- [x] ThreadStart 函数指针特例

### 资源层

- [x] `.bin` simple BIN/FVP 结构（完整格式）
- [x] 标准 zlib HZC/NVSG 结构（完整格式）
- [x] `type` 字段（RGB24/RGBA32/多帧/灰度）
- [x] `offsetX/offsetY` 的场景合成语义
- [x] TLG-HZC 变体的识别方式
- [x] Loose file/folder 覆盖优先于 `.bin`（VFS 规则）
- [x] 文件名排序依赖日文 locale（`CompareStringA(0x411)`）

---

## 已能进入工程落地的内容

- HCB 文本提取与地址修正回封
- HCB → IR JSON → CFG → Lua-like IR 转换链
- IR JSON → HCB 回编译（round-trip 验证通过）
- BIN 封解包（读取/重建）
- 标准 HZC 预览与重建（含 `offsetX/offsetY` 保留）
- TLG-HZC 识别与转标准 HZC

---

## 当前已知歧义与待验证点

### opcode 层

| 问题 | 状态 |
|---|---|
| `0x08/0x09` 历史命名混淆（`pushtrue/pushfalse` 曾写反） | 本项目已采用 `rfvp` 语义：`0x08=push_nil`、`0x09=push_true` |
| `0x25/0x27` 比较助记符历史混淆 | 本项目已裁定：`0x25=set_ge`、`0x27=set_le` |
| `0x11/0x12/0x17/0x18`（表操作）在旧版引擎的一致性 | **[待验证]**，当前以 `rfvp` 为基线 |

### 引擎版本差异

| 问题 | 状态 |
|---|---|
| 旧版（Wiz 时代）与新版（HD/Steam）opcode 是否完全一致 | **[待验证]** |
| `ACPX/XPK` 旧式归档格式 | 已识别，超出当前主线范围 |
| 标准 zlib HZC 与 TLG-HZC 在不同作品中的分布 | **[待调查]** |

### 高层结构

| 问题 | 状态 |
|---|---|
| `custom_syscall_count` 的真实用途 | **[待验证]**，目前旧工具忽略，rfvp 读取但基本为 0 |
| `type=4`（灰度/黑白）HZC 的精确像素语义 | **[待验证]** |
| 多帧差分 HZC 的底图关联编码方式 | **[高可信但未全覆盖]** |
| FVP 原始开发脚本语言与当前 IR 的对应关系 | **[未知]**，可能永远无法恢复 |

---

## 建议技术路线

### 阶段一：规范化（已基本完成）

- [x] 建立统一术语体系
- [x] 规范 opcode 二进制编码与语义
- [x] 规范 HCB 文件结构
- [x] 规范 BIN / HZC 结构
- [x] 建立 syscall 语义数据库

### 阶段二：工具链（已建立雏形）

- [x] HCB → IR JSON（`hcb_to_ir.py`）
- [x] IR JSON → CFG（控制流图）
- [x] IR JSON → Lua-like IR（人类可读）
- [x] IR JSON → HCB（回编译，`ir_to_hcb.py`）
- [x] Round-trip 验证（`roundtrip_verify.py`）

### 阶段三：语义增强（进行中）

精化 syscall 参数类型（当前部分条目仍是 `confidence=generic`）：

- [ ] Text 域所有 syscall 的参数类型精确化
- [ ] Prim 域所有 syscall 的参数类型精确化
- [ ] Motion 域所有 syscall 的参数类型与 easing 参数含义
- [ ] 建立 HCB 反编译器使用的 syscall effect model

### 阶段四：结构化分析（待启动）

- [ ] CFG → 结构化 IR（`if/while` 还原，`ir_to_structured.py`）
- [ ] 常见功能块模式识别（文本打印块、资源加载块、线程启动块等）
- [ ] 自动标注 syscall 调用点的语义注释

### 阶段五：资源作者管线（待完善）

- [ ] PNG → 标准 HZC（带 `offsetX/offsetY` 保留的完整工作流）
- [ ] 标准 HZC ↔ TLG-HZC 双向转换
- [ ] BIN 打包工具（日文 locale 排序规则）
- [ ] Loose 资源覆盖的快速测试工作流文档化

### 阶段六：最小原创工程（终极目标）

能够：
1. 从零写一个最小可启动 HCB（主入口 + 几个 syscall 调用）
2. 搭配最小资源目录（`graph/`、`voice/`、`bgm/`）
3. 在 `rfvp` 上跑通
4. 有可用的 DSL 或高层 IR 编写工具

**一旦这一步完成，FVP 自由创作就从逆向问题进入内容工程问题。**

---

## 真正的瓶颈

不是"看不懂 HCB 文件长什么样"，而是：

> 1. **syscall 语义的宿主实现细节**：知道 `TextPrint` 接受什么参数，但不完全知道它对 TextManager 内部状态的全部影响。
> 2. **作者语言/高层 IR**：目前能做到"反汇编成可读 IR"，但还没有一套适合人手写的高层脚本语言→HCB 的完整编译链。

换句话说：

> 逆向层已经基本打通；创作层还需要继续建设。

---

## 延伸阅读

如果你想深入某个方向：

- **想懂 VM 执行细节**：读 `rfvp-0.3.0/crates/rfvp/src/script/context.rs`
- **想懂 syscall 的宿主实现**：读 `rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/*.rs`
- **想懂资源格式**：读 `GARbro-1.5.44/ArcFormats/Favorite/`
- **想懂汉化工程实践**：读民间文档（星空HD中文化攻略、Wiz 实操两篇、lilith 的星空HD记录）
- **想动手逆向**：用 `hcb_to_ir.py` 反汇编一个实际的 `.hcb` 文件，从最简单的函数开始读

---

← [返回目录](./README.md)
