# -*- coding: utf-8 -*-
"""Generate syscall semantic database for fvp_analysis project."""
from __future__ import annotations

from pathlib import Path
import json
import re
from collections import Counter, defaultdict

ROOT = Path("fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src")
SYSCALL_DIR = ROOT / "subsystem/components/syscalls"
WORLD_RS = ROOT / "subsystem/world.rs"
GENERATED_RS = SYSCALL_DIR / "generated.rs"
OUT_DIR = Path("fvp_analysis/result/syscall语义数据库")
OUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_PREFIX = "fvp_analysis/reference/rfvp-0.3.0/crates/rfvp/src"

def rel(path: Path) -> str:
    s = path.as_posix()
    marker = "fvp_analysis/reference/"
    if marker in s:
        return s[s.index(marker):]
    return s

# -----------------------------------------------------------------------------
# 1. Extract base specs from rfvp generated.rs and explicit registrations.
# -----------------------------------------------------------------------------

generated_text = GENERATED_RS.read_text(encoding="utf-8")
world_text = WORLD_RS.read_text(encoding="utf-8")

spec_pat = re.compile(
    r'SyscallSpec\s*\{\s*name:\s*"([^"]+)",\s*group:\s*"([^"]+)",\s*handler:\s*"([^"]+)",\s*argc:\s*(-?\d+),\s*comment:\s*"([^"]*)"\s*\}'
)

base_specs = {}
for name, group, handler, argc, comment in spec_pat.findall(generated_text):
    base_specs[name] = {
        "name": name,
        "group": group,
        "handler": handler,
        "arg_count": int(argc),
        "comment": comment,
        "from_generated_spec": True,
    }

reg_pat = re.compile(r'm\.insert\("([^"]+)"\.into\(\),\s*Box::new\(([^\)]+)\)\);')
registered = {}
for name, handler in reg_pat.findall(world_text):
    registered[name] = handler

# Map handler struct -> implementation file.
handler_files = {}
for p in SYSCALL_DIR.glob("*.rs"):
    text = p.read_text(encoding="utf-8", errors="replace")
    for m in re.finditer(r'pub\s+struct\s+([A-Za-z0-9_]+)\s*;', text):
        handler_files[m.group(1)] = rel(p)

# Legacy/world-only arg counts not present in generated.rs.
manual_argc = {
    "ChrAdd": 4,
    "ChrGetRGB": 2,
    "ChrGetVol": 1,
    "ConfigDisplay": 9,
    "ConfigEtc": 3,
    "ConfigSet": 0,
    "ConfigSound": 5,
    "LoadFile": 0,
    "SaveFile": 0,
    "LoadTitle": 0,
    "SaveTitle": 0,
    "MoviePlay": 2,
    "PrimSetClip": 1,
    "QuickCopy": 2,
    "QuickState": 1,
    "LoadQuick": 1,
    "SaveQuick": 1,
    "SaveLoadMenu": 1,
    "SaveName": 2,
    "SoundPan": 2,
    "TextDataSet": 3,
    "TextDataGet": 3,
    "TextHistory": 4,
    "TextHyphenation": 3,
    "TextReprint": 0,
    "TextRepaint": 0,
    "ExitDialog": 0,
    "MenuMessSkip": 1,
}

# -----------------------------------------------------------------------------
# 2. Semantic enrichment helpers.
# -----------------------------------------------------------------------------

