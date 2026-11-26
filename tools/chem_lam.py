#!/usr/bin/env python3
"""chem_lam.py -- the ENSEMBLE-BASIS lever on Lambda (and hence lambda_eff).

WHY THIS EXISTS
    The chemistry score is  score = lambda_eff * T_total * Q_total  (LOWER is
    better) and  lambda_eff = sqrt(E_gap * (2*Lambda - E_gap)).

    The verifier's metrics use the factorization's values in exactly two
    places per rank r (work/tools/chem_ens.py):

        M_r = sum_c x_c x_c^T      (x_c = w[r,:,c])      -> error_2
        y_r = sum_c W_c x_c        (W_c = Wnative[r,c])   -> h1_prime

    Both are INVARIANT under an orthogonal rotation of the ensemble basis
        x'_c = sum_d O_cd x_d ,  W' = W O^T ,  O orthogonal,
    and E_SOS's W-term  (1/2 sum_c W_c^2) is invariant too, so E_gap does
    not move.  The errors do not move.  The WORDS do not move, so the ANGLE
    circuits and the loaders stay byte-identical.

    What DOES move is Lambda's ensemble term
        1/4 sum_(r,c) ( |H2_I[r,c]| + sum_b |w[r,b,c]| )^2 ,
    with H2_I[r,c] = W_c + sum_b x_c[b].  Since lambda_eff grows with
    Lambda, a SMALLER Lambda is a BETTER submission -- and the same state,
    the same cost model and the same circuits.

    This tool
      1. splits Lambda into its invariant part (sum_j |lambda_j|) and the
         movable ensemble term,
      2. reports the floor (the invariant part),
      3. searches for a better ensemble basis per rank (random rotations +
         coordinate descent), evaluating the TRUE Lambda each time with the
         official metric code.

Usage:
    chem_lam.py <npz> [--rounds N] [--seed S] [--eval-only]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/verifiers'))
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))

from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_angle_words  # noqa: E402

N = 76
UPPER = -22140.27335


def native(w, h2i):
    return np.asarray(h2i, dtype=np.float64) - np.sum(np.asarray(w, dtype=np.float64), axis=1)


def eval_metrics(w, h2i, words, edges, S, beta_1, ref, brot):
    Wn = native(w, h2i)
    return evaluate_dfthc_angle_words(words, np.asarray(w, dtype=np.float64),
                                      Wn, S, beta_1, ref, brot=brot,
                                      tree_edges=edges, energy_upper=UPPER)


def ensemble_term(w, h2i):
    """1/4 sum_(r,c) (|H2_I[r,c]| + sum_b |w[r,b,c]|)^2"""
    w = np.asarray(w)
    h2i = np.asarray(h2i)
    t = 0.0
    for r in range(w.shape[0]):
        for c in range(w.shape[2]):
            t += (abs(h2i[r, c]) + np.abs(w[r, :, c]).sum()) ** 2
    return t / 4.0


def rotate(w, h2i, O):
    """apply a per-rank orthogonal rotation O (R,C,C) to the ensemble basis"""
    w = np.asarray(w, dtype=np.float64)
    h2i = np.asarray(h2i, dtype=np.float64)
    Wn = native(w, h2i)
    w2 = np.einsum('rbc,rcd->rbd', w, O)
    W2 = np.einsum('rc,rcd->rd', Wn, O)          # W' = W O^T
    h2i2 = W2 + np.sum(w2, axis=1)
    return w2, h2i2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('npz', nargs='?',
                    default=str(ROOT / 'work/trees/v149/dfthcsos/submission.npz'))
    ap.add_argument('--rounds', type=int, default=200)
    ap.add_argument('--seed', type=int, default=7)
    ap.add_argument('--brot', type=int, default=7)
    ap.add_argument('--out')
    ap.add_argument('--eval-only', action='store_true')
    args = ap.parse_args()

    p = pathlib.Path(args.npz)
    z = np.load(p)
    U, W, H2I = z['U'], z['W'], z['H2_I']
    R, B, C = W.shape
    words, edges = z['angle_words'], z['tree_edges']

    # the fixed shifts and beta_1
    from dfthcsos.scoreinfra.reference import load_fixed_shifts
    from dfthcsos.verify import load_inputs
    inp = load_inputs({'U': U, 'W': W, 'H2_I': H2I, 'H1_I': z['H1_I'],
                       'Hsym_lower': z['Hsym_lower']})
    S, beta_1, ref = inp.S, inp.beta_1, inp.ref

    m = eval_metrics(W, H2I, words, edges, S, beta_1, ref, args.brot)
    et = ensemble_term(W, H2I)
    inv_part = m['Lambda'] - et
    print(f'{p.name}: R={R} B={B} C={C}')
    print(f'  Lambda          = {m["Lambda"]:.6f}')
    print(f'  invariant part  = {inv_part:.6f}   (sum_j |lambda_j|; cannot move)')
    print(f'  ensemble term   = {et:.6f}   (movable)')
    print(f'  E_gap           = {m["E_gap"]:.12f}  (invariant under rotations)')
    print(f'  lambda_eff      = {m["lambda_eff"]:.6f}')
    print(f'  error_1         = {m["error_1"]:.12f}')
    print(f'  error_2         = {m["error_2"]:.12f}')
    print()
    print('  per-rank ensemble diagnostics:')
    w = np.asarray(W, dtype=np.float64)
    Wn = native(w, H2I)
    for r in range(R):
        x = w[r]
        M = x @ x.T
        ev = np.linalg.eigvalsh(M)
        l1 = np.abs(x).sum(axis=0)
        l2 = np.linalg.norm(x, axis=0)
        term = (np.abs(H2I[r]) + l1) ** 2
        print(f'    r={r}: sum_c ||x_c||_1^2 = {np.sum(l1**2):10.2f}  '
              f'||x_c||_1/||x_c||_2 = {np.mean(l1/np.maximum(l2,1e-300)):5.2f}  '
              f'rank(M_r)={int(np.sum(ev > ev.max()*1e-12)):3d}  '
              f'trace(M_r)={ev.sum():.4f}  '
              f'|H2_I| in [{np.abs(H2I[r]).min():.3f},{np.abs(H2I[r]).max():.3f}]  '
              f'term sum={term.sum():.2f}')
    print()
    print(f'  LOWER BOUND on Lambda: {inv_part:.6f} (ensemble term -> 0 is not')
    print( '  reachable, but the term can only shrink)')

    if args.eval_only:
        return 0

    # ---- search for a better basis ------------------------------------
    rng = np.random.default_rng(args.seed)
    O = np.tile(np.eye(C), (R, 1, 1))
    best = et
    best_w, best_h = np.asarray(W, dtype=np.float64), np.asarray(H2I, dtype=np.float64)
    print()
    print('  searching ensemble rotations ...', flush=True)
    for it in range(args.rounds):
        cand_O = O.copy()
        r = int(rng.integers(R))
        # a small random Givens-style rotation in one (c,d) plane
        c1, c2 = rng.choice(C, size=2, replace=False)
        th = rng.uniform(-np.pi, np.pi)
        G = np.eye(C)
        G[c1, c1] = np.cos(th)
        G[c2, c2] = np.cos(th)
        G[c1, c2] = np.sin(th)
        G[c2, c1] = -np.sin(th)
        cand_O[r] = O[r] @ G
        cw, ch = rotate(best_w, best_h, cand_O)
        ct = ensemble_term(cw, ch)
        if ct < best - 1e-12:
            best, best_w, best_h, O = ct, cw, ch, cand_O
            if it % 20 == 0:
                print(f'    iter {it:5d}: ensemble term {best:.4f}', flush=True)
    print(f'  after {args.rounds} rotations: ensemble term {et:.4f} -> {best:.4f}')

    # ---- verify the metrics are unchanged -----------------------------
    m2 = eval_metrics(best_w, best_h, words, edges, S, beta_1, ref, args.brot)
    print()
    print('  metrics after the rotation:')
    for k in ('error_1', 'error_2', 'Lambda', 'E_SOS', 'E_gap', 'lambda_eff'):
        print(f'    {k:12s} {m[k]:.12f}  ->  {m2[k]:.12f}')
    ok = (m2['error_1'] <= 0.020 and m2['error_2'] <= 0.020
          and m2['gap_in_domain'] and m2['E_gap'] > 3.914898 and m2['Lambda'] > 49.0)
    print(f'    gates: {"PASS" if ok else "FAIL"}')

    T, Q = 13166.0, 405
    s0 = m['lambda_eff'] * T * Q
    s1 = m2['lambda_eff'] * T * Q
    print(f'    score {s0:,.0f} -> {s1:,.0f}  '
          f'(dGM = {33.21179/3 * (s0/s1 - 1):+.5f} GM)')

    if args.out:
        o = pathlib.Path(args.out)
        np.savez(o, U=U, W=best_w, H2_I=best_h, H1_I=z['H1_I'],
                 Hsym_lower=z['Hsym_lower'], tree_edges=edges,
                 angle_words=words)
        print(f'  wrote {o}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
