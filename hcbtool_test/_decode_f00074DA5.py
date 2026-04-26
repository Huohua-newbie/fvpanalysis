# -*- coding: utf-8 -*-
"""Decode and document Sakura raw fragment f_00074DA5.

This helper uses the syscall table from Sakura.hcb and decodes the raw function
bytes stored in hcbtool_test/f_00074DA5, then emits a markdown note and a TSV
instruction table for manual reverse-engineering.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import sys

BASE_ADDR = 0x00074DA5
APP_DIR = Path(__file__).resolve().parent
RAW_PATH = APP_DIR / "f_00074DA5"
LUA_PATH = APP_DIR / "f_00074DA5.lua"
HCB_PATH = APP_DIR / "Sakura.hcb"
HCB_IR_CORE = APP_DIR / "hcb_ir_core.py"
OUT_MD = APP_DIR / "f_00074DA5逐条反汇编对照.md"
OUT_TSV = APP_DIR / "f_00074DA5逐条反汇编.tsv"


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
    spec = importlib.util.spec_from_file_location("hcb_ir_core_local", HCB_IR_CORE)
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
    lines.append("# f_00074DA5 逐条反汇编对照")
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
    lines.append("## 2. 与 Lua-like 代码对应的阶段语义")
    lines.append("")
    lines.append("### 阶段 A：清理显示状态并装载标题 Logo 相关图元")
    lines.append("")
    lines.append("对应 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:6) 到 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:93)：")
    lines.append("")
    lines.append("- 调 [`f_00037E50()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120324) 把若干全局显示标志切到关闭/初始化状态。")
    lines.append("- 调 [`f_0005261B()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:165942) 做一次 V3D 运动/镜头状态重置。")
    lines.append("- 置 `G[9] = 1`，说明进入一个特殊显示流程。")
    lines.append("- 通过 [`f_000373A5()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:118905) 装入图元：`logo_bg`、`logo_favo`、`logo_favo_view`、`logo_favo_view_p1`、`logo_favo_view_p2`、`logo_favo_view_p3`。")
    lines.append("- 再通过 `PrimSetZ` / `PrimSetOP` / `PrimSetAlpha` 为这些图元配置层级、位置和初始透明度。")
    lines.append("")
    lines.append("### 阶段 B：启动 Logo 动画")
    lines.append("")
    lines.append("对应 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:94) 到 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:219)：")
    lines.append("")
    lines.append("- 先调用 [`f_00055946()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:172695) 做一次与 V3D 动作同步的等待/启动。")
    lines.append("- 设 `l0 = 2000`，把它当作多段动画统一持续时间。")
    lines.append("- 调 [`f_00037F11()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120423) 开启辅助图元/输入相关状态。")
    lines.append("- 对 257 / 256 / 255 三个片段图元分别执行：")
    lines.append("  - `MotionAlpha(..., 0 -> 255, 2000)`：淡入")
    lines.append("  - `MotionMoveR(..., ±360*10, 0, 2000, 3)`：左右旋转/平移")
    lines.append("  - `MotionMoveS2(..., 5000,1000,5000,1000,2000,3)`：缩放或尺寸变化")
    lines.append("- 对 252 / 254 则执行 `MotionMoveZ`、`MotionMove`、`MotionAlpha`，让背景与前景视图一起推进。")
    lines.append("")
    lines.append("### 阶段 C：等待用户跳过，或等动画自然完成")
    lines.append("")
    lines.append("对应 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:220) 到 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:280)：")
    lines.append("")
    lines.append("- 不断用 `MotionAlphaTest(252)` 测试图元 252 的 alpha 动作是否还在进行。")
    lines.append("- 在循环中每帧调用 [`f_0003769F()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119287)，其本质只是 `ThreadNext`，即让出一帧。")
    lines.append("- 同时轮询 `InputGetDown`，检测 `3` 和 `1` 掩码，若用户按键则触发 `ControlPulse` 并提前进入收尾。")
    lines.append("- 若第一段动画结束，则让图元 250 在 `3500` 时间内淡出；若用户未按键，则再调用 [`f_00037708()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119357) 等待约 `1200` ms 或输入。")
    lines.append("")
    lines.append("### 阶段 D：统一淡出并恢复状态")
    lines.append("")
    lines.append("对应 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:281) 到 [`f_00074DA5.lua`](fvp_analysis/result/hcbtool_test/f_00074DA5.lua:414)：")
    lines.append("")
    lines.append("- 令 253 / 252 / 254 / 255 / 256 / 257 全部在 `2500` 内淡出。")
    lines.append("- 检查 `G[3] >= 1` 后调用 [`f_00036500()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:116863)，它会转去 [`f_0005511C()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:1) 做一个模式切换。当前两个分支执行内容相同，更像保留结构。")
    lines.append("- 再次循环等待图元 252 的 alpha 动画结束，期间允许按键跳过。")
    lines.append("- 最后对 254 / 255 / 256 / 257 / 250 / 253 / 252 再做一次 `100` 时长的快速归零透明度。")
    lines.append("- 清掉 `G[9]`，然后调用 [`f_00037F11(0, nil)`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120423) 关闭辅助状态并返回。")
    lines.append("")
    lines.append("## 3. 具体在做什么")
    lines.append("")
    lines.append("综合看，这不是普通剧情函数，而是一段**标题 / 品牌 Logo 演出脚本**。")
    lines.append("")
    lines.append("它做的事情大致是：")
    lines.append("")
    lines.append("1. 初始化显示状态")
    lines.append("2. 装入 `logo_bg`、`logo_favo` 以及 `logo_favo_view` 与其三个分片 `p1/p2/p3`")
    lines.append("3. 给这些图元设置 Z、位置和透明度")
    lines.append("4. 启动一组淡入 + 位移/缩放动画")
    lines.append("5. 在播放中等待用户按键跳过，或让动画自然播完")
    lines.append("6. 统一淡出并恢复图形状态")
    lines.append("")
    lines.append("因此，`f_00074DA5()` 很可能就是 Sakura 启动流程中负责展示 logo / 品牌画面的一个专用演出函数。")
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
