#!/usr/bin/env python3
"""chem_lamrank.py -- how much room is there in Lambda's ensemble term?

For ONE rank r the objective of an orthogonal ensemble basis O is

    F_r(O) = sum_c ( ||w O[:,c]||_1 + |w_B^T O[:,c]| )^2 ,   w_B = H2_I[r]

(the verifier's lambda_h2, up to the factor 1/4).  This tool measures:

  * the shipped value,
  * the best value found by a big random search,
  * the best value found by a greedy "sparse column" construction,
  * a lower bound (sum_c ||w v_c||_2^2 = trace(M_r) and ||w_B||_2^2).

If the shipped value cannot be beaten by a wide margin the lever is dead
and the chemistry lane stays closed at the public factorization.

Usage: chem_lamrank.py [rank] [--trials N]
"""
from __future__ import annotations

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


def F(wr, wB, O):
    """sum_c (||w O[:,c]||_1 + |wB^T O[:,c]|)^2"""
    Y = wr @ O
    return float(np.sum((np.abs(Y).sum(axis=0) + np.abs(wB @ O)) ** 2))


def main() -> int:
    r = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 0
    trials = 200000
    for a in sys.argv:
        if a.startswith('--trials'):
            trials = int(a.split('=')[1])

    p = ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    z = np.load(p)
    W, H2I = z['W'], z['H2_I']
    R, B, C = W.shape
    w = np.asarray(W, dtype=np.float64)
    h2 = np.asarray(H2I, dtype=np.float64)
    wr = w[r]
    wB = h2[r]

    base = F(wr, wB, np.eye(C))
    M = wr @ wr.T
    tr = float(np.linalg.eigvalsh(M).sum())
    print(f'rank {r}: shipped F_r = {base:.4f}')
    print(f'  lower bound trace(M_r) = {tr:.4f}   ||w_B||_2^2 = '
          f'{float(wB @ wB):.4f}   C = {C}')

    rng = np.random.default_rng(0)
    best = base
    t0 = time.time()
    for i in range(trials):
        k = int(rng.integers(2, min(C, 12) + 1))
        idx = rng.choice(C, size=k, replace=False)
        A = rng.normal(size=(k, k))
        Q, _ = np.linalg.qr(A)
        O = np.eye(C)
        O[np.ix_(idx, idx)] = Q
        v = F(wr, wB, O)
        if v < best - 1e-10:
            best = v
            print(f'  random improvement: {best:.4f}  (trial {i})', flush=True)
    print(f'  after {trials} random subspace trials ({time.time()-t0:.0f}s): '
          f'best {best:.4f}')

    # ---- greedy sparse-column construction -----------------------------
    # choose columns of O one at a time, each time minimising f(v) over the
    # unit sphere subject to orthogonality to the already-chosen ones
    # (a local random search inside the orthogonal complement).
    chosen = []
    O = np.zeros((C, C))
    for c in range(C):
        bestv, bestf = None, None
        for _ in range(400):
            v = rng.normal(size=C)
            if chosen:
                v -= sum(float(v @ O[:, j]) * O[:, j] for j in chosen)
            n = np.linalg.norm(v)
            if n < 1e-9:
                continue
            v = v / n
            f = float(np.abs(wr @ v).sum() + abs(wB @ v))
            if bestf is None or f < bestf:
                bestf, bestv = f, v
        O[:, c] = bestv
        chosen.append(c)
    gs = F(wr, wB, O)
    print(f'  greedy sparse-column construction: {gs:.4f}')

    # ---- the shipped basis per rank, for comparison --------------------
    print()
    print('  per-rank shipped F_r:')
    tot = 0.0
    for rr in range(R):
        fr = F(w[rr], h2[rr], np.eye(C))
        tot += fr
        print(f'    r={rr}: {fr:10.4f}')
    print(f'    total/4 = {tot/4:.4f}  (Lambda ensemble term)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
