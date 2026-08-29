# -*- coding: utf-8 -*-
"""Generate Sakura SPEAK function structure analysis markdown.

Inputs:
- Sakura_SPEAK          raw concatenated bytecode for all SPEAK functions before 0x19E0
- Sakura_hcb_ir/Sakura.lua
- Sakura_hcb_ir/Sakura.ir.json

Output:
- SPEAK函数功能块结构分析.md
"""
from __future__ import annotations

from pathlib import Path
import json
import re
import struct
from typing import Any

BASE_DIR = Path("fvp_analysis/result/hcbtool_test")
RAW_PATH = BASE_DIR / "Sakura_SPEAK"
LUA_PATH = BASE_DIR / "Sakura_hcb_ir" / "Sakura.lua"
IR_PATH = BASE_DIR / "Sakura_hcb_ir" / "Sakura.ir.json"
OUT_PATH = BASE_DIR / "SPEAK函数功能块结构分析.md"

OPNAMES = {
    0x00: "nop", 0x01: "init_stack", 0x02: "call", 0x03: "syscall", 0x04: "ret", 0x05: "retv",
    0x06: "jmp", 0x07: "jz", 0x08: "push_nil", 0x09: "push_true", 0x0A: "push_i32", 0x0B: "push_i16",
    0x0C: "push_i8", 0x0D: "push_f32", 0x0E: "push_string", 0x0F: "push_global", 0x10: "push_stack",
    0x11: "push_global_table", 0x12: "push_local_table", 0x13: "push_top", 0x14: "push_return",
    0x15: "pop_global", 0x16: "pop_stack", 0x17: "pop_global_table", 0x18: "pop_local_table", 0x19: "neg",
    0x1A: "add", 0x1B: "sub", 0x1C: "mul", 0x1D: "div", 0x1E: "mod", 0x1F: "bit_test", 0x20: "and",
    0x21: "or", 0x22: "set_e", 0x23: "set_ne", 0x24: "set_g", 0x25: "set_ge", 0x26: "set_l", 0x27: "set_le",
}


def u8(b: bytes, i: int) -> int:
    return b[i]


def i8(b: bytes, i: int) -> int:
    return int.from_bytes(b[i:i+1], "little", signed=True)


def u16(b: bytes, i: int) -> int:
    return int.from_bytes(b[i:i+2], "little", signed=False)


def i16(b: bytes, i: int) -> int:
    return int.from_bytes(b[i:i+2], "little", signed=True)


def i32(b: bytes, i: int) -> int:
    return int.from_bytes(b[i:i+4], "little", signed=True)


def u32(b: bytes, i: int) -> int:
    return int.from_bytes(b[i:i+4], "little", signed=False)


def decode_instr(blob: bytes, off: int, base_addr: int, syscalls: dict[int, str]) -> tuple[dict[str, Any], int]:
    start = off
    op = blob[off]
    name = OPNAMES.get(op, f"unk_{op:02X}")
    off += 1
    args: dict[str, Any] = {}
    if op == 0x01:
        args["args"] = i8(blob, off); args["locals"] = i8(blob, off+1); off += 2
    elif op in (0x02, 0x06, 0x07):
        args["target"] = u32(blob, off); off += 4
    elif op == 0x03:
        sid = u16(blob, off); args["id"] = sid; args["name"] = syscalls.get(sid, f"syscall_{sid}"); off += 2
    elif op == 0x0A:
        args["value"] = i32(blob, off); off += 4
    elif op == 0x0B:
        args["value"] = i16(blob, off); off += 2
    elif op == 0x0C:
        args["value"] = i8(blob, off); off += 1
    elif op == 0x0D:
        args["value"] = struct.unpack_from("<f", blob, off)[0]; off += 4
    elif op == 0x0E:
        ln = u8(blob, off)
        raw = blob[off+1:off+1+ln]
        args["length"] = ln
        args["text"] = raw[:-1].decode("shift_jis", errors="replace")
        off += 1 + ln
    elif op in (0x0F, 0x11, 0x15, 0x17):
        args["index"] = u16(blob, off); off += 2
    elif op in (0x10, 0x12, 0x16, 0x18):
        args["index"] = i8(blob, off); off += 1
    return {
        "addr": base_addr + start,
        "offset": start,
        "opcode": op,
        "mnemonic": name,
        "args": args,
        "raw_hex": blob[start:off].hex(" ").upper(),
        "size": off - start,
    }, off


def load_syscalls() -> dict[int, str]:
    ir = json.loads(IR_PATH.read_text(encoding="utf-8"))
    return {int(x["id"]): x["name"] for x in ir["sysdesc"]["syscalls"]}


