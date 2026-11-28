#!/usr/bin/env python3
"""build_sha_table.py — build the static 18-file SHA table for a submission tree.

The table is the FIRST half of the campaign's two-receipt gate: the gate
(`harness/submit_gate.sh`) refuses to build a zip unless the tree contains
EXACTLY the files named in the table and every file's sha256 AND byte size
match it.

Usage:
  build_sha_table.py <tree_dir> --out work/sha_tables/sha_table_vNNN.txt \
                     --tree-label "v151 = ..."
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib

EXPECTED = 18


def sha256(p: pathlib.Path) -> tuple[str, int]:
    h = hashlib.sha256()
    n = 0
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("tree", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--tree-label", default="")
    a = ap.parse_args()
    files = sorted(p for p in a.tree.rglob("*") if p.is_file())
    if len(files) != EXPECTED:
        raise SystemExit(f"tree has {len(files)} files, expected {EXPECTED}")
    table = {"tree": a.tree_label or str(a.tree), "files": {}}
    for p in files:
        rel = p.relative_to(a.tree).as_posix()
        table["files"][rel] = list(sha256(p))
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(table, indent=1))
    print(f"wrote {a.out} with {len(table['files'])} files")


if __name__ == "__main__":
    main()
