# -*- coding: utf-8 -*-
"""Decode and document Sakura f_00002025 byte fragment.

This helper is intentionally local to hcbtool_test because f_00002025 is stored
as a raw function byte fragment without an HCB header/sysdesc table.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

BASE_ADDR = 0x00002025
SRC = Path(__file__).with_name("f_00002025")
OUT_MD = Path(__file__).with_name("f_00002025逐条反汇编对照.md")
OUT_TSV = Path(__file__).with_name("f_00002025逐条反汇编.tsv")

OPCODES: dict[int, tuple[str, str]] = {
    0x00: ("nop", "null"),
    0x01: ("init_stack", "i8i8"),
    0x02: ("call", "x32"),
    0x03: ("syscall", "u16"),
    0x04: ("ret", "null"),
    0x05: ("retv", "null"),
    0x06: ("jmp", "x32"),
    0x07: ("jz", "x32"),
    0x08: ("push_nil", "null"),
    0x09: ("push_true", "null"),
    0x0A: ("push_i32", "i32"),
    0x0B: ("push_i16", "i16"),
    0x0C: ("push_i8", "i8"),
    0x0D: ("push_f32", "f32"),
    0x0E: ("push_string", "string"),
    0x0F: ("push_global", "u16"),
    0x10: ("push_stack", "i8"),
    0x11: ("push_global_table", "u16"),
    0x12: ("push_local_table", "i8"),
    0x13: ("push_top", "null"),
    0x14: ("push_return", "null"),
    0x15: ("pop_global", "u16"),
    0x16: ("pop_stack", "i8"),
    0x17: ("pop_global_table", "u16"),
    0x18: ("pop_local_table", "i8"),
    0x19: ("neg", "null"),
    0x1A: ("add", "null"),
    0x1B: ("sub", "null"),
    0x1C: ("mul", "null"),
    0x1D: ("div", "null"),
    0x1E: ("mod", "null"),
    0x1F: ("bit_test", "null"),
    0x20: ("and", "null"),
    0x21: ("or", "null"),
    0x22: ("set_e", "null"),
    0x23: ("set_ne", "null"),
    0x24: ("set_g", "null"),
    0x25: ("set_ge", "null"),
    0x26: ("set_l", "null"),
    0x27: ("set_le", "null"),
}

SYSCALLS = {
    7: ("ColorSet", 5),
}


@dataclass
class StackVal:
    expr: str
    value: int | None


@dataclass
class InstructionRow:
    index: int
    rel: int
    addr: int
    raw: str
    mnemonic: str
    operand: str
    effect: str
    lua_like: str
    stack_after: str


@dataclass
class ColorSetCall:
    index: int
    first_rel: int
    last_rel: int
    first_addr: int
    last_addr: int
    args: list[StackVal]
    instruction_indices: list[int]


def i8(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 1], "little", signed=True)


def i16(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 2], "little", signed=True)


def i32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 4], "little", signed=True)


def u16(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 2], "little", signed=False)


def u32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off + 4], "little", signed=False)


def fmt_hex(raw: bytes) -> str:
    return raw.hex(" ").upper()


def stack_preview(stack: list[StackVal]) -> str:
    if not stack:
        return ""
    return ", ".join(v.expr for v in stack)


def make_number(value: int) -> StackVal:
    return StackVal(str(value), value)


def binop(a: StackVal, b: StackVal, op: str) -> StackVal:
    if a.value is not None and b.value is not None:
        if op == "+":
            return StackVal(str(a.value + b.value), a.value + b.value)
        if op == "-":
            return StackVal(str(a.value - b.value), a.value - b.value)
        if op == "*":
            return StackVal(str(a.value * b.value), a.value * b.value)
        if op == "/" and b.value != 0:
            return StackVal(str(a.value // b.value), a.value // b.value)
    return StackVal(f"({a.expr} {op} {b.expr})", None)


def decode(data: bytes) -> tuple[list[InstructionRow], list[ColorSetCall]]:
    rows: list[InstructionRow] = []
    calls: list[ColorSetCall] = []
    stack: list[StackVal] = []
    current_call_instrs: list[int] = []
    current_call_first_rel: int | None = None
    current_call_first_addr: int | None = None
    pc = 0
    idx = 1

    while pc < len(data):
        rel = pc
        addr = BASE_ADDR + rel
        op = data[pc]
        pc += 1
        if op not in OPCODES:
            raise ValueError(f"unknown opcode 0x{op:02X} at +0x{rel:04X}")
        mnemonic, kind = OPCODES[op]
        operand = ""
        effect = ""
        lua_like = ""

        if mnemonic == "init_stack":
            args = i8(data, pc)
            locals_ = i8(data, pc + 1)
            pc += 2
            operand = f"args={args}, locals={locals_}"
            effect = "初始化栈帧"
            lua_like = f"-- init_stack args={args} locals={locals_}"
        elif mnemonic == "syscall":
            sid = u16(data, pc)
            pc += 2
            name, argc = SYSCALLS.get(sid, (f"syscall_{sid}", 0))
            operand = f"id={sid} ({name}), argc={argc}"
            if argc:
                call_args = stack[-argc:]
                del stack[-argc:]
            else:
                call_args = []
            effect = f"调用系统函数 {name}"
            lua_like = f"__syscall(\"{name}\", {', '.join(a.expr for a in call_args)})"
            if name == "ColorSet":
                calls.append(ColorSetCall(
                    index=len(calls) + 1,
                    first_rel=current_call_first_rel if current_call_first_rel is not None else rel,
                    last_rel=rel,
                    first_addr=current_call_first_addr if current_call_first_addr is not None else addr,
                    last_addr=addr,
                    args=call_args,
                    instruction_indices=current_call_instrs[:] + [idx],
                ))
                current_call_instrs.clear()
                current_call_first_rel = None
                current_call_first_addr = None
        elif mnemonic == "push_i8":
            value = i8(data, pc)
            pc += 1
            operand = str(value)
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(make_number(value))
            current_call_instrs.append(idx)
            effect = f"压入整数 {value}"
            lua_like = f"S{len(stack) - 1} = {value}"
        elif mnemonic == "push_i16":
            value = i16(data, pc)
            pc += 2
            operand = str(value)
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(make_number(value))
            current_call_instrs.append(idx)
            effect = f"压入整数 {value}"
            lua_like = f"S{len(stack) - 1} = {value}"
        elif mnemonic == "push_i32":
            value = i32(data, pc)
            pc += 4
            operand = str(value)
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(make_number(value))
            current_call_instrs.append(idx)
            effect = f"压入整数 {value}"
            lua_like = f"S{len(stack) - 1} = {value}"
        elif mnemonic == "add":
            b = stack.pop()
            a = stack.pop()
            result = binop(a, b, "+")
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(result)
            current_call_instrs.append(idx)
            effect = f"栈顶两项相加：{a.expr} + {b.expr} -> {result.expr}"
            lua_like = result.expr
        elif mnemonic == "sub":
            b = stack.pop()
            a = stack.pop()
            result = binop(a, b, "-")
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(result)
            current_call_instrs.append(idx)
            effect = f"栈顶两项相减：{a.expr} - {b.expr} -> {result.expr}"
            lua_like = result.expr
        elif mnemonic == "mul":
            b = stack.pop()
            a = stack.pop()
            result = binop(a, b, "*")
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(result)
            current_call_instrs.append(idx)
            effect = f"栈顶两项相乘：{a.expr} * {b.expr} -> {result.expr}"
            lua_like = result.expr
        elif mnemonic == "div":
            b = stack.pop()
            a = stack.pop()
            result = binop(a, b, "/")
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(result)
            current_call_instrs.append(idx)
            effect = f"栈顶两项相除：{a.expr} / {b.expr} -> {result.expr}"
            lua_like = result.expr
        elif mnemonic == "ret":
            effect = "函数返回"
            lua_like = "return"
        elif mnemonic in {"call", "jmp", "jz"}:
            target = u32(data, pc)
            pc += 4
            operand = f"0x{target:08X}"
            effect = f"{mnemonic} 到 0x{target:08X}"
            lua_like = effect
        elif mnemonic == "push_nil":
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(StackVal("nil", None))
            current_call_instrs.append(idx)
            effect = "压入 nil"
            lua_like = f"S{len(stack) - 1} = nil"
        elif mnemonic == "push_true":
            if not current_call_instrs:
                current_call_first_rel = rel
                current_call_first_addr = addr
            stack.append(StackVal("true", 1))
            current_call_instrs.append(idx)
            effect = "压入 true"
            lua_like = f"S{len(stack) - 1} = true"
        else:
            effect = "本函数未出现或未特殊展开的指令"
            lua_like = mnemonic

        raw = data[rel:pc]
        rows.append(InstructionRow(
            index=idx,
            rel=rel,
            addr=addr,
            raw=fmt_hex(raw),
            mnemonic=mnemonic,
            operand=operand,
            effect=effect,
            lua_like=lua_like,
            stack_after=stack_preview(stack),
        ))
        idx += 1

    return rows, calls


def call_final_tuple(call: ColorSetCall) -> tuple[str, str, str, str, str]:
    values = []
    for arg in call.args:
        values.append(str(arg.value) if arg.value is not None else arg.expr)
    while len(values) < 5:
        values.append("")
    return tuple(values[:5])  # type: ignore[return-value]


def build_markdown(data: bytes, rows: list[InstructionRow], calls: list[ColorSetCall]) -> str:
    lines: list[str] = []
    lines.append("# f_00002025 逐条反汇编对照")
    lines.append("")
    lines.append("## 1. 基本信息")
    lines.append("")
    lines.append(f"- 原始片段：`fvp_analysis/result/hcbtool_test/f_00002025`")
    lines.append(f"- 基址：`0x{BASE_ADDR:08X}`")
    lines.append(f"- 字节长度：`{len(data)}` bytes")
    lines.append(f"- 覆盖地址：`0x{BASE_ADDR:08X}` .. `0x{BASE_ADDR + len(data) - 1:08X}`")
    lines.append(f"- 指令数：`{len(rows)}`")
    lines.append(f"- `ColorSet` 调用数：`{len(calls)}`")
    lines.append("")
    lines.append("该片段整体是一个调色板初始化函数：从头到尾连续压入 `ColorSet(index, r, g, b, a)` 的 5 个参数并调用 syscall `7`，最后连续两个 `ret` 对应 Lua 中 block 0 / block 1 的两个 `return`。")
    lines.append("")
    lines.append("## 2. ColorSet 调用汇总")
    lines.append("")
    lines.append("| # | 地址范围 | slot | R | G | B | A | 参数表达式 |")
    lines.append("|---:|---|---:|---:|---:|---:|---:|---|")
    for call in calls:
        slot, r, g, b, a = call_final_tuple(call)
        expr = ", ".join(arg.expr for arg in call.args)
        lines.append(f"| {call.index} | `0x{call.first_addr:08X}`..`0x{call.last_addr:08X}` | {slot} | {r} | {g} | {b} | {a} | `{expr}` |")
    lines.append("")
    lines.append("## 3. 逐条指令对照")
    lines.append("")
    lines.append("| # | 地址 | 相对偏移 | 原始字节 | 指令 | 操作数 | 对应 Lua / 语义 | 执行后栈摘要 |")
    lines.append("|---:|---:|---:|---|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row.index} | `0x{row.addr:08X}` | `+0x{row.rel:04X}` | `{row.raw}` | `{row.mnemonic}` | `{row.operand}` | {row.effect}；`{row.lua_like}` | `{row.stack_after}` |"
        )
    lines.append("")
    lines.append("## 4. 关键观察")
    lines.append("")
    lines.append("- `0x01 00 00` 对应 `init_stack args=0 locals=0`。")
    lines.append("- `0x0C` / `0x0B` 分别用于压入 i8 / i16 整数；例如 `0C 01` 是 `S0 = 1`，`0B FF 00` 是 `255`。")
    lines.append("- `0x1A` 是 `add`，`0x1B` 是 `sub`；Lua 中的 `S1 = (S1 - S2)`、`S2 = (S2 + S3)` 均来自这类栈顶二元运算。")
    lines.append("- `0x03 07 00` 是 syscall 7，即 `ColorSet`，固定消耗 5 个参数。")
    lines.append("- 末尾 `0x04 0x04` 是两个连续 `ret`，对应 Lua 中 block 0 的 `return` 与 block 1 的 `return`。")
    lines.append("")
    return "\n".join(lines)


def build_tsv(rows: list[InstructionRow]) -> str:
    header = ["index", "addr", "rel", "raw", "mnemonic", "operand", "effect", "lua_like", "stack_after"]
    lines = ["\t".join(header)]
    for row in rows:
        fields = [
            str(row.index),
            f"0x{row.addr:08X}",
            f"+0x{row.rel:04X}",
            row.raw,
            row.mnemonic,
            row.operand,
            row.effect,
            row.lua_like,
            row.stack_after,
        ]
        lines.append("\t".join(field.replace("\t", " ") for field in fields))
    return "\n".join(lines)


def main() -> None:
    data = SRC.read_bytes()
    rows, calls = decode(data)
    OUT_MD.write_text(build_markdown(data, rows, calls), encoding="utf-8")
    OUT_TSV.write_text(build_tsv(rows), encoding="utf-8")
    print(f"bytes={len(data)} instructions={len(rows)} colorset_calls={len(calls)}")
    print(f"markdown={OUT_MD}")
    print(f"tsv={OUT_TSV}")


if __name__ == "__main__":
    main()
