# [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 详细解析

## 1. 总结

[`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 是 Sakura 正文脚本最常用的**文本输出包装器**。它本身并不直接执行 `TextPrint`，而是把文本和显示控制参数交给 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1) 建立正文文本状态，再根据第五参数选择性执行一次历史记录/阅读状态更新，最后调用 [`f_0004DF22()`](Sakura_hcb_ir/Sakura/f_0004DF22.lua:1) 进入正文显示后的推进、输入等待和 UI 收束流程。

其高层伪代码是：

```lua
function f_0004CEFD(text, size_mode, speed_mode, quote_mode, read_mode)
    f_0004CD33(text, size_mode, speed_mode, quote_mode)

    if read_mode == -1 then
        f_0006A924()
    end

    f_0004DF22()
end
```

需要特别注意：当前 Lua-like 导出存在参数槽编号偏移。导出函数体里出现的 `a1/a2/a3/a4/a5`，对应调用者实际传入的第 1–5 个参数；导出的 `a0` 不是本函数实际使用的第一个用户参数。原始 HCB 应以 `push_stack -6/-5/-4/-3/-2` 为准。

---

## 2. 函数定位与原始控制流

### 2.1 地址和规模

- 函数地址：`0x0004CEFD`。
- 原始起始偏移：`315133`。
- `init_stack args=5, locals=0`，见 [`Sakura.ir.json`](Sakura_hcb_ir/Sakura.ir.json:1231415)。
- 函数主体只有一个条件分支和两个下游调用，CFG 见 [`Sakura.cfg.json`](../../03_data/cfg/Sakura.cfg.json:298821)。
- 在 [`Sakura.function_calls.csv`](Sakura_hcb_ir/Sakura.function_calls.csv:4811) 中统计为约 `56865` 次调用，是正文脚本中的高频公共入口。

### 2.2 原始指令级对应

| 地址 | 原始操作 | 作用 |
|---|---|---|
| `0x0004CEFD` | `init_stack args=5, locals=0` | 建立五参数函数栈。 |
| `0x0004CF00` | `push_stack -6` | 取第 1 个真实参数。 |
| `0x0004CF02` | `push_stack -5` | 取第 2 个真实参数。 |
| `0x0004CF04` | `push_stack -4` | 取第 3 个真实参数。 |
| `0x0004CF06` | `push_stack -3` | 取第 4 个真实参数。 |
| `0x0004CF08` | `call 0x0004CD33` | 调用正文文本状态构建函数。 |
| `0x0004CF0D` | `push_stack -2` | 取第 5 个真实参数。 |
| `0x0004CF0F` | `push_i8 -1` | 压入特殊值 `-1`。 |
| `0x0004CF11` | `set_e` | 判断第 5 参数是否等于 `-1`。 |
| `0x0004CF12` | `jz 0x0004CF1C` | 若不是 `-1`，跳过特殊处理。 |
| `0x0004CF17` | `call 0x0006A924` | 第 5 参数为 `-1` 时执行一次附加处理。 |
| `0x0004CF1C` | `call 0x0004DF22` | 进入正文显示/等待/推进流程。 |
| `0x0004CF21` | `ret` | 返回。 |

对应的反编译结果见 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:154847)。

因此，第五参数并没有被传入 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1)，它只影响 `f_0004CEFD()` 自己是否调用 [`f_0006A924()`](Sakura_hcb_ir/Sakura/f_0006A924.lua:1)。

---

## 3. 五个入参的总体表

| 实际参数 | 导出中主要名称 | 传递/读取位置 | 当前最可靠语义 | 置信度 |
|---|---|---|---|---|
| 第 1 参数 | `a1` | 传给 `f_0004CD33()`，最终写入 `G[231]`、`G[238]` | **正文文本内容**；也可为 `nil`，表示只推进/刷新而不追加文本 | 高 |
| 第 2 参数 | `a2` | 传给 `f_0004CD33()`，再传给 `f_0004D5B7()` | **文本字号/尺寸模式**，不是普通字符内容；`nil` 时使用默认尺寸路径 | 高 |
| 第 3 参数 | `a3` | 传给 `f_0004CD33()`，再传给 `f_0004D6A7()` | **逐字显示速度模式**；`nil` 时不改写当前速度 | 高 |
| 第 4 参数 | `a4` | 传给 `f_0004CD33()`，决定 `G[231]` 前后缀 | **引号/文本包围与连接模式**；`0/1` 有明确特殊含义，其他值通常不加引号 | 高 |
| 第 5 参数 | `a5` | 仅在 `f_0004CEFD()` 中与 `-1` 比较 | **特殊阅读/历史记录处理开关**；只有 `-1` 才调用 `f_0006A924()` | 中高 |

注意：第二、三参数的“尺寸”和“速度”是从其下游映射函数推断出的业务名称；原始代码实际以若干整数模式值换算后调用 `TextSize` / `TextSpeed`，并非直接把传入整数原样当作最终像素或毫秒。

---

## 4. 第 1 参数：正文文本内容

### 4.1 传递路径

[`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 将第 1–4 参数原样转发给 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1)。在 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1) 的文本拼接段：

