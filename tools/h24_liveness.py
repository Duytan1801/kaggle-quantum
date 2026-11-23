#!/usr/bin/env python3
"""Liveness profile of the 39 q generator build (H24 substrate).

For every wire we compute the intervals during which it holds a value that is
still needed later (a backward liveness pass over the op list).  Two wires can
share one physical wire iff their live intervals never overlap.

This is the cheap discriminating test for H24: it says whether a 38 q (or 37 q)
build is reachable by pure wire re-allocation, or whether a value must be
*recomputed* (the affine-lend route that was killed on 2026-11-22).
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import kmxsim as K  # noqa: E402

WRITE_OPS = {'X', 'H', 'Z', 'S', 'T', 'Y', 'Z_POW', 'CCX', 'CSWAP', 'CCZ'}
READ_OPS = {'CX', 'CZ', 'CCX', 'CSWAP', 'CCZ', 'HMR', 'BIT_STORE0', 'BIT_STORE1'}


def live_intervals(ops: list[K.Op], nq: int) -> dict[int, list[tuple[int, int]]]:
    """Backward liveness: wire w is live at op i if it is read/written at or
    after i and was last written before i."""
    last_write = {}
    last_touch = {}
    for i, op in enumerate(ops):
        wires = list(op.q)
        if op.name == 'HMR':
            wires = [w for w in op.q]
        for w in wires:
            last_touch[w] = i
            if op.name in WRITE_OPS or op.name in ('HMR', 'R'):
                last_write[w] = i
    intervals = defaultdict(list)
    # For each wire, the live ranges are [write_i, last_touch_after_i].
    pending = defaultdict(list)
    for i, op in enumerate(ops):
        wires = list(op.q)
        for w in wires:
            if op.name in WRITE_OPS or op.name in ('HMR', 'R'):
                pending[w].append(i)
    # recompute: a write at i starts a live range that ends at the next touch
    # of that wire after the last subsequent write.
    for w in range(nq):
        touches = [i for i, op in enumerate(ops) if w in op.q]
        if not touches:
            continue
        writes = [i for i, op in enumerate(ops)
                  if w in op.q and (op.name in WRITE_OPS or op.name in ('HMR', 'R'))]
        if not writes:
            continue
        # live range per write: until the next write or end
        for k, wi in enumerate(writes):
            nxt = writes[k + 1] if k + 1 < len(writes) else None
            end = nxt - 1 if nxt is not None else touches[-1]
            if end >= wi:
                intervals[w].append((wi, end))
    return dict(intervals)


def mergeable(iv: dict[int, list[tuple[int, int]]], nq: int) -> list[tuple[int, int, int]]:
    """Pairs of wires whose live ranges never overlap."""
    out = []
    for a in range(nq):
        for b in range(a + 1, nq):
            ia = iv.get(a, [])
            ib = iv.get(b, [])
            if not ia or not ib:
                continue
            overlap = any(not (e1 < s2 or e2 < s1)
                          for s1, e1 in ia for s2, e2 in ib)
            if not overlap:
                out.append((a, b, min(s for s, _ in ia), max(e for _, e in ia)))
    return out


def peak_profile(iv: dict[int, list[tuple[int, int]]], nq: int,
                 n_ops: int) -> tuple[int, list[int], list[tuple[int, int]]]:
    """Peak simultaneously-live wires and the intervals where the peak holds."""
    events: list[tuple[int, int]] = []
    for w, ranges in iv.items():
        for s, e in ranges:
            events.append((s, +1))
            events.append((e + 1, -1))
    events.sort()
    cur = 0
    live: set[int] = set()
    peak = 0
    peak_wires: set[int] = set()
    curve = []
    prev = 0
    for idx, (pos, delta) in enumerate(events):
        cur += delta
        if pos > prev:
            curve.append((prev, pos - 1, cur, sorted(live)))
            prev = pos
        if cur > peak:
            peak = cur
        # rebuild live set lazily below
    # recompute live set per event position
    live = set()
    curve = []
    cur = 0
    prev = 0
    for pos, delta in events:
        if pos > prev:
            curve.append((prev, pos - 1, cur, sorted(live)))
            prev = pos
        # apply all deltas at this position
        idx = 0
        # (events sorted; apply each)
        break
    # simple O(n*w) pass over the range boundaries
    bounds = sorted({p for ranges in iv.values() for (a, b) in ranges for p in (a, b + 1)})
    curve = []
    for i in range(len(bounds) - 1):
        s, e = bounds[i], bounds[i + 1] - 1
        live = {w for w, ranges in iv.items() if any(a <= s <= b for a, b in ranges)}
        curve.append((s, e, len(live), sorted(live)))
    peak = max((c[2] for c in curve), default=0)
    peak_wires = max(curve, key=lambda c: c[2])[3]
    peak_spans = [(s, e) for s, e, c, _ in curve if c == peak]
    return peak, peak_wires, peak_spans


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('circuit', type=pathlib.Path)
    ap.add_argument('--out', type=pathlib.Path)
    args = ap.parse_args()
    ops, xreg = K.parse_kmx(str(args.circuit))
    nq = K.num_wires(ops)
    iv = live_intervals(ops, nq)
    print(f'ops={len(ops)} wires={nq}')
    for w in range(nq):
        r = iv.get(w, [])
        if not r:
            print(f'q{w:2}: unused')
            continue
        print(f'q{w:2}: {len(r):4d} live ranges, first {r[0][0]:6d}-{r[0][1]:6d}, '
              f'last {r[-1][0]:6d}-{r[-1][1]:6d}, total live ops '
              f'{sum(e - s + 1 for s, e in r):6d}')
    pairs = mergeable(iv, nq)
    print(f'\nmergeable (non-overlapping) wire pairs: {len(pairs)}')
    for a, b, s, e in pairs:
        print(f'  q{a} <-> q{b}   (q{a} lives {s}..{e})')

    peak, peak_wires, spans = peak_profile(iv, nq, len(ops))
    print(f'\npeak simultaneously-live wires: {peak}')
    print(f'peak wire set: {peak_wires}')
    if spans:
        print(f'peak spans: {spans[0][0]}..{spans[0][1]}'
              f' ({len(spans)} spans, total '
              f'{sum(e - s + 1 for s, e in spans)} ops)')

    if args.out:
        args.out.write_text(json.dumps({
            'nq': nq, 'n_ops': len(ops),
            'intervals': {str(k): v for k, v in iv.items()},
            'mergeable': pairs,
            'peak_live': peak,
            'peak_wires': peak_wires,
            'peak_spans': spans,
        }, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
