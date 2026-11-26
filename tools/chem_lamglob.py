#!/usr/bin/env python3
"""chem_lamglob.py -- a GLOBAL search for a better ensemble basis.

Coordinate descent over all Givens 2-planes finds nothing (the shipped
basis is a strict local minimum), so this tool tries to escape it:

  * random-subspace rotations of dimension k = 3..8 (a 2-plane search cannot
    leave a basin that needs a coordinated move in >=3 coordinates),
  * simulated annealing over 2-plane moves with restarts,
  * a "shifted" start: the eigen-decomposition basis and random bases, then
    descent from each.

The objective is Lambda's ensemble term
    1/4 sum_(r,c) ( |H2_I[r,c]| + ||x[r,:,c]||_1 )^2
which the official metric code confirms equals Lambda minus the invariant
sum_j |lambda_j|.

Usage:
    chem_lamglob.py [npz] [--seconds S] [--seed S] [--out FILE]
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
    w = np.asarray(w, dtype=np.float64)
    return np.asarray(h2i, dtype=np.float64) - np.sum(w, axis=1)


def rank_term(wr, h2r):
    l1 = np.abs(wr).sum(axis=0)
    return float(np.sum((np.abs(h2r) + l1) ** 2))


def rot_rank(w, h2, r, O):
    x = w[r] @ O
    Wn = native(w[r:r + 1], h2[r:r + 1])[0]
    W2 = Wn @ O
    w[r] = x
    h2[r] = W2 + x.sum(axis=0)
    return w, h2


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('npz', nargs='?',
                    default=str(ROOT / 'work/trees/v149/dfthcsos/submission.npz'))
    ap.add_argument('--seconds', type=float, default=600.0)
    ap.add_argument('--seed', type=int, default=11)
    ap.add_argument('--out')
    args = ap.parse_args()

    p = pathlib.Path(args.npz)
    z = np.load(p)
    U, W, H2I = z['U'], z['W'], z['H2_I']
    R, B, C = W.shape
    words, edges = z['angle_words'], z['tree_edges']

    from dfthcsos.verify import load_inputs
    inp = load_inputs({'U': U, 'W': W, 'H2_I': H2I, 'H1_I': z['H1_I'],
                       'Hsym_lower': z['Hsym_lower']})
    S, beta_1, ref = inp.S, inp.beta_1, inp.ref

    def metrics(w, h2i):
        Wn = native(w, h2i)
        return evaluate_dfthc_angle_words(words, np.asarray(w, dtype=np.float64),
                                          Wn, S, beta_1, ref, brot=7,
                                          tree_edges=edges, energy_upper=UPPER)

    w0 = np.asarray(W, dtype=np.float64).copy()
    h20 = np.asarray(H2I, dtype=np.float64).copy()
    m0 = metrics(w0, h20)
    base = sum(rank_term(w0[r], h20[r]) for r in range(R)) / 4.0
    inv = m0['Lambda'] - base
    print(f'shipped: Lambda={m0["Lambda"]:.6f}  ensemble={base:.6f}  '
          f'inv={inv:.6f}  lambda_eff={m0["lambda_eff"]:.6f}')
    print(f'floor if the ensemble term were 0: Lambda={inv:.6f}  '
          f'lambda_eff={np.sqrt(m0["E_gap"]*(2*inv-m0["E_gap"])):.6f}')

    rng = np.random.default_rng(args.seed)
    t_end = time.time() + args.seconds

    best_w, best_h = w0.copy(), h20.copy()
    best = base
    trials = 0
    # ---- phase 1: random subspace rotations ---------------------------
    print('phase 1: random subspace rotations', flush=True)
    while time.time() < t_end * 0.6 + time.time() * 0.4:
        if time.time() >= t_end:
            break
        r = int(rng.integers(R))
        k = int(rng.integers(3, 9))
        idx = rng.choice(C, size=k, replace=False)
        A = rng.normal(size=(k, k))
        Q, _ = np.linalg.qr(A)
        O = np.eye(C)
        O[np.ix_(idx, idx)] = Q
        w2, h2b = rot_rank(best_w.copy(), best_h.copy(), r, O)
        t = sum(rank_term(w2[k2], h2b[k2]) for k2 in range(R)) / 4.0
        trials += 1
        if t < best - 1e-10:
            best, best_w, best_h = t, w2, h2b
            print(f'  improved: ensemble {best:.6f}  (trial {trials})', flush=True)

    # ---- phase 2: annealing over 2-plane moves -------------------------
    print('phase 2: annealing over 2-plane moves', flush=True)
    cur_w, cur_h = best_w.copy(), best_h.copy()
    cur = best
    temp0 = 2.0
    while time.time() < t_end:
        r = int(rng.integers(R))
        c1, c2 = rng.choice(C, size=2, replace=False)
        th = rng.uniform(-np.pi / 2, np.pi / 2)
        w2, h2b = rot_rank(cur_w.copy(), cur_h.copy(), r, np.eye(C))
        # a 2-plane rotation
        O = np.eye(C)
        O[c1, c1] = np.cos(th)
        O[c2, c2] = np.cos(th)
        O[c1, c2] = np.sin(th)
        O[c2, c1] = -np.sin(th)
        w2, h2b = rot_rank(cur_w.copy(), cur_h.copy(), r, O)
        t = sum(rank_term(w2[k2], h2b[k2]) for k2 in range(R)) / 4.0
        trials += 1
        frac = (time.time() - (t_end - args.seconds)) / args.seconds
        temp = temp0 * max(0.0, 1.0 - frac)
        if t < cur or rng.random() < np.exp((cur - t) / max(temp, 1e-6)):
            cur, cur_w, cur_h = t, w2, h2b
            if cur < best - 1e-10:
                best, best_w, best_h = cur, w2, h2b
                print(f'  improved: ensemble {best:.6f}  (trial {trials})', flush=True)

    print()
    print(f'trials: {trials}   ensemble term {base:.6f} -> {best:.6f}')
    if best < base - 1e-9:
        m1 = metrics(best_w, best_h)
        print('  metrics after the search:')
        for kk in ('error_1', 'error_2', 'Lambda', 'E_SOS', 'E_gap', 'lambda_eff'):
            print(f'    {kk:12s} {m0[kk]:.12f} -> {m1[kk]:.12f}')
        s0 = m0['lambda_eff'] * 13166.0 * 405
        s1 = m1['lambda_eff'] * 13166.0 * 405
        print(f'    score {s0:,.0f} -> {s1:,.0f}  '
              f'dGM = {33.21179/3*(s0/s1-1):+.5f} GM')
        if args.out:
            o = pathlib.Path(args.out)
            np.savez(o, U=U, W=best_w, H2_I=best_h, H1_I=z['H1_I'],
                     Hsym_lower=z['Hsym_lower'], tree_edges=edges,
                     angle_words=words)
            print(f'  wrote {o}')
    else:
        print('  NO IMPROVEMENT FOUND -- the shipped ensemble basis is the best')
        print('  found by subspace rotations and annealing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
