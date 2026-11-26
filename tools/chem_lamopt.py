#!/usr/bin/env python3
"""chem_lamopt.py -- minimise Lambda's ENSEMBLE TERM by rotating the
ensemble basis of the chemistry factorization.

THE LEVER
    The chemistry score is  score = lambda_eff * T_total * Q_total  (LOWER is
    better) and  lambda_eff = sqrt(E_gap * (2*Lambda - E_gap)).

    The verifier's error metrics use the factorization's values in exactly
    two places per rank r:

        M_r = sum_c x_c x_c^T   (x_c = w[r,:,c])   -> error_2
        y_r = sum_c W_c x_c     (W_c = Wnative[r,c]) -> h1_prime

    Both are invariant under an orthogonal rotation of the ensemble basis
    (x' = x O, W' = W O^T), and so are error_1, error_2 and E_gap (the
    E_SOS term 1/2 sum_c W_c^2 is ||W||^2, rotation-invariant).  The WORDS
    do not move, so the ANGLE circuits and the loaders stay byte-identical
    -- only submission.npz changes.

    What moves is Lambda's ensemble term
        E_ens = 1/4 sum_(r,c) ( |H2_I[r,c]| + ||x[r,:,c]||_1 )^2 ,
    with H2_I[r,c] = W_c + sum_b x_c[b].  Since lambda_eff grows with
    Lambda, a SMALLER E_ens is a BETTER submission -- the same state, the
    same circuits, the same cost model, a smaller normalisation.

    Measured on our v149 factorization:  Lambda = 283.057 of which the
    INVARIANT part (sum_j |lambda_j|) is only 12.908 and the ensemble term
    is 270.149 (95 %).

    Note that every decomposition M_r = sum_c x_c x_c^T with C linearly
    independent vectors is reached by a rotation of the shipped one (both
    are factorisations of the same PSD matrix), so the rotation family
    searches the FULL space of ensemble bases.

THE SEARCH
    Coordinate descent over Givens rotations in the (c1,c2) planes of each
    rank, with a coarse grid then a local refinement.  The objective is
    piecewise smooth (L1), so a grid + refinement is the right tool.

Usage:
    chem_lamopt.py <npz> [--sweeps N] [--grid N] [--out FILE]
"""
from __future__ import annotations

import argparse
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/verifiers'))
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))

from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_angle_words  # noqa: E402

UPPER = -22140.27335


def native(w, h2i):
    return np.asarray(h2i, dtype=np.float64) - np.sum(np.asarray(w, dtype=np.float64), axis=1)


def rank_term(wr, h2r):
    """sum_c (|H2_I[r,c]| + ||x_c||_1)^2  for ONE rank"""
    l1 = np.abs(wr).sum(axis=0)
    return float(np.sum((np.abs(h2r) + l1) ** 2))


