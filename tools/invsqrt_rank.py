#!/usr/bin/env python3
"""invsqrt_rank.py — how many priced invsqrt rotations are actually needed?

MEASUREMENT
    The minimax LP with ONE of the 33 priced rotations removed still reaches the
    SAME min_margin (36,584,658 units) as the full set.  So the 33 indicator
    vectors are linearly dependent: some of them can be deleted from the
    circuit and the remaining ones re-fitted to reproduce the same phase
    function EXACTLY.  Every deleted rotation is worth
    (1/4)*(0.56*log2(1/eps)+5.3)*Q ~ 275 cost units (~+0.05 GM) because
    eps = pi*min_margin/2^64/n_rot grows as n_rot falls.

    This tool computes the numerical rank of the 33 indicator vectors and
    selects a maximal independent subset (pivoted Cholesky on the Gram
    matrix), so the deletions are provably lossless.

Usage:  python invsqrt_rank.py <sens.npz>
"""
from __future__ import annotations

import sys

import numpy as np

MAX_X = 3133452


def zpow_class(u):
    u = int(u) & ((1 << 64) - 1)
    if u % (1 << 62) == 0:
        return 'clifford'
    if u % (1 << 61) == 0:
        return 't'
    return 'rotation'


def main():
    d = np.load(sys.argv[1], allow_pickle=True)
    V = d['V']
    units = d['units']
    texts = d['texts']
    classes = [zpow_class(u) for u in units]
    priced = [k for k, c in enumerate(classes) if c == 'rotation']
    P = V[priced, :].astype(np.float64)
    print(f'{len(priced)} priced rotations')

    # Gram matrix (counts of co-occurrence), scaled to O(1)
    G = (P @ P.T) / MAX_X
    w = np.linalg.eigvalsh(G)
    print('Gram eigenvalues (descending):')
    for i, ev in enumerate(w[::-1]):
        print(f'   {i:>3}: {ev:.6e}')
    thr = max(w.max(), 1.0) * 1e-10
    rank = int((w > thr).sum())
    print(f'\nnumerical rank (threshold {thr:.3e}): {rank} of {len(priced)}')

    # pivoted Cholesky on the Gram matrix -> maximal independent column subset
    n = len(priced)
    keep = []
    L = np.zeros((n, n))
    resid = G.copy()
    for step in range(n):
        d_ = np.sqrt(np.maximum(np.diag(resid), 0.0))
        if d_.max() <= 1e-9:
            break
        p = int(np.argmax(d_))
        keep.append(p)
        v = resid[:, p] / d_[p]
        L[:, step] = v
        resid = resid - np.outer(v, v * d_[p])
        print(f'  step {step}: pick priced rot {priced[p]:>2} (diag {d_[p]:.6e})')
    print(f'\nindependent subset size {len(keep)}: priced indices {sorted(priced[p] for p in keep)}')
    dropped = [k for k in priced if k not in [priced[p] for p in keep]]
    print(f'droppable (dependent) priced rotations: {dropped}')
    for k in dropped:
        print(f'   rot {k:>2}: class {classes[k]} text {texts[k]}')

    # verify the dependency: express every dropped column in the kept span
    K = P[keep, :]
    # least squares per dropped column (over-determined; use normal equations)
    Gkk = K @ K.T
    for k in dropped:
        b = K @ P[priced.index(k), :]
        try:
            coef = np.linalg.solve(Gkk + 1e-9 * np.eye(len(keep)), b)
        except np.linalg.LinAlgError:
            print(f'   rot {k}: singular')
            continue
        resid = P[priced.index(k), :] - coef @ K
        err = float(np.abs(resid).max())
        print(f'   rot {k:>2}: max |v - sum coef_i v_i| = {err:.3e} '
              f'(exact dependency: {err < 1e-9})')

    np.savez('/tmp/opencode/inv37_rank.npz',
             keep=np.array([priced[p] for p in keep], dtype=np.int64),
             dropped=np.array(dropped, dtype=np.int64),
             priced=np.array(priced, dtype=np.int64))
    print('\nwrote /tmp/opencode/inv37_rank.npz')


if __name__ == '__main__':
    main()
