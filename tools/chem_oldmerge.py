#!/usr/bin/env python3
"""chem_oldmerge.py -- can the OLD loaders' plan be compressed?

The five loaders goodpjw2008 did not re-solve cost 240-245 Toffolis:
147 feature computations + 98 products (k=0).  This tool asks the two
questions that decide whether a cheap compression exists:

  1. do two products share a FACTOR?  If u_p = u_q then
         g_p XOR g_q = u AND (v_p XOR v_q)
     so the two products can be MERGED into one (same mask), which saves one
     Toffoli; the same holds when v_p = v_q.
  2. what are the output masks?  A product that feeds several outputs is
     already "wired" (goodpjw's term); a product that feeds one output is
     "unwired".

Usage: chem_oldmerge.py <tree-dir> [batch ...]
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter, defaultdict

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219


def analyse(tree, k, states):
    ops, sel, wq = CE.parse_kmx(pathlib.Path(tree) / f'angle_k_{k}.kmb')
    zin = states[k]
    cur = {}
    for i, q in enumerate(sel):
        cur[q] = CE.fun((CE.ADDR >> i) & 1)
    for j, q in enumerate(wq):
        cur[q] = CE.fun(zin[j])
    products = []
    fan_pending = set()
    w2w_before = w2w_after = 0
    seen_product = False
    for idx, (t, a, c) in enumerate(ops):
        if t == 'CX':
            if 11 <= a[0] < 46 and 11 <= a[1] < 46:
                if seen_product:
                    w2w_after += 1
                else:
                    w2w_before += 1
                fan_pending.add(a[1])
            cur[a[1]] = cur.get(a[1], 0) ^ cur.get(a[0], 0)
        elif t == 'X':
            cur[a[0]] = cur.get(a[0], 0) ^ CE.ALL
        elif t == 'CCX':
            u, v = cur.get(a[0], 0), cur.get(a[1], 0)
            if a[2] < 46:
                seen_product = True
                products.append(dict(idx=idx, tgt=a[2], u=u, v=v,
                                     mask=tuple(sorted(fan_pending | {a[2]}))))
                fan_pending = set()
            cur[a[2]] = cur.get(a[2], 0) ^ (u & v)
        elif t == 'HMR':
            cur[a[0]] = 0
    return products, w2w_before, w2w_after


def main() -> int:
    tree = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'work/trees/v149/dfthcsos')
    ks = [int(a) for a in sys.argv[2:] if not a.startswith('--')] or [0]
    states = CE.chain_states(pathlib.Path(tree) / 'submission.npz')
    for k in ks:
        prods, wb, wa = analyse(tree, k, states)
        us = Counter(p['u'] for p in prods)
        vs = Counter(p['v'] for p in prods)
        sizes = Counter(len(p['mask']) for p in prods)
        outs = set()
        for p in prods:
            outs.update(p['mask'])
        print(f'=== batch k={k}: {len(prods)} products')
        print(f'    distinct first factors u: {len(us)} (dupes: '
              f'{sum(c-1 for c in us.values() if c > 1)})')
        print(f'    distinct second factors v: {len(vs)} (dupes: '
              f'{sum(c-1 for c in vs.values() if c > 1)})')
        print(f'    mask sizes: {dict(sorted(sizes.items()))}')
        print(f'    outputs covered: {len(outs)} of 30;  word-word CX before/after '
              f'the first product: {wb}/{wa}')
        # merge potential: products with the same u
        byu = defaultdict(list)
        for p in prods:
            byu[p['u']].append(p)
        merges = [(u, ps) for u, ps in byu.items() if len(ps) > 1]
        if merges:
            u, ps = merges[0]
            print(f'    example merge group (same u, {len(ps)} products): '
                  f'targets {[p["tgt"] for p in ps]} masks '
                  f'{[len(p["mask"]) for p in ps]}')
        else:
            print('    no two products share a first factor')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