def infer_group(name: str, known: str | None = None) -> str:
    if known:
        # Normalize noisy generated groups.
        gmap = {"V3": "V3D", "Float": "Utils", "Int": "Utils", "Rand": "Utils", "Sys": "System", "BREAKPOINT": "Debug", "Debmess": "Debug"}
        return gmap.get(known, known)
    prefixes = [
        ("Audio", "Audio"), ("Sound", "Sound"), ("Text", "Text"), ("Input", "Input"), ("Control", "Control"),
        ("Thread", "Thread"), ("Timer", "Timer"), ("Movie", "Movie"), ("Motion", "Motion"), ("V3D", "V3D"),
        ("Prim", "Prim"), ("Graph", "Graph"), ("Gaiji", "Gaiji"), ("Save", "Save"), ("Load", "Save"),
        ("Quick", "Save"), ("Parts", "Parts"), ("Flag", "Flag"), ("History", "History"), ("Cursor", "Cursor"),
        ("Color", "Color"), ("Snow", "Snow"), ("Dissolve", "Dissolve"), ("Lip", "Lip"), ("Window", "Window"),
        ("Exit", "Exit"), ("Title", "Title"), ("Config", "LegacyConfig"), ("Chr", "LegacyCharacter"),
    ]
    for pre, group in prefixes:
        if name.startswith(pre):
            return group
    if name in {"IntToText", "FloatToInt", "Rand", "SysProjFolder", "SysAtSkipName"}:
        return "Utils"
    if name in {"Debmess", "BREAKPOINT", "DebugMessage", "BreakPoint"}:
        return "Debug"
    return "Misc"

subsystems_by_group = {
    "Audio": ["bgm_player", "vfs"],
    "Sound": ["se_player", "audio_manager", "vfs"],
    "Text": ["motion_manager.text_manager", "fontface_manager", "motion_manager.graph/texture"],
    "Input": ["inputs_manager"],
    "Control": ["inputs_manager", "scene fast-forward"],
    "Thread": ["thread_wrapper", "thread_manager"],
    "Timer": ["timer_manager"],
    "Movie": ["video_manager", "motion_manager", "audio_manager", "vfs", "GameData.halt"],
    "Motion": ["motion_manager", "prim_manager"],
    "V3D": ["motion_manager.v3d"],
    "Prim": ["motion_manager.prim_manager", "rendering"],
    "Graph": ["motion_manager.graph_buff", "texture cache", "vfs"],
    "Gaiji": ["motion_manager.gaiji_manager", "text_manager", "vfs"],
    "Save": ["save_manager", "thread_wrapper", "motion_manager", "vfs"],
    "Parts": ["motion_manager.parts_manager"],
    "Flag": ["flag_manager"],
    "History": ["history_manager"],
    "Cursor": ["window", "inputs_manager", "cursor_table"],
    "Color": ["motion_manager.color_manager"],
    "Snow": ["motion_manager.snow"],
    "Dissolve": ["motion_manager.dissolve", "thread_wrapper"],
    "Lip": ["motion_manager.lip"],
    "Window": ["window", "GameData.window/lifecycle flags"],
    "Exit": ["GameData.lifecycle", "thread_wrapper"],
    "Title": ["title/menu state"],
    "System": ["system/path"],
    "Utils": ["VM utility only"],
    "Debug": ["logger/debug"],
    "LegacyConfig": ["legacy config state", "bgm_player", "se_player"],
    "LegacyCharacter": ["legacy character table", "color_manager"],
    "Misc": ["unknown"],
}

return_type_overrides = {
    "AudioState": "BoolLike",
    "FlagGet": "BoolLike",
    "HistoryGet": "Mixed<Int|String|Nil>",
    "InputGetCursIn": "BoolLike",
    "InputGetCursX": "Int",
    "InputGetCursY": "Int",
    "InputGetDown": "Int",
    "InputGetEvent": "Table|Nil",
    "InputGetRepeat": "Int",
    "InputGetState": "Int",
    "InputGetUp": "Int",
    "InputGetWheel": "Int",
    "TimerGet": "Int",
    "Movie": "BoolLike",
    "MoviePlay": "BoolLike",
    "MovieState": "BoolLike",
    "Rand": "Float",
    "FloatToInt": "Int",
    "IntToText": "String|Nil",
    "WindowMode": "Mixed<Int|BoolLike|Nil>",
    "ExitMode": "BoolLike|Nil",
    "TextFontCount": "Int",
    "TextFontGet": "Int",
    "TextFontName": "String|Nil",
    "TextOutSize": "Mixed",
    "TextSize": "Mixed",
    "TextTest": "BoolLike",
    "MotionPause": "Int|Nil",
    "V3DMotionPause": "Int|Nil",
    "V3DMotionTest": "BoolLike",
    "MotionAnimTest": "Int",
    "PartsMotionTest": "Int",
    "QuickState": "BoolLike",
    "ChrGetVol": "Int|Nil",
    "TextDataGet": "Mixed",
    "TextHistory": "Int|Nil",
    "SaveData": "Mixed<Int|String|BoolLike|Nil>",
}