def get_speak_function_starts() -> list[int]:
    starts = []
    pat = re.compile(r"^function f_([0-9A-F]{8})\(")
    for line in LUA_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"function f_([0-9A-F]{8})\(", line)
        if m:
            addr = int(m.group(1), 16)
            if addr < 0x19E0:
                starts.append(addr)
            else:
                break
    return starts


def extract_lua_sections(starts: list[int]) -> dict[int, list[str]]:
    lines = LUA_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    sections: dict[int, list[str]] = {}
    i = 0
    while i < len(lines):
        m = re.match(r"function f_([0-9A-F]{8})\(", lines[i])
        if not m:
            i += 1
            continue
        addr = int(m.group(1), 16)
        j = i + 1
        while j < len(lines) and lines[j] != "end":
            j += 1
        if j < len(lines):
            if addr in starts:
                sections[addr] = lines[i:j+1]
            i = j + 1
        else:
            break
    return sections


def human_effect(inst: dict[str, Any]) -> str:
    m = inst["mnemonic"]
    a = inst["args"]
    if m == "init_stack":
        return f"函数序言，参数数={a['args']}，局部变量数={a['locals']}"
    if m == "push_i8" or m == "push_i16" or m == "push_i32":
        return f"压入整数常量 {a['value']}"
    if m == "push_string":
        return f"压入字符串 {a['text']!r}"
    if m == "push_global":
        return f"读取全局变量 G[{a['index']}]"
    if m == "pop_global":
        return f"把栈顶写入全局变量 G[{a['index']}]"
    if m == "push_stack":
        return f"读取当前栈帧偏移 {a['index']} 对应的参数/局部值"
    if m == "call":
        return f"调用内部函数 0x{a['target']:08X}"
    if m == "syscall":
        return f"调用 syscall {a['name']} (id={a['id']})"
    if m == "set_e":
        return "比较栈顶两个值是否相等，结果写回栈"
    if m == "set_ne":
        return "比较栈顶两个值是否不等，结果写回栈"
    if m == "set_g":
        return "比较栈顶两个值是否大于"
    if m == "set_ge":
        return "比较栈顶两个值是否大于等于"
    if m == "set_l":
        return "比较栈顶两个值是否小于"
    if m == "set_le":
        return "比较栈顶两个值是否小于等于"
    if m == "or":
        return "把前后两个条件结果做逻辑 or"
    if m == "and":
        return "把前后两个条件结果做逻辑 and"
    if m == "neg":
        return "取负号（常见于把 1 变为 -1）"
    if m == "add":
        return "执行加法并把结果写回栈"
    if m == "jmp":
        return f"无条件跳转到 0x{a['target']:08X}"
    if m == "jz":
        return f"若栈顶为假(Nil)则跳转到 0x{a['target']:08X}"
    if m == "push_nil":
        return "压入 Nil"
    if m == "push_true":
        return "压入 True"
    if m == "push_return":
        return "把最近一次 call/syscall 的返回值压栈"
    if m == "ret":
        return "函数返回"
    return "常规栈机操作"


def extract_summary(addr: int, lua_lines: list[str]) -> dict[str, Any]:
    text = "\n".join(lua_lines)
    summary: dict[str, Any] = {
        "style_id": None,
        "state_global": None,
        "variants": [],
        "uses_conditional_g293": False,
        "property_id": None,
    }
    m = re.search(r"G\[227\] = (\d+)", text)
    if m:
        summary["style_id"] = int(m.group(1))
    m = re.search(r"G\[(20\d{2}|2000|2001|2011)\]", text)
    if m:
        summary["state_global"] = int(m.group(1))
    # variants: detect blocks containing SetAndPrint-like pattern f_0004CCDA
    lines = lua_lines
    for i, line in enumerate(lines):
        if "f_0004CCDA" in line:
            display = None
            alt = None
            trigger = None
            # backtrack two push_string / nil
            window = lines[max(0, i-8):i+1]
            for prev in window:
                sm = re.search(r'S\d+ = "([^"]*)"', prev)
                if sm:
                    if display is None:
                        display = sm.group(1)
                    elif alt is None:
                        alt = sm.group(1)
            if any("= nil" in p for p in window) and alt is None:
                alt = None
            # search previous trigger compare block
            for prev in reversed(lines[max(0, i-20):i]):
                tm = re.search(r"S1 = (-?\d+)", prev)
                if tm:
                    # use nearest integer before compare/jz as tentative trigger
                    trigger = int(tm.group(1))
                    break
            summary["variants"].append({"display": display, "alt": alt, "trigger_guess": trigger})
    if "G[293] = nil" in text and "G[293] = a1" in text:
        summary["uses_conditional_g293"] = True
    m = re.search(r"f_0008D409\((\d+)\)", text)
    if m:
        summary["property_id"] = int(m.group(1))
    return summary


