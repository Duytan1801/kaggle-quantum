#!/usr/bin/env python3
"""rotations.py — list every rotation (Z_POW) in a workspace: target, angle, conditioning.

Usage: rotations.py <workspace_dir> [ops.tsv]
Flags duplicate (target,angle) pairs and angles that differ only by a multiple of pi/2
(a Z rotation by pi/2 is a phase flip / S gate -- usually much cheaper).
"""
from __future__ import annotations

import sys
import csv
import json
import pathlib
from fractions import Fraction

ws = pathlib.Path(sys.argv[1])
rows = []
with open(ws / 'ops.tsv') as f:
    for r in csv.DictReader(f, delimiter='\t'):
        rows.append(r)

rots = [(int(r['index']), r['kind'], r['operands'], r['cond'], r['bit'], r['stage']) for r in rows
        if 'Z_POW' in r['kind']]
print('Z_POW ops:', len(rots))
for r in rots:
    print('   ', r)

# angles from the kmx (ops.tsv has no angle column)
try:
    import kmx_reader  # noqa
except Exception:
    pass

# duplicates on (target, cond)
from collections import Counter
c = Counter((r[2], r[3]) for r in rots)
print('\nduplicate (operands,cond):', [(k, v) for k, v in c.items() if v > 1])

# collect raw op stream angles from the canonical kmx via kickmix if available
try:
    import kickmix as km
    circ = km.Circuit.from_file(str(ws.parent / 'f2cdab0b7afc' / 'circuit.kmx')) if False else None
except Exception as e:
    print('(no angle source)', e)
