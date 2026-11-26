#!/usr/bin/env python3
"""chem_mitm.py -- MEET-IN-THE-MIDDLE on the products of one loader.

THE QUESTION
    A loader's plan is correct iff, for every output i,

        pi(D_i)  =  XOR_{p in M_i} pi(g_p)          (mod the feature span F)

    where pi is the quotient by F = span(the cached features) and M_i is the
    set of products that feed output i.  The old (unwired) loaders use 98
    products and every output is fed by 14-29 of them.  If some output can be
    fed by a SMALLER subset of the SAME products, then the products outside
    that subset may become unused -- and an unused product is a free Toffoli.

    This is an exact subset-sum over GF(2), solved with a meet-in-the-middle:
    2^(m/2) subsets per half, m <= 30.

Usage: chem_mitm.py <tree-dir> [batch ...]
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219


def build_piv(vectors):
    piv = {}
    for v in vectors:
        v = int(v)
        while v:
            b = v.bit_length() - 1
            row = piv.get(b)
            if row is None:
                piv[b] = v
                break
            v ^= row
    return piv


def reduce_mod(v, piv):
    v = int(v)
    while v:
        b = v.bit_length() - 1
        row = piv.get(b)
        if row is None:
            return v
        v ^= row
    return 0


def min_subset(classes, target):
    """minimum number of classes whose XOR is target (or None)."""
    m = len(classes)
    if m == 0:
        return 0 if target == 0 else None
    h = m // 2
    def enum(part):
        out = {}
        n = len(part)
        for s in range(1 << n):
            x = 0
            c = 0
            ss = s
            while ss:
                i = (ss & -ss).bit_length() - 1
                ss &= ss - 1
                x ^= part[i]
                c += 1
            if x not in out or out[x][0] > c:
                out[x] = (c, s)
        return out
    L = enum(classes[:h])
    R = enum(classes[h:])
    best = None
    for x, (c, s) in L.items():
        y = target ^ x
        r = R.get(y)
        if r is not None and (best is None or c + r[0] < best[0]):
            best = (c + r[0], s | (r[1] << h))
    return None if best is None else best[0]


def main() -> int:
    tree = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'work/trees/v149/dfthcsos')
    ks = [int(a) for a in sys.argv[2:] if not a.startswith('--')] or [0]
    states = CE.chain_states(tree / 'submission.npz')
    for k in ks:
        ops, sel, wq = CE.parse_kmx(tree / f'angle_k_{k}.kmb')
        zin = states[k]
        cur = {}
        feat_at = {}
        for i, q in enumerate(sel):
            cur[q] = CE.fun((CE.ADDR >> i) & 1)
        for j, q in enumerate(wq):
            cur[q] = CE.fun(zin[j])
        feats, prods = [], []
        fan = []
        for idx, (t, a, c) in enumerate(ops):
            if t == 'CX':
                if 11 <= a[0] < 46 and 11 <= a[1] < 46:
                    fan.append((a[0], a[1]))
                cur[a[1]] = cur.get(a[1], 0) ^ cur.get(a[0], 0)
            elif t == 'X':
                cur[a[0]] = cur.get(a[0], 0) ^ CE.ALL
            elif t == 'CCX':
                u, v = cur.get(a[0], 0), cur.get(a[1], 0)
                if a[2] >= 46:
                    feat_at[a[2]] = u & v
                    feats.append(u & v)
                else:
                    m = {a[2]} | {dst for src, dst in fan if src == a[2]}
                    prods.append((u & v, m))
                    fan = []
                cur[a[2]] = cur.get(a[2], 0) ^ (u & v)
            elif t == 'HMR':
                feat_at[a[0]] = 0
                cur[a[0]] = 0
        piv = build_piv(feats)
        classes = [reduce_mod(g, piv) for g, _ in prods]
        D = [CE.fun(states[k + 1][j]) for j in range(35)]
        sizes = []
        mins = []
        for j, q in enumerate(wq):
            idxs = [p for p, (_, m) in enumerate(prods) if q in m]
            if not idxs:
                continue
            tgt = reduce_mod(D[j], piv)
            ms = min_subset([classes[p] for p in idxs], tgt)
            sizes.append(len(idxs))
            mins.append(ms)
        print(f'=== batch k={k}: {len(feats)} features, {len(prods)} products')
        print(f'    products per output: {dict(sorted(Counter(sizes).items()))}')
        print(f'    MINIMUM subset per output: {dict(sorted(Counter(mins).items()))}')
        gain = sum(s - (m if m is not None else s) for s, m in zip(sizes, mins))
        print(f'    total removable product slots (upper bound on saved Toffolis): {gain}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
