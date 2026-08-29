# Text 分组 syscall 含义详解

## 1. 分组范围与结论概览

依据 [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:107)、[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6032-7285) 与 rfvp 参考实现，`Text` 分组当前包含 27 个 syscall：

1. `TextBuff`
2. `TextClear`
3. `TextColor`
4. `TextDataGet`
5. `TextDataSet`
6. `TextFont`
7. `TextFontCount`
8. `TextFontGet`
9. `TextFontName`
10. `TextFontSet`
11. `TextFormat`
12. `TextFunction`
13. `TextHistory`
14. `TextHyphenation`
15. `TextOutSize`
16. `TextPause`
17. `TextPos`
18. `TextPrint`
19. `TextRepaint`
20. `TextReprint`
21. `TextShadowDist`
22. `TextSize`
23. `TextSkip`
24. `TextSpace`
25. `TextSpeed`
26. `TextSuspendChr`
27. `TextTest`

其中现代显式实现主要位于 [`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:1)，`TextDataGet`、`TextDataSet`、`TextHistory`、`TextHyphenation` 通过 [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:485-570) 提供兼容实现；`TextRepaint` 在 [`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:1235-1243) 中作为重绘别名实现。

`Text` 分组可以概括为：

> **围绕文本槽位、文本内容、字体、颜色、字号、描边、间距、ruby/特殊标记解析、显示位置、打字速度、跳过/暂停和历史记录的一组文本系统接口。**

---

## 2. Text 运行模型

### 2.1 文本槽位范围

现代 Text syscall 通常使用 `0..31` 的文本槽位：

- `text_id = 0..31`；
- 每个槽位拥有独立的内容、字体、颜色、字号、布局和输出状态；
- 文本槽位渲染后映射到 graph/texture 槽 `4064 + text_id`：[`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:594-599)。

因此文本系统通常分为三层：

1. [`TextManager`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/resources/text_manager.rs:1)：保存文本状态与排版参数；
2. [`TextPrint`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:544)：修改内容并触发文字纹理更新；
3. [`PrimSetText`](fvp_analysis/result/syscall语义数据库/syscall含义详解/21_Prim.md:779)：把文本槽位绑定到显示 prim。

### 2.2 Text 与 Prim 的边界

`TextPrint` 不直接决定文本 prim 的屏幕位置；它负责写入某个文本槽位并刷新对应纹理。显示对象的创建和树组织由 Prim 组负责：

```text
TextBuff(text_id, w, h)
TextPrint(text_id, content)
PrimSetText(prim_id, text_id, x, y)
PrimGroupIn(prim_id, parent_id)
```

### 2.3 文本内容的两种 VM 字符串

`TextPrint` 接受：

- `String`：普通运行时字符串；
- `ConstString`：带有 HCB 代码区地址身份的常量字符串。

两者都会写入文本槽并上传纹理，但 `ConstString` 还会根据其地址调用 `mark_readed_text_first()`，用于 `TextTest` 和“该文本常量是否第一次被读到”的判定：[`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:587-623)。

### 2.4 TextPrint 的调度副作用

`TextPrint` 可能根据文本速度、控制键、控制脉冲和全局设置进入文本等待：

- 设置当前 thread 的 text wait；
- 调用 `should_break()`；
- 当前 syscall 返回 `Nil`，后续由 VM/文本系统继续推进。

这也是 Text 组中最明确的调度型接口。数据库将它标为 `yield=true`、`text_wait=true`：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6900-6917)。

---

## 3. 文本缓冲与内容输出

## 3.1 `TextBuff`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6035)
- **签名**：`TextBuff(id, width, height)`
- **返回值**：`Nil`

### 入参语义

- `id`
  - 类型：`Int`；
  - 有效范围：`0..31`；
  - 含义：文本槽位。
- `width`
  - 类型：`Int | Nil`；
  - 默认值：`8`；
  - 非负整数时覆盖默认宽度。
- `height`
  - 类型：`Int | Nil`；
  - 默认值：`8`；
  - 非负整数时覆盖默认高度。

### 具体作用

