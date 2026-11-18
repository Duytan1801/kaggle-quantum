#!/usr/bin/env python3
"""live_overlap.py — per-qubit live intervals (first touch -> last touch) and the
minimum number of physical wires needed (interval-graph colouring).

If min_wires < circuit.num_qubits, the circuit can be RENUMBERED onto fewer physical
qubits with identical semantics — a pure relabeling win:
  invsqrt score = num_qubits * toffoli_equivalent   (-1 qubit = +1/44 = +2.27% cost)
  dqi     score = rep * num_qubits**2 * toffolis     (-1 qubit = +0.225% cost)

Usage: live_overlap.py <circuit.kmx> [n_x_input_qubits]
"""
import sys
import numpy as np

sys.path.insert(0, '/tmp/opencode/recon/datasets/asteriospanoras_qcc-circuit-atlas/tools')
from qccscope import kmx  # noqa: E402

CX, CCX, CSWAP, CZ, CCZ, X, Z, SWAP, ZPOW, HMR, R, NEG, BINV, BST0, BST1, PUSH, POP, INFO, DBG = range(19)


def intervals_of(path):
    c = kmx.load(path)
    nq = c.num_qubits
    n = len(c.op)
    first = np.full(nq, n, dtype=np.int64)   # sentinel = never touched
    last = np.full(nq, -1, dtype=np.int64)
    OP = c.op; A = c.a; B = c.b; Cc = c.c
    # vectorised first-touch: first op index where each wire appears
    for arr in (A, B, Cc):
        mask = arr >= 0
        idx = np.where(mask)[0]
        vals = arr[mask]
        # first occurrence
        order = np.argsort(vals, kind='stable')
        v_sorted = vals[order]; i_sorted = idx[order]
        uniq, starts, counts = np.unique(v_sorted, return_index=True, return_counts=True)
        f = i_sorted[starts]
        l = i_sorted[starts + counts - 1]
        np.minimum.at(first, uniq, f)
        np.maximum.at(last, uniq, l)
    return c, first, last


def min_wires(first, last):
    """Greedy colouring of interval graph: sweep events."""
    nq = len(first)
    events = []
    for q in range(nq):
        if last[q] < 0:
            continue
        events.append((first[q], 1, q))
        events.append((last[q] + 1, -1, q))
    events.sort()
    active = {}
    peak = 0
    # classic: at each start, assign a free wire
    free = list(range(nq))
    assign = {}
    used = 0
    for t, kind, q in events:
        if kind == 1:
            # reuse a wire whose interval ended
            for w in list(free):
                if w in assign and assign[w][1] < t:
                    free.append(free.pop(free.index(w)))  # no-op placeholder
            # simpler: maintain per-wire end
            if not free:
                used += 1
                free.append(used - 1)
            w = free.pop(0)
            assign[w] = (q, last[q])
            active[w] = q
            peak = max(peak, len(assign))
        else:
            w = None
            for k, (qq, ll) in list(assign.items()):
                if qq == q:
                    w = k
                    break
            if w is not None:
                del assign[w]
                free.append(w)
    return peak, used + 1


def max_overlap(first, last):
    """Maximum number of simultaneously live wires (sweep line)."""
    events = []
    for q in range(len(first)):
        if last[q] < 0:
            continue
        events.append((first[q], 1))
        events.append((last[q] + 1, -1))
    events.sort()
    cur = peak = 0
    for t, d in events:
        cur += d
        peak = max(peak, cur)
    return peak


def main():
    path = sys.argv[1]
    c, first, last = intervals_of(path)
    nq = c.num_qubits
    used = int((last >= 0).sum())
    ov = max_overlap(first, last)
    print(f'file: {path}')
    print(f'  declared num_qubits: {nq}   ops: {len(c.op)}   wires touched: {used}')
    print(f'  max simultaneous LIVE wires (interval overlap): {ov}')
    if ov < nq:
        print(f'  => RENUMBERING WIN: {nq} -> {ov} physical wires '
              f'(+{100*(nq-ov)/nq:.2f}% on the invsqrt/dqi cost factor)')
    # list the longest-lived wires and the overlap profile
    order = np.argsort(-(last - first))
    print('  longest-lived wires (wire, first, last, span):',
          [(int(q), int(first[q]), int(last[q]), int(last[q] - first[q])) for q in order[:10]])
    # where does the peak occur?
    ev = []
    for q in range(nq):
        if first[q] >= 0:
            ev.append((first[q], 1)); ev.append((last[q] + 1, -1))
    ev.sort()
    cur = 0; peak = 0; peak_t = None
    for t, d in ev:
        cur += d
        if cur > peak:
            peak = cur; peak_t = t
    print(f'  peak overlap {peak} first reached at op {peak_t}')


if __name__ == '__main__':
    main()
