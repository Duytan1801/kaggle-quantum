#!/usr/bin/env python3
"""scratch_s_map.py — is each scratch wire a function of s (leading zero pair count)?

If a wire's value is determined by s alone, it belongs to the s-encoding and could be
re-encoded (s has only 12 values).  Otherwise it carries independent information.

Usage: scratch_s_map.py <circuit.kmx> <op>
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, '/tmp/opencode/recon/datasets/vqcc-tools-0.1.0/scripts')
import numpy as np
import qhdl_bitsim as B


def s_of_x(x: np.ndarray) -> np.ndarray:
    """s = number of LEADING zero pairs of the 22-bit x (pairs from the top).

    s=0 -> x >= 2^20 ; s=1 -> 2^18 <= x < 2^20 ; ... s=10 -> 1 <= x < 4.
    """
    pairs = [(21, 20), (19, 18), (17, 16), (15, 14), (13, 12), (11, 10), (9, 8), (7, 6), (5, 4), (3, 2), (1, 0)]
    s = np.zeros(len(x), dtype=np.int64)
    still = np.ones(len(x), dtype=bool)
    for hi, lo in pairs:
        pz = (((x >> hi) & 1) == 0) & (((x >> lo) & 1) == 0)
        s += (pz & still).astype(np.int64)
        still &= pz
    return s


def main() -> None:
    path, op_at = pathlib.Path(sys.argv[1]), int(sys.argv[2])
    ops, header, xq, nq = B.load(str(path))
    sim = B.BitSim(ops, rows=None, num_qubits=nq, x_qubits=list(xq), outcome='zero')
    state = {}

    def snap(i, s):
        if i == op_at:
            for q in range(nq):
                state[q] = B.unpack_bits(s.q[q], s.n).copy()

    sim.run(stop=op_at + 1, snaps=[op_at], on_snap=snap)
    x = sim.rows
    s = s_of_x(x)
    print(f'op {op_at}: s distribution (count per s value):')
    cnt = np.bincount(s, minlength=12)
    for k, c in enumerate(cnt):
        print(f'   s={k:>2}: {c:>9}  x in [{1 << max(0, 20-2*k)}, {1 << (22-2*k)})')
    print()
    print('wire  ones%   function-of-s?   s->value map (only if determined)')
    for q in range(nq):
        v = state.get(q)
        if v is None:
            continue
        # for each s value, check the wire is constant
        determined = True
        mapping = {}
        for k in range(12):
            m = s == k
            if not m.any():
                continue
            vals = v[m]
            u = np.unique(vals)
            if len(u) > 1:
                determined = False
                break
            mapping[k] = int(u[0])
        tag = 'reg' if q in set(xq) else 'scr'
        if determined:
            print(f'  q{q:<3} {tag} {100*v.mean():5.1f}%  YES   {mapping}')
        else:
            print(f'  q{q:<3} {tag} {100*v.mean():5.1f}%  no')


if __name__ == '__main__':
    main()
