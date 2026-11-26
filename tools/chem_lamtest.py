#!/usr/bin/env python3
"""chem_lamtest.py -- verify the ensemble-rotation invariance and probe the
landscape of Lambda's ensemble term.

Checks, on the shipped v149 factorization:
  1. a RANDOM rotation leaves error_1, error_2, E_gap and the words
     unchanged, and moves only Lambda;
  2. random rotations move the ensemble term UP and DOWN (the landscape is
     not one-sided), and the shipped basis is at least a local minimum;
  3. how far the term can be pushed by a structured (not random) change:
     e.g. dropping the smallest-|H2_I| ensembles by folding them into the
     others (a rotation is NOT needed for that -- the Gram matrix is
     preserved by the fold).

Usage: chem_lamtest.py [npz]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/verifiers'))
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))

from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_angle_words  # noqa: E402

UPPER = -22140.27335


def native(w, h2i):
    return np.asarray(h2i, dtype=np.float64) - np.sum(np.asarray(w, dtype=np.float64), axis=1)


def rank_term(wr, h2r):
    l1 = np.abs(wr).sum(axis=0)
    return float(np.sum((np.abs(h2r) + l1) ** 2))


def rot(w, h2, r, O):
    w = w.copy()
    h2 = h2.copy()
    x = w[r]
    Wn = native(w[r:r + 1], h2[r:r + 1])[0]
    x2 = x @ O
    W2 = Wn @ O
    w[r] = x2
    h2[r] = W2 + x2.sum(axis=0)
    return w, h2


def main() -> int:
    p = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                     else ROOT / 'work/trees/v149/dfthcsos/submission.npz')
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

    w = np.asarray(W, dtype=np.float64)
    h2 = np.asarray(H2I, dtype=np.float64)
    m0 = metrics(w, h2)
    term0 = sum(rank_term(w[r], h2[r]) for r in range(R)) / 4.0
    print(f'shipped: Lambda={m0["Lambda"]:.6f}  ensemble term={term0:.6f}  '
          f'lambda_eff={m0["lambda_eff"]:.6f}')
    print(f'         error_1={m0["error_1"]:.12f} error_2={m0["error_2"]:.12f} '
          f'E_gap={m0["E_gap"]:.12f}')

    rng = np.random.default_rng(0)
    print()
    print('random rotations of ONE rank (the other ranks untouched):')
    for t in range(6):
        r = int(rng.integers(R))
        A = rng.normal(size=(C, C))
        Q, _ = np.linalg.qr(A)
        w2, h2b = rot(w, h2, r, Q)
        m = metrics(w2, h2b)
        term = sum(rank_term(w2[k], h2b[k]) for k in range(R)) / 4.0
        print(f'  r={r}: ensemble term {term:9.4f} (base {term0:.4f})  '
              f'Lambda {m["Lambda"]:.4f}  err1 {m["error_1"]:.10f}  '
              f'err2 {m["error_2"]:.10f}  E_gap {m["E_gap"]:.10f}')

    print()
    print('FULL random rotations of ALL ranks:')
    for t in range(4):
        Qs = []
        for r in range(R):
            A = rng.normal(size=(C, C))
            Q, _ = np.linalg.qr(A)
            Qs.append(Q)
        w2, h2b = w.copy(), h2.copy()
        for r in range(R):
            w2, h2b = rot(w2, h2b, r, Qs[r])
        m = metrics(w2, h2b)
        term = sum(rank_term(w2[k], h2b[k]) for k in range(R)) / 4.0
        print(f'  ensemble term {term:9.4f}  Lambda {m["Lambda"]:.4f}  '
              f'err1 {m["error_1"]:.10f}  err2 {m["error_2"]:.10f}  '
              f'E_gap {m["E_gap"]:.10f}  lambda_eff {m["lambda_eff"]:.4f}')

    print()
    print('STRUCTURED alternative: fold the smallest-|H2_I| ensembles of each')
    print('rank into the largest one (the Gram matrix M_r is preserved by the')
    print('fold x_c -> x_c + x_c0, W_c -> W_c + W_c0).')
    for keep in (46, 32, 24, 16, 8):
        w2, h2b = w.copy(), h2.copy()
        for r in range(R):
            # order the ensembles by |H2_I| + ||x||_1, fold the small ones
            key = np.abs(h2[r]) + np.abs(w[r]).sum(axis=0)
            order = np.argsort(key)[::-1]
            for c in order[keep:]:
                w[r, :, order[0]] += w[r, :, c]
                h2[r, order[0]] += h2[r, c]
                w[r, :, c] = 0.0
                h2[r, c] = 0.0
        m = metrics(w2, h2b)
        term = sum(rank_term(w2[k], h2b[k]) for k in range(R)) / 4.0
        print(f'  keep {keep:3d}/rank: ensemble term {term:9.4f}  '
              f'Lambda {m["Lambda"]:9.4f}  err1 {m["error_1"]:.10f}  '
              f'err2 {m["error_2"]:.10f}  E_gap {m["E_gap"]:.10f}  '
              f'lambda_eff {m["lambda_eff"]:.4f}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
