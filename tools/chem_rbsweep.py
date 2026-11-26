#!/usr/bin/env python3
"""chem_rbsweep.py -- the cost of every (R, B, C) SHAPE with R*B = 1143.

THE LEVER
    The chemistry score is  score = lambda_eff * T_total * Q_total  (LOWER is
    better) and the *heuristic* part of T and Q is a pure function of the
    factorization SHAPE (R, B, C) -- see
    work/toolchain/verifiers/dfthcsos/scoreinfra/costs_prepare.py:

        T_state = outer_state_prep() + inner_state_prep()
        Q_state = outer_persistent + inner_persistent + max(outer_temp, inner_temp)
        T_givens = givens_rotations()

    The ANGLE part (T = 6666, Q_persistent = 35, Q_temp = 82) is the shipped
    loader family and does NOT depend on the shape.

    The address space is N + R*B = 76 + 1143 = 1219, so R*B is pinned at 1143
    (the loader family must cover exactly those addresses) -- but the SPLIT
    between R and B is free, and the cost model treats R and B very
    differently:
      * the outer state prep sees X_o = N + R*C  (so it likes a SMALL R),
      * the inner state prep sees L = R*C*B    (so it likes a SMALL R*C*B),
      * b2 = ceil(log2 B) + chi + 1           (so it likes a SMALL B),
      * the Givens count depends on N and the tree, not on R/B.

    So a different split of 1143 into R x B may be CHEAPER at the same
    lambda_eff.  This script enumerates every (R, B) with R*B = 1143 (and a
    few nearby shapes for reference) and prints the implied score at the
    shipped lambda_eff.

Usage: chem_rbsweep.py [brot]
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/verifiers')

from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1  # noqa: E402

N = 76
CHI = 10
LAM = 46.91432538757801
ANG_T = 6666.0
ANG_PERS = 35
ANG_TEMP = 82
GM0 = 33.21179


def divisors(n):
    out = []
    for d in range(1, int(n ** 0.5) + 1):
        if n % d == 0:
            out.append(d)
            if d != n // d:
                out.append(n // d)
    return sorted(out)


def main() -> int:
    brot = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    RB = 1143
    C = 46
    print(f'brot={brot}  N={N} chi={CHI}  R*B={RB} (addresses {N+RB})  '
          f'shipped shape R=9 B=127 C=46')
    print()
    print(f'{"R":>4s} {"B":>5s} {"C":>4s} {"T_state":>8s} {"T_giv":>7s} '
          f'{"T_total":>8s} {"pers":>5s} {"temp":>5s} {"Q_total":>7s} '
          f'{"score":>14s} {"dGM":>8s}')
    rows = []
    for R in divisors(RB):
        B = RB // R
        for Cc in (C,):
            try:
                m = SpinFreeData_V1(R=R, B=B, C=Cc, N=N, chi=CHI, beta=brot)
                t = m.outer_state_prep() + m.inner_state_prep()
                gv = m.givens_rotations()
                qo = m.outer_state_prep_qubit_cost()
                qi = m.inner_state_prep_qubit_cost()
                pers = qo['persistent'] + qi['persistent']
                tmp = max(qo['temporary'], qi['temporary'])
                T = ANG_T + t + gv
                persistent = pers + ANG_PERS
                Qtot = persistent + max(tmp, ANG_TEMP)
                sc = LAM * T * Qtot
                rows.append((R, B, Cc, t, gv, T, pers, tmp, Qtot, sc))
            except Exception as e:
                print(f'{R:4d} {B:5d} {Cc:4d}  EXC {type(e).__name__}: {e}')
    rows.sort(key=lambda r: r[9])
    for R, B, Cc, t, gv, T, pers, tmp, Qtot, sc in rows:
        star = ' <== shipped' if (R, B, Cc) == (9, 127, 46) else ''
        print(f'{R:4d} {B:5d} {Cc:4d} {t:8d} {gv:7d} {T:8.0f} {pers:5d} '
              f'{tmp:5d} {Qtot:7d} {sc:14,.0f} '
              f'{GM0/3*(250157973.2614051/sc-1):+8.4f}{star}')
    print()
    print('--- the same sweep for the C that each shape would allow ---')
    print('    (C_min = max_r rank(M_r); for a NEW factorization it is unknown)')
    for R, B, Cc, t, gv, T, pers, tmp, Qtot, sc in rows[:6]:
        print(f'  R={R:4d} B={B:5d}: ', end='')
        line = []
        for C2 in (8, 16, 23, 32, 46, 64, 92):
            try:
                m = SpinFreeData_V1(R=R, B=B, C=C2, N=N, chi=CHI, beta=brot)
                t2 = m.outer_state_prep() + m.inner_state_prep()
                gv2 = m.givens_rotations()
                qo = m.outer_state_prep_qubit_cost()
                qi = m.inner_state_prep_qubit_cost()
                p2 = qo['persistent'] + qi['persistent']
                tm2 = max(qo['temporary'], qi['temporary'])
                T2 = ANG_T + t2 + gv2
                Q2 = p2 + ANG_PERS + max(tm2, ANG_TEMP)
                line.append(f'C={C2}: {LAM*T2*Q2:,.0f}')
            except Exception:
                line.append(f'C={C2}: EXC')
        print('  '.join(line))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
