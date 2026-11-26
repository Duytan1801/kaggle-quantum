#!/usr/bin/env python3
"""chem_dbg2.py -- step-by-step diff of two trackers."""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                    # noqa: E402
import chem_extract as CE                                 # noqa: E402

NV = 1219
tree = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ROOT / 'work/trees/v149/dfthcsos')
k = int(sys.argv[2]) if len(sys.argv) > 2 else 2
states = CE.chain_states(tree / 'submission.npz')
hdr, ops, sel, wq = CP.read_loader(str(tree / f'angle_k_{k}.kmb'))
zin = states[k]
S = np.zeros((1 + max(max(t[1:]) for t in ops), NV), bool)
S[wq] = zin
for i, q in enumerate(sel):
    S[q] = (CE.ADDR >> i) & 1

f = {}
for i, q in enumerate(sel):
    f[q] = CE.fun((CE.ADDR >> i) & 1)
for j, q in enumerate(wq):
    f[q] = CE.fun(zin[j])


def toarr(v):
    return np.unpackbits(np.frombuffer(v.to_bytes((NV + 7) // 8, 'little'),
                                       dtype=np.uint8), bitorder='little')[:NV].astype(bool)


for i, t in enumerate(ops):
    if t[0] == 'CX':
        S[t[2]] ^= S[t[1]]
        f[t[2]] = f.get(t[2], 0) ^ f.get(t[1], 0)
    elif t[0] == 'X':
        S[t[1]] ^= True
        f[t[1]] = f.get(t[1], 0) ^ CE.ALL
    elif t[0] == 'CCX':
        S[t[3]] ^= S[t[1]] & S[t[2]]
        f[t[3]] = f.get(t[3], 0) ^ (f.get(t[1], 0) & f.get(t[2], 0))
    elif t[0] == 'HMR':
        S[t[1]] = False
        f[t[1]] = 0
    # compare
    for q in range(S.shape[0]):
        a = toarr(f.get(q, 0))
        if not (a == S[q]).all():
            print(f'DIVERGE at op {i} {t} qubit {q}: '
                  f'{int((a != S[q]).sum())} addresses')
            sys.exit()
print('NO DIVERGE (value tracking identical)')
