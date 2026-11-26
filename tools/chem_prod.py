#!/usr/bin/env python3
"""chem_prod.py -- what do the solved plans' products actually look like?

For a public plan this reports, per product:
  * how the U and V feature sets split into bank-side and low-side features,
  * the rank of the product matrix A = (XOR U) AND (XOR V) over GF(2),
  * the number of outputs the product feeds.

The point is to see the shape of the search space before designing a search
for the five batches goodpjw did not solve.

Usage: chem_prod.py <batch k> [npz]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_struct as CS                                      # noqa: E402

ADDR = CP.ADDR
BANK = ADDR >> 4
LOW = ADDR & 15


def gf2_rank(M):
    A = M.copy() % 2
    m, n = A.shape
    r = 0
    for c in range(n):
        piv = None
        for i in range(r, m):
            if A[i, c]:
                piv = i
                break
        if piv is None:
            continue
        A[[r, piv]] = A[[piv, r]]
        for i in range(m):
            if i != r and A[i, c]:
                A[i] ^= A[r]
        r += 1
        if r == m:
            break
    return r


def main():
    k = int(sys.argv[1])
    npz = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    P = CP.decode_plans()[k]
    f = CS.build_features(P)
    nf = len(f)
    swap = P['early'] > 0
    early = P['early']

    # feature classes (model indices)
    #   0        const
    #   1..11    address bits (1..4 are low bits, 5..11 are bank bits)
    #   12..16   QUADS (low functions)
    #   17..     cached bank ANDs (bank functions)
    #   then     6 low ANDs (low functions), then mixed (bank functions at low 7/14)
    nb = 66 if swap else 68
    bank_idx = set(range(5, 12)) | set(range(17, 17 + nb))
    low_idx = set(range(1, 5)) | set(range(12, 17))
    mixed_idx = set()
    if swap:
        bank_idx |= {17 + nb, 18 + nb}
        low_idx |= set(range(17 + nb + 2, 17 + nb + 8))
        mixed_idx |= set(range(17 + nb + 8, nf))
    else:
        low_idx |= set(range(17 + nb, 17 + nb + 6))
        mixed_idx |= set(range(17 + nb + 6, nf))
    print(f'k={k} nf={nf} swap={swap} early={early}')
    print(f'  bank-side feature indices: {len(bank_idx)}   low-side: {len(low_idx)}   mixed: {len(mixed_idx)}')

    nP = len(P['U'])
    rows = []
    for p in range(nP):
        first = (p < early) if swap else True

        def split(mask):
            u_bank = u_low = 0
            for j in np.nonzero(mask)[0]:
                if j == 0:
                    continue
                if swap and j in (83, 84):
                    if (j == 83) != first:
                        continue
                    u_bank ^= f[83 if first else 84]
                    continue
                if j in mixed_idx:
                    u_bank ^= f[j]
                elif j in bank_idx:
                    u_bank ^= f[j]
                else:
                    u_low ^= f[j]
            return u_bank, u_low

        ub, ul = split(P['U'][p])
        vb, vl = split(P['V'][p])
        au = ub ^ ul
        av = vb ^ vl
        A = au & av
        M = A.reshape(CS.NBANK, CS.NLOW)
        rows.append({
            'p': p,
            'uBank': int(ub[CS.VALID].sum()),
            'uLow': int(ul[CS.VALID].sum()),
            'vBank': int(vb[CS.VALID].sum()),
            'vLow': int(vl[CS.VALID].sum()),
            'rank': gf2_rank(M.astype(np.uint8)),
            'mask': int(P['M'][p].sum()),
            'nonzeroCols': int((M.any(axis=0)).sum()),
        })

    print()
    print(f'{"p":>4s} {"|u_bank|":>8s} {"|u_low|":>7s} {"|v_bank|":>8s} {"|v_low|":>7s} '
          f'{"rank":>4s} {"mask":>4s} {"cols":>4s}')
    for r in rows[:20]:
        print(f'{r["p"]:4d} {r["uBank"]:8d} {r["uLow"]:7d} {r["vBank"]:8d} {r["vLow"]:7d} '
              f'{r["rank"]:4d} {r["mask"]:4d} {r["nonzeroCols"]:4d}')
    print('...')
    arr = np.array([[r['rank'], r['mask'], r['nonzeroCols'], r['uLow'] > 0, r['vLow'] > 0]
                    for r in rows])
    print(f'rank histogram   : {dict(zip(*np.unique(arr[:, 0], return_counts=True)))}')
    print(f'mask sizes       : min {arr[:, 1].min()} max {arr[:, 1].max()} mean {arr[:, 1].mean():.2f}')
    print(f'nonzero cols     : min {arr[:, 2].min()} max {arr[:, 2].max()} mean {arr[:, 2].mean():.2f}')
    print(f'products with a low part in U: {int(arr[:, 3].sum())}/{nP};  in V: {int(arr[:, 4].sum())}/{nP}')
    print(f'total rank sum   : {int(arr[:, 0].sum())}')


if __name__ == '__main__':
    raise SystemExit(main())
