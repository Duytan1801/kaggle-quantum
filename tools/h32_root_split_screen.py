#!/usr/bin/env python3
"""H32 screen — is the family-C root split m=6 / m=5 viable?

Background
----------
The archived q2026-v154 ISR bundle ships ONE invsqrt build: family C at the
root split m=7, cap 39 (`cfg/cfg_M.json`: m=7, cap=39, br=7, bt=6,
narrow=1, nocorr=1, `_fc2_blast`=1, sched2=[0,0,1,2,3,4,6,6]).

The bundle's own designer tool `r37_inv_40_model.py` documents the width
ladder of the root split:

    "Exact integer model of family C at any root split m (8 = today's
     41-wire circuit, 7 = 40 wires, 6 = 39 wires in FC's layout:
     v m + dividend 27 + flags 4 + held carry 1 + 1 clean)"

and its `chain()` already carries the divider-top-bit table
`a = {8: 8, 7: 10, 6: 12, 5: 14}[m]`, i.e. **m=6 and m=5 are in the model's
design space**.  The public closure ledger (`apache v173
structure/stage_status.json`) independently flags the invsqrt `square_root`
stage as "little-explored" — "other constructions of the consuming square
root are untried as far as we know".

This screen runs the UNCHANGED designer model at m = 7 (baseline, must
reproduce the shipped build's positive angle margin) and at m = 6 and m = 5.
It is a NECESSARY-condition test: if the chain does not close (the word
leaves [2^26, 2^27)) or the converged all-input angle margin is <= 0, no
circuit can exist at that m and the lane is closed for free.

Usage: h32_root_split_screen.py [--m 7 6 5] [--procs 6]
"""
from __future__ import annotations

import argparse
import json
import math
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TOOLS = (ROOT / 'work/gens/q2026_v154/isr/repo/experiments/isr/iterations'
         / '758_isr_leader_public/public_generator/invsqrt/tools')
WORK = pathlib.Path('/tmp/opencode/h32_screen')
MAX_X = 3133452
M64 = (1 << 64) - 1


def make_chain(wd: pathlib.Path) -> pathlib.Path:
    """target/tol for x = 1..MAX_X, exactly as the official verifier (copied
    from the bundle's own `invsqrt_fk_angles.py: reference`)."""
    p = wd / 'chain.npz'
    if p.exists():
        return p
    venv_py = ROOT / 'work/toolchain/venv/bin/python'
    code = (
        'import math, numpy as np\n'
        f'MAX_X={MAX_X}; M64={(1 << 64) - 1}\n'
        'tg=np.empty(MAX_X,dtype=np.uint64); tl=np.empty(MAX_X,dtype=np.uint64)\n'
        'for x in range(1,MAX_X+1):\n'
        '    r=math.isqrt((1<<130)//x)\n'
        '    tg[x-1]=((r+1)>>1)&M64\n'
        '    tl[x-1]=min(r>>25,1<<63)\n'
        f'np.savez({str(p)!r}, target=tg, tol=tl)\n'
    )
    subprocess.run([str(venv_py), '-c', code], check=True)
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--m', nargs='+', type=int, default=[7, 6, 5])
    ap.add_argument('--procs', type=int, default=6)
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    chain = make_chain(WORK)
    print(f'chain: {chain} ({chain.stat().st_size} B)', flush=True)

    specs = []
    for m in a.m:
        for off in (0, -1):
            specs.append(dict(name=f'm{m}_r37_off{off}', m=m, ho='r37', st={}, s=9,
                              off=off, bt=6, F1=5, ring=27, blast=1, slot='std'))
        # the plain series U (mathematically ideal, NOT a circuit): an upper
        # bound on what any HO stage can achieve at this m.
        specs.append(dict(name=f'm{m}_ideal', m=m, ho='ideal', off=-1, bt=6,
                          F1=5, ring=27, blast=1, slot='std'))
        # a smaller root split shifts y's range up, so the HO table needs more
        # address bits (nb): the shipped m=7 table is nb=10 (1024 entries).
        for nb in (11, 12, 13):
            specs.append(dict(name=f'm{m}_r37_nb{nb}', m=m, ho='r37',
                              st=dict(nb=nb), s=9, off=0, bt=6, F1=5,
                              ring=27, blast=1, slot='std'))
    specp = WORK / 'specs.json'
    specp.write_text(json.dumps(specs, indent=1))
    print(f'{len(specs)} specs -> {specp}', flush=True)

    outp = WORK / 'out.jsonl'
    if outp.exists():
        outp.unlink()
    env = dict(os.environ)
    env['PYTHONPATH'] = str(TOOLS)
    cmd = [str(ROOT / 'harness/run_capped.sh'), '3G',
           str(ROOT / 'work/toolchain/venv/bin/python'),
           str(TOOLS / 'r37_inv_40_model.py'), str(TOOLS), str(WORK),
           str(outp), str(a.procs), str(specp)]
    print('running:', ' '.join(cmd), flush=True)
    rc = subprocess.run(cmd, env=env).returncode
    print('rc =', rc, flush=True)
    for line in outp.read_text().splitlines():
        o = json.loads(line)
        print(json.dumps({k: o.get(k) for k in (
            'name', 'm', 'margin', 'conv', 'lp_bound', 'n_rot', 'rot_cost',
            'y_min', 'y_max', 'U_min', 'U_max', 'Y_min', 'Y_max', 'note', 'error')},
            indent=None), flush=True)
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
