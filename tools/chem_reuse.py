#!/usr/bin/env python3
"""chem_reuse.py -- can a solved batch's products express another batch's targets?

IDEA
    goodpjw2008 re-solved ten of the fifteen chemistry loaders.  Each solved
    plan is a set of "products"  A_p = (XOR of features in U_p) AND (XOR of
    features in V_p), each fed to a mask of outputs.  A plan's output delta is

        D[i] = linear_rest_i  +  XOR_{p : i in mask_p} A_p .

    The products are functions of (bank, low) only -- they do NOT depend on
    which batch they serve.  So a solved plan's product set might span the
    target matrices of an UNSOLVED batch, in which case we could reuse the
    products (with a fresh feature set) and get a 205-Toffoli loader for a
    batch goodpjw left at 240-245.

    This script tests, for every (solved plan, unsolved batch) pair:

      * does  span{A_p}  contain every target matrix M_i of the batch?
      * is the residual (M_i minus the unique product combination) inside
        the span of the plan's own feature set?  (the linear rest must be
        expressible over the features we keep)

    A hit means the batch is reachable with that plan's product count.

Usage: chem_reuse.py [submission.npz]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_struct as CS                                      # noqa: E402

NV = CP.NV
ADDR = CP.ADDR
BANK = ADDR >> 4
LOW = ADDR & 15


def fun(f):
    return int.from_bytes(np.packbits(np.asarray(f, bool), bitorder='little').tobytes(), 'little')


def cells_to_addr(v):
    return fun(v[BANK * 16 + LOW])


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


def reduce_vec(v, basis):
    """-> (residual, coefficients as {pivot: coef})"""
    coef = {}
    while v:
        p = v.bit_length() - 1
        b = basis.get(p)
        if b is None:
            return v, coef
        bv, bc = b
        v ^= bv
        coef = {k: coef.get(k, 0) ^ bc.get(k, 0) for k in set(coef) | set(bc)}
    return 0, coef


def build_basis(vectors):
    """-> {pivot: (vector, {index: 1})}"""
    basis: dict[int, tuple[int, dict[int, int]]] = {}
    for idx, v in enumerate(vectors):
        cur = v
        coef = {idx: 1}
        while cur:
            p = cur.bit_length() - 1
            if p not in basis:
                basis[p] = (cur, coef)
                break
            bv, bc = basis[p]
            cur ^= bv
            coef = {k: coef.get(k, 0) ^ bc.get(k, 0) for k in set(coef) | set(bc)}
            coef = {k: c for k, c in coef.items() if c}
    return basis


def main():
    npz = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    plans = CP.decode_plans()

    # target matrices per batch (30 live outputs)
    tgt = {}
    for k in range(15):
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[CP.OUTS]
        tgt[k] = [cells_to_addr(CS.cellvec(d[i])) for i in range(30)]

    print(f'{npz}')
    print()
    print('--- products of each solved plan ---')
    prod_sets = {}
    for k in sorted(plans):
        P = plans[k]
        f = CS.build_features(P)
        fi = [cells_to_addr(x) for x in f]
        swap = P['early'] > 0
        early = P['early']
        A = []
        for p in range(len(P['U'])):
            u, v = P['U'][p], P['V'][p]
            # the swap layout reuses one ancilla: products before `early` see
            # the ands[66] feature (index 83), the rest the ands[67] one (84)
            def lin(mask, first):
                acc = 0
                if mask[0]:
                    acc ^= fi[0]                      # the constant
                for j in np.nonzero(mask)[0]:
                    if j == 0:
                        continue
                    if swap and j in (83, 84):
                        if (j == 83) != first:
                            continue                  # not live in this phase
                        acc ^= fi[83 if first else 84]
                        continue
                    acc ^= fi[j]
                return acc
            first = (p < early) if swap else True
            au = lin(u, first)
            av = lin(v, first)
            A.append(au & av)
        prod_sets[k] = A
        print(f'  k={k}: {len(A)} products')

    print()
    print('--- can a solved plan\'s products span another batch\'s targets? ---')
    print(f'{"plan":>5s} {"batch":>6s} {"inSpan":>7s} {"residInF":>9s}')
    for kp in sorted(plans):
        A = prod_sets[kp]
        bA = build_basis(A)
        fspan = basis_of([cells_to_addr(x) for x in CS.build_features(plans[kp])])
        for kb in range(15):
            if kb == kp:
                continue
            n_in = 0
            n_res = 0
            for M in tgt[kb]:
                r, coef = reduce_vec(M, bA)
                if r == 0:
                    n_in += 1
                    # residual against the product combination
                    combo = 0
                    for idx, c in coef.items():
                        if c:
                            combo ^= A[idx]
                    res = M ^ combo
                    rr, _ = reduce_vec(res, fspan)
                    if rr == 0:
                        n_res += 1
            if n_in:
                print(f'{kp:5d} {kb:6d} {n_in:7d} {n_res:9d}')


if __name__ == '__main__':
    raise SystemExit(main())