[`text_buff()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:10-55) 为文本槽位设置缓冲尺寸并立即上传清空后的文本纹理：

1. 校验槽位；
2. 使用默认 `8×8` 或参数中的非负尺寸；
3. 调用 `text_manager.set_text_buff()`；
4. 调用 `text_upload_slot(..., false)`。

它不负责打印字符串；通常是文本槽位生命周期的初始化接口。

> `TextBuff` 是 **创建/调整文本缓冲区并刷新对应空白纹理的接口**。

## 3.2 `TextClear`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6087)
- **签名**：`TextClear(id)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`，文本槽位。

[`text_clear()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:58-77) 清除文本管理器中的内容，并立即重新上传清空后的文本纹理。

> `TextClear` 是 **清空指定文本槽位内容并刷新显示纹理的接口**。

## 3.3 `TextPrint`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6885)
- **签名**：`TextPrint(id, content)`
- **返回值**：数据库记录为 `Nil`；普通字符串返回 `Nil`，`ConstString` 还可能返回“首次读取”意义的 `True/Nil`。

### 入参语义

- `id`
  - 类型：`Int`；
  - 有效范围：`0..31`；
  - 含义：目标文本槽位。
- `content`
  - 类型：`String | ConstString`；
  - 内容长度：当前实现要求字节长度 `<512`；
  - 含义：要写入并显示的文本。

### 具体作用

[`text_print()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:544-628) 会：

1. 写入文本槽位内容；
2. 调用 legacy 文本历史收集入口；
3. 按字体、颜色、排版参数重新生成文本纹理；
4. 根据 `TextSpeed`、Ctrl 键、控制脉冲和全局变量决定是否进入 text wait；
5. `ConstString` 路径额外记录常量字符串地址是否第一次读取。

### 返回值与控制流

- 普通 `String`：返回 `Nil`；
- `ConstString`：第一次看到该地址返回 `True`，此前已经读过则返回 `Nil`；
- 如果文本显示需要等待，则进入 `thread_text_wait` 并 `should_break()`。

> `TextPrint` 是 **写入文本、刷新文本纹理并可能触发文字显示等待的核心接口**。

## 3.4 `TextReprint`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6966)
- **签名**：`TextReprint()`
- **返回值**：`Nil`

调用 [`MotionManager::text_reprint()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:631-634)，不修改文本内容，只依据当前字体、颜色和布局状态重新生成文本纹理。

> `TextReprint` 是 **对已有文本槽位执行重新排版/重绘的接口**。

## 3.5 `TextRepaint`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6931)
- **签名**：`TextRepaint()`
- **返回值**：`Nil`

当前实现结构体名为 `TextRepaint`，内部同样调用 `text_reprint()`：[`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:1235-1243)。

因此在当前 rfvp 中：

- `TextRepaint` 与 `TextReprint` 的运行效果基本相同；
- 两者都不重新设置文本内容；
- 两者都用于把已有状态重新上传为文本纹理。

> `TextRepaint` 是 **重绘语义的兼容别名**。

---

## 4. 字体与颜色

## 4.1 `TextColor`

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6127)
- **签名**：`TextColor(id, color1, color2, color3)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `color1/2/3`：`Int | Nil`；
- 颜色槽位有效范围：`0..255`；
- `Nil` 或非整数表示不修改该颜色槽位。

`TextColor` 从共享 `ColorManager` 读取颜色条目，并写入文本槽位的三类颜色配置：[`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:141-184)。

当前 handler 还兼容旧版 3 参数调用：如果实际参数数为 3，则调用 `text_color_legacy_aw()`，只设置前两个颜色槽，且 legacy 文本 id 限制为 `0..7`。

> `TextColor` 是 **把颜色表槽位绑定到文本槽位的接口**，不是直接写 RGBA 像素。

## 4.2 `TextFont`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6291)
- **签名**：`TextFont(id, font1, font2)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `font1/font2`：`Int | Nil`；
- 当前实现接受 `-5..=font_count` 的字体 ID；
- `Nil` 或其他类型表示保持原值。

字体 ID 约定：

- `-1`：当前字体或特殊“当前字体”语义；
- `-2..-5`：内置日文字体槽；
- 非负值：字体管理器中的用户/枚举字体。

当前 handler 兼容旧版 2 参数调用：legacy 路径只设置主字体槽，legacy 文本 id 限制为 `0..7`。

> `TextFont` 是 **设置文本主字体与第二字体/替补字体槽位的接口**。

## 4.3 `TextFontCount`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6343)
- **签名**：`TextFontCount()`
- **返回值**：`Int`

返回 [`FontfaceManager::get_font_count()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:239-241) 的字体数量。

> `TextFontCount` 是 **查询字体枚举数量的接口**。

## 4.4 `TextFontGet`

- **参数个数**：0：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6376)
- **签名**：`TextFontGet()`
- **返回值**：`Int`

返回 [`FontfaceManager::get_system_fontface_id()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:243-247) 当前系统字体 ID。

> `TextFontGet` 是 **查询当前系统字体 ID 的接口**。

## 4.5 `TextFontName`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6409)
- **签名**：`TextFontName(id)`
- **返回值**：`String | Nil`

- `id`：`Int`，字体 ID；
- 字体存在：返回字体名称字符串；
- 字体不存在或参数类型无效：返回 `Nil`。

实现见 [`text_font_name()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:249-261)。

> `TextFontName` 是 **把字体 ID 转换为字体名称的查询接口**。

## 4.6 `TextFontSet`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6449)
- **签名**：`TextFontSet(id)`
- **返回值**：`Nil`

- `id`：`Int`；
- 有效范围：`-5..=font_count`；
- 若能解析字体名称，则更新系统当前字体 ID 和当前字体名称。

实现见 [`text_font_set()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:264-279)。

> `TextFontSet` 是 **设置宿主文本系统当前字体的接口**，区别于 `TextFont` 对单个文本槽位的字体绑定。

---

## 5. 排版格式与文本效果

## 5.1 `TextFormat`

- **参数个数**：7：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6489)
- **签名**：`TextFormat(id, space_vertical, space_horizontal, start_vertical, start_horizontal, ruby_horizontal, ruby_vertical)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `space_vertical`：`Int`，范围 `-32..32`；
- `space_horizontal`：`Int`，范围 `-32..32`；
- `start_vertical`：`Int`，范围 `0..64`；
- `start_horizontal`：`Int`，范围 `0..64`；
- `ruby_horizontal`：`Int`，范围 `-16..16`；
- `ruby_vertical`：`Int`，范围 `-16..16`；
- 非法或非整数的可选格式参数不修改对应字段。

该接口集中设置文本间距、文本起始偏移和 ruby 标注偏移：[`text_format()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:282-341)。

