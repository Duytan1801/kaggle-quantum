#!/usr/bin/env python3
"""chem_shape.py — cost of the chemistry factorization SHAPE (R, B, C).

The chemistry score is

    score = lambda_eff * T_total * Q_total

and the state-preparation part of T and Q is a *heuristic* cost that depends
only on the SHAPE of the submitted factorization:

    T_stateprep = outer_state_prep() + inner_state_prep()   (SpinFreeData_V1)
    Q_stateprep = outer_persistent + inner_persistent
                  + max(outer_temp, inner_temp)

with N = 76, chi = 10, beta = brot.  The number of addresses is 76 + R*B,
so R*B is pinned by the loader family's address space (1219 for our
77-bank x 16-low layout, i.e. R*B = 1143) unless the whole loader family is
rebuilt.

This script sweeps the shape space and prints the cheapest options, so we
know whether the shape is a live lever before paying for a loader rebuild.

Usage: chem_shape.py [brot]
"""
from __future__ import annotations

import math
import pathlib
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/verifiers'))
from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1   # noqa: E402

N = 76
CHI = 10


def state_costs(R, B, C, brot):
    try:
        m = SpinFreeData_V1(R=R, B=B, C=C, N=N, chi=CHI, beta=brot)
        t = m.outer_state_prep() + m.inner_state_prep()
        qo = m.outer_state_prep_qubit_cost()
        qi = m.inner_state_prep_qubit_cost()
        q = (qo['persistent'] + qi['persistent']
             + max(qo['temp'], qi['temp']))
        return t, q, qo, qi
    except Exception as exc:                                  # noqa: BLE001
        return None, None, str(exc), None


def main():
    brot = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    print(f'brot={brot}  N={N} chi={CHI}   our shipped shape: R=9 B=127 C=46 '
          f'(R*B=1143, addresses 1219)')
    print()
    rows = []
    for RB in (1143,):
        # every factor split of R*B
        for R in range(1, RB + 1):
            if RB % R:
                continue
            B = RB // R
            for C in (1, 2, 4, 8, 16, 23, 32, 46, 64, 92, 128, 256):
                t, q, qo, qi = state_costs(R, B, C, brot)
                if t is None:
                    continue
                rows.append((t, q, R, B, C))
    rows.sort()
    print(f'{"T_state":>8s} {"Q_state":>8s} {"R":>5s} {"B":>6s} {"C":>5s} {"R*C":>7s}')
    for t, q, R, B, C in rows[:25]:
        print(f'{t:8d} {q:8d} {R:5d} {B:6d} {C:5d} {R * C:7d}')
    print()
    ours = [r for r in rows if r[2] == 9 and r[3] == 127 and r[4] == 46]
    if ours:
        t, q, R, B, C = ours[0]
        print(f'ours: T_state={t} Q_state={q}')
        best = rows[0]
        print(f'best: T_state={best[0]} Q_state={best[1]} at R={best[2]} B={best[3]} C={best[4]}')
        # projected score change (words would have to be rebuilt)
        T_old = 13166.0
        Q_old = 405.0
        for label, tt, qq in (('ours', t, q), ('best', best[0], best[1])):
            T_new = (T_old - 4550) + tt
            Q_new = (Q_old - 288) + qq + 82 + 35
            print(f'  {label}: T_total ~ {T_new:.0f}  Q_total ~ {Q_new:.0f}  '
                  f'score ratio {(T_old / T_new) * (Q_old / Q_new):.5f}  '
                  f'GM 33.21179 -> {33.21179 * ((T_old / T_new) * (Q_old / Q_new)) ** (-1 / 3):.5f}')

    print()
    print('--- also: other R*B (fewer addresses => smaller table, needs a loader rebuild) ---')
    rows2 = []
    for RB in (127, 255, 381, 511, 639, 767, 895, 1023, 1143, 1279, 1535, 2047):
        for R in (1, 3, 9, 27, 81, 127, 381, 1143):
            if RB % R:
                continue
            B = RB // R
            for C in (16, 32, 46, 64, 128):
                t, q, qo, qi = state_costs(R, B, C, brot)
                if t is None:
                    continue
                rows2.append((t, q, R, B, C, RB))
    rows2.sort()
    for t, q, R, B, C, RB in rows2[:20]:
        print(f'  R*B={RB:5d} T_state={t:6d} Q_state={q:5d}  R={R:5d} B={B:5d} C={C:4d}')


if __name__ == '__main__':
    raise SystemExit(main())
