# 12 · 案例：Sakura 开场电车 CG 加载链

> **前置阅读**：[11 · 冷启动与 boot 全局量](./11-coldstart-boot-globals.md)、[03 · VM 与指令集](./03-vm-and-opcodes.md)
>
> 置信度：**[已验证]**（calltrace + `--break-pc` 二分 + 开关全局量对照；地址为 `Sakura.hcb` 实测）。

以开场电车 CG（`KURO_e011b2`，红兜帽熟睡 + 邻座少年）为例，演示 CG 从“剧本里一个字符串”到“进 graph 槽”的完整链条。理解这条链，才能明白 CG 显示需要哪些前置状态。

## 1. 链条总览

```text
666627: call 9611                    # 场景流（"春色"句后，6 参数全 Nil 除末参 1100）
9611:   push "KURO_e011b2" + 栈值 → call 332832     # 1020 个同族 stub 之一（9219+56k），各带一个 CG 名
332832: 变体选择（读参数 + boot 全局量，见 [11]) → call 333826
333826: 清理旧槽 (188/189) → call 334016
334016: push 190 / 191 + 名 → call 225940            # CG 固定进槽 190/191
225940: prefix + name → GraphLoad(slot, "graph_vis/KURO_e011b2")
        → PrimSetSprt/OP/Z/RS/XY + V3DSet（摆位）
```

要点：

- **名是逐级显式传递的**（`push_stack -N` 取参），不是全局量。每一跳的 `init_stack args=N` 与“取最后 N 个压栈值”严格对应（规则见 [13](./13-methods-calltrace-stack.md)）。
- **槽号是常量**：CG 固定 `190/191`，BG 走另一条（`331832`，槽 `186/187`）。`GraphLoad(190, Nil)` 只是换图前的卸载，别误读成“加载失败”。
- **前缀动态**：`225940` 按 `global8` 拼 `graph_vish/ | graph_sd/ | graph_vis/`（默认 vis）。
- `9611` 一族（`9219, 9275, …, 9611, 9667, …`，步长 56）是“一名一函数”的 CG 登记表；真正的 CG 总表函数另有其人（`260217`，含 `KURO_e011~e013` 全系，被 4 个分发点调用）。

## 2. 显示侧（`332832` 后半）

加载完成后同一函数继续：`PrimSetNull → PrimSetOP/Z/RS/XY`（`190/191`）、`V3DSet`（相机）、`DissolveWait`（`global68==Nil` 时跳过等待）。即“加载—摆位—转场等待”三段式是同一个 CG 单元包办的。

## 3. 调试时认链指纹

trace 里看到以下组合，即 CG 链在跑（无论最终成败）：

- `PrimSetAlpha/Draw(190/191)`（setup）
- `GraphLoad(190/191, Nil)`（卸载旧图）
- `Dissolve(mask)` + `DissolveWait`

只看到前两项、没有命名 `GraphLoad(190/191, "graph_vis/…")` → 卡在变体门，按 [11] 查全局量。

## 4. 待验证

- `260217` 的 4 个调用点分别对应什么演出（gallery 回想 vs 主线）。
- `190/191` 双槽的分工（左右眼/差分 AB 面？本案 e011a1/b2/c2…轮流进 `191`）。