> `TextFormat` 是 **文本槽位的综合排版参数设置接口**。

## 5.2 `TextFunction`

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6565)
- **签名**：`TextFunction(id, special_unit_mode, ruby_mode, wait_mode)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `special_unit_mode`：`Int`，`0..1`；控制 `<...>` 特殊单元解析模式；
- `ruby_mode`：`Int`，`0..2`；控制 `[...]` ruby 解析模式；
- `wait_mode`：`Int`，`0..2`；控制 `{n}` 等等待标记模式。

当前源码注释给出了这些映射：[`text_function()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:344-395)。

> `TextFunction` 是 **控制文本特殊语法、ruby 解析和等待标记解释方式的接口**。

## 5.3 `TextOutSize`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6732)
- **签名**：`TextOutSize(id, outline, ruby_outline)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `outline`：`Int | Nil`，范围 `0..12`；
- `ruby_outline`：`Int | Nil`，范围 `0..8`；
- 非整数/`Nil` 可保持对应默认值或不修改。

`TextOutSize` 设置正文描边级别和 ruby 描边级别：[`text_out_size()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:427-467)。

handler 兼容旧版 2 参数调用，legacy 路径只设置主描边槽且文本 id 限制为 `0..7`。

> `TextOutSize` 是 **设置正文与 ruby 文字描边级别的接口**。

## 5.4 `TextShadowDist`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7000)
- **签名**：`TextShadowDist(id, distance)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `distance`：`Int | Nil`；
- 当前实现将距离限制到 `0..12`；
- 非整数按默认 `0` 处理。

[`text_shadow_dist()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:636-670) 设置文本阴影偏移距离。

> `TextShadowDist` 是 **设置文本阴影距离的接口**。

## 5.5 `TextSize`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7046)
- **签名**：`TextSize(id, size, ruby_size)`
- **返回值**：数据库记录为 `Mixed`，当前实现的设置分支返回 `Nil`。

- `id`：`Int`，范围 `0..31`；
- `size`：`Int | Nil`，范围 `12..64`；
- `ruby_size`：`Int | Nil`，范围 `8..32`。

