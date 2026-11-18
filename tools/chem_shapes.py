#!/usr/bin/env python3
"""chem_shapes.py — inventory factorizations and score them with the OFFICIAL cost model.

For every candidate factorization (an .npz with the DF-THC arrays), report:
  * the shape (R, B, C) and the row count 76 + R*B,
  * the official `T_total` and `Q_total` (SpinFreeData_V1 + the angles' own cost),
  * the resulting ratio against the official reference 3_355_599_588.3155375.

The angles' Toffoli count is estimated from the number of rows and bits, and can
be overridden with --angles-toffoli (the measured value of the loaders).
"""
from __future__ import annotations

import argparse
import glob
import json
import math
import os
import sys

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/verifiers')

from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1  # noqa: E402

REF_CHEM = 3_355_599_588.3155375
N_ORBITALS = 76
KEEP_BITS = 10


def heuristic_costs(R: int, B: int, C: int, brot: int) -> dict:
    model = SpinFreeData_V1(R=R, B=B, C=C, N=N_ORBITALS, chi=KEEP_BITS, beta=brot)
    outer = model.outer_state_prep()
    inner = model.inner_state_prep()
    givens = model.givens_rotations()
    outer_q = model.outer_state_prep_qubit_cost()
    inner_q = model.inner_state_prep_qubit_cost()
    return {
        'outer': outer, 'inner': inner, 'givens': givens,
        'toffoli': outer + inner + givens,
        'outer_persistent': outer_q['persistent'], 'inner_persistent': inner_q['persistent'],
        'outer_temp': outer_q['temporary'], 'inner_temp': inner_q['temporary'],
    }


def total_costs(R: int, B: int, C: int, brot: int, J: int, angles_toffoli: int,
                angles_temp: int = 77) -> dict:
    h = heuristic_costs(R, B, C, brot)
    T = h['toffoli'] + angles_toffoli
    persistent = h['outer_persistent'] + h['inner_persistent'] + J * brot
    temporary = max(h['outer_temp'], h['inner_temp'], angles_temp)
    Q = persistent + temporary
    return {**h, 'T_total': T, 'Q_total': Q, 'persistent': persistent,
            'temporary': temporary, 'rows': N_ORBITALS + R * B}


def ratio(T: int, Q: int, lam: float) -> float:
    return REF_CHEM / (lam * T * Q)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--brot', type=int, default=8)
    ap.add_argument('--J', type=int, default=5)
    ap.add_argument('--lam', type=float, default=46.92171681802857)
    ap.add_argument('--angles-toffoli', type=int, default=8044)
    ap.add_argument('--angles-temp', type=int, default=77)
    ap.add_argument('--grid', action='store_true')
    args = ap.parse_args()

    if args.grid:
        print(f'grid: brot={args.brot} J={args.J} lam={args.lam} angles_toffoli={args.angles_toffoli}')
        print(f'{"R":>4}{"B":>5}{"C":>4}{"rows":>7}{"T":>8}{"Q":>6}{"ratio":>10}'
              f'{"innerT":>8}{"in_temp":>9}')
        best = []
        for R in (4, 5, 6, 7, 8, 9, 10, 12, 13, 14, 16, 18, 20, 24, 26, 30):
            for B in (30, 40, 50, 60, 80, 100, 120, 143, 160, 180, 255):
                for C in (20, 25, 30, 35, 40, 44, 45, 46, 50, 60, 80, 90, 128):
                    try:
                        c = total_costs(R, B, C, args.brot, args.J,
                                         args.angles_toffoli, args.angles_temp)
                    except (ValueError, ZeroDivisionError):
                        continue
                    r = ratio(c['T_total'], c['Q_total'], args.lam)
                    best.append((r, R, B, C, c))
        best.sort(reverse=True)
        for r, R, B, C, c in best[:35]:
            print(f'{R:>4}{B:>5}{C:>4}{c["rows"]:>7}{c["T_total"]:>8}{c["Q_total"]:>6}'
                  f'{r:>10.3f}{c["inner"]:>8}{c["inner_temp"]:>9}')
        return

    print('=== inventory of candidate factorizations ===')
    for path in sorted(glob.glob(sys.argv[1] if len(sys.argv) > 1 else '/tmp/opencode/**/*.npz',
                                 recursive=True)):
        try:
            import numpy as np
            d = np.load(path, allow_pickle=False)
            keys = list(d.files)
            U = d['U'] if 'U' in keys else None
            if U is None:
                print(f'{os.path.basename(path):<34} keys={keys[:8]} (no U)')
                continue
            R, B, _ = U.shape
            C = d['W'].shape[-1] if 'W' in keys else 0
            words = None
            for k in ('words', 'angle_words', 'two_body_words'):
                if k in keys:
                    words = d[k]
                    break
            nw = None if words is None else (words.shape, int(words.max()) if words.size else 0)
            try:
                c = total_costs(R, B, C, args.brot, args.J, args.angles_toffoli, args.angles_temp)
                r = ratio(c['T_total'], c['Q_total'], args.lam)
                cost = f'T={c["T_total"]:>6} Q={c["Q_total"]:>4} rows={c["rows"]:>5} ratio={r:>8.3f}'
            except (ValueError, ZeroDivisionError) as exc:
                cost = f'cost-model error: {exc}'
            print(f'{os.path.basename(path):<34} R={R:<3} B={B:<4} C={C:<4} {cost}')
            if nw:
                print(f'{"":<34} words shape={nw[0]} max_word={nw[1]}')
        except Exception as exc:  # noqa: BLE001
            print(f'{os.path.basename(path):<34} ERROR {exc}')


if __name__ == '__main__':
    main()
