#!/usr/bin/env python3
"""chem_fixed.py -- the FIXED-FACTOR search: can ONE factor cover the target?

THE IDEA (new, this wake)
    A plan is correct iff   span{ pi(g_p) }  CONTAINS  Q = span{ pi(D_i) },
    where pi is the quotient by the feature span F (dim 99) and g_p is a
    product u AND v.  This is exact (work/tools/chem_prune.py) and it is
    verified by an exact circuit simulation (work/tools/chem_check_plan.py).

    Now FIX one factor u and let the other factor v range over F.  Then

        M_u : F -> V/F,      v |-> pi(u AND v)

    is a LINEAR map, because multiplication by a fixed u is linear.  So the
    classes reachable with the factor u form a SUBSPACE

        L_u = span{ pi(u AND f_j) : j = 0..nf-1 }.

    If L_u contains Q, then EVERY target class is reachable with that one
    factor, and a plan needs only dim(Q) products (one per basis element of
    Q) -- 23 instead of goodpjw's 123!  The per-output masks and the linear
    rests then follow from linear algebra alone.

    This tool:
      1. builds the exact quotient space,
      2. tests a battery of candidate factors u (every feature, every factor
         of the public plan's own products, and random XORs of features),
      3. reports, for each, dim(L_u), how much of Q it covers, and whether
         Q is contained in it.

Usage:
    chem_fixed.py <batch> [--rand N] [--dump]
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


def xor_features(f, idxs):
    v = 0
    for j in idxs:
        v ^= f[j]
    return v


def build(k, tree='v149'):
    plans = CP.decode_plans()
    P = plans[k]
    f = CPR.plan_features(P)
    nf = len(f)
    G = CPR.product_functions(P, f)

    z = np.load(ROOT / f'work/trees/{tree}/dfthcsos/submission.npz')
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
    return P, f, nf, G, FB, qcls, QB, D


def image_basis(FB, ufun, f, nf):
    """-> a Basis for L_u = span{ pi(u AND f_j) }"""
    IB = CPR.Basis()
    for j in range(nf):
        r, _ = FB.reduce(ufun & f[j])
        IB.add(r, {})
    return IB


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch', type=int)
    ap.add_argument('--rand', type=int, default=0)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--dump', action='store_true')
    args = ap.parse_args()
    k = args.batch

    P, f, nf, G, FB, qcls, QB, D = build(k)
    dimQ = QB.rank()
    print(f'batch {k}: nf={nf} nP={len(G)} dimF={FB.rank()} dimQ={dimQ}')

    def cover(IB):
        """-> (number of the 30 targets inside, dim L_u)"""
        n = sum(1 for q in qcls if IB.contains(q))
        return n, IB.rank()

    # ---- 1. every single feature ------------------------------------
    best = []
    for j in range(nf):
        IB = image_basis(FB, f[j], f, nf)
        n, d = cover(IB)
        best.append((n, d, ('feature', j)))
        if n == 30:
            print(f'  *** feature {j} covers ALL 30 targets (dim L = {d})')
    print(f'  single features: best coverage {max(b[0] for b in best)}/30, '
          f'best dim L {max(b[1] for b in best)}')

    # ---- 2. the public plan's own product factors --------------------
    swap = P['early'] > 0
    nb = 66 if swap else 68
    i1 = 17 + nb
    i3 = 17 + nb + 1
    best2 = []
    for p, (U, V) in enumerate(zip(P['U'], P['V'])):
        for tag, mask in (('u', U), ('v', V)):
            idxs = [j for j in np.nonzero(mask)[0].tolist()]
            if swap:
                # a factor may use i3 only in phase 1 and i1 only in phase 2
                lim = P['early']
                idxs = [j for j in idxs
                        if not (j == i3 and p < lim) and not (j == i1 and p >= lim)]
            ufun = xor_features(f, idxs)
            IB = image_basis(FB, ufun, f, nf)
            n, d = cover(IB)
            best2.append((n, d, (tag, p)))
            if n == 30:
                print(f'  *** public product {p} factor {tag} covers ALL 30 '
                      f'(dim L = {d})')
    if best2:
        print(f'  public-plan factors: best coverage {max(b[0] for b in best2)}/30, '
              f'best dim L {max(b[1] for b in best2)}')

    # ---- 3. random XORs of features ----------------------------------
    if args.rand:
        rng = random.Random(args.seed)
        bestr = (0, 0, None)
        for t in range(args.rand):
            nfeat = rng.choice([2, 2, 3, 3, 4, 5, 6])
            idxs = rng.sample(range(nf), nfeat)
            ufun = xor_features(f, idxs)
            IB = image_basis(FB, ufun, f, nf)
            n, d = cover(IB)
            if (n, d) > (bestr[0], bestr[1]):
                bestr = (n, d, tuple(idxs))
                print(f'  random candidate {t}: coverage {n}/30 dim L {d} '
                      f'features {idxs}')
            if n == 30:
                print(f'  *** RANDOM candidate covers ALL 30: {idxs}')
                break
        print(f'  random candidates: best coverage {bestr[0]}/30 (dim L {bestr[1]})')

    # ---- 4. how big is L_u at best, and what does Q look like? ------
    print()
    print('  Q basis (the target classes) -- for reference:')
    for q in list(QB.b.values())[:3]:
        print(f'    residual bits {bin(q[0]).count("1")}')


if __name__ == '__main__':
    raise SystemExit(main())
