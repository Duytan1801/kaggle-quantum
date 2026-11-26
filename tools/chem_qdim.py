#!/usr/bin/env python3
"""chem_qdim.py -- the dimension of the PRODUCT-CLASS space.

All the classes a product can ever have are

        pi(f_j AND f_k)   for the 99 x 99 feature pairs,

so the span of all possible product classes is

        W2 = span{ pi(f_j AND f_k) }  subset of  V/F .

The public plan's products live in W2, and so must every target class
Q = span{ pi(D_i) }.  dim(W2) says how much room a search has:

  * if dim(W2) is small, the products' classes are far from generic and a
    small product family may well span Q;
  * if dim(W2) is close to dim(V/F) = 1120, the classes are generic and a
    small family spanning a 23-dimensional Q is very unlikely -- which is
    exactly what goodpjw2008's published method ("plant low-rank elements
    in Z", "GPU FWHT", "matroid parity") is designed to defeat.

Usage: chem_qdim.py [batch ...]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_prune as CPR                                     # noqa: E402


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ks = [int(a) for a in args] if args else [14]
    for k in ks:
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
        dimF = FB.rank()
        dimV = 1219
        W2 = CPR.Basis()
        for j in range(nf):
            for kk in range(nf):
                r, _ = FB.reduce(f[j] & f[kk])
                W2.add(r, {})
        QB = CPR.Basis()
        qcls = []
        for t in D:
            q = FB.reduce(t)[0]
            qcls.append(q)
            QB.add(q, {})
        dimQ = QB.rank()
        inQ = all(W2.contains(q) for q in qcls)
        # how many of the PUBLIC products' classes are in W2?
        pub = [FB.reduce(g)[0] for g in G]
        npub = sum(1 for p in pub if W2.contains(p))
        print(f'batch {k}: dimF={dimF} dim(V/F)={dimV - dimF} dimQ={dimQ} '
              f'dimW2={W2.rank()}  Q subset W2: {inQ}  '
              f'public classes in W2: {npub}/{len(pub)}')
        print(f'    quotient used by the products: {W2.rank()}/{dimV - dimF} '
              f'= {100.0 * W2.rank() / (dimV - dimF):.1f}%')
        # the rank of the public products' classes inside W2
        PB = CPR.Basis()
        for p in pub:
            PB.add(p, {})
        print(f'    public product classes: rank {PB.rank()} inside W2; '
              f'Q dim {dimQ} -> the public family is {PB.rank() / dimQ:.1f}x '
              f'the target dimension')


if __name__ == '__main__':
    raise SystemExit(main())
