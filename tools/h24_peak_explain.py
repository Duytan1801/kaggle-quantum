#!/usr/bin/env python3
"""Explain the peak-live wires of an invsqrt build at a chosen op index.

For every wire whose live range covers the chosen op, print the write that
started the range and the next use after it.  This says which wires could be
removed from the simultaneously-live set and what would have to be recomputed.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import kmxsim as K  # noqa: E402
from h24_liveness import live_intervals  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('circuit', type=pathlib.Path)
    ap.add_argument('--op', type=int, default=9797)
    ap.add_argument('--out', type=pathlib.Path)
    args = ap.parse_args()
    ops, xreg = K.parse_kmx(str(args.circuit))
    nq = K.num_wires(ops)
    iv = live_intervals(ops, nq)
    k = args.op
    print(f'ops={len(ops)} wires={nq} focus op {k}')
    print(f'context: {ops[max(0,k-3)].text()} | {ops[k-1].text()} | {ops[k].text()} '
          f'| {ops[min(len(ops)-1,k+1)].text()} | {ops[min(len(ops)-1,k+2)].text()}')
    rows = []
    for w in range(nq):
        ranges = [r for r in iv.get(w, []) if r[0] <= k <= r[1]]
        if not ranges:
            continue
        s, e = ranges[-1]
        writes = [i for i, op in enumerate(ops)
                  if w in op.q and op.name in ('X', 'H', 'Z', 'S', 'T', 'Y', 'Z_POW',
                                               'CCX', 'CSWAP', 'CCZ', 'HMR', 'R')]
        prior = [i for i in writes if i <= k]
        nxt_use = next((i for i, op in enumerate(ops) if i > k and w in op.q), None)
        rows.append({
            'wire': w, 'range': (s, e),
            'last_write': prior[-1] if prior else None,
            'last_write_op': ops[prior[-1]].text() if prior else None,
            'next_use': nxt_use,
            'next_use_op': ops[nxt_use].text() if nxt_use else None,
        })
        print(f'q{w:2}: live {s:6d}..{e:6d} | last write {prior[-1] if prior else None:>6} '
              f'{ops[prior[-1]].text() if prior else "":22} | next use {nxt_use} '
              f'{ops[nxt_use].text() if nxt_use else ""}')
    if args.out:
        args.out.write_text(json.dumps(rows, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
