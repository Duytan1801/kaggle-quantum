#!/usr/bin/env python3
"""Exact every-op affine scan for H24's q37/q38 divider wires.

This is the pre-registered targeted probe in
``work/recon/h24_divider_affine_prereg_2026-11-22.md``.  It scans every op
in a bounded carry window, over all legal x inputs, for GF(2) affine
relations involving q37 or q38.  The same op-window scan is repeated for
forced-zero, forced-one, and five independent random HMR streams.  Only a
relation present in all streams is salt-invariant.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import defaultdict

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import kmxsim as K  # noqa: E402
from invsqrt_affine import gf2_nullspace  # noqa: E402

TARGETS = (37, 38)


def relation_key(dep: list[int]) -> tuple[int, ...]:
    """Canonical orientation: the target wire comes first."""
    target = next((w for w in TARGETS if w in dep), None)
    if target is None:
        return tuple(sorted(dep))
    rest = [w for w in dep if w != target]
    return (target, *rest)


def scan_one(ops: list[K.Op], xreg: list[int], start: int, stop: int,
             mode: str, seed: int) -> dict[int, set[tuple[int, ...]]]:
    nq = K.num_wires(ops)
    nwords = (K.NPAD + 63) // 64
    ones = np.full(nwords, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    pad = K.NPAD % 64
    if pad:
        ones[-1] &= np.uint64((1 << pad) - 1)
    sim = K.Sim(nq, mode, seed)
    sim.load_x(xreg)
    found: dict[int, set[tuple[int, ...]]] = defaultdict(set)
    for i, op in enumerate(ops):
        sim.apply(op)
        if i < start or i >= stop:
            continue
        planes = [sim.Q[w].copy() for w in range(nq)] + [ones]
        for dep in gf2_nullspace(planes):
            if len(dep) <= 2:
                continue
            if any(w in dep for w in TARGETS):
                found[i].add(relation_key(dep))
    return dict(found)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('circuit', type=pathlib.Path)
    ap.add_argument('--start', type=int, required=True)
    ap.add_argument('--end', type=int, required=True)
    ap.add_argument('--out', type=pathlib.Path, required=True)
    args = ap.parse_args()

    ops, xreg = K.parse_kmx(str(args.circuit))
    streams = [('zero', 0), ('one', 0), ('rand', 1), ('rand', 2),
               ('rand', 3), ('rand', 4), ('rand', 5)]
    per_stream = {
        f'{mode}:{seed}': scan_one(ops, xreg, args.start, args.end, mode, seed)
        for mode, seed in streams
    }

    all_ops = sorted(set().union(*(set(v) for v in per_stream.values())))
    common: list[dict] = []
    stream_specific: list[dict] = []
    for i in all_ops:
        sets = {name: values.get(i, set()) for name, values in per_stream.items()}
        intersection = set.intersection(*sets.values()) if sets else set()
        union = set.union(*sets.values()) if sets else set()
        row = {
            'op_index': i,
            'op': ops[i].text(),
            'common': [list(x) for x in sorted(intersection)],
            'per_stream': {name: [list(x) for x in sorted(values)]
                           for name, values in sets.items()},
        }
        if intersection:
            common.append(row)
        if union - intersection:
            stream_specific.append(row)

    result = {
        'circuit': str(args.circuit),
        'window': [args.start, args.end],
        'num_ops': len(ops),
        'num_qubits': K.num_wires(ops),
        'streams': [f'{m}:{s}' for m, s in streams],
        'common_relation_ops': common,
        'stream_specific_relation_ops': stream_specific,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=1) + '\n')
    print(f'common relation ops: {len(common)}')
    print(f'stream-specific relation ops: {len(stream_specific)}')
    for row in common[:20]:
        print(row['op_index'], row['op'], row['common'])
    print(f'wrote {args.out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
