#!/usr/bin/env python3
"""Exact H24 carry-window probes (read-only; no main-state mutation).

Pre-registered falsifiable hypotheses (2026-11-21):
 H1  The Tony reverse carry block's seven output wires are simultaneously live.
 H2  Immediate measurement-based erasure of completed carries can reduce the
     number of simultaneously live reverse-carry outputs from 7 to <=3 while
     preserving computational-basis wires and pi phase exactly, for every
     relevant Boolean input and every HMR outcome stream.
 H3  A dedicated global scratch wire can be removed only if its value is
     reconstructible/erasable across its whole use interval; this probe tests
     simple affine/complement relations for q34/q35/q38.

The script reports measured facts; it does not modify generator state.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kmxsim as K  # noqa: E402


def intervals(flags: np.ndarray) -> list[tuple[int, int, bool]]:
    """Boolean run intervals over the legal x array."""
    if len(flags) == 0:
        return []
    e = np.flatnonzero(flags[1:] != flags[:-1]) + 1
    starts = np.r_[0, e]
    ends = np.r_[e, len(flags)]
    return [(int(s), int(t), bool(flags[s])) for s, t in zip(starts, ends)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit", type=pathlib.Path)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    ops, xreg = K.parse_kmx(str(args.circuit))
    nq = K.num_wires(ops)
    sim = K.Sim(nq, "rand", 7)
    sim.load_x(xreg)
    carry = [29, 30, 31, 32, 33, 36, 37]
    hits: list[dict] = []
    prev_nonzero = None
    max_live_carry = 0
    max_op = -1
    for i, op in enumerate(ops):
        sim.apply(op)
        live = [w for w in carry if sim.Q[w].any()]
        n = len(live)
        if n > max_live_carry:
            max_live_carry, max_op = n, i
        if n == len(carry):
            hits.append({"op": i, "text": op.text()})
        # Check whether q35 is the complement of q34 over all legal x.
        if i % 25 == 0 or 17500 <= i <= 18500:
            a = K.unpack(sim.Q[34])[: K.MAX_X]
            b = K.unpack(sim.Q[35])[: K.MAX_X]
            if np.array_equal(a, ~b):
                pass
    print(f"max simultaneous nonzero reverse-carry wires = {max_live_carry} at op {max_op} ({ops[max_op].text()})")
    print(f"ops with all seven reverse carries nonzero = {len(hits)}; first={hits[:3]}")
    # Complement timeline q34/q35 at stride 25.
    sim2 = K.Sim(nq, "rand", 7)
    sim2.load_x(xreg)
    timeline = []
    for i, op in enumerate(ops):
        sim2.apply(op)
        if i % 25 == 0:
            a = K.unpack(sim2.Q[34])[: K.MAX_X]
            b = K.unpack(sim2.Q[35])[: K.MAX_X]
            if np.array_equal(a, ~b):
                timeline.append([i, op.text(), "complement"])
            elif np.array_equal(a, b):
                timeline.append([i, op.text(), "equal"])
            else:
                timeline.append([i, op.text(), "neither"])
    # Compress sampled relation labels.
    compressed = []
    for row in timeline:
        if not compressed or compressed[-1][2] != row[2]:
            compressed.append([row[0], row[1], row[2]])
    print("q34/q35 sampled relation transitions:")
    for row in compressed:
        print(" ", row)
    result = {
        "circuit": str(args.circuit),
        "num_ops": len(ops),
        "num_qubits": nq,
        "carry_wires": carry,
        "max_simultaneous_nonzero_reverse_carries": max_live_carry,
        "max_at_op": max_op,
        "max_at_text": ops[max_op].text(),
        "all_seven_nonzero_op_count": len(hits),
        "all_seven_first": hits[:10],
        "q34_q35_relation_transitions": compressed,
    }
    if args.out:
        args.out.write_text(json.dumps(result, indent=2) + "\n")
        print("wrote", args.out)


if __name__ == "__main__":
    main()
