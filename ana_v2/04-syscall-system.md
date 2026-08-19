# 04 · Syscall 系统

> **前置阅读**：[03 · VM 与指令集](./03-vm-and-opcodes.md)

Syscall 是 HCB 脚本与引擎宿主世界之间的全部连接。单看 opcode，FVP 的指令集其实不大（0x00–0x27，共 40 条）。**真正难的是 syscall**：它们决定了脚本"实际做了什么"——显示文字、加载图片、播音乐、启动线程、保存存档……

---

## 导入表机制回顾

HCB 尾部的 syscall 导入表把"本脚本用到了哪些宿主函数"一一列出，每条记录包含：

- `arg_count`：调用时从 VM 栈弹出的参数个数
- `name`：syscall 名称字符串（如 `"TextPrint"`）

脚本代码里的 `syscall i16` 指令只存**序号**（即导入表的下标），不存名字。运行时才通过 `序号 → 名字 → 宿主实现` 两步查找来分发调用。

这意味着：
- 不同游戏的 HCB 里，同一个 syscall 的序号可能不同；
- 读懂脚本时，必须先解析 HCB 导入表，建立 `id → name` 映射，再看代码。

---

## 调用约定

VM 执行 `syscall id` 时：

1. 查导入表得到 `arg_count` 和 `name`；
2. 从栈里弹出 `arg_count` 个值，按逆序恢复为调用顺序；
3. 通过 `name` 在宿主 syscall 注册表（`SYSCALL_TBL`）里找到实现；
4. 执行，把结果写入 `return_value`；
5. 调用方若需要返回值，用 `push_return` 取出。

---

## 功能分组

当前语义数据库共收录 **174 个 syscall**，按功能域分组：

| 分组 | 数量 | 典型成员 |
|---|---:|---|
| Text | 27 | `TextPrint`、`TextSize`、`TextSpeed`、`TextColor`、`TextPause` |
| Prim | 21 | `PrimSetSprt`、`PrimSetXY`、`PrimSetWH`、`PrimSetAlpha`、`PrimSetZ` |
| Motion | 19 | `MotionAlpha`、`MotionMove`、`MotionMoveR`、`MotionMoveZ`、`LipSync` |
| Save | 14 | `SaveWrite`、`Load`、`SaveFlagGet`、`SaveFlagSet` |
| Sound | 9 | `SoundLoad`、`SoundPlay`、`SoundStop`、`SoundVolume` |
| Input | 11 | `InputGet`、`ControlPulse`、`MousePosGet` |
| Parts | 8 | `PartsLoad`、`PartsSet`、`PartsUpdate` |
| Audio | 7 | `AudioLoad`、`AudioPlay`、`AudioStop`、`AudioVolume` |
| Thread | 6 | `ThreadStart`、`ThreadWait`、`ThreadSleep`、`ThreadNext`、`ThreadExit` |
| V3D | 5 | 3D 相关（较少用） |
| Movie | 4 | `Movie`、`MovieState`、`MovieStop` |
| Timer | 3 | `TimerStart`、`TimerGet` |
| Snow | 3 | `SnowStart`、`SnowStop` |
| Dissolve | 2 | `DissolveSet`、`DissolveWait` |
| 其他 | … | History、Flag、Gaiji、Cursor、Exit、Window… |

---

## 关键 syscall 详解

### TextPrint

```
参数：(text_buffer_id: Int, text: ConstString)
副作用：向 TextManager 追加文本，启动逐字显示，线程进入 TEXT_WAIT 状态
```

这是视觉小说脚本里出现频率最高的 syscall。它：

1. 把文本写入指定缓冲槽；
2. 触发文本逐字 reveal 动画；
3. 当前脚本上下文进入 `TEXT` 挂起状态；
4. 等待玩家点击（或自动模式计时）后，由场景系统恢复上下文。

典型字节码模式：

```
0C 00          push_i8  0           // text_buffer_id = 0
0E .. "今日も晴れだ\0"  push_string  "今日も晴れだ"
03 XX XX       syscall  TextPrint
```

### GraphLoad

```
参数：(graph_id: Int, path: String)
副作用：加载图像资源到 graph_id 槽，供 PrimSetSprt 引用
```

加载完成后，后续的 prim 操作通过 `graph_id` 引用这张图，不再需要路径字符串。

### PrimSet* 系列

`Prim`（Primitive）是 FVP 的图元/精灵系统。脚本不直接"画图"，而是配置 prim 的属性，由渲染系统自动绘制。常见的 prim 属性设置 syscall：

