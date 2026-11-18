#!/usr/bin/env python3
"""rot_merge.py — find mergeable rotation sequences on the same wire.

Two (or more) Z_POWs on the same wire can be replaced by ONE Z_POW with the summed
angle iff no op touches that wire between them (Z is diagonal and commutes with ops
on other wires) and they sit in the same condition context.

Usage: rot_merge.py <circuit.kmx> [wire]
"""
from __future__ import annotations

import sys
import pathlib
from fractions import Fraction

sys.path.insert(0, '/tmp/opencode/recon/datasets/vqcc-tools-0.1.0/scripts')
import qhdl_bitsim as B

path = pathlib.Path(sys.argv[1])
only = int(sys.argv[2][1:]) if len(sys.argv) > 2 else None
ops, header, xq = B.parse_kmx(str(path))

stack = []
ctx = {}
rots = {}
for i, o in enumerate(ops):
    if o.code == B.C_PUSH:
        stack.append(o.cond)
    elif o.code == B.C_POP:
        if stack:
            stack.pop()
    ctx[i] = tuple(stack)
    if o.code == B.C_ZPOW:
        rots.setdefault(o.q[0], []).append(i)

touch = {}
for i, o in enumerate(ops):
    for w in set(o.q or ()):
        touch.setdefault(w, []).append(i)

for w, idxs in sorted(rots.items()):
    if only is not None and w != only:
        continue
    print(f'=== q{w}: {len(idxs)} rotations')
    for a in range(len(idxs)):
        for b in range(a + 1, len(idxs)):
            i, j = idxs[a], idxs[b]
            if ctx[i] != ctx[j]:
                continue
            between = [k for k in touch.get(w, []) if i < k < j]
            if not between:
                ang = (Fraction(ops[i].angle, 1 << 64) + Fraction(ops[j].angle, 1 << 64)) % 1
                print(f'   MERGE op{i} + op{j} -> {float(ang):.12f} turns (no touch of q{w} between; ctx {ctx[i]})')
    # chains: consecutive rotations with no touch between
    chain = []
    for i in idxs:
        if chain and [k for k in touch.get(w, []) if chain[-1] < k < i]:
            chain = [i]
        else:
            chain.append(i)
        if len(chain) >= 2:
            ang = sum((Fraction(ops[k].angle, 1 << 64) for k in chain), Fraction(0)) % 1
            print(f'   CHAIN {chain} -> {float(ang):.12f} turns  (ctx {[ctx[k] for k in chain]})')
            chain = [i]
