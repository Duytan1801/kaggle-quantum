#!/usr/bin/env python3
"""chem_colrank.py -- the COLUMN BLOCKING of the loader problem.

THE STRUCTURE (derived from the emitter + the public plans)
    A product g = u.v with u = alpha_u + x(low), v = alpha_v + y(low) has the
    column-difference structure

        d_j(g) = d_y(j) . alpha_u  +  d_x(j) . alpha_v ,

    where d_x(j) = x(j) XOR x(0) is the DIFFERENCE of the low profile.  So a
    product contributes TWO bank directions, each to a (possibly different)
    set of columns, and NOTHING to the column differences elsewhere.

    The linear rest is free, but not arbitrarily: the free parts are
      * bank-only features (the span W of the 68 cached bank ANDs and the
        7 bank address bits) -- the same vector in every column, hence
        invisible in a column DIFFERENCE,
      * low-only features -- their difference is a single vector
        e = (banks 0..75 set, bank 76 clear), because the address grid
        stops at 1219 (bank 76 has only lows 0,1,2),
      * the 8 mixed features -- only at columns 7 and 14.

    Hence for every column j the 30 outputs' difference rows must live in

        span{alpha's of the products active at j}  +  span{e}  [+ mixed at 7,14]

    and the number of products is at least

        nP  >=  ( sum_j  dim( the rows at column j )  ) / 2

    because each product carries two directions.  THIS NUMBER decides whether
    a plan with nP ~ 40..80 is even possible.

Usage: chem_colrank.py [submission.npz]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402

NBANK, NLOW = 77, 16


def rank(vs):
    b = {}
    r = 0
    for v in vs:
        cur = v
        while cur:
            p = cur.bit_length() - 1
            e = b.get(p)
            if e is None:
                b[p] = cur
                r += 1
                break
            cur ^= e
    return r


def main():
    npz = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    plans = CP.decode_plans()

    # the free low-only difference direction: banks 0..75 set, bank 76 clear
    E = (1 << 76) - 1

    print(f'{npz}')
    print()
    print(f'{"k":>3s} | {"r_0":>4s} | ' + ' '.join(f'j{j:<2d}' for j in range(1, 16)) +
          f' | {"sum_j":>6s} {"/2":>4s} | {"union":>6s} | public nP')
    for k in range(15):
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[CP.OUTS]
        colj = [[] for _ in range(NLOW)]
        col0 = []
        for i in range(30):
            cols = []
            for j in range(NLOW):
                v = 0
                for b in range(NBANK):
                    idx = b * NLOW + j
                    if idx < d.shape[1] and d[i][idx]:
                        v |= 1 << b
                cols.append(v)
            col0.append(cols[0])
            for j in range(1, NLOW):
                colj[j].append(cols[j] ^ cols[0])
        r0 = rank(col0)
        rj = [rank(colj[j]) for j in range(1, NLOW)]
        s = sum(rj)
        union = rank([x for j in range(1, NLOW) for x in colj[j]])
        nP = plans[k]['U'].shape[0] if k in plans else None
        pub = f'{nP:10d}' if nP else f'{"-":>10s}'
        print(f'{k:3d} | {r0:4d} | ' + ' '.join(f'{r:2d} ' for r in rj) +
              f' | {s:6d} {s // 2:4d} | {union:6d} | {pub}')

    print()
    print('r_j  = rank of the 30 outputs\' column-j DIFFERENCE rows (the rows the')
    print('       products must cover at column j, modulo the free parts)')
    print('sum_j/2 = the product-count lower bound (two directions per product)')
    print('union  = rank of all the difference rows together')
    print()
    print('the free low-only difference direction e is ONE vector; removing it')
    print('changes the per-column ranks by at most 1, so it cannot close a gap')
    print('of more than 15 columns x 1 dim = 15 products.')


if __name__ == '__main__':
    raise SystemExit(main())
