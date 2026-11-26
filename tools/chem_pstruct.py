#!/usr/bin/env python3
"""chem_pstruct.py -- the GENERATIVE STRUCTURE of a public chemistry plan.

WHY THIS IS THE KEY TO H48
    H48 wants a plan with far fewer products than goodpjw's 123..132.  The
    bound says nP >= 39.  To beat 123 we must understand *how* goodpjw's
    products are built, because only then can we look for a different
    construction.

    Each product g_p = u_p AND v_p has a bank direction pair and a low
    profile.  This script decomposes every product of a public plan into

        * its two factors' feature mix (bank-only / low-only / mixed),
        * its COLUMN DIFFERENCE structure:  d_j(g) = g[:,j] XOR g[:,0]
          for each low column j, as a 77-bit bank vector,
        * its mask (which outputs it feeds),

    and reports the patterns that emerge.  In particular it tests the
    "one correction per column" hypothesis: a product whose difference
    structure is nonzero in exactly ONE column acts as a *correction* for
    that column (goodpjw's prose: "three corrections per column instead of
    four ... a GPU search over partitions of the banks").

Usage:
    chem_pstruct.py <batch>          analyse one public batch
    chem_pstruct.py <batch> --dump   also print every product
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_prune as CPR                                     # noqa: E402

NBANK, NLOW = 77, 16


def classify(P, nf):
    """-> (bank_idx, low_idx, mixed_idx) feature index sets"""
    swap = P['early'] > 0
    nb = 66 if swap else 68
    bank_idx = list(range(5, 12)) + list(range(17, 17 + nb))
    if swap:
        bank_idx += [17 + nb, 17 + nb + 1]
    mixed_start = nf - (9 if swap else 8)
    mixed_idx = list(range(mixed_start, nf))
    low_idx = [0] + list(range(1, 5)) + list(range(12, 17))
    low_and_start = (17 + nb + 2) if swap else (17 + nb)
    low_idx += list(range(low_and_start, low_and_start + 6))
    return bank_idx, low_idx, mixed_idx


def split_feature_sets(P, U, V, nf):
    """-> for each product: the feature-index sets of u and v"""
    bank_idx, low_idx, mixed_idx = classify(P, nf)
    b, l, m = set(bank_idx), set(low_idx), set(mixed_idx)
    out = []
    for u, v in zip(U, V):
        us = set(np.nonzero(u)[0].tolist())
        vs = set(np.nonzero(v)[0].tolist())
        out.append((us, vs))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    k = int(args[0]) if args else 14
    dump = '--dump' in sys.argv

    plans = CP.decode_plans()
    P = plans[k]
    f = CPR.plan_features(P)
    nf = len(f)
    G = CPR.product_functions(P, f)

    # ---- the target deltas -------------------------------------------
    z = np.load(ROOT / 'work/trees/v149/dfthcsos/submission.npz')
    W = z['angle_words']
    wk = CP.word_bits(W, k)
    wp = CP.word_bits(W, k - 1)
    d = (wk ^ wp)[CP.OUTS]
    D = [CPR.fun(d[i]) for i in range(30)]

    # ---- per-column bank vectors of a function ------------------------
    def colvec(func):
        """-> list of 16 bank vectors (77-bit ints)"""
        out = []
        for j in range(NLOW):
            v = 0
            for b in range(NBANK):
                if (func >> (b * NLOW + j)) & 1:
                    v |= 1 << b
            out.append(v)
        return out

    # ---- per-product difference structure -----------------------------
    rows = []
    for p, g in enumerate(G):
        cols = colvec(g)
        diffs = [cols[j] ^ cols[0] for j in range(1, NLOW)]
        act = [j for j in range(1, NLOW) if diffs[j - 1]]
        # is the difference structure "rank one" (a low profile x a bank vector)?
        # -> all active columns share the same bank vector up to a scalar
        bank_dirs = []
        for j in act:
            bank_dirs.append(diffs[j - 1])
        mask = set(np.nonzero(P['M'][p])[0].tolist())
        rows.append(dict(p=p, cols=cols, diffs=diffs, act=act, dirs=bank_dirs,
                         mask=mask, g=g))

    # ---- report -------------------------------------------------------
    print(f'=== batch {k}: nf={nf} nP={len(G)} swap={P["early"] > 0}')
    print(f'  target: per-column bank-vector ranks')
    for i in (0, 1, 2, 7, 15):
        tc = colvec(D[i])
        td = [tc[j] ^ tc[0] for j in range(1, NLOW)]
        r = CPR.Basis((j, td[j - 1]) for j in range(15)).rank()
        print(f'    output {i:2d}: rank of the 15 difference rows = {r:2d}   '
              f'col0 bits = {bin(tc[0]).count("1"):2d}')

    # how many products are "single-column corrections"?
    nact = Counter(len(r['act']) for r in rows)
    print(f'  products by number of active difference columns: '
          f'{dict(sorted(nact.items()))}')
    print(f'  products with ZERO active difference columns: '
          f'{nact.get(0, 0)}')

    # per column, how many products are active there?
    percol = Counter()
    for r in rows:
        for j in r['act']:
            percol[j] += 1
    print('  active products per column (1..15): '
          f'{[percol[j] for j in range(1, NLOW)]}')

    # ---- the "corrections per column" hypothesis ----------------------
    # a single-column product with direction v serves outputs whose target
    # difference at that column is v (or v + bank-only terms)
    print()
    print('  single-column products (corrections):')
    corr = [r for r in rows if len(r['act']) == 1]
    print(f'    count = {len(corr)}')
    cbycol = Counter(r['act'][0] for r in corr)
    print(f'    by column: {dict(sorted(cbycol.items()))}')
    for r in corr[:6]:
        print(f'      p{r["p"]:3d} col {r["act"][0]:2d}  dir bits '
              f'{bin(r["dirs"][0]).count("1"):2d}  mask size {len(r["mask"]):2d}')

    # ---- how are the outputs covered? ---------------------------------
    # the coefficient vector c_i is unique (the product classes are
    # independent), so solve it with the quotient basis
    FB = CPR.Basis((j, f[j]) for j in range(nf))
    resG = [FB.reduce(g)[0] for g in G]
    SB = CPR.Basis((p, resG[p]) for p in range(len(G)))
    cvec = []
    for i in range(30):
        sol = SB.solve(FB.reduce(D[i])[0])
        cvec.append(set(sol.keys()) if sol else None)
    print()
    print('  per-output product usage:')
    sizes = [len(c) for c in cvec if c is not None]
    if sizes:
        print(f'    min {min(sizes)} max {max(sizes)} mean {np.mean(sizes):.2f}')
    # the mask of a product = the outputs whose c_i contains it
    ok = all((p in cvec[i]) == (i in rows[p]['mask']) for p in range(len(G))
             for i in range(30))
    print(f'    solved masks agree with the stored masks: {ok}')

    # ---- per-output column structure ----------------------------------
    print()
    print('  for output 0: which columns does each used product touch?')
    used = sorted(cvec[0])
    for p in used[:14]:
        print(f'    p{p:3d} cols {rows[p]["act"]} dirs '
              f'{[bin(x).count("1") for x in rows[p]["dirs"]]}')

    # ---- the bank directions ------------------------------------------
    all_dirs = []
    for r in rows:
        all_dirs.extend(r['dirs'])
    B = CPR.Basis((i, all_dirs[i]) for i in range(len(all_dirs)))
    print()
    print(f'  distinct difference directions: {len(all_dirs)} '
          f'(rank {B.rank()} of {NBANK})')

    if dump:
        print()
        for r in rows:
            print(f'  p{r["p"]:3d} act={r["act"]} '
                  f'dirs={[bin(x).count("1") for x in r["dirs"]]} '
                  f'mask={sorted(r["mask"])}')


if __name__ == '__main__':
    raise SystemExit(main())