def apply_givens(wr, h2r, c1, c2, th):
    """rotate the ensemble basis of one rank in the (c1,c2) plane"""
    w2 = wr.copy()
    h2 = h2r.copy()
    x1 = w2[:, c1].copy()
    x2 = w2[:, c2].copy()
    w2[:, c1] = np.cos(th) * x1 + np.sin(th) * x2
    w2[:, c2] = -np.sin(th) * x1 + np.cos(th) * x2
    # W' = W O^T : in a 2-plane, (W1,W2) -> (W1 cos - W2 sin, W1 sin + W2 cos)
    W1 = h2[c1] - np.sum(x1)
    W2 = h2[c2] - np.sum(x2)
    nW1 = W1 * np.cos(th) - W2 * np.sin(th)
    nW2 = W1 * np.sin(th) + W2 * np.cos(th)
    h2[c1] = nW1 + np.sum(w2[:, c1])
    h2[c2] = nW2 + np.sum(w2[:, c2])
    return w2, h2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('npz', nargs='?',
                    default=str(ROOT / 'work/trees/v149/dfthcsos/submission.npz'))
    ap.add_argument('--sweeps', type=int, default=3)
    ap.add_argument('--grid', type=int, default=25)
    ap.add_argument('--brot', type=int, default=7)
    ap.add_argument('--out')
    ap.add_argument('--seed', type=int, default=3)
    args = ap.parse_args()

    p = pathlib.Path(args.npz)
    z = np.load(p)
    U, W, H2I = z['U'], z['W'], z['H2_I']
    R, B, C = W.shape
    words, edges = z['angle_words'], z['tree_edges']

    from dfthcsos.scoreinfra.reference import load_fixed_shifts
    from dfthcsos.verify import load_inputs
    inp = load_inputs({'U': U, 'W': W, 'H2_I': H2I, 'H1_I': z['H1_I'],
                       'Hsym_lower': z['Hsym_lower']})
    S, beta_1, ref = inp.S, inp.beta_1, inp.ref

    def metrics(w, h2i):
        Wn = native(w, h2i)
        return evaluate_dfthc_angle_words(words, np.asarray(w, dtype=np.float64),
                                          Wn, S, beta_1, ref, brot=args.brot,
                                          tree_edges=edges, energy_upper=UPPER)

    w = np.asarray(W, dtype=np.float64).copy()
    h2 = np.asarray(H2I, dtype=np.float64).copy()
    m0 = metrics(w, h2)
    term0 = sum(rank_term(w[r], h2[r]) for r in range(R)) / 4.0
    inv = m0['Lambda'] - term0
    print(f'{p.name}: R={R} B={B} C={C}')
    print(f'  Lambda = {m0["Lambda"]:.6f}   invariant {inv:.6f}   '
          f'ensemble term {term0:.6f}')
    print(f'  lambda_eff = {m0["lambda_eff"]:.6f}  E_gap = {m0["E_gap"]:.12f}')
    print(f'  error_1 = {m0["error_1"]:.12f}  error_2 = {m0["error_2"]:.12f}')

    rng = np.random.default_rng(args.seed)
    grid = np.linspace(-np.pi / 2, np.pi / 2, args.grid)
    t0 = time.time()
    for sweep in range(args.sweeps):
        improved = 0
        for r in range(R):
            for c1 in range(C):
                for c2 in range(c1 + 1, C):
                    cur = rank_term(w[r], h2[r])
                    best_val, best_th = cur, 0.0
                    for th in grid:
                        w2, h2b = apply_givens(w[r], h2[r], c1, c2, th)
                        v = rank_term(w2, h2b)
                        if v < best_val - 1e-13:
                            best_val, best_th = v, th
                    if best_val < cur - 1e-13:
                        # local refinement
                        lo, hi = best_th - np.pi / args.grid, best_th + np.pi / args.grid
                        for _ in range(3):
                            for th in np.linspace(lo, hi, 9):
                                w2, h2b = apply_givens(w[r], h2[r], c1, c2, th)
                                v = rank_term(w2, h2b)
                                if v < best_val - 1e-13:
                                    best_val, best_th = v, th
                            step = (hi - lo) / 6.0
                            lo, hi = best_th - step, best_th + step
                        w[r], h2[r] = apply_givens(w[r], h2[r], c1, c2, best_th)
                        improved += 1
        term = sum(rank_term(w[r], h2[r]) for r in range(R)) / 4.0
        print(f'  sweep {sweep}: {improved} planes improved, '
              f'ensemble term {term:.6f}  ({time.time()-t0:.0f}s)', flush=True)
        if improved == 0:
            break

    m1 = metrics(w, h2)
    print()
    print('  metrics after the rotation:')
    for k in ('error_1', 'error_2', 'Lambda', 'E_SOS', 'E_gap', 'lambda_eff'):
        print(f'    {k:12s} {m0[k]:.12f}  ->  {m1[k]:.12f}')
    ok = (m1['error_1'] <= 0.020 and m1['error_2'] <= 0.020
          and m1['gap_in_domain'] and m1['E_gap'] > 3.914898 and m1['Lambda'] > 49.0)
    print(f'    gates: {"PASS" if ok else "FAIL"}')

    T, Q = 13166.0, 405
    s0 = m0['lambda_eff'] * T * Q
    s1 = m1['lambda_eff'] * T * Q
    print(f'    score {s0:,.0f} -> {s1:,.0f}   '
          f'dGM = {33.21179/3 * (s0/s1 - 1):+.5f} GM')

    if args.out:
        o = pathlib.Path(args.out)
        np.savez(o, U=U, W=w, H2_I=h2, H1_I=z['H1_I'],
                 Hsym_lower=z['Hsym_lower'], tree_edges=edges,
                 angle_words=words)
        print(f'  wrote {o}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