| syscall | 说明 |
|---|---|
| `PrimSetSprt(prim_id, graph_id, u, v)` | 绑定纹理，设置 UV 起始坐标 |
| `PrimSetXY(prim_id, x, y)` | 设置显示位置 |
| `PrimSetWH(prim_id, w, h)` | 设置显示尺寸 |
| `PrimSetAlpha(prim_id, alpha)` | 设置透明度（0–255） |
| `PrimSetZ(prim_id, z)` | 设置 Z 层级 |
| `PrimSetOP(prim_id, x, y)` | 设置旋转/缩放的参考点（Origin Point） |

### Motion* 系列

Motion syscall 是 FVP 动画系统的入口。它们**启动**一个动画，但不阻塞脚本（除非配合 `DissolveWait` 或 `MotionAlphaTest` 等待逻辑）。

常见参数模式：

```
MotionAlpha(prim_id, src_alpha, dst_alpha, duration_ms, easing?, callback?)
MotionMove(prim_id, src_x, src_y, dst_x, dst_y, duration_ms, easing?, callback?)
MotionMoveR(prim_id, src_rot, dst_rot, duration_ms, easing?, callback?)
MotionMoveZ(prim_id, src_z, dst_z, duration_ms, easing?, callback?)
MotionMoveS2(prim_id, src_sx, src_sy, dst_sx, dst_sy, duration_ms, easing?, callback?)
```

旋转单位是 `0.1°`，所以 `3600 = 360°`（完整一圈）。

### ThreadStart

```
参数：(thread_id: Int, function_addr: Int)
副作用：在 thread_id 槽位启动新的脚本上下文，从 function_addr 开始执行
控制流：starts_context（不阻塞当前线程）
```

⚠️ 特别注意：`function_addr` 是**代码地址**，不是普通整数。回封 HCB 时必须把它纳入地址重定位。

```
0C 05          push_i8  5                  // thread_id = 5
0A XX XX XX XX push_i32 <function_addr>    // 这个立即数是地址！
03 XX XX       syscall  ThreadStart
```

### ThreadWait / ThreadSleep

```
ThreadWait(ms)   → 当前上下文进入 WAIT 状态，ms 毫秒后自动恢复
ThreadSleep(ms)  → 当前上下文进入 SLEEP 状态，需要被 ThreadRaise 唤醒
```

### DissolveWait

```
参数：无（或配置参数）
副作用：若当前有 dissolve（转场溶解）动画在进行，线程进入 DISSOLVE_WAIT 状态，等待完成
```

---

## 控制流副作用分类

syscall 除了修改 GameData，还可能影响 VM 调度，即"让当前线程让出执行"。本项目使用以下标签：

| 标签 | 含义 |
|---|---|
| `yield` | 当前上下文可能让出执行 |
| `wait` | 进入计时等待（`ThreadWait`） |
| `sleep` | 进入睡眠（`ThreadSleep`） |
| `text_wait` | 进入文本显示等待（`TextPrint`） |
| `dissolve_wait` | 等待画面转场完成（`DissolveWait`） |
| `starts_context` | 启动另一个脚本上下文（`ThreadStart`） |
| `exits_context` | 退出当前上下文（`ThreadExit`） |
| `halt` | 暂停宿主推进（如模态播放视频） |

在分析 HCB 的控制流时，这些标签非常有用——遇到带 `wait/sleep/text_wait` 的 syscall，就知道当前线程会在这里"停下来"，等待某个条件再继续。

---

## 语音 ID 的启发式关联

`FVP-Yuki` 工具采用了一种聪明的工程启发式来自动关联台词和语音：

> 若一个 `push_i32` 的值很大（如 > 1,000,000），且其后紧跟 `push_string` 和 `TextPrint`，则暂时把这个大整数记为"语音 ID 候选"。

这不是严格的格式规范，但在实践中效果良好，可以自动生成 `(voice_id, 台词文本)` 对照表。

---

## 数据库文件

`syscall语义数据库/syscall_spec.json` 提供了所有 174 个 syscall 的机器可读记录，每条包含：

- `name`、`group`、`arg_count`
- `parameter_types`（部分已精细化，部分仍是 `confidence=generic` 占位）
- `return_type`
- `affected_game_data_subsystems`
- `control_flow`（是否 yield/wait/sleep/…）
- `verification_status`

后续工具（反编译器、编辑器、DSL 编译器）均可直接引用这个文件。

---

## 下一篇

[→ 05 · BIN 与 HZC 资源格式](./05-bin-and-hzc-formats.md)
