#!/usr/bin/env python3
"""chem_h48.py -- measure the PRODUCT COUNT needed to express a batch with a
fixed 82-feature (wired) feature space.

The wired loaders use
    F = span{ 1, 11 selection bits, 5 low QUADs, 82 cached AND features }
and write each output delta as  (XOR of products) XOR (an element of F),
where a product is  u AND v  with u, v arbitrary GF(2) combinations of F.
Because AND is bilinear, the set of ALL products spans  span{f_a AND f_b} over
a basis of F.  For the wired F that span has dimension 1217 of 1219, i.e. the
scheme can express *almost every* function -- the question is only HOW MANY
distinct products are needed.

This tool answers that by greedy linear covering:
  * residuals  r_i = D_i reduced mod F
  * W = span{r_i}
  * repeatedly add the product whose reduced image lies in W and matches the
    most residuals (i.e. eliminates the most outputs)

It reports the count trajectory, so the H48 kill criterion
(nP <= 157 for k11) can be read off directly.

Usage: chem_h48.py <tree> <feature-batch> <target-batch> [--max-products N]
"""
from __future__ import annotations

import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219
ADDR = CE.ADDR
LOW = ADDR & 15
BANK = ADDR >> 4
QUADS = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3)]


def add_to(piv, v):
    v = int(v)
    while v:
        b = v.bit_length() - 1
        row = piv.get(b)
        if row is None:
            piv[b] = v
            return True
        v ^= row
    return False


def reduce_v(piv, v):
    v = int(v)
    while v:
        b = v.bit_length() - 1
        row = piv.get(b)
        if row is None:
            return v
        v ^= row
    return 0


def feature_space(tree, k, states):
    """The 99-dim basis of the wired scheme, taken from loader k."""
    ops, sel, wq = CE.parse_kmx(pathlib.Path(tree) / f'angle_k_{k}.kmb')
    cur = {}
    for i, q in enumerate(sel):
        cur[q] = CE.fun((ADDR >> i) & 1)
    for j, q in enumerate(wq):
        cur[q] = CE.fun(states[k][j])
    feats = []
    for t, a, c in ops:
        if t == 'CX':
            cur[a[1]] = cur.get(a[1], 0) ^ cur.get(a[0], 0)
        elif t == 'X':
            cur[a[0]] = cur.get(a[0], 0) ^ CE.ALL
        elif t == 'CCX':
            u, v = cur.get(a[0], 0), cur.get(a[1], 0)
            if a[2] >= 46:
                feats.append(u & v)
            cur[a[2]] = cur.get(a[2], 0) ^ (u & v)
        elif t == 'HMR':
            cur[a[0]] = 0
    lin = [CE.ALL] + [CE.fun((ADDR >> i) & 1) for i in range(11)]
    lin += [CE.fun(((LOW >> x) & 1) & ((LOW >> y) & 1)) for x, y in QUADS]
    return lin + feats, len(feats)


def deltas(tree, k):
    z = np.load(pathlib.Path(tree) / 'submission.npz')
    W = np.asarray(z['angle_words'])
    out = []
    for j in range(5):
        col = 5 * k + j
        for i in range(7):
            bit = ((W[:, col] >> i) & 1).astype(bool)
            prev = np.zeros(NV, bool) if k == 0 else ((W[:, col - 5] >> i) & 1).astype(bool)
            out.append(CE.fun(bit ^ prev))
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    maxp = 400
    for a in sys.argv[1:]:
        if a.startswith('--max-products'):
            maxp = int(a.split('=')[1])
    tree = args[0]
    fk = int(args[1])
    targets = [int(x) for x in args[2:]] or [fk]
    states = CE.chain_states(pathlib.Path(tree) / 'submission.npz')

    t0 = time.time()
    feats, nand = feature_space(tree, fk, states)
    Fp = {}
    for f in feats:
        add_to(Fp, f)
    print(f'[feature k={fk}] {nand} ANDs, |F| = {len(Fp)}', flush=True)

    # product candidates: all pairs of the 99-dim F basis
    basis = list(Fp.values())
    prods = []
    seen = set()
    for a in range(len(basis)):
        fa = basis[a]
        for b in range(a, len(basis)):
            p = fa & basis[b]
            if p and p not in seen:
                seen.add(p)
                prods.append(p)
    print(f'[products] {len(prods)} distinct pairwise ANDs', flush=True)
    Pp = {}
    for p in prods:
        add_to(Pp, p)
    print(f'[span(F + products)] dim = {len(Fp) + len(Pp)} of {NV}', flush=True)

    for tk in targets:
        D = deltas(tree, tk)
        res = [reduce_v(Fp, d) for d in D]
        # W = span of residuals
        Wp = {}
        for r in res:
            if r:
                add_to(Wp, r)
        print(f'\n=== target k={tk}: {sum(1 for r in res if r)}/35 residuals outside F, '
              f'dim W = {len(Wp)}', flush=True)
        # reduced product images
        red = {}
        for p in prods:
            rp = reduce_v(Fp, p)
            if rp:
                red.setdefault(rp, []).append(p)
        # products whose reduced image lies in W
        inW = [rp for rp in red if reduce_v(Wp, rp) == 0]
        print(f'    products with reduced image in W: {len(inW)}', flush=True)

        # greedy covering.  A grows by exactly one vector per iteration, so the
        # cached reduced product images update in O(1) each (XOR the new pivot
        # when its leading bit is set) -- no full re-reduction.
        A = dict(Fp)
        chosen = []
        img = [reduce_v(Fp, p) for p in prods]
        cur = [reduce_v(A, d) for d in D]
        while any(cur) and len(chosen) < maxp:
            from collections import Counter
            cnt = Counter(img)
            best = None
            for r in set(cur):
                if r and cnt.get(r):
                    if best is None or cnt[r] > best[0]:
                        best = (cnt[r], r)
            if best is None:
                break
            _, rp = best
            p = prods[img.index(rp)]
            chosen.append(p)
            newbit = rp.bit_length() - 1
            add_to(A, p)
            # O(1) image update for the single new pivot rp
            for i2 in range(len(img)):
                v = img[i2]
                if v and (v >> newbit) & 1:
                    img[i2] = v ^ rp
            cur = [reduce_v(A, d) for d in D]
            if len(chosen) % 10 == 0 or not any(cur):
                print(f'    {len(chosen):4d} products, {sum(1 for r in cur if r)}/35 uncovered '
                      f'[{time.time()-t0:.0f}s]', flush=True)
        print(f'  RESULT k={tk}: {len(chosen)} products, '
              f'{sum(1 for r in cur if r)}/35 uncovered, '
              f'loader cost = {nand} + {len(chosen)} = {nand + len(chosen)}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
