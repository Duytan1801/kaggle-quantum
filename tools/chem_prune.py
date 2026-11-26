#!/usr/bin/env python3
"""chem_prune.py -- is the public chemistry plan over-provisioned?

THE OBSERVATION
    A plan expresses each output's batch delta as

        D_i  =  XOR_{p : i in M_p} g_p   XOR   R_i

    where g_p = u_p AND v_p is a *product* (one Toffoli) and R_i is a *linear
    rest* -- an XOR of the cached features, which is FREE (the features are
    already computed for the products, and the rest is applied with CNOTs).

    So let F = span(the features).  Everything in F is free.  Write pi for the
    quotient map V -> V/F.  The plan is correct iff

        pi(D_i) = SUM_{p : i in M_p} pi(g_p)   for every output i.

    Over GF(2) every element of a span is a subset sum, so the ONLY global
    condition is

        span{ pi(g_p) }  must contain  span{ pi(D_i) }.

    If the plan's products are redundant, a SMALLER subset of them still spans
    the same quotient space; the per-output masks and the linear rests then
    follow from linear algebra, and the loader gets cheaper by one Toffoli per
    dropped product.

    This tool measures the quotient dimension q = dim(span{D} + F) - dim(F),
    the rank of the products' images, and the size of a minimal spanning
    subset -- for a PUBLIC plan (known-answer control) or for a plan file.

    If q is small, the public 123-132 products are massively over-provisioned
    and the whole chemistry leg can be rebuilt much cheaper.

Usage:
    chem_prune.py --batch 14                 measure + build the pruned plan
    chem_prune.py --batch 14 --emit OUT.py   also write the pruned plan
    chem_prune.py --all                      measure every public batch
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402

NV = CP.NV
ADDR = CP.ADDR
BANK, LOW = CP.BANK, CP.LOW
OUTS = CP.OUTS
NBANK = 77
NLOW = 16


def fun(f):
    return int.from_bytes(np.packbits(np.asarray(f, bool), bitorder='little').tobytes(), 'little')


# ---------------------------------------------------------------- features
def plan_features(P):
    """the plan's feature functions as 1219-bit ints, index-aligned with the
    emitter's `names` list (index 0 = constant, 1..11 address bits,
    12..16 QUADS, then the cached ANDs, then the low ANDs, then the mixed)."""
    swap = P['early'] > 0
    nb, nmix = (66, 9) if swap else (68, 8)
    f = [fun(np.ones(NV, bool))]
    for i in range(11):
        f.append(fun(((ADDR >> i) & 1).astype(bool)))
    for (x, y) in CP.QUADS:
        f.append(fun((((LOW >> x) & 1) & (LOW >> y)).astype(bool)))

    # the emitter's growing `gens` list: bank-bit generators, then one entry
    # per cached AND (its own u & v mask)
    gens = [sum(((x >> i) & 1) << x for x in range(77)) for i in range(7)]

    def pair(row):
        u = v = 0
        for i in row[:3]:
            u ^= gens[i] if i < 255 else 0
        for i in row[3:]:
            v ^= gens[i] if i < 255 else 0
        return u, v

    def up(b):
        return fun(np.array([(b >> i) & 1 for i in range(77)], bool)[BANK])

    for row in P['ands'][:nb]:
        u, v = pair(row)
        gens.append(u & v)
        f.append(up(u & v))
    if swap:
        u1, v1 = pair(P['ands'][66])
        f.append(up(u1 & v1))                       # i1
        u3, v3 = pair(P['ands'][67])
        f.append(up(u3 & v3))                       # i3
    lb = [fun((LOW >> i) & 1) for i in range(4)]
    for s, t in CP.LOW_ANDS:
        u = fun(np.ones(NV, bool))
        for x in s:
            u &= lb[x]
        f.append(u & lb[t])
    for g in range(nmix):
        c = 7 if g < nmix - 4 else 14
        bmask = P['B'][g]
        b = np.zeros(NBANK, bool)
        for b_ in range(NBANK):
            b[b_] = bool(bmask[b_])
        f.append(fun((LOW == c) & b[BANK]))
    return f


def product_functions(P, f):
    """-> list of the products' functions (one per product, phase-correct)

    NOTE the constant: the emitter's `sup()` drops feature 0 from the qubit
    set and passes it as a separate flag, which `controls()` turns into an X
    on the control qubit.  So a set constant bit means "XOR the all-ones
    function into that factor" -- it must be included here.
    """
    swap = P['early'] > 0
    nb = 66 if swap else 68
    i1 = 17 + nb
    i3 = 17 + nb + 1
    out = []
    for p, (u, v) in enumerate(zip(P['U'], P['V'])):
        gu = gv = 0
        for j in np.nonzero(u)[0]:
            if swap and j == i3 and p < P['early']:
                continue                       # not live in this phase
            if swap and j == i1 and p >= P['early']:
                continue
            gu ^= f[j]
        for j in np.nonzero(v)[0]:
            if swap and j == i3 and p < P['early']:
                continue
            if swap and j == i1 and p >= P['early']:
                continue
            gv ^= f[j]
        out.append(gu & gv)
    return out


# ---------------------------------------------------------------- GF(2)
class Basis:
    """a GF(2) basis with tracking of the generating vectors' coefficients

    The basis is kept in REDUCED row-echelon form (every basis vector has
    zeros at all other pivots), so the reduction of a vector is CANONICAL:
    the residual has zeros at every pivot position and therefore depends
    only on the coset (the quotient class), which is what the quotient-space
    arithmetic needs.
    """

    def __init__(self, gens=()):
        self.b = {}                      # pivot -> (vector, coef dict)
        for idx, v in gens:
            self.add(v, {idx: 1})
        self._reduce()
        self.pivots = sorted(self.b, reverse=True)

    def add(self, v, coef):
        cur, c = v, dict(coef)
        while cur:
            p = cur.bit_length() - 1
            e = self.b.get(p)
            if e is None:
                self.b[p] = (cur, c)
                self.pivots = sorted(self.b, reverse=True)
                return True
            cur ^= e[0]
            c = self._xorcoef(c, e[1])
        return False

    @staticmethod
    def _xorcoef(a, b):
        out = dict(a)
        for k, v in b.items():
            out[k] = out.get(k, 0) ^ v
        return {k: v for k, v in out.items() if v}

    def _reduce(self):
        """make the basis reduced (zeros at all other pivots)

        Eliminating pivot q from a higher pivot p can expose a pivot r < q,
        and reducing basis[r] can expose further pivots, so iterate to a
        fixed point.
        """
        pivots = sorted(self.b, reverse=True)
        changed = True
        while changed:
            changed = False
            for p in pivots:
                vec, coef = self.b[p]
                for q in pivots:
                    if q == p:
                        continue
                    if (vec >> q) & 1:
                        ev, ec = self.b[q]
                        vec ^= ev
                        coef = self._xorcoef(coef, ec)
                        changed = True
                self.b[p] = (vec, coef)

    def reduce(self, v):
        """-> (residual, coef) with v = residual XOR sum(coef[j] * gen_j)

        The residual is CANONICAL: all pivot positions are zero, so two
        vectors have the same residual iff they differ by an element of the
        span.  `contains` is then simply "residual == 0".
        """
        cur, c = v, {}
        while True:
            hit = False
            for q in self.pivots:
                if (cur >> q) & 1:
                    e = self.b[q]
                    cur ^= e[0]
                    c = self._xorcoef(c, e[1])
                    hit = True
                    break
            if not hit:
                break
        return cur, c

    def rank(self):
        return len(self.b)

    def contains(self, v):
        r, _ = self.reduce(v)
        return r == 0

    def solve(self, v):
        """-> {gen index: 1} if v is in the span, else None"""
        r, c = self.reduce(v)
        if r:
            return None
        return {k: x for k, x in c.items() if x}


# ---------------------------------------------------------------- main
def analyse(P, k, tree='v149', verbose=True):
    npz = ROOT / f'work/trees/{tree}/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    f = plan_features(P)
    nf = len(f)
    G = product_functions(P, f)

    # targets
    wk = CP.word_bits(W, k)
    wp = CP.word_bits(W, k - 1)
    d = (wk ^ wp)[OUTS]
    D = [fun(d[i]) for i in range(30)]

    # F = span(features), tracked by feature index
    FB = Basis((j, f[j]) for j in range(nf))
    dimF = FB.rank()

    # classes of the targets
    resD, coefD = [], []
    for t in D:
        r, c = FB.reduce(t)
        resD.append(r)
        coefD.append(c)

    # the quotient space spanned by the targets
    QB = Basis()
    for r in resD:
        QB.add(r, {})
    q = QB.rank()

    # the products' classes
    resG = []
    for g in G:
        r, _ = FB.reduce(g)
        resG.append(r)

    # rank of the products' images (as a plain basis)
    PB = Basis()
    for r in resG:
        PB.add(r, {})
    rankG = PB.rank()

    # do the products span the target quotient?
    spans = all(PB.contains(r) for r in resD)

    if verbose:
        print(f'batch {k}: nf={nf} nP={len(G)} dimF={dimF} dimQ={q} '
              f'rank(products\' images)={rankG} products span Q: {spans}')

    # ---- greedy minimal subset of products spanning Q
    sel = []
    basis = Basis()
    covered = False
    for p in range(len(G)):
        if basis.add(resG[p], {p: 1}):
            sel.append(p)
            if all(basis.contains(r) for r in resD):
                covered = True
                break
    if verbose:
        print(f'  greedy spanning subset: {len(sel)} products '
              f'(dim Q = {q}); covers all targets: {covered}')

    # ---- per-output masks and linear rests
    SB = Basis((p, resG[p]) for p in sel)
    masks = {p: [] for p in sel}
    rests = []
    ok = True
    for i in range(30):
        sol = SB.solve(resD[i])
        if sol is None:
            ok = False
            rests.append(None)
            continue
        for p in sol:
            masks[p].append(i)
        # R_i = D_i XOR sum(g_p)
        v = D[i]
        for p in sol:
            v ^= G[p]
        r, c = FB.reduce(v)
        if r:
            ok = False
        rests.append(c)

    if verbose:
        print(f'  per-output solve: {ok}')
        if ok:
            sizes = [len(masks[p]) for p in sel]
            print(f'  mask sizes: min {min(sizes)} max {max(sizes)} mean {np.mean(sizes):.2f}')
            used = [len(c) for c in rests]
            print(f'  linear-rest feature counts: min {min(used)} max {max(used)} '
                  f'mean {np.mean(used):.2f}')

    # ---- build the pruned plan
    if not ok:
        return None

    def maskvec(idxs):
        m = np.zeros(30, np.uint8)
        for i in idxs:
            m[i] = 1
        return m

    def restvec(c):
        m = np.zeros(nf, np.uint8)
        for j, x in c.items():
            m[j] = x
        return m

    newP = dict(
        early=P['early'],
        ands=P['ands'].copy(),
        B=P['B'].copy(),
        U=P['U'][sel].copy(),
        V=P['V'][sel].copy(),
        M=np.stack([maskvec(masks[p]) for p in sel]),
        R=np.stack([restvec(c) for c in rests]),
    )
    return newP, dict(nP_old=len(G), nP_new=len(sel), dimF=dimF, dimQ=q,
                      rankG=rankG, spans=spans)


def plan_to_literal(P):
    """a Python literal for the plan dict (for --plan-file)"""
    import pprint
    d = dict(P)
    for key in ('ands', 'B', 'U', 'V', 'M', 'R'):
        d[key] = np.asarray(d[key]).tolist()
    return pprint.pformat(d, width=100, sort_dicts=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', type=int)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--emit')
    ap.add_argument('--tree', default='v149')
    args = ap.parse_args()

    plans = CP.decode_plans()
    if args.all:
        for k in sorted(plans):
            analyse(plans[k], k, tree=args.tree)
            print()
        return 0

    k = args.batch
    P = plans[k]
    res = analyse(P, k, tree=args.tree)
    if res is None:
        return 1
    newP, info = res
    nb, nmix = (66, 9) if newP['early'] > 0 else (68, 8)
    tof_old = nb + 6 + nmix + (2 if newP['early'] > 0 else 0) + info['nP_old']
    tof_new = nb + 6 + nmix + (2 if newP['early'] > 0 else 0) + info['nP_new']
    print(f'  Toffolis: {tof_old} -> {tof_new}  (saves {tof_old - tof_new})')
    if args.emit:
        out = pathlib.Path(args.emit)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(plan_to_literal(newP))
        print(f'  wrote {out}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
