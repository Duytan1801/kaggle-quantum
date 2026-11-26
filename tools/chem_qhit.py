#!/usr/bin/env python3
"""chem_qhit.py -- how close are the public products to the target quotient?

The plan is correct iff   span{ pi(g_p) }  CONTAINS  Q = span{ pi(D_i) },
where pi is the quotient by the feature span F (everything in F is free).

goodpjw's products have nP = 123..132 while dim Q is only 23..24, so their
product classes span a much bigger space than Q and every one of them is
needed (the per-output representations are UNIQUE, because the classes are
linearly independent).

Two questions decide whether a cheaper plan exists:

  1. How many of the public products' classes lie IN Q?  If many do, they
     alone might span Q and the rest could be dropped.
  2. What is the "outside part" of a typical class?  (how far from Q)

Usage: chem_qhit.py [batch ...]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_prune as CPR                                     # noqa: E402


def analyse(k, tree='v149'):
    plans = CP.decode_plans()
    P = plans[k]
    f = CPR.plan_features(P)
    G = CPR.product_functions(P, f)

    z = np.load(ROOT / f'work/trees/{tree}/dfthcsos/submission.npz')
    W = z['angle_words']
    wk = CP.word_bits(W, k)
    wp = CP.word_bits(W, k - 1)
    d = (wk ^ wp)[CP.OUTS]
    D = [CPR.fun(d[i]) for i in range(30)]

    FB = CPR.Basis((j, f[j]) for j in range(len(f)))
    resD = [FB.reduce(t)[0] for t in D]
    resG = [FB.reduce(g)[0] for g in G]

    # Q = span of the target classes, with tracking of WHICH targets
    QB = CPR.Basis()
    qdim = 0
    for r in resD:
        if QB.add(r, {}):
            qdim += 1
    print(f'batch {k}: nP={len(G)} dimQ={qdim} dimF={FB.rank()}')

    # how many product classes lie in Q?
    inside = [p for p in range(len(G)) if QB.contains(resG[p])]
    # the component outside Q: reduce the class against Q
    outside = []
    for p in range(len(G)):
        r, _ = QB.reduce(resG[p])
        outside.append(bin(r).count('1'))
    print(f'  product classes inside Q: {len(inside)} of {len(G)}')
    print(f'  outside-Q bits: min {min(outside)} max {max(outside)} '
          f'mean {np.mean(outside):.1f}')

    # do the inside ones span Q on their own?
    if inside:
        IB = CPR.Basis()
        for p in inside:
            IB.add(resG[p], {})
        print(f'  span of the inside classes: dim {IB.rank()} '
              f'(Q dim {qdim}) -> {"SPANS Q" if IB.rank() == qdim else "does not span Q"}')
    return dict(k=k, nP=len(G), dimQ=qdim, inside=len(inside))


def main():
    args = sys.argv[1:]
    ks = [int(a) for a in args] if args else sorted(CP.decode_plans())
    for k in ks:
        analyse(k)
        print()


if __name__ == '__main__':
    raise SystemExit(main())
