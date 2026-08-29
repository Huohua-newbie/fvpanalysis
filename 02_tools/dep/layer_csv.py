#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 dependency.json 的调用依赖图按「反向拓扑分层」输出为 CSV。

分层语义（用户需求）：
    layer 0  = 叶子节点：只被调、不调用任何节点的节点（syscall 恒为叶子；出度为 0 的脚本函数）
    layer N  = 只调用 layer ≤ N-1 内节点的函数（不再「直接」调用更高层/未被分层的节点）

核心：对「A 调用 B」边，取 A 的层号 = max( A 的所有被调方层号 ) + 1。
即从叶子出发、逆着调用方向传播的「最长路径」层号。

含环处理：先用 Tarjan 求强连通分量(SCC)缩环，把每个环合并为单个逻辑节点(type=cycle)，
再对缩点后的 DAG 做分层，保证环内节点不会被错误地互相抬高层号。
"""
import json
import csv
import collections
import sys

d = json.load(open('dependency.json', encoding='utf-8'))
functions = d['nodes']['functions']                 # 全量脚本函数
syscalls = d['nodes']['syscalls']                   # 130 个 syscall 名
leaf_functions = set(d['nodes']['leaf_functions'])  # 出度 0 的脚本函数
edges = d['edges']
stats = d.get('stats', {})

fn_set = set(functions)
nodes = list(functions) + ['syscall:' + s for s in syscalls]

# --- 有向邻接（去重唯一关系边） ---
succ = collections.defaultdict(set)   # src -> {dst}
pred = collections.defaultdict(set)   # dst -> {src}
for e in edges:
    s, t = e['src'], e['dst']
    succ[s].add(t)
    pred[t].add(s)

# ============ Tarjan SCC ============
index = {}
low = {}
onstack = set()
stack = []
scc_of = {}          # node -> scc_id
sccs = []            # list of set(node)
counter = [0]

def strongconnect(v):
    index[v] = low[v] = counter[0]; counter[0] += 1
    stack.append(v); onstack.add(v)
    for w in succ[v]:
        if w not in index:
            strongconnect(w)
            low[v] = min(low[v], low[w])
        elif w in onstack:
            low[v] = min(low[v], index[w])
    if low[v] == index[v]:
        comp = set()
        while True:
            w = stack.pop(); onstack.discard(w); comp.add(w); scc_of[w] = len(sccs)
            if w == v:
                break
        sccs.append(comp)

for n in nodes:
    if n not in index:
        strongconnect(n)

# SCC 是否含环（尺寸>1，或自环）
scc_is_cycle = []
for comp in sccs:
    cyc = len(comp) > 1
    if not cyc:
        only = next(iter(comp))
        cyc = only in succ.get(only, set())   # 自环
    scc_is_cycle.append(cyc)

# 缩点 DAG
scc_succ = collections.defaultdict(set)
for s, dsts in succ.items():
    si = scc_of[s]
    for t in dsts:
        ti = scc_of[t]
        if si != ti:
            scc_succ[si].add(ti)

# ============ SCC 层号（在缩点 DAG 上） ============
# 叶子 SCC：不含出边（到其它 SCC）的 SCC。syscall SCC 一定出度为 0；出度为0函数 SCC 同理。
scc_outdeg = {i: len(scc_succ[i]) for i in range(len(sccs))}
# 层号：scc_layer[i] = 0 if 出度为0  else 1 + max(scc_layer[j] for j in scc_succ[i])
# 用逆拓扑（Kahn）从 sink 开始
scc_layer = [0] * len(sccs)
# 反向邻接
scc_pred = collections.defaultdict(set)
for i in scc_succ:
    for j in scc_succ[i]:
        scc_pred[j].add(i)
# 剩余未处理的出边数（到已定层 j 的关系由后向传播处理）
# 这里直接用「延迟传播」：反复对每个 i 用其子 SCC 定层，模拟最长路径
# 但需要拓扑序。先做拓扑排序（从 sink 开始）。
order = {}
visited = [False]*len(sccs)
def dfs_top(u, tmp, perm):
    if tmp[u]: return  # 已经在路径中（环已缩点，不应出现）
    visited[u] = True
    for w in scc_succ[u]:
        if not visited[w]:
            dfs_top(w, tmp, perm)
    perm.append(u)
perm = []
for i in range(len(sccs)):
    if not visited[i]:
        tmp = [False]*len(sccs)
        dfs_top(i, tmp, perm)
# perm 是 DFS 后序：子节点先被 append，父节点后来 append。
# 因此按 perm 从前到后处理 → 先处理子节点、后处理父节点，
# 计算父层号所需的子层号必然已知。这正是「叶子先、逐层上推」的正确顺序。
for i in perm:
    if not scc_succ[i]:
        scc_layer[i] = 0
    else:
        mx = 0
        for j in scc_succ[i]:
            mx = max(mx, scc_layer[j])
        scc_layer[i] = mx + 1

# ==== 环内节点层号：整个 SCC 视为同层（取其内部最大合法层，防止互相抬高） ====
# 对环 SCC，层号 = scc_layer[scc]，环内所有节点同层，并在 type 标注 cycle。

# ============ 生成 CSV ============
def node_type(n):
    if n.startswith('syscall:'):
        return 'syscall'
    if scc_is_cycle[scc_of[n]] and len(sccs[scc_of[n]]) > 1:
        return 'cycle'
    return 'function'

def node_layer(n):
    return scc_layer[scc_of[n]]

rows = []
for node in nodes:
    t = node_type(node)
    name = node[8:] if t == 'syscall' else node
    lyr = node_layer(node)
    rows.append({
        'layer': lyr,
        'name': name,
        'type': t,
        'out_degree': len(succ.get(node, set())),
        'in_degree': len(pred.get(node, set())),
        'degree': len(succ.get(node, set())) + len(pred.get(node, set())),
    })

rows.sort(key=lambda r: (r['layer'], 0 if r['type'] == 'syscall' else (1 if r['type'] == 'function' else 2), r['name']))

with open('layer_dep.csv', 'w', newline='', encoding='utf-8-sig') as fo:
    w = csv.writer(fo)
    w.writerow(['layer', 'name', 'type', 'out_degree', 'in_degree', 'degree'])
    for r in rows:
        w.writerow([r['layer'], r['name'], r['type'], r['out_degree'], r['in_degree'], r['degree']])

max_layer = max(scc_layer) if scc_layer else 0
layer_dist = collections.Counter(r['layer'] for r in rows)
type_dist = collections.Counter(r['type'] for r in rows)
cycle_nodes = sum(1 for r in rows if r['type'] == 'cycle')
print('max_layer:', max_layer)
print('layer_dist (layer->count):', dict(sorted(layer_dist.items())))
print('type_dist:', dict(type_dist))
print('cycle 节点数(缩环):', cycle_nodes)
print('总节点:', len(nodes))
print('CSV 已写入 layer_dep.csv')
