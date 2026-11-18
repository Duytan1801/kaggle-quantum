#!/usr/bin/env python3
"""sweep_invsqrt.py — download every public invsqrt circuit of the competition and
score it with the OFFICIAL verifier, then report the best.

Source: manwithacat/vqcc-apache-public-circuits (the community's mirror of every
public circuit file).  We fetch the 96 `circuits/invsqrt/*.kmb` members one by one
(`kaggle datasets download -f` keeps each download small), run the unmodified official
verifier `work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py` on each, and
write a CSV table.

Usage: sweep_invsqrt.py <paths.txt> <outdir> <out.csv>
"""
from __future__ import annotations

import csv
import json
import pathlib
import subprocess
import sys

KG = '/home/bandoc/Downloads/opencode/qaenv/bin/kaggle'
VER = '/home/bandoc/Downloads/opencode/work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py'
PY = '/home/bandoc/Downloads/opencode/work/toolchain/venv/bin/python'
KICK = '/home/bandoc/Downloads/opencode/work/toolchain/kickmix'
DS = 'manwithacat/vqcc-apache-public-circuits'


def main():
    paths = pathlib.Path(sys.argv[1]).read_text().split()
    outdir = pathlib.Path(sys.argv[2])
    outcsv = pathlib.Path(sys.argv[3])
    outdir.mkdir(parents=True, exist_ok=True)
    inv = [p for p in paths if p.startswith('circuits/invsqrt/')]
    rows = []
    if outcsv.exists():
        rows = list(csv.DictReader(outcsv.open()))
    done = {r['path'] for r in rows}
    for i, p in enumerate(inv):
        if p in done:
            continue
        dst = outdir / p          # kaggle keeps the dataset path structure
        if not dst.exists():
            r = subprocess.run([KG, 'datasets', 'download', '-d', DS, '-f', p, '-p', str(outdir)],
                               capture_output=True, text=True, timeout=900)
            if not dst.exists():
                print(f'[{i+1}/{len(inv)}] DOWNLOAD FAILED {p}: {r.stderr[-200:]}', flush=True)
                continue
        env = {'PYTHONPATH': KICK, 'PATH': '/usr/bin:/bin'}
        r = subprocess.run([PY, VER, str(dst), '--shots-per-x', '4', '--batch-size', '16',
                            '--max-workers', '4'],
                           capture_output=True, text=True, env=env, timeout=1800)
        txt = r.stdout + r.stderr
        i0, j0 = txt.find('{'), txt.rfind('}')
        rec = {'path': p, 'status': 'ERROR', 'score': '', 'num_qubits': '', 'toffoli_count': '',
               'rotation_count': '', 'rotation_eps': '', 'worst': '', 'tail': txt[-300:]}
        if 0 <= i0 < j0:
            try:
                d = json.loads(txt[i0:j0 + 1])
                rec.update(status=d.get('status', ''), score=d.get('score', ''),
                           num_qubits=d.get('num_qubits', ''),
                           toffoli_count=d.get('toffoli_count', ''),
                           rotation_count=d.get('rotation_count', ''),
                           rotation_eps=d.get('rotation_eps', ''),
                           worst=d.get('worst_error_over_tolerance', ''))
            except Exception as e:
                rec['tail'] = f'json {e!r} ' + rec['tail']
        rows.append(rec)
        print(f'[{i+1}/{len(inv)}] {plib_name(p)} status={rec["status"]} score={rec["score"]} '
              f'Q={rec["num_qubits"]} T={rec["toffoli_count"]}', flush=True)
        with outcsv.open('w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)


def plib_name(p):
    return pathlib.Path(p).name


if __name__ == '__main__':
    main()
