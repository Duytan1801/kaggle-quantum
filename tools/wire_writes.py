#!/usr/bin/env python3
"""wire_writes.py — static write map for a workspace ops.tsv.

Usage: wire_writes.py <ops.tsv> <q22> [q23 ...]

Prints, for each requested wire, every op that writes it (target of X/CX/CCX/Z/SWAP
etc.), with the op index and kind.  Also prints the first write index for every
register wire q0..q21 (the x-consumption order).
"""
from __future__ import annotations

import sys
import csv


def main() -> None:
    path = sys.argv[1]
    want = sys.argv[2:]
    rows = []
    with open(path) as f:
        r = csv.DictReader(f, delimiter='\t')
        for row in r:
            rows.append(row)

    WRITE_KINDS = {'X', 'CX', 'CCX', 'Z', 'SWAP', 'CSWAP', 'HMR', 'RESET', 'MEASURE', 'MEAS'}
    for w in want:
        hits = []
        for row in rows:
            kind, operands = row['kind'], row['operands']
            qs = [q.strip() for q in operands.split(',')] if operands else []
            if not qs:
                continue
            tgt = None
            if kind in ('X', 'Z', 'HMR', 'RESET'):
                tgt = qs[0]
            elif kind in ('CX', 'CCX'):
                tgt = qs[-1]
            elif kind in ('SWAP', 'CSWAP'):
                tgt = qs[-1]
            if tgt == w:
                hits.append((int(row['index']), kind, operands, row['stage']))
        print(f'--- {w}: {len(hits)} writes')
        for h in hits[:40]:
            print('   ', h)

    print('\n=== first write per register wire (x-consumption order)')
    first = {}
    for row in rows:
        kind, operands = row['kind'], row['operands']
        qs = [q.strip() for q in operands.split(',')] if operands else []
        if not qs:
            continue
        tgt = qs[0] if kind in ('X', 'Z', 'HMR', 'RESET') else (qs[-1] if kind in ('CX', 'CCX', 'SWAP', 'CSWAP') else None)
        if tgt and tgt.startswith('q') and tgt not in first:
            n = int(tgt[1:])
            if n <= 21:
                first[tgt] = (int(row['index']), kind, operands)
    for q in sorted(first, key=lambda z: int(z[1:])):
        print(f'   {q}: first write at op {first[q][0]} ({first[q][1]} {first[q][2]})')


if __name__ == '__main__':
    main()
