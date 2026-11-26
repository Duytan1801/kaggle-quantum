#!/usr/bin/env python3
"""chem_dbg.py -- cross-check the function tracker against the validated reader."""
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
ref = CP.run_loader(ops, sel, wq, zin)       # (35, NV) bool
ops2, sel2, wq2, f, features, products, cb = CE.extract(tree, k, states)
mine = np.zeros((35, NV), bool)
for j, q in enumerate(wq2):
    mine[j] = np.unpackbits(np.frombuffer(f[q].to_bytes((NV + 7) // 8, 'little'),
                                          dtype=np.uint8), bitorder='little')[:NV].astype(bool)
want = states[k + 1]
print('ref == want :', bool((ref == want).all()))
print('mine == want:', bool((mine == want).all()))
print('mine == ref :', bool((mine == ref).all()))
bad = np.nonzero((mine != ref).any(axis=0))[0]
print('mismatching addresses:', len(bad), bad[:10])
for j in range(35):
    if (mine[j] != ref[j]).any():
        print(f'  output {j}: {(mine[j] != ref[j]).sum()} addresses differ')
        break
print('ref vs want per output:',
      [(j, int((ref[j] != want[j]).sum())) for j in range(35) if (ref[j] != want[j]).any()][:8])
