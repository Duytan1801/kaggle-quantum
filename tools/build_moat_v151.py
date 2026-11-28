#!/usr/bin/env python3
"""build_moat_v151.py — build the `badboyhalo1801/moat-lab` in-kernel gate for v151.

The SECOND mechanical receipt of the two-receipt gate: an in-kernel run of the
UNCHANGED official verifiers on the exact snapshot-dataset bytes.

v151 = goodpjw2008's `qcc-shorter-chemistry-loaders-lb-33-25733` tree (public
LB 33.25733), which is the public frontier and beats our v150 (33.25564):

  invsqrt   6b59214530108d8c   prvsiyan's variant, 37 q   (NEW bytes vs v150)
  dqi       6f78ecdd636051d4   unchanged from v149/v150
  dfthcsos  npz 25ac10da813d2f2 + 5 re-solved loaders
            249,131,841.8273937 (405 q, lambda_eff 46.91430370584927, T 13,112)
            => -38,000.59 cost units vs v150's 249,169,842.41339546

The invsqrt member is NEW BYTES, so it needs its own in-kernel official run:
unlike v150's invsqrt (byte-identical to v149, already covered), 6b592145 has
no prior in-kernel receipt, and the campaign rule is that no member enters a
submission tree without one.

DQI 6f78ecdd is byte-identical to v149/v150 and keeps the public-board evidence
(goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067 and liuzewen123's verbatim copy
both scored 33.17067 with these exact bytes).

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import re
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
DST = pathlib.Path('/tmp/opencode/kernel_moat_v151')
TABLE = json.loads((ROOT / 'work/sha_tables/sha_table_v151.txt').read_text())['files']
assert len(TABLE) == 18, f'expected 18 files, got {len(TABLE)}'

ANCHOR = 'qcc-release-v151'
DATASET = 'badboyhalo1801/qcc-release-v151'

SHA_LINES = ',\n'.join(f'    {k!r}: ({v[0]!r}, {v[1]})' for k, v in sorted(TABLE.items()))

CELL = '''# moat-lab — v151 RELEASE RECEIPT
#
# The gate's second receipt: run the UNCHANGED official verifiers in-kernel on
# the exact bytes of the snapshot dataset, and write V151_RECEIPT.json with a
# V151-RECEIPT-PASS verdict only if every leg passes.
#
# v151 = goodpjw2008's 33.25733 tree (public frontier, beats our v150 33.25564):
#   invsqrt  6b59214530108d8c   (37 qubits)  NEW BYTES -> full official run here
#   dqi      6f78ecdd636051d4   (900 qubits) unchanged from v149/v150
#   chem     npz 25ac10da813d2f2 + 5 re-solved loaders (T=13112, Q=405)
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
VER = COMP / 'verifiers'
log('competition:', COMP)

ENV = dict(os.environ)
ENV['PYTHONPATH'] = f"{VER}:{COMP / 'kickmix'}"

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
    hits = [Path(p) for p in root.rglob(base) if p.is_file()]
    if hits:
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
    receipt = {'portfolio': 'v151_gpw_v22_chemistry', 'shas_ok': False,
               'missing': missing, 'bad_sha': bad,
               'verdict': 'V151-RECEIPT-FAIL-SHA'}
    Path('/kaggle/working/V151_RECEIPT.json').write_text(json.dumps(receipt, indent=1))
    raise SystemExit('SHA GATE FAILED')

# ------------------------------------------------------------- verifiers ---
PY = sys.executable

def run_verify(script: Path, target: Path, extra: list[str], label: str,
               timeout: int = 10800) -> dict:
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

# invsqrt: the official 200,540,928-shot run.  37 qubits / 1406 Toffolis is
# well inside the kernel budget.  A timeout is a FAIL, never an anchor.
inv = run_verify(VER / 'invsqrt' / 'verify_submission_invsqrt.py', INV, [],
                 'invsqrt', timeout=10800)

# dqi: default 102,400 shots, default (empty) salt = the public draw.
dqi = run_verify(VER / 'dqi' / 'verify_submission_dqi.py', DQI, [],
                 'dqi', timeout=10800)

# dfthcsos: the verifier takes the directory holding angle_k_* + submission.npz.
chem_root = root / 'dfthcsos'
if not chem_root.is_dir():
    chem_root = Path('/kaggle/working') / 'dfthcsos_v151'
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
    'portfolio': 'v151_gpw_v22_chemistry',
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
    'source': {
        'release': 'goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25733',
        'public_lb': 33.25733,
        'note': 'the public frontier tree; its chemistry leg (npz 25ac10da + 5 '
                're-solved loaders, T 13112) is 38,000.59 cost units below our '
                'v150 chemistry (T 13114).',
    },
    'verdict': 'V151-RECEIPT-PASS' if ok and gm else 'V151-RECEIPT-FAIL',
}
Path('/kaggle/working/V151_RECEIPT.json').write_text(json.dumps(receipt, indent=1))
print('=== VERDICT', receipt['verdict'], '| GM', gm, '===', flush=True)
print(json.dumps(receipt['verifies'], indent=1), flush=True)
'''

META = {
    'id': 'badboyhalo1801/moat-lab',
    'title': 'moat-lab v151 — release receipt (goodpjw2008 33.25733 tree)',
    'code_file': 'notebook.ipynb',
    'language': 'python',
    'kernel_type': 'notebook',
    'is_private': True,
    'enable_gpu': False,
    'enable_tpu': False,
    'enable_internet': True,
    'keywords': [],
    'dataset_sources': [DATASET],
    'competition_sources': ['google-verifiable-quantum-circuit-compilation'],
    'kernel_sources': [],
}


def main() -> None:
    DST.mkdir(parents=True, exist_ok=True)
    # the two template placeholders MUST be substituted before the notebook is
    # written -- an unsubstituted `__SHA_LINES__` is a NameError at kernel
    # runtime (this exact failure killed moat-lab v65/v66).
    cell = CELL.replace('__SHA_LINES__', SHA_LINES).replace('__DATASET__', DATASET) \
                .replace('__ANCHOR__', ANCHOR)
    left = re.findall(r'__[A-Z][A-Z_]+__', cell)
    assert not left, f'unsubstituted placeholder(s) left in the moat-lab cell: {sorted(set(left))}'
    nb = {
        "cells": [
            {"cell_type": "code", "execution_count": None, "metadata": {},
             "outputs": [], "source": cell.splitlines(keepends=True)},
        ],
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python",
                           "name": "python3"},
            "language_info": {"name": "python", "version": "3.13.0"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }
    nb_path = DST / "notebook.ipynb"
    nb_path.write_text(json.dumps(nb, indent=1))
    (DST / "kernel-metadata.json").write_text(json.dumps(META, indent=1))
    # pre-push gate: every code cell must parse
    for i, c in enumerate(nb["cells"]):
        ast.parse("".join(c["source"]))
        print(f"cell {i} parses OK ({len(''.join(c['source']))} chars)")
    print(f"wrote {nb_path}")


if __name__ == "__main__":
    main()