def infer_return_type(name: str, group: str) -> str:
    if name in return_type_overrides:
        return return_type_overrides[name]
    if name.endswith("Test") or name.endswith("State") or name.startswith("InputGet") or name.endswith("Get"):
        if group in {"Motion", "V3D", "Movie", "Flag", "Input"}:
            return "BoolLike|Int|Nil"
        return "Mixed"
    return "Nil"

control_flow_overrides = {
    "ThreadNext": {"yield": True, "reason": "requests ThreadNext; current context yields for scheduler turn"},
    "ThreadWait": {"yield": True, "wait": True, "reason": "sets WAIT status until timer expires"},
    "ThreadSleep": {"yield": True, "sleep": True, "reason": "sets SLEEP status until raised/unblocked"},
    "ThreadStart": {"starts_context": True, "reason": "starts/replaces a script context by id"},
    "ThreadExit": {"exits_context": True, "reason": "requests context termination"},
    "TextPrint": {"yield": True, "text_wait": True, "conditional": True, "reason": "may arm text reveal wait and break current context"},
    "DissolveWait": {"yield": True, "dissolve_wait": True, "conditional": True, "reason": "non-nil argument blocks until dissolve completes if transition active"},
    "ExitMode": {"yield": True, "conditional": True, "reason": "mode=3 locks scripter and breaks current context"},
    "ExitDialog": {"yield": True, "reason": "requests exit dialog and breaks current context"},
    "Movie": {"yield": True, "halt": True, "conditional": True, "reason": "modal movie sets halt and breaks current context; layer movie does not"},
    "MoviePlay": {"yield": True, "halt": True, "conditional": True, "reason": "legacy alias of Movie; modal mode halts"},
    "SaveCreate": {"yield": True, "conditional": True, "reason": "fnid=3 requests local save capture and should_break"},
    "SaveData": {"yield": True, "conditional": True, "reason": "some save-data operations request prepare-local-savedata and break"},
    "Load": {"yield": True, "dissolve_wait": True, "reason": "requests load at safe point and waits for dissolve/load transition"},
    "LoadFile": {"yield": True, "reason": "legacy UI request; breaks context"},
    "SaveFile": {"yield": True, "reason": "legacy UI request; prepares save and breaks context"},
    "LoadQuick": {"yield": True, "reason": "delegates load path"},
    "SaveQuick": {"yield": True, "conditional": True, "reason": "delegates save path"},
}

def control_flow(name: str) -> dict:
    base = {
        "yield": False,
        "wait": False,
        "sleep": False,
        "text_wait": False,
        "dissolve_wait": False,
        "starts_context": False,
        "exits_context": False,
        "halt": False,
        "conditional": False,
        "reason": "no VM scheduling side effect identified",
    }
    base.update(control_flow_overrides.get(name, {}))
    return base

