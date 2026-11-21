#!/usr/bin/env python3
"""build_salt_probe.py — build the `badboyhalo1801/salt-probe` kernel (H21).

The private board re-runs the official verifiers with a salt nobody knows.  A DQI
circuit that passes at the default salt can draw a *failed shot* at another salt,
and one failed shot raises the DQI cost by the repetition factor (alexchilton's
8-salt study: +0.46 % cost per failed shot in 102,400 shots).

v135's dqi (4b572141) has only ever been measured at the default salt, so this
kernel runs the UNCHANGED official DQI verifier on the exact snapshot bytes at
four extra salts and reports the cost + error counts for each.

Cheap insurance: 4 x ~130 s.  Output: SALT_PROBE.json in /kaggle/working.
"""
from __future__ import annotations

import ast
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
DST = pathlib.Path('/tmp/opencode/kernel_salt_probe')
TABLE = json.loads((ROOT / 'work/sha_tables/sha_table_v135.txt').read_text())['files']
DQI_SHA = TABLE['dqi.kmb'][0]
DQI_SIZE = TABLE['dqi.kmb'][1]

SALTS = ['salt-v135-a', 'salt-v135-b', 'salt-v135-c', 'salt-v135-d']

CELL = '''# salt-probe — H21: does v135's DQI survive a non-default salt?
#
# Runs the UNCHANGED official DQI verifier on the exact snapshot bytes at four
# salts.  The default salt gave 305,041,647,011.3978 with 0 value / 0 phase
# errors; a failed shot at another salt raises the cost by the repetition
# factor (measured +0.46 % per failed shot by alexchilton).
import glob, hashlib, json, os, subprocess, sys, time
from pathlib import Path

T0 = time.time()
def log(*a):
    print(f"[{(time.time()-T0)/60:6.2f} min]", *a, flush=True)

COMP = None
for cand in ('/kaggle/input/competitions/google-verifiable-quantum-circuit-compilation',
             '/kaggle/input/google-verifiable-quantum-circuit-compilation'):
    if Path(cand, 'verifiers').is_dir():
        COMP = Path(cand)
        break
if COMP is None:
    hits = [h for h in glob.glob('/kaggle/input/**/google-verifiable-quantum-circuit-compilation',
                                 recursive=True) if Path(h, 'verifiers').is_dir()]
    if not hits:
        raise SystemExit('competition verifiers not mounted')
    COMP = Path(hits[0])
VER, KICK = COMP / 'verifiers', COMP / 'kickmix'
ENV = dict(os.environ)
ENV['PYTHONPATH'] = os.pathsep.join([str(KICK), str(VER)])
PY = sys.executable
log('competition:', COMP)

DQI_SHA = '__DQI_SHA__'
DQI_SIZE = __DQI_SIZE__
SALTS = __SALTS__

roots = [Path(p) for p in glob.glob('/kaggle/input/**', recursive=True)
         if Path(p).is_dir() and 'qcc-release-v135' in Path(p).as_posix()]
if not roots:
    raise SystemExit('snapshot dataset qcc-release-v135 not mounted')
root = sorted(roots, key=lambda p: len(p.as_posix()))[0]
log('dataset root:', root)

hits = [Path(p) for p in root.rglob('dqi.kmb') if Path(p).is_file()]
if not hits:
    raise SystemExit('dqi.kmb not found in snapshot')
dqi = sorted(hits, key=lambda p: len(p.as_posix()))[0]
b = dqi.read_bytes()
sha = hashlib.sha256(b).hexdigest()
log('dqi:', dqi, len(b), sha[:16])
if sha != DQI_SHA or len(b) != DQI_SIZE:
    out = {'verdict': 'SALT-PROBE-FAIL-SHA', 'sha256': sha, 'bytes': len(b)}
    Path('/kaggle/working/SALT_PROBE.json').write_text(json.dumps(out, indent=1))
    raise SystemExit('DQI SHA GATE FAILED')

rows = []
for salt in [''] + SALTS:
    t = time.time()
    cmd = [PY, str(VER / 'dqi' / 'verify_submission_dqi.py'), str(dqi)]
    if salt:
        cmd += ['--salt', salt]
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=7200)
    o = (r.stdout or '') + '\\n' + (r.stderr or '')
    i, j = o.find('{'), o.rfind('}')
    res = {}
    if 0 <= i < j:
        try:
            res = json.loads(o[i:j + 1])
        except Exception:
            res = {}
    row = {
        'salt': salt or '(default)',
        'status': res.get('status'),
        'score': res.get('score'),
        'value_errors': res.get('value_errors'),
        'phase_errors': res.get('phase_errors'),
        'toffoli_count': res.get('toffoli_count'),
        'num_qubits': res.get('num_qubits'),
        'repetition_factor': res.get('repetition_factor'),
        'effective_error_rate': res.get('effective_error_rate'),
        'seconds': round(time.time() - t, 1),
    }
    if not res:
        row['tail'] = o[-400:]
    rows.append(row)
    log(salt or '(default)', 'status', row['status'], 'score', row['score'],
        'err', row['value_errors'], row['phase_errors'])

base = next((r for r in rows if r['salt'] == '(default)'), {})
worst = max((r for r in rows if r.get('score')), key=lambda r: r['score'], default={})
out = {
    'dqi_sha256': sha,
    'default_score': base.get('score'),
    'worst_score': worst.get('score'),
    'worst_salt': worst.get('salt'),
    'worst_factor': (worst['score'] / base['score']) if base.get('score') and worst.get('score') else None,
    'any_errors': any((r.get('value_errors') or 0) + (r.get('phase_errors') or 0) for r in rows),
    'rows': rows,
    'verdict': 'SALT-PROBE-DONE',
}
Path('/kaggle/working/SALT_PROBE.json').write_text(json.dumps(out, indent=1))
print('=== SALT PROBE ===', flush=True)
print(json.dumps(out, indent=1), flush=True)
'''

