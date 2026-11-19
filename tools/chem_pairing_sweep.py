#!/usr/bin/env python3
"""chem_pairing_sweep.py — score every (loader-set × npz) pairing of a chem leg.

The chemistry cost is  cost = lambda_eff(npz) × T_total(loaders) × Q,
with `lambda_eff` determined by the WEIGHTS npz and `T_total` by the 15 loader
circuits.  Those two are published separately (npz by the refit author, loaders
by the loader-compiler author), so the pairing is a genuine optimisation axis:
a better npz with a cheaper loader set can beat either alone.

The official dfthcsos verifier (`work/toolchain/verifiers/dfthcsos/verify.py`)
computes the exact cost for a (loaders, npz) directory, so the sweep is
mechanical and decisive rather than a model.

Usage: chem_pairing_sweep.py <outdir> --loader-set NAME=DIR[,NAME2=DIR2] --npz NAME=FILE[...]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
PY = ROOT / 'work/toolchain/venv/bin/python'
VER = ROOT / 'work/toolchain/verifiers/dfthcsos/verify.py'
KICK = ROOT / 'work/toolchain/kickmix'

REF = 3355599588.3155375


def parse_pairs(items: list[str]) -> dict[str, str]:
    out = {}
    for it in items:
        name, _, path = it.partition('=')
        out[name] = path
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('outdir')
    ap.add_argument('--loader-set', action='append', required=True)
    ap.add_argument('--npz', action='append', required=True)
    ap.add_argument('--timeout', type=int, default=1800)
    a = ap.parse_args()
    out = pathlib.Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    loaders = parse_pairs(a.loader_set)
    npzs = parse_pairs(a.npz)

    rows = []
    for lname, ldir in loaders.items():
        ldir = pathlib.Path(ldir)
        kmbs = sorted(ldir.glob('angle_k_*.kmb'))
        if len(kmbs) != 15:
            print(f'  SKIP loader set {lname}: {len(kmbs)} angle_k_*.kmb (need 15)')
            continue
        for nname, nfile in npzs.items():
            nfile = pathlib.Path(nfile)
            if not nfile.exists():
                print(f'  SKIP npz {nname}: {nfile} missing')
                continue
            work = out / f'{lname}__{nname}'
            if work.exists():
                shutil.rmtree(work)
            work.mkdir(parents=True)
            for k in kmbs:
                shutil.copyfile(k, work / k.name)
            shutil.copyfile(nfile, work / 'submission.npz')
            env = {**os.environ, 'PYTHONPATH': f'{KICK}:{ROOT}/work/toolchain/verifiers'}
            try:
                r = subprocess.run([str(PY), str(VER), str(work), '--shots-per-address', '1'],
                                   capture_output=True, text=True, env=env,
                                   timeout=a.timeout)
                out_s = (r.stdout or '') + '\n' + (r.stderr or '')
            except subprocess.TimeoutExpired:
                print(f'  TIMEOUT {lname} x {nname}')
                continue
            i, j = out_s.find('{'), out_s.rfind('}')
            try:
                d = json.loads(out_s[i:j + 1])
            except Exception:
                print(f'  PARSE-FAIL {lname} x {nname}: {out_s[-300:]}')
                continue
            score = d.get('score')
            row = {'loaders': lname, 'npz': nname, 'status': d.get('status'),
                   'score': score, 'lambda_eff': d.get('lambda_eff'),
                   'toffoli_count': d.get('toffoli_count'), 'num_qubits': d.get('num_qubits')}
            rows.append(row)
            ratio = (REF / score) if score else None
            sc = 'None' if score is None else f'{score:.3f}'
            print(f"  {lname:22} x {nname:18} status={str(d.get('status')):5} "
                  f"cost={sc:>20} "
                  f"lambda_eff={d.get('lambda_eff')} T={d.get('toffoli_count')} "
                  f"Q={d.get('num_qubits')} ratio={round(ratio,6) if ratio else None}")

    rows.sort(key=lambda r: (r['score'] is None, r['score']))
    best = rows[0] if rows else None
    print('\n=== ranking ===')
    for r in rows:
        print(f"  {r['loaders']:22} x {r['npz']:18} {r['status']:5} {r['score']}")
    if best:
        print(f"\nBEST: {best['loaders']} x {best['npz']} = {best['score']}")
    pathlib.Path(out / 'pairing_results.json').write_text(json.dumps(rows, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
