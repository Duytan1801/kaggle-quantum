#!/usr/bin/env python3
"""build_moat_v148.py — build the `badboyhalo1801/moat-lab` in-kernel gate for v148.

The SECOND mechanical receipt of the two-receipt gate: an in-kernel run of the
UNCHANGED official verifiers on the exact snapshot-dataset bytes.

v148 = v147's invsqrt + DQI with goodpjw2008's shorter chemistry loaders
(`qcc-shorter-chemistry-loaders-lb-33-21011`, public LB 33.21011):

  invsqrt   bb676b95f94c923c   60,927.57739905387   (37 q, unchanged)
  dqi       6f78ecdd636051d4   ~305,032,962,722    (unchanged)
  dfthcsos  npz 573d10bed90b4ad7 + 10 re-solved 3,334-T loaders
            + 5 unchanged 3,357-T loaders
            250,195,979.3541336 (405 q, lambda_eff 46.91432641685298, T 13,168)
            => -893,577.67 cost units vs v147 => predicted GM 33.21008

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
DST = pathlib.Path('/tmp/opencode/kernel_moat_v148')
TABLE = json.loads((ROOT / 'work/sha_tables/sha_table_v148.txt').read_text())['files']
assert len(TABLE) == 18, f'expected 18 files, got {len(TABLE)}'

ANCHOR = 'qcc-release-v148'
DATASET = 'badboyhalo1801/qcc-release-v148'

SHA_LINES = ',\n'.join(f'    {k!r}: ({v[0]!r}, {v[1]})' for k, v in sorted(TABLE.items()))

CELL = '''# moat-lab — v148 RELEASE RECEIPT
#
# The gate's second receipt: run the UNCHANGED official verifiers in-kernel on
# the exact bytes of the snapshot dataset, and write V148_RECEIPT.json with a
# V148-RECEIPT-PASS verdict only if every leg passes.
#
# v148 = v147 tree + goodpjw2008's shorter chemistry loaders (public 33.21011):
#   invsqrt  bb676b95f94c923c   (37 qubits, 1406.31 Toffolis)
#   dqi      6f78ecdd636051d4   (0 value / 0 phase errors on the public draw)
#   chem     npz 573d10bed90b4ad7 + 10 3,334-T + 5 3,357-T loaders (T=13168, Q=405)
import glob, hashlib, json, os, shutil, subprocess, sys, time
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
    receipt = {'portfolio': 'v148_shorter_chem_loaders', 'shas_ok': False,
               'missing': missing, 'bad_sha': bad,
               'verdict': 'V148-RECEIPT-FAIL-SHA'}
    Path('/kaggle/working/V148_RECEIPT.json').write_text(json.dumps(receipt, indent=1))
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
    # Kaggle's current dataset CLI may flatten the chemistry directory.
    # Materialize the verifier's required angle_k_*.kmb names locally.
    chem_root = Path('/kaggle/working') / 'dfthcsos_v148'
    chem_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    for rel, src in paths.items():
        if rel.startswith('dfthcsos/'):
            shutil.copyfile(src, chem_root / Path(rel).name)
            copied += 1
    if copied != 16:
        raise SystemExit(f'expected 16 chemistry files, copied {copied}')
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
# The OFFICIAL DQI contract is the verifier's own verdict (eps_plus < 1/16);
# a non-zero failed-shot count is NOT a verifier failure.  The public board's
# shot draw is NOT the default salt (three public trees prove it: 4b572141 /
# 141f02ac / 6f78ecdd drew 0 / 2 / 4 failed shots at the default salt and 0 on
# the board), so a non-zero default-salt count is a lottery draw, not a
# verdict.  A DQI leg with failed shots is therefore admissible ONLY when
# PUBLIC_DQI_EVIDENCE names the EXACT bytes we ship together with a public
# leaderboard score for them.  No evidence -> REJECT (still fail-closed).
PUBLIC_DQI_EVIDENCE = [{'release': 'goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067', 'public_lb': 33.17067, 'dqi_sha256': '6f78ecdd636051d4d2dd8f24aaece1d454eb220aaf0df2c1d64c3d96fe22081d', 'note': 'the release that shipped these exact DQI bytes; its notebook states "The public leaderboard draw of this file had none", and the whole tree was scored 33.17067 on the public board'}, {'release': 'liuzewen123/qcc-dqi-zero-test-cuts-verbatim-33-17067', 'public_lb': 33.17067, 'dqi_sha256': '6f78ecdd636051d4d2dd8f24aaece1d454eb220aaf0df2c1d64c3d96fe22081d', 'note': 'an independent verbatim copy of the same 18 bytes, scored 33.17067 on the public board'}]
dqi_err = (dqi.get('value_errors') or 0) + (dqi.get('phase_errors') or 0)
dqi_sha = dqi.get('circuit_sha256')
if dqi_err:
    hit = [e for e in PUBLIC_DQI_EVIDENCE if e['dqi_sha256'] == dqi_sha]
    log('DQI SHOT ERRORS:', dqi.get('value_errors'), dqi.get('phase_errors'),
        '| public board evidence rows for these exact bytes:', len(hit))
    if not hit:
        ok = False
        log('NO PUBLIC BOARD EVIDENCE for this DQI bytes -> REJECT')
else:
    log('DQI default-salt draw is clean (0 value / 0 phase errors)')

gm = None
if len(ratios) == 3:
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3)

receipt = {
    'portfolio': 'v148_shorter_chem_loaders',
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
    'public_dqi_evidence': PUBLIC_DQI_EVIDENCE,
    'dqi_default_salt_failed_shots': dqi_err,
    'ratios': ratios,
    'gm': gm,
    'dataset': '__DATASET__',
    'verdict': 'V148-RECEIPT-PASS' if ok and gm else 'V148-RECEIPT-FAIL',
}
Path('/kaggle/working/V148_RECEIPT.json').write_text(json.dumps(receipt, indent=1))
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
        'labels': 'V148_RECEIPT.json' in src and 'V148-RECEIPT-PASS' in src,
        'sha gate blocks': 'SHA GATE FAILED' in src,
        'dqi errors gate': 'DQI SHOT ERRORS' in src,
    }
    print('moat-lab v148 built — JSON + ast.parse gate PASS')
    for k, v in checks.items():
        print(f'  {k}: {v}')
    assert all(checks.values())
    print('notebook:', p)


if __name__ == '__main__':
    main()
