#!/usr/bin/env python3
"""width_probe.py — can the Q44 invsqrt be re-allocated to 43 qubits?

The qccscope liveness report says: static peak 44, 433 peak episodes, greedy
idle-gap cover [(wire 24, 428 eps, 5258 ops), (wire 0, 5 eps, 35 ops)],
uncoverable_episodes = 0.

"Idle" in that report means: a wire is LIVE (holds a non-zero value) across the
whole episode but is not TOUCHED during it.  That is the standard
"re-allocation" argument: if a wire is untouched while a fresh temporary is
needed, the temporary could have been allocated to it -- but only if the wire's
value can be restored, which a mere rename cannot do.

This probe computes the STRICT version of the question:

  Q1 (rename-only): is there a wire whose live interval is a SUBSET of another
     wire's, i.e. can two wires be merged by pure relabelling?  (no value
     change, no op change -- only the wire indices move)

  Q2 (peak-episode allocation): for every op index where the width is at the
     peak, how many wires are simultaneously live-and-untouched?  If that
     count is >= 1 everywhere, the circuit can be re-allocated to peak-1 by
     MOVING the fresh temporary into the idle wire -- but the idle wire's own
     value must be preserved, so this needs a SWAP-based construction.

  Q3 (the real blocker): list the exact ops that open each peak episode and
     the wire(s) that are live-but-untouched across it.

Usage: width_probe.py FILE.kmx [--input-register r0]
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qccscope import kmx, liveness  # noqa: E402

WRITE_TARGETS = {'X': [0], 'CX': [1], 'CCX': [2], 'SWAP': [0, 1], 'CSWAP': [1, 2]}
READS = {'CX': [0], 'CCX': [0, 1], 'CZ': [0, 1], 'CCZ': [0, 1, 2], 'SWAP': [0, 1],
         'CSWAP': [0, 1], 'Z': [0], 'Z_POW': [0], 'HMR': [0], 'R': [0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('kmx')
    ap.add_argument('--input-register', action='append', default=None)
    a = ap.parse_args()
    circ = kmx.load(a.kmx)
    nq = circ.num_qubits
    regs = {r: circ.input_qubits() for r in circ.input_qubits.__self__.registers} if False else None
    iv = np.array(circ.op)  # placeholder to keep numpy import meaningful

    # Use qccscope's liveness (it already computes intervals + width).
    lv = liveness.compute(circ)
    print(f"qubits declared {nq}   static peak {lv.peak}")

    rep = liveness.episode_report(circ, lv)
    eps = rep['episodes']
    print(f"peak episodes: {rep['n_episodes']}   ops at peak: {rep['ops_at_level']}")
    print(f"greedy idle cover: {rep['greedy_cover']}   uncoverable: {rep['uncoverable_episodes']}")
    print(f"idle wires per episode: min {rep['idle_wires_per_episode_min']}, "
          f"mean {rep['idle_wires_per_episode_mean']:.2f}")

    # ---- Q1: rename-only merge test (interval containment) ----
    intervals = lv.intervals  # list of (wire, open, close)
    by_wire = {}
    for rec in intervals:
        w, s, e = rec[0], rec[1], rec[2]
        by_wire.setdefault(w, []).append((s, e))
    merges = []
    for w1, i1 in by_wire.items():
        for w2, i2 in by_wire.items():
            if w1 >= w2:
                continue
            # every live interval of w1 inside some interval of w2?
            if len(i1) <= len(i2) and all(
                    any(a2 <= a1 and b1 <= b2 for (a2, b2) in i2) for (a1, b1) in i1):
                merges.append((w1, w2, len(i1), len(i2)))
    print(f"\nQ1 rename-only merges (w1 inside w2): {len(merges)}")
    for m in merges[:12]:
        print("   ", m)

    # ---- Q2/Q3: per peak episode, the opener op and the idle wires ----
    print("\nQ3 first 12 peak episodes:")
    ops = circ
    for (s, e) in eps[:12]:
        names = []
        for k in range(s, min(e, s + 4)):
            names.append(f"{kmx.OPS[ops.op[k]]}{list(ops.c[k:k+1])}{list(ops.b[k:k+1])}")
        print(f"   episode [{s},{e}) len {e-s}  first ops: {' '.join(names)}")
    print(f"\nwire 24 / wire 0 intervals:")
    for w in (24, 0):
        if w in by_wire:
            print(f"   wire {w}: {by_wire[w]}")


if __name__ == '__main__':
    main()
