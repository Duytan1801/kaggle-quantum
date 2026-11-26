#!/usr/bin/env python3
"""chem_quad.py — is the batch delta a quadratic form in the loader features?

THE MODEL
    A goodpjw-style loader plan has 99 (or 100) *features*  f_j(a)  -- pure
    functions of the 11 address bits -- and nP *products*

        g_p(a) = L^U_p(a) AND L^V_p(a),      L^U_p = XOR of ~49 features,

    each XORed into a 30-bit output mask, plus a linear rest.  So every
    output delta is a QUADRATIC FORM in the feature vector:

        D_k[i](a) = sum_p M_p[i] * (c_p . F(a)) * (d_p . F(a)) + (r_i . F(a))

    where F(a) is the 99-bit feature vector at address a.

    The set of all such functions is the quadratic space

        Q = span{ f_i } + span{ f_i * f_j : i < j },

    of dimension at most 99 + C(99,2) = 4950.

THE TEST
    For a batch k and output i:  is D_k[i] in Q?

    * If NO for some output, then NO choice of the 68 cached bank ANDs and the
      8 mixed features can ever represent that delta in this scheme, whatever
      the search does.  That is a hard structural limit.
    * If YES, the delta is representable in principle and the question becomes
      whether it can be written with <= 132 rank-1 terms.

    A feature set is batch-specific in the public plans, so we test each batch
    against the feature sets of the ten public plans (and their union).

Usage:
    chem_quad.py <submission.npz>
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_struct as CS                                      # noqa: E402

CELLS = CS.CELLS
VALID = CS.VALID


def to_int(b):
    """numpy bool vector -> python int bitmask (bit p = cell p)"""
    return int.from_bytes(np.packbits(b, bitorder='little').tobytes(), 'little')


def quad_basis(feats):
    """-> (basis dict, rank, span_size) for Q = span{f_i, f_i*f_j}"""
    ints = [to_int(f) for f in feats]
    basis = {}

    def reduce_vec(v):
        while v:
            p = v.bit_length() - 1
            b = basis.get(p)
            if b is None:
                return v, p
            v ^= b
        return 0, None

    for i, a in enumerate(ints):
        r, p = reduce_vec(a)
        if r:
            basis[p] = r
    n = len(ints)
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
    path = pathlib.Path(sys.argv[1]).resolve()
    z = np.load(path)
    W = z['angle_words']
    plans = CP.decode_plans()

    # target deltas as int masks
    tgt = {}
    for k in range(15):
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[CS.OUTS]
        tgt[k] = [to_int(CS.cellvec(d[i])) for i in range(30)]

    # feature sets of the ten public plans
    feat = {k: CS.build_features(plans[k]) for k in plans}

    print(f'{path}   angle_words {W.shape}   cells {CELLS}   valid {int(VALID.sum())}')
    print()
    print('--- each public plan\'s OWN feature set against its own batch ---')
    print(f'{"k":>3s} {"nf":>4s} {"dimQ":>6s} {"inQ":>4s}  per-output membership (0..29)')
    for k in sorted(plans):
        f = feat[k]
        B = quad_basis(f)
        mem = [in_span(B, t) for t in tgt[k]]
        print(f'{k:3d} {len(f):4d} {len(B):6d} {sum(mem):4d}  '
              f'{"".join("." if m else "X" for m in mem)}')

    print()
    print('--- union of ALL ten public feature sets vs all fifteen batches ---')
    allf = []
    for k in sorted(plans):
        allf.extend(feat[k])
    # dedupe
    seen = set()
    uniq = []
    for f in allf:
        t = to_int(f)
        if t not in seen:
            seen.add(t)
            uniq.append(f)
    B = quad_basis(uniq)
    print(f'union feature count {len(uniq)}   dim Q = {len(B)}')
    print(f'{"k":>3s} {"inQ":>4s}  per-output membership')
    for k in range(15):
        mem = [in_span(B, t) for t in tgt[k]]
        print(f'{k:3d} {sum(mem):4d}  {"".join("." if m else "X" for m in mem)}')

    print()
    print('--- MAXIMAL feature set: all degree<=2 polys in b0..b6 + all low funcs ---')
    # bank side: every polynomial of degree <= 2 in the 7 bank bits
    bankp = []
    for mask in range(1 << 7):
        v = np.zeros(CS.NBANK, bool)
        for b in range(CS.NBANK):
            acc = False
            for i in range(7):
                if (mask >> i) & 1:
                    acc ^= bool((b >> i) & 1)
            v[b] = acc
        bankp.append(v)
    # low side: all 16 functions of the 4 low bits are available in principle
    lowf = []
    for m in range(16):
        v = np.zeros(CS.NLOW, bool)
        for l in range(CS.NLOW):
            acc = False
            for i in range(4):
                if (m >> i) & 1:
                    acc ^= bool((l >> i) & 1)
            v[l] = acc
        lowf.append(v)
    # mixed: (low == c) AND bank
    mixed = []
    for c in (7, 14):
        for bmask in range(1 << 7):
            bv = np.zeros(CS.NBANK, bool)
            for b in range(CS.NBANK):
                acc = False
                for i in range(7):
                    if (bmask >> i) & 1:
                        acc ^= bool((b >> i) & 1)
                bv[b] = acc
            lv = np.zeros(CS.NLOW, bool)
            lv[c] = True
            mixed.append(CS.grid_of_bank77(bv) & CS.cellvec(lv[CS.LOW]))
    feats = []
    feats.append(np.ones(CELLS, bool))
    for b in bankp:
        feats.append(CS.grid_of_bank77(b))
    for l in lowf:
        feats.append(CS.cellvec(l[CS.LOW]))
    feats.extend(mixed)
    B = quad_basis(feats)
    print(f'maximal feature count {len(feats)}   dim Q = {len(B)}')
    print(f'{"k":>3s} {"inQ":>4s}  per-output membership')
    for k in range(15):
        mem = [in_span(B, t) for t in tgt[k]]
        print(f'{k:3d} {sum(mem):4d}  {"".join("." if m else "X" for m in mem)}')


if __name__ == '__main__':
    raise SystemExit(main())
