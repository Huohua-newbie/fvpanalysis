#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sakura.lua 函数依赖图提取器

从 hcb_to_ir.py 生成的 Lua-like 栈 IR 中提取函数调用依赖图。
- 节点：脚本函数 f_XXXXXXXX 与 syscall（宿主函数）
- 边：调用关系；syscall 视为叶子节点（不继续展开）
- 输出：dependency.json、dependency.dot、stats.json

Lua IR 约定：
    函数定义  function f_XXXXXXXX(a0, ...) ... end
    函数调用  __ret = f_XXXXXXXX(...)
    syscall   __ret = __syscall("Name", ...)

依赖图语义：
    - 关系边：A->B 表示函数 A 调用 B（B 可为本脚本函数或 syscall）
    - count：该 (A,B) 调用边出现的原始次数
    - syscall 节点恒为叶子（无出边）
"""
import re
import json
import collections

LUA = 'Sakura.lua'

FUNC_DEF_RE = re.compile(r'^function\s+(f_[0-9A-F]+)\s*\(')
FUNC_CALL_RE = re.compile(r'__ret\s*=\s*(f_[0-9A-F]+)\s*\(')
SYSCALL_RE = re.compile(r'__ret\s*=\s*__syscall\("([^"]+)"')


def parse():
    """逐行扫描，收集每个函数的原始调用序列（不去重，保留真实 count）。"""
    funcs = []       # [{'name':..., 'calls':[raw...], 'syscalls':[raw...]}]
    cur = None
    calls = []
    syscalls = []

    def flush():
        nonlocal cur, calls, syscalls
        if cur is not None:
            funcs.append({'name': cur, 'calls': list(calls), 'syscalls': list(syscalls)})
        calls = []
        syscalls = []

    with open(LUA, encoding='utf-8') as f:
        for line in f:
            mu = FUNC_DEF_RE.match(line)
            if mu:
                flush()
                cur = mu.group(1)
                continue
            if cur is None:
                continue
            mc = FUNC_CALL_RE.search(line)
            if mc:
                calls.append(mc.group(1))
                continue
            ms = SYSCALL_RE.search(line)
            if ms:
                syscalls.append(ms.group(1))
    flush()
    return funcs


def main():
    funcs = parse()
    names = [f['name'] for f in funcs]
    name_set = set(names)

    # 全部出现的 syscall 名
    syscall_names = sorted({s for f in funcs for s in f['syscalls']})

    # 调用边计数（保留原始 count）
    edges = collections.Counter()  # (src, dst) -> count
    for f in funcs:
        src = f['name']
        for dst in f['calls']:
            edges[(src, dst)] += 1          # dst 为脚本函数或未定义目标
        for s in f['syscalls']:
            edges[(src, 'syscall:' + s)] += 1

    # 入度 / 出度（基于去重后的唯一关系边）
    in_deg = collections.Counter()
    out_deg = collections.Counter()
    for (s, d) in edges:
        out_deg[s] += 1
        in_deg[d] += 1

    # 叶子：syscall 恒为叶子；脚本函数若出度为 0 也为叶子
    func_leaf = [n for n in name_set if out_deg[n] == 0]
    syscall_nodes = ['syscall:' + s for s in syscall_names]

    # 统计
    func_call_occurrences = sum(1 for f in funcs for _ in f['calls'])
    syscall_occurrences = sum(1 for f in funcs for _ in f['syscalls'])
    stat = {
        'functions_defined': len(names),
        'unique_dep_edges': len(edges),
        'function_call_occurrences': func_call_occurrences,
        'syscall_occurrences': syscall_occurrences,
        'total_call_sites': func_call_occurrences + syscall_occurrences,
        'unique_syscalls': len(syscall_names),
        'unique_syscall_edges': sum(1 for (s, d) in edges if d.startswith('syscall:')),
        'func_leaf_nodes': len(func_leaf),
        'func_defined_and_called': len(set(x for x in in_deg if x in name_set)),
        'func_never_called': len([n for n in name_set if in_deg[n] == 0]),
    }

    print(json.dumps(stat, ensure_ascii=False, indent=2))

    # --- dependency.json ---
    dep = {
        'schema': 'fvp-lua-dep-graph/2',
        'source': 'Sakura_hcb_ir/Sakura.lua',
        'nodes': {
            'functions': names,
            'syscalls': syscall_names,
            'leaf_functions': func_leaf,
        },
        'edges': [{'src': s, 'dst': d, 'count': c}
                  for (s, d), c in sorted(edges.items())],
        'stats': stat,
    }
    with open('dependency.json', 'w', encoding='utf-8') as fo:
        json.dump(dep, fo, ensure_ascii=False, indent=2)

    # --- dependency.dot ---
    with open('dependency.dot', 'w', encoding='utf-8') as fo:
        fo.write('digraph FVP {\n')
        fo.write('  rankdir=LR;\n')
        fo.write('  node [shape=box, fontname="Consolas"];\n')
        # syscall 叶子（橙色圆）
        fo.write('  node [shape=ellipse, color=#c2570a, style=filled, fillcolor="#ffe8cc", fontcolor="#7a3b00"];\n')
        for s in syscall_nodes:
            fo.write(f'  "{s}" [label="{s[8:]}"];\n')
        # 出度为 0 的脚本函数（绿色椭圆）
        if func_leaf:
            fo.write('  node [shape=ellipse, color=#1a5c1a, style=filled, fillcolor="#d8f5d0", fontcolor="#1a5c1a"];\n')
            for n in func_leaf:
                fo.write(f'  "{n}" [label="{n}"];\n')
        # 普通函数（蓝框）
        fo.write('  node [shape=box, color=#3a4a6b, style=filled, fillcolor="#eef2ff", fontcolor="#1f2a44"];\n')
        for n in names:
            if n not in set(func_leaf):
                fo.write(f'  "{n}" [label="{n}"];\n')
        # 边
        for (s, d) in sorted(edges):
            fo.write(f'  "{s}" -> "{d}";\n')
        fo.write('}\n')

    print(f"已写入 dependency.json / dependency.dot  (函数 {len(names)}, 唯一边 {len(edges)})")


if __name__ == '__main__':
    main()