```lua
G[231] = G[231] + text
G[238] = text
```

对应 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:154792)。

因此第 1 参数的作用是：

> 把一段正文字符串追加到当前正文缓冲，并把本次原始输入保存到 `G[238]`。

### 4.2 普通调用

最常见形态是：

```lua
f_0004CEFD("世界がそっと、ため息をつく――", nil, nil, nil, nil)
```

例如 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:314694)。大量正文调用都采用这一形式：第 1 参数是字符串，第 2–5 参数均为 `nil`。

### 4.3 第 1 参数为 `nil`

第 1 参数偶尔为 `nil`，例如连续的：

```lua
f_0004CEFD(nil, nil, nil, nil, nil)
```

这不应简单理解为“显示空字符串”。结合 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1) 的缓冲逻辑，它更像是：

- 不追加新的正文内容；
- 仍执行一次正文状态建立；
- 仍进入 [`f_0004DF22()`](Sakura_hcb_ir/Sakura/f_0004DF22.lua:1) 的显示后处理；
- 常用于空白行、文本段结束、等待点或 UI 状态推进。

实际是否完全无输出，还取决于调用前 `G[231]` 是否已有内容以及当前文本系统状态。

### 4.4 普通字符串与常量字符串

HCB 中的第 1 参数可以是普通运行时字符串，也可以是带代码地址身份的常量字符串。下游最终可能交给 Text 系统处理；根据 [`26_Text.md`](../syscalls/26_Text.md:70)，`TextPrint` 对 `ConstString` 还会参与“首次读到”标记。因此不能把它一律看成普通 Lua 字符串：对阅读历史和已读判断而言，常量地址身份可能有额外意义。

---

## 5. 第 2 参数：文本尺寸/字号模式

第 2 参数在 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1) 中被保存到 `G[236]`，随后传给 [`f_0004D5B7()`](Sakura_hcb_ir/Sakura/f_0004D5B7.lua:1)：

```lua
if size_mode ~= nil then
    G[236] = size_mode
    f_0004D5B7(size_mode)
else
    G[236] = 0
end
```

对应 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:154819-154832)。

### 5.1 [`f_0004D5B7()`](Sakura_hcb_ir/Sakura/f_0004D5B7.lua:1) 的模式映射

该函数最终调用：

```lua
TextSize(0, computed_size, nil)
```

映射关系如下：

| 第 2 参数值 | TextSize 第 2 参数 | 解释 |
|---:|---:|---|
| `nil` | 不调用 `f_0004D5B7()`；由 `G[236]=0` 表示默认 | 使用当前/默认字号状态 |
| `-3` | `base - 1` | 特殊缩小模式 |
| `-2` | `base / 2` | 半尺寸模式 |
| `-1` | `base * 4 / 5` | 约 80% 尺寸模式 |
| `1` | `base * 3 / 2` | 约 150% 尺寸模式 |
| `2` | `base * 5 / 3` | 约 166.7% 尺寸模式 |
| `3` | `base * 5 / 4` | 约 125% 尺寸模式 |
| `8..64` | 原值直接作为 TextSize | 直接字号/尺寸值路径 |
| `0` | 原值 `base` | 使用基础字号 |

其中 `base` 在函数入口被设为 `33`，见 [`f_0004D5B7.lua`](Sakura_hcb_ir/Sakura/f_0004D5B7.lua:5)。

