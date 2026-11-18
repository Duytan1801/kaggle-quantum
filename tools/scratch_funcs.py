#!/usr/bin/env python3
"""scratch_funcs.py — identify the Boolean function each long-lived scratch wire holds.

At a given op the circuit's state is a deterministic function of x (zero measurement
branch).  We simulate all 3,133,452 legal x bit-parallel with QHDL's bitsim and read
every scratch wire, then try to name each wire's function:

  * threshold      [x < 2^k]  or  [x >= 2^k]
  * band           [2^a <= x < 2^b]
  * unary-of-s     [s == k]  / [s >= k]   (s = leading zero *pair* count of x)
  * single x bit   [bit j of x]
  * xor of x bits

Usage: scratch_funcs.py <circuit.kmx> <op> [--rows N]
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, '/tmp/opencode/recon/datasets/vqcc-tools-0.1.0/scripts')
import numpy as np
import qhdl_bitsim as B


def s_of_x(x: np.ndarray) -> np.ndarray:
    """leading zero pair count of a 22-bit x (pairs from the top)."""
    pairs = [(21, 20), (19, 18), (17, 16), (15, 14), (13, 12), (11, 10), (9, 8), (7, 6), (5, 4), (3, 2), (1, 0)]
    s = np.zeros_like(x)
    for hi, lo in pairs:
        pair_zero = ((x >> hi) & 1) == 0
        pair_zero &= ((x >> lo) & 1) == 0
        s = s + (~pair_zero).astype(s.dtype) * (s == 0)
    return s


def main() -> None:
    path = pathlib.Path(sys.argv[1])
    op_at = int(sys.argv[2])
    rows = None
    if '--rows' in sys.argv:
        rows = int(sys.argv[sys.argv.index('--rows') + 1])
    ops, header, xq, nq = B.load(str(path))
    sim = B.BitSim(ops, rows=rows, num_qubits=nq, x_qubits=list(xq), outcome='zero')
    state = {}

    def snap(i, s):
        if i == op_at:
            for q in range(nq):
                state[q] = B.unpack_bits(s.q[q], s.n).copy()

    sim.run(stop=op_at + 1, snaps=[op_at], on_snap=snap)
    x = sim.rows
    n = len(x)
    print(f'op {op_at}: {n} rows, nq={nq}')
    s = s_of_x(x)
    thresh = {}
    for k in range(0, 23):
        thresh[k] = (x < (1 << k))
    bands = {}
    for a in range(0, 23):
        for b in range(a + 1, 24):
            bands[(a, b)] = (x >= (1 << a)) & (x < (1 << b))
    xbits = {j: ((x >> j) & 1).astype(bool) for j in range(22)}
    for q in range(nq):
        v = state.get(q)
        if v is None:
            continue
        name = None
        ones = int(v.sum())
        if ones == 0:
            name = 'constant 0'
        elif ones == n:
            name = 'constant 1'
        else:
            for k, t in thresh.items():
                if np.array_equal(v, t):
                    name = f'threshold [x < 2^{k}]'
                    break
            if name is None:
                for (a, b), t in bands.items():
                    if np.array_equal(v, t):
                        name = f'band [2^{a} <= x < 2^{b}]'
                        break
            if name is None:
                for k in range(12):
                    if np.array_equal(v, s == k):
                        name = f'unary-of-s [s == {k}]'
                        break
                    if np.array_equal(v, s >= k):
                        name = f'unary-of-s [s >= {k}]'
                        break
            if name is None:
                for j, t in xbits.items():
                    if np.array_equal(v, t):
                        name = f'x bit {j}'
                        break
            if name is None:
                name = 'complex'
        tag = 'register' if q in set(xq) else 'scratch'
        print(f'  q{q:<3} {tag:8} ones={ones:>9} ({100*ones/n:5.1f}%)  {name}')


if __name__ == '__main__':
    main()
