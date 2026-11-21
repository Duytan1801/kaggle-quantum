#!/usr/bin/env python3
"""build_moat_v136.py — build the `badboyhalo1801/moat-lab` in-kernel gate for v136.

The SECOND mechanical receipt of the two-receipt gate: an in-kernel run of the
UNCHANGED official verifiers on the exact snapshot-dataset bytes.

v136 = the public-best tree (LB 33.1002) published as the output of
`goodpjw2008/qcc-public-best-loader-table-swap-lb-33-0753`:

  invsqrt   d2148a7cd7a4d0a0   60,955.32670759028   (37 q)
  dqi       4b5721411adc239f   305,041,647,011.3978 (0 value / 0 phase errors)
  dfthcsos  npz 6b9903dda33a + exchanged loader_k_2 046679fe
            253,143,456.48793402 (405 q, lambda_eff 46.918298421794454)

This builder writes a fresh notebook (the v1xx template lived in volatile
/tmp/opencode and was lost).  It is deliberately defensive about the dataset
layout (Kaggle may keep `dfthcsos/` or flatten it to `dfthcsos__*`) and about
verifier CLIs, and it never invents a verdict: every leg must come back PASS
from a parsed JSON block.

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
DST = pathlib.Path('/tmp/opencode/kernel_moat_v136')
TABLE = json.loads((ROOT / 'work/sha_tables/sha_table_v136.txt').read_text())['files']
assert len(TABLE) == 18, f'expected 18 files, got {len(TABLE)}'

ANCHOR = 'qcc-release-v136'
DATASET = 'badboyhalo1801/qcc-release-v136'

SHA_LINES = ',\n'.join(f'    {k!r}: ({v[0]!r}, {v[1]})' for k, v in sorted(TABLE.items()))

CELL = '''# moat-lab — v136 RELEASE RECEIPT
#
# The gate's second receipt: run the UNCHANGED official verifiers in-kernel on
# the exact bytes of the snapshot dataset, and write V136_RECEIPT.json with a
# V136-RECEIPT-PASS verdict only if every leg passes.
#
# v136 = public-best 33.1002 tree (goodpjw2008 kernel output):
#   invsqrt  d2148a7cd7a4d0a0   (37 qubits, 1406.31 Toffolis)
#   dqi      4b5721411adc239f   (0 value / 0 phase errors on the public draw)
#   chem     npz 6b9903dda33a + exchanged loader_k_2 046679fe
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
    hits = glob.glob('/kaggle/input/**/google-verifiable-quantum-circuit-compilation',
                     recursive=True)
    hits = [h for h in hits if Path(h, 'verifiers').is_dir()]
    if not hits:
        raise SystemExit('competition verifiers not mounted')
    COMP = Path(hits[0])
VER, KICK = COMP / 'verifiers', COMP / 'kickmix'
sys.path[:0] = [str(KICK), str(VER)]
import kickmix as km

ENV = dict(os.environ)
ENV['PYTHONPATH'] = os.pathsep.join(
    [str(KICK), str(VER)] + sorted({str(p.parent) for p in VER.rglob('*.py')})
    + ([ENV['PYTHONPATH']] if ENV.get('PYTHONPATH') else []))
PY = sys.executable
log('competition:', COMP)

REF = {'invsqrt': 2076774.233715282, 'dqi': 24439463583672.93,
       'dfthcsos': 3355599588.3155375}

SHA_TABLE = {
__SHA_LINES__
}
assert len(SHA_TABLE) == 18, len(SHA_TABLE)

# ---------------------------------------------------------------- dataset ---
roots = [Path(p) for p in glob.glob('/kaggle/input/**', recursive=True)
         if Path(p).is_dir() and '__ANCHOR__' in Path(p).as_posix()]
if not roots:
    raise SystemExit('snapshot dataset __ANCHOR__ not mounted')
root = sorted(roots, key=lambda p: len(p.as_posix()))[0]
log('dataset root:', root)

def find_file(rel: str) -> Path | None:
    cands = [root / rel,
             root / rel.replace('/', '__'),
             root / '__'.join(rel.split('/')),
             root / rel.split('/')[-1]]
    for c in cands:
        if c.is_file():
            return c
    base = rel.split('/')[-1]
    hits = [Path(p) for p in root.rglob(base) if Path(p).is_file()]
    if hits:
        # prefer the candidate whose parent matches the subdirectory name
        sub = rel.split('/')[0] if '/' in rel else None
        if sub:
            for h in hits:
                if sub in h.as_posix():
                    return h
        return sorted(hits, key=lambda p: len(p.as_posix()))[0]
    return None

paths, missing, bad = {}, [], []
for rel, (sha, size) in SHA_TABLE.items():
    p = find_file(rel)
    if p is None:
        missing.append(rel)
        continue
    b = p.read_bytes()
    if hashlib.sha256(b).hexdigest() != sha or len(b) != size:
        bad.append(rel)
    paths[rel] = p
shas_ok = not missing and not bad
log('files found:', len(paths), '| missing:', missing, '| sha mismatch:', bad)
if not shas_ok:
    receipt = {'portfolio': 'v136_public_best_33_1002', 'shas_ok': False,
               'missing': missing, 'bad_sha': bad,
               'verdict': 'V136-RECEIPT-FAIL-SHA'}
    Path('/kaggle/working/V136_RECEIPT.json').write_text(json.dumps(receipt, indent=1))
    raise SystemExit('SHA GATE FAILED')

# ------------------------------------------------------------- verifiers ---
def run_verify(script: Path, target: Path, extra: list[str], label: str,
               timeout: int = 7200) -> dict:
    cmd = [PY, str(script), str(target)] + extra
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=timeout)
        out = (r.stdout or '') + '\\n' + (r.stderr or '')
    except subprocess.TimeoutExpired:
        out = 'TIMEOUT'
    i, j = out.find('{'), out.rfind('}')
    res = {}
    if 0 <= i < j:
        try:
            p = json.loads(out[i:j + 1])
            res = p if isinstance(p, dict) else {}
        except Exception:
            res = {}
    log(f'[{label}] dt={time.time()-t:.0f}s status={res.get("status")} '
        f'score={res.get("score")}')
    if not res:
        log(f'[{label}] tail:', out[-500:].replace(chr(10), ' | '))
    res['_dt'] = round(time.time() - t, 1)
    res['_raw_tail'] = out[-700:]
    return res

INV = paths['invsqrt.kmb']
DQI = paths['dqi.kmb']

# invsqrt: the official 200,540,928-shot run.  37 qubits / 1406 Toffolis is well
# inside the kernel budget (the same circuit took ~20 min whole-portfolio in a
# public kernel).  Generous timeout; a timeout is a FAIL, never an anchor.
inv = run_verify(VER / 'invsqrt' / 'verify_submission_invsqrt.py', INV, [],
                 'invsqrt', timeout=10800)

# dqi: default 102,400 shots, default (empty) salt = the public draw.
dqi = run_verify(VER / 'dqi' / 'verify_submission_dqi.py', DQI, [],
                 'dqi', timeout=10800)

# dfthcsos: the verifier takes the directory holding angle_k_* + submission.npz.
chem_root = root / 'dfthcsos'
if not chem_root.is_dir():
    idx = next((p.parent for r, p in paths.items() if r.endswith('angle_k_0.kmb')), None)
    if idx is None:
        raise SystemExit('dfthcsos directory not found')
    chem_root = idx
log('chem dir:', chem_root, sorted(p.name for p in chem_root.iterdir())[:4])
chem = run_verify(VER / 'dfthcsos' / 'verify.py', chem_root,
                  ['--shots-per-address', '1'], 'dfthcsos', timeout=10800)

# --------------------------------------------------------------- receipt ---
legs = {'invsqrt': inv, 'dqi': dqi, 'dfthcsos': chem}
ratios, ok = {}, shas_ok
for leg, r in legs.items():
    if r.get('status') != 'PASS' or r.get('score') is None:
        ok = False
        log('LEG NOT PASS:', leg, r.get('status'))
    else:
        ratios[leg] = REF[leg] / r['score']
if dqi.get('value_errors') or dqi.get('phase_errors'):
    ok = False
    log('DQI SHOT ERRORS:', dqi.get('value_errors'), dqi.get('phase_errors'))

gm = None
if len(ratios) == 3:
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3)

receipt = {
    'portfolio': 'v136_public_best_33_1002',
    'shas_ok': shas_ok,
    'verifiers': ['verify_submission_invsqrt.py', 'verify_submission_dqi.py',
                  'dfthcsos/verify.py'],
    'verifies': {
        'invsqrt': {k: inv.get(k) for k in (
            'status', 'score', 'num_qubits', 'toffoli_count', 'toffoli_equivalent',
            'rotation_count', 'rotation_eps', 'verified_shots',
            'worst_error_over_tolerance', 'worst_x', 'circuit_sha256')},
        'dqi': {k: dqi.get(k) for k in (
            'status', 'score', 'num_qubits', 'toffoli_count', 'value_errors',
            'phase_errors', 'verified_shots', 'effective_error_rate',
            'repetition_factor', 'circuit_sha256')},
        'dfthcsos': {k: chem.get(k) for k in (
            'status', 'score', 'num_qubits', 'toffoli_count', 'lambda_eff',
            'batch_size')},
    },
    'leg_timings': {k: v.get('_dt') for k, v in legs.items()},
    'ratios': ratios,
    'gm': gm,
    'dataset': '__DATASET__',
    'verdict': 'V136-RECEIPT-PASS' if ok and gm else 'V136-RECEIPT-FAIL',
}
Path('/kaggle/working/V136_RECEIPT.json').write_text(json.dumps(receipt, indent=1))
print('=== VERDICT', receipt['verdict'], '| GM', gm, '===', flush=True)
print(json.dumps(receipt['verifies'], indent=1), flush=True)
'''

META = {
    'id': 'badboyhalo1801/moat-lab',
    'title': 'moat-lab',
    'code_file': 'moat-lab.ipynb',
    'language': 'python',
    'kernel_type': 'notebook',
    'is_private': True,
    'enable_gpu': False,
    'enable_tpu': False,
    'enable_internet': False,
    'keywords': [],
    'dataset_sources': [DATASET],
    'kernel_sources': [],
    'competition_sources': ['google-verifiable-quantum-circuit-compilation'],
    'model_sources': [],
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    cell = (CELL.replace('__SHA_LINES__', SHA_LINES)
                .replace('__ANCHOR__', ANCHOR)
                .replace('__DATASET__', DATASET))
    nb = {
        'cells': [{'cell_type': 'code', 'execution_count': None, 'metadata': {},
                   'outputs': [], 'source': cell.splitlines(keepends=True)}],
        'metadata': {'kernelspec': {'display_name': 'Python 3', 'language': 'python',
                                    'name': 'python3'},
                     'language_info': {'name': 'python', 'version': '3.11.0'}},
        'nbformat': 4, 'nbformat_minor': 5,
    }
    p = DST / 'moat-lab.ipynb'
    p.write_text(json.dumps(nb, indent=1) + '\n')
    (DST / 'kernel-metadata.json').write_text(json.dumps(META, indent=1) + '\n')

    nb2 = json.loads(p.read_text())
    for i, c in enumerate(nb2['cells']):
        if c.get('cell_type') == 'code':
            ast.parse(''.join(c['source']))
    src = ''.join(nb2['cells'][0]['source'])
    checks = {
        'anchor': f'__ANCHOR__'.replace('__ANCHOR__', ANCHOR) in src,
        'sha table 18': src.count("': ('") >= 18,
        'three verifiers': all(s in src for s in (
            'verify_submission_invsqrt.py', 'verify_submission_dqi.py',
            "'dfthcsos' / 'verify.py'")),
        'no anchor shortcut': 'INVSQLT_ANCHOR' not in src,
        'labels': 'V136_RECEIPT.json' in src and 'V136-RECEIPT-PASS' in src,
        'sha gate blocks': 'SHA GATE FAILED' in src,
        'dqi errors gate': 'DQI SHOT ERRORS' in src,
    }
    print('moat-lab v136 built — JSON + ast.parse gate PASS')
    for k, v in checks.items():
        print(f'  {k}: {v}')
    assert all(checks.values())
    print('notebook:', p)


if __name__ == '__main__':
    main()
