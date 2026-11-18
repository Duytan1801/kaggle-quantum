#!/usr/bin/env python3
"""sweep_chem_sets.py — score every public chemistry set (npz + 15 loaders) locally.

The chemistry leg is deterministic: cost = lambda_eff * T * Q with
T = 6662 + 2 * (per-pass loader Toffolis), so a set can be scored offline in
~20 s with the competition's own verifier.  Every public portfolio that ships a
complete set (15 loaders + submission.npz) is extracted and verified.

Usage: sweep_chem_sets.py [--pool /tmp/opencode/pool /tmp/opencode/pool2]
"""
import glob
import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time
import zipfile

PY = '/home/bandoc/Downloads/opencode/work/toolchain/venv/bin/python'
VER = '/home/bandoc/Downloads/opencode/work/toolchain/verifiers/dfthcsos/verify.py'
KICK = '/home/bandoc/Downloads/opencode/work/toolchain/kickmix'
WORK = pathlib.Path('/tmp/opencode/chem_sweep')
LOG = pathlib.Path('/tmp/opencode/chem_sweep_results.json')

ROOTS = ['/tmp/opencode/pool', '/tmp/opencode/pool2']
if '--pool' in sys.argv:
    ROOTS = sys.argv[sys.argv.index('--pool') + 1].split(',')

sets = {}          # key -> {npz: bytes, loaders: {k: bytes}, source: str}


def add_set(npz_bytes, loaders, source):
    key = hashlib.sha256(npz_bytes).hexdigest()[:12] + ':' + \
        hashlib.sha256(b''.join(loaders[k] for k in sorted(loaders))).hexdigest()[:12]
    if key in sets:
        sets[key]['also_in'].append(source)
        return
    sets[key] = {'npz': npz_bytes, 'loaders': loaders, 'source': source, 'also_in': []}


for root in ROOTS:
    for zp in sorted(glob.glob(f'{root}/*/*.zip')):
        src = os.path.basename(os.path.dirname(zp))
        try:
            z = zipfile.ZipFile(zp)
        except Exception:
            continue
        names = z.namelist()
        npzs = [n for n in names if n.lower().endswith('.npz')]
        loaders = {}
        for n in names:
            b = os.path.basename(n)
            m = re.fullmatch(r'angle_k_(\d+)\.kmb', b)
            if m:
                loaders[int(m.group(1))] = n
        if not npzs or len(loaders) < 15:
            continue
        for npz_name in npzs:
            try:
                npz_bytes = z.read(npz_name)
            except Exception:
                continue
            ld = {}
            try:
                for k in range(15):
                    ld[k] = z.read(loaders[k])
            except KeyError:
                continue
            add_set(npz_bytes, ld, f'{src}:{npz_name}')

print(f'complete chemistry sets found: {len(sets)}')
results = []
for key, s in sorted(sets.items(), key=lambda kv: kv[1]['source']):
    d = WORK / key
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    (d / 'submission.npz').write_bytes(s['npz'])
    for k, b in s['loaders'].items():
        (d / f'angle_k_{k}.kmb').write_bytes(b)
    t = time.time()
    env = {**os.environ, 'PYTHONPATH': KICK}
    try:
        r = subprocess.run([PY, VER, str(d)], capture_output=True, text=True,
                           env=env, timeout=1800)
        out = (r.stdout or '') + '\n' + (r.stderr or '')
    except subprocess.TimeoutExpired:
        out = 'TIMEOUT'
    dt = round(time.time() - t, 1)
    i, j = out.find('{'), out.rfind('}')
    res = {}
    if 0 <= i < j:
        try:
            res = json.loads(out[i:j + 1])
        except Exception:
            pass
    rec = {
        'key': key,
        'source': s['source'],
        'also_in': s['also_in'],
        'npz_sha12': hashlib.sha256(s['npz']).hexdigest()[:12],
        'loader_sha12s': {k: hashlib.sha256(s['loaders'][k]).hexdigest()[:12] for k in sorted(s['loaders'])},
        'status': res.get('status'),
        'score': res.get('score'),
        'lambda_eff': res.get('lambda_eff'),
        'toffoli_count': res.get('toffoli_count'),
        'num_qubits': res.get('num_qubits'),
        'dt': dt,
        'tail': out[-400:],
    }
    results.append(rec)
    print(f"{key}  {rec['status']:<5} score={rec['score']}  T={rec['toffoli_count']}  "
          f"Q={rec['num_qubits']}  lambda={rec['lambda_eff']}  dt={dt}s  <- {s['source']}")
    shutil.rmtree(d, ignore_errors=True)

LOG.write_text(json.dumps(results, indent=1))
good = [r for r in results if r.get('score')]
good.sort(key=lambda r: r['score'])
print('\n=== best chemistry sets ===')
for r in good[:12]:
    print(f"  {r['score']:>18,.2f}  T={r['toffoli_count']:<8} Q={r['num_qubits']} "
          f"lambda={r['lambda_eff']}  {r['key']}  {r['source']}")
print('written', LOG)
