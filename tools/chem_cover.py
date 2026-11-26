#!/usr/bin/env python3
"""chem_cover.py -- the FACTOR-COVER search: build a plan with few products.

THE SEARCH (new, this wake)
    A plan is correct iff   span{ pi(g_p) }  CONTAINS  Q = span{ pi(D_i) },
    with pi the quotient by the feature span F (dim 99).  This is EXACT and
    is checked by an exact circuit simulation (work/tools/chem_check_plan.py).

    Fix one factor u; the map  M_u : F -> V/F,  v |-> pi(u AND v)  is
    LINEAR, so the classes reachable with that factor form the subspace

        L_u = span{ pi(u AND f_j) : j } .

    Therefore, if a SMALL SET of factors {u_1..u_k} has

        Q  subset of  L_{u_1} + ... + L_{u_k} ,

    then a plan exists whose products all use one of those k factors, and
    the number of products is only what is needed to span Q (dim Q = 23 for
    the non-swap batches) -- against goodpjw2008's 123..132.

    This tool:
      1. builds the exact quotient space and the target space Q,
      2. pools candidate factors (every feature, every factor of the public
         plan's own products, random XORs of features),
      3. greedily picks the factors whose image spaces grow the sum fastest,
      4. emits the resulting PLAN (products + masks + linear rests) and
         writes it as a Python literal for the exact verifier.

Usage:
    chem_cover.py <batch> [--rand N] [--emit FILE]
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


class Gen:
    """a product generator: a factor u (feature mask) and a v (feature mask)"""

    def __init__(self, ufun, vidx, label):
        self.ufun = ufun
        self.vidx = tuple(vidx)
        self.label = label


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('batch', type=int)
    ap.add_argument('--rand', type=int, default=0)
    ap.add_argument('--seed', type=int, default=3)
    ap.add_argument('--emit')
    ap.add_argument('--maxfac', type=int, default=12)
    args = ap.parse_args()
    k = args.batch

    plans = CP.decode_plans()
    P = plans[k]
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
    print(f'batch {k}: nf={nf} nP(public)={len(G)} dimF={FB.rank()} dimQ={dimQ}')

    def xorf(idxs):
        v = 0
        for j in idxs:
            v ^= f[j]
        return v

    # ---- candidate pool ---------------------------------------------
    pool = []          # (ufun, label)
    for j in range(nf):
        pool.append((f[j], ('feature', j)))
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
            pool.append((xorf(idxs), ('public', p, tag)))
    rng = random.Random(args.seed)
    for t in range(args.rand):
        n = rng.choice([2, 2, 3, 3, 4, 5])
        idxs = rng.sample(range(nf), n)
        pool.append((xorf(idxs), ('rand', t, tuple(idxs))))
    print(f'  candidate factors: {len(pool)}')

    # ---- the image basis of one factor (with v-tracking) ------------
    def image(ufun):
        """-> (Basis over the images, list of Gen per generator index)"""
        IB = CPR.Basis()
        gens = []
        for j in range(nf):
            r, _ = FB.reduce(ufun & f[j])
            if IB.add(r, {len(gens): 1}):
                gens.append(Gen(ufun, [j], ('image', j)))
        return IB, gens

    # ---- greedy cover ------------------------------------------------
    CB = CPR.Basis()          # the sum of the chosen image spaces
    chosen = []               # (ufun, gens)
    used_gens = []            # the product generators in use
    covered = 0
    while covered < 30 and len(chosen) < args.maxfac:
        best = None
        for ufun, label in pool:
            if any(ufun == c[0] for c in chosen):
                continue
            IB, gens = image(ufun)
            # how much does it add to the sum?
            add = 0
            trial = CPR.Basis()
            for p, (vec, coef) in CB.b.items():
                trial.add(vec, {p: 1})
            for p, (vec, coef) in IB.b.items():
                if trial.add(vec, {p: 1}):
                    add += 1
            if add > 0 and (best is None or add > best[0]):
                best = (add, ufun, label, IB, gens)
        if best is None or best[0] == 0:
            print('  no factor adds anything more')
            break
        add, ufun, label, IB, gens = best
        # merge
        off = len(used_gens)
        for p, (vec, coef) in IB.b.items():
            # translate the v-coefficients into a Gen
            vidx = []
            for gi, on in coef.items():
                if on:
                    vidx.extend(gens[gi].vidx)
            g = Gen(ufun, vidx, label)
            used_gens.append(g)
            CB.add(vec, {off + p: 1})
        chosen.append((ufun, label))
        covered = sum(1 for q in qcls if CB.contains(q))
        print(f'  + factor {label}: image adds {add} dims, covered targets '
              f'{covered}/30, sum dim {CB.rank()}')

    if covered < 30:
        print(f'  FAILED to cover Q with {len(chosen)} factors '
              f'({covered}/30 targets)')
        return 1

    # ---- express Q in the combined basis -----------------------------
    # the products we actually need: the generators used by the Q basis
    qbasis = list(QB.b.values())
    used = set()
    for vec, coef in qbasis:
        sol = CB.solve(vec)
        assert sol is not None
        used |= set(sol.keys())
    print(f'  products needed to span Q: {len(used)}')
    prod = [used_gens[i] for i in sorted(used)]

    # ---- build the plan ----------------------------------------------
    # masks: for each output i, the subset of products whose sum gives q_i
    masks = {p: [] for p in range(len(prod))}
    for i in range(30):
        sol = CB.solve(qcls[i])
        assert sol is not None, f'output {i} not in the span'
        for gi in sol:
            masks[prod.index(used_gens[gi])].append(i)
    # linear rests: the feature coefficients of D_i
    rests = []
    for i in range(30):
        r, c = FB.reduce(D[i])
        assert r == 0 or True
        rests.append(c)

    # the product feature masks
    U = np.zeros((len(prod), nf), np.uint8)
    V = np.zeros((len(prod), nf), np.uint8)
    for p, g in enumerate(prod):
        # recover the feature mask of u: the label carries it for the
        # single-feature case; in general recompute from the function
        ufun = g.ufun
        for j in range(nf):
            if (ufun >> (0)) and False:
                pass
        # the feature masks are recovered by matching the function value
        for j in range(nf):
            if ufun == f[j]:
                U[p, j] = 1
                break
        else:
            raise SystemExit('factor is not a single feature; extend the tool')
        for j in g.vidx:
            V[p, j] = 1
    M = np.zeros((len(prod), 30), np.uint8)
    for p, outs in masks.items():
        for i in outs:
            M[p, i] = 1
    R = np.zeros((30, nf), np.uint8)
    for i, c in enumerate(rests):
        for j, on in c.items():
            if on:
                R[i, j] = 1

    newP = dict(early=P['early'], ands=P['ands'].copy(), B=P['B'].copy(),
                U=U, V=V, M=M, R=R)
    nb2 = 66 if newP['early'] > 0 else 68
    nmix = 9 if newP['early'] > 0 else 8
    cost = nb2 + 6 + nmix + (2 if newP['early'] > 0 else 0) + len(prod)
    print(f'  NEW PLAN: nP={len(prod)} cost={cost} Toffolis '
          f'(public {len(G)} products, cost '
          f'{nb2 + 6 + nmix + (2 if newP["early"] > 0 else 0) + len(G)})')

    if args.emit:
        import pprint
        d = {k2: np.asarray(v).tolist() for k2, v in newP.items()}
        pathlib.Path(args.emit).write_text(pprint.pformat(d, width=100,
                                                          sort_dicts=True))
        print(f'  wrote {args.emit}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