def render_function_section(idx: int, start: int, end: int, blob: bytes, lua_lines: list[str], syscalls: dict[int, str]) -> str:
    out = []
    out.append(f"## {idx}. function `f_{start:08X}`")
    out.append("")
    out.append(f"- 原始 HCB 起始地址：`0x{start:08X}`")
    out.append(f"- 原始 HCB 结束地址：`0x{end:08X}`")
    out.append(f"- 函数长度：`0x{end - start:04X}` / `{end - start}` 字节")
    out.append("")
    summary = extract_summary(start, lua_lines)
    if summary["style_id"] is not None:
        out.append(f"### 结构摘要")
        out.append("")
        out.append(f"- 样式编号 `G[227]`：`{summary['style_id']}`")
        if summary["state_global"] is not None:
            out.append(f"- 主要状态变量：`G[{summary['state_global']}]`")
        if summary["property_id"] is not None:
            out.append(f"- 角色属性查表编号：`{summary['property_id']}`")
        out.append(f"- `G[293]` 是否条件写入：`{'是' if summary['uses_conditional_g293'] else '否'}`")
        if summary["variants"]:
            out.append(f"- 名字分支候选：")
            for v in summary["variants"]:
                out.append(f"  - display=`{v['display']}` alt=`{v['alt']}` trigger_guess=`{v['trigger_guess']}`")
        out.append("")
    out.append("### Lua-like 片段")
    out.append("")
    out.append("```lua")
    excerpt = lua_lines[:80]
    out.extend(excerpt)
    if len(lua_lines) > 80:
        out.append("-- ...")
    out.append("```")
    out.append("")
    out.append("### 逐条反汇编对照")
    out.append("")
    out.append("| 地址 | 字节 | 指令 | 作用解释 |")
    out.append("|---:|---|---|---|")
    off = 0
    while off < len(blob):
        inst, off2 = decode_instr(blob, off, start, syscalls)
        arg_desc = ""
        a = inst["args"]
        if inst["mnemonic"] == "init_stack":
            arg_desc = f" {a['args']},{a['locals']}"
        elif inst["mnemonic"] in {"call", "jmp", "jz"}:
            arg_desc = f" 0x{a['target']:08X}"
        elif inst["mnemonic"] == "syscall":
            arg_desc = f" {a['id']} ({a['name']})"
        elif inst["mnemonic"] in {"push_i8", "push_i16", "push_i32", "push_f32"}:
            arg_desc = f" {a['value']}"
        elif inst["mnemonic"] == "push_string":
            arg_desc = f" len={a['length']} {a['text']!r}"
        elif inst["mnemonic"] in {"push_global", "push_global_table", "pop_global", "pop_global_table"}:
            arg_desc = f" {a['index']}"
        elif inst["mnemonic"] in {"push_stack", "push_local_table", "pop_stack", "pop_local_table"}:
            arg_desc = f" {a['index']}"
        out.append(f"| `0x{inst['addr']:08X}` | `{inst['raw_hex']}` | `{inst['mnemonic']}{arg_desc}` | {human_effect(inst)} |")
        off = off2
    out.append("")
    out.append("### 功能解释")
    out.append("")
    out.append("这类函数整体上都属于 `SPEAK function`：先设置 `G[227]` 样式编号，再调用 `f_000019E0` 之前的文本样式初始化函数，然后根据参数分支决定显示名字、同步状态并写入 `G[29] / G[293] / G[294] / G[295]`。")
    out.append("")
    return "\n".join(out)


