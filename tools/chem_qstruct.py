#!/usr/bin/env python3
"""chem_qstruct.py -- the geometry of the target quotient space Q.

WHY THIS MATTERS
    A plan is correct iff   span{ pi(g_p) }  CONTAINS  Q = span{ pi(D_i) },
    where pi is the quotient by the feature span F (everything in F is free
    in the loader: the "linear rest" is applied with free CNOTs).

    So the search for a cheaper plan is exactly:  find the fewest products
    whose classes span Q.  The lower bound is dim Q.

    The quotient V/F is small and has a clean shape.  Write a function on
    the address grid as a 16 (columns) x 77 (banks) matrix.  The features
    are
        * bank functions  (68 cached ANDs + 7 address bank bits)  -> the
          same bank vector in EVERY column,
        * low functions   (4 low bits + 5 QUADS + 6 low ANDs)      -> one
          bank column, constant over banks,
        * mixed features  (bank function AND low==7 / low==14)    -> only on
          the two special columns,
        * the constant.
    Hence, per ordinary column, F reaches the subspace
    span(bank features) + <1> of the 77-dim bank space, and the quotient
    per column is 77 - dim(that) = 2 dimensions; on columns 7 and 14 the
    mixed features make the quotient zero.  The whole quotient V/F is
    therefore 28-dimensional, and Q (23 dims) sits inside it.

    This script prints that geometry and measures the hit rate of random
    products against Q, which decides whether a structured search (or a
    randomised one) can beat the public 123..132 products.

Usage: chem_qstruct.py [batch]
"""
from __future__ import annotations

import pathlib
import random
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_prune as CPR                                     # noqa: E402

NBANK = 77
NLOW = 16


def bank77_of_bits(bits):
    """a 77-bit bank mask"""
    v = 0
    for i, b in enumerate(bits):
        if b:
            v |= 1 << i
    return v


def main():
    k = int(sys.argv[1]) if len(sys.argv) > 1 else 14
    plans = CP.decode_plans()
    P = plans[k]
    f = CPR.plan_features(P)
    swap = P['early'] > 0
    nb = 66 if swap else 68
    nf = len(f)

    # ---- feature classification -------------------------------------
    bank_idx = list(range(5, 12)) + list(range(17, 17 + nb))     # address bank
    # bits + cached bank ANDs
    mixed_start = nf - (9 if swap else 8)
    mixed_idx = list(range(mixed_start, nf))
    low_idx = [0] + list(range(1, 5)) + list(range(12, 17))
    low_and_start = (17 + nb + 2) if swap else (17 + nb)
    low_idx += list(range(low_and_start, low_and_start + 6))
    print(f'batch {k}: nf={nf} swap={swap}')
    print(f'  bank-side feature indices: {len(bank_idx)}   low-side: {len(low_idx)}'
          f'   mixed: {len(mixed_idx)}')

    # ---- bank-side subspace ----------------------------------------
    # the cached bank features as 77-bit masks (they are bank-only)
    def bank_mask_of_feature(j):
        """the 77-bit bank mask of a bank-only feature (index j)"""
        v = f[j]
        # a bank-only feature is constant over the 16 columns of a bank
        m = 0
        for b in range(NBANK):
            bit = (v >> (b * NLOW)) & 1
            if bit:
                m |= 1 << b
        return m

    Bc = [bank_mask_of_feature(j) for j in bank_idx]
    # + the constant bank vector
    Bc = Bc + [bank77_of_bits([1] * NBANK)]
    BB = CPR.Basis((i, Bc[i]) for i in range(len(Bc)))
    print(f'  bank subspace dim {BB.rank()} of {NBANK}  -> per-column quotient '
          f'{NBANK - BB.rank()}')

    # ---- the target classes in quotient coordinates -----------------
    z = np.load(ROOT / 'work/trees/v149/dfthcsos/submission.npz')
    W = z['angle_words']
    wk = CP.word_bits(W, k)
    wp = CP.word_bits(W, k - 1)
    d = (wk ^ wp)[CP.OUTS]
    D = [CPR.fun(d[i]) for i in range(30)]

    FB = CPR.Basis((j, f[j]) for j in range(nf))
    resD = [FB.reduce(t)[0] for t in D]

    # per-column bank coordinates: the residual of the column's bank vector
    # modulo the bank subspace
    def col_coords(func):
        """-> list of 16 residual masks (the quotient coordinates per column)"""
        out = []
        for j in range(NLOW):
            v = 0
            for b in range(NBANK):
                if (func >> (b * NLOW + j)) & 1:
                    v |= 1 << b
            out.append(BB.reduce(v)[0])
        return out

    coordsD = [col_coords(r) for r in resD]
    QB = CPR.Basis()
    for c in coordsD:
        flat = 0
        for j, cv in enumerate(c):
            flat |= (cv & ((1 << NBANK) - 1)) << (j * NBANK)
        QB.add(flat, {})
    print(f'  dim Q (from the per-column coordinates): {QB.rank()}')

    # how do the coordinates look?
    nz = [sum(1 for cv in c if cv) for c in coordsD]
    print(f'  non-zero coordinate columns per output: min {min(nz)} max {max(nz)} '
          f'(of {NLOW})')

    # ---- random products: hit rate against Q -----------------------
    # u = alpha_u (bank) + q_u (low), v = alpha_v (bank) + q_v (low)
    random.seed(11)

    def rand_combo(idxs):
        v = 0
        for j in idxs:
            if random.getrandbits(1):
                v ^= f[j]
        return v

    # a product's class, computed directly: build the function and reduce
    def product_class(gu, gv):
        g = gu & gv
        r, _ = FB.reduce(g)
        flat = 0
        for j in range(NLOW):
            v = 0
            for b in range(NBANK):
                if (r >> (b * NLOW + j)) & 1:
                    v |= 1 << b
            flat |= (BB.reduce(v)[0] & ((1 << NBANK) - 1)) << (j * NBANK)
        return flat

    N = 4000
    hits = 0
    hits_ordinary = 0
    for _ in range(N):
        gu = rand_combo(bank_idx + low_idx)
        gv = rand_combo(bank_idx + low_idx)
        flat = product_class(gu, gv)
        if QB.contains(flat):
            hits += 1
    print(f'  random products hitting Q: {hits}/{N}  ({100.0 * hits / N:.2f}%)')

    # pure bank products (q_u = q_v = 0)
    hits2 = 0
    for _ in range(N):
        gu = rand_combo(bank_idx)
        gv = rand_combo(bank_idx)
        flat = product_class(gu, gv)
        if QB.contains(flat):
            hits2 += 1
    print(f'  pure-bank products hitting Q: {hits2}/{N}  ({100.0 * hits2 / N:.2f}%)')


if __name__ == '__main__':
    raise SystemExit(main())