# More detailed parameters for common/important syscalls. Others use generic Variant list.
manual_params = {
    "AudioLoad": [("Int", "channel 0..3"), ("String|ConstString|Nil", "audio path; nil unloads/stops channel")],
    "AudioPlay": [("Int", "channel 0..3"), ("Any truthy", "loop flag")],
    "AudioStop": [("Int", "channel 0..3"), ("Int|Nil", "fadeout ms")],
    "AudioState": [("Int", "channel 0..3")],
    "AudioType": [("Int", "channel 0..3"), ("Int", "sound type 0..9")],
    "AudioVol": [("Int", "channel 0..3"), ("Int", "volume 0..100"), ("Int|Nil", "crossfade ms")],
    "AudioSilentOn": [("Int", "channel 0..3")],
    "SoundLoad": [("Int", "slot/channel"), ("String|ConstString|Nil", "sound path; nil unloads")],
    "SoundPlay": [("Int", "slot/channel"), ("Any truthy", "loop/flag"), ("Int|Nil", "optional fade/volume parameter")],
    "SoundStop": [("Int", "slot/channel"), ("Int|Nil", "fadeout ms")],
    "SoundVol": [("Int", "slot/channel"), ("Int", "volume 0..100"), ("Int|Nil", "crossfade ms")],
    "SoundType": [("Int", "slot/channel"), ("Int", "sound type")],
    "SoundTypeVol": [("Int", "sound type"), ("Int", "volume")],
    "SoundMasterVol": [("Int", "master volume")],
    "SoundSilentOn": [("Int", "slot/channel")],
    "ThreadStart": [("Int", "thread id 0..31"), ("Int", "HCB code address")],
    "ThreadWait": [("Int", "wait duration ms")],
    "ThreadSleep": [("Int", "sleep token/duration")],
    "ThreadRaise": [("Int", "raise token")],
    "ThreadExit": [("Int|Nil", "thread id; nil means current")],
    "ThreadNext": [],
    "FlagSet": [("Int", "id_bit_pos 0..2047"), ("Any", "truthy sets flag; nil clears")],
    "FlagGet": [("Int", "id_bit_pos 0..2047")],
    "HistorySet": [("Int|Nil", "kind; nil pushes current entry"), ("Variant", "value")],
    "HistoryGet": [("Int|Nil", "kind; nil returns history count"), ("Int", "index 0=latest")],
    "InputSetClick": [("Int", "0 or 1")],
    "ControlMask": [("Variant", "nil masks control; non-nil unmasks")],
    "TextPrint": [("Int", "text buffer id"), ("String|ConstString", "text to print")],
    "TextBuff": [("Int", "text buffer id 0..31"), ("Int|Nil", "width, default 8"), ("Int|Nil", "height, default 8")],
    "TextClear": [("Int", "text buffer id")],
    "TextColor": [("Int", "text id"), ("Int|Nil", "color slot 1"), ("Int|Nil", "color slot 2"), ("Int|Nil", "color slot 3")],
    "TextFont": [("Int", "text id"), ("Int|Nil", "font id 1"), ("Int|Nil", "font id 2")],
    "GraphLoad": [("Int", "texture index 0..4095"), ("String|ConstString|Nil", "resource path; nil unloads")],
    "GraphRGB": [("Int|Nil", "texture index"), ("Int|Nil", "R tone 0..200 default 100"), ("Int|Nil", "G tone"), ("Int|Nil", "B tone")],
    "GaijiLoad": [("String", "character/code"), ("Int", "font size slot"), ("String", "graph resource path")],
    "Movie": [("String", "movie path"), ("Variant", "nil=layer video; non-nil=modal movie")],
    "MoviePlay": [("String", "movie path"), ("Variant", "nil=layer video; non-nil=modal movie")],
    "MovieState": [("Int", "mode 0 playing? / 1 not loaded?")],
    "MovieStop": [],
    "WindowMode": [("Int", "mode query/set code")],
    "ExitMode": [("Int", "exit behavior mode")],
    "DissolveWait": [("Variant", "nil=query; non-nil=block if dissolve active")],
    "SaveCreate": [("Int", "fnid"), ("Variant", "value")],
    "SaveData": [("Int|Nil", "fnid"), ("Variant", "value"), ("Variant", "value2")],
    "SaveWrite": [("Int", "slot")],
    "Load": [("Int", "slot")],
    "Rand": [],
    "FloatToInt": [("Float", "value")],
    "IntToText": [("Int", "value"), ("Int", "zero pad width")],
}

def generic_params(name: str, argc: int, group: str) -> list[dict]:
    if name in manual_params:
        arr = manual_params[name]
    elif argc < 0:
        arr = []
    else:
        arr = [("Variant", f"arg{i+1}") for i in range(argc)]
    return [
        {"index": i + 1, "type": typ, "meaning": meaning, "confidence": "known" if name in manual_params else "generic"}
        for i, (typ, meaning) in enumerate(arr)
    ]

