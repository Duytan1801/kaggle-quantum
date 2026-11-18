#!/usr/bin/env python3
"""merge_scan_kmx.py — find mergeable Z_POW rotations on the same wire (kmx text).

Rule: Z_POWs on the same wire can merge into ONE with the summed angle iff
  (a) same condition context (exact PUSH_CONDITION stack tuple), and
  (b) no op touches that wire between them (Z diagonal ⇒ commutes with ops
      on other wires and with controlled ops where the wire is a CONTROL;
      conservative: any touch of the wire blocks).

All angles here are exact multiples of 2^-64 turns (verified), and the
simulator tracks phase in uint64 mod 2^64, so a merged sum applies a
BIT-IDENTICAL phase ⇒ min_margin unchanged ⇒ only n_rot/eps change.

Usage: merge_scan_kmx.py <circuit.kmx>
"""
from __future__ import annotations
import re, sys
from fractions import Fraction

path = sys.argv[1]
lines = open(path).read().splitlines()

ops = []          # (idx, kind, wires, angle)
cond_stack = []
cond_of = {}
ZPOW = re.compile(r'Z_POW q(\d+) (\S+)')
for i, l in enumerate(lines):
    l = l.strip()
    if l.startswith('PUSH_CONDITION'):
        cond_stack.append(l)
    elif l.startswith('POP_CONDITION'):
        if cond_stack:
            cond_stack.pop()
    else:
        m = ZPOW.match(l)
        if m:
            ops.append((i, 'ZPOW', [int(m.group(1))], m.group(2)))
        else:
            m = re.match(r'([A-Z_0-9]+)(?:\s+(.*))?$', l)
            if m:
                kind = m.group(1)
                rest = m.group(2) or ''
                wires = [int(x) for x in re.findall(r'q(\d+)', rest)]
                bits = re.findall(r'b(\d+)', rest)
                ops.append((i, kind, wires, None))
    cond_of[i] = tuple(cond_stack)

touch = {}
for i, kind, wires, ang in ops:
    for w in wires:
        touch.setdefault(w, []).append(i)

rots = {}
angle_of = {}
for i, kind, w, ang in ops:
    if kind == 'ZPOW':
        rots.setdefault(w[0], []).append(i)
        angle_of[i] = Fraction(ang)

total_merges = 0
for w, idxs in sorted(rots.items()):
    # greedy chains: consecutive rotations with no wire touch between
    chains = []
    cur = [idxs[0]]
    for prev, nxt in zip(idxs, idxs[1:]):
        between = [k for k in touch.get(w, []) if prev < k < nxt]
        if between or cond_of[prev] != cond_of[nxt]:
            chains.append(cur); cur = [nxt]
        else:
            cur.append(nxt)
    chains.append(cur)
    for ch in chains:
        if len(ch) >= 2:
            ang = sum((angle_of[j] for j in ch), Fraction(0))
            total_merges += len(ch) - 1
            ctx = cond_of[ch[0]]
            mark = ' [CONDITIONED]' if ctx else ''
            print(f'q{w}: merge ops {ch} ({len(ch)} -> 1), sum angle {float(ang):.15e}{mark}')
print(f'\nTOTAL merges found: {total_merges} (each worth ~+0.14 GM if counted as a rotation)')
