#!/usr/bin/env python3
"""chem_featuse.py -- are all 82 cached features USED by the public plans?

THE LEVER
    A loader costs  82 + nP  Toffolis:  68 cached bank ANDs + 6 low ANDs +
    8 mixed features, then one Toffoli per product.  Every cached feature
    that NO product and NO linear rest uses is a WASTED Toffoli -- it can be
    dropped from the plan, and its ancilla freed.

    The public plans cost 205..215 Toffolis, of which 82 (38 %) are cached
    features.  If even 10 of them are unused, that is 10 Toffolis per
    loader, 30 loader-runs (15 batches x 2 passes) = 300 Toffolis of the
    13,166 -> a 2.3 % chemistry cost cut.

    This tool reports, for every public batch: which feature indices are
    referenced by the products (U/V) and by the linear rests (R), how many
    are unused, and the exact Toffoli saving.

Usage: chem_featuse.py [batch ...]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402

# the feature layout (must match chem_plan.build_loader)
#   0            : the constant
#   1..11        : the 11 address bits
#   12..16       : the 5 QUADS features (from the incoming words)
#   17..17+nb-1  : the cached bank ANDs
#   (swap) +2    : the two early-AND features
#   then         : the 6 low ANDs
#   then         : the 8 (or 9) mixed features


def feature_layout(P):
    """-> (kind, index) list, and the index ranges"""
    swap = P['early'] > 0
    nb = 66 if swap else 68
    nmix = 9 if swap else 8
    nf = 100 if swap else 99
    kinds = []
    kinds.append(('const', 0))
    for i in range(11):
        kinds.append(('addr', 1 + i))
    for i in range(5):
        kinds.append(('quads', 12 + i))
    for i in range(nb):
        kinds.append(('bankAND', 17 + i))
    if swap:
        kinds.append(('bankAND', 17 + nb))
        kinds.append(('bankAND', 17 + nb + 1))
    for i in range(6):
        kinds.append(('lowAND', 17 + nb + (2 if swap else 0) + i))
    for i in range(nmix):
        kinds.append(('mixed', 17 + nb + (2 if swap else 0) + 6 + i))
    assert len(kinds) == nf, (len(kinds), nf)
    return kinds


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    ks = [int(a) for a in args] if args else sorted(CP.decode_plans())
    plans = CP.decode_plans()

    total_save = 0
    total_nP = 0
    for k in ks:
        P = plans[k]
        kinds = feature_layout(P)
        nf = len(kinds)
        used = np.zeros(nf, int)
        # products: U and V are (nP, nf) masks
        for M in (P['U'], P['V']):
            for j in np.nonzero(M.any(axis=0))[0]:
                used[j] += int(M[:, j].sum())
        # the linear rests
        for j in np.nonzero(P['R'].any(axis=0))[0]:
            used[j] += int(P['R'][:, j].sum())
        unused = [j for j in range(nf) if used[j] == 0]
        by_kind = {}
        for kind, j in kinds:
            by_kind.setdefault(kind, [0, 0])
            by_kind[kind][0] += 1
            if used[j] == 0:
                by_kind[kind][1] += 1
        nP = P['U'].shape[0]
        swap = P['early'] > 0
        nb = 66 if swap else 68
        nmix = 9 if swap else 8
        cost = nb + 6 + nmix + (2 if swap else 0) + nP
        save = len(unused)
        total_save += save
        total_nP += nP
        print(f'batch {k:2d}: nP={nP:3d} cost={cost:3d}  features={nf} '
              f'unused={save:2d}  ' +
              ' '.join(f'{kk}:{v[1]}/{v[0]}' for kk, v in by_kind.items()))
        if unused:
            print(f'          unused feature indices: {unused}')
    print()
    print(f'total unused features over {len(ks)} batches: {total_save}')
    print(f'per-pass Toffoli saving if all were dropped: {total_save} '
          f'(of {total_nP + 82 * len(ks)})')
    print(f'T saving over both passes: {2 * total_save} of 13,166')


if __name__ == '__main__':
    raise SystemExit(main())
