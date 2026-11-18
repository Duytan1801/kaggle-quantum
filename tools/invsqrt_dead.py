#!/usr/bin/env python3
"""invsqrt_dead.py — find 'dead-write' Toffolis in an invsqrt .kmx circuit.

A dead-write Toffoli is a CCX whose target wire is never *read* again before it is
measured away (HMR), and whose measurement's classical bit is not used before that
measurement.  asteriospanoras' exact fix replaces

    CCX c1 c2 t            (at i)
    ...
    HMR t b                (at j)

with

    HMR t b                (at i)
    CZ c1 c2 if b          (at i+1)

which removes the Toffoli from every shot at no qubit cost.  (The measurement
destroys the target, so the Toffoli's write is dead; the conditional CZ keeps the
phase bookkeeping identical.)

Usage: invsqrt_dead.py FILE.kmx [--show N]
"""
import sys
from collections import defaultdict


def parse(path):
    lines = open(path).read().splitlines()
    ops = []
    for i, l in enumerate(lines):
        t = l.split()
        if not t:
            continue
        ops.append((i, t))
    return lines, ops


def main(path, show=8):
    lines, ops = parse(path)
    counts = defaultdict(int)
    for _, t in ops:
        counts[t[0]] += 1
    print('file:', path, ' lines:', len(lines), ' ops:', len(ops))
    print(' op counts:', dict(sorted(counts.items(), key=lambda kv: -kv[1])))

    # index of each op
    idx = {i: n for n, (i, t) in enumerate(ops)}

    # for each wire: the ops that read it (as a control) and write it
    reads = defaultdict(list)     # wire -> op indices where it is a control
    writes = defaultdict(list)    # wire -> op indices where it is a target
    hmr = defaultdict(list)       # wire -> op indices of HMR measuring it
    bituse = defaultdict(list)    # classical bit -> op indices where it is used
    ccx = []
    for n, (i, t) in enumerate(ops):
        name = t[0]
        if name == 'CCX':
            c1, c2, tg = t[1], t[2], t[3]
            ccx.append((n, c1, c2, tg))
            reads[c1].append(n)
            reads[c2].append(n)
            writes[tg].append(n)
        elif name == 'HMR':
            q, b = t[1], t[2]
            writes[q].append(n)
            hmr[q].append(n)
        elif name == 'R':
            q = t[1]
            writes[q].append(n)
        elif name in ('CX', 'CZ', 'SWAP'):
            a, bb = t[1], t[2]
            reads[a].append(n)
            writes[bb].append(n)
            if name == 'SWAP':
                reads[bb].append(n)
                writes[a].append(n)
        elif name == 'X':
            writes[t[1]].append(n)
        elif name in ('Z', 'Z_POW'):
            writes[t[1]].append(n)
        elif name.startswith('BIT_'):
            writes[t[1]].append(n)
        elif name == 'PUSH_CONDITION':
            bituse[t[1]].append(n)
        elif name.endswith('_IF') or ' if ' in l_ if False else False:
            pass
    # conditional gates: "<OP> ... if b"
    for n, (i, t) in enumerate(ops):
        if len(t) > 1 and t[-2] == 'if':
            bituse[t[-1]].append(n)
    print('\n CCX count:', len(ccx))

    cands = []
    for n, c1, c2, tg in ccx:
        # next measurement of the target
        later_hmr = [h for h in hmr[tg] if h > n]
        if not later_hmr:
            continue
        j = later_hmr[0]
        # target must not be read between n and j
        bad = [r for r in reads[tg] if n < r < j]
        if bad:
            continue
        # target must not be written between either (a later write would matter)
        badw = [w for w in writes[tg] if n < w < j]
        if badw:
            continue
        # the classical bit of that HMR must not be used before j
        b = ops[j][1][2]
        badb = [u for u in bituse[b] if u < j]
        if badb:
            continue
        # the controls must not be touched between n and j in a way that changes them
        # (the fixed version evaluates CZ at position n, the original at n too, so
        #  control values are read at the same place; only the target's value moved)
        cands.append((n, j, c1, c2, tg, b))

    print(' dead-write CCX candidates:', len(cands))
    for n, j, c1, c2, tg, b in cands[:show]:
        print(f'   op {n} (line {ops[n][0]}): CCX {c1} {c2} {tg}   ->  HMR {tg} {b} at op {j} (line {ops[j][0]})')
    return cands


if __name__ == '__main__':
    p = sys.argv[1]
    sh = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 8
    main(p, sh)
