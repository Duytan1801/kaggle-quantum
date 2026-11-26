#!/usr/bin/env python3
"""chem_sim.py — ground-truth symbolic simulation of an emitted loader.

Every qubit's value is tracked as a 1,232-cell boolean function of the
address, so the circuit can be simulated exactly (no shots).  The script
compares, product by product, the contribution the circuit makes to the word
registers with the contribution predicted by the plan model in chem_struct.

Usage: chem_sim.py <batch k> [npz] [tree]
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
    plans = CP.decode_plans()
    P = plans[k]

    pub = ROOT / f'work/trees/{tree}/dfthcsos' / f'angle_k_{k}.kmb'
    hdr, pops, sel, wq = CP.read_loader(str(pub))
    ops = CP.build_loader(P, sel, wq)

    nq = 1 + max(max(t[1:]) for t in ops)
    F = np.zeros((nq, CELLS), bool)
    for i, q in enumerate(sel):
        F[q] = CS.cellvec(((CP.ADDR >> i) & 1).astype(bool))
    zin = CP.word_bits(W, k - 1)
    for i, q in enumerate(wq):
        F[q] = CS.cellvec(zin[i])
    init = F.copy()

    # locate the product CCX ops: the first 82 CCX are the feature computes
    ccx_idx = [i for i, t in enumerate(ops) if t[0] == 'CCX']
    assert len(ccx_idx) == 82 + len(P['U']), (len(ccx_idx), len(P['U']))
    prod_start = ccx_idx[82:]

    f = CS.build_features(P)
    nf = len(f)
    model = np.zeros((30, CELLS), bool)
    for i in range(30):
        for j in range(nf):
            if P['R'][i][j]:
                model[i] ^= f[j]
    mprod = []
    for p in range(len(P['U'])):
        gu = np.zeros(CELLS, bool)
        for j in np.nonzero(P['U'][p])[0]:
            gu ^= f[j]
        gv = np.zeros(CELLS, bool)
        for j in np.nonzero(P['V'][p])[0]:
            gv ^= f[j]
        mprod.append(gu & gv)
    for p in range(len(P['U'])):
        for i in np.nonzero(P['M'][p])[0]:
            model[i] ^= mprod[p]

    # segment the ops: [0,prod_start[0]) = feature computes,
    # then each product occupies ops[prod_start[p] : prod_start[p+1])
    segs = []
    prev = 0
    for a in prod_start:
        segs.append((prev, a))
        prev = a
    segs.append((prev, len(ops)))

    cum = np.zeros((30, CELLS), bool)
    mcum = np.zeros((30, CELLS), bool)
    prevF = F.copy()
    # map feature index -> qubit (same order as chem_struct.build_features)
    feat_q = {0: None}
    for i, q in enumerate(sel):
        feat_q[1 + i] = q
    for j in range(5):
        feat_q[12 + j] = wq[7 * j + 6]
    anc = 46
    nswap = 68 if P['early'] == 0 else 66
    for t in range(nswap):
        feat_q[17 + t] = anc + t
    off = 17 + nswap
    if P['early'] > 0:
        feat_q[off] = anc + nswap
        feat_q[off + 1] = anc + nswap
        off += 2
    for t in range(6):
        feat_q[off + t] = anc + nswap + (2 if P['early'] > 0 else 0) + t
    off += 6
    for t in range(9 if P['early'] > 0 else 8):
        feat_q[off + t] = anc + nswap + (2 if P['early'] > 0 else 0) + 6 + t
    # walk the ops; the product CCX ops are ccx_idx[82:]
    ccx_no = 0
    prod_no = 0
    for a, t in enumerate(ops):
        if t[0] == 'CX':
            F[t[2]] ^= F[t[1]]
        elif t[0] == 'X':
            F[t[1]] ^= True
        elif t[0] == 'CCX':
            if ccx_no == 82 and prod_no == 0:
                # snapshot: compare every feature qubit's value with the model
                print('feature-qubit value check before product 0:')
                bad = []
                for j, q in feat_q.items():
                    if j == 0 or q is None:
                        continue
                    d = int((F[q] ^ f[j])[VALID].sum())
                    if d:
                        bad.append((j, q, d))
                print('  mismatching features:', bad)
                print('  n bad', len(bad))
                # parity check
                pu = np.zeros(CELLS, bool)
                for j in np.nonzero(P['U'][0])[0]:
                    pu ^= f[j]
                print('  circuit parity(U) vs model:', int((F[t[1]] ^ pu)[VALID].sum()))
                pv2 = np.zeros(CELLS, bool)
                for j in np.nonzero(P['V'][0])[0]:
                    pv2 ^= f[j]
                print('  circuit parity(V) vs model:', int((F[t[2]] ^ pv2)[VALID].sum()))
            F[t[3]] ^= F[t[1]] & F[t[2]]
            ccx_no += 1
            if ccx_no > 82:
                pv = F[t[1]] & F[t[2]]
                mp = mprod[prod_no]
                d = int((pv ^ mp)[VALID].sum())
                if prod_no < 6 or prod_no == len(P['U']) - 1:
                    print(f'  product {prod_no:3d}: circuit value |pv|={int(pv[VALID].sum()):4d} '
                          f'model |g|={int(mp[VALID].sum()):4d}  differing cells {d:5d}')
                prod_no += 1
        elif t[0] == 'HMR':
            F[t[1]] = False
        prevF = F.copy()

    print()
    final_delta = np.zeros((30, CELLS), bool)
    for i, o in enumerate(OUTS):
        final_delta[i] = F[wq[o]] ^ init[wq[o]]
    # apply the final QUADS CX correction (q5 -> q6)
    for j in range(5):
        q5, q6 = wq[7 * j + 5], wq[7 * j + 6]
        F[q6] ^= F[q5]
        init_delta_q6 = F[q6] ^ init[q6]
        i6 = OUTS.index(7 * j + 6) if (7 * j + 6) in OUTS else None
        i5 = OUTS.index(7 * j + 5)
        # bit 5's true delta is 0 (dead bit trick); bit 6 keeps its value
        final_delta[i5] = F[q5] ^ init[q5]
        if i6 is not None:
            final_delta[i6] = init_delta_q6

    wk = CP.word_bits(W, k)
    want = np.stack([CS.cellvec((wk ^ CP.word_bits(W, k - 1))[o]) for o in OUTS])
    print('circuit delta == target delta:',
          bool(np.array_equal(final_delta & VALID[None, :], want & VALID[None, :])))
    print('model    delta == target delta:',
          bool(np.array_equal(model & VALID[None, :], want & VALID[None, :])))
    dif = (model ^ want) & VALID[None, :]
    print('model-vs-target differing cells per output:',
          [int(dif[i].sum()) for i in range(30)])
    print('target per-output live weight:', [int(want[i][VALID].sum()) for i in range(30)])
    print('target bit5 outputs (OUTS idx of 7j+5) live weight:',
          [int(want[OUTS.index(7 * j + 5)][VALID].sum()) for j in range(5)])


if __name__ == '__main__':
    raise SystemExit(main())
