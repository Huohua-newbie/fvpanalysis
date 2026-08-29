# 05 · BIN 与 HZC 资源格式

> **前置阅读**：[01 · FVP 引擎总览](./01-overview.md)

FVP 的资源系统围绕两类容器构建：`.bin` 是通用资源包，`HZC/NVSG` 是图像容器。理解它们对做资源替换、汉化和原创内容都至关重要。

---

## `.bin` 资源包（simple BIN/FVP 格式）

### 结构

```c
struct FvpBin {
    u32 file_count;          // 包内文件总数
    u32 name_table_size;     // 文件名表的字节长度

    // 索引表，每条 12 字节
    struct Entry {
        u32 name_offset;     // 相对名字表起点的偏移
        u32 data_offset;     // 相对 bin 文件起点的偏移
        u32 data_size;       // 该条目数据大小（字节）
    } entries[file_count];

    char names[name_table_size]; // NUL 分隔的文件名列表
    u8   payload[];              // 所有条目的数据，按 offset/size 存储
}
```

### 条目类型推断

`.bin` 不存储类型标记，按条目数据开头的魔数（magic）猜测类型：

| 开头字节 | 类型 |
|---|---|
| `hzc1` | HZC 图像容器 |
| `OggS` | OGG 音频 |
| `RIFF` | WAV 音频 |
| `\x89PNG` | PNG 图像 |
| `\xFF\xD8\xFF` | JPG 图像 |
| `BM` | BMP 图像 |
| `TLG5.0` / `TLG6.0` | TLG 图像 |

### 文件名排序与 locale

`.bin` 包内的文件名**不是随机顺序**。原始工具链使用 `CompareStringA(0x411, NORM_IGNORECASE, ...)` 排序，即**日文 locale、忽略大小写**的字符串比较。

这意味着：
- 引擎查找资源时可能依赖有序列表做二分查找；
- 重新打包 `.bin` 时，如果文件名排序不符合原规则，可能导致"包能打开但找不到资源"的崩溃；
- 在非日文环境重建包时，最安全的做法是**保留原条目顺序**。

### 旧格式：ACPX/XPK

GARbro 里还实现了一种 Favorite 旧式归档格式（签名 `ACPX`/`XPK01`，条目 0x28 字节，支持 LZW 压缩）。本项目当前不把它纳入主线，遇到时单独处理。

---

## HZC / NVSG 图像容器

HZC 是 FVP 最常见的图像格式。准确说，它是两个概念叠加：

- **`hzc1`**：外层容器/压缩标识
- **`NVSG`**：内层图像数据头

大多数情况下二者绑定出现，但概念上应分开理解——`hzc1` 描述"这是一个压缩载体"，`NVSG` 描述"载体内部是什么图像"。

### 标准头部（44 字节，`header_size = 0x20`）

| 偏移 | 大小 | 字段 | 说明 |
|---|---:|---|---|
| `0x00` | 4 | `magic` | 固定 `hzc1` |
| `0x04` | 4 | `uncompressed_size` | 解压后 raster 大小（字节） |
| `0x08` | 4 | `header_size` | 常见 `0x20`（32 字节） |
| `0x0C` | 4 | `payload_magic` | 固定 `NVSG` |
| `0x10` | 2 | `unknown1` | 常见 `0x0100`，保留原样 |
| `0x12` | 2 | `type` | 图像模式（见下表） |
| `0x14` | 2 | `width` | 宽度（像素） |
| `0x16` | 2 | `height` | 高度（像素） |
| `0x18` | 2 | `offsetX` | 游戏内显示偏移 X（**signed** int16） |
| `0x1A` | 2 | `offsetY` | 游戏内显示偏移 Y（**signed** int16） |
| `0x1C` | 2 | `unknown2` | 保留 |
| `0x1E` | 2 | `unknown3` | 保留 |
| `0x20` | 4 | `image_count` | 多帧/差分帧数，0 视为 1 |
| `0x24` | 8 | padding | 补到总头长 44 字节 |
| `0x2C` | 变长 | payload | 压缩图像数据（zlib 或 TLG） |

