# Sakura.lua 函数依赖图

本目录演示从 `Sakura.lua`（HCB 可逆转换工具链生成的 Lua-like 栈 IR）中提取**函数调用依赖图**，其中 **`syscall` 为叶子节点**。

## 可行性结论

**完全可行。** 因为该 IR 具有非常规整、统一的表达形式，可精确解析：

| 关系 | Lua IR 表达 | 数量 |
|---|---|---|
| 函数定义 | `function f_XXXXXXXX(a0, ...)` | 5,456 |
| 脚本函数调用 | `__ret = f_XXXXXXXX(...)` | 122,559 次 |
| syscall 调用 | `__ret = __syscall("Name", ...)` | 8,672 次 |
| 去重调用边 | `src → dst` | 14,952 |
| 唯一 syscall | `"Name"` | 130 |
| 出度为 0 的叶子函数 | — | 99 |

`syscall` 是宿主提供的函数，**不会继续调用脚本侧的其它函数**，因此天然是依赖图的叶子节点。

## 提取规则

解析逻辑见 [`extract_dep.py`](../../02_tools/dep/extract_dep.py)：

1. **节点**：每个 `function f_XXXXXXXX(...)` 为一个函数节点；每个出现的 `syscall:Name` 为一个 syscall 节点（宿主叶子）。
2. **边**：函数体内的 `__ret = f_YYYYYYYY(...)` 产生 `f_XXXXXXXX → f_YYYYYYYY`；`__ret = __syscall("Name", ...)` 产生 `f_XXXXXXXX → syscall:Name`。
3. **叶子**：syscall 恒为叶子；脚本函数若出度为 0（不调用任何函数），也标记为叶子。
4. 边保留原始调用次数 `count`，同时提供去重后的唯一关系边。

> 说明：函数体以 `function f_...(` 为界，逐行扫描累积调用。`func_never_called: 2,971` 表示这些函数从未被本模块其它函数直接调用（可能是入口/线程起点或死代码）。

## 产出物

| 文件 | 说明 |
|---|---|
| `dependency.json` | 完整结构化依赖图（nodes / edges / stats） |
| `dependency.dot` | Graphviz DOT 描述，可用于外部渲染 |
| `dependency.html` | **自包含交互式浏览器可视化**，双击即可打开 |
| `extract_dep.py` | 提取脚本 |
| `build_html.py` | 由 `dependency.json` 生成 HTML 的脚本 |
| `stats.json` | （可选）独立统计，见 `dependency.json.stats` |

## 统计摘要（来自 `dependency.json`）

```json
{
  "functions_defined": 5456,
  "unique_dep_edges": 14952,
  "function_call_occurrences": 122559,
  "syscall_occurrences": 8672,
  "total_call_sites": 131231,
  "unique_syscalls": 130,
  "unique_syscall_edges": 1616,
  "func_leaf_nodes": 99,
  "func_defined_and_called": 2485,
  "func_never_called": 2971
}
```

- `syscall_occurrences: 8672`：全部 8,672 次 syscall 调用，分布在 130 种 syscall 上；去重后的 `函数→syscall` 关系边 1,616 条。
- `func_leaf_nodes: 99`：99 个脚本函数不调用任何其它节点，加上 130 个 syscall，共 229 个叶子。
- `func_never_called: 2971`：近半数函数仅定义、未被直接调用，符合脚本入口/线程点分布特征。

## 反向拓扑分层 CSV（layer_dep.csv）

[`layer_csv.py`](../../02_tools/dep/layer_csv.py) 把依赖图按「调用层次」反向拓扑分层，写入 `layer_dep.csv`。语义为：

| layer | 含义 |
|---|---|
| 0 | 叶子节点：只被调、不调用任何节点（130 syscall + 99 出度为 0 的脚本函数 = 229） |
| N | 只调用 layer ≤ N-1 内节点的函数（层号 = 其所有被调方层号的最大值 + 1） |

**列**：`layer, name, type, out_degree, in_degree, degree`（type 为 `syscall` / `function` / `cycle`）。

**含环处理**：调用图中存在 3 个小环（6/3/2 节点，共 11 节点），它们来自事件调度/互递归（如 `DissolveWait` 事件循环、`f_00037F11↔f_0004A5DE↔f_0004A608` 互递归）。环上节点无法严格定层，故先用 Tarjan 强连通分量缩环，缩点后再对 DAG 做最长路径分层；环内节点标记为 `type=cycle`。

**验证**：0 条违反「层号 > 被调方层号」的边；layer0 恰为 229 个叶子且全部 syscall 位于 layer0。

> 层分布存在两个大簇（layer5=3501、layer11=1037），原因是大量函数共享同一深度辅助函数（hub），如 `f_00058B8C`（layer4，被 3445 个函数调用）、`f_00051420`/`f_00010271`/`f_00010298`，属真实扇出聚簇。

## 可视化

打开 `dependency.html`：

- **顶部**：品牌区、实时统计（函数 / syscall / 调用边 / 调用点）与图例（函数 / 叶子函数 / syscall）。
- **左侧栏**：「Top 交点」和「Top Syscall」热门节点，点击即改为图中心。
- **搜索框**：支持全量 5456 函数 + 130 syscall 的下拉联想，回车精确定位。
- **方向切换**：`双向 / 被调用 / 调用者` 决定从中心扩展的方向。
- **深度滑块**：**1–5 层 BFS 多层展开**，轻松深入依赖链。
- **画布**：分层横向布局（中心在中间，被调用者向右、调用者向左），`syscall` 为橙色椭圆叶子，出度为 0 的脚本函数为绿色叶子；**自动适配视口**，可滚轮缩放、拖拽平移、`+/−/0` 快捷键。
- **右侧详情面板**：展示节点的调用者/被调用者芯片、度数，点击芯片或「设为中心」可继续下钻。

> 由于整图含 5,456 函数 + 130 syscall、数万条边，直接一次性渲染为一张静态图不可读，因此采用「节点中心式」+ 多层 BFS 展开的交互浏览方式。

## 复现

```bash
cd docs/02_tools/dep
python extract_dep.py   # 生成 dependency.json / dependency.dot
python build_html.py    # 生成 dependency.html
# 产物输出到 docs/04_outputs/diagrams/
```
