#!/usr/bin/env python3
"""Analyse the divider's CSWAP permutation runs for width reduction.

For each run of CSWAPs we report, per CSWAP, the three wires involved and the
live-width profile of the run.  The question the run answers: can the run be
reordered (or split) so that fewer data wires are simultaneously live, which
is the only way the 39 q generator could reach 38 q / 37 q.
"""
from __future__ import annotations

import argparse
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import kmxsim as K  # noqa: E402


def runs(ops: list[K.Op], gap: int = 40) -> list[tuple[int, int]]:
    idx = [i for i, o in enumerate(ops) if o.name == 'CSWAP']
    if not idx:
        return []
    out = []
    start = prev = idx[0]
    for i in idx[1:]:
        if i - prev > gap:
            out.append((start, prev))
            start = i
        prev = i
    out.append((start, prev))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('circuit', type=pathlib.Path)
    ap.add_argument('--gap', type=int, default=40)
    args = ap.parse_args()
    ops, xreg = K.parse_kmx(str(args.circuit))
    print(f'ops={len(ops)} wires={K.num_wires(ops)}')
    for a, b in runs(ops, args.gap):
        block = [o for o in ops[a:b + 1] if o.name == 'CSWAP']
        wires = defaultdict(int)
        for o in block:
            for w in o.q:
                wires[w] += 1
        controls = {o.q[0] for o in block}
        print(f'\nrun ops {a}..{b}: {len(block)} CSWAPs, controls {sorted(controls)}')
        print('  participants:', sorted(w for w in wires if w not in controls),
              f'({len(wires) - len(controls)} data wires)')
        # prefix/suffix usage of each participant after the run
        for w in sorted(wires):
            after = next((i for i, o in enumerate(ops) if i > b and w in o.q), None)
            before = max((i for i, o in enumerate(ops) if i < a and w in o.q), default=None)
            print(f'    q{w:2}: in-run uses {wires[w]:3d} | last use before run '
                  f'{before} | first use after run {after}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