verification_by_group = defaultdict(lambda: "needs_runtime_verification")
for g in ["Input", "Flag", "Thread", "History", "Movie", "Window", "Exit", "Timer", "Utils", "Debug"]:
    verification_by_group[g] = "implemented_in_rfvp_high_confidence"
for g in ["Audio", "Sound", "Text", "Graph", "Prim", "Motion", "V3D", "Parts", "Save", "Dissolve", "Snow", "Lip", "Color", "Cursor", "Gaiji"]:
    verification_by_group[g] = "implemented_in_rfvp_needs_game_coverage"
for g in ["LegacyConfig", "LegacyCharacter"]:
    verification_by_group[g] = "legacy_compatibility_partial"

# explicit source files by group for evidence fallback
source_by_group = {
    "Audio": "sound.rs", "Sound": "sound.rs", "Text": "text.rs", "Input": "input.rs", "Control": "input.rs",
    "Thread": "thread.rs", "Timer": "timer.rs", "Movie": "movie.rs", "Motion": "motion.rs", "V3D": "motion.rs",
    "Prim": "graph.rs", "Graph": "graph.rs", "Gaiji": "graph.rs", "Save": "saveload.rs", "Parts": "parts.rs",
    "Flag": "flag.rs", "History": "history.rs", "Cursor": "cursor.rs", "Color": "color.rs", "Snow": "other_anm.rs",
    "Dissolve": "other_anm.rs", "Lip": "other_anm.rs", "Window": "utils.rs", "Exit": "utils.rs", "Title": "utils.rs",
    "System": "utils.rs", "Utils": "utils.rs", "Debug": "utils.rs", "LegacyConfig": "legacy.rs", "LegacyCharacter": "legacy.rs",
}

# Build entries.
all_names = sorted(set(base_specs) | set(registered))
entries = []
for name in all_names:
    base = base_specs.get(name, {})
    handler = registered.get(name) or base.get("handler") or name
    group = infer_group(name, base.get("group"))
    argc = base.get("arg_count")
    if argc is None:
        argc = manual_argc.get(name, -1)
    impl_file = handler_files.get(handler)
    if not impl_file:
        f = source_by_group.get(group)
        impl_file = rel(SYSCALL_DIR / f) if f else None
    implementation_status = "implemented_explicitly_in_rfvp" if name in registered else "listed_generated_maybe_stub"
    if handler in {"nullsub_2", "UnimplementedSyscall"}:
        implementation_status = "stub_or_noop"
    if name in registered and group.startswith("Legacy"):
        implementation_status = "implemented_legacy_compatibility"
    evidence = [rel(GENERATED_RS)] if name in base_specs else []
    evidence.append(rel(WORLD_RS)) if name in registered else None
    if impl_file:
        evidence.append(impl_file)
    entry = {
        "name": name,
        "group": group,
        "handler": handler,
        "arg_count": argc,
        "parameter_types": generic_params(name, argc, group),
        "return_type": infer_return_type(name, group),
        "affected_game_data_subsystems": subsystems_by_group.get(group, ["unknown"]),
        "control_flow": control_flow(name),
        "implementation_status": implementation_status,
        "verification_status": verification_by_group[group],
        "evidence_sources": sorted(set(evidence)),
        "notes": [],
    }
    if argc == -1:
        entry["notes"].append("arg_count 未在 generated.rs 中出现，当前为人工/未知占位。")
    if entry["implementation_status"] == "stub_or_noop":
        entry["notes"].append("rfvp 中当前为空实现或兼容占位，不能视为完整原引擎语义。")
    if group.startswith("Legacy") or name in manual_argc:
        entry["notes"].append("该项属于旧版/兼容 syscall 或未进入 generated.rs 的显式注册项。")
    entries.append(entry)

