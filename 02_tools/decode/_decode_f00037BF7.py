# -*- coding: utf-8 -*-
"""Decode and document Sakura raw fragment f_00037BF7.

This follows the same workflow used for f_00002025 / f_00074DA5 / f_00075195.
It resolves syscall names from Sakura.hcb, decodes each instruction, and writes
both markdown and TSV outputs for manual reverse-engineering.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import importlib.util
import sys

BASE_ADDR = 0x00037BF7
APP_DIR = Path(__file__).resolve().parent
RAW_PATH = APP_DIR / "f_00037BF7"
LUA_PATH = APP_DIR / "f_00037BF7.lua"
HCB_PATH = APP_DIR / "Sakura.hcb"
HCB_IR_CORE = APP_DIR / "hcb_ir_core.py"
OUT_MD = APP_DIR / "f_00037BF7逐条反汇编对照.md"
OUT_TSV = APP_DIR / "f_00037BF7逐条反汇编.tsv"


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
    spec = importlib.util.spec_from_file_location("hcb_ir_core_local_f00037BF7", HCB_IR_CORE)
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
    lines.append("# f_00037BF7 逐条反汇编对照")
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
    lines.append("从 [`f_00037BF7.lua`](fvp_analysis/result/hcbtool_test/f_00037BF7.lua:1) 看，这一段是“退出游戏时的专用演出函数”，其核心动作不是普通 `Quit`，而是先建立一套全屏 byebye 画面与遮罩层，再按顺序执行淡入/缩放/溶解/退出线程。")
    lines.append("")
    lines.append("已识别到的关键步骤包括：")
    lines.append("")
    lines.append("1. 置 `G[298] = true`，并通过 [`f_00037E46()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:120313) 调 `ControlMask(nil)`，屏蔽/冻结用户控制输入。")
    lines.append("2. 条件性调用 [`f_00037AE8()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119932)，说明在某些标题/菜单状态下会先做额外清理。")
    lines.append("3. 调 [`f_00037B23()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:119975)、[`f_00055078()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:171526)、[`f_000553AA()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:171994)、[`f_0005522A()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:171774)、[`f_00054E2E()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:171212) 对场景、计时与 dissolve 相关状态进行初始化。")
    lines.append("4. 建立 4 个全屏/近全屏 prim：")
    lines.append("   - `431`：Tile，全屏遮罩")
    lines.append("   - `430`：`menu_byebye_bg`")
    lines.append("   - `99`：`menu_byebye`")
    lines.append("   - `429`：`menu_byebye` 的另一层，且 blend=1")
    lines.append("   - `35`：另一层全屏 Tile")
    lines.append("5. 这些图层都被加入 group `797`，随后调用 [`f_000520EE()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:165184) 与 [`f_000524BB()`](fvp_analysis/result/hcbtool_test/Sakura_hcb_ir/Sakura.lua:165732) 启动 alpha / scale 运动。")
    lines.append("6. 关键动画参数：")
    lines.append("   - `430`：alpha `0 -> 160`，时长 `l0`（通常 3000ms）")
    lines.append("   - `99` 与 `429`：scale 约 `1100 -> 1000`，时长 `l0`，type=3（减速）")
    lines.append("   - `99`：alpha `0 -> 128`，时长 `l0`")
    lines.append("   - `429`：alpha `0 -> 128`，时长 `l0`，且 type=1")
    lines.append("   - `35`：alpha `0 -> 255`，时长 `l0-500`")
    lines.append("7. 最后调用 `ThreadNext` 后以 [`ThreadExit(0)`](fvp_analysis/result/hcbtool_test/f_00037BF7.lua:228) 结束当前线程。")
    lines.append("")
    lines.append("因此，这段函数可以阶段性命名为：")
    lines.append("")
    lines.append("> **ExitGame_Presentation / 退出游戏演出函数**")
    lines.append("")
    lines.append("其视觉效果大致是：")
    lines.append("")
    lines.append("- 先锁定输入")
    lines.append("- 叠加 byebye 背景、标志与遮罩")
    lines.append("- 通过 alpha 与轻微 scale 收束形成退出演出")
    lines.append("- 再通过 Tile 遮罩与 dissolve / fade 把整屏带出")
    lines.append("")
    lines.append("## 3. 逐条反汇编对照")
    lines.append("")
    lines.append("| # | 地址 | 相对偏移 | 原始字节 | 指令 | 操作数 | 注释 |")
    lines.append("|---:|---:|---:|---|---|---|---|")
    for row in rows:
        lines.append(
            f"| {row.index} | `0x{row.addr:08X}` | `+0x{row.rel:04X}` | `{row.raw_hex}` | `{row.mnemonic}` | `{row.operand}` | {row.note} |"
        )
    lines.append("")
    lines.append("## 4. 小结")
    lines.append("")
    lines.append("[`f_00037BF7()`](fvp_analysis/result/hcbtool_test/f_00037BF7.lua:1) 不是简单的“退出游戏”函数，而是一个完整的退出演出控制器。与标题 LOGO 演出类似，它先构建一套专门的图层（`menu_byebye_bg` / `menu_byebye` / Tile 遮罩），再用 alpha、scale 与 dissolve 形成退场效果，最后让脚本线程退出。说明在 FVP 中，退出游戏同样被当作一段正式的图形演出，而不是立即跳转/关闭。")
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
