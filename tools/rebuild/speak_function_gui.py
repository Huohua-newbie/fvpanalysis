# -*- coding: utf-8 -*-
"""SPEAK function GUI builder for fvp_analysis.

This is the first experimental "function-block system editor" for the HCB
rebuild workflow.  It targets the Sakura-style speaker-name display function
family analysed in hcbtool_test:

- f_00000004 : クロ / ？？？
- f_00001918 : 大雅 / ぼく / ？？？
- f_00000872 : ソル / 一磨 / 遠矢 / ？？？

The GUI writes two files:
- .lua : human-readable Lua-like function block
- .tmp : raw HCB bytecode fragment for the function body

The .tmp file is *not* a full HCB file.  It is the bytecode sequence of a single
function, with internal jmp/jz addresses assembled as absolute HCB addresses
based on the configured function base address.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import struct
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

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


@dataclass
class VariantSpec:
    trigger: str = "default"  # integer text or "default"
    display_name: str = ""
    alt_name: str = ""       # empty => nil
    comment: str = ""

    def is_default(self) -> bool:
        return self.trigger.strip().lower() in {"", "default", "else", "默认"}


@dataclass
class SpeakConfig:
    function_name: str = "ShowSpeakerName_Custom"
    base_addr: int = 0x00000004
    block_index: int = 1
    previous_block_sizes: list[int] = field(default_factory=list)
    auto_base_addr: bool = True
    args_count: int = 3
    style_id: int = 1
    state_global: int = 2001
    enable_pre_state: bool = True
    pre_state_values: list[int] = field(default_factory=lambda: [0, 2, 4, 6])
    pre_state_inc: int = 1
    enable_direct_state_set: bool = False
    direct_state_value: int = 7
    mode_arg_stack_index: int = -3
    enable_post_state: bool = True
    post_state_values: list[int] = field(default_factory=lambda: [0, 1, 4, 5])
    post_state_inc: int = 2
    sync_mode: str = "style"  # style or fixed
    sync_fixed_id: int = 0
    g293_mode: str = "always_arg"  # always_arg / conditional_keep / nil
    g293_stack_index: int = -4
    g293_keep_stack_index: int = -2
    g294_stack_index: int = -2
    property_id: int = 1
    setup_style_addr: int = 0x000019E0
    set_name_addr: int = 0x0004CCDA
    sync_addr: int = 0x000977B8
    get_property_addr: int = 0x0008D409
    encoding: str = "sjis"
    variants: list[VariantSpec] = field(default_factory=list)


def compute_base_addr(block_index: int, previous_block_sizes: list[int]) -> int:
    """Compute function base from generated SPEAK block index and previous block sizes.

    SPEAK block #1 starts at HCB code area address 0x00000004.
    For block #N, base = 4 + sum(size of previous N-1 blocks).
    If more previous sizes are supplied than needed, only the first N-1 are used.
    """
    idx = max(1, int(block_index))
    return 4 + sum(int(x) for x in previous_block_sizes[:idx - 1])


def cfg_with_computed_base(cfg: SpeakConfig) -> SpeakConfig:
    if cfg.auto_base_addr:
        cfg.base_addr = compute_base_addr(cfg.block_index, cfg.previous_block_sizes)
    cfg.encoding = normalize_encoding_name(cfg.encoding)
    return cfg


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

    def neg(self) -> None:
        self.op(0x19)

    def add(self) -> None:
        self.op(0x1A)

    def set_e(self) -> None:
        self.op(0x22)

    def set_ne(self) -> None:
        self.op(0x23)

    def or_(self) -> None:
        self.op(0x21)

    def push_return(self) -> None:
        self.op(0x14)

    def ret(self) -> None:
        self.op(0x04)

    def assemble(self) -> bytes:
        # pass 1
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

        # pass 2
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


def push_compare_global_to_values(asm: Assembler, global_idx: int, values: list[int]) -> None:
    """Push truthy result of G[idx] in {values}. Leaves one bool-like value on stack."""
    first = True
    for v in values:
        asm.push_global(global_idx)
        asm.push_int_auto(v)
        asm.set_e()
        if not first:
            asm.or_()
        first = False
    if first:
        asm.push_nil()


def emit_state_increment_if(asm: Assembler, global_idx: int, values: list[int], inc: int, label_skip: str) -> None:
    push_compare_global_to_values(asm, global_idx, values)
    asm.jz(label_skip)
    asm.push_global(global_idx)
    asm.push_int_auto(inc)
    asm.add()
    asm.pop_global(global_idx)
    asm.label(label_skip)


def emit_sync_call(asm: Assembler, cfg: SpeakConfig) -> None:
    if cfg.sync_mode == "style":
        asm.push_global(227)
    else:
        asm.push_int_auto(cfg.sync_fixed_id)
    asm.push_true()
    asm.call(cfg.sync_addr)


def build_speak_tmp(cfg: SpeakConfig) -> bytes:
    cfg = cfg_with_computed_base(cfg)
    asm = Assembler(cfg.base_addr, cfg.encoding)

    asm.op(0x01, w_i8(cfg.args_count) + w_i8(0))  # init_stack args, locals=0

    asm.push_int_auto(cfg.style_id)
    asm.pop_global(227)
    asm.push_global(227)
    asm.call(cfg.setup_style_addr)

    if cfg.enable_direct_state_set:
        asm.push_int_auto(cfg.direct_state_value)
        asm.pop_global(cfg.state_global)

    if cfg.enable_pre_state and cfg.pre_state_values:
        emit_state_increment_if(asm, cfg.state_global, cfg.pre_state_values, cfg.pre_state_inc, "after_pre_state")

    # Variants: all non-default branches are emitted in order, then default branch.
    default_variant = None
    normal_variants: list[VariantSpec] = []
    for v in cfg.variants:
        if v.is_default():
            default_variant = v
        else:
            normal_variants.append(v)
    if default_variant is None:
        default_variant = VariantSpec("default", "", "", "default")

    for idx, var in enumerate(normal_variants):
        next_label = f"variant_next_{idx}"
        asm.push_stack(cfg.mode_arg_stack_index)
        trigger = parse_int(var.trigger)
        asm.push_int_auto(trigger)
        asm.set_e()
        asm.jz(next_label)
        asm.push_string(var.display_name)
        if var.alt_name:
            asm.push_string(var.alt_name)
        else:
            asm.push_nil()
        asm.call(cfg.set_name_addr)
        emit_sync_call(asm, cfg)
        asm.jmp("common_end")
        asm.label(next_label)

    # default branch
    asm.push_string(default_variant.display_name)
    if default_variant.alt_name:
        asm.push_string(default_variant.alt_name)
    else:
        asm.push_nil()
    asm.call(cfg.set_name_addr)
    emit_sync_call(asm, cfg)

    if cfg.enable_post_state and cfg.post_state_values:
        emit_state_increment_if(asm, cfg.state_global, cfg.post_state_values, cfg.post_state_inc, "common_end")
    else:
        asm.label("common_end")

    # common tail
    asm.push_int_auto(1)
    asm.pop_global(29)

    if cfg.g293_mode == "always_arg":
        asm.push_stack(cfg.g293_stack_index)
        asm.pop_global(293)
    elif cfg.g293_mode == "conditional_keep":
        # if keep_arg != 1 then G293=nil else G293=arg
        asm.push_stack(cfg.g293_keep_stack_index)
        asm.push_int_auto(1)
        asm.set_ne()
        asm.jz("g293_keep_arg")
        asm.push_nil()
        asm.pop_global(293)
        asm.jmp("g293_done")
        asm.label("g293_keep_arg")
        asm.push_stack(cfg.g293_stack_index)
        asm.pop_global(293)
        asm.label("g293_done")
    elif cfg.g293_mode == "nil":
        asm.push_nil()
        asm.pop_global(293)

    asm.push_stack(cfg.g294_stack_index)
    asm.pop_global(294)

    asm.push_int_auto(cfg.property_id)
    asm.call(cfg.get_property_addr)
    asm.push_return()
    asm.pop_global(295)
    asm.ret()
    asm.ret()

    return asm.assemble()


def lua_quote(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def stack_alias_for(idx: int) -> str:
    # Keep the source-oriented offset visible; this is an editor-facing Lua-like sketch.
    return f"STACK[{idx}]"


def build_speak_lua(cfg: SpeakConfig, tmp: bytes | None = None) -> str:
    cfg = cfg_with_computed_base(cfg)
    variants = cfg.variants[:]
    default = next((v for v in variants if v.is_default()), None)
    nondef = [v for v in variants if not v.is_default()]
    if default is None:
        default = VariantSpec("default", "", "", "default")

    lines: list[str] = []
    lines.append("-- Generated by SPEAK function GUI builder")
    lines.append("-- This is a Lua-like template sketch, not full HCB source.")
    lines.append(f"-- speak_block_index = {cfg.block_index}")
    lines.append(f"-- previous_block_sizes = {cfg.previous_block_sizes}")
    lines.append(f"-- auto_base_addr = {cfg.auto_base_addr}")
    lines.append(f"-- function_base = 0x{cfg.base_addr:08X}")
    lines.append(f"-- write_encoding = {cfg.encoding}")
    lines.append(f"-- style_id = {cfg.style_id} (manual)")
    if tmp is not None:
        lines.append(f"-- tmp_size = {len(tmp)} bytes")
        lines.append(f"-- next_function_base = 0x{cfg.base_addr + len(tmp):08X}")
    lines.append("")
    lines.append(f"function {cfg.function_name}(...) ")
    lines.append("  -- 固定部分：名字栏样式/角色显示编号（G[227] 手动设置；实际脚本可按需要实时变化）")
    lines.append(f"  G[227] = {cfg.style_id}")
    lines.append(f"  __ret = f_{cfg.setup_style_addr:08X}(G[227])  -- SPEAK_CharacterNameText")
    if cfg.enable_direct_state_set:
        lines.append(f"  G[{cfg.state_global}] = {cfg.direct_state_value}  -- 直接设置名字状态")
    if cfg.enable_pre_state and cfg.pre_state_values:
        lines.append(f"  if G[{cfg.state_global}] in {{{', '.join(map(str, cfg.pre_state_values))}}} then")
        lines.append(f"    G[{cfg.state_global}] = G[{cfg.state_global}] + {cfg.pre_state_inc}")
        lines.append("  end")
    lines.append("")
    lines.append(f"  local mode = {stack_alias_for(cfg.mode_arg_stack_index)}")
    for var in nondef:
        lines.append(f"  if mode == {parse_int(var.trigger)} then")
        lines.append(f"    SetAndPrintSpeakerName({lua_quote(var.display_name)}, {lua_quote(var.alt_name) if var.alt_name else 'nil'})")
        sync_id = "G[227]" if cfg.sync_mode == "style" else str(cfg.sync_fixed_id)
        lines.append(f"    SyncSpeakerState({sync_id}, true)")
        lines.append("    goto common_end")
        lines.append("  end")
    lines.append("")
    lines.append("  -- 默认分支")
    lines.append(f"  SetAndPrintSpeakerName({lua_quote(default.display_name)}, {lua_quote(default.alt_name) if default.alt_name else 'nil'})")
    sync_id = "G[227]" if cfg.sync_mode == "style" else str(cfg.sync_fixed_id)
    lines.append(f"  SyncSpeakerState({sync_id}, true)")
    if cfg.enable_post_state and cfg.post_state_values:
        lines.append(f"  if G[{cfg.state_global}] in {{{', '.join(map(str, cfg.post_state_values))}}} then")
        lines.append(f"    G[{cfg.state_global}] = G[{cfg.state_global}] + {cfg.post_state_inc}")
        lines.append("  end")
    lines.append("")
    lines.append("  ::common_end::")
    lines.append("  G[29] = 1")
    if cfg.g293_mode == "always_arg":
        lines.append(f"  G[293] = {stack_alias_for(cfg.g293_stack_index)}")
    elif cfg.g293_mode == "conditional_keep":
        lines.append(f"  if {stack_alias_for(cfg.g293_keep_stack_index)} == 1 then")
        lines.append(f"    G[293] = {stack_alias_for(cfg.g293_stack_index)}")
        lines.append("  else")
        lines.append("    G[293] = nil")
        lines.append("  end")
    else:
        lines.append("  G[293] = nil")
    lines.append(f"  G[294] = {stack_alias_for(cfg.g294_stack_index)}")
    lines.append(f"  G[295] = f_{cfg.get_property_addr:08X}({cfg.property_id})")
    lines.append("  return")
    lines.append("end")
    lines.append("")
    if tmp is not None:
        lines.append("-- raw_tmp_hex:")
        lines.append("-- " + tmp.hex(" ").upper())
    return "\n".join(lines)


PRESETS: dict[str, SpeakConfig] = {
    "クロ / first sample": SpeakConfig(
        function_name="ShowSpeakerName_Kuro",
        base_addr=0x00000004,
        args_count=3,
        style_id=1,
        state_global=2001,
        mode_arg_stack_index=-3,
        property_id=1,
        variants=[
            VariantSpec("-1", "　 ？？？ 　", "　？クロ　　", "unknown"),
            VariantSpec("default", "　　クロ　　", "", "normal"),
        ],
    ),
    "大雅 / second sample": SpeakConfig(
        function_name="ShowSpeakerName_TaigaLike",
        base_addr=0x00001918,
        args_count=5,
        style_id=99,
        state_global=2000,
        enable_pre_state=False,
        enable_direct_state_set=True,
        direct_state_value=7,
        mode_arg_stack_index=-5,
        enable_post_state=False,
        sync_mode="fixed",
        sync_fixed_id=0,
        g293_mode="conditional_keep",
        g293_stack_index=-6,
        g293_keep_stack_index=-2,
        g294_stack_index=-4,
        property_id=0,
        variants=[
            VariantSpec("-1", "　 ？？？ 　", "　 ？大雅 　", "unknown"),
            VariantSpec("20", "　　ぼく　　", "", "self pronoun"),
            VariantSpec("default", "　　大雅　　", "", "normal"),
        ],
    ),
    "ソル alias group / third sample": SpeakConfig(
        function_name="ShowSpeakerName_SolAliasGroup",
        base_addr=0x00000872,
        args_count=3,
        style_id=11,
        state_global=2011,
        mode_arg_stack_index=-3,
        property_id=11,
        variants=[
            VariantSpec("-1", "　 ？？？ 　", "　 ？ソル 　", "unknown"),
            VariantSpec("10", "　　一磨　　", "　 ？一磨 　", "alias Kazuma"),
            VariantSpec("100", "　　遠矢　　", "　 ？遠矢 　", "alias Toya"),
            VariantSpec("default", "　　ソル　　", "", "normal"),
        ],
    ),
}


class VariantTable(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.rows: list[dict[str, tk.StringVar]] = []
        self.inner = ttk.Frame(self)
        self.inner.pack(fill="both", expand=True)
        header = ttk.Frame(self.inner)
        header.grid(row=0, column=0, sticky="ew")
        for i, text in enumerate(["触发 pushint", "显示名", "备用/问号名(nil可空)", "备注", "操作"]):
            ttk.Label(header, text=text, width=[12, 22, 24, 16, 8][i]).grid(row=0, column=i, padx=2, pady=2)
        ttk.Button(self, text="添加变体", command=self.add_row).pack(anchor="w", pady=4)

    def clear(self):
        for child in list(self.inner.children.values()):
            if int(child.grid_info().get("row", 0)) > 0:
                child.destroy()
        self.rows.clear()

    def add_row(self, spec: VariantSpec | None = None):
        r = len(self.rows) + 1
        spec = spec or VariantSpec()
        vars_ = {
            "trigger": tk.StringVar(value=spec.trigger),
            "display": tk.StringVar(value=spec.display_name),
            "alt": tk.StringVar(value=spec.alt_name),
            "comment": tk.StringVar(value=spec.comment),
        }
        frame = ttk.Frame(self.inner)
        frame.grid(row=r, column=0, sticky="ew")
        ttk.Entry(frame, textvariable=vars_["trigger"], width=12).grid(row=0, column=0, padx=2, pady=1)
        ttk.Entry(frame, textvariable=vars_["display"], width=24).grid(row=0, column=1, padx=2, pady=1)
        ttk.Entry(frame, textvariable=vars_["alt"], width=26).grid(row=0, column=2, padx=2, pady=1)
        ttk.Entry(frame, textvariable=vars_["comment"], width=18).grid(row=0, column=3, padx=2, pady=1)
        def remove():
            frame.destroy()
            self.rows.remove(vars_)
        ttk.Button(frame, text="删除", command=remove).grid(row=0, column=4, padx=2, pady=1)
        self.rows.append(vars_)

    def get_variants(self) -> list[VariantSpec]:
        out = []
        for row in self.rows:
            out.append(VariantSpec(
                trigger=row["trigger"].get().strip() or "default",
                display_name=row["display"].get(),
                alt_name=row["alt"].get(),
                comment=row["comment"].get(),
            ))
        return out

    def set_variants(self, variants: list[VariantSpec]):
        self.clear()
        for v in variants:
            self.add_row(v)


class SpeakBuilderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FVP SPEAK function block editor")
        self.geometry("1120x760")
        self._build_ui()
        self.load_preset("クロ / first sample")

    def _build_ui(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=8, pady=6)
        ttk.Label(top, text="预设：").pack(side="left")
        self.preset_var = tk.StringVar()
        preset_combo = ttk.Combobox(top, textvariable=self.preset_var, values=list(PRESETS), width=36, state="readonly")
        preset_combo.pack(side="left", padx=4)
        preset_combo.bind("<<ComboboxSelected>>", lambda e: self.load_preset(self.preset_var.get()))
        ttk.Button(top, text="生成预览", command=self.refresh_preview).pack(side="left", padx=4)
        ttk.Button(top, text="导出 .lua + .tmp", command=self.export_files).pack(side="left", padx=4)
        ttk.Button(top, text="保存配置 JSON", command=self.save_config_json).pack(side="left", padx=4)

        main = ttk.PanedWindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=4)

        left = ttk.Frame(main)
        right = ttk.Frame(main)
        main.add(left, weight=2)
        main.add(right, weight=3)

        form = ttk.LabelFrame(left, text="固定项目 / 模板参数")
        form.pack(fill="x", padx=4, pady=4)
        self.vars: dict[str, tk.StringVar | tk.BooleanVar] = {}
        def sv(name, value=""):
            self.vars[name] = tk.StringVar(value=str(value)); return self.vars[name]
        def bv(name, value=False):
            self.vars[name] = tk.BooleanVar(value=bool(value)); return self.vars[name]

        fields = [
            ("function_name", "函数名"), ("base_addr", "函数基址"), ("block_index", "SPEAK块编号"), ("previous_block_sizes", "前序块大小(逗号)"), ("args_count", "参数数"),
            ("style_id", "G[227] 样式ID(手动)"), ("state_global", "状态变量 G[]"), ("property_id", "属性/角色ID"),
            ("mode_arg_stack_index", "模式参数 push_stack"), ("g293_stack_index", "G293参数 push_stack"),
            ("g294_stack_index", "G294参数 push_stack"), ("g293_keep_stack_index", "G293保留开关 push_stack"),
            ("setup_style_addr", "样式函数地址"), ("set_name_addr", "名字函数地址"),
            ("sync_addr", "同步函数地址"), ("get_property_addr", "属性函数地址"),
        ]
        for idx, (key, label) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=idx//2, column=(idx%2)*2, sticky="e", padx=3, pady=2)
            ttk.Entry(form, textvariable=sv(key), width=20).grid(row=idx//2, column=(idx%2)*2+1, sticky="w", padx=3, pady=2)

        auto_base_row = ttk.Frame(form)
        auto_base_row.grid(row=(len(fields)+1)//2, column=0, columnspan=4, sticky="w", padx=3, pady=2)
        ttk.Checkbutton(auto_base_row, text="自动计算函数基址（块1默认=4；其后 base=4+前序块大小之和）", variable=bv("auto_base_addr", True)).pack(side="left")
        ttk.Button(auto_base_row, text="刷新基址", command=self.refresh_base_addr).pack(side="left", padx=8)

        flags = ttk.LabelFrame(left, text="状态推进 / 同步策略")
        flags.pack(fill="x", padx=4, pady=4)
        ttk.Checkbutton(flags, text="启用前置状态 +inc", variable=bv("enable_pre_state")).grid(row=0, column=0, sticky="w")
        ttk.Entry(flags, textvariable=sv("pre_state_values"), width=18).grid(row=0, column=1)
        ttk.Entry(flags, textvariable=sv("pre_state_inc"), width=6).grid(row=0, column=2)
        ttk.Checkbutton(flags, text="直接设置状态", variable=bv("enable_direct_state_set")).grid(row=1, column=0, sticky="w")
        ttk.Entry(flags, textvariable=sv("direct_state_value"), width=18).grid(row=1, column=1)
        ttk.Checkbutton(flags, text="启用默认分支后置状态 +inc", variable=bv("enable_post_state")).grid(row=2, column=0, sticky="w")
        ttk.Entry(flags, textvariable=sv("post_state_values"), width=18).grid(row=2, column=1)
        ttk.Entry(flags, textvariable=sv("post_state_inc"), width=6).grid(row=2, column=2)

        ttk.Label(flags, text="同步ID").grid(row=3, column=0, sticky="e")
        self.sync_mode = tk.StringVar(value="style")
        ttk.Combobox(flags, textvariable=self.sync_mode, values=["style", "fixed"], state="readonly", width=10).grid(row=3, column=1, sticky="w")
        ttk.Entry(flags, textvariable=sv("sync_fixed_id"), width=8).grid(row=3, column=2)
        ttk.Label(flags, text="G293策略").grid(row=4, column=0, sticky="e")
        self.g293_mode = tk.StringVar(value="always_arg")
        ttk.Combobox(flags, textvariable=self.g293_mode, values=["always_arg", "conditional_keep", "nil"], state="readonly", width=18).grid(row=4, column=1, sticky="w")
        ttk.Label(flags, text="写入编码").grid(row=5, column=0, sticky="e")
        self.encoding_var = tk.StringVar(value="sjis")
        enc_combo = ttk.Combobox(flags, textvariable=self.encoding_var, values=["sjis", "gbk", "utf8"], state="readonly", width=18)
        enc_combo.grid(row=5, column=1, sticky="w")
        enc_combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_preview())

        variants_box = ttk.LabelFrame(left, text="可编辑内容：名字变体")
        variants_box.pack(fill="both", expand=True, padx=4, pady=4)
        self.variant_table = VariantTable(variants_box)
        self.variant_table.pack(fill="both", expand=True)

        self.preview = tk.Text(right, wrap="none", font=("Consolas", 10))
        self.preview.pack(fill="both", expand=True)

    def load_preset(self, name: str):
        cfg = PRESETS[name]
        self.preset_var.set(name)
        self.apply_config(cfg)
        self.refresh_preview()

    def apply_config(self, cfg: SpeakConfig):
        cfg = cfg_with_computed_base(cfg)
        def setv(k, v):
            if k in self.vars:
                self.vars[k].set(str(v))  # type: ignore[attr-defined]
        for k in ["function_name", "base_addr", "block_index", "args_count", "style_id", "state_global", "property_id", "mode_arg_stack_index", "g293_stack_index", "g293_keep_stack_index", "g294_stack_index", "setup_style_addr", "set_name_addr", "sync_addr", "get_property_addr", "pre_state_inc", "direct_state_value", "post_state_inc", "sync_fixed_id"]:
            setv(k, getattr(cfg, k))
        setv("previous_block_sizes", ",".join(map(str, cfg.previous_block_sizes)))
        setv("pre_state_values", ",".join(map(str, cfg.pre_state_values)))
        setv("post_state_values", ",".join(map(str, cfg.post_state_values)))
        self.vars["auto_base_addr"].set(cfg.auto_base_addr)  # type: ignore[attr-defined]
        self.vars["enable_pre_state"].set(cfg.enable_pre_state)  # type: ignore[attr-defined]
        self.vars["enable_direct_state_set"].set(cfg.enable_direct_state_set)  # type: ignore[attr-defined]
        self.vars["enable_post_state"].set(cfg.enable_post_state)  # type: ignore[attr-defined]
        self.sync_mode.set(cfg.sync_mode)
        self.g293_mode.set(cfg.g293_mode)
        self.encoding_var.set(cfg.encoding)
        self.variant_table.set_variants(cfg.variants)

    def collect_config(self) -> SpeakConfig:
        v = self.vars
        cfg = SpeakConfig(
            function_name=v["function_name"].get(),  # type: ignore[attr-defined]
            base_addr=parse_int(v["base_addr"].get()),  # type: ignore[attr-defined]
            block_index=parse_int(v["block_index"].get(), 1),  # type: ignore[attr-defined]
            previous_block_sizes=parse_int_set(v["previous_block_sizes"].get()),  # type: ignore[attr-defined]
            auto_base_addr=bool(v["auto_base_addr"].get()),  # type: ignore[attr-defined]
            args_count=parse_int(v["args_count"].get()),  # type: ignore[attr-defined]
            style_id=parse_int(v["style_id"].get()),  # type: ignore[attr-defined]
            state_global=parse_int(v["state_global"].get()),  # type: ignore[attr-defined]
            enable_pre_state=bool(v["enable_pre_state"].get()),  # type: ignore[attr-defined]
            pre_state_values=parse_int_set(v["pre_state_values"].get()),  # type: ignore[attr-defined]
            pre_state_inc=parse_int(v["pre_state_inc"].get()),  # type: ignore[attr-defined]
            enable_direct_state_set=bool(v["enable_direct_state_set"].get()),  # type: ignore[attr-defined]
            direct_state_value=parse_int(v["direct_state_value"].get()),  # type: ignore[attr-defined]
            mode_arg_stack_index=parse_int(v["mode_arg_stack_index"].get()),  # type: ignore[attr-defined]
            enable_post_state=bool(v["enable_post_state"].get()),  # type: ignore[attr-defined]
            post_state_values=parse_int_set(v["post_state_values"].get()),  # type: ignore[attr-defined]
            post_state_inc=parse_int(v["post_state_inc"].get()),  # type: ignore[attr-defined]
            sync_mode=self.sync_mode.get(),
            sync_fixed_id=parse_int(v["sync_fixed_id"].get()),  # type: ignore[attr-defined]
            g293_mode=self.g293_mode.get(),
            g293_stack_index=parse_int(v["g293_stack_index"].get()),  # type: ignore[attr-defined]
            g293_keep_stack_index=parse_int(v["g293_keep_stack_index"].get()),  # type: ignore[attr-defined]
            g294_stack_index=parse_int(v["g294_stack_index"].get()),  # type: ignore[attr-defined]
            property_id=parse_int(v["property_id"].get()),  # type: ignore[attr-defined]
            setup_style_addr=parse_int(v["setup_style_addr"].get()),  # type: ignore[attr-defined]
            set_name_addr=parse_int(v["set_name_addr"].get()),  # type: ignore[attr-defined]
            sync_addr=parse_int(v["sync_addr"].get()),  # type: ignore[attr-defined]
            get_property_addr=parse_int(v["get_property_addr"].get()),  # type: ignore[attr-defined]
            encoding=self.encoding_var.get(),
            variants=self.variant_table.get_variants(),
        )
        return cfg_with_computed_base(cfg)

    def refresh_base_addr(self):
        try:
            cfg = self.collect_config()
            self.vars["base_addr"].set(str(cfg.base_addr))  # type: ignore[attr-defined]
            self.refresh_preview()
        except Exception as e:
            messagebox.showerror("基址计算失败", str(e))

    def refresh_preview(self):
        try:
            cfg = self.collect_config()
            self.vars["base_addr"].set(str(cfg.base_addr))  # type: ignore[attr-defined]
            tmp = build_speak_tmp(cfg)
            lua = build_speak_lua(cfg, tmp)
            self.preview.delete("1.0", "end")
            self.preview.insert("1.0", lua)
        except Exception as e:
            messagebox.showerror("生成失败", str(e))

    def export_files(self):
        try:
            cfg = self.collect_config()
            tmp = build_speak_tmp(cfg)
            lua = build_speak_lua(cfg, tmp)
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
        except Exception as e:
            messagebox.showerror("导出失败", str(e))

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
            data["variants"] = [v.__dict__ for v in cfg.variants]
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            messagebox.showinfo("保存完成", str(path))
        except Exception as e:
            messagebox.showerror("保存失败", str(e))


def main():
    app = SpeakBuilderApp()
    app.mainloop()


if __name__ == "__main__":
    main()
