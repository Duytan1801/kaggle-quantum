#!/usr/bin/env python3
"""rot_angles.py — exact rotation inventory for an invsqrt circuit.

For every Z_POW in the kmx: index, target wire, exact angle (turns), enclosing
condition stack, and the verifier's counted-vs-uncounted status (from the exec
sample).  Flags:
  * Clifford angles (multiple of 1/4 turn) -> likely free (level < 4)
  * pairs on the same wire with no intervening touch -> mergeable (angle sum)
  * pairs on the same wire with angle sum 0 mod 1 turn -> cancellable

Usage: rot_angles.py <circuit.kmx> [exec_seed1.json]
"""
from __future__ import annotations

import sys
import json
import pathlib
from fractions import Fraction

sys.path.insert(0, '/tmp/opencode/recon/datasets/vqcc-tools-0.1.0/scripts')
import qhdl_bitsim as B

path = pathlib.Path(sys.argv[1])
ops, header, xq = B.parse_kmx(str(path))
exec_path = sys.argv[2] if len(sys.argv) > 2 else None
counts = {}
rows_n = 1
if exec_path:
    d = json.loads(pathlib.Path(exec_path).read_text())
    rows_n = d['rows']
    counts = {int(k): v for k, v in d.get('sampled', {}).items()}

# enclosing condition stack
stack = []
rots = []
for i, o in enumerate(ops):
    if o.code == B.C_PUSH:
        stack.append(o.cond)
    elif o.code == B.C_POP:
        if stack:
            stack.pop()
    elif o.code == B.C_ZPOW:
        turns = Fraction(o.angle, 1 << 64)
        rots.append(dict(i=i, wire=o.q[0], angle=o.angle, turns=turns, cond=tuple(stack),
                         mean=(counts.get(i, 0) / rows_n) if counts else None))

print(f'Z_POW ops: {len(rots)}')
for r in rots:
    t = r['turns']
    frac = Fraction(t, 1)
    cliff = (frac * 4) % 1 == 0
    pc = r['mean'] if r['mean'] is not None else 1.0
    print(f"  op {r['i']:>6} q{r['wire']:<3} angle={float(t):.12f} turns  cond={r['cond'] or '-'} "
          f"exec={pc:.4f} {'CLIFFORD' if cliff else ''}")

# touch map
touch = {}
for i, o in enumerate(ops):
    for w in set(o.q or ()):
        touch.setdefault(w, []).append(i)

print('\n=== same-wire pairs (no intervening touch of that wire), angle sum not 0:')
for a in range(len(rots)):
    for b in range(a + 1, len(rots)):
        ra, rb = rots[a], rots[b]
        if ra['wire'] != rb['wire']:
            continue
        between = [i for i in touch.get(ra['wire'], []) if ra['i'] < i < rb['i']]
        if between:
            continue
        s = (ra['turns'] + rb['turns']) % 1
        tag = 'CANCEL' if s == 0 else 'MERGE'
        print(f"  {tag}: op{ra['i']}(q{ra['wire']}) + op{rb['i']} -> {float(s):.12f} turns "
              f"(cond {ra['cond']} vs {rb['cond']})")
