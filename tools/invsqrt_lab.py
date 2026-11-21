#!/usr/bin/env python3
"""invsqrt_lab.py — score-aware experiments on the invsqrt rotation basis.

WHY
    The minimax LP says the CURRENT 33 priced angles are already optimal inside
    their own span (max min_margin = 36,584,657 units, no improvement).  But
    the score is not only the margin:

        score = Q * (toffoli + t/4 + n_rot * (0.56*log2(1/eps)+5.3)/4)
        eps   = pi * min_margin / 2^64 / n_rot

    so a rotation is worth keeping only if it buys more margin than it costs.
    Two families of experiments:

      DROP  : remove one priced rotation (n_rot 33 -> 32) and re-optimise the
              remaining 32.  Wins if the margin stays above 32/33 of the old
              one (the eps then improves).
      ADD   : add k NEW rotations on the x-register wires (Z_POW on x_i is the
              bit indicator bit_i(x); the x bits are available at the very top
              of the circuit and Z_POW does not disturb the register, so this
              is a legal circuit edit).  The new columns enlarge the span and
              may buy a much bigger margin.

    Every experiment reports the resulting SCORE, not just the margin.

Usage:  python invsqrt_lab.py <sens.npz>
"""
from __future__ import annotations

import math
import sys

import numpy as np
from scipy.optimize import linprog

MASK64 = (1 << 64) - 1
MAX_X = 3133452
Q = 37
TOFFOLI = 1406.311400272666
T_BASE = 8.498471040726292
CURRENT_MARGIN = 36584657


def score_for(m, nrot, toffoli=TOFFOLI, t=T_BASE, q=Q):
    eps = math.pi * m / 2 ** 64 / nrot
    rot_t = 0.56 * math.log2(1 / eps) + 5.3
    teq = toffoli + t / 4 + nrot * rot_t / 4
    return q * teq, eps, rot_t


def zpow_class(u):
    u = int(u) & MASK64
    if u % (1 << 62) == 0:
        return 'clifford'
    if u % (1 << 61) == 0:
        return 't'
    return 'rotation'


def solve_lp(Vcols, err, tol, iters=12, active=5000, max_active=400000):
    """Constraint-generation Chebyshev LP.

    Vcols : (ncol, MAX_X) bool  -- the basis functions (phase indicators)
    err   : (MAX_X,) int64      -- current signed error
    tol   : (MAX_X,) int64      -- official tolerance
    returns (m, du, n_active)

    Everything is SCALED by max|err| before it reaches HiGHS: after deleting a
    rotation the error can be ~1 turn (2^64 units) while the tolerance is ~1e9
    units, and that dynamic range makes the raw LP unusable.
    """
    scale = max(1.0, float(np.abs(err).max()))
    err = err.astype(np.float64) / scale
    tol = tol.astype(np.float64) / scale
    ncol = Vcols.shape[0]
    margins = tol - np.abs(err)
    act = np.argsort(margins)[:active].copy()
    c = np.zeros(ncol + 1)
    c[-1] = -1.0
    bounds = [(None, None)] * ncol + [(None, None)]
    best = None
    for it in range(iters):
        rows = []
        rhs = []
        for x in act:
            v = Vcols[:, x].astype(np.float64)
            rows.append(np.concatenate([v, [1.0]]))
            rhs.append(float(tol[x] - err[x]))
            rows.append(np.concatenate([-v, [1.0]]))
            rhs.append(float(tol[x] + err[x]))
        A = np.asarray(rows, dtype=np.float64)
        b = np.asarray(rhs, dtype=np.float64)
        res = linprog(c, A_ub=A, b_ub=b, bounds=bounds, method='highs')
        if not res.success:
            return None, None, it
        du = np.asarray(res.x[:ncol])
        m = float(res.x[-1])
        # scan
        worst_min = None
        viol = []
        chunk = 100000
        for x0 in range(0, MAX_X, chunk):
            x1 = min(x0 + chunk, MAX_X)
            acc = err[x0:x1].astype(np.float64)
            for j in range(ncol):
                if du[j]:
                    acc += Vcols[j, x0:x1] * du[j]
            mm = tol[x0:x1] - np.abs(acc)
            worst_min = float(mm.min()) if worst_min is None else min(worst_min, float(mm.min()))
            bad = np.flatnonzero(mm < m - 1.0)
            if len(bad):
                viol.extend((x0 + bad).tolist())
        if best is None or (worst_min is not None and worst_min > best[0]):
            best = (worst_min if worst_min is not None else -1e30, du)
        if not viol:
            break
        act = np.unique(np.concatenate([act, np.array(sorted(set(viol)), dtype=np.int64)]))
        if len(act) > max_active:
            act = act[-max_active:]
    if best is None:
        return None, None, iters
    return best[0] * scale, best[1] * scale, len(act)


def main():
    d = np.load(sys.argv[1], allow_pickle=True)
    V = d['V']
    err = d['err'].astype(np.int64)
    tol = d['tol'].astype(np.int64)
    units = d['units']
    classes = [zpow_class(u) for u in units]
    priced = [k for k, c in enumerate(classes) if c == 'rotation']
    print(f'{len(priced)} priced rotations, current margin {CURRENT_MARGIN:,}')

    base_score, base_eps, _ = score_for(CURRENT_MARGIN, len(priced))
    print(f'current score {base_score:,.2f} (eps {base_eps:.4e})')

    # ---- bit basis: bit_i(x) for the 22 x-register wires
    xs = np.arange(1, MAX_X + 1, dtype=np.uint64)
    bits = np.stack([((xs >> i) & 1).astype(bool) for i in range(22)])
    print(f'bit basis built: {bits.shape}')

    # ---- DROP experiments
    print('\n=== DROP one priced rotation (n_rot 33 -> 32) ===')
    drops = []
    for skip in priced:
        cols = [k for k in priced if k != skip]
        Vc = V[cols, :]
        m, du, na = solve_lp(Vc, err, tol, iters=8, active=4000)
        if m is None:
            print(f'  drop rot {skip}: LP failed')
            continue
        sc, eps, _ = score_for(m, 32)
        drops.append((sc, skip, m, eps))
        print(f'  drop rot {skip:>2}: margin {m:>14,.0f} (x{ m / CURRENT_MARGIN:6.2f}) '
              f'eps {eps:.4e} score {sc:,.2f} ({sc - base_score:+,.2f})')
    drops.sort()
    if drops:
        print(f'  BEST DROP: rot {drops[0][1]} score {drops[0][0]:,.2f} ({drops[0][0] - base_score:+,.2f})')

    # ---- ADD experiments: 33 priced + k bit columns
    print('\n=== ADD k bit-basis rotations (n_rot 33 -> 33+k) ===')
    Vp = V[priced, :]
    for k in (1, 2, 3, 4, 6, 8, 12, 16, 22):
        Vc = np.concatenate([Vp, bits[:k]], axis=0)
        m, du, na = solve_lp(Vc, err, tol, iters=8, active=4000)
        if m is None:
            print(f'  add {k}: LP failed')
            continue
        sc, eps, _ = score_for(m, 33 + k)
        print(f'  add {k:>2}: margin {m:>14,.0f} (x{ m / CURRENT_MARGIN:8.2f}) '
              f'eps {eps:.4e} score {sc:,.2f} ({sc - base_score:+,.2f})')


if __name__ == '__main__':
    main()
