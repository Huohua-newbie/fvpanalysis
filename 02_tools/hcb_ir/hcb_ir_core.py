# -*- coding: utf-8 -*-
"""Core library for reversible HCB <-> CFG/IR conversion.

This module is intentionally self-contained and follows the project-local
specification in fvp_analysis/result/fvp_analysis项目规范文档.md.

Design goal:
- HCB -> decoded flat instruction stream
- instruction stream -> functions and CFG
- instruction stream -> readable Lua-like stack IR
- IR JSON -> HCB, with address relocation for calls/jumps/ThreadStart function pointers
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import struct

SCHEMA = "fvp_analysis.hcb_ir.v1"

NLS_CODECS = {
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


def norm_nls(nls: str) -> str:
    key = (nls or "sjis").lower().replace(" ", "")
    if key in ("shiftjis", "shift-jis", "shift_jis", "sjis"):
        return "sjis"
    if key in ("gbk", "gb2312", "gb18030"):
        return "gbk"
    if key in ("utf8", "utf-8"):
        return "utf8"
    raise ValueError(f"unknown nls: {nls}")


def codec_of(nls: str) -> str:
    return NLS_CODECS[norm_nls(nls)]


def decode_cstring(raw_with_nul: bytes, nls: str) -> str:
    raw = raw_with_nul.split(b"\x00", 1)[0]
    return raw.decode(codec_of(nls), errors="replace")


def encode_cstring(text: str, nls: str) -> bytes:
    b = text.encode(codec_of(nls), errors="strict") + b"\x00"
    if len(b) > 255:
        raise ValueError(f"C string too long for HCB u8 length: {len(b)} bytes including NUL")
    return b


def raw_or_encoded(obj: dict[str, Any], text_key: str, original_key: str, raw_key: str, nls: str) -> bytes:
    """Preserve raw bytes if text was not changed; otherwise encode text."""
    text = obj.get(text_key, "")
    original = obj.get(original_key, text)
    raw_hex = obj.get(raw_key)
    if raw_hex and text == original:
        return bytes.fromhex(raw_hex)
    return encode_cstring(text, nls)


def u8(data: bytes, off: int) -> int:
    return data[off]


def i8(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off+1], "little", signed=True)


def u16(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off+2], "little", signed=False)


def i16(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off+2], "little", signed=True)


def u32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off+4], "little", signed=False)


def i32(data: bytes, off: int) -> int:
    return int.from_bytes(data[off:off+4], "little", signed=True)


def f32(data: bytes, off: int) -> float:
    return struct.unpack_from("<f", data, off)[0]


def w_u8(v: int) -> bytes:
    return int(v & 0xFF).to_bytes(1, "little", signed=False)


def w_i8(v: int) -> bytes:
    return int(v).to_bytes(1, "little", signed=True)


def w_u16(v: int) -> bytes:
    return int(v).to_bytes(2, "little", signed=False)


def w_i16(v: int) -> bytes:
    return int(v).to_bytes(2, "little", signed=True)


def w_u32(v: int) -> bytes:
    return int(v).to_bytes(4, "little", signed=False)


def w_i32(v: int) -> bytes:
    return int(v).to_bytes(4, "little", signed=True)


def w_f32(v: float) -> bytes:
    return struct.pack("<f", float(v))


# Canonical opcode specification used by this project.
OPCODES: dict[int, tuple[str, str]] = {
    0x00: ("nop", "null"),
    0x01: ("init_stack", "i8i8"),
    0x02: ("call", "x32"),
    0x03: ("syscall", "i16"),
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

NAME_TO_OPCODE = {name: op for op, (name, _kind) in OPCODES.items()}

OP_ARG_SIZE = {
    "null": 0,
    "i8": 1,
    "u8": 1,
    "i16": 2,
    "u16": 2,
    "i32": 4,
    "u32": 4,
    "x32": 4,
    "f32": 4,
    "i8i8": 2,
}

TERMINATORS = {"jmp", "jz", "ret", "retv"}


def read_sysdesc(data: bytes, sys_desc_offset: int, nls: str) -> dict[str, Any]:
    off = sys_desc_offset
    entry_point = u32(data, off); off += 4
    nonvolatile = u16(data, off); off += 2
    volatile = u16(data, off); off += 2
    game_mode = u8(data, off); off += 1
    game_mode_reserved = u8(data, off); off += 1
    title_len = u8(data, off); off += 1
    title_raw = data[off:off+title_len]; off += title_len
    title = decode_cstring(title_raw, nls)
    syscall_count = u16(data, off); off += 2
    syscalls = []
    for idx in range(syscall_count):
        argc = u8(data, off); off += 1
        name_len = u8(data, off); off += 1
        name_raw = data[off:off+name_len]; off += name_len
        name = decode_cstring(name_raw, nls)
        syscalls.append({
            "id": idx,
            "args": argc,
            "name": name,
            "name_original": name,
            "name_raw_hex": name_raw.hex(),
        })
    custom_syscall_count = u16(data, off) if off + 2 <= len(data) else 0
    off += 2 if off + 2 <= len(data) else 0
    return {
        "sys_desc_offset": sys_desc_offset,
        "entry_point": entry_point,
        "non_volatile_global_count": nonvolatile,
        "volatile_global_count": volatile,
        "game_mode": game_mode,
        "game_mode_reserved": game_mode_reserved,
        "game_title": title,
        "game_title_original": title,
        "game_title_raw_hex": title_raw.hex(),
        "syscall_count": syscall_count,
        "syscalls": syscalls,
        "custom_syscall_count": custom_syscall_count,
        "sysdesc_end_offset": off,
    }


def syscall_by_id(sysdesc: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(sc["id"]): sc for sc in sysdesc.get("syscalls", [])}


def decode_instruction(data: bytes, pc: int, sysdesc: dict[str, Any], nls: str) -> tuple[dict[str, Any], int]:
    start = pc
    opcode = u8(data, pc); pc += 1
    if opcode not in OPCODES:
        raise ValueError(f"unknown opcode 0x{opcode:02X} at 0x{start:08X}; cannot determine length")
    mnemonic, arg_kind = OPCODES[opcode]
    args: dict[str, Any] = {}

    if mnemonic == "init_stack":
        args["args"] = i8(data, pc); pc += 1
        args["locals"] = i8(data, pc); pc += 1
    elif mnemonic in {"call", "jmp", "jz"}:
        args["target"] = u32(data, pc); pc += 4
    elif mnemonic == "syscall":
        sid = u16(data, pc); pc += 2
        sc = syscall_by_id(sysdesc).get(sid)
        args["id"] = sid
        args["name"] = sc["name"] if sc else f"syscall_{sid}"
        args["arg_count"] = sc["args"] if sc else 0
    elif mnemonic == "push_i32":
        args["value"] = i32(data, pc); pc += 4
    elif mnemonic == "push_i16":
        args["value"] = i16(data, pc); pc += 2
    elif mnemonic == "push_i8":
        args["value"] = i8(data, pc); pc += 1
    elif mnemonic == "push_f32":
        args["value"] = f32(data, pc); pc += 4
    elif mnemonic == "push_string":
        strlen = u8(data, pc); pc += 1
        raw = data[pc:pc+strlen]; pc += strlen
        text = decode_cstring(raw, nls)
        args.update({"length": strlen, "text": text, "text_original": text, "raw_hex": raw.hex()})
    elif mnemonic in {"push_global", "push_global_table", "pop_global", "pop_global_table"}:
        args["index"] = u16(data, pc); pc += 2
    elif mnemonic in {"push_stack", "push_local_table", "pop_stack", "pop_local_table"}:
        args["index"] = i8(data, pc); pc += 1
    else:
        # no argument
        if arg_kind != "null":
            size = OP_ARG_SIZE[arg_kind]
            args["raw_arg_hex"] = data[pc:pc+size].hex()
            pc += size

    inst = {
        "addr": start,
        "opcode": opcode,
        "mnemonic": mnemonic,
        "args": args,
        "size": pc - start,
        "raw_hex": data[start:pc].hex(),
    }
    return inst, pc


def decode_hcb(path: str | Path, nls: str = "sjis") -> dict[str, Any]:
    nls = norm_nls(nls)
    path = Path(path)
    data = path.read_bytes()
    if len(data) < 8:
        raise ValueError("HCB too small")
    sys_desc_offset = u32(data, 0)
    if sys_desc_offset > len(data):
        raise ValueError(f"invalid sys_desc_offset {sys_desc_offset}, file size {len(data)}")
    sysdesc = read_sysdesc(data, sys_desc_offset, nls)

    pc = 4
    instructions: list[dict[str, Any]] = []
    while pc < sys_desc_offset:
        inst, pc2 = decode_instruction(data, pc, sysdesc, nls)
        if pc2 <= pc:
            raise ValueError(f"decoder did not advance at 0x{pc:08X}")
        instructions.append(inst)
        pc = pc2

    # Mark ThreadStart function-pointer immediate pattern: push_i32 ... syscall ThreadStart.
    for i, inst in enumerate(instructions[:-1]):
        nxt = instructions[i + 1]
        if inst["mnemonic"] == "push_i32" and nxt["mnemonic"] == "syscall" and nxt["args"].get("name") == "ThreadStart":
            inst["args"]["address_role"] = "thread_start_function_pointer"

    funcs = split_functions(instructions)
    return {
        "schema": SCHEMA,
        "source_file": str(path),
        "nls": nls,
        "sysdesc": sysdesc,
        "program": {
            "code_start": 4,
            "sys_desc_offset": sys_desc_offset,
            "entry_point": sysdesc["entry_point"],
            "instructions": instructions,
        },
        "functions": funcs,
        "cfg": {},
    }


def split_functions(instructions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    funcs: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for inst in instructions:
        if inst["mnemonic"] == "init_stack":
            if current is not None:
                current["end_addr"] = inst["addr"]
                funcs.append(current)
            current = {
                "name": f"f_{inst['addr']:08X}",
                "start_addr": inst["addr"],
                "args_count": inst["args"].get("args", 0),
                "locals_count": inst["args"].get("locals", 0),
                "instruction_addrs": [inst["addr"]],
            }
        else:
            if current is None:
                current = {
                    "name": f"f_{inst['addr']:08X}",
                    "start_addr": inst["addr"],
                    "args_count": 0,
                    "locals_count": 0,
                    "instruction_addrs": [],
                }
            current["instruction_addrs"].append(inst["addr"])
    if current is not None:
        last_end = instructions[-1]["addr"] + instructions[-1]["size"] if instructions else current["start_addr"]
        current["end_addr"] = last_end
        funcs.append(current)
    # Mark entry function.
    return funcs


def inst_by_addr_map(ir: dict[str, Any]) -> dict[int, dict[str, Any]]:
    return {int(inst["addr"]): inst for inst in ir["program"]["instructions"]}


def stack_delta(inst: dict[str, Any], funcs_by_start: dict[int, dict[str, Any]] | None = None) -> int:
    m = inst["mnemonic"]
    if m in {"nop", "init_stack", "jmp", "ret"}:
        return 0
    if m == "jz" or m == "retv":
        return -1
    if m in {"push_nil", "push_true", "push_i32", "push_i16", "push_i8", "push_f32", "push_string", "push_global", "push_stack", "push_top", "push_return"}:
        return 1
    if m in {"push_global_table", "push_local_table"}:
        return 0  # pop key, push value into same stack slot
    if m in {"pop_global", "pop_stack"}:
        return -1
    if m in {"pop_global_table", "pop_local_table"}:
        return -2
    if m in {"neg"}:
        return 0
    if m in {"add", "sub", "mul", "div", "mod", "bit_test", "and", "or", "set_e", "set_ne", "set_g", "set_ge", "set_l", "set_le"}:
        return -1
    if m == "syscall":
        return -int(inst["args"].get("arg_count", 0))
    if m == "call":
        target = int(inst["args"].get("target", 0))
        argc = 0
        if funcs_by_start and target in funcs_by_start:
            argc = int(funcs_by_start[target].get("args_count", 0))
        return -argc
    return 0


def block_term(inst: dict[str, Any] | None) -> str:
    if not inst:
        return "fallthrough"
    m = inst["mnemonic"]
    if m == "jmp":
        return "jmp"
    if m == "jz":
        return "jz"
    if m == "ret":
        return "ret"
    if m == "retv":
        return "retv"
    return "fallthrough"


def build_cfg(func: dict[str, Any], ir: dict[str, Any] | None = None) -> dict[str, Any]:
    # This overload is also called by decode_hcb before ir exists; use function-local addr list only.
    if ir is not None:
        addr_map = inst_by_addr_map(ir)
        insts = [addr_map[a] for a in func["instruction_addrs"]]
        funcs_by_start = {f["start_addr"]: f for f in ir.get("functions", [])}
    else:
        raise RuntimeError("build_cfg(func) requires full IR in this version")


def build_all_cfg(ir: dict[str, Any]) -> dict[str, Any]:
    addr_map = inst_by_addr_map(ir)
    funcs_by_start = {int(f["start_addr"]): f for f in ir.get("functions", [])}
    out: dict[str, Any] = {}
    for func in ir.get("functions", []):
        insts = [addr_map[a] for a in func["instruction_addrs"] if a in addr_map]
        out[f"0x{func['start_addr']:08X}"] = build_cfg_for_insts(func, insts, funcs_by_start)
    return out


def build_cfg_for_insts(func: dict[str, Any], insts: list[dict[str, Any]], funcs_by_start: dict[int, dict[str, Any]]) -> dict[str, Any]:
    if not insts:
        return {"blocks": [], "max_depth": 0}
    addr_to_idx = {inst["addr"]: i for i, inst in enumerate(insts)}
    leaders = {insts[0]["addr"]}
    for i, inst in enumerate(insts):
        m = inst["mnemonic"]
        if m in {"jmp", "jz"}:
            target = int(inst["args"]["target"])
            if target in addr_to_idx:
                leaders.add(target)
            if i + 1 < len(insts):
                leaders.add(insts[i+1]["addr"])
        elif m in {"ret", "retv"} and i + 1 < len(insts):
            leaders.add(insts[i+1]["addr"])
    leaders = sorted(leaders)
    blocks = []
    addr_to_block: dict[int, int] = {}
    for bid, start in enumerate(leaders):
        next_leader = leaders[bid+1] if bid+1 < len(leaders) else (insts[-1]["addr"] + insts[-1]["size"])
        indices = [i for i, inst in enumerate(insts) if start <= inst["addr"] < next_leader]
        if not indices:
            continue
        for i in indices:
            addr_to_block[insts[i]["addr"]] = len(blocks)
        last = insts[indices[-1]]
        blocks.append({
            "id": len(blocks),
            "start": start,
            "end": insts[indices[-1]]["addr"] + insts[indices[-1]]["size"],
            "instruction_addrs": [insts[i]["addr"] for i in indices],
            "preds": [],
            "succs": [],
            "term": block_term(last),
            "in_depth": 0,
            "out_depth": 0,
            "is_loop_header": False,
        })
    # succs
    for b in blocks:
        last = addr_to_idx.get(b["instruction_addrs"][-1])
        inst = insts[last] if last is not None else None
        if not inst:
            continue
        m = inst["mnemonic"]
        if m == "jmp":
            tid = addr_to_block.get(int(inst["args"]["target"]))
            if tid is not None:
                b["succs"].append(tid)
        elif m == "jz":
            tid = addr_to_block.get(int(inst["args"]["target"]))
            if tid is not None:
                b["succs"].append(tid)
            # fallthrough next inst
            idx = addr_to_idx[inst["addr"]]
            if idx + 1 < len(insts):
                fid = addr_to_block.get(insts[idx+1]["addr"])
                if fid is not None and fid not in b["succs"]:
                    b["succs"].append(fid)
        elif m not in {"ret", "retv"}:
            idx = addr_to_idx[inst["addr"]]
            if idx + 1 < len(insts):
                fid = addr_to_block.get(insts[idx+1]["addr"])
                if fid is not None:
                    b["succs"].append(fid)
    for b in blocks:
        for s in b["succs"]:
            blocks[s]["preds"].append(b["id"])
    # stack depths approximate worklist
    depths: dict[int, int] = {0: 0}
    queue = [0] if blocks else []
    max_depth = 0
    while queue:
        bid = queue.pop(0)
        d = depths.get(bid, 0)
        b = blocks[bid]
        for a in b["instruction_addrs"]:
            d += stack_delta(addr_to_idx and insts[addr_to_idx[a]], funcs_by_start)
            if d < 0:
                d = 0
            max_depth = max(max_depth, d)
        b["in_depth"] = depths.get(bid, 0)
        b["out_depth"] = d
        for sid in b["succs"]:
            nd = max(depths.get(sid, 0), d)
            if sid not in depths or nd != depths[sid]:
                depths[sid] = nd
                queue.append(sid)
    for b in blocks:
        for sid in b["succs"]:
            if blocks[sid]["start"] < b["start"]:
                blocks[sid]["is_loop_header"] = True
    return {"function": func["name"], "start_addr": func["start_addr"], "blocks": blocks, "max_depth": max_depth}


def finalize_ir(ir: dict[str, Any]) -> dict[str, Any]:
    ep = ir["sysdesc"]["entry_point"]
    for f in ir.get("functions", []):
        if f["start_addr"] == ep:
            f["is_entry"] = True
            f["name"] = "entry_point"
        else:
            f["is_entry"] = False
    ir["cfg"] = build_all_cfg(ir)
    return ir


def make_ir(path: str | Path, nls: str = "sjis") -> dict[str, Any]:
    ir = decode_hcb(path, nls)
    return finalize_ir(ir)


def save_json(path: str | Path, obj: Any) -> None:
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def lua_quote(s: str) -> str:
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t') + '"'


def slot_name(args_count: int, idx: int) -> str:
    if idx < 0:
        abs_i = -idx - 2
        return f"a{args_count - abs_i}" if abs_i <= args_count else f"a_{idx}"
    return f"a{idx}" if idx < args_count else f"l{idx - args_count}"


def emit_lua_like(ir: dict[str, Any]) -> str:
    addr_map = inst_by_addr_map(ir)
    func_by_start = {int(f["start_addr"]): f for f in ir.get("functions", [])}
    block_by_func = ir.get("cfg", {})
    lines: list[str] = []
    lines.append("-- Lua-like HCB IR generated by fvp_analysis hcb_to_ir.py")
    lines.append("-- This file is human-readable; the reversible source of truth is the .ir.json file.")
    lines.append("local function __is_nil(v) return v == nil end")
    lines.append("local function __syscall(name, ...) return nil end")
    lines.append("")
    for func in ir.get("functions", []):
        name = func.get("name") or f"f_{func['start_addr']:08X}"
        args_count = int(func.get("args_count", 0))
        locals_count = int(func.get("locals_count", 0))
        args_s = ", ".join(f"a{i}" for i in range(args_count))
        lines.append(f"function {name}({args_s})")
        if locals_count > 0:
            lines.append("  local " + ", ".join(f"l{i}" for i in range(locals_count)))
        # declare stack temps roughly up to max_depth
        cfg = block_by_func.get(f"0x{func['start_addr']:08X}", {})
        max_depth = cfg.get("max_depth", 0)
        if max_depth > 0:
            lines.append("  local " + ", ".join(f"S{i}" for i in range(max_depth + 2)))
        blocks = cfg.get("blocks", [])
        if not blocks:
            blocks = [{"id": 0, "start": func["start_addr"], "instruction_addrs": func["instruction_addrs"], "in_depth": 0, "succs": []}]
        for b in blocks:
            label = f"BB_{b['start']:08X}"
            lines.append(f"  ::{label}:: -- block {b.get('id',0)}, succs={b.get('succs', [])}")
            sp = int(b.get("in_depth", 0))
            for a in b["instruction_addrs"]:
                inst = addr_map[a]
                m = inst["mnemonic"]
                args = inst["args"]
                indent = "  "
                if m == "init_stack":
                    lines.append(f"  -- init_stack args={args.get('args')} locals={args.get('locals')}")
                elif m == "nop":
                    lines.append("  -- nop")
                elif m == "push_nil":
                    lines.append(f"  S{sp} = nil"); sp += 1
                elif m == "push_true":
                    lines.append(f"  S{sp} = true"); sp += 1
                elif m in {"push_i32", "push_i16", "push_i8", "push_f32"}:
                    lines.append(f"  S{sp} = {args.get('value')}"); sp += 1
                elif m == "push_string":
                    lines.append(f"  S{sp} = {lua_quote(args.get('text',''))}"); sp += 1
                elif m == "push_global":
                    lines.append(f"  S{sp} = G[{args['index']}]"); sp += 1
                elif m == "pop_global":
                    sp = max(0, sp-1); lines.append(f"  G[{args['index']}] = S{sp}")
                elif m == "push_stack":
                    lines.append(f"  S{sp} = {slot_name(args_count, int(args['index']))}"); sp += 1
                elif m == "pop_stack":
                    sp = max(0, sp-1); lines.append(f"  {slot_name(args_count, int(args['index']))} = S{sp}")
                elif m == "push_global_table":
                    k = max(0, sp-1); lines.append(f"  S{k} = GT[{args['index']}][S{k}]")
                elif m == "push_local_table":
                    k = max(0, sp-1); lines.append(f"  S{k} = LT[{args['index']}][S{k}]")
                elif m == "pop_global_table":
                    if sp >= 2:
                        lines.append(f"  GT[{args['index']}][S{sp-2}] = S{sp-1}"); sp -= 2
                    else:
                        lines.append("  -- pop_global_table on short stack"); sp = 0
                elif m == "pop_local_table":
                    if sp >= 2:
                        lines.append(f"  LT[{args['index']}][S{sp-2}] = S{sp-1}"); sp -= 2
                    else:
                        lines.append("  -- pop_local_table on short stack"); sp = 0
                elif m == "push_top":
                    lines.append(f"  S{sp} = S{max(0, sp-1)}"); sp += 1
                elif m == "push_return":
                    lines.append(f"  S{sp} = __ret"); sp += 1
                elif m == "neg":
                    lines.append(f"  S{max(0, sp-1)} = -S{max(0, sp-1)}")
                elif m in {"add", "sub", "mul", "div", "mod", "bit_test", "and", "or", "set_e", "set_ne", "set_g", "set_ge", "set_l", "set_le"}:
                    if sp < 2:
                        lines.append(f"  -- {m} on short stack")
                    else:
                        a0, a1 = sp-2, sp-1
                        expr = {
                            "add": f"S{a0} + S{a1}", "sub": f"S{a0} - S{a1}", "mul": f"S{a0} * S{a1}", "div": f"S{a0} / S{a1}", "mod": f"S{a0} % S{a1}",
                            "bit_test": f"(S{a0} & S{a1}) ~= 0", "and": f"(S{a0} ~= nil) and (S{a1} ~= nil)", "or": f"(S{a0} ~= nil) or (S{a1} ~= nil)",
                            "set_e": f"S{a0} == S{a1}", "set_ne": f"S{a0} ~= S{a1}", "set_g": f"S{a0} > S{a1}", "set_ge": f"S{a0} >= S{a1}", "set_l": f"S{a0} < S{a1}", "set_le": f"S{a0} <= S{a1}",
                        }[m]
                        lines.append(f"  S{a0} = ({expr})"); sp -= 1
                elif m == "syscall":
                    argc = int(args.get("arg_count", 0)); base = max(0, sp-argc)
                    argv = ", ".join(f"S{i}" for i in range(base, sp))
                    lines.append(f"  __ret = __syscall({lua_quote(args.get('name',''))}{', ' if argv else ''}{argv})")
                    sp = base
                elif m == "call":
                    target = int(args.get("target", 0)); callee = func_by_start.get(target, {})
                    argc = int(callee.get("args_count", 0)); base = max(0, sp-argc)
                    argv = ", ".join(f"S{i}" for i in range(base, sp))
                    fname = callee.get("name", f"f_{target:08X}")
                    lines.append(f"  __ret = {fname}({argv})")
                    sp = base
                elif m == "jz":
                    sp = max(0, sp-1)
                    target = int(args["target"])
                    lines.append(f"  if __is_nil(S{sp}) then goto BB_{target:08X} end")
                elif m == "jmp":
                    target = int(args["target"])
                    lines.append(f"  goto BB_{target:08X}")
                elif m == "ret":
                    lines.append("  return")
                elif m == "retv":
                    sp = max(0, sp-1); lines.append(f"  return S{sp}")
                else:
                    lines.append(f"  -- unsupported {m}")
        lines.append("end")
        lines.append("")
    return "\n".join(lines)


def encode_instruction(inst: dict[str, Any], old_to_new: dict[int, int], nls: str) -> bytes:
    m = inst["mnemonic"]
    op = NAME_TO_OPCODE[m]
    args = inst.get("args", {})
    out = bytearray([op])
    if m == "init_stack":
        out += w_i8(args.get("args", 0)) + w_i8(args.get("locals", 0))
    elif m in {"call", "jmp", "jz"}:
        old_t = int(args.get("target", 0))
        out += w_u32(old_to_new.get(old_t, old_t))
    elif m == "syscall":
        out += w_u16(args.get("id", 0))
    elif m == "push_i32":
        v = int(args.get("value", 0))
        if args.get("address_role") == "thread_start_function_pointer":
            v = old_to_new.get(v, v)
        out += w_i32(v)
    elif m == "push_i16":
        out += w_i16(args.get("value", 0))
    elif m == "push_i8":
        out += w_i8(args.get("value", 0))
    elif m == "push_f32":
        out += w_f32(float(args.get("value", 0.0)))
    elif m == "push_string":
        raw = raw_or_encoded(args, "text", "text_original", "raw_hex", nls)
        out += w_u8(len(raw)) + raw
    elif m in {"push_global", "push_global_table", "pop_global", "pop_global_table"}:
        out += w_u16(args.get("index", 0))
    elif m in {"push_stack", "push_local_table", "pop_stack", "pop_local_table"}:
        out += w_i8(args.get("index", 0))
    else:
        # one-byte opcode
        pass
    return bytes(out)


def instruction_size_for_encode(inst: dict[str, Any], nls: str) -> int:
    m = inst["mnemonic"]
    if m == "push_string":
        raw = raw_or_encoded(inst.get("args", {}), "text", "text_original", "raw_hex", nls)
        return 2 + len(raw)
    kind = OPCODES[NAME_TO_OPCODE[m]][1]
    return 1 + OP_ARG_SIZE.get(kind, 0)


def assemble_ir(ir: dict[str, Any], nls: str | None = None) -> bytes:
    nls = norm_nls(nls or ir.get("nls", "sjis"))
    instructions = ir["program"]["instructions"]
    # First pass: old address -> new address.
    old_to_new: dict[int, int] = {}
    addr = 4
    for inst in instructions:
        old_to_new[int(inst["addr"])] = addr
        addr += instruction_size_for_encode(inst, nls)
    code = bytearray()
    for inst in instructions:
        code += encode_instruction(inst, old_to_new, nls)
    sys_desc_offset = 4 + len(code)
    sysdesc = ir["sysdesc"]
    old_ep = int(sysdesc.get("entry_point", ir["program"].get("entry_point", 4)))
    entry_point = old_to_new.get(old_ep, old_ep)
    sdb = bytearray()
    sdb += w_u32(entry_point)
    sdb += w_u16(sysdesc.get("non_volatile_global_count", 0))
    sdb += w_u16(sysdesc.get("volatile_global_count", 0))
    sdb += w_u8(sysdesc.get("game_mode", 0))
    sdb += w_u8(sysdesc.get("game_mode_reserved", 0))
    title_raw = raw_or_encoded(sysdesc, "game_title", "game_title_original", "game_title_raw_hex", nls)
    sdb += w_u8(len(title_raw)) + title_raw
    syscalls = sysdesc.get("syscalls", [])
    sdb += w_u16(len(syscalls))
    for sc in syscalls:
        name_raw = raw_or_encoded(sc, "name", "name_original", "name_raw_hex", nls)
        sdb += w_u8(sc.get("args", 0))
        sdb += w_u8(len(name_raw))
        sdb += name_raw
    sdb += w_u16(sysdesc.get("custom_syscall_count", 0))
    return w_u32(sys_desc_offset) + bytes(code) + bytes(sdb)


def write_hcb_from_ir(ir_path: str | Path, out_path: str | Path, nls: str | None = None) -> None:
    ir = load_json(ir_path)
    Path(out_path).write_bytes(assemble_ir(ir, nls=nls))
