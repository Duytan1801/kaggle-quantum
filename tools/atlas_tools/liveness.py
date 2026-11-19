#!/usr/bin/env python3
"""Static qubit liveness for kmx circuits.

A qubit is dead from an unconditional HMR or R (which leave it in |0>) until the next op that writes it; an
unconditional SWAP of a live and a dead qubit moves the live interval. ``max_overlap`` is the peak number of qubits
live at the same time: a lower bound for the qubits a re-allocation of the same op sequence would need (input
register qubits are treated as live from the start).

    python liveness.py circuit.kmx [--input-register r0]

Licence: Apache-2.0.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kmsim  # noqa: E402

WRITE = {'X': [0], 'CX': [1], 'CCX': [2], 'SWAP': [0, 1], 'CSWAP': [1, 2]}


def intervals(ops, nq, xq):
    """Live intervals {qubit: [(start_op, end_op), ...]}; xq = qubits that hold input at the start."""
    zero = [q not in xq for q in range(nq)]
    start = [0] * nq
    depth = 0
    iv = {q: [] for q in range(nq)}
    for k, (n, qs, bs, c, a) in enumerate(ops):
        if n == 'PUSH_CONDITION':
            depth += 1
            continue
        if n == 'POP_CONDITION':
            depth -= 1
            continue
        uncond = depth == 0 and c is None
        if n in ('HMR', 'R') and uncond:
            q = qs[0]
            if not zero[q]:
                iv[q].append((start[q], k))
                zero[q] = True
            continue
        if n == 'SWAP' and uncond and zero[qs[0]] != zero[qs[1]]:
            a_, b_ = qs if not zero[qs[0]] else qs[::-1]  # a_ live, b_ zero
            iv[a_].append((start[a_], k))
            zero[a_] = True
            zero[b_] = False
            start[b_] = k
            continue
        for q in [qs[i] for i in WRITE.get(n, [])]:
            if zero[q]:
                zero[q] = False
                start[q] = k
    for q in range(nq):
        if not zero[q]:
            iv[q].append((start[q], len(ops)))
    return iv


def max_overlap(iv):
    """Peak number of simultaneously live intervals."""
    ev = sorted([(s, 1) for v in iv.values() for s, e in v] + [(e, -1) for v in iv.values() for s, e in v],
                key=lambda t: (t[0], t[1]))
    cur = mx = 0
    for t, d in ev:
        cur += d
        mx = max(mx, cur)
    return mx


def main(argv=None):
    ap = argparse.ArgumentParser(description="Peak static qubit liveness of a kmx circuit.")
    ap.add_argument("kmx", help="circuit in kmx text format (.kmx or .kmx.gz)")
    ap.add_argument("--input-register", action="append", default=None,
                    help="register id(s) holding input at the start (default: r0 if present); repeatable")
    a = ap.parse_args(argv)
    ops, regs = kmsim.parse(a.kmx)
    nq, _ = kmsim.sizes(ops, regs)
    names = a.input_register if a.input_register is not None else (["r0"] if "r0" in regs else [])
    xq = {q for r in names for q in regs.get(r, [])}
    iv = intervals(ops, nq, xq)
    peak = max_overlap(iv)
    print(f"qubits declared {nq}  peak live {peak}  input qubits {len(xq)}")
    return peak


if __name__ == "__main__":
    main()
