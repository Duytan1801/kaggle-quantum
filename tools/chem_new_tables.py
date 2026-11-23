#!/usr/bin/env python3
"""Measure newly-harvested public chemistry tables against the shared 3,357-T loaders.

Usage: chem_new_tables.py <name>:<dir-with-submission.npz> [...]

Each candidate ships `dfthcsos/submission.npz` (the chemistry table) plus the
15 shared loader members `dfthcsos/angle_k_*.kmb`.  We rebuild one directory per
candidate (the candidate's table + the shared loaders) and run the UNCHANGED
local official chemistry verifier, so the verdict is measured, not claimed.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
V147 = ROOT / 'work/trees/v147'
WORK = pathlib.Path('/tmp/opencode/chem_new')
PY = ROOT / 'work/toolchain/venv/bin/python'
VER = ROOT / 'work/toolchain/verifiers/dfthcsos/verify.py'


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    WORK.mkdir(parents=True, exist_ok=True)
    loaders = sorted((V147 / 'dfthcsos').glob('angle_k_*.kmb'))
    assert len(loaders) == 15, len(loaders)
    for spec in sys.argv[1:]:
        name, src = spec.split(':', 1)
        npz = pathlib.Path(src) / 'dfthcsos' / 'submission.npz'
        if not npz.exists():
            npz = pathlib.Path(src) / 'submission.npz'
        h = sha(npz)
        d = WORK / f'{name}_{h[:12]}'
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        shutil.copyfile(npz, d / 'submission.npz')
        for l in loaders:
            shutil.copyfile(l, d / l.name)
        log = WORK / f'{name}_{h[:12]}.log'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(ROOT / 'work/toolchain/kickmix')
        subprocess.run([str(ROOT / 'harness/run_capped.sh'), '3G', str(PY), str(VER),
                        str(d), '--shots-per-address', '1'],
                       stdout=log.open('w'), stderr=subprocess.STDOUT, timeout=7200,
                       env=env)
        text = log.read_text()
        i, j = text.find('{'), text.rfind('}')
        obj = {}
        if 0 <= i < j:
            try:
                obj = json.loads(text[i:j + 1])
            except Exception:
                obj = {}
        print(f'{name} table={h[:16]} status={obj.get("status")} score={obj.get("score")} '
              f'T={obj.get("toffoli_count")} Q={obj.get("num_qubits")} '
              f'lambda={obj.get("lambda_eff")} log={log}', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
