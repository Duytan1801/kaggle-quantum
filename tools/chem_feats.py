#!/usr/bin/env python3
"""chem_feats.py — extract the loader's feature functions from the circuit.

Ground truth: symbolically simulate the emitted loader and read every
feature ancilla's value at the moment all 82 feature computes are done and
before the first product's parity chain starts.  This gives the exact
function of every feature, independent of any theory about how the plan
built it.

Usage: chem_feats.py <batch k> [npz] [tree]
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


def feature_qubits(P, sel, wq):
    """feature index -> qubit (the emitter's `names` list)"""
    swap = P['early'] > 0
    nb, nmix = (66, 9) if swap else (68, 8)
    fq = {0: None}
    for i, q in enumerate(sel):
        fq[1 + i] = q
    for j in range(5):
        fq[12 + j] = wq[7 * j + 6]
    anc = 46
    n = 0
    for t in range(nb):
        fq[17 + t] = anc + n
        n += 1
    if swap:
        fq[17 + nb] = anc + n
        fq[18 + nb] = anc + n
        n += 1
    for t in range(6):
        fq[17 + nb + (2 if swap else 0) + t] = anc + n
        n += 1
    for t in range(nmix):
        fq[17 + nb + (2 if swap else 0) + 6 + t] = anc + n
        n += 1
    return fq, anc, n


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
    nq = 1 + max(max(t[1:]) for t in ops)
    F = np.zeros((nq, CELLS), bool)
    for i, q in enumerate(sel):
        F[q] = CS.cellvec(((CP.ADDR >> i) & 1).astype(bool))

    fq, anc, nanc = feature_qubits(P, sel, wq)
    ccx = 0
    feats = {}
    for a, t in enumerate(ops):
        if t[0] == 'CX':
            F[t[2]] ^= F[t[1]]
        elif t[0] == 'X':
            F[t[1]] ^= True
        elif t[0] == 'CCX':
            F[t[3]] ^= F[t[1]] & F[t[2]]
            ccx += 1
            if ccx == 82:
                for j, q in fq.items():
                    if j and q is not None:
                        feats[j] = F[q].copy()
                break
        elif t[0] == 'HMR':
            F[t[1]] = False

    model = CS.build_features(P)
    print(f'k={k} tree={tree}  ancillas used {nanc}')
    print(f'{"feat":>5s} {"qubit":>6s} {"empirical |.|":>14s} {"model |.|":>11s} {"diff":>6s}')
    for j in sorted(feats):
        d = int((feats[j] ^ model[j])[VALID].sum())
        flag = '' if d == 0 else '   <-- MISMATCH'
        print(f'{j:5d} {fq[j]:6d} {int(feats[j][VALID].sum()):14d} '
              f'{int(model[j][VALID].sum()):11d} {d:6d}{flag}')

    # what IS the empirical mixed feature?
    nmix = 9 if P['early'] > 0 else 8
    base = 17 + (66 if P['early'] > 0 else 68) + (2 if P['early'] > 0 else 0) + 6
    print()
    print('mixed features: empirical decomposition')
    for g in range(nmix):
        j = base + g
        e = feats[j]
        rows = e.reshape(CS.NBANK, CS.NLOW)
        lows = np.nonzero(rows.any(axis=0))[0]
        banks = np.nonzero(rows.any(axis=1))[0]
        full = bool(rows[:, lows[0]].all()) if len(lows) else False
        print(f'  g={g}: active lows={list(lows)}  #banks={len(banks)}  '
              f'all lows full? {full}  first banks={list(banks[:8])}')
        # compare with P['B'][g]
        bm = P['B'][g]
        banksB = np.nonzero([bool(bm[CS.BANK[b]]) for b in range(CS.NBANK)])[0]
        print(f'       P[B][g] banks={list(banksB[:8])} #={len(banksB)}  '
              f'same set? {set(banks.tolist())==set(banksB.tolist())}')


if __name__ == '__main__':
    raise SystemExit(main())
