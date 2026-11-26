#!/usr/bin/env python3
"""Compare a public release's submission.zip against a static SHA table.

Handles both member layouts competitors use:
  * flat:      angle_k_0.kmb, submission.npz, dqi.kmb, invsqrt.kmb
  * nested:   dfthcsos/angle_k_0.kmb, dfthcsos/submission.npz, dqi.kmb, ...

Usage: cmp_tree.py <zip> <sha_table.json>
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys
import zipfile


def main() -> int:
    z = pathlib.Path(sys.argv[1])
    table = json.loads(pathlib.Path(sys.argv[2]).read_text())["files"]
    ours = {k: v[0] for k, v in table.items()}
    with zipfile.ZipFile(z) as zf:
        members = [n for n in zf.namelist() if not n.endswith('/')]
        print(f'{z.name}: {len(members)} members')
        # flat layout: the chemistry table is the only submission.npz
        npz = [n for n in members if n.endswith('submission.npz')]
        chem_loaders = [n for n in members
                        if n.split('/')[-1].startswith('angle_k_') and n.endswith('.kmb')]
        in_dfthcsos = any('/' in n for n in chem_loaders)
        for n in sorted(members):
            base = n.split('/')[-1]
            if base.startswith('angle_k_') and base.endswith('.kmb'):
                rel = f'dfthcsos/{base}'
            elif base == 'submission.npz':
                rel = 'dfthcsos/submission.npz'
            else:
                rel = base
            h = hashlib.sha256(zf.read(n)).hexdigest()
            if rel in ours:
                tag = 'SAME' if ours[rel] == h else 'DIFF'
            else:
                tag = 'EXTRA'
            print(f'  {tag:5} {h[:16]} {n}   -> {rel}')
        if chem_loaders:
            k = len(set(n.split('/')[-1] for n in chem_loaders))
            print(f'  chemistry loaders: {k} distinct (nested={in_dfthcsos})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