metadata = {
    "schema": "fvp_analysis.syscall_spec.v1",
    "title": "FVP syscall 语义数据库",
    "description": "基于 rfvp-0.3.0、fvp_analysis 项目规范文档和参考资料整理的 syscall 语义数据库。",
    "entry_count": len(entries),
    "source_priority": [
        "rfvp-0.3.0 generated.rs 的 SyscallSpec",
        "rfvp-0.3.0 world.rs 的 SYSCALL_TBL 注册表",
        "rfvp-0.3.0 syscalls/*.rs 的实现代码",
        "fvp_analysis 项目规范文档与前期综述",
    ],
    "field_notes": {
        "return_type": "Nil 表示无有效返回；BoolLike 表示 True/Nil；Mixed 表示按 fnid/mode 分支返回不同类型。",
        "parameter_types": "known 表示依据源码/人工归纳；generic 表示仅按参数数占位，后续需细化。",
        "control_flow.yield": "表示该 syscall 会或可能使当前 VM context 让出执行权。",
    },
}

db = {"metadata": metadata, "syscalls": entries}

# -----------------------------------------------------------------------------
# 3. Output JSON.
# -----------------------------------------------------------------------------
json_path = OUT_DIR / "syscall_spec.json"
json_path.write_text(json.dumps(db, ensure_ascii=False, indent=2), encoding="utf-8")

# -----------------------------------------------------------------------------
# 4. Output TXT summary.
# -----------------------------------------------------------------------------
lines = []
lines.append("FVP syscall 语义数据库 - TXT 简表")
lines.append("=" * 80)
lines.append(f"总条目数: {len(entries)}")
lines.append("")
lines.append("字段: name | group | argc | return_type | control_flow | affected_subsystems | status")
lines.append("-" * 80)
for e in entries:
    cf = []
    for key in ["yield", "wait", "sleep", "text_wait", "dissolve_wait", "starts_context", "exits_context", "halt"]:
        if e["control_flow"].get(key):
            cf.append(key)
    cf_s = ",".join(cf) if cf else "-"
    subs = ",".join(e["affected_game_data_subsystems"])
    lines.append(f"{e['name']} | {e['group']} | {e['arg_count']} | {e['return_type']} | {cf_s} | {subs} | {e['verification_status']}")
lines.append("")
lines.append("按分组统计")
lines.append("-" * 80)
for group, count in sorted(Counter(e["group"] for e in entries).items()):
    lines.append(f"{group}: {count}")
lines.append("")
lines.append("存在 VM 调度副作用的 syscall")
lines.append("-" * 80)
for e in entries:
    if e["control_flow"].get("yield") or e["control_flow"].get("starts_context") or e["control_flow"].get("exits_context") or e["control_flow"].get("halt"):
        lines.append(f"{e['name']}: {e['control_flow']['reason']}")

txt_path = OUT_DIR / "syscall_spec.txt"
txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

