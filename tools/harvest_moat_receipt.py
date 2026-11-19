#!/usr/bin/env python3
"""harvest_moat_receipt.py — wait for the moat-lab kernel run and harvest its receipt.

The SECOND mechanical receipt of the two-receipt gate is the moat-lab's
in-kernel verification: the kernel runs the UNCHANGED official verifiers on the
exact bytes of the snapshot dataset and writes `V<NN>_RECEIPT.json` with a
`-RECEIPT-PASS` verdict.  This tool waits for the run to reach a terminal
state, downloads the output, and copies the receipt into work/receipts/.

Usage:
  harvest_moat_receipt.py --version 50 --label V133 [--poll 60] [--timeout 5400]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KERNEL = 'badboyhalo1801/moat-lab'


def status() -> str:
    r = subprocess.run(['kaggle', 'kernels', 'status', KERNEL], capture_output=True, text=True,
                       timeout=180)
    out = (r.stdout or '') + (r.stderr or '')
    for st in ('COMPLETE', 'ERROR', 'RUNNING', 'CANCELLED'):
        if st in out:
            return st
    return 'UNKNOWN'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', type=int, required=True)
    ap.add_argument('--label', required=True, help='e.g. V133')
    ap.add_argument('--poll', type=int, default=60)
    ap.add_argument('--timeout', type=int, default=5400)
    a = ap.parse_args()

    out_dir = pathlib.Path(f'/tmp/opencode/moat_out_{a.label.lower()}')
    if out_dir.exists():
        shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    st = status()
    print(f'[{time.strftime("%H:%M:%S")}] moat-lab status: {st}', flush=True)
    while st not in ('COMPLETE', 'ERROR', 'CANCELLED'):
        if time.time() - t0 > a.timeout:
            print('TIMEOUT waiting for the kernel run', flush=True)
            return 2
        time.sleep(a.poll)
        st = status()
        print(f'[{time.strftime("%H:%M:%S")}] moat-lab status: {st} '
              f'({time.time()-t0:.0f}s)', flush=True)
    if st != 'COMPLETE':
        print(f'kernel finished with {st}', flush=True)

    r = subprocess.run(['kaggle', 'kernels', 'output', KERNEL, '-p', str(out_dir)],
                       capture_output=True, text=True, timeout=1800)
    print('output fetch rc=', r.returncode, (r.stdout or '')[-200:], flush=True)

    receipt = out_dir / f'{a.label}_RECEIPT.json'
    if not receipt.exists():
        cands = list(out_dir.rglob('*RECEIPT*.json'))
        print('receipt not found; candidates:', [str(c) for c in cands], flush=True)
        return 3
    dest = ROOT / 'work/receipts' / f'{a.label}_MOAT_RECEIPT.json'
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(receipt, dest)
    data = json.loads(receipt.read_text())
    print('verdict:', data.get('verdict'), flush=True)
    print('shas_ok:', data.get('shas_ok'), flush=True)
    print('gm_pred:', data.get('gm_pred'), flush=True)
    print('ratios:', data.get('ratios'), flush=True)
    print('dqi:', {k: v for k, v in (data.get('verifies') or {}).get('dqi', {}).items()
                   if k in ('status', 'score', 'value_errors', 'phase_errors', 'verified_shots')},
          flush=True)
    print('dfthcsos_in_kernel:', {k: v for k, v in (data.get('dfthcsos_in_kernel') or {}).items()
                                  if k in ('status', 'score', 'lambda_eff', 'toffoli_count',
                                           'num_qubits')}, flush=True)
    print('invsqrt_anchor:', {k: v for k, v in (data.get('invsqrt_anchor') or {}).items()
                               if k in ('status', 'score', 'num_qubits', 'verified_shots',
                                        'circuit_sha256')}, flush=True)
    print(f'wrote {dest}', flush=True)
    return 0 if data.get('verdict', '').endswith('RECEIPT-PASS') else 1


if __name__ == '__main__':
    raise SystemExit(main())
