#!/usr/bin/env python3
"""build_salt_lab.py — build the `badboyhalo1801/salt-lab` kernel.

H17 (protect the prize): the PUBLIC board scores each submission with one
salt; the PRIVATE draw may use a different one, and the DQI leg scores a
failed shot catastrophically (one failed shot in 102,400 multiplied the cost by
~7.6x, and a private-salt failure scores the whole submission 0 per
alexchilton's 8-salt table).  Our exact shipped members have never been
tested against a private salt.

This kernel runs the UNCHANGED official DQI verifier at N salts (the empty
salt = the public draw) on the EXACT bytes of the snapshot dataset, and writes
one JSON with every result.  Each DQI run takes ~127 s in-kernel, so 6 salts
cost ~15 min of kernel time.

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import json
import pathlib

DST = pathlib.Path('/tmp/opencode/kernel_salt_lab')
SALTS = ['', 'salt-a', 'salt-b', 'salt-c', 'salt-d', 'salt-e']
SHOTS = 102400

CELL_BODY = '''
COMP = Path('/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation')
if not COMP.exists():
    hits = glob.glob('/kaggle/input/**/google-verifiable-quantum-circuit-compilation', recursive=True)
    COMP = Path(hits[0])
sys.path[:0] = [str(COMP / 'kickmix'), str(COMP / 'verifiers')]
import kickmix as km

OUT = Path('/kaggle/working')
OUT.mkdir(parents=True, exist_ok=True)

# --- locate the snapshot dataset (the anchor) -------------------------------
roots = [Path(p) for p in glob.glob('/kaggle/input/**', recursive=True)
         if Path(p).is_dir() and 'qcc-release-v133' in Path(p).as_posix()]
if not roots:
    raise SystemExit('snapshot dataset qcc-release-v133 not mounted')
root = roots[0]

# --- the exact DQI bytes (sha-pinned) ---------------------------------------
cands = [root / 'dqi.kmb'] + [Path(p) for p in root.rglob('dqi.kmb')]
cands = [c for c in cands if c.is_file()]
if not cands:
    raise SystemExit('dqi.kmb not found in ' + root.as_posix())
dqi = cands[0]
sha = hashlib.sha256(dqi.read_bytes()).hexdigest()
print('dqi.kmb:', dqi, sha[:16])

ver = {}
for p in glob.glob(str(COMP / 'verifiers' / '**' / '*.py'), recursive=True):
    ver[Path(p).name] = Path(p)
vdirs = sorted({str(p.parent) for p in ver.values()})
PY = ':'.join([str(COMP / 'kickmix')] + vdirs)
print('verifiers:', sorted(ver)[:8])

SALT_LAB = {'dqi_sha256': sha, 'shots': SHOTS, 'results': []}
script = ver.get('verify_submission_dqi.py')
if script is None:
    raise SystemExit('verify_submission_dqi.py not found')
for salt in SALTS:
    cmd = [sys.executable, str(script), str(dqi), '--num-shots', str(SHOTS)]
    if salt:
        cmd += ['--salt', salt]
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           env={**os.environ, 'PYTHONPATH': PY}, timeout=3600)
        out = (r.stdout or '') + '\\n' + (r.stderr or '')
    except subprocess.TimeoutExpired:
        out = 'TIMEOUT'
    i, j = out.find('{'), out.rfind('}')
    res = {}
    if 0 <= i < j:
        try:
            p = json.loads(out[i:j + 1]); res = p if isinstance(p, dict) else {}
        except Exception:
            pass
    rec = {'salt': salt or '(public/empty)', 'dt': round(time.time() - t, 1),
           'status': res.get('status'), 'score': res.get('score'),
           'value_errors': res.get('value_errors'), 'phase_errors': res.get('phase_errors'),
           'verified_shots': res.get('verified_shots'),
           'effective_error_rate': res.get('effective_error_rate'),
           'repetition_factor': res.get('repetition_factor'),
           'toffoli_count': res.get('toffoli_count'),
           'raw_tail': out[-700:]}
    SALT_LAB['results'].append(rec)
    print(f"[salt={salt or '(empty)'}] dt={rec['dt']}s status={rec['status']} "
          f"value_err={rec['value_errors']} phase_err={rec['phase_errors']} "
          f"score={rec['score']}", flush=True)

clean = sum(1 for r in SALT_LAB['results'] if r['status'] == 'PASS'
            and not r['value_errors'] and not r['phase_errors'])
SALT_LAB['clean'] = clean
SALT_LAB['of'] = len(SALT_LAB['results'])
SALT_LAB['verdict'] = ('SALT-CLEAN' if clean == len(SALT_LAB['results'])
                       else f'SALT-FAIL-{len(SALT_LAB["results"]) - clean}')
(OUT / 'SALT_LAB.json').write_text(json.dumps(SALT_LAB, indent=1))
print('=== salt-lab verdict:', SALT_LAB['verdict'], f'({clean}/{len(SALT_LAB["results"])} clean) ===')
'''

CELL_HEAD = '''# salt-lab — private-salt robustness of the shipped DQI decoder (H17)
#
# The public board scores every submission with ONE salt.  The private draw may
# differ, and the DQI leg is catastrophic on a failed shot (one failed shot in
# 102,400 multiplied the cost by ~7.6x; a private-salt failure scores the
# submission 0 per alexchilton's 8-salt table).  Our exact shipped DQI bytes
# (15a4b7403356092e) had never been tested against a private salt.
#
# This kernel runs the UNCHANGED official verifier at several salts on the exact
# bytes of the snapshot dataset and writes SALT_LAB.json.
import glob, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path

SALTS = __SALTS__
SHOTS = __SHOTS__
'''

META = {
    'id': 'badboyhalo1801/salt-lab',
    'title': 'salt-lab',
    'code_file': 'salt-lab.ipynb',
    'language': 'python',
    'kernel_type': 'notebook',
    'is_private': True,
    'enable_gpu': False,
    'enable_tpu': False,
    'enable_internet': False,
    'keywords': [],
    'dataset_sources': ['badboyhalo1801/qcc-release-v133'],
    'kernel_sources': [],
    'competition_sources': ['google-verifiable-quantum-circuit-compilation'],
    'model_sources': [],
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    cell = (CELL_HEAD + CELL_BODY).replace('__SALTS__', repr(SALTS)).replace('__SHOTS__', str(SHOTS))
    nb = {
        'cells': [{'cell_type': 'code', 'execution_count': None, 'metadata': {},
                   'outputs': [], 'source': cell.splitlines(keepends=True)}],
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
                     'language_info': {'name': 'python', 'version': '3.11.0'}},
        'nbformat': 4, 'nbformat_minor': 5,
    }
    path = DST / 'salt-lab.ipynb'
    path.write_text(json.dumps(nb, indent=1) + '\n')
    (DST / 'kernel-metadata.json').write_text(json.dumps(META, indent=1) + '\n')

    nb2 = json.loads(path.read_text())
    for i, c in enumerate(nb2['cells']):
        if c.get('cell_type') == 'code':
            ast.parse(''.join(c['source']))
    src = ''.join(nb2['cells'][0]['source'])
    checks = {
        'anchor': 'qcc-release-v133' in src,
        'sha pinned': 'sha256' in src,
        'salts': f'SALTS = {SALTS!r}' in src,
        'official verifier': 'verify_submission_dqi.py' in src,
        'writes receipt': 'SALT_LAB.json' in src,
        'shots official': f'SHOTS = {SHOTS}' in src,
    }
    print('salt-lab built — JSON + ast.parse gate PASS')
    for k, v in checks.items():
        print(f'  {k}: {v}')
    assert all(checks.values())
    print('notebook:', path)


if __name__ == '__main__':
    main()
