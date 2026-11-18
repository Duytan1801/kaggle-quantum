#!/usr/bin/env python3
"""invq_dead.py — find wires that are written but never read (droppable scratch).

In kickmix text a wire is READ by: CX as control, CCX/CCZ as control, CZ (both),
Z (phase on its value), Z_POW (phase on its value), HMR (measure), SWAP (both),
CSWAP, and conditional gates.  It is WRITTEN by: X, CX as target, CCX as target,
SWAP/CSWAP, and reset by R/HMR.

A wire that is only ever written and reset carries no information that any gate
consumes: the whole wire can be deleted (and the circuit re-indexed), which is a
direct width reduction.  For invsqrt, cost = Q * C, so one fewer qubit is worth
about +0.216 GM.

Usage: invq_dead.py <file.kmx|file.kmb>
"""
from __future__ import annotations

import pathlib
import sys
from collections import defaultdict

READ_ROLES = {
    'CX': ('control',), 'CCX': ('control', 'control'), 'CCZ': ('control', 'control'),
    'CSWAP': ('control', 'control', 'control'), 'CZ': ('both', 'both'),
    'Z': ('phase',), 'Z_POW': ('phase',), 'HMR': ('measure',), 'SWAP': ('both', 'both'),
    'NEG': ('phase',),
}


def to_kmx(path: pathlib.Path) -> list[str]:
    if path.suffix == '.kmx':
        return [l for l in path.read_text().splitlines() if l.strip()]
    sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
    import kickmix as km
    tmp = pathlib.Path('/tmp/opencode/_dead.kmx')
    km.Circuit.from_file(str(path), format='kmb').to_file(str(tmp), format='kmx')
    return [l for l in tmp.read_text().splitlines() if l.strip()]


def main() -> None:
    src = pathlib.Path(sys.argv[1])
    lines = to_kmx(src)
    reads: dict[int, list[str]] = defaultdict(list)
    writes: dict[int, list[str]] = defaultdict(list)
    regs: dict[int, str] = {}
    for i, l in enumerate(lines):
        t = l.split()
        op = t[0]
        if op == 'APPEND_TO_REGISTER':
            regs[int(t[1][1:])] = t[2]
            continue
        if op == 'REGISTER':
            continue
        qs = [int(x[1:]) for x in t[1:] if x.startswith('q')]
        if op in ('X',):
            for q in qs:
                writes[q].append(l)
        elif op in ('R',):
            for q in qs:
                writes[q].append(l)
        elif op == 'CX':
            c, x = qs
            reads[c].append(l)
            writes[x].append(l)
        elif op in ('CCX', 'CSWAP'):
            for q in qs[:-1]:
                reads[q].append(l)
            writes[qs[-1]].append(l)
        elif op in ('CCZ', 'CZ'):
            for q in qs:
                reads[q].append(l)
        elif op == 'SWAP':
            for q in qs:
                reads[q].append(l)
                writes[q].append(l)
        elif op in ('Z', 'Z_POW', 'HMR', 'NEG'):
            for q in qs:
                reads[q].append(l)
        elif op in ('BIT_STORE0', 'BIT_STORE1', 'BIT_INVERT', 'PUSH_CONDITION', 'POP_CONDITION'):
            pass
        else:
            for q in qs:
                reads[q].append(l)

    xreg = {q for q, r in regs.items() if r == 'x'}
    print(f'file: {src}')
    print(f'x register wires: {sorted(xreg)}')
    dead = []
    for q in sorted(set(reads) | set(writes)):
        if not reads[q] and writes[q]:
            dead.append(q)
    print(f'wires never read: {dead}')
    for q in dead:
        print(f'  q{q}: {len(writes[q])} writes, role={regs.get(q)}')
        for l in writes[q][:6]:
            print('     ', l)
    # near-dead: read only by resets
    weak = []
    for q in sorted(set(reads) | set(writes)):
        real = [l for l in reads[q] if not l.startswith(('R ', 'HMR '))]
        if not real and q not in xreg:
            weak.append(q)
    print(f'scratch wires read only by reset/measure: {weak}')


if __name__ == '__main__':
    main()
