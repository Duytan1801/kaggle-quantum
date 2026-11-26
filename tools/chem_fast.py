#!/usr/bin/env python3
"""chem_fast.py -- FAST fixed-factor / factor-cover search.

Speed
    pi is LINEAR, so for a factor u = sum_j c_j f_j,

        pi(u AND f_k) = sum_j c_j * pi(f_j AND f_k) ,

    and the 99 x 99 table P[j][k] = pi(f_j AND f_k) can be precomputed once.
    A candidate factor is then evaluated with XORs only (no reductions), so
    thousands of candidates per minute are possible.

What it measures
    For a candidate factor u, the classes reachable with that factor form
    the linear subspace

        L_u = span{ pi(u AND f_j) : j } .

    A plan needs the products' classes to span Q = span{ pi(D_i) }.  If a
    SMALL SET of factors {u_k} has  Q subset of L_{u_1} + ... + L_{u_k},
    then a plan exists with only dim(Q) products (23 for the non-swap
    batches) instead of goodpjw2008's 123..132 -- worth about +3.6 GM.

Usage:
    chem_fast.py <batch> [--rand N] [--seed S] [--maxfac K] [--emit FILE]
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
    ap.add_argument('--seed', type=int, default=17)
    ap.add_argument('--maxfac', type=int, default=16)
    ap.add_argument('--emit')
    ap.add_argument('--time', type=float, default=0.0,
                    help='stop after this many seconds (0 = no limit)')
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
    print('  precomputing the 99x99 product table ...', flush=True)
    prod = [[0] * nf for _ in range(nf)]
    for j in range(nf):
        fj = f[j]
        for kk in range(nf):
            prod[j][kk] = FB.reduce(fj & f[kk])[0]
    print(f'  done ({time.time() - t0:.0f}s)', flush=True)

    # the images of the individual features, for a quick sanity check
    def image(c):
        """-> list of the nf image vectors pi(u AND f_k) for u = sum c_j f_j"""
        cols = []
        for kk in range(nf):
            v = 0
            for j in range(nf):
                if c[j]:
                    v ^= prod[j][kk]
            cols.append(v)
        return cols

    def image_basis(c):
        IB = CPR.Basis()
        for v in image(c):
            IB.add(v, {})
        return IB

    # ---- candidate pool ---------------------------------------------
    rng = random.Random(args.seed)
    cands = []
    for j in range(nf):
        c = [0] * nf
        c[j] = 1
        cands.append((c, ('feature', j)))
    # public plan factors
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
        n = rng.choice([2, 2, 3, 3, 4, 5, 6, 8])
        idxs = rng.sample(range(nf), n)
        c = [0] * nf
        for j in idxs:
            c[j] = 1
        cands.append((c, ('rand', t, tuple(idxs))))
    print(f'  candidates: {len(cands)}', flush=True)

    # ---- evaluate every candidate: how many targets does L_u cover? ---
    scores = []
    for n, (c, label) in enumerate(cands):
        IB = image_basis(c)
        cov = sum(1 for q in qcls if IB.contains(q))
        scores.append((cov, IB.rank(), c, label))
        if cov >= 10:
            print(f'  ** candidate {label} covers {cov}/30 targets '
                  f'(dim L {IB.rank()})', flush=True)
        if n % 200 == 0 and args.time and time.time() - t0 > args.time:
            print('  time limit reached', flush=True)
            break
    scores.sort(key=lambda t: (-t[0], -t[1]))
    print(f'  best single-factor coverage: {scores[0][0]}/30 '
          f'(dim L {scores[0][1]}) label {scores[0][3]}', flush=True)
    for s in scores[:5]:
        print(f'    coverage {s[0]}/30 dimL {s[1]} {s[3]}')

    # ---- greedy cover ------------------------------------------------
    CB = CPR.Basis()
    chosen = []
    covered = 0
    while covered < 30 and len(chosen) < args.maxfac:
        best = None
        for cov, dl, c, label in scores[:400]:
            if any(c == cc for cc, _ in chosen):
                continue
            IB = image_basis(c)
            trial = CPR.Basis()
            for p, (vec, coef) in CB.b.items():
                trial.add(vec, {p: 1})
            for p, (vec, coef) in IB.b.items():
                trial.add(vec, {p: 1})
            newcov = sum(1 for q in qcls if trial.contains(q))
            if best is None or (newcov, trial.rank()) > (best[0], best[1]):
                best = (newcov, trial.rank(), c, label, IB)
        if best is None:
            break
        newcov, dl, c, label, IB = best
        if newcov == covered:
            print('  no further coverage gain', flush=True)
            break
        for p, (vec, coef) in IB.b.items():
            CB.add(vec, {p: 1})
        chosen.append((c, label))
        covered = newcov
        print(f'  + factor {label}: covered {covered}/30, sum dim {CB.rank()}',
              flush=True)

    print(f'  RESULT: covered {covered}/30 with {len(chosen)} factors', flush=True)
    return 0 if covered == 30 else 1


if __name__ == '__main__':
    raise SystemExit(main())
