#!/usr/bin/env python3
"""Measure every distinct public chemistry table against the shared 3,357-T loaders.

Each candidate release that shares v145's 15 loader members differs only in
`dfthcsos/submission.npz` (and sometimes the DQI member).  This script builds
one directory per distinct table (symlinked loaders + the candidate table) and
runs the UNCHANGED local official chemistry verifier on each, so the queue
verdicts are measured rather than assumed.
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
V145 = ROOT / 'work/trees/v145_ozertuu_33170350'
WORK = pathlib.Path('/tmp/opencode/chem_variants')
PY = ROOT / 'work/toolchain/venv/bin/python'
VER = ROOT / 'work/toolchain/verifiers/dfthcsos/verify.py'


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    tables = {}
    for npz in sorted(pathlib.Path('/tmp/opencode/adjudicate').rglob('submission.npz')):
        if npz.parent.name != 'dfthcsos':
            continue
        tables.setdefault(sha(npz), npz)
    print(f'distinct chemistry tables: {len(tables)}')
    WORK.mkdir(parents=True, exist_ok=True)
    loaders = sorted((V145 / 'dfthcsos').glob('angle_k_*.kmb'))
    for h, npz in tables.items():
        d = WORK / h[:12]
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        shutil.copyfile(npz, d / 'submission.npz')
        for l in loaders:
            shutil.copyfile(l, d / l.name)
        log = WORK / f'{h[:12]}.log'
        env = dict(os.environ)
        env['PYTHONPATH'] = str(ROOT / 'work/toolchain/kickmix')
        with log.open('w') as fh:
            subprocess.run([str(ROOT / 'harness/run_capped.sh'), '3G', str(PY), str(VER),
                            str(d), '--shots-per-address', '1'],
                           stdout=fh, stderr=subprocess.STDOUT, timeout=7200, env=env)
        text = log.read_text()
        i, j = text.find('{'), text.rfind('}')
        obj = {}
        if 0 <= i < j:
            import json
            try:
                obj = json.loads(text[i:j + 1])
            except Exception:
                obj = {}
        print(f'{h[:12]} status={obj.get("status")} score={obj.get("score")} '
              f'T={obj.get("toffoli_count")} Q={obj.get("num_qubits")} '
              f'lambda={obj.get("lambda_eff")} log={log}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
