#!/usr/bin/env python3
"""chem_pair.py -- the PAIR-SUM search: a tree of products spanning Q.

THE IDEA (new, this wake)
    A plan is correct iff   span{ pi(g_p) }  CONTAINS  Q = span{ pi(D_i) }.
    Over GF(2) every element of a span is a subset sum, so if we can find
    product classes equal to the DIFFERENCES of the target classes,

        x_p = q_i  XOR  q_j ,

    then the 29 classes of a spanning TREE on the 30 outputs span exactly Q
    (the tree differences generate the same space as the vertices), and a
    plan with only 29 products exists -- against goodpjw2008's 123..132.
    Cost: 82 + 29 = 111 Toffolis per loader instead of 205..215, i.e.
    chemistry T 13,166 -> 9,830 and about +3.4 GM.

    The classes x_p are realisable iff they lie in the image of one of the
    factor maps  L_u = span{ pi(u AND f_j) }  (see chem_fast.py).

This tool
    1. computes the 30 target classes q_i and the 435 pair sums,
    2. scans a large pool of candidate factors u and records every pair
       (i,j) whose sum lies in L_u,
    3. reports whether the found pairs contain a spanning tree on the 30
       outputs (and the resulting product count).

Usage:
    chem_pair.py <batch> [--rand N] [--seed S] [--emit FILE]
"""
from __future__ import annotations

import argparse
import pathlib
import random
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_prune as CPR                                     # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch', type=int)
    ap.add_argument('--rand', type=int, default=0)
    ap.add_argument('--seed', type=int, default=23)
    ap.add_argument('--emit')
    ap.add_argument('--time', type=float, default=0.0)
    args = ap.parse_args()
    k = args.batch

    import time
    t0 = time.time()

    P = CP.decode_plans()[k]
    f = CPR.plan_features(P)
    nf = len(f)
    G = CPR.product_functions(P, f)

    z = np.load(ROOT / 'work/trees/v149/dfthcsos/submission.npz')
    W = z['angle_words']
    wk = CP.word_bits(W, k)
    wp = CP.word_bits(W, k - 1)
    d = (wk ^ wp)[CP.OUTS]
    D = [CPR.fun(d[i]) for i in range(30)]

    FB = CPR.Basis((j, f[j]) for j in range(nf))
    qcls = [FB.reduce(t)[0] for t in D]
    QB = CPR.Basis()
    for q in qcls:
        QB.add(q, {})
    dimQ = QB.rank()
    print(f'batch {k}: nf={nf} nP(public)={len(G)} dimF={FB.rank()} dimQ={dimQ}',
          flush=True)

    # ---- the product table P[j][k] = pi(f_j AND f_k) ------------------
    prod = [[0] * nf for _ in range(nf)]
    for j in range(nf):
        fj = f[j]
        for kk in range(nf):
            prod[j][kk] = FB.reduce(fj & f[kk])[0]
    print(f'  product table done ({time.time() - t0:.0f}s)', flush=True)

    def image(c):
        cols = []
        for kk in range(nf):
            v = 0
            for j in range(nf):
                if c[j]:
                    v ^= prod[j][kk]
            cols.append(v)
        return cols

    # ---- the pair sums ----------------------------------------------
    pairs = []
    for i in range(30):
        for j in range(i + 1, 30):
            pairs.append((i, j, qcls[i] ^ qcls[j]))
    print(f'  pair sums: {len(pairs)}', flush=True)

    # ---- candidate factors ------------------------------------------
    rng = random.Random(args.seed)
    cands = []
    for j in range(nf):
        c = [0] * nf
        c[j] = 1
        cands.append((c, ('feature', j)))
    swap = P['early'] > 0
    nb = 66 if swap else 68
    i1, i3 = 17 + nb, 17 + nb + 1
    for p, (U, V) in enumerate(zip(P['U'], P['V'])):
        for tag, mask in (('u', U), ('v', V)):
            idxs = [j for j in np.nonzero(mask)[0].tolist()]
            if swap:
                lim = P['early']
                idxs = [j for j in idxs
                        if not (j == i3 and p < lim) and not (j == i1 and p >= lim)]
            c = [0] * nf
            for j in idxs:
                c[j] = 1
            cands.append((c, ('public', p, tag)))
    for t in range(args.rand):
        n = rng.choice([2, 2, 3, 3, 4, 5, 6, 8, 10])
        idxs = rng.sample(range(nf), n)
        c = [0] * nf
        for j in idxs:
            c[j] = 1
        cands.append((c, ('rand', t, tuple(idxs))))
    print(f'  candidate factors: {len(cands)}', flush=True)

    # ---- scan --------------------------------------------------------
    found = {}          # (i,j) -> (factor index, label)
    by_factor = {}
    for n, (c, label) in enumerate(cands):
        cols = image(c)
        IB = CPR.Basis()
        for v in cols:
            IB.add(v, {})
        hits = []
        for (i, j, s) in pairs:
            if IB.contains(s):
                hits.append((i, j))
        if hits:
            by_factor[label] = hits
            for (i, j) in hits:
                found.setdefault((i, j), (n, label))
        if n % 100 == 0:
            print(f'    scanned {n}/{len(cands)} factors, pairs found '
                  f'{len(found)}  ({time.time() - t0:.0f}s)', flush=True)
            if args.time and time.time() - t0 > args.time:
                print('  time limit', flush=True)
                break

    print(f'  PAIR SUMS FOUND: {len(found)} of {len(pairs)}', flush=True)
    for (i, j), (n, label) in sorted(found.items()):
        print(f'    ({i:2d},{j:2d}) via {label}', flush=True)

    # ---- is there a spanning tree? -----------------------------------
    # union-find over the found pairs
    parent = list(range(30))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    tree = []
    for (i, j) in sorted(found):
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj
            tree.append((i, j))
    comps = len({find(i) for i in range(30)})
    print(f'  spanning forest from the found pairs: {len(tree)} edges, '
          f'{comps} components', flush=True)
    if comps == 1:
        print(f'  *** A PLAN WITH {len(tree)} PRODUCTS IS POSSIBLE ***', flush=True)
        if args.emit:
            pathlib.Path(args.emit).write_text(
                f'# batch {k}: tree edges {tree}\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
