#!/usr/bin/env python3
"""build_sha_table.py — write the static 18-file SHA table for a submission tree.

The table is RECEIPT 1a of the two-receipt gate: `harness/submit_gate.sh`
recomputes every file's SHA-256 and size and refuses the tree on any drift.

Usage:
  build_sha_table.py --tree work/trees/v133_combo --out work/sha_tables/sha_table_v133.txt \
                     --desc "v133 = ghazarosbarseghyan91 combo (invsqrt ecf908fec987b61a ...)"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--tree', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--desc', required=True)
    ap.add_argument('--expect', type=int, default=18)
    a = ap.parse_args()

    tree = pathlib.Path(a.tree)
    files = sorted(str(p.relative_to(tree)) for p in tree.rglob('*') if p.is_file())
    if len(files) != a.expect:
        raise SystemExit(f'expected {a.expect} files in {tree}, got {len(files)}: {files}')
    table = {'tree': a.desc, 'files': {}}
    for name in files:
        p = tree / name
        table['files'][name] = [hashlib.sha256(p.read_bytes()).hexdigest(), p.stat().st_size]
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(table, indent=1) + '\n')
    print(f'wrote {out} with {len(table["files"])} files')
    for name in files:
        print(f'  {name:<34} {table["files"][name][0][:16]}  {table["files"][name][1]:>10,}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