### `type` 字段含义

| 值 | 含义 | 通道 |
|---:|---|---|
| `0` | 单帧 BGR24 | 3 字节/像素 |
| `1` | 单帧 BGRA32 | 4 字节/像素（含 alpha） |
| `2` | 多帧/差分帧组 BGRA32 | 4 字节/像素 × N 帧 |
| `3` | 8 位灰度 | 1 字节/像素 |
| `4` | 黑白/二值近似 | 待验证 |

背景图通常是 `type=0`，立绘/UI 按钮通常是 `type=1`，表情差分通常是 `type=2`。

### `offsetX / offsetY` 的重要性

这两个字段表示图像在游戏画面中的**显示偏移**，是场景合成参数，不是图像内容本身。

- 立绘图常有非零偏移，用于精确定位角色在屏幕上的位置；
- 替换图片时**必须保留原始偏移**，否则画面位置会错位；
- 重建 HZC 时不能只根据 PNG 重新生成头部，必须读取原 HZC 头并继承这些字段。

---

## 标准 zlib 型 HZC 的 payload

解压（zlib inflate）后得到原始像素栅格数据（raw raster）：

- `type=0`：按 `BGR` 排列，每行 `width × 3` 字节，从上到下
- `type=1`：按 `BGRA` 排列，每行 `width × 4` 字节
- `type=2`：多帧连续存放，`frame_size = width × height × 4`

> **关于"BMP 行倒序"说法**：早期民间文档常说 HZC 是"去掉 BMP 头再反转行序 + zlib"。这个说法和"raw raster 从上到下"本质等价（BMP 是从下往上），但现代工具直接按 raw raster 处理更简洁，不需要 BMP 作为中间形态。

重建标准 zlib HZC 时，压缩等级用 `9`，通常可复现原始文件的 `0x78 0xDA` zlib header。

---

## TLG 负载型 HZC（非标准变体）

在较新的 HD / Steam 版资源里，HZC 的外层头部（`hzc1 + NVSG`）不变，但 payload 不是 zlib，而是：

- `TLG5.0`（5 字节签名）
- `TLG6.0`
- `TLG0.0\0sds\x1a`（SDS 包裹的 TLG）

处理这类文件时，必须先识别 payload 类型，再分支走不同的解码路径：

```
读取 HZC 头部
→ 检查 payload 开头
  → 若是 zlib (0x78 xx) → 标准路径
  → 若是 TLG5.0/6.0  → TLG 解码路径
  → 若是 TLG0.0 SDS   → SDS 解包 → TLG 解码
```

某些 TLG-HZC 还带有差分底图关系（一张基础图 + 若干差分帧），需要先合成再使用。

---

## 音频资源

BIN 里的音频直接以标准格式存储：

- `OggS` → OGG Vorbis（最常见，语音和 BGM）
- `RIFF` → WAV（某些音效）

解包后直接可用，无需额外处理。

---

## 视频资源

OP 等视频通常以**外置文件**形式存放在 `movie/` 目录，格式常见 `.wmv`，不封入 `.bin`。引擎通过 `Movie` syscall 调用系统媒体播放器播放。

---

## 重建 BIN 的注意事项

做资源替换时的最佳实践：

1. **研究阶段**：优先用 loose 文件覆盖（直接放到同名目录），快速验证，不必重封；
2. **分发阶段**：需要封回 `.bin` 时，保持原条目顺序；
3. **注意文件名**：BIN 里的文件名是 Shift-JIS 字节串，重命名时要记录原始字节名和解码后的文本名；
4. **不要改 offset 以外的头部字段**：重建时只更新条目的 `data_offset` 和 `data_size`，不改名字表顺序。

---

## 下一篇

[→ 06 · HCB 可逆转换工具链](./06-hcb-ir-toolchain.md)
