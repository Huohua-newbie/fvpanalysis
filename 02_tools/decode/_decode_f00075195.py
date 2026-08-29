# -*- coding: utf-8 -*-
"""Decode and document Sakura raw fragment f_00075195.

This helper mirrors the workflow previously used for f_00002025 and f_00074DA5:
- load raw bytes from a standalone fragment file
- resolve syscall names from Sakura.hcb
- decode each instruction with exact offsets
- emit markdown and TSV for manual reverse-engineering
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import sys

BASE_ADDR = 0x00075195
APP_DIR = Path(__file__).resolve().parent
RAW_PATH = APP_DIR / "f_00075195"
LUA_PATH = APP_DIR / "f_00075195.lua"
HCB_PATH = APP_DIR / "Sakura.hcb"
HCB_IR_CORE = APP_DIR / "hcb_ir_core.py"
OUT_MD = APP_DIR / "f_00075195逐条反汇编对照.md"
OUT_TSV = APP_DIR / "f_00075195逐条反汇编.tsv"


@dataclass
class DecodedRow:
    index: int
    rel: int
    addr: int
    raw_hex: str
    mnemonic: str
    operand: str
    note: str



def load_hcb_ir_core():
    spec = importlib.util.spec_from_file_location("hcb_ir_core_local_f00075195", HCB_IR_CORE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"无法加载 {HCB_IR_CORE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module



def format_operand(inst: dict) -> str:
    args = inst.get("args", {})
    mnemonic = inst["mnemonic"]
    if mnemonic == "init_stack":
        return f"args={args.get('args')}, locals={args.get('locals')}"
    if mnemonic in {"call", "jmp", "jz"}:
        return f"0x{int(args.get('target', 0)):08X}"
    if mnemonic == "syscall":
        return f"id={args.get('id')} ({args.get('name')}), argc={args.get('arg_count')}"
    if mnemonic in {"push_i32", "push_i16", "push_i8", "push_f32"}:
        return str(args.get("value"))
    if mnemonic == "push_string":
        return repr(args.get("text", ""))
    if mnemonic in {"push_global", "push_global_table", "pop_global", "pop_global_table"}:
        return f"G[{args.get('index')}]"
    if mnemonic in {"push_stack", "push_local_table", "pop_stack", "pop_local_table"}:
        return f"STACK[{args.get('index')}]"
    return ""



def format_note(inst: dict) -> str:
    mnemonic = inst["mnemonic"]
    args = inst.get("args", {})
    if mnemonic == "call":
        return f"调用函数 f_{int(args.get('target', 0)):08X}"
    if mnemonic == "syscall":
        return f"调用系统函数 {args.get('name')}"
    if mnemonic == "jmp":
        return f"无条件跳转到 0x{int(args.get('target', 0)):08X}"
    if mnemonic == "jz":
        return f"栈顶为 nil 则跳转到 0x{int(args.get('target', 0)):08X}"
    if mnemonic.startswith("push_"):
        return "压栈"
    if mnemonic.startswith("pop_"):
        return "出栈写回"
    if mnemonic == "set_e":
        return "比较是否相等"
    if mnemonic == "set_ne":
        return "比较是否不等"
    if mnemonic == "set_g":
        return "比较是否大于"
    if mnemonic == "set_ge":
        return "比较是否大于等于"
    if mnemonic == "set_l":
        return "比较是否小于"
    if mnemonic == "set_le":
        return "比较是否小于等于"
    if mnemonic == "add":
        return "栈顶两项相加"
    if mnemonic == "sub":
        return "栈顶两项相减"
    if mnemonic == "mul":
        return "栈顶两项相乘"
    if mnemonic == "div":
        return "栈顶两项相除"
    if mnemonic == "mod":
        return "栈顶两项取模"
    if mnemonic == "bit_test":
        return "按位测试"
    if mnemonic == "and":
        return "逻辑与"
    if mnemonic == "or":
        return "逻辑或"
    if mnemonic == "neg":
        return "取负"
    if mnemonic == "ret":
        return "函数返回"
    return ""



def decode_rows() -> list[DecodedRow]:
    hcb = load_hcb_ir_core()
    hcb_data = HCB_PATH.read_bytes()
    sys_desc_offset = int.from_bytes(hcb_data[:4], "little", signed=False)
    sysdesc = hcb.read_sysdesc(hcb_data, sys_desc_offset, "sjis")
    fragment = RAW_PATH.read_bytes()

    rows: list[DecodedRow] = []
    pc = 0
    index = 1
    while pc < len(fragment):
        inst, pc2 = hcb.decode_instruction(fragment, pc, sysdesc, "sjis")
        rows.append(DecodedRow(
            index=index,
            rel=pc,
            addr=BASE_ADDR + pc,
            raw_hex=inst["raw_hex"].upper(),
            mnemonic=inst["mnemonic"],
            operand=format_operand(inst),
            note=format_note(inst),
        ))
        pc = pc2
        index += 1
    return rows



def count_by_mnemonic(rows: list[DecodedRow], mnemonic: str) -> int:
    return sum(1 for row in rows if row.mnemonic == mnemonic)



def build_markdown(rows: list[DecodedRow]) -> str:
    raw = RAW_PATH.read_bytes()
    lines: list[str] = []
    lines.append("# f_00075195 逐条反汇编对照")
    lines.append("")
    lines.append("## 1. 基本信息")
    lines.append("")
    lines.append(f"- Lua-like 文件：`{LUA_PATH.as_posix()}`")
    lines.append(f"- 原始字节文件：`{RAW_PATH.as_posix()}`")
    lines.append(f"- 基址：`0x{BASE_ADDR:08X}`")
    lines.append(f"- 字节长度：`{len(raw)}` bytes")
    lines.append(f"- 结束地址：`0x{BASE_ADDR + len(raw) - 1:08X}`")
    lines.append(f"- 指令数：`{len(rows)}`")
    lines.append(f"- `call` 数：`{count_by_mnemonic(rows, 'call')}`")
    lines.append(f"- `syscall` 数：`{count_by_mnemonic(rows, 'syscall')}`")
    lines.append("")
    lines.append("## 2. 整体功能概览")
    lines.append("")
    lines.append("从 [`f_00075195.lua`](fvp_analysis/result/hcbtool_test/f_00075195.lua:1) 可见，该函数是标题界面 / title menu 的一个资源构建与状态切换函数，而不是单一图层动画函数。它完成的核心工作包括：")
    lines.append("")
    lines.append("1. 根据 `G[2108]~G[2111]` 决定标题背景变体 `title_bg1_A/B/C/D`；")
    lines.append("2. 装载标题背景、copyright、logo 与各菜单项图元；")
    lines.append("3. 根据 `G[3]` 等状态决定是否使用 `title_album` 还是 `title_omit` / `title_trial` 等资源；")
    lines.append("4. 通过若干子函数（如 `f_00077A12()`、`f_00077B0E()`、`f_00077C0A()`、`f_00077D06()`、`f_00077E02()`）给不同菜单组挂接 `MotionAnim` 帧动画；")
    lines.append("5. 当 `a1 != 1` 时执行完整资源回收：停止动画、对所有相关 prim 调 `f_00037421()` / `PrimSetNull`，并清理标题界面相关全局状态。")
    lines.append("")
    lines.append("因此，`f_00075195` 更接近：")
    lines.append("")
    lines.append("> **TitleScene_BuildOrTeardown / 标题界面资源建立与回收函数**")
    lines.append("")
    lines.append("而不是简单的“播放一段动画”的函数。")
    lines.append("")
    lines.append("## 3. 已识别到的局部结构")
    lines.append("")
    lines.append("### 3.1 背景变体选择")
    lines.append("")
    lines.append("函数开头通过 `G[2108]~G[2111]` 组合出 `l84`，再把它映射为：")
    lines.append("")
    lines.append("- `0 -> title_bg1_A`")
    lines.append("- `1 -> title_bg1_B`")
    lines.append("- `2 -> title_bg1_C`")
    lines.append("- `3 -> title_bg1_D`")
    lines.append("")
    lines.append("同时把 `G[243]` 写成对应编号，说明标题背景可能与某种标题界面模式 / 已解锁状态相关。")
    lines.append("")
    lines.append("### 3.2 菜单组资源批量装载")
    lines.append("")
    lines.append("该函数并不是逐项零散处理，而是按组装载：")
    lines.append("")
    lines.append("- 背景与版权：`258`, `278`")
    lines.append("- logo：`265`")
    lines.append("- start 组：`1500~1516`")
    lines.append("- continue 组：`1517~1533`")
    lines.append("- album / omit / trial 相关组：`1534~1550`、`277`")
    lines.append("- option 组：`1551~1567`")
    lines.append("- end 组：`1568~1584`")
    lines.append("")
    lines.append("这些组之间都有类似模式：")
    lines.append("")
    lines.append("- 主节点先 `f_00037345(..., 5, nil)` 进入 group 5")
    lines.append("- 其后 15 个分帧图层用 `f_000373A5(..., nil, nil)` 载入")
    lines.append("- 主节点随后 `PrimSetDraw(..., 1)` + `PrimSetAlpha(..., 0)`")
    lines.append("- group 根节点如 `1500/1517/1534/1551/1568` 则 `PrimSetDraw(..., 0)`")
    lines.append("- 最后调用专用函数 `f_00077A12` / `f_00077B0E` / `f_00077C0A` / `f_00077D06` / `f_00077E02` 为这一组安装动画状态")
    lines.append("")
    lines.append("### 3.3 五个菜单组动画驱动函数")
    lines.append("")
    lines.append("已读取到以下 5 个函数定义：")
    lines.append("")
    lines.append("- [`f_00077A12()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:234037)")
    lines.append("- [`f_00077B0E()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:234145)")
    lines.append("- [`f_00077C0A()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:234253)")
    lines.append("- [`f_00077D06()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:234361)")
    lines.append("- [`f_00077E02()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:234469)")
    lines.append("")
    lines.append("它们结构高度一致：")
    lines.append("")
    lines.append("- `a1 == 0`：把对应 `G[1234]~G[1238]` 标志清 0；")
    lines.append("- `a1 == 2`：对该组首帧与第二帧调用一次短促 `MotionAnim(..., 1, 2)`，像是焦点切入或初始化态；")
    lines.append("- 其他情况：若标志未置位，则对整组多个 frame prim 连续调用 `MotionAnim(..., 150, ...)`，并把标志置 1。")
    lines.append("")
    lines.append("说明这些函数本质上是：")
    lines.append("")
    lines.append("> **标题菜单按钮组的逐帧动画安装器 / 播放控制器**")
    lines.append("")
    lines.append("## 4. 逐条反汇编对照")
    lines.append("")
    lines.append("| # | 地址 | 相对偏移 | 原始字节 | 指令 | 操作数 | 注释 |")
    lines.append("|---:|---:|---:|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row.index} | `0x{row.addr:08X}` | `+0x{row.rel:04X}` | `{row.raw_hex}` | `{row.mnemonic}` | `{row.operand}` | {row.note} |"
        )
    lines.append("")
    lines.append("## 5. 小结")
    lines.append("")
    lines.append("与之前研究的 [`f_00074DA5()`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:1) 不同，[`f_00075195()`](fvp_analysis/result/hcbtool_test/f_00075195.lua:1) 更接近标题界面构建函数：它主要负责**装载标题资源、决定不同模式下的资源分支、把各菜单按钮帧图组织成 prim 组，并挂接对应的 MotionAnim 动画函数**。当传入参数不等于 1 时，它又会把整套标题资源回收掉，说明它同时承担“建立 / 销毁标题界面”的双重职责。")
    lines.append("")
    return "\n".join(lines)



def build_tsv(rows: list[DecodedRow]) -> str:
    lines = ["index\taddr\trel\traw_hex\tmnemonic\toperand\tnote"]
    for row in rows:
        lines.append(
            "\t".join([
                str(row.index),
                f"0x{row.addr:08X}",
                f"+0x{row.rel:04X}",
                row.raw_hex,
                row.mnemonic,
                row.operand.replace("\t", " "),
                row.note.replace("\t", " "),
            ])
        )
    return "\n".join(lines)



def main() -> None:
    rows = decode_rows()
    OUT_MD.write_text(build_markdown(rows), encoding="utf-8")
    OUT_TSV.write_text(build_tsv(rows), encoding="utf-8")
    print(f"instructions={len(rows)}")
    print(f"markdown={OUT_MD}")
    print(f"tsv={OUT_TSV}")


if __name__ == "__main__":
    main()