def general_analysis(function_starts: list[int], sections: dict[int, list[str]]) -> str:
    out = []
    out.append("## 统一结构分析：SPEAK 函数的更普遍模式")
    out.append("")
    out.append("基于对 `Sakura_SPEAK` 中全部 SPEAK 函数的观察，再结合已经详细解析过的三个样例（`クロ`、`大雅/ぼく`、`ソル/一磨/遠矢`），可以把 SPEAK 函数抽象成更普遍的结构。")
    out.append("")
    out.append("### 1. 固定骨架")
    out.append("")
    out.append("绝大多数 SPEAK 函数都遵循：")
    out.append("")
    out.append("```text")
    out.append("init_stack")
    out.append("push style_id")
    out.append("G[227] = style_id")
    out.append("call f_000019E0(G[227])        ; 配置名字栏/正文的文本样式")
    out.append("[可选] 处理名字公开状态变量（如 G[2001]/G[2000]/G[2011]）")
    out.append("[若干模式分支] -> f_0004CCDA(name, alt_name)")
    out.append("                -> f_000977B8(sync_id, true)")
    out.append("[可选] 默认分支下额外推进状态")
    out.append("G[29] = 1")
    out.append("G[293] = arg / nil / conditional")
    out.append("G[294] = arg")
    out.append("G[295] = f_0008D409(property_id)")
    out.append("ret")
    out.append("ret")
    out.append("```")
    out.append("")
    out.append("### 2. 可变项")
    out.append("")
    out.append("不同 SPEAK 函数之间，真正变化的部分主要只有：")
    out.append("")
    out.append("1. `G[227]` 的样式编号")
    out.append("2. 状态变量编号（如 `G[2001]` / `G[2000]` / `G[2011]`）")
    out.append("3. 模式参数从哪个 `push_stack` 取值")
    out.append("4. 每个模式触发值（如 `-1`, `10`, `20`, `100`）")
    out.append("5. 每个分支对应显示名与备用/问号名")
    out.append("6. `f_000977B8` 的同步编号（有的直接用 `G[227]`，有的用固定值）")
    out.append("7. `G[293]` 的写入策略（总写 / 条件写 / 写 nil）")
    out.append("8. `f_0008D409` 的属性编号")
    out.append("")
    out.append("### 3. 共同职责")
    out.append("")
    out.append("这些函数的共同职责不是“打印一段台词”，而是：")
    out.append("")
    out.append("> **在文本框左侧名字栏中，以某个特定的样式显示某个角色或角色组在当前剧情状态下应呈现的名字。**")
    out.append("")
    out.append("也就是说，它们共同构成了一个：")
    out.append("")
    out.append("> **说话人名显示系统 / 身份公开状态机系统**")
    out.append("")
    out.append("### 4. 进一步工程意义")
    out.append("")
    out.append("这意味着，未来如果要把 SPEAK 函数做成更高层的编辑器或 DSL，可以直接把它们看成：")
    out.append("")
    out.append("- 一个固定模板")
    out.append("- 若干可编辑字段")
    out.append("- 若干名字变体分支")
    out.append("- 一个状态推进规则")
    out.append("")
    out.append("这正是当前 `hcbrebuild_test/speak_function_gui.py` 走的方向。")
    return "\n".join(out)


def main() -> None:
    syscalls = load_syscalls()
    starts = get_speak_function_starts()
    raw = RAW_PATH.read_bytes()
    # Compute boundaries by original HCB addresses.
    boundaries = []
    for idx, start in enumerate(starts):
        end = starts[idx + 1] if idx + 1 < len(starts) else 0x19E0
        boundaries.append((start, end))
    # Verify concatenation size.
    total = sum(e - s for s, e in boundaries)
    if total != len(raw):
        raise SystemExit(f"size mismatch: expected concatenated size {total}, got {len(raw)}")
    lua_sections = extract_lua_sections(starts)
    cur = 0
    parts = []
    parts.append("# SPEAK函数功能块结构分析")
    parts.append("")
    parts.append("## 0. 说明")
    parts.append("")
    parts.append("本文针对 `Sakura_SPEAK` 中汇总的全部 SPEAK 函数做统一分析。所谓 SPEAK 函数，是指在 `Sakura.hcb` 前半段批量定义的、用于控制文本框左侧说话人名显示的函数族。")
    parts.append("")
    parts.append("分析方法：")
    parts.append("")
    parts.append("1. 使用 `Sakura_SPEAK` 中的原始字节串逐个切分函数。")
    parts.append("2. 使用 `Sakura.lua` 中对应函数的 Lua-like IR 进行对照。")
    parts.append("3. 对每个函数给出逐条反汇编与功能解释。")
    parts.append("4. 最后再总结这类 SPEAK 函数的普遍结构。")
    parts.append("")
    parts.append(f"- 函数总数：`{len(boundaries)}`")
    parts.append(f"- 原始拼接字节长度：`{len(raw)}` / `0x{len(raw):X}`")
    parts.append("")
    for i, (start, end) in enumerate(boundaries, 1):
        blob = raw[cur:cur + (end - start)]
        cur += (end - start)
        lua_lines = lua_sections.get(start, [f"function f_{start:08X}(...)", "  -- 对应 Lua 片段未找到", "end"])
        parts.append(render_function_section(i, start, end, blob, lua_lines, syscalls))
    parts.append(general_analysis(starts, lua_sections))
    OUT_PATH.write_text("\n\n".join(parts) + "\n", encoding="utf-8")
    print(OUT_PATH)
    print(f"functions={len(boundaries)}")


if __name__ == "__main__":
    main()