### 5.2 实际调用样本

在 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:314817-314823) 附近，文本调用前出现：

```lua
f_0004CEFD("…………", nil, nil, nil, nil)
```

而在其他剧情段中，文本接口的第 2 参数会出现 `0`、`150` 等值。这些值不应直接解释为“等待 150 ms”；它们属于正文文本尺寸/排版模式链，具体最终效果还要结合当前布局和字号基准。

### 5.3 重要区分

第 2 参数不是：

- 文本显示持续时间；
- `f_00037708()` 的等待时长；
- 文本窗口坐标。

它通过 [`TextSize`](../syscalls/26_Text.md:328) 影响文字的字号/尺寸排版。

---

## 6. 第 3 参数：逐字显示速度模式

第 3 参数在 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 中被判断：

```lua
if speed_mode ~= nil then
    G[236] = speed_mode
    f_0004D6A7(speed_mode)
else
    G[236] = 0
end
```

实际源码位置为 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:154819-154840)。这里导出变量名存在复用，阅读时应以“传给 `f_0004D6A7` 的第三参数”理解。

### 6.1 [`f_0004D6A7()`](Sakura_hcb_ir/Sakura/f_0004D6A7.lua:1) 的换算

该函数最终执行：

```lua
TextSpeed(0, computed_speed)
```

默认基准在入口被设为 `20`，见 [`f_0004D6A7.lua`](Sakura_hcb_ir/Sakura/f_0004D6A7.lua:5)。模式映射为：

| 第 3 参数值 | TextSpeed 值 | 可能含义 |
|---:|---:|---|
| `nil` | 不调用速度设置函数 | 保留当前速度 |
| `0` | `0` | 关闭或极快显示，具体取决于 VM 对 `TextSpeed(0,0)` 的定义 |
| `-1` | `-1` | 特殊瞬时/跳过速度模式 |
| 其他值 | `20 * mode` | 以基准速度进行倍率换算 |
| `>=101` | `10` | 上限/特殊高速值被归一化为 `10` |

具体 TextSpeed 的运行时语义见 [`26_Text.md`](../syscalls/26_Text.md:426)：它控制逐字输出速度和文字等待参数，并可能影响 `TextPrint` 是否进入 text wait。

### 6.2 第 3 参数与 `f_00037708(500,nil)` 的区别

两者都可能影响玩家感受到的文字节奏，但职责不同：

- 第 3 参数通过 `TextSpeed` 影响**一条文本内部逐字出现的速度**；
- [`f_00037708(500,nil)`](Sakura_hcb_ir/Sakura/f_00037708.lua:1) 影响**两次正文调用之间的推进间隔**；
- [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 本身只是把速度模式传入下游。

因此，如果游戏表现为文字逐字出现，应优先检查第 3 参数及 `TextSpeed`；如果是整句输出后停顿约 500 ms，应检查 [`f_00037708()`](Sakura_hcb_ir/Sakura/f_00037708.lua:1)。

---

## 7. 第 4 参数：引号、前缀和文本连接模式

第 4 参数在 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1) 中被归一化：

```lua
if quote_mode == nil then
    quote_mode = 0
end
```

随后它控制全局正文缓冲 `G[231]` 的前后缀。

### 7.1 新文本段的前缀

当 `G[231]` 原本为空时：

| 第 4 参数 | 写入的前缀 |
|---:|---|
| `0` | `「` |
| `1` | 空字符串 |
| 其他值 | 不满足上述两个分支，保留空/旧状态差异 |

当 `G[231]` 原本非空时：

| 第 4 参数 | 写入的前缀 |
|---:|---|
| `0` | `~「` |
| `1` | 空字符串 |
| 其他值 | 通常不追加特殊前缀 |

代码证据见 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:154754-154791)。

### 7.2 文本段结束时的后缀

当 `G[227] >= 1` 时，若第 4 参数为 `0`，在文本后追加：

```text
」
```

代码见 [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:154799-154818)。

因此最常见的默认值 `nil -> 0`，其效果接近：

```text
「文本内容」
```

而第 4 参数为 `1` 时，抑制前后日文引号，适合旁白、特殊演出文本或已经由脚本自行提供标点/包围符号的文本。

### 7.3 可解释的模式表

