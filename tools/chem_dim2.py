#!/usr/bin/env python3
"""chem_dim2.py -- the DIMENSION BUDGET of a loader (the real lower bound).

WHY dim Q is not the right bound
    dim Q = dim(span{pi(D_i)}) = 23..24 counts the quotient-space dimension.
    But the *structure* of a product's contribution is what limits the count:

    A product u.v with u = alpha_u + q_u(low), v = alpha_v + q_v(low) has

        u.v = alpha_u alpha_v                       (a bank function)
            + alpha_u q_v + alpha_v q_u             (bank x low profile)
            + q_u q_v                               (low only)

    The FIRST term is uniform over the 16 columns, so it cancels in the
    column-difference pattern  d_j + d_0  that a product has to reproduce.
    What is left per column is a combination of TWO bank directions,
    alpha_u and alpha_v.  So a product supplies at most TWO independent bank
    directions to every output in its mask.

    Therefore, if output i needs the bank directions
        { d_j + d_0 : j = 1..15 }   (the "difference directions")
    to be spanned by the products that serve it, and the total number of
    independent directions over all outputs is S, then

        nP  >=  ceil(S / 2)

    because every product contributes two directions shared by all outputs in
    its mask.  This is exactly the counting in goodpjw2008's published prose
    ("The number of products is therefore half the number of dimensions that
    all 76 banks together need", "89 + 88 + 83 = 260 dimensions instead of
    262 for 24 outputs" -> 130 products).

    This script measures S for every batch and compares the bound with the
    public plans' actual product counts.

Usage: chem_dim2.py [submission.npz]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402

NBANK, NLOW = 77, 16


def gf2_rank_cols(cols):
    """rank over GF(2) of a list of 77-bit ints"""
    basis = {}
    r = 0
    for v in cols:
        cur = v
        while cur:
            p = cur.bit_length() - 1
            e = basis.get(p)
            if e is None:
                basis[p] = cur
                r += 1
                break
            cur ^= e
    return r


def joint_rank(d):
    """rank over GF(2) of the 30 outputs' difference matrices (15x77 each)

    A product contributes to the difference pattern at most TWO rank-1
    terms (Delta q_v tensor alpha_u and Delta q_u tensor alpha_v); the
    alpha_u alpha_v term is uniform over the columns and cancels.  So a
    family of nP products spans a space of dimension <= 2 nP in the
    difference-pattern space, and the 30 targets' patterns must lie in it:

        nP  >=  ceil(joint_rank / 2).
    """
    basis = {}
    rank = 0
    flat_all = []
    for i in range(d.shape[0]):
        cols = []
        for j in range(NLOW):
            v = 0
            for b in range(NBANK):
                idx = b * NLOW + j
                if idx < d.shape[1] and d[i][idx]:
                    v |= 1 << b
            cols.append(v)
        # flatten the 15 difference vectors into one 15*77-bit integer
        flat = 0
        for jj, j in enumerate(range(1, NLOW)):
            flat |= (cols[j] ^ cols[0]) << (jj * NBANK)
        flat_all.append(flat)
        cur = flat
        while cur:
            p = cur.bit_length() - 1
            e = basis.get(p)
            if e is None:
                basis[p] = cur
                rank += 1
                break
            cur ^= e
    # the dimension of the BANK-DIRECTION space: the span of all the
    # difference rows (77-bit vectors) over all outputs and columns
    dbasis = {}
    drank = 0
    for flat in flat_all:
        for jj in range(NLOW - 1):
            row = (flat >> (jj * NBANK)) & ((1 << NBANK) - 1)
            cur = row
            while cur:
                p = cur.bit_length() - 1
                e = dbasis.get(p)
                if e is None:
                    dbasis[p] = cur
                    drank += 1
                    break
                cur ^= e
    return rank, drank


def main():
    npz = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    plans = CP.decode_plans()

    print(f'{npz}   angle_words {W.shape}')
    print()
    print(f'{"k":>3s} {"nOut":>5s} {"S(sum dirs)":>12s} {"jointRank":>10s} {"ceil/2":>7s} '
          f'{"dirs":>6s} {"ceil/2":>7s} {"public nP":>9s}')
    for k in range(15):
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[CP.OUTS]
        total = 0
        mx = 0
        for i in range(30):
            # the 16 column bank vectors of this output
            cols = []
            for j in range(NLOW):
                v = 0
                for b in range(NBANK):
                    idx = b * NLOW + j
                    if idx < d.shape[1] and d[i][idx]:
                        v |= 1 << b
                cols.append(v)
            diffs = [cols[j] ^ cols[0] for j in range(1, NLOW)]
            r = gf2_rank_cols(diffs)
            total += r
            mx = max(mx, r)
        jr, drank = joint_rank(d)
        nP = plans[k]['U'].shape[0] if k in plans else None
        pub = f'{nP:9d}' if nP else '        -'
        flag = '' if nP is None else ('   (3.2x the bound)' if nP >= 3 * drank / 2 else '   near bound')
        print(f'{k:3d} {30:5d} {total:12d} {jr:10d} {-(-jr // 2):7d} {drank:6d} '
              f'{-(-drank // 2):7d} {pub}{flag}')

    print()
    print('S       = sum over outputs of the rank of the 15 column-difference bank vectors')
    print('jointRank = rank of all 30 difference matrices together (15x77 each)')
    print('nP >= ceil(jointRank/2): a product contributes at most TWO rank-1 terms')
    print('to the difference pattern (the alpha_u alpha_v term is uniform and cancels).')
    print('dirs = dimension of the BANK-DIRECTION space (all difference rows);')
    print('nP >= ceil(dirs/2): every product supplies two bank directions.')


if __name__ == '__main__':
    raise SystemExit(main())
