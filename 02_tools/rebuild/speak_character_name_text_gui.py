# -*- coding: utf-8 -*-
"""SPEAK_CharacterNameText function GUI builder for fvp_analysis.

This script builds a function-block similar to Sakura's f_000019E0, i.e. the
speaker-name / body-text style dispatcher used by SPEAK blocks.

The GUI outputs two files:
- .lua : human-readable Lua-like preview
- .tmp : raw HCB bytecode fragment for a single function body

Current editor model:
- 特殊起始分支：通常放 style_id == 0 / 98 / 99 之类的前置特殊判断
- 常规离散分支：通常放 style_id == N 的逐项判断
- 区间/范围分支：通常放 style_id >= N / <= N / lo <= style_id <= hi

Each row manually edits the columns:
| style_id 条件 | f_0008CC08 参数 | TextColor(8,...) | TextOutSize(0,...) | TextColor(0,...) |

The row count of each category is controlled directly by adding/removing rows in
its table.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(__file__).resolve().parent
DEFAULT_OUT_DIR = APP_DIR / "output"

ENCODING_ALIASES = {
    "sjis": "shift_jis",
    "shiftjis": "shift_jis",
    "shift-jis": "shift_jis",
    "shift_jis": "shift_jis",
    "gbk": "gb18030",
    "gb2312": "gb18030",
    "gb18030": "gb18030",
    "utf8": "utf-8",
    "utf-8": "utf-8",
}

CONDITION_HELP = (
    "支持条件写法示例：0 / 98 / style_id == 13 / >= 40 / style_id >= 40 / "
    "<= 39 / 30 <= style_id <= 39 / 30..39 / default"
)


@dataclass
class BranchSpec:
    condition: str = ""
    palette_args: str = ""
    name_color_args: str = ""
    text_size_args: str = ""
    body_color_args: str = ""
    comment: str = ""


@dataclass
class ConditionSpec:
    kind: str
    raw: str
    v1: int | None = None
    v2: int | None = None


@dataclass
class CompiledBranch:
    section: str
    row_index: int
    spec: BranchSpec
    condition: ConditionSpec
    palette_args: list[Any] | None
    name_color_args: list[Any] | None
    text_size_args: list[Any] | None
    body_color_args: list[Any] | None


@dataclass
class CharacterNameTextConfig:
    function_name: str = "SPEAK_CharacterNameText_Custom"
    base_addr: int = 0x000019E0
    block_index: int = 1
    previous_block_sizes: list[int] = field(default_factory=list)
    auto_base_addr: bool = False
    args_count: int = 1
    locals_count: int = 1
    style_stack_index: int = -2
    palette_func_addr: int = 0x0008CC08
    text_color_syscall_id: int = 112
    text_out_size_syscall_id: int = 120
    encoding: str = "sjis"
    special_start_branches: list[BranchSpec] = field(default_factory=list)
    regular_branches: list[BranchSpec] = field(default_factory=list)
    range_branches: list[BranchSpec] = field(default_factory=list)


SAMPLE_PRESET = CharacterNameTextConfig(
    function_name="SPEAK_CharacterNameText_Sample",
    base_addr=0x000019E0,
    auto_base_addr=False,
    args_count=1,
    locals_count=1,
    style_stack_index=-2,
    palette_func_addr=0x0008CC08,
    text_color_syscall_id=112,
    text_out_size_syscall_id=120,
    special_start_branches=[
        BranchSpec("0", "", "", "0, 5, nil", "0, 10, 11, 100", "基础样式"),
        BranchSpec("98", "0, 51", "8, 10, 51, 100", "0, 5, nil", "0, 10, 51, 100", "特殊样式 98"),
        BranchSpec("99", "0, 51", "8, 10, 51, 100", "0, 5, nil", "0, 10, 51, 100", "特殊样式 99"),
    ],
    regular_branches=[
        BranchSpec("1", "1, 52", "8, 10, 52, 100", "0, 5, nil", "0, 10, 52, 100", "常规离散样式示例"),
        BranchSpec("13", "51, 90", "8, 10, 90, 100", "0, 5, nil", "0, 10, 90, 100", "特殊映射示例"),
        BranchSpec("25", "25, 76", "8, 10, 76, 100", "0, 5, nil", "0, 10, 76, 100", "离散尾项示例"),
    ],
    range_branches=[
        BranchSpec("30 <= style_id <= 39", "51, 90", "8, 10, 90, 100", "0, 5, nil", "0, 10, 90, 100", "区间映射 A"),
        BranchSpec(">= 40", "52, 91", "8, 10, 91, 100", "0, 5, nil", "0, 10, 91, 100", "区间映射 B"),
    ],
)


def normalize_encoding_name(value: str) -> str:
    key = (value or "sjis").strip().lower().replace(" ", "")
    if key in ("shiftjis", "shift-jis", "shift_jis", "sjis"):
        return "sjis"
    if key in ("gbk", "gb2312", "gb18030"):
        return "gbk"
    if key in ("utf8", "utf-8"):
        return "utf8"
    raise ValueError(f"未知写入编码：{value}，可选 sjis / gbk / utf8")



def python_codec(value: str) -> str:
    return ENCODING_ALIASES[normalize_encoding_name(value)]



def parse_int(value: str, default: int = 0) -> int:
    s = str(value).strip()
    if not s:
        return default
    return int(s, 0)



def parse_int_set(value: str) -> list[int]:
    s = str(value).strip()
    if not s:
        return []
    out: list[int] = []
    for part in s.replace("，", ",").split(","):
        part = part.strip()
        if part:
            out.append(parse_int(part))
    return out



def compute_base_addr(block_index: int, previous_block_sizes: list[int]) -> int:
    idx = max(1, int(block_index))
    return 4 + sum(int(x) for x in previous_block_sizes[:idx - 1])



def cfg_with_computed_base(cfg: CharacterNameTextConfig) -> CharacterNameTextConfig:
    if cfg.auto_base_addr:
        cfg.base_addr = compute_base_addr(cfg.block_index, cfg.previous_block_sizes)
    cfg.encoding = normalize_encoding_name(cfg.encoding)
    return cfg



def strip_optional_parens(text: str) -> str:
    s = text.strip()
    if s.startswith("(") and s.endswith(")"):
        return s[1:-1].strip()
    return s



def split_csv_args(text: str) -> list[str]:
    s = strip_optional_parens(text).replace("，", ",")
    return [part.strip() for part in s.split(",") if part.strip()]



def parse_scalar_token(token: str) -> Any:
    s = token.strip()
    lower = s.lower()
    if lower in {"nil", "none", "null", "空"}:
        return None
    if lower in {"true", "真"}:
        return True
    if lower in {"false", "假"}:
        return False
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        return s[1:-1]
    return parse_int(s)



def parse_arg_list(value: str) -> list[Any] | None:
    s = str(value).strip()
    if not s or s.lower() in {"skip", "none", "无"}:
        return None
    return [parse_scalar_token(part) for part in split_csv_args(s)]



def normalize_condition_text(text: str) -> str:
    s = str(text).strip()
    s = s.replace("，", ",").replace("（", "(").replace("）", ")")
    s = s.replace("且", " and ").replace("并且", " and ")
    s = re.sub(r"\b(?:style_id|id|a0|a1)\b", "style_id", s, flags=re.IGNORECASE)
    s = re.sub(r"\s+", " ", s).strip()
    return s



def parse_style_condition(text: str) -> ConditionSpec:
    raw = normalize_condition_text(text)
    if not raw:
        raise ValueError("style_id 条件不能为空")
    lower = raw.lower()
    if lower in {"default", "else", "always", "true", "*"}:
        return ConditionSpec("always", raw)

    patterns: list[tuple[str, str]] = [
        (r"^(-?(?:0x[0-9a-f]+|\d+))\s*<=\s*style_id\s*<=\s*(-?(?:0x[0-9a-f]+|\d+))$", "range"),
        (r"^style_id\s*>=\s*(-?(?:0x[0-9a-f]+|\d+))\s*(?:and|&&)\s*style_id\s*<=\s*(-?(?:0x[0-9a-f]+|\d+))$", "range"),
        (r"^(-?(?:0x[0-9a-f]+|\d+))\s*\.\.\s*(-?(?:0x[0-9a-f]+|\d+))$", "range"),
        (r"^style_id\s*(?:==|=)\s*(-?(?:0x[0-9a-f]+|\d+))$", "eq"),
        (r"^(-?(?:0x[0-9a-f]+|\d+))$", "eq"),
        (r"^style_id\s*>=\s*(-?(?:0x[0-9a-f]+|\d+))$", "ge"),
        (r"^>=\s*(-?(?:0x[0-9a-f]+|\d+))$", "ge"),
        (r"^style_id\s*<=\s*(-?(?:0x[0-9a-f]+|\d+))$", "le"),
        (r"^<=\s*(-?(?:0x[0-9a-f]+|\d+))$", "le"),
        (r"^style_id\s*>\s*(-?(?:0x[0-9a-f]+|\d+))$", "gt"),
        (r"^>\s*(-?(?:0x[0-9a-f]+|\d+))$", "gt"),
        (r"^style_id\s*<\s*(-?(?:0x[0-9a-f]+|\d+))$", "lt"),
        (r"^<\s*(-?(?:0x[0-9a-f]+|\d+))$", "lt"),
    ]

    for pattern, kind in patterns:
        m = re.match(pattern, lower, flags=re.IGNORECASE)
        if not m:
            continue
        if kind == "range":
            lo = parse_int(m.group(1))
            hi = parse_int(m.group(2))
            if lo > hi:
                raise ValueError(f"区间条件下界大于上界：{text}")
            return ConditionSpec(kind, raw, lo, hi)
        return ConditionSpec(kind, raw, parse_int(m.group(1)))

    raise ValueError(f"无法解析 style_id 条件：{text}\n{CONDITION_HELP}")



def condition_to_lua(cond: ConditionSpec) -> str:
    if cond.kind == "always":
        return "true"
    if cond.kind == "eq":
        return f"style_id == {cond.v1}"
    if cond.kind == "ge":
        return f"style_id >= {cond.v1}"
    if cond.kind == "le":
        return f"style_id <= {cond.v1}"
    if cond.kind == "gt":
        return f"style_id > {cond.v1}"
    if cond.kind == "lt":
        return f"style_id < {cond.v1}"
    if cond.kind == "range":
        return f"style_id >= {cond.v1} and style_id <= {cond.v2}"
    return cond.raw



def compile_branch(section: str, row_index: int, spec: BranchSpec) -> CompiledBranch:
    try:
        condition = parse_style_condition(spec.condition)
        palette_args = parse_arg_list(spec.palette_args)
        name_color_args = parse_arg_list(spec.name_color_args)
        text_size_args = parse_arg_list(spec.text_size_args)
        body_color_args = parse_arg_list(spec.body_color_args)
    except Exception as exc:
        raise ValueError(f"{section} 第 {row_index} 行解析失败：{exc}") from exc
    return CompiledBranch(
        section=section,
        row_index=row_index,
        spec=spec,
        condition=condition,
        palette_args=palette_args,
        name_color_args=name_color_args,
        text_size_args=text_size_args,
        body_color_args=body_color_args,
    )



def compile_all_branches(cfg: CharacterNameTextConfig) -> list[CompiledBranch]:
    cfg = cfg_with_computed_base(cfg)
    out: list[CompiledBranch] = []
    groups = [
        ("特殊起始分支", cfg.special_start_branches),
        ("常规离散分支", cfg.regular_branches),
        ("区间离散分支", cfg.range_branches),
    ]
    for section, items in groups:
        for i, spec in enumerate(items, start=1):
            if not any([
                spec.condition.strip(),
                spec.palette_args.strip(),
                spec.name_color_args.strip(),
                spec.text_size_args.strip(),
                spec.body_color_args.strip(),
                spec.comment.strip(),
            ]):
                continue
            out.append(compile_branch(section, i, spec))
    return out



def w_i8(v: int) -> bytes:
    return int(v).to_bytes(1, "little", signed=True)



def w_u8(v: int) -> bytes:
    return int(v & 0xFF).to_bytes(1, "little", signed=False)



def w_u16(v: int) -> bytes:
    return int(v).to_bytes(2, "little", signed=False)



def w_u32(v: int) -> bytes:
    return int(v).to_bytes(4, "little", signed=False)



def encode_cstr(text: str, encoding: str) -> bytes:
    raw = text.encode(python_codec(encoding), errors="strict") + b"\x00"
    if len(raw) > 255:
        raise ValueError(f"字符串过长：{text!r} -> {len(raw)} bytes including NUL")
    return raw


class Assembler:
    def __init__(self, base_addr: int, encoding: str = "shift_jis"):
        self.base_addr = base_addr
        self.encoding = encoding
        self.items: list[tuple[str, object]] = []

    def label(self, name: str) -> None:
        self.items.append(("label", name))

    def op(self, opcode: int, payload: bytes = b"") -> None:
        self.items.append(("bytes", bytes([opcode]) + payload))

    def jmp(self, label: str) -> None:
        self.items.append(("jmp", label))

    def jz(self, label: str) -> None:
        self.items.append(("jz", label))

    def call(self, addr: int) -> None:
        self.op(0x02, w_u32(addr))

    def syscall(self, sid: int) -> None:
        self.op(0x03, w_u16(sid))

    def push_i8(self, v: int) -> None:
        self.op(0x0C, w_i8(v))

    def push_i16(self, v: int) -> None:
        self.op(0x0B, int(v).to_bytes(2, "little", signed=True))

    def push_i32(self, v: int) -> None:
        self.op(0x0A, int(v).to_bytes(4, "little", signed=True))

    def push_int_auto(self, v: int) -> None:
        if -128 <= v <= 127:
            self.push_i8(v)
        elif -32768 <= v <= 32767:
            self.push_i16(v)
        else:
            self.push_i32(v)

    def push_nil(self) -> None:
        self.op(0x08)

    def push_true(self) -> None:
        self.op(0x09)

    def push_string(self, text: str) -> None:
        raw = encode_cstr(text, self.encoding)
        self.op(0x0E, w_u8(len(raw)) + raw)

    def push_stack(self, idx: int) -> None:
        self.op(0x10, w_i8(idx))

    def set_e(self) -> None:
        self.op(0x22)

    def set_g(self) -> None:
        self.op(0x24)

    def set_ge(self) -> None:
        self.op(0x25)

    def set_l(self) -> None:
        self.op(0x26)

    def set_le(self) -> None:
        self.op(0x27)

    def ret(self) -> None:
        self.op(0x04)

    def assemble(self) -> bytes:
        labels: dict[str, int] = {}
        pc = self.base_addr
        for typ, val in self.items:
            if typ == "label":
                labels[str(val)] = pc
            elif typ == "bytes":
                pc += len(val)  # type: ignore[arg-type]
            elif typ in {"jmp", "jz"}:
                pc += 5
            else:
                raise ValueError(typ)

        out = bytearray()
        for typ, val in self.items:
            if typ == "label":
                continue
            if typ == "bytes":
                out.extend(val)  # type: ignore[arg-type]
            elif typ == "jmp":
                out.append(0x06)
                out.extend(w_u32(labels[str(val)]))
            elif typ == "jz":
                out.append(0x07)
                out.extend(w_u32(labels[str(val)]))
        return bytes(out)



def push_value(asm: Assembler, value: Any) -> None:
    if value is None or value is False:
        asm.push_nil()
    elif value is True:
        asm.push_true()
    elif isinstance(value, str):
        asm.push_string(value)
    else:
        asm.push_int_auto(int(value))



def lua_quote(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'



def lua_atom(value: Any) -> str:
    if value is None or value is False:
        return "nil"
    if value is True:
        return "true"
    if isinstance(value, str):
        return lua_quote(value)
    return str(value)



def lua_args(values: list[Any] | None) -> str:
    if not values:
        return ""
    return ", ".join(lua_atom(v) for v in values)



def stack_alias_for(idx: int) -> str:
    return f"STACK[{idx}]"



def emit_condition_check(asm: Assembler, cfg: CharacterNameTextConfig, cond: ConditionSpec, fail_label: str) -> None:
    if cond.kind == "always":
        return

    def push_style() -> None:
        asm.push_stack(cfg.style_stack_index)

    if cond.kind == "eq":
        push_style()
        asm.push_int_auto(int(cond.v1))
        asm.set_e()
        asm.jz(fail_label)
        return
    if cond.kind == "ge":
        push_style()
        asm.push_int_auto(int(cond.v1))
        asm.set_ge()
        asm.jz(fail_label)
        return
    if cond.kind == "le":
        push_style()
        asm.push_int_auto(int(cond.v1))
        asm.set_le()
        asm.jz(fail_label)
        return
    if cond.kind == "gt":
        push_style()
        asm.push_int_auto(int(cond.v1))
        asm.set_g()
        asm.jz(fail_label)
        return
    if cond.kind == "lt":
        push_style()
        asm.push_int_auto(int(cond.v1))
        asm.set_l()
        asm.jz(fail_label)
        return
    if cond.kind == "range":
        push_style()
        asm.push_int_auto(int(cond.v1))
        asm.set_ge()
        asm.jz(fail_label)
        push_style()
        asm.push_int_auto(int(cond.v2))
        asm.set_le()
        asm.jz(fail_label)
        return
    raise ValueError(f"unsupported condition kind: {cond.kind}")



def emit_style_actions(asm: Assembler, cfg: CharacterNameTextConfig, branch: CompiledBranch) -> None:
    action_groups = [
        (branch.palette_args, ("call", cfg.palette_func_addr)),
        (branch.name_color_args, ("syscall", cfg.text_color_syscall_id)),
        (branch.text_size_args, ("syscall", cfg.text_out_size_syscall_id)),
        (branch.body_color_args, ("syscall", cfg.text_color_syscall_id)),
    ]
    for args, target in action_groups:
        if not args:
            continue
        for value in args:
            push_value(asm, value)
        kind, value = target
        if kind == "call":
            asm.call(int(value))
        else:
            asm.syscall(int(value))



def build_character_name_text_tmp(cfg: CharacterNameTextConfig) -> bytes:
    cfg = cfg_with_computed_base(cfg)
    branches = compile_all_branches(cfg)
    asm = Assembler(cfg.base_addr, cfg.encoding)
    asm.op(0x01, w_i8(cfg.args_count) + w_i8(cfg.locals_count))

    for idx, branch in enumerate(branches):
        fail_label = f"branch_next_{idx}"
        emit_condition_check(asm, cfg, branch.condition, fail_label)
        emit_style_actions(asm, cfg, branch)
        asm.jmp("function_end")
        asm.label(fail_label)

    asm.label("function_end")
    asm.ret()
    asm.ret()
    return asm.assemble()



def build_character_name_text_lua(cfg: CharacterNameTextConfig, tmp: bytes | None = None) -> str:
    cfg = cfg_with_computed_base(cfg)
    branches = compile_all_branches(cfg)
    lines: list[str] = []
    lines.append("-- Generated by SPEAK_CharacterNameText GUI builder")
    lines.append("-- This is a Lua-like template sketch, not full HCB source.")
    lines.append(f"-- speak_block_index = {cfg.block_index}")
    lines.append(f"-- previous_block_sizes = {cfg.previous_block_sizes}")
    lines.append(f"-- auto_base_addr = {cfg.auto_base_addr}")
    lines.append(f"-- function_base = 0x{cfg.base_addr:08X}")
    lines.append(f"-- init_stack args={cfg.args_count} locals={cfg.locals_count}")
    lines.append(f"-- style_stack_index = {cfg.style_stack_index}")
    lines.append(f"-- palette_func_addr = 0x{cfg.palette_func_addr:08X}")
    lines.append(f"-- text_color_syscall_id = {cfg.text_color_syscall_id}")
    lines.append(f"-- text_out_size_syscall_id = {cfg.text_out_size_syscall_id}")
    lines.append(f"-- write_encoding = {cfg.encoding}")
    lines.append(f"-- special_start_count = {len(cfg.special_start_branches)}")
    lines.append(f"-- regular_count = {len(cfg.regular_branches)}")
    lines.append(f"-- range_count = {len(cfg.range_branches)}")
    if tmp is not None:
        lines.append(f"-- tmp_size = {len(tmp)} bytes")
        lines.append(f"-- next_function_base = 0x{cfg.base_addr + len(tmp):08X}")
    lines.append("")
    lines.append(f"function {cfg.function_name}(...) ")
    lines.append(f"  local style_id = {stack_alias_for(cfg.style_stack_index)}")
    lines.append("")

    last_section = None
    for branch in branches:
        if branch.section != last_section:
            lines.append(f"  -- {branch.section}")
            last_section = branch.section
        if branch.spec.comment.strip():
            lines.append(f"  -- {branch.spec.comment.strip()}")
        cond_lua = condition_to_lua(branch.condition)
        if branch.condition.kind == "always":
            lines.append("  do")
        else:
            lines.append(f"  if {cond_lua} then")
        if branch.palette_args:
            lines.append(f"    f_{cfg.palette_func_addr:08X}({lua_args(branch.palette_args)})")
        if branch.name_color_args:
            lines.append(f"    TextColor({lua_args(branch.name_color_args)})")
        if branch.text_size_args:
            lines.append(f"    TextOutSize({lua_args(branch.text_size_args)})")
        if branch.body_color_args:
            lines.append(f"    TextColor({lua_args(branch.body_color_args)})")
        if not any([branch.palette_args, branch.name_color_args, branch.text_size_args, branch.body_color_args]):
            lines.append("    -- no-op")
        lines.append("    goto function_end")
        lines.append("  end")
        lines.append("")

    lines.append("  ::function_end::")
    lines.append("  return")
    lines.append("end")
    lines.append("")
    if tmp is not None:
        lines.append("-- raw_tmp_hex:")
        lines.append("-- " + tmp.hex(" ").upper())
    return "\n".join(lines)


class BranchTable(ttk.Frame):
    HEADERS = [
        ("condition", "style_id 条件", 18),
        ("palette", "f_0008CC08 参数", 18),
        ("name_color", "TextColor(8,...)", 20),
        ("text_size", "TextOutSize(0,...)", 18),
        ("body_color", "TextColor(0,...)", 20),
        ("comment", "备注", 18),
    ]

    def __init__(self, master, add_button_text: str = "添加分支"):
        super().__init__(master)
        self.rows: list[dict[str, tk.StringVar]] = []
        top = ttk.Frame(self)
        top.pack(fill="x", pady=4)
        self.count_var = tk.StringVar(value="当前 0 条")
        ttk.Label(top, textvariable=self.count_var).pack(side="left")
        ttk.Button(top, text=add_button_text, command=self.add_row).pack(side="left", padx=6)
        ttk.Button(top, text="清空本组", command=self.clear).pack(side="left", padx=4)

        header = ttk.Frame(self)
        header.pack(fill="x")
        for col, (_key, text, width) in enumerate(self.HEADERS):
            ttk.Label(header, text=text, width=width).grid(row=0, column=col, padx=2, pady=2)
        ttk.Label(header, text="操作", width=8).grid(row=0, column=len(self.HEADERS), padx=2, pady=2)

        self.inner = ttk.Frame(self)
        self.inner.pack(fill="both", expand=True)

    def _refresh_count(self):
        self.count_var.set(f"当前 {len(self.rows)} 条")

    def clear(self):
        for child in list(self.inner.children.values()):
            child.destroy()
        self.rows.clear()
        self._refresh_count()

    def add_row(self, spec: BranchSpec | None = None):
        spec = spec or BranchSpec()
        row_index = len(self.rows)
        frame = ttk.Frame(self.inner)
        frame.grid(row=row_index, column=0, sticky="ew")
        vars_ = {
            "condition": tk.StringVar(value=spec.condition),
            "palette": tk.StringVar(value=spec.palette_args),
            "name_color": tk.StringVar(value=spec.name_color_args),
            "text_size": tk.StringVar(value=spec.text_size_args),
            "body_color": tk.StringVar(value=spec.body_color_args),
            "comment": tk.StringVar(value=spec.comment),
        }
        for col, (key, _text, width) in enumerate(self.HEADERS):
            ttk.Entry(frame, textvariable=vars_[key], width=width + 2).grid(row=0, column=col, padx=2, pady=1)

        def remove() -> None:
            frame.destroy()
            self.rows.remove(vars_)
            self._refresh_count()

        ttk.Button(frame, text="删除", command=remove).grid(row=0, column=len(self.HEADERS), padx=2, pady=1)
        self.rows.append(vars_)
        self._refresh_count()

    def get_branches(self) -> list[BranchSpec]:
        out: list[BranchSpec] = []
        for row in self.rows:
            out.append(BranchSpec(
                condition=row["condition"].get(),
                palette_args=row["palette"].get(),
                name_color_args=row["name_color"].get(),
                text_size_args=row["text_size"].get(),
                body_color_args=row["body_color"].get(),
                comment=row["comment"].get(),
            ))
        return out

    def set_branches(self, branches: list[BranchSpec]):
        self.clear()
        for branch in branches:
            self.add_row(branch)


class CharacterNameTextBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FVP SPEAK_CharacterNameText function editor")
        self.geometry("1400x860")
        self._build_ui()
        self.apply_config(SAMPLE_PRESET)
        self.refresh_preview()

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="预设：Sakura f_000019E0 样例（可直接修改）").pack(side="left")
        ttk.Button(top, text="恢复样例", command=self.reset_to_sample).pack(side="left", padx=6)
        ttk.Button(top, text="生成预览", command=self.refresh_preview).pack(side="left", padx=4)
        ttk.Button(top, text="导出 .lua + .tmp", command=self.export_files).pack(side="left", padx=4)
        ttk.Button(top, text="保存配置 JSON", command=self.save_config_json).pack(side="left", padx=4)

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=4)
        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=3)
        main.add(right, weight=2)

        self.vars: dict[str, tk.StringVar | tk.BooleanVar] = {}

        def sv(name: str, value: Any = ""):
            self.vars[name] = tk.StringVar(value=str(value))
            return self.vars[name]

        def bv(name: str, value: bool = False):
            self.vars[name] = tk.BooleanVar(value=bool(value))
            return self.vars[name]

        base_box = ttk.LabelFrame(left, text="固定项目 / 函数参数")
        base_box.pack(fill="x", padx=4, pady=4)
        fields = [
            ("function_name", "函数名"),
            ("base_addr", "函数基址"),
            ("block_index", "块编号"),
            ("previous_block_sizes", "前序块大小(逗号)"),
            ("args_count", "参数数"),
            ("locals_count", "局部数"),
            ("style_stack_index", "style_id push_stack"),
            ("palette_func_addr", "f_0008CC08 地址"),
            ("text_color_syscall_id", "TextColor syscall ID"),
            ("text_out_size_syscall_id", "TextOutSize syscall ID"),
        ]
        for idx, (key, label) in enumerate(fields):
            ttk.Label(base_box, text=label).grid(row=idx // 2, column=(idx % 2) * 2, sticky="e", padx=3, pady=2)
            ttk.Entry(base_box, textvariable=sv(key), width=22).grid(row=idx // 2, column=(idx % 2) * 2 + 1, sticky="w", padx=3, pady=2)

        extra_row = ttk.Frame(base_box)
        extra_row.grid(row=(len(fields) + 1) // 2, column=0, columnspan=4, sticky="w", padx=3, pady=2)
        ttk.Checkbutton(extra_row, text="自动计算函数基址（块1默认=4；其后 base=4+前序块大小之和）", variable=bv("auto_base_addr", False)).pack(side="left")
        ttk.Button(extra_row, text="刷新基址", command=self.refresh_base_addr).pack(side="left", padx=8)
        ttk.Label(extra_row, text="写入编码").pack(side="left", padx=(12, 4))
        self.encoding_var = tk.StringVar(value="sjis")
        enc = ttk.Combobox(extra_row, textvariable=self.encoding_var, values=["sjis", "gbk", "utf8"], state="readonly", width=10)
        enc.pack(side="left")
        enc.bind("<<ComboboxSelected>>", lambda e: self.refresh_preview())

        help_box = ttk.LabelFrame(left, text="条件与参数填写说明")
        help_box.pack(fill="x", padx=4, pady=4)
        ttk.Label(help_box, text=CONDITION_HELP, wraplength=900, justify="left").pack(anchor="w", padx=6, pady=4)
        ttk.Label(
            help_box,
            text="参数列可填写示例：0, 51 / (8, 10, 52, 100) / 0, 5, nil；留空表示跳过该调用。",
            wraplength=900,
            justify="left",
        ).pack(anchor="w", padx=6, pady=4)

        notebook = ttk.Notebook(left)
        notebook.pack(fill="both", expand=True, padx=4, pady=4)

        special_tab = ttk.Frame(notebook)
        regular_tab = ttk.Frame(notebook)
        range_tab = ttk.Frame(notebook)
        notebook.add(special_tab, text="特殊起始分支")
        notebook.add(regular_tab, text="常规离散分支")
        notebook.add(range_tab, text="区间离散分支")

        self.special_table = BranchTable(special_tab, "添加特殊起始分支")
        self.special_table.pack(fill="both", expand=True, padx=4, pady=4)
        self.regular_table = BranchTable(regular_tab, "添加常规离散分支")
        self.regular_table.pack(fill="both", expand=True, padx=4, pady=4)
        self.range_table = BranchTable(range_tab, "添加区间离散分支")
        self.range_table.pack(fill="both", expand=True, padx=4, pady=4)

        self.preview = tk.Text(right, wrap="none", font=("Consolas", 10))
        self.preview.pack(fill="both", expand=True)

    def reset_to_sample(self):
        self.apply_config(SAMPLE_PRESET)
        self.refresh_preview()

    def apply_config(self, cfg: CharacterNameTextConfig):
        cfg = cfg_with_computed_base(cfg)

        def setv(k: str, v: Any):
            if k in self.vars:
                self.vars[k].set(str(v))  # type: ignore[attr-defined]

        for key in [
            "function_name",
            "base_addr",
            "block_index",
            "args_count",
            "locals_count",
            "style_stack_index",
            "palette_func_addr",
            "text_color_syscall_id",
            "text_out_size_syscall_id",
        ]:
            setv(key, getattr(cfg, key))
        setv("previous_block_sizes", ",".join(map(str, cfg.previous_block_sizes)))
        self.vars["auto_base_addr"].set(cfg.auto_base_addr)  # type: ignore[attr-defined]
        self.encoding_var.set(cfg.encoding)
        self.special_table.set_branches(cfg.special_start_branches)
        self.regular_table.set_branches(cfg.regular_branches)
        self.range_table.set_branches(cfg.range_branches)

    def collect_config(self) -> CharacterNameTextConfig:
        v = self.vars
        cfg = CharacterNameTextConfig(
            function_name=v["function_name"].get(),  # type: ignore[attr-defined]
            base_addr=parse_int(v["base_addr"].get()),  # type: ignore[attr-defined]
            block_index=parse_int(v["block_index"].get(), 1),  # type: ignore[attr-defined]
            previous_block_sizes=parse_int_set(v["previous_block_sizes"].get()),  # type: ignore[attr-defined]
            auto_base_addr=bool(v["auto_base_addr"].get()),  # type: ignore[attr-defined]
            args_count=parse_int(v["args_count"].get(), 1),  # type: ignore[attr-defined]
            locals_count=parse_int(v["locals_count"].get(), 0),  # type: ignore[attr-defined]
            style_stack_index=parse_int(v["style_stack_index"].get(), -2),  # type: ignore[attr-defined]
            palette_func_addr=parse_int(v["palette_func_addr"].get()),  # type: ignore[attr-defined]
            text_color_syscall_id=parse_int(v["text_color_syscall_id"].get()),  # type: ignore[attr-defined]
            text_out_size_syscall_id=parse_int(v["text_out_size_syscall_id"].get()),  # type: ignore[attr-defined]
            encoding=self.encoding_var.get(),
            special_start_branches=self.special_table.get_branches(),
            regular_branches=self.regular_table.get_branches(),
            range_branches=self.range_table.get_branches(),
        )
        return cfg_with_computed_base(cfg)

    def refresh_base_addr(self):
        try:
            cfg = self.collect_config()
            self.vars["base_addr"].set(str(cfg.base_addr))  # type: ignore[attr-defined]
            self.refresh_preview()
        except Exception as exc:
            messagebox.showerror("基址计算失败", str(exc))

    def refresh_preview(self):
        try:
            cfg = self.collect_config()
            self.vars["base_addr"].set(str(cfg.base_addr))  # type: ignore[attr-defined]
            tmp = build_character_name_text_tmp(cfg)
            lua = build_character_name_text_lua(cfg, tmp)
            self.preview.delete("1.0", "end")
            self.preview.insert("1.0", lua)
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))

    def export_files(self):
        try:
            cfg = self.collect_config()
            tmp = build_character_name_text_tmp(cfg)
            lua = build_character_name_text_lua(cfg, tmp)
            DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
            base = filedialog.asksaveasfilename(
                title="选择输出 Lua 文件名",
                initialdir=str(DEFAULT_OUT_DIR),
                initialfile=cfg.function_name + ".lua",
                defaultextension=".lua",
                filetypes=[("Lua-like", "*.lua"), ("All", "*.*")],
            )
            if not base:
                return
            lua_path = Path(base)
            tmp_path = lua_path.with_suffix(".tmp")
            lua_path.write_text(lua, encoding="utf-8")
            tmp_path.write_bytes(tmp)
            messagebox.showinfo("导出完成", f"Lua: {lua_path}\nTMP: {tmp_path}\nbytes={len(tmp)}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))

    def save_config_json(self):
        try:
            cfg = self.collect_config()
            DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
            path = filedialog.asksaveasfilename(
                title="保存配置 JSON",
                initialdir=str(DEFAULT_OUT_DIR),
                initialfile=cfg.function_name + ".json",
                defaultextension=".json",
                filetypes=[("JSON", "*.json"), ("All", "*.*")],
            )
            if not path:
                return
            data = cfg.__dict__.copy()
            data["special_start_branches"] = [b.__dict__ for b in cfg.special_start_branches]
            data["regular_branches"] = [b.__dict__ for b in cfg.regular_branches]
            data["range_branches"] = [b.__dict__ for b in cfg.range_branches]
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("保存完成", str(path))
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))



def main():
    app = CharacterNameTextBuilderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
