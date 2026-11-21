#!/usr/bin/env python3
"""dqi_liveness.py — per-wire live ranges in a KMX circuit, and the qubit-count lower bound.

The DQI leg's score is `R(eps) * Q^2 * T`, and Q is the circuit's qubit count, so
one qubit is worth ~0.0245 GM at Q=900.  The only way to cut Q is to RE-INDEX
wires so that wires whose live ranges do not overlap share a physical wire
(classical register allocation / interval graph colouring).

This tool streams a .kmx file and computes, per wire:

  * first and last instruction index where the wire appears,
  * the number of instructions touching it,
  * whether it is ever measured / reset (which would make reuse legal),
then computes the interval-graph chromatic number (the minimum number of wires
that can host the circuit) and greedily allocates wires.

Usage:
  python dqi_liveness.py <circuit.kmx> [--json out.json] [--dump-wires file]
"""
from __future__ import annotations

import collections
import heapq
import json
import pathlib
import sys


def main() -> None:
    path = pathlib.Path(sys.argv[1])
    json_out = None
    dump_wires = None
    args = sys.argv[2:]
    for i, a in enumerate(args):
        if a == '--json':
            json_out = pathlib.Path(args[i + 1])
        elif a == '--dump-wires':
            dump_wires = pathlib.Path(args[i + 1])

    ops = collections.Counter()
    first: dict[str, int] = {}
    last: dict[str, int] = {}
    count: collections.Counter[str] = collections.Counter()
    measured: set[str] = set()
    reset: set[str] = set()
    idx = 0
    # gates whose wire arguments are all wires (skip REGISTER/APPEND lines)
    with path.open('r', errors='replace') as f:
        for line in f:
            idx += 1
            t = line.split()
            if not t:
                continue
            op = t[0]
            ops[op] += 1
            if op in ('APPEND_TO_REGISTER', 'REGISTER'):
                continue
            wires = t[1:]
            if op in ('MEASURE', 'MEAS', 'MEASURE_ALL'):
                measured.update(w for w in wires if w.startswith('q'))
            if op in ('RESET', 'CLEAR'):
                reset.update(w for w in wires if w.startswith('q'))
            for w in wires:
                # only quantum wires matter for the qubit count; 'b' wires are
                # classical bits and 'if' is a keyword
                if not w.startswith('q'):
                    continue
                if w not in first:
                    first[w] = idx
                last[w] = idx
                count[w] += 1

    wires = sorted(first)
    n = len(wires)
    # sweep line: maximum number of simultaneously live wires
    events = []
    for w in wires:
        events.append((first[w], 1))
        events.append((last[w] + 1, -1))
    events.sort()
    cur = 0
    max_overlap = 0
    overlap_at = {}
    for pos, d in events:
        cur += d
        if cur > max_overlap:
            max_overlap = cur
            overlap_at[pos] = cur

    # greedy interval colouring -> wire slots
    intervals = sorted(((first[w], last[w], w) for w in wires))
    # slot's current end
    slot_end: list[int] = []
    assign: dict[str, int] = {}
    for s, e, w in intervals:
        # find a slot whose last interval ended before s
        placed = False
        for k in range(len(slot_end)):
            if slot_end[k] < s:
                slot_end[k] = e
                assign[w] = k
                placed = True
                break
        if not placed:
            slot_end.append(e)
            assign[w] = len(slot_end) - 1

    # per slot, list wires in time order
    slots: dict[int, list[tuple[int, int, str]]] = collections.defaultdict(list)
    for w in wires:
        slots[assign[w]].append((first[w], last[w], w))

    print(f'file: {path}')
    print(f'lines: {idx:,}   distinct wires used: {n}')
    print('op counts (top 15):')
    for op, c in ops.most_common(15):
        print(f'   {op:<20} {c:>12,}')
    print(f'measured wires: {len(measured)}   reset wires: {len(reset)}')
    print(f'max simultaneous live wires (interval chromatic bound): {max_overlap}')
    print(f'greedy wire slots needed: {len(slot_end)}')
    if max_overlap < n:
        print(f'>>> Q can in principle drop {n} -> {max_overlap} (saves {n - max_overlap} wires)')

    # wires with short or early-ending lives (merge candidates)
    life = sorted(((last[w] - first[w], count[w], w, first[w], last[w]) for w in wires))
    print('\n30 shortest-lived wires (span, touches, wire, first, last):')
    for span, c, w, s, e in life[:30]:
        print(f'   span {span:>10,}  touches {c:>9,}  {w:<10} [{s:,}..{e:,}]')

    # how many pairs are disjoint
    dis = 0
    srt = sorted(wires, key=lambda w: first[w])
    ends = []
    for w in srt:
        e = last[w]
        dis += sum(1 for x in ends if x < first[w])
        ends.append(e)
    print(f'\ndisjoint (non-overlapping) wire pairs: {dis:,}')

    out = {
        'file': str(path),
        'lines': idx,
        'n_wires': n,
        'max_overlap': max_overlap,
        'greedy_slots': len(slot_end),
        'ops': dict(ops),
        'measured_wires': len(measured),
        'reset_wires': len(reset),
        'disjoint_pairs': dis,
        'wires': {w: [first[w], last[w], count[w], assign[w]] for w in wires},
        'slots': {str(k): [[s, e, w] for (s, e, w) in v] for k, v in slots.items()},
    }
    if json_out:
        json_out.write_text(json.dumps(out))
        print(f'wrote {json_out}')
    if dump_wires:
        with dump_wires.open('w') as f:
            for w in wires:
                f.write(f'{w}\t{first[w]}\t{last[w]}\t{count[w]}\t{assign[w]}\n')
        print(f'wrote {dump_wires}')


if __name__ == '__main__':
    main()
