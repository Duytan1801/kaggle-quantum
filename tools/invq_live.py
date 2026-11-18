#!/usr/bin/env python3
"""invq_live.py — qubit liveness timeline for a kickmix circuit (.kmx text).

For every qubit we compute the interval(s) during which it carries a *non-reset*
value: an HMR or R ends the current live range of the qubit it touches (both
measure-and-reset it to |0>).  Ranges that are separated by a reset can be
re-labelled onto the same physical qubit, so the minimal number of physical
qubits is the maximum number of simultaneously live ranges (an interval-packing
bound), computed with a sweep over range endpoints.

Output: per-qubit ranges, the max live count, and the op index where the peak
occurs (so the critical moment can be inspected).

Usage: invq_live.py <file.kmx|file.kmb> [--top N]
"""
from __future__ import annotations

import pathlib
import sys
from collections import defaultdict

RESET_OPS = {'R', 'HMR'}


def to_kmx(path: pathlib.Path) -> list[str]:
    if path.suffix == '.kmx':
        return [l for l in path.read_text().splitlines() if l.strip()]
    sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
    import kickmix as km
    tmp = pathlib.Path('/tmp/opencode/_live.kmx')
    km.Circuit.from_file(str(path), format='kmb').to_file(str(tmp), format='kmx')
    return [l for l in tmp.read_text().splitlines() if l.strip()]


def main() -> None:
    src = pathlib.Path(sys.argv[1])
    lines = to_kmx(src)
    # ranges[q] = list of (start, end) op indices; a range ends when the qubit is reset
    ranges: dict[int, list[tuple[int, int]]] = defaultdict(list)
    open_start: dict[int, int] = {}
    for i, l in enumerate(lines):
        t = l.split()
        op = t[0]
        if op in ('APPEND_TO_REGISTER', 'REGISTER'):
            continue
        qs = [int(x[1:]) for x in t[1:] if x.startswith('q')]
        if op in RESET_OPS:
            for q in qs:
                if q in open_start:
                    ranges[q].append((open_start.pop(q), i))
        else:
            for q in qs:
                if q not in open_start:
                    open_start[q] = i
    last = len(lines)
    for q, s in open_start.items():
        ranges[q].append((s, last))

    # sweep for max simultaneous live ranges
    events: list[tuple[int, int, int]] = []
    for q, rs in ranges.items():
        for a, b in rs:
            events.append((a, 1, q))
            events.append((b + 1, -1, q))
    events.sort()
    cur = 0
    peak = 0
    peak_at = 0
    live: set[int] = set()
    for at, delta, q in events:
        if delta > 0:
            live.add(q)
        else:
            live.discard(q)
        if len(live) > peak:
            peak = len(live)
            peak_at = at
    print(f'file: {src}')
    print(f'ops: {len(lines)}  qubits with ranges: {len(ranges)}')
    print(f'max simultaneously-live ranges (min physical qubits): {peak}  (first at op {peak_at})')
    print(f'total ranges: {sum(len(v) for v in ranges.values())}  '
          f'(qubits reused after reset: {sum(len(v) - 1 for v in ranges.values())})')
    print('per-qubit ranges:')
    for q in sorted(ranges):
        rs = ranges[q]
        flag = '  <- reused' if len(rs) > 1 else ''
        print(f'  q{q:<3} n={len(rs):<3} {rs[:6]}{"..." if len(rs) > 6 else ""}{flag}')
    # show context around the peak
    print(f'--- context around op {peak_at}:')
    for j in range(max(0, peak_at - 4), min(len(lines), peak_at + 5)):
        print(f'  {j}: {lines[j]}')


if __name__ == '__main__':
    main()