| 第 4 参数 | 作用概括 |
|---:|---|
| `nil` | 归一化为 `0`，默认使用日文引号包装。 |
| `0` | 普通对话/引号模式：追加 `「`、`」`，已有段落时可能追加 `~「`。 |
| `1` | 无引号模式：不追加引号。 |
| 其他值 | 目前没有同等明确的前后缀行为，可能用于连接/特殊文本段。 |

第 4 参数不是字号、速度或等待时长，而是**文本缓冲字符串的格式化标志**。

---

## 8. 第 5 参数：`-1` 特殊处理开关

第 5 参数不传给 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1)，只在 [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 本体被检查：

```lua
if read_mode == -1 then
    f_0006A924()
end
```

### 8.1 [`f_0006A924()`](Sakura_hcb_ir/Sakura/f_0006A924.lua:1) 的实际行为

该函数只是包装：

```lua
function f_0006A924()
    f_00091C82()
end
```

而 [`f_00091C82()`](Sakura_hcb_ir/Sakura/f_00091C82.lua:1) 执行：

```lua
SaveCreate(3, G[3531])
if SaveCreate(...) ~= true then
    G[3531] = G[3531] + 1
    if G[3531] >= 369 then
        G[3531] = 361
    end
end
```

也就是说，第 5 参数为 `-1` 时，会触发一轮以 `G[3531]` 为索引、槽位类型为 `3` 的 `SaveCreate`，并维护 `G[3531]` 的循环范围 `361..368`。

这更接近：

- 阅读/文本进度记录；
- 历史或临时存档槽创建；
- 某种正文演出状态的轮转保存。

目前没有足够证据把它命名为普通的“已读标记写入”，但可以确定它不是文本内容写入，也不是字号/速度设置。

### 8.2 第 5 参数的典型值

常见正文调用使用：

```lua
f_0004CEFD(text, nil, nil, nil, nil)
```

特殊调用会出现：

```lua
f_0004CEFD(text, ..., ..., ..., -1)
```

例如 [`f_004B1A32.lua`](Sakura_hcb_ir/Sakura/f_004B1A32.lua:120-140) 附近的调用链中，第五参数明确压入 `-1`。这类调用应理解为：

> 在显示该文本之前/期间，额外更新一组阅读相关的保存槽状态。

其他数值如 `0`、`100`、`1200` 若出现在相邻的其他函数参数中，不能据此认为它们是 `f_0004CEFD()` 第五参数；必须观察紧邻调用前实际压入的五个值。

---

## 9. 下游 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1) 的完整职责

虽然用户关注的是 [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1)，但正文实际状态变化主要发生在 [`f_0004CD33()`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1)。它的流程可以分为以下几层。

### 9.1 参数默认化

```lua
if quote_mode == nil then
    quote_mode = 0
end
```

第 4 参数缺省时采用普通引号模式。

### 9.2 特殊布局覆盖

```lua
if G[1193] == 1 then
    speed_or_size_mode = 1
end
```

已有 [`f_000493AC()`](Sakura_hcb_ir/Sakura/f_000493AC.lua:1) 分析表明，`G[1193]` 是特殊/演出式文本布局状态之一。因此在居中独白或演出文本模式下，某些调用方传入的模式会被函数强制覆盖，避免普通对话样式继续生效。

### 9.3 输出前的全局/UI准备

函数还会调用：

- [`f_000520A1()`](Sakura_hcb_ir/Sakura/f_000520A1.lua:1)：在 `G[247] == true` 时执行；
- [`f_00060795()`](Sakura_hcb_ir/Sakura/f_00060795.lua:1)：传入三个 `nil`；
- [`f_000545F7()`](Sakura_hcb_ir/Sakura/f_000545F7.lua:1)；
- [`f_000528FF(-1)`](Sakura_hcb_ir/Sakura/f_000528FF.lua:1)：在 `G[297] == 0` 时执行；
- [`f_00096432()`](Sakura_hcb_ir/Sakura/f_00096432.lua:1)；
- [`f_0004A1AA(nil,nil,nil)`](Sakura_hcb_ir/Sakura/f_0004A1AA.lua:1)；
- [`f_00049EC9()`](Sakura_hcb_ir/Sakura/f_00049EC9.lua:1)；
- [`f_00066CB2()`](Sakura_hcb_ir/Sakura/f_00066CB2.lua:1)。

这些调用构成正文显示前的 UI、输入、控制脉冲、窗口和演出状态准备。因此一次正文调用并不只是“写字符串”。

### 9.4 正文缓冲拼接

核心状态是：

| 全局槽 | 作用 |
|---|---|
| `G[231]` | 当前正文输出缓冲，负责拼接前缀、文本、后缀。 |
| `G[238]` | 最近一次原始文本参数。 |
| `G[236]` | 当前尺寸/速度模式状态；无相关参数时写入 `0`。 |
| `G[227]` | 当前正文段/行状态，决定是否补闭引号。 |
| `G[1193]` | 特殊演出式文本布局状态，会覆盖部分模式。 |

核心拼接可归纳为：

```lua
if G[231] == nil then
    if quote_mode == 0 then
        G[231] = "「"
    elseif quote_mode == 1 then
        G[231] = ""
    end
else
    if quote_mode == 0 then
        G[231] = "~「"
    elseif quote_mode == 1 then
        G[231] = ""
    end
end

G[231] = G[231] + text
G[238] = text

if G[227] >= 1 and quote_mode == 0 then
    G[231] = G[231] + "」"
end
```

### 9.5 尺寸与速度设置

- 第 2 参数非 `nil`：写入 `G[236]`，调用 [`f_0004D5B7()`](Sakura_hcb_ir/Sakura/f_0004D5B7.lua:1)；
- 第 3 参数非 `nil`：写入相应模式槽，调用 [`f_0004D6A7()`](Sakura_hcb_ir/Sakura/f_0004D6A7.lua:1)；
- 对应参数为 `nil`：把相关状态恢复为 `0` 或保留默认路径。

因此，参数非 `nil` 的少数调用不是异常，而是剧情脚本对字号、逐字速度和文本格式进行局部覆盖。

---

## 10. [`f_0004DF22()`](Sakura_hcb_ir/Sakura/f_0004DF22.lua:1) 的位置

[`f_0004DF22()`](Sakura_hcb_ir/Sakura/f_0004DF22.lua:1) 本身只是：

```lua
function f_0004DF22()
    f_0004D7A6()
end
```

真正复杂的是 [`f_0004D7A6()`](Sakura_hcb_ir/Sakura/f_0004D7A6.lua:1)。该函数包含大量：

- `InputGetState`、`InputGetDown`、`InputGetUp`、`InputGetWheel`；
- `TimerSet`、`TimerGet`；
- `PrimHit`、光标和按钮命中处理；
- `ControlPulse`；
- `ThreadNext`；
- 音频状态和 UI 控制；
- `G[1964]`、`G[240]`、`G[1963]` 等跳过/输入/历史状态判断。

因此一次 [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 调用的“显示完成”并不是函数返回瞬间简单结束，而是会进入一套正文阅读控制流程。根据 [`26_Text.md`](../syscalls/26_Text.md:79)，真正的 `TextPrint` 可能触发 Text wait；而 Sakura 这层封装又在外部用 `f_0004D7A6()` 处理输入、跳过和 UI 状态。

所以需要区分：

1. `f_0004CD33()`：构造正文文本缓冲和文本参数；
2. `f_0004CEFD()`：公共包装、特殊阅读记录开关、进入正文推进；
3. `f_0004DF22()` / `f_0004D7A6()`：正文显示后的等待、跳过、输入与 UI 收束。

---

## 11. `f_0004CEFD()` 的推荐命名和等价实现

### 11.1 推荐语义名

```text
正文文本输出/阅读推进包装器
```

或者在脚本重建时使用：

```lua
TextScenarioPrint(text, size_mode, speed_mode, quote_mode, read_mode)
```

### 11.2 等价伪代码

```lua
function f_0004CEFD(text, size_mode, speed_mode, quote_mode, read_mode)
    -- 1. 构造正文缓冲、前后缀和局部文本样式
    f_0004CD33(text, size_mode, speed_mode, quote_mode)

    -- 2. 特殊阅读/历史状态处理
    if read_mode == -1 then
        f_0006A924()
    end

    -- 3. 进入正文显示后的等待、输入和 UI 推进
    f_0004DF22()
end
```

---

## 12. 对“第一个参数即可完成文本写入”的修正

这个观察基本正确，但需要分成两层理解：

### 12.1 调用者层面

对大多数剧情脚本而言：

```lua
f_0004CEFD(text, nil, nil, nil, nil)
```

第 1 参数已经足以指定要输出的正文内容，其他参数使用默认路径。

### 12.2 引擎封装层面

第 1 参数并不是直接调用 `TextPrint` 的唯一信息。一次完整正文输出还依赖：

- `G[231]` 当前缓冲内容；
- `G[227]` 当前段落/行状态；
- 第 2 参数决定的字号模式；
- 第 3 参数决定的逐字速度；
- 第 4 参数决定的引号和连接格式；
- 第 5 参数决定是否执行特殊阅读记录；
- `G[1193]`、`G[247]`、`G[297]` 等全局 UI/演出状态；
- `f_0004D7A6()` 中的输入和跳过状态。

因此第 1 参数是“文本内容的主要业务入参”，但不是“整个正文显示过程的全部状态”。

---

## 13. 最终结论

1. [`f_0004CEFD()`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1) 是 Sakura 正文系统的高频公共包装器，而非底层 Text syscall 本身。
2. 第 1 参数是正文文本，通常为字符串；为 `nil` 时可表示空白/推进/状态刷新调用。
3. 第 2 参数控制字号/文本尺寸模式，最终经 [`f_0004D5B7()`](Sakura_hcb_ir/Sakura/f_0004D5B7.lua:1) 转换后调用 `TextSize`。
4. 第 3 参数控制逐字输出速度模式，最终经 [`f_0004D6A7()`](Sakura_hcb_ir/Sakura/f_0004D6A7.lua:1) 转换后调用 `TextSpeed`。
5. 第 4 参数控制正文缓冲的引号、前缀、后缀和连接方式；默认 `nil` 等价于普通引号模式 `0`。
6. 第 5 参数只在等于 `-1` 时触发 [`f_0006A924()`](Sakura_hcb_ir/Sakura/f_0006A924.lua:1)，该调用进一步维护 `SaveCreate(3, G[3531])` 的阅读/历史相关槽位。
7. 函数最后通过 [`f_0004DF22()`](Sakura_hcb_ir/Sakura/f_0004DF22.lua:1) 进入正文显示后的输入等待、跳过、计时和 UI 推进。
8. 如果要研究“文字逐字出现速度”，应继续追踪第 3 参数和 `TextSpeed`；如果要研究“整句之间的停顿”，应追踪 [`f_00037708()`](Sakura_hcb_ir/Sakura/f_00037708.lua:1)；如果要研究“居中/演出式布局”，则应追踪 [`f_000493AC()`](Sakura_hcb_ir/Sakura/f_000493AC.lua:1)。

---

## 14. 证据索引

- [`f_0004CEFD.lua`](Sakura_hcb_ir/Sakura/f_0004CEFD.lua:1)
- [`Sakura.lua`](../../04_outputs/lua_ir/Sakura.lua:154847)
- [`Sakura.ir.json`](Sakura_hcb_ir/Sakura.ir.json:1231415)
- [`Sakura.cfg.json`](../../03_data/cfg/Sakura.cfg.json:298821)
- [`f_0004CD33.lua`](Sakura_hcb_ir/Sakura/f_0004CD33.lua:1)
- [`f_0004D5B7.lua`](Sakura_hcb_ir/Sakura/f_0004D5B7.lua:1)
- [`f_0004D6A7.lua`](Sakura_hcb_ir/Sakura/f_0004D6A7.lua:1)
- [`f_0006A924.lua`](Sakura_hcb_ir/Sakura/f_0006A924.lua:1)
- [`f_00091C82.lua`](Sakura_hcb_ir/Sakura/f_00091C82.lua:1)
- [`f_0004DF22.lua`](Sakura_hcb_ir/Sakura/f_0004DF22.lua:1)
- [`f_0004D7A6.lua`](Sakura_hcb_ir/Sakura/f_0004D7A6.lua:1)
- [`26_Text.md`](../syscalls/26_Text.md:1)
- [`Sakura.function_calls.csv`](Sakura_hcb_ir/Sakura.function_calls.csv:4811)
