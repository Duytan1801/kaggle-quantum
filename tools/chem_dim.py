#!/usr/bin/env python3
"""chem_dim.py — how many rank-1 products does a batch NEED?

THE COUNTING ARGUMENT
    A plan's output delta is

        D[i] = linear_rest_i  +  XOR_{p : i in mask_p} (L^U_p . L^V_p)

    and a product (L^U . L^V), with L^U = alpha(bank) + q1(low) and
    L^V = beta(bank) + q2(low), expands to

        alpha.beta . (q1.q2) + alpha.q2 + beta.q1

    i.e. a matrix of rank at most THREE over GF(2).  So n products can span
    at most 3n dimensions.

    The linear rest absorbs anything in span(F) (F = the plan's feature
    space), so the products must span the quotient

        residual_k = dim( span{D_i} + span(F) ) - dim( span(F) )

    and therefore

        n_products  >=  ceil(residual_k / 3).

    This script measures residual_k for every batch, with F taken as the
    MAXIMAL feature space (every bank function, every low feature, every
    mixed feature), which gives the most generous possible lower bound.

    The ten public plans are the control: their measured nP (123..132) must
    be at least the bound.

Usage: chem_dim.py [submission.npz]
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


def rank_of(vectors):
    """GF(2) rank of a list of ints"""
    basis: dict[int, int] = {}
    for v in vectors:
        while v:
            p = v.bit_length() - 1
            b = basis.get(p)
            if b is None:
                basis[p] = v
                break
            v ^= b
    return len(basis)


def span_add(a, b):
    """basis dict union"""
    out = dict(a)
    for v in b:
        while v:
            p = v.bit_length() - 1
            bb = out.get(p)
            if bb is None:
                out[p] = v
                break
            v ^= bb
    return out


def basis_of(vectors):
    basis: dict[int, int] = {}
    for v in vectors:
        while v:
            p = v.bit_length() - 1
            b = basis.get(p)
            if b is None:
                basis[p] = v
                break
            v ^= b
    return basis


def maximal_features():
    """-> list of ints: the most generous feature space a plan could use.

    * every bank function (the 68 cached ANDs can span all of them)
    * the 11 address bits
    * the 5 QUADS features
    * the 6 LOW ANDs
    * every mixed feature (bank function AND low==7 / low==14)
    """
    feats = [fun(np.ones(NV, bool))]
    for i in range(11):
        feats.append(fun(((ADDR >> i) & 1).astype(bool)))
    for (x, y) in CP.QUADS:
        feats.append(fun((((LOW >> x) & 1) & (LOW >> y)).astype(bool)))
    # every bank function
    for b in range(NBANK):
        v = np.zeros(NBANK, bool)
        v[b] = True
        feats.append(fun(v[BANK]))
    # the 6 LOW ANDs
    for (s, t) in CP.LOW_ANDS:
        u = np.ones(NLOW, bool)
        for x in s:
            u &= ((np.arange(NLOW) >> x) & 1).astype(bool)
        v = ((np.arange(NLOW) >> t) & 1).astype(bool)
        f = np.zeros(NV, bool)
        f[:] = (u & v)[LOW]
        feats.append(fun(f))
    # every mixed feature
    for c in (7, 14):
        le = (LOW == c)
        for b in range(NBANK):
            v = np.zeros(NBANK, bool)
            v[b] = True
            feats.append(fun(le & v[BANK]))
    return feats


def main():
    npz = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    F = maximal_features()
    dimF = rank_of(F)
    print(f'{npz}   angle_words {W.shape}')
    print(f'maximal feature space: {len(F)} generators, dim {dimF}')
    print()

    plans = CP.decode_plans()
    print(f'{"k":>3s} {"nOut":>4s} {"dimD":>5s} {"dimF+D":>7s} {"resid":>6s} {"lb(nP)":>7s} '
          f'{"public nP":>9s}')
    for k in range(15):
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[CP.OUTS]
        D = [fun(d[i]) for i in range(30)]
        dimD = rank_of(D)
        bD = basis_of(D)
        bF = basis_of(F)
        bSum = span_add(bF, bD)
        dimSum = len(bSum)
        resid = dimSum - dimF
        lb = -(-resid // 3)
        nP = plans[k]['U'].shape[0] if k in plans else None
        pub = f'{nP:9d}' if nP else '         -'
        flag = '' if nP is None or nP >= lb else '   <-- BOUND VIOLATED'
        print(f'{k:3d} {30:4d} {dimD:5d} {dimSum:7d} {resid:6d} {lb:7d} {pub}{flag}')

    print()
    print('cost per loader = 82 (features) + nP, or 83 + nP in the swap layout')
    print('old loaders for k=0,1,5,7,11 cost 245,240,240,240,240 Toffolis')


if __name__ == '__main__':
    raise SystemExit(main())
