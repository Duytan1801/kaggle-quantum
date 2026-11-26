#!/usr/bin/env python3
"""chem_rec.py — compare the emitter's RECORD against the chem_struct model.

The emitter (chem_plan.build_loader) is the validated reference: it rebuilds
goodpjw's ten public loaders byte for byte.  It tracks, for every feature
qubit, the boolean function it *believes* that qubit carries (RECORD['fn']).
chem_struct.build_features is an independent reconstruction of the same
feature list from the plan's structural fields.

This script builds both for a batch and reports every disagreement, so the
remaining model error (if any) is pinned to an exact feature.

Usage: chem_rec.py <batch k> [npz] [tree]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_struct as CS                                      # noqa: E402

CELLS, VALID, OUTS = CS.CELLS, CS.VALID, CS.OUTS


def main():
    k = int(sys.argv[1])
    npz = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / 'work/trees/v149/dfthcsos/submission.npz'
    tree = sys.argv[3] if len(sys.argv) > 3 else 'v149'
    z = np.load(npz)
    W = z['angle_words']
    P = CP.decode_plans()[k]
    pub = ROOT / f'work/trees/{tree}/dfthcsos' / f'angle_k_{k}.kmb'
    hdr, pops, sel, wq = CP.read_loader(str(pub))
    ops = CP.build_loader(P, sel, wq)

    names = CP.RECORD['names']
    fn = CP.RECORD['fn']
    model = CS.build_features(P)
    print(f'k={k} tree={tree}  emitter names: {len(names)}   model features: {len(model)}')

    # The emitter may reuse one ancilla for two features (the "swap" layout):
    # names[83] and names[84] then name the SAME qubit, which holds the
    # ands[66] feature during the first `early` products and the ands[67]
    # feature afterwards.  RECORD keeps the LAST value, so the comparison for
    # the reused qubit must use the later feature.
    reused = {}
    if len(names) > 84 and names[83] == names[84]:
        reused[names[83]] = 84

    bad = 0
    for j, q in enumerate(names):
        if j == 0:
            continue
        if q not in fn:
            print(f'  feat {j:3d} qubit {q}: NOT in RECORD')
            bad += 1
            continue
        emp = np.array([(fn[q] >> a) & 1 for a in range(CP.NV)], bool)
        empc = CS.cellvec(emp)
        jj = reused.get(q, j)
        mine = model[jj]
        d = int((empc ^ mine)[VALID].sum())
        if d:
            print(f'  feat {j:3d} qubit {q}: MISMATCH {d} cells '
                  f'(emp |.|={int(empc[VALID].sum())}, model[{jj}] |.|={int(mine[VALID].sum())})')
            bad += 1
    print(f'feature disagreements: {bad}')

    # what IS the emitter's mixed feature?  decompose it.
    print()
    print('mixed-feature decomposition (emitter truth):')
    for j in range(len(names)):
        q = names[j]
        if q not in fn:
            continue
        emp = np.array([(fn[q] >> a) & 1 for a in range(CP.NV)], bool)
        rows = CS.cellvec(emp).reshape(CS.NBANK, CS.NLOW)
        lows = np.nonzero(rows.any(axis=0))[0]
        banks = np.nonzero(rows.any(axis=1))[0]
        if len(lows) == 1 and len(banks) and (rows[:, lows[0]] == rows[:, 0]).all():
            continue        # bank-only feature
        if len(lows) == 0:
            continue
        print(f'  feat {j:3d} qubit {q}: active lows={list(lows)} #banks={len(banks)} '
              f'rows-uniform={bool((rows == rows[:, :1]).all())}')


if __name__ == '__main__':
    raise SystemExit(main())
