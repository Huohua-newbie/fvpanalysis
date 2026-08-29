# -*- coding: utf-8 -*-
"""Round-trip verifier for HCB -> IR -> HCB.

If no text/syscall/title fields are edited in the IR, the rebuilt file should be
binary-identical for ordinary HCB files supported by this converter.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import tempfile

from hcb_ir_core import make_ir, assemble_ir


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Verify HCB -> IR -> HCB roundtrip.")
    p.add_argument("input_hcb")
    p.add_argument("--nls", default="sjis", choices=["sjis", "gbk", "utf8"])
    p.add_argument("--write-rebuilt", default=None, help="Optional path to write rebuilt HCB")
    return p


def main() -> None:
    args = build_parser().parse_args()
    inp = Path(args.input_hcb)
    original = inp.read_bytes()
    ir = make_ir(inp, args.nls)
    rebuilt = assemble_ir(ir, args.nls)
    same = original == rebuilt
    print(f"roundtrip_equal={same}")
    print(f"original_size={len(original)} rebuilt_size={len(rebuilt)}")
    if args.write_rebuilt:
        out = Path(args.write_rebuilt)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(rebuilt)
        print(f"rebuilt written: {out}")
    if not same:
        # Find first differing byte for diagnostics.
        n = min(len(original), len(rebuilt))
        diff = next((i for i in range(n) if original[i] != rebuilt[i]), None)
        if diff is None and len(original) != len(rebuilt):
            diff = n
        print(f"first_diff={diff}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
