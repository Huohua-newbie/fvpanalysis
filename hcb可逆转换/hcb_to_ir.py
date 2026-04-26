# -*- coding: utf-8 -*-
"""HCB -> project IR/CFG/Lua-like IR exporter."""
from __future__ import annotations

import argparse
from pathlib import Path

from hcb_ir_core import make_ir, save_json, emit_lua_like


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Convert HCB to reversible JSON IR, CFG and Lua-like stack IR.")
    p.add_argument("input_hcb", help="Input .hcb/.chb file")
    p.add_argument("--nls", default="sjis", choices=["sjis", "gbk", "utf8"], help="Text encoding used by HCB strings")
    p.add_argument("-o", "--out-dir", default=None, help="Output directory; default: alongside input with _hcb_ir suffix")
    p.add_argument("--prefix", default=None, help="Output filename prefix; default: input stem")
    return p


def main() -> None:
    args = build_parser().parse_args()
    inp = Path(args.input_hcb)
    out_dir = Path(args.out_dir) if args.out_dir else inp.with_suffix("").parent / (inp.stem + "_hcb_ir")
    out_dir.mkdir(parents=True, exist_ok=True)
    prefix = args.prefix or inp.stem

    ir = make_ir(inp, args.nls)
    ir_path = out_dir / f"{prefix}.ir.json"
    cfg_path = out_dir / f"{prefix}.cfg.json"
    lua_path = out_dir / f"{prefix}.lua"

    save_json(ir_path, ir)
    save_json(cfg_path, {"schema": "fvp_analysis.hcb_cfg.v1", "source_file": str(inp), "cfg": ir["cfg"], "functions": ir["functions"]})
    lua_path.write_text(emit_lua_like(ir), encoding="utf-8")

    print(f"IR:  {ir_path}")
    print(f"CFG: {cfg_path}")
    print(f"Lua: {lua_path}")
    print(f"functions={len(ir['functions'])} instructions={len(ir['program']['instructions'])}")


if __name__ == "__main__":
    main()
