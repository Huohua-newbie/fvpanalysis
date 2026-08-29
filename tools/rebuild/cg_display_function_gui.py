# -*- coding: utf-8 -*-
"""CG display wrapper function GUI builder for fvp_analysis.

本脚本面向已总结出的 FVP 引擎“CG 引入 / CG 显示包装函数”家族，
例如：

- f_00002403 -> KURO_e011a1
- f_0000243B -> KURO_e011b1
- 以及同模板的大量 HARU / CHIWA / HIORI / ETC / SD / ... 资源入口

当前抽象出的稳定骨架为：

    init_stack args, locals
    push_true
    pop_global <flag_global>
    call <init_addr>
    <push show arg #1..#10>
    call <show_addr>
    <push finalize arg #1..#3>
    call <finalize_addr>
    ret

默认预设直接对应当前最典型的模板：

    G[flag_global] = true
    f_00010271()
    f_00051420(resource_name, STACK[-7], 1, nil, STACK[-6], STACK[-5], STACK[-4], STACK[-3], nil, nil)
    f_00010298(nil, nil, STACK[-2])
    return

GUI 输出两个文件：
- .lua : 供用户阅读的 Lua-like 草稿
- .tmp : 单个 function 的原始 HCB 字节片段

注意：.tmp 不是完整 .hcb，只是单个函数体的字节序列。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import json
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

ARG_KIND_VALUES = ["nil", "true", "int", "string", "stack", "global"]

SHOW_ARG_ROWS = [
    ("show_arg1", "显示参数1", "通常是资源名字符串，如 KURO_e011b1"),
    ("show_arg2", "显示参数2", "通常是第1输入槽，如 STACK[-7]"),
    ("show_arg3", "显示参数3", "通常是固定常量 1"),
    ("show_arg4", "显示参数4", "通常为 nil"),
    ("show_arg5", "显示参数5", "通常是第2输入槽，如 STACK[-6]"),
    ("show_arg6", "显示参数6", "通常是第3输入槽，如 STACK[-5]"),
    ("show_arg7", "显示参数7", "通常是第4输入槽，如 STACK[-4]"),
    ("show_arg8", "显示参数8", "通常是第5输入槽，如 STACK[-3]"),
    ("show_arg9", "显示参数9", "通常为 nil"),
    ("show_arg10", "显示参数10", "通常为 nil"),
]

FINALIZE_ARG_ROWS = [
    ("finalize_arg1", "后处理参数1", "通常为 nil"),
    ("finalize_arg2", "后处理参数2", "通常为 nil"),
    ("finalize_arg3", "后处理参数3", "通常是第6输入槽，如 STACK[-2]"),
]


@dataclass
class ArgSpec:
    kind: str = "nil"
    value: str = ""


@dataclass
class CGWrapperConfig:
    function_name: str = "ShowCGWrapper_Custom"
    base_addr: int = 0x0000243B
    block_index: int = 1
    previous_block_sizes: list[int] = field(default_factory=list)
    auto_base_addr: bool = False
    args_count: int = 6
    locals_count: int = 0
    flag_global: int = 2125
    init_addr: int = 0x00010271
    show_addr: int = 0x00051420
    finalize_addr: int = 0x00010298
    encoding: str = "sjis"
    show_args: list[ArgSpec] = field(default_factory=list)
    finalize_args: list[ArgSpec] = field(default_factory=list)


DEFAULT_SHOW_ARGS = [
    ArgSpec("string", "KURO_e011b1"),
    ArgSpec("stack", "-7"),
    ArgSpec("int", "1"),
    ArgSpec("nil", ""),
    ArgSpec("stack", "-6"),
    ArgSpec("stack", "-5"),
    ArgSpec("stack", "-4"),
    ArgSpec("stack", "-3"),
    ArgSpec("nil", ""),
    ArgSpec("nil", ""),
]

DEFAULT_FINALIZE_ARGS = [
    ArgSpec("nil", ""),
    ArgSpec("nil", ""),
    ArgSpec("stack", "-2"),
]


def clone_specs(items: list[ArgSpec]) -> list[ArgSpec]:
    return [ArgSpec(kind=x.kind, value=x.value) for x in items]


def make_family_preset(function_name: str, base_addr: int, flag_global: int, resource_name: str) -> CGWrapperConfig:
    show_args = clone_specs(DEFAULT_SHOW_ARGS)
    show_args[0].value = resource_name
    return CGWrapperConfig(
        function_name=function_name,
        base_addr=base_addr,
        block_index=1,
        previous_block_sizes=[],
        auto_base_addr=False,
        args_count=6,
        locals_count=0,
        flag_global=flag_global,
        init_addr=0x00010271,
        show_addr=0x00051420,
        finalize_addr=0x00010298,
        encoding="sjis",
        show_args=show_args,
        finalize_args=clone_specs(DEFAULT_FINALIZE_ARGS),
    )


PRESETS: dict[str, CGWrapperConfig] = {
    "CG wrapper / blank template": CGWrapperConfig(
        function_name="ShowCGWrapper_Custom",
        base_addr=0x0000243B,
        block_index=1,
        previous_block_sizes=[],
        auto_base_addr=False,
        args_count=6,
        locals_count=0,
        flag_global=2125,
        init_addr=0x00010271,
        show_addr=0x00051420,
        finalize_addr=0x00010298,
        encoding="sjis",
        show_args=clone_specs(DEFAULT_SHOW_ARGS),
        finalize_args=clone_specs(DEFAULT_FINALIZE_ARGS),
    ),
    "KURO_e011a1 / f_00002403": make_family_preset("ShowCG_KURO_e011a1", 0x00002403, 2124, "KURO_e011a1"),
    "KURO_e011b1 / f_0000243B": make_family_preset("ShowCG_KURO_e011b1", 0x0000243B, 2125, "KURO_e011b1"),
}


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


def parse_required_int(value: str, label: str) -> int:
    s = str(value).strip()
    if not s:
        raise ValueError(f"{label} 需要填写整数值")
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


def encode_cstr(text: str, encoding: str) -> bytes:
    raw = text.encode(python_codec(encoding), errors="strict") + b"\x00"
    if len(raw) > 255:
        raise ValueError(f"字符串过长：{text!r} -> {len(raw)} bytes including NUL")
    return raw


def w_i8(v: int) -> bytes:
    return int(v).to_bytes(1, "little", signed=True)


def w_u8(v: int) -> bytes:
    return int(v & 0xFF).to_bytes(1, "little", signed=False)


def w_u16(v: int) -> bytes:
    return int(v).to_bytes(2, "little", signed=False)


def w_u32(v: int) -> bytes:
    return int(v).to_bytes(4, "little", signed=False)


def compute_base_addr(block_index: int, previous_block_sizes: list[int]) -> int:
    idx = max(1, int(block_index))
    return 4 + sum(int(x) for x in previous_block_sizes[: idx - 1])


def ensure_spec_count(items: list[ArgSpec], defaults: list[ArgSpec]) -> list[ArgSpec]:
    out = clone_specs(items)
    if len(out) < len(defaults):
        out.extend(clone_specs(defaults[len(out) :]))
    return out[: len(defaults)]


def cfg_with_computed_base(cfg: CGWrapperConfig) -> CGWrapperConfig:
    if cfg.auto_base_addr:
        cfg.base_addr = compute_base_addr(cfg.block_index, cfg.previous_block_sizes)
    cfg.encoding = normalize_encoding_name(cfg.encoding)
    cfg.show_args = ensure_spec_count(cfg.show_args, DEFAULT_SHOW_ARGS)
    cfg.finalize_args = ensure_spec_count(cfg.finalize_args, DEFAULT_FINALIZE_ARGS)
    return cfg


def normalize_arg_kind(kind: str) -> str:
    key = (kind or "nil").strip().lower()
    if key not in ARG_KIND_VALUES:
        raise ValueError(f"不支持的参数来源类型：{kind}；可选 {', '.join(ARG_KIND_VALUES)}")
    return key


class Assembler:
    def __init__(self, base_addr: int, encoding: str = "sjis"):
        self.base_addr = base_addr
        self.encoding = encoding
        self.chunks: list[bytes] = []

    def op(self, opcode: int, payload: bytes = b"") -> None:
        self.chunks.append(bytes([opcode]) + payload)

    def call(self, addr: int) -> None:
        self.op(0x02, w_u32(addr))

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

    def push_global(self, idx: int) -> None:
        self.op(0x0F, w_u16(idx))

    def push_stack(self, idx: int) -> None:
        self.op(0x10, w_i8(idx))

    def pop_global(self, idx: int) -> None:
        self.op(0x15, w_u16(idx))

    def ret(self) -> None:
        self.op(0x04)

    def assemble(self) -> bytes:
        return b"".join(self.chunks)


def push_arg_spec(asm: Assembler, spec: ArgSpec, label: str) -> None:
    kind = normalize_arg_kind(spec.kind)
    value = spec.value
    if kind == "nil":
        asm.push_nil()
        return
    if kind == "true":
        asm.push_true()
        return
    if kind == "int":
        asm.push_int_auto(parse_required_int(value, label))
        return
    if kind == "string":
        asm.push_string(value)
        return
    if kind == "stack":
        asm.push_stack(parse_required_int(value, label))
        return
    if kind == "global":
        asm.push_global(parse_required_int(value, label))
        return
    raise ValueError(f"{label} 不支持的参数来源：{kind}")


def lua_quote(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def lua_arg_spec(spec: ArgSpec, label: str) -> str:
    kind = normalize_arg_kind(spec.kind)
    value = spec.value
    if kind == "nil":
        return "nil"
    if kind == "true":
        return "true"
    if kind == "int":
        return str(parse_required_int(value, label))
    if kind == "string":
        return lua_quote(value)
    if kind == "stack":
        return f"STACK[{parse_required_int(value, label)}]"
    if kind == "global":
        return f"G[{parse_required_int(value, label)}]"
    raise ValueError(f"{label} 不支持的参数来源：{kind}")


def build_cg_wrapper_tmp(cfg: CGWrapperConfig) -> bytes:
    cfg = cfg_with_computed_base(cfg)
    asm = Assembler(cfg.base_addr, cfg.encoding)

    asm.op(0x01, w_i8(cfg.args_count) + w_i8(cfg.locals_count))
    asm.push_true()
    asm.pop_global(cfg.flag_global)
    asm.call(cfg.init_addr)

    for idx, spec in enumerate(cfg.show_args, start=1):
        push_arg_spec(asm, spec, f"显示参数{idx}")
    asm.call(cfg.show_addr)

    for idx, spec in enumerate(cfg.finalize_args, start=1):
        push_arg_spec(asm, spec, f"后处理参数{idx}")
    asm.call(cfg.finalize_addr)

    asm.ret()
    return asm.assemble()


def build_cg_wrapper_lua(cfg: CGWrapperConfig, tmp: bytes | None = None) -> str:
    cfg = cfg_with_computed_base(cfg)
    show_args = [lua_arg_spec(spec, f"显示参数{idx}") for idx, spec in enumerate(cfg.show_args, start=1)]
    finalize_args = [lua_arg_spec(spec, f"后处理参数{idx}") for idx, spec in enumerate(cfg.finalize_args, start=1)]

    lines: list[str] = []
    lines.append("-- Generated by CG display wrapper GUI builder")
    lines.append("-- This is a Lua-like template sketch, not full HCB source.")
    lines.append("-- function family skeleton:")
    lines.append("--   G[flag_global] = true")
    lines.append("--   f_init()")
    lines.append("--   f_show(arg1..arg10)")
    lines.append("--   f_finalize(arg1..arg3)")
    lines.append(f"-- block_index = {cfg.block_index}")
    lines.append(f"-- previous_block_sizes = {cfg.previous_block_sizes}")
    lines.append(f"-- auto_base_addr = {cfg.auto_base_addr}")
    lines.append(f"-- function_base = 0x{cfg.base_addr:08X}")
    lines.append(f"-- init_stack args={cfg.args_count} locals={cfg.locals_count}")
    lines.append(f"-- flag_global = G[{cfg.flag_global}]")
    lines.append(f"-- init_addr = 0x{cfg.init_addr:08X}")
    lines.append(f"-- show_addr = 0x{cfg.show_addr:08X}")
    lines.append(f"-- finalize_addr = 0x{cfg.finalize_addr:08X}")
    lines.append(f"-- write_encoding = {cfg.encoding}")
    if tmp is not None:
        lines.append(f"-- tmp_size = {len(tmp)} bytes")
        lines.append(f"-- next_function_base = 0x{cfg.base_addr + len(tmp):08X}")
    lines.append("")
    lines.append(f"function {cfg.function_name}(...) ")
    lines.append(f"  G[{cfg.flag_global}] = true")
    lines.append(f"  __ret = f_{cfg.init_addr:08X}()")
    lines.append(f"  __ret = f_{cfg.show_addr:08X}({', '.join(show_args)})")
    lines.append(f"  __ret = f_{cfg.finalize_addr:08X}({', '.join(finalize_args)})")
    lines.append("  return")
    lines.append("end")
    lines.append("")
    lines.append("-- arg_source_notes:")
    for idx, (_key, title, desc) in enumerate(SHOW_ARG_ROWS, start=1):
        lines.append(f"--   show_arg{idx}: {title} / {desc}")
    for idx, (_key, title, desc) in enumerate(FINALIZE_ARG_ROWS, start=1):
        lines.append(f"--   finalize_arg{idx}: {title} / {desc}")
    if tmp is not None:
        lines.append("")
        lines.append("-- raw_tmp_hex:")
        lines.append("-- " + tmp.hex(" ").upper())
    return "\n".join(lines)


def config_to_dict(cfg: CGWrapperConfig) -> dict[str, Any]:
    cfg = cfg_with_computed_base(cfg)
    return {
        "function_name": cfg.function_name,
        "base_addr": cfg.base_addr,
        "block_index": cfg.block_index,
        "previous_block_sizes": list(cfg.previous_block_sizes),
        "auto_base_addr": cfg.auto_base_addr,
        "args_count": cfg.args_count,
        "locals_count": cfg.locals_count,
        "flag_global": cfg.flag_global,
        "init_addr": cfg.init_addr,
        "show_addr": cfg.show_addr,
        "finalize_addr": cfg.finalize_addr,
        "encoding": cfg.encoding,
        "show_args": [{"kind": x.kind, "value": x.value} for x in cfg.show_args],
        "finalize_args": [{"kind": x.kind, "value": x.value} for x in cfg.finalize_args],
    }


def config_from_dict(data: dict[str, Any]) -> CGWrapperConfig:
    cfg = CGWrapperConfig(
        function_name=str(data.get("function_name", "ShowCGWrapper_Custom")),
        base_addr=int(data.get("base_addr", 0x0000243B)),
        block_index=int(data.get("block_index", 1)),
        previous_block_sizes=[int(x) for x in data.get("previous_block_sizes", [])],
        auto_base_addr=bool(data.get("auto_base_addr", False)),
        args_count=int(data.get("args_count", 6)),
        locals_count=int(data.get("locals_count", 0)),
        flag_global=int(data.get("flag_global", 2125)),
        init_addr=int(data.get("init_addr", 0x00010271)),
        show_addr=int(data.get("show_addr", 0x00051420)),
        finalize_addr=int(data.get("finalize_addr", 0x00010298)),
        encoding=str(data.get("encoding", "sjis")),
        show_args=[ArgSpec(kind=str(x.get("kind", "nil")), value=str(x.get("value", ""))) for x in data.get("show_args", [])],
        finalize_args=[ArgSpec(kind=str(x.get("kind", "nil")), value=str(x.get("value", ""))) for x in data.get("finalize_args", [])],
    )
    return cfg_with_computed_base(cfg)


class FixedArgTable(ttk.Frame):
    def __init__(self, master, rows: list[tuple[str, str, str]]):
        super().__init__(master)
        self.row_defs = rows
        self.rows: list[dict[str, tk.StringVar]] = []

        header = ttk.Frame(self)
        header.pack(fill="x", pady=(0, 4))
        ttk.Label(header, text="参数槽", width=12).grid(row=0, column=0, padx=2, pady=2)
        ttk.Label(header, text="含义", width=20).grid(row=0, column=1, padx=2, pady=2)
        ttk.Label(header, text="来源类型", width=12).grid(row=0, column=2, padx=2, pady=2)
        ttk.Label(header, text="值", width=28).grid(row=0, column=3, padx=2, pady=2)
        ttk.Label(header, text="说明", width=36).grid(row=0, column=4, padx=2, pady=2)

        inner = ttk.Frame(self)
        inner.pack(fill="x")
        for idx, (_key, title, desc) in enumerate(rows):
            kind_var = tk.StringVar(value="nil")
            value_var = tk.StringVar(value="")
            ttk.Label(inner, text=f"#{idx + 1}", width=12).grid(row=idx, column=0, padx=2, pady=2, sticky="w")
            ttk.Label(inner, text=title, width=20).grid(row=idx, column=1, padx=2, pady=2, sticky="w")
            combo = ttk.Combobox(inner, textvariable=kind_var, values=ARG_KIND_VALUES, state="readonly", width=10)
            combo.grid(row=idx, column=2, padx=2, pady=2, sticky="w")
            ttk.Entry(inner, textvariable=value_var, width=30).grid(row=idx, column=3, padx=2, pady=2, sticky="w")
            ttk.Label(inner, text=desc, width=36).grid(row=idx, column=4, padx=2, pady=2, sticky="w")
            self.rows.append({"kind": kind_var, "value": value_var})

    def get_specs(self) -> list[ArgSpec]:
        return [ArgSpec(kind=row["kind"].get(), value=row["value"].get()) for row in self.rows]

    def set_specs(self, specs: list[ArgSpec], defaults: list[ArgSpec]) -> None:
        items = ensure_spec_count(specs, defaults)
        for row, spec in zip(self.rows, items):
            row["kind"].set(spec.kind)
            row["value"].set(spec.value)


class CGWrapperBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FVP CG display wrapper function editor")
        self.geometry("1440x900")
        self._build_ui()
        self.load_preset("KURO_e011b1 / f_0000243B")

    def _build_ui(self) -> None:
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="预设：").pack(side="left")
        self.preset_var = tk.StringVar()
        preset_combo = ttk.Combobox(top, textvariable=self.preset_var, values=list(PRESETS), width=34, state="readonly")
        preset_combo.pack(side="left", padx=4)
        preset_combo.bind("<<ComboboxSelected>>", lambda e: self.load_preset(self.preset_var.get()))
        ttk.Button(top, text="生成预览", command=self.refresh_preview).pack(side="left", padx=4)
        ttk.Button(top, text="导出 .lua + .tmp", command=self.export_files).pack(side="left", padx=4)
        ttk.Button(top, text="保存配置 JSON", command=self.save_config_json).pack(side="left", padx=4)
        ttk.Button(top, text="载入配置 JSON", command=self.load_config_json).pack(side="left", padx=4)

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

        base_box = ttk.LabelFrame(left, text="固定骨架参数")
        base_box.pack(fill="x", padx=4, pady=4)

        fields = [
            ("function_name", "函数名"),
            ("base_addr", "函数基址"),
            ("block_index", "块编号"),
            ("previous_block_sizes", "前序块大小(逗号)"),
            ("args_count", "参数数"),
            ("locals_count", "局部数"),
            ("flag_global", "标记位 G[]"),
            ("init_addr", "初始化函数地址"),
            ("show_addr", "显示核心函数地址"),
            ("finalize_addr", "后处理函数地址"),
        ]
        for idx, (key, label) in enumerate(fields):
            ttk.Label(base_box, text=label).grid(row=idx // 2, column=(idx % 2) * 2, sticky="e", padx=3, pady=2)
            ttk.Entry(base_box, textvariable=sv(key), width=24).grid(row=idx // 2, column=(idx % 2) * 2 + 1, sticky="w", padx=3, pady=2)

        extra_row = ttk.Frame(base_box)
        extra_row.grid(row=(len(fields) + 1) // 2, column=0, columnspan=4, sticky="w", padx=3, pady=2)
        ttk.Checkbutton(extra_row, text="自动计算函数基址（块1默认=4；其后 base=4+前序块大小之和）", variable=bv("auto_base_addr", False)).pack(side="left")
        ttk.Button(extra_row, text="刷新基址", command=self.refresh_base_addr).pack(side="left", padx=8)
        ttk.Label(extra_row, text="写入编码").pack(side="left", padx=(12, 4))
        self.encoding_var = tk.StringVar(value="sjis")
        enc_combo = ttk.Combobox(extra_row, textvariable=self.encoding_var, values=["sjis", "gbk", "utf8"], state="readonly", width=10)
        enc_combo.pack(side="left")
        enc_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_preview())

        help_box = ttk.LabelFrame(left, text="模板说明")
        help_box.pack(fill="x", padx=4, pady=4)
        help_text = (
            "固定骨架：G[flag] = true -> f_init() -> f_show(10参) -> f_finalize(3参) -> return\n"
            "参数来源类型支持：nil / true / int / string / stack / global\n"
            "典型模板：show_arg1=string(resource_name), show_arg2=stack(-7), show_arg3=int(1), "
            "show_arg4=nil, show_arg5..8=stack(-6..-3), show_arg9..10=nil, finalize_arg3=stack(-2)。"
        )
        ttk.Label(help_box, text=help_text, wraplength=920, justify="left").pack(anchor="w", padx=6, pady=6)

        show_box = ttk.LabelFrame(left, text="显示核心函数参数（10 个）")
        show_box.pack(fill="x", padx=4, pady=4)
        self.show_arg_table = FixedArgTable(show_box, SHOW_ARG_ROWS)
        self.show_arg_table.pack(fill="x", padx=4, pady=4)

        finalize_box = ttk.LabelFrame(left, text="后处理函数参数（3 个）")
        finalize_box.pack(fill="x", padx=4, pady=4)
        self.finalize_arg_table = FixedArgTable(finalize_box, FINALIZE_ARG_ROWS)
        self.finalize_arg_table.pack(fill="x", padx=4, pady=4)

        self.preview = tk.Text(right, wrap="none", font=("Consolas", 10))
        self.preview.pack(fill="both", expand=True)

    def load_preset(self, name: str) -> None:
        cfg = PRESETS[name]
        self.preset_var.set(name)
        self.apply_config(cfg)
        self.refresh_preview()

    def apply_config(self, cfg: CGWrapperConfig) -> None:
        cfg = cfg_with_computed_base(cfg)

        def setv(key: str, value: Any) -> None:
            if key in self.vars:
                self.vars[key].set(str(value))  # type: ignore[attr-defined]

        for key in [
            "function_name",
            "base_addr",
            "block_index",
            "args_count",
            "locals_count",
            "flag_global",
            "init_addr",
            "show_addr",
            "finalize_addr",
        ]:
            setv(key, getattr(cfg, key))
        setv("previous_block_sizes", ",".join(map(str, cfg.previous_block_sizes)))
        self.vars["auto_base_addr"].set(cfg.auto_base_addr)  # type: ignore[attr-defined]
        self.encoding_var.set(cfg.encoding)
        self.show_arg_table.set_specs(cfg.show_args, DEFAULT_SHOW_ARGS)
        self.finalize_arg_table.set_specs(cfg.finalize_args, DEFAULT_FINALIZE_ARGS)

    def collect_config(self) -> CGWrapperConfig:
        v = self.vars
        cfg = CGWrapperConfig(
            function_name=v["function_name"].get(),  # type: ignore[attr-defined]
            base_addr=parse_int(v["base_addr"].get()),  # type: ignore[attr-defined]
            block_index=parse_int(v["block_index"].get(), 1),  # type: ignore[attr-defined]
            previous_block_sizes=parse_int_set(v["previous_block_sizes"].get()),  # type: ignore[attr-defined]
            auto_base_addr=bool(v["auto_base_addr"].get()),  # type: ignore[attr-defined]
            args_count=parse_int(v["args_count"].get(), 6),  # type: ignore[attr-defined]
            locals_count=parse_int(v["locals_count"].get(), 0),  # type: ignore[attr-defined]
            flag_global=parse_int(v["flag_global"].get()),  # type: ignore[attr-defined]
            init_addr=parse_int(v["init_addr"].get()),  # type: ignore[attr-defined]
            show_addr=parse_int(v["show_addr"].get()),  # type: ignore[attr-defined]
            finalize_addr=parse_int(v["finalize_addr"].get()),  # type: ignore[attr-defined]
            encoding=self.encoding_var.get(),
            show_args=self.show_arg_table.get_specs(),
            finalize_args=self.finalize_arg_table.get_specs(),
        )
        return cfg_with_computed_base(cfg)

    def refresh_base_addr(self) -> None:
        try:
            cfg = self.collect_config()
            self.vars["base_addr"].set(str(cfg.base_addr))  # type: ignore[attr-defined]
            self.refresh_preview()
        except Exception as exc:
            messagebox.showerror("基址计算失败", str(exc))

    def refresh_preview(self) -> None:
        try:
            cfg = self.collect_config()
            self.vars["base_addr"].set(str(cfg.base_addr))  # type: ignore[attr-defined]
            tmp = build_cg_wrapper_tmp(cfg)
            lua = build_cg_wrapper_lua(cfg, tmp)
            self.preview.delete("1.0", "end")
            self.preview.insert("1.0", lua)
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))

    def export_files(self) -> None:
        try:
            cfg = self.collect_config()
            tmp = build_cg_wrapper_tmp(cfg)
            lua = build_cg_wrapper_lua(cfg, tmp)
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

    def save_config_json(self) -> None:
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
            Path(path).write_text(json.dumps(config_to_dict(cfg), ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("保存完成", str(path))
        except Exception as exc:
            messagebox.showerror("保存失败", str(exc))

    def load_config_json(self) -> None:
        try:
            DEFAULT_OUT_DIR.mkdir(parents=True, exist_ok=True)
            path = filedialog.askopenfilename(
                title="载入配置 JSON",
                initialdir=str(DEFAULT_OUT_DIR),
                filetypes=[("JSON", "*.json"), ("All", "*.*")],
            )
            if not path:
                return
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            cfg = config_from_dict(data)
            self.apply_config(cfg)
            self.refresh_preview()
            self.preset_var.set("")
        except Exception as exc:
            messagebox.showerror("载入失败", str(exc))


def main() -> None:
    app = CGWrapperBuilderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
