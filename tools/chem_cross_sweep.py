#!/usr/bin/env python3
"""Cross-measure chemistry (table x loader-set) combinations.

The q2026-v154 release ships a chemistry table AND its own loader set; the
public floor `e7f08627208c` ships a table and the 3,357-Toffoli loaders.  A
table and a loader set are only weakly coupled (the table holds the fitted
weights, the loaders hold the circuit), so the 3x3 cross matrix may contain a
combination that beats the public floor.  Every cell is measured with the
UNCHANGED official chemistry verifier.

Usage: chem_cross_sweep.py [--jobs 1]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
W = pathlib.Path('/tmp/opencode/chem_cross')
PY = ROOT / 'work/toolchain/venv/bin/python'
VER = ROOT / 'work/toolchain/verifiers/dfthcsos/verify.py'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--jobs', type=int, default=1)
    a = ap.parse_args()
    env = dict(os.environ)
    env['PYTHONPATH'] = str(ROOT / 'work/toolchain/kickmix')
    results = {}
    for d in sorted(W.iterdir()):
        log = d / 'verify.log'
        with log.open('w') as fh:
            subprocess.run([str(ROOT / 'harness/run_capped.sh'), '3G', str(PY), str(VER),
                            str(d), '--shots-per-address', '1'],
                           stdout=fh, stderr=subprocess.STDOUT, timeout=7200, env=env)
        text = log.read_text(errors='replace')
        i, j = text.find('{'), text.rfind('}')
        obj = {}
        if 0 <= i < j:
            try:
                obj = json.loads(text[i:j + 1])
            except Exception:
                obj = {}
        results[d.name] = obj
        print(f'{d.name:34} status={obj.get("status")} score={obj.get("score")} '
              f'T={obj.get("toffoli_count")} Q={obj.get("num_qubits")} '
              f'lambda={obj.get("lambda_eff")}', flush=True)
    best = min((v.get('score'), k) for k, v in results.items()
                if v.get('status') == 'PASS' and v.get('score') is not None)
    print(f'\nBEST: {best[1]} score={best[0]}')
    (W / 'SUMMARY.json').write_text(json.dumps(results, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
