#!/usr/bin/env python3
"""chem_span.py -- is a target delta INSIDE the span of the 82-feature scheme?

The wired loaders use a fixed feature space

    F = span{ 1, 11 address bits, 5 QUADS (low-bit products), 82 cached ANDs }

and write each output as  D_i = XOR of products  XOR  R_i  with  R_i in F and
every product  u AND v  with  u, v in F.  Because AND is bilinear over GF(2),
the span of ALL such products is exactly

    span{ f_a AND f_b : a <= b }   over a basis of F.

So the question "can this batch be built with the 82-feature scheme at all?"
is a LINEAR question: is every D_i in span(F + products)?  This tool answers
it exactly, with no search.  (A yes does not give a plan -- the product COUNT
is still a search -- but a no kills the scheme for that feature set.)

Usage: chem_span.py <tree-dir> <feature-batch> <target-batch> [...]
       chem_span.py work/trees/v150/dfthcsos 2 11 7 1 5 0
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219
ADDR = CE.ADDR
BANK, LOW = ADDR >> 4, ADDR & 15
QUADS = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3)]
OUTS = [o for o in range(35) if o % 7 != 6]


def basis_features(tree, k, states):
    """The 99-dim feature space F of loader k, as functions over the addresses."""
    ops, sel, wq = CE.parse_kmx(pathlib.Path(tree) / f'angle_k_{k}.kmb')
    cur = {}
    for i, q in enumerate(sel):
        cur[q] = CE.fun((ADDR >> i) & 1)
    for j, q in enumerate(wq):
        cur[q] = CE.fun(states[k][j])
    feats = []
    for idx, (t, a, c) in enumerate(ops):
        if t == 'CX':
            cur[a[1]] = cur.get(a[1], 0) ^ cur.get(a[0], 0)
        elif t == 'X':
            cur[a[0]] = cur.get(a[0], 0) ^ CE.ALL
        elif t == 'CCX':
            u, v = cur.get(a[0], 0), cur.get(a[1], 0)
            if a[2] >= 46:
                feats.append(u & v)
            cur[a[2]] = cur.get(a[2], 0) ^ (u & v)
        elif t == 'HMR':
            cur[a[0]] = 0
    lin = [CE.ALL] + [CE.fun((ADDR >> i) & 1) for i in range(11)]
    lin += [CE.fun(((LOW >> x) & 1) & ((LOW >> y) & 1)) for x, y in QUADS]
    return lin + feats, len(feats)


def add_to(piv, v):
    v = int(v)
    while v:
        b = v.bit_length() - 1
        row = piv.get(b)
        if row is None:
            piv[b] = v
            return True
        v ^= row
    return False


def reduce_with(piv, v):
    v = int(v)
    while v:
        b = v.bit_length() - 1
        row = piv.get(b)
        if row is None:
            return v
        v ^= row
    return 0


def span_of_features(feats):
    piv = {}
    for f in feats:
        add_to(piv, f)
    return piv


def product_span(feats):
    """span{ f_a AND f_b } over the feature list (a <= b)."""
    piv = {}
    n = len(feats)
    for a in range(n):
        fa = feats[a]
        for b in range(a, n):
            add_to(piv, fa & feats[b])
    return piv


def delta_funs(tree, k):
    z = np.load(pathlib.Path(tree) / 'submission.npz')
    W = np.asarray(z['angle_words'])
    D = []
    for j in range(5):
        col = 5 * k + j
        for i in range(7):
            bit = ((W[:, col] >> i) & 1).astype(bool)
            prev = np.zeros(NV, bool) if k == 0 else ((W[:, col - 5] >> i) & 1).astype(bool)
            D.append(CE.fun(bit ^ prev))
    return D


def main() -> int:
    tree = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'work/trees/v150/dfthcsos')
    args = [int(a) for a in sys.argv[2:]]
    fk = args[0]
    targets = args[1:] or [fk]
    states = CE.chain_states(pathlib.Path(tree) / 'submission.npz')
    feats, nand = basis_features(tree, fk, states)
    Fpiv = span_of_features(feats)
    Ppiv = product_span(feats)
    print(f'feature batch k={fk}: {nand} cached ANDs, |F| basis dim {len(Fpiv)}, '
          f'|span(F + products)| dim {len(Ppiv)}')
    for tk in targets:
        D = delta_funs(tree, tk)
        missF = sum(1 for d in D if reduce_with(Fpiv, d))
        missP = [i for i, d in enumerate(D) if reduce_with(Ppiv, d)]
        print(f'  target k={tk:2d}: D_i outside F: {missF}/35; '
              f'D_i outside span(F+products): {len(missP)}/35'
              + (f'  (first {missP[:6]})' if missP else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