设置正文与 ruby 字体大小：[`text_size()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:702-743)。handler 兼容旧版 2 参数调用，legacy 主字号范围为 `8..64`、文本 id 为 `0..7`。

> `TextSize` 是 **设置文本正文和 ruby 字号的接口**。

## 5.6 `TextSpace`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7143)
- **签名**：`TextSpace(id, vertical, horizontal)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `vertical`：`Int`，范围 `-32..32`；
- `horizontal`：`Int`，范围 `-32..32`；
- 非法或非整数参数不修改对应字段。

[`text_space()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:774-815) 设置文本行距/垂直间距和字符/水平间距。

> `TextSpace` 是 **单独调整文本水平、垂直间距的简化排版接口**；`TextFormat` 是其更完整的综合版本。

## 5.7 `TextSuspendChr`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7242)
- **签名**：`TextSuspendChr(id, chars)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `chars`：`String | ConstString`；
- 含义：禁则/换行限制字符集合。

[`text_suspend_chr()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:848-875) 将字符集合写入文本管理器。

`TextHyphenation` 当前也复用此函数，见后文。

> `TextSuspendChr` 是 **设置文本换行禁则字符集合的接口**。

---

## 6. 文本位置、速度、跳过与暂停

## 6.1 `TextPos`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6831)
- **签名**：`TextPos(id, x, y)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `x/y`：可选整数；
- `Nil` 或非整数表示保持原值。

[`text_pos()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:506-541) 设置文本槽位内部的文本起始位置。它与 `PrimSetText(prim_id, text_id, x, y)` 不同：

- `TextPos` 调整文本内容在文本缓冲内部的位置；
- `PrimSetText` 调整文本 prim 在场景树中的位置。

> `TextPos` 是 **文本槽位内部布局位置设置接口**。

## 6.2 `TextSpeed`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall含义详解/7194)
- **签名**：`TextSpeed(id, speed)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `speed`：`Int`，范围 `-1..300000`；
- `0`：源码注释明确表示立即显示；
- 其他值：由文本系统作为文字显示推进速度/等待参数使用；
- `-1`：保留的特殊速度值，具体业务含义需结合 TextManager 和原版样本验证。

实现见 [`text_speed()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:818-845)。

> `TextSpeed` 是 **设置文本逐字显示速度/等待参数的接口**。

## 6.3 `TextSkip`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7098)
- **签名**：`TextSkip(id, skip)`
- **返回值**：`Nil`

- `id`：`Int`，范围 `0..31`；
- `skip`：`Int`，范围 `0..3`；
- 含义：文本槽位的 skip 模式。

当前 syscall 层只确认它把 `0..3` 写入 `TextManager::set_text_skip()`：[`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:746-770)。具体 0、1、2、3 分别对应自动跳过、用户跳过、快速显示还是其他模式，当前 reference 没有给出足够稳定的枚举说明。

> `TextSkip` 是 **设置文本跳过模式的接口**，具体数值映射仍需实机/脚本验证。

## 6.4 `TextPause`

- **参数个数**：2：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6787)
- **签名**：`TextPause(id, pause)`
- **返回值**：`Int | Nil`

- `id`：`Int`，范围 `0..31`；
- `pause`：
  - `Int(0)`：取消暂停；
  - `Int(1)`：设置暂停；
  - `Nil`：查询当前暂停状态；
  - 其他类型/数值：不产生作用。

查询时返回：

- `Int(1)`：已暂停；
- `Int(0)`：未暂停。

设置分支返回 `Nil`。实现见 [`text_pause()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:471-503)。

> `TextPause` 是 **文本槽位暂停/恢复以及暂停状态查询接口**。

---

## 7. 字体输出后的文本纹理刷新

### `TextRepaint` 与 `TextReprint` 的关系

这两个 syscall 都不接受参数、返回 `Nil`，当前实现都调用文本重新上传逻辑：

- `TextRepaint`：偏向“重绘”命名；
- `TextReprint`：偏向“重新打印/重生成”命名；
- 当前 rfvp 行为基本一致。

当字体、颜色、字号、描边或排版状态发生修改后，调用它们可以把已有内容重新渲染到 graph `4064 + id`。

---

## 8. Legacy 文本数据与历史接口

## 8.1 `TextDataSet`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6238)
- **签名**：`TextDataSet(text_id, key, value)`
- **返回值**：`Nil`

当前 legacy 实现：

- `text_id`：`Int`，范围 `0..7`；
- `key`：`Int`；
- `key=0`：写入 pending history slot 0；
- `key=1`：写入 pending history slot 1；
- 其他 key：忽略；
- `value`：任意 `Variant`，原样保存。

实现见 [`text_data_set()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:485-503)。

它不是直接修改现代文本槽的排版状态，而是为 legacy 文本历史记录准备两个待写字段。

> `TextDataSet` 是 **旧版文本历史条目的临时字段设置接口**。

## 8.2 `TextDataGet`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6185)
- **签名**：`TextDataGet(text_id, index, key)`
- **返回值**：`Mixed`，实际可以返回任意保存的 `Variant` 或 `Nil`。

- `text_id`：`Int`，范围 `0..7`；
- `index`：`Int`，必须非负；
- `key`：`Int`，当前 `0/1` 有效；
- `key=0`：读取历史条目的 slot0；
- `key=1`：读取历史条目的 slot1；
- 历史不存在或 key 无效：返回 `Nil`。

实现见 [`text_data_get()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:506-534)。

> `TextDataGet` 是 **读取 legacy 文本历史条目字段的接口**。

## 8.3 `TextHistory`

- **参数个数**：4：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6623)
- **签名**：`TextHistory(text_id, mode, prim_a, prim_b)`
- **返回值**：`Int | Nil`

- `text_id`：`Int`，范围 `0..7`；
- `mode`：控制历史功能；
- `prim_a / prim_b`：启用历史显示时使用的两个 prim ID 候选，当前实现只保存整数值。

当前实现分支：

- `mode=-1`：返回当前历史条目数量 `Int`；
- `mode=0`：关闭历史收集，返回 `Nil`；
- `mode>0`：读取对应历史条目的 slot0，未找到则 `Nil`；
- 其他 truthy 非 `Nil`：开启历史收集，并记录 `prim_a/prim_b`。

文本打印时，legacy hook [`on_legacy_text_print()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:171-193) 会把正文和 pending slot 写入历史，最多保留 100 条。

> `TextHistory` 是 **legacy 文本 backlog/历史记录功能的开启、关闭、计数与读取接口**。

当前 rfvp 只恢复了历史数据状态，具体如何把历史内容显示到 `prim_a/prim_b`，仍需更多 UI 调用链验证。

## 8.4 `TextHyphenation`

- **参数个数**：3：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6682)
- **签名**：`TextHyphenation(text_id, limit, chars)`
- **返回值**：`Nil`

当前 legacy 实现直接转调 `text_suspend_chr()`：[`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:569-571)。因此：

- `text_id`：按现代实现要求为 `0..31`；
- `limit`：当前兼容实现忽略；
- `chars`：`String | ConstString`，作为禁则字符集合保存。

名称中的 hyphenation 暗示原版可能有断词/断行限制功能，但当前 rfvp 只实现为禁则字符设置。

> `TextHyphenation` 是 **旧版断行/连字符接口的兼容映射，当前实际效果等价于设置禁则字符集合**。

---

## 9. `TextTest`

- **参数个数**：1：[`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:7288)
- **签名**：`TextTest(const_string)`
- **返回值**：`BoolLike`

### 入参语义

- `const_string`
  - 类型：`ConstString`；
  - 含义：需要测试的 HCB 常量字符串及其代码区地址身份。

普通 `String` 不包含稳定的 HCB 地址身份，当前实现对其返回 `Nil`。

### 具体作用

[`text_test()`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:878-891) 使用常量字符串地址作为 bitmap/集合键：

- 第一次标记该地址：返回 `True`；
- 此后再次测试：返回 `Nil`。

这与 `TextPrint(ConstString)` 的“首次读到”分支共享同一类 read bitmap 状态。

> `TextTest` 是 **测试某个 HCB 常量字符串是否首次被读取/处理的接口**。

---

## 10. Text 组整体工作流

### 10.1 初始化文本槽位

```text
TextBuff(text_id, width, height)
TextColor(text_id, color1, color2, color3)
TextFont(text_id, font1, font2)
TextSize(text_id, size, ruby_size)
TextOutSize(text_id, outline, ruby_outline)
TextFormat(text_id, ...)
TextFunction(text_id, ...)
TextSpace(text_id, vertical, horizontal)
TextPos(text_id, x, y)
```

### 10.2 输出文本

```text
TextPrint(text_id, content)
PrimSetText(prim_id, text_id, x, y)
PrimGroupIn(prim_id, parent_id)
```

### 10.3 修改后重绘

```text
TextColor(...)
TextFont(...)
TextSize(...)
TextFormat(...)
TextRepaint() / TextReprint()
```

### 10.4 控制显示过程

```text
TextSpeed(text_id, speed)
TextSkip(text_id, mode)
TextPause(text_id, 1)
TextPause(text_id, nil)     // 查询
TextSuspendChr(text_id, chars)
```

### 10.5 典型文本同步点

当 `TextPrint` 根据文本速度和输入状态进入等待时，脚本通常由文本 wait 状态暂停；之后由输入/控制相关 syscall 或文本系统状态推进。`TextPrint` 本身不返回“等待完成”，而是通过 VM context 状态改变完成同步。

---

## 11. 高置信度结论

以下结论比较稳：

- `Text` 分组当前共有 27 个 syscall。
- 现代文本槽位范围主要为 `0..31`，对应文本纹理 graph `4064 + id`。
- `TextBuff` 初始化/调整缓冲区，`TextClear` 清空槽位，`TextPrint` 写入内容并上传纹理。
- `TextPrint` 接受 `String` 和 `ConstString`；`ConstString` 额外参与首次读取检测。
- `TextPrint` 可能进入 `text_wait` 并让当前 context break。
- `TextRepaint` 和 `TextReprint` 当前实现基本等价，都是重新上传已有文本内容。
- `TextColor` 使用共享颜色表槽位，而不是直接传 RGBA。
- `TextFont` 设置单个文本槽位字体，`TextFontSet` 设置系统当前字体；`TextFontCount/Get/Name` 用于字体查询。
- `TextSize` 同时支持正文和 ruby 字号；`TextOutSize` 同时支持正文和 ruby 描边。
- `TextFormat` 和 `TextSpace` 控制行距、字距、起始偏移与 ruby 偏移。
- `TextFunction` 控制特殊单元、ruby 和等待标记的解析模式。
- `TextPause(nil)` 查询暂停状态，返回 `Int(0/1)`；设置分支返回 `Nil`。
- `TextHistory`、`TextDataGet/Set`、`TextHyphenation` 属于 legacy 文本兼容链。
- `TextTest` 以 `ConstString` 地址为键，返回一次性 `True/Nil`。

---

## 12. 仍需保守处理的点

1. `TextPrint` 的具体等待条件由 `TextManager::should_block_on_print()`、全局变量、Ctrl 输入和控制脉冲共同决定；不同游戏的脚本配置可能产生不同表现。
2. `TextSkip` 的 `0..3` 数值对应关系尚未从当前 reference 中完全恢复。
3. `TextSpeed(-1)` 的确切业务意义仍需结合原版文本推进逻辑验证。
4. `TextFunction` 的 ruby、特殊单元和 wait mode 数值已经有源码注释映射，但各模式的最终视觉/脚本差异仍建议结合样本验证。
5. `TextDataGet/Set` 与 `TextHistory` 的 legacy 文本历史 UI 显示链尚未完全恢复；当前实现主要恢复了内存状态和读取接口。
6. `TextHyphenation` 当前只是 `TextSuspendChr` 的兼容映射，原版断词/断行逻辑是否更复杂，reference 不足以确认。
7. `TextSize` 的数据库返回类型为 `Mixed`，但当前设置实现返回 `Nil`；该字段可能是历史 ABI 合并结果，后续应结合数据库生成脚本和旧版调用约定修正。
8. `TextOutSize`、`TextFont`、`TextColor`、`TextSize` 的实际参数数量在 handler 中兼容早期 ABI，HCB 导入表中的 argc 与运行时分支需要结合具体游戏版本判断。

---

## 13. 证据来源

- [`README.md`](fvp_analysis/result/syscall语义数据库/README.md:107-109)
- [`syscall_spec.json`](fvp_analysis/result/syscall语义数据库/syscall_spec.json:6032-7285)
- [`syscall_spec.txt`](fvp_analysis/result/syscall语义数据库/syscall_spec.txt:138-160)
- [`generated.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs:131-157)
- [`world.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs:624-646)
- [`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:10-891)
- [`text.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/text.rs:895-1245)
- [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:171-193)
- [`legacy.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/legacy.rs:485-570)
- [`gpu_prim.rs`](fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src/rendering/gpu_prim.rs:594-667)
- [`21_Prim.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/21_Prim.md:779-825)
- [`11_History.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/11_History.md:145-147)
- [`02_Color.md`](fvp_analysis/result/syscall语义数据库/syscall含义详解/02_Color.md:102-139)
