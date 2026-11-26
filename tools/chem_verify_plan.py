#!/usr/bin/env python3
"""chem_verify_plan.py -- check a loader's recovered plan against its target.

For every output i the plan must satisfy

    D_i  =  XOR_{p : i in M_p} g_p   XOR   R_i

with g_p = u_p AND v_p the products, M_p their masks (the word-to-word CNOT
fan) and R_i the linear rest (the ancilla-to-word CNOTs at the end).  This
script checks that identity directly, which validates the recovered plan
before anything is re-emitted.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219


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
        feats = []
        prods = []
        fan = []
        R = {q: 0 for q in wq}
        for idx, (t, a, c) in enumerate(ops):
            if t == 'CX':
                if 11 <= a[0] < 46 and 11 <= a[1] < 46:
                    fan.append((a[0], a[1]))
                elif a[0] >= 46 and 11 <= a[1] < 46:
                    R[a[1]] ^= feat_at.get(a[0], 0)
                cur[a[1]] = cur.get(a[1], 0) ^ cur.get(a[0], 0)
            elif t == 'X':
                cur[a[0]] = cur.get(a[0], 0) ^ CE.ALL
            elif t == 'CCX':
                u, v = cur.get(a[0], 0), cur.get(a[1], 0)
                if a[2] >= 46:
                    feat_at[a[2]] = u & v
                    feats.append((a[2], u & v))
                else:
                    m = {a[2]} | {dst for src, dst in fan if src == a[2]}
                    prods.append((u, v, m))
                    fan = []
                cur[a[2]] = cur.get(a[2], 0) ^ (u & v)
            elif t == 'HMR':
                feat_at[a[0]] = 0
                cur[a[0]] = 0
        # check D_i = R_i XOR (products)
        bad = 0
        for j, q in enumerate(wq):
            D = CE.fun(states[k + 1][j])
            acc = R[q]
            for u, v, m in prods:
                if q in m:
                    acc ^= u & v
            if acc != D:
                bad += 1
        print(f'=== batch k={k}: {len(feats)} features, {len(prods)} products; '
              f'outputs wrong: {bad}/35')
        # is R_i inside the span of the features?
        piv = {}
        for _, f in feats:
            v = f
            while v:
                b = v.bit_length() - 1
                row = piv.get(b)
                if row is None:
                    piv[b] = v
                    break
                v ^= row
        outside = 0
        for q in wq:
            v = R[q]
            while v:
                b = v.bit_length() - 1
                row = piv.get(b)
                if row is None:
                    outside += 1
                    break
                v ^= row
        print(f'    R_i outside the feature span: {outside}/35')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
