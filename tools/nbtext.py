#!/usr/bin/env python3
"""nbtext.py — dump a notebook's markdown/code summary.

Usage: nbtext.py <notebook.ipynb> [--code N] [--md] [--grep PATTERN]
"""
from __future__ import annotations

import sys
import json
import pathlib

p = pathlib.Path(sys.argv[1])
nb = json.loads(p.read_text())
args = sys.argv[2:]


def show_code(n=None):
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] != 'code':
            continue
        src = ''.join(c['source'])
        if n is not None and i != n:
            continue
        print(f'--- code cell {i} ({len(src)} chars)')
        print(src[:4000])
        print()


if '--grep' in args:
    pat = args[args.index('--grep') + 1]
    for i, c in enumerate(nb['cells']):
        src = ''.join(c['source'])
        if pat.lower() in src.lower():
            print(f'=== cell {i} ({c["cell_type"]}) hit "{pat}"')
            for ln in src.split('\n'):
                if pat.lower() in ln.lower():
                    print('   >', ln[:300])
            print()
elif '--md' in args:
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] == 'markdown':
            print(f'--- md cell {i}')
            print(''.join(c['source'])[:3000])
            print()
elif '--code' in args:
    show_code(int(args[args.index('--code') + 1]))
else:
    print('cells:', len(nb['cells']))
    for i, c in enumerate(nb['cells']):
        src = ''.join(c['source'])
        print(f'  [{i}] {c["cell_type"]:8} {len(src):>8} chars  {src[:110].splitlines()[0] if src.strip() else ""}')