META = {
    'id': 'badboyhalo1801/salt-probe',
    'title': 'salt-probe',
    'code_file': 'salt-probe.ipynb',
    'language': 'python',
    'kernel_type': 'notebook',
    'is_private': True,
    'enable_gpu': False,
    'enable_tpu': False,
    'enable_internet': False,
    'keywords': [],
    'dataset_sources': ['badboyhalo1801/qcc-release-v135'],
    'kernel_sources': [],
    'competition_sources': ['google-verifiable-quantum-circuit-compilation'],
    'model_sources': [],
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    cell = (CELL.replace('__DQI_SHA__', DQI_SHA)
                .replace('__DQI_SIZE__', str(DQI_SIZE))
                .replace('__SALTS__', repr(SALTS)))
    nb = {
        'cells': [{'cell_type': 'code', 'execution_count': None, 'metadata': {},
                   'outputs': [], 'source': cell.splitlines(keepends=True)}],
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python',
                                    'name': 'python3'},
                     'language_info': {'name': 'python', 'version': '3.11.0'}},
        'nbformat': 4, 'nbformat_minor': 5,
    }
    p = DST / 'salt-probe.ipynb'
    p.write_text(json.dumps(nb, indent=1) + '\n')
    (DST / 'kernel-metadata.json').write_text(json.dumps(META, indent=1) + '\n')
    nb2 = json.loads(p.read_text())
    for c in nb2['cells']:
        if c.get('cell_type') == 'code':
            ast.parse(''.join(c['source']))
    src = ''.join(nb2['cells'][0]['source'])
    assert DQI_SHA in src and 'DQI SHA GATE FAILED' in src and 'SALT_PROBE.json' in src
    assert src.count('--salt') >= 1
    print('salt-probe built — JSON + ast.parse gate PASS')
    print('notebook:', p)


if __name__ == '__main__':
    main()