# -----------------------------------------------------------------------------
# 5. Output README.md.
# -----------------------------------------------------------------------------
md = []
md.append("# FVP syscall 语义数据库说明")
md.append("")
md.append("本目录由 `fvp_analysis` 阶段二生成，用于建立可供后续工程引用的 syscall 语义数据库。")
md.append("")
md.append("## 文件说明")
md.append("")
md.append("- `syscall_spec.json`：机器可读数据库，供后续脚本、IR、反编译器、编辑器引用。")
md.append("- `syscall_spec.txt`：人类快速浏览用简表。")
md.append("- `README.md`：本说明文档。")
md.append("")
md.append("## 数据来源")
md.append("")
md.append("主要依据：")
md.append("")
md.append("1. `rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/generated.rs` 中的 `SYSCALL_SPECS`。")
md.append("2. `rfvp-0.3.0/crates/rfvp/src/subsystem/world.rs` 中的 `SYSCALL_TBL` 注册表。")
md.append("3. `rfvp-0.3.0/crates/rfvp/src/subsystem/components/syscalls/*.rs` 的实际实现。")
md.append("4. `fvp_analysis/result/fvp_analysis项目规范文档.md` 与前期综述结论。")
md.append("")
md.append("## JSON 顶层结构")
md.append("")
md.append("```json")
md.append("{")
md.append("  \"metadata\": { ... },")
md.append("  \"syscalls\": [ ... ]")
md.append("}")
md.append("```")
md.append("")
md.append("## 单条 syscall 字段")
md.append("")
md.append("| 字段 | 含义 |")
md.append("|---|---|")
md.append("| `name` | syscall 名称，即 HCB 导入表中的符号名。 |")
md.append("| `group` | 功能分组，如 Text、Graph、Sound、Thread。 |")
md.append("| `handler` | rfvp 中对应的 handler struct。 |")
md.append("| `arg_count` | 参数数量。来自 generated.rs 或人工补充。 |")
md.append("| `parameter_types` | 参数类型与含义；`confidence=generic` 表示仍需细化。 |")
md.append("| `return_type` | 返回值类型。`BoolLike` 表示 `True/Nil`。 |")
md.append("| `affected_game_data_subsystems` | 影响的 GameData 子系统。 |")
md.append("| `control_flow` | 是否 yield / wait / sleep / text_wait / halt 等。 |")
md.append("| `implementation_status` | 当前 rfvp 实现状态。 |")
md.append("| `verification_status` | 语义可信度与待验证状态。 |")
md.append("| `evidence_sources` | 证据来源文件。 |")
md.append("| `notes` | 额外说明。 |")
md.append("")
md.append("## 重要约定")
md.append("")
md.append("### 1. 参数类型分级")
md.append("")
md.append("本数据库目前采用两级参数信息：")
md.append("")
md.append("- `confidence=known`：已依据源码或人工归纳填写具体类型。")
md.append("- `confidence=generic`：仅依据参数数量生成 `Variant` 占位，后续需要逐项细化。")
md.append("")
md.append("### 2. 返回值类型")
md.append("")
md.append("- `Nil`：无有效返回或失败返回。")
md.append("- `BoolLike`：FVP VM 风格布尔值，即 `True/Nil`。")
md.append("- `Mixed<...>`：根据 `fnid` / `mode` 等分支返回不同类型。")
md.append("")
md.append("### 3. 调度副作用")
md.append("")
md.append("`control_flow` 字段用于后续 HCB 语义分析时判断该 syscall 是否会改变 VM 调度：")
md.append("")
md.append("- `yield`：当前 context 可能让出执行。")
md.append("- `wait`：进入计时等待。")
md.append("- `sleep`：进入 sleep 状态。")
md.append("- `text_wait`：进入文本显示等待。")
md.append("- `dissolve_wait`：等待画面转场完成。")
md.append("- `starts_context`：启动另一个脚本 context。")
md.append("- `exits_context`：退出 context。")
md.append("- `halt`：暂停宿主游戏推进，如 modal movie。")
md.append("")
md.append("## 统计")
md.append("")
md.append(f"- syscall 条目总数：`{len(entries)}`")
md.append("")
md.append("### 按分组统计")
md.append("")
md.append("| group | count |")
md.append("|---|---:|")
for group, count in sorted(Counter(e["group"] for e in entries).items()):
    md.append(f"| {group} | {count} |")
md.append("")
md.append("## 当前限制")
md.append("")
md.append("1. 不是所有 syscall 的参数类型都已精确化；`generic` 参数需要在下一轮逐项细化。")
md.append("2. 部分旧版/兼容 syscall 来自 `legacy.rs`，其语义可能只覆盖某些早期 FVP 游戏。")
md.append("3. `stub_or_noop` 项不能视为完整原引擎语义。")
md.append("4. 本数据库以 `rfvp` 为当前语义基线，后续仍需用原引擎实机行为校验。")
md.append("")
md.append("## 后续建议")
md.append("")
md.append("下一步建议基于 `syscall_spec.json` 继续生成：")
md.append("")
md.append("- syscall 参数类型精修表。")
md.append("- HCB 反编译器使用的 syscall effect model。")
md.append("- 可视化脚本编辑器中的 syscall 自动补全/说明。")
md.append("- 游戏创作 DSL 的标准库函数映射。")
md.append("")
readme_path = OUT_DIR / "README.md"
readme_path.write_text("\n".join(md) + "\n", encoding="utf-8")

print(json_path)
print(txt_path)
print(readme_path)
print(f"entries={len(entries)}")
print("groups=", dict(sorted(Counter(e['group'] for e in entries).items())))
