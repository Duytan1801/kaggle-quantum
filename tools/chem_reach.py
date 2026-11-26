#!/usr/bin/env python3
"""chem_reach.py — is the batch delta reachable in the plan scheme at all?

THE QUESTION
    goodpjw2008 re-solved ten of the fifteen chemistry loaders with the
    "plan" scheme (68 cached bank ANDs + 6 low ANDs + 8 mixed features + a
    rank-1 product per Toffoli).  Five batches (k = 0,1,5,7,11) were left
    untouched at 240-245 Toffolis.  Is that because the search was hard, or
    because the scheme CANNOT represent those deltas?

THE MODEL (verified exactly against all ten public plans -- see chem_rec.py)
    A plan's features are functions of the address (bank = a>>4, low = a&15):

      * 11 address bits
      * 5 QUADS features:  low_x AND (low >= 2^y)
      * 68 cached bank ANDs: products of two linear forms over the 7 bank
        bits -- so their span is every degree<=2 polynomial in the bank bits
      * 6 LOW ANDs:  (AND of a subset of the low bits) AND low_t
      * 8 mixed:  (low == 7 or 14) AND (a bank mask)

    A product is L^U AND L^V for two arbitrary linear forms L over the
    features, so every output delta is a QUADRATIC FORM in the feature
    vector:

        D[i] = sum_p mask[p][i] * (L^U_p . L^V_p)  +  (linear rest)

    Hence D[i] must lie in

        Q = span{ f } + span{ f_i * f_j : i < j }.

THE TEST
    Build the MAXIMAL feature set (every degree<=2 bank polynomial, every
    possible mixed bank mask) and the maximal quadratic space Q.  Then ask
    whether each output delta lies in Q.

    * NO  => the scheme cannot represent that output, whatever the search
            does.  H42 is dead for that batch.
    * YES => representable in principle; the remaining question is the number
            of products needed.

    The ten public plans are the control: their deltas must test YES.

Usage:
    chem_reach.py [submission.npz]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402

NV = CP.NV
ADDR = CP.ADDR
BANK = ADDR >> 4
LOW = ADDR & 15
NBANK = 77
NLOW = 16


def fun(f):
    return int.from_bytes(np.packbits(np.asarray(f, bool), bitorder='little').tobytes(), 'little')


def cells_to_addr(v):
    """1232-cell bool vector -> int over the 1219 addresses"""
    return fun(v[BANK * NLOW + LOW])


def bank_poly_bits():
    """-> (linear, quadratic) lists of 77-vectors.

    `linear[m]` is the function "XOR of bank bits selected by m";
    `quad[m1][m2]` is their product.  Together they span every degree<=2
    polynomial in the seven bank bits.
    """
    lin = []
    for mask in range(1 << 7):
        v = np.zeros(NBANK, bool)
        for b in range(NBANK):
            acc = False
            for i in range(7):
                if (mask >> i) & 1:
                    acc ^= bool((b >> i) & 1)
            v[b] = acc
        lin.append(v)
    quad = []
    for v1 in lin:
        for v2 in lin:
            quad.append(v1 & v2)
    return lin, quad


def bank_fn(v77):
    """77-vector of bank values -> address function int"""
    return fun(v77[BANK])


def build_features(maximal=True):
    """-> list of (label, int function over the 1219 addresses)"""
    feats = []
    feats.append(('const', fun(np.ones(NV, bool))))
    for i in range(11):
        feats.append((f'addr{i}', fun(((ADDR >> i) & 1).astype(bool))))
    for j, (x, y) in enumerate(CP.QUADS):
        feats.append((f'quad{j}', fun((((LOW >> x) & 1) & (LOW >> y)).astype(bool))))
    lin, quad = bank_poly_bits()
    if maximal:
        # a basis of every degree<=2 polynomial in the bank bits (29 dims)
        seen = set()
        for v in lin:
            seen.add(bank_fn(v))
        for v in quad:
            seen.add(bank_fn(v))
        for n, t in enumerate(sorted(seen)):
            feats.append((f'bank_q{n}', t))
    for n, (s, t) in enumerate(CP.LOW_ANDS):
        u = np.ones(NLOW, bool)
        for x in s:
            u &= ((np.arange(NLOW) >> x) & 1).astype(bool)
        v = ((np.arange(NLOW) >> t) & 1).astype(bool)
        f = np.zeros(NV, bool)
        f[:] = (u & v)[LOW]
        feats.append((f'low{n}', fun(f)))
    if maximal:
        # the mixed space: any bank mask AND (low == 7 or 14).  A basis of it
        # is "bank b, low c" for every (b, c); a real plan has only eight of
        # them, so this is a strict upper bound on what a plan can reach.
        for c in (7, 14):
            le = (LOW == c)
            for b in range(NBANK):
                v77 = np.zeros(NBANK, bool)
                v77[b] = True
                f = le & v77[BANK]
                if f.any():
                    feats.append((f'mix{c}_{b}', fun(f)))
    return feats


def quad_basis(feats):
    """-> (pivot dict, dim) for Q = span(f) + span(f_i * f_j)"""
    basis: dict[int, int] = {}

    def reduce_vec(v):
        while v:
            p = v.bit_length() - 1
            b = basis.get(p)
            if b is None:
                return v, p
            v ^= b
        return 0, None

    for _, f in feats:
        r, p = reduce_vec(f)
        if r:
            basis[p] = r
    n = len(feats)
    ints = [f for _, f in feats]
    for i in range(n):
        ai = ints[i]
        for j in range(i + 1, n):
            r, p = reduce_vec(ai & ints[j])
            if r:
                basis[p] = r
    return basis


def in_span(basis, vec):
    v = vec
    while v:
        p = v.bit_length() - 1
        b = basis.get(p)
        if b is None:
            return False
        v ^= b
    return True


def main():
    npz = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    print(f'{npz}   angle_words {W.shape}')

    import chem_struct as CS                                   # noqa: E402

    plans = CP.decode_plans()

    # ---- control: the real feature set of each public plan ----------
    print('CONTROL -- each public plan\'s OWN feature set vs its own batch')
    for k in sorted(plans):
        feats = [(f'f{i}', cells_to_addr(f)) for i, f in enumerate(CS.build_features(plans[k]))]
        basis = quad_basis(feats)
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[CP.OUTS]
        mem = [in_span(basis, fun(d[i])) for i in range(30)]
        print(f'  k={k:2d} nf={len(feats):3d} dimQ={len(basis):4d} inQ={sum(mem):2d}/30 '
              f'{"".join("." if m else "X" for m in mem)}')
    print()

    feats = build_features(maximal=True)
    print(f'maximal feature count: {len(feats)}')
    basis = quad_basis(feats)
    print(f'dim Q (maximal quadratic space): {len(basis)}')
    print()

    print(f'{"k":>3s} {"nIn":>4s}   per-output membership of D_k[i] in Q')
    for k in range(15):
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[CP.OUTS]
        mem = []
        for i in range(30):
            t = fun(d[i])
            mem.append(in_span(basis, t))
        n = sum(mem)
        flag = '' if n == 30 else ('   <-- NOT REACHABLE' if n == 0 else '   <-- partial')
        print(f'{k:3d} {n:4d}   {"".join("." if m else "X" for m in mem)}{flag}')


if __name__ == '__main__':
    raise SystemExit(main())
