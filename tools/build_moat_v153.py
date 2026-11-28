#!/usr/bin/env python3
"""build_moat_v153.py — build the `badboyhalo1801/moat-lab` in-kernel gate for v153.

THE SECOND MECHANICAL RECEIPT (two-receipt gate, second half)
=============================================================
v153 is the PUBLIC FRONTIER tree of goodpjw2008's V33 notebook
(`qcc-shorter-chemistry-loaders-lb-33-29012`, public LB **33.29012**,
published 2026-11-27 23:35 UTC).  Its own in-kernel receipt (shipped inside
the kernel output as `receipt.json`) already ran the UNCHANGED official
verifiers and reports:

  invsqrt   b08370f271ba8f17  evgendvorkin's rewrite of maoxin123's 75e43352,
                              37 q, cost 60,769.42127769003   (PASS)
  dqi       b183c793b6b7c7a2  logiclab's V58 DQI, 900 q       (PASS)
  dfthcsos  npz f2b6cc37ce87b0d8 + 15 re-solved loaders
            249,043,677.36582175 (405 q, lambda_eff 46.912012523842144,
            T 13,108)                                        (PASS)

This kernel re-runs the same three official verifiers on the snapshot-dataset
bytes and writes V153_RECEIPT.json.  It is required because the campaign rule
is that no member enters a submission tree without an official in-kernel
receipt on the EXACT bytes we ship, and because the V33 tree is new bytes for
all three legs (new invsqrt, new chemistry npz, and 8 new loaders).

WHY THE TREE IS BETTER THAN v152 (measured, not claimed)
--------------------------------------------------------
  v152: invsqrt 60,927.54794503887 + dqi 305,031.4e6 + chem 249,131,640.8997796
  v153: invsqrt 60,769.42127769003 + dqi 305,031.4e6 + chem 249,043,677.36582175

  GM = (R_i/i * R_d/d * R_c/c)^(1/3) = 33.29012

which reproduces the release's measured public LB 33.29012 to 5 decimals --
an arithmetic cross-check that the board agrees with the adopted bytes.

The DQI is byte-identical to v152's b183c793, whose public board draw is
clean (zhuangbility v23 and evgendvorkin V81 both published it; the default
salt draw is a property of the .kmb's SHA-256 alone, so it does not change).

PUBLIC_DQI_EVIDENCE for these exact bytes (required when the default-salt
draw is not clean):
  * goodpjw2008 V33 (this tree)                     public LB 33.29012
  * zhuangbility/qcc-v23-our-refit-b183c793-...     public LB 33.25737
  * evgendvorkin V81 (same DQI bytes)               public LB 33.25229

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import re
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
DST = pathlib.Path('/tmp/opencode/kernel_moat_v153')
TABLE = json.loads((ROOT / 'work/sha_tables/sha_table_v153.txt').read_text())['files']
assert len(TABLE) == 18, f'expected 18 files, got {len(TABLE)}'

ANCHOR = 'qcc-release-v153'
DATASET = 'badboyhalo1801/qcc-release-v153'

SHA_LINES = ',\n'.join(f'    {k!r}: ({v[0]!r}, {v[1]})' for k, v in sorted(TABLE.items()))

CELL = '''# moat-lab — v153 RELEASE RECEIPT
#
# The gate's second receipt: run the UNCHANGED official verifiers in-kernel on
# the exact bytes of the snapshot dataset, and write V153_RECEIPT.json with a
# V153-RECEIPT-PASS verdict only if every leg passes.
#
# v153 = goodpjw2008's V33 public-frontier tree (LB 33.29012):
#   invsqrt  b08370f271ba8f17   (37 qubits) NEW BYTES -> full official run here
#   dqi      b183c793b6b7c7a2   (900 qubits) same bytes as v152 -> receipt re-run
#   chem     npz f2b6cc37ce87b0d8 + 15 re-solved loaders (T=13108, Q=405,
#            lambda_eff 46.912012523842144, cost 249,043,677.36582175)
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
    return None

paths = {}
for rel in SHA_TABLE:
    p = find_file(rel)
    if p is None:
        raise SystemExit(f'missing from the dataset: {rel}')
    paths[rel] = p
log('dataset files:', len(paths))

shas_ok = True
for rel, (sha, size) in SHA_TABLE.items():
    p = paths[rel]
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    if h != sha or p.stat().st_size != size:
        shas_ok = False
        log('SHA MISMATCH', rel, h[:16], 'want', sha[:16])
log('shas_ok =', shas_ok)
if not shas_ok:
    raise SystemExit('SHA GATE FAILED')

def extract_json(out: str) -> dict:
    """Return the LAST top-level JSON object in `out` that has a "status" key.

    The verifiers pretty-print their result dict, so a naive
    ``out.splitlines()[i:j]`` / character-slice parse is wrong (that exact bug
    produced a FAIL receipt on moat-lab v70 even though every leg printed a
    PASS).  Use the incremental decoder instead: scan every '{' and try to
    decode a complete object from there.
    """
    dec = json.JSONDecoder()
    best: dict = {}
    idx = 0
    while True:
        k = out.find('{', idx)
        if k < 0:
            break
        try:
            obj, end = dec.raw_decode(out[k:])
        except Exception:
            idx = k + 1
            continue
        if isinstance(obj, dict) and 'status' in obj:
            best = obj
            idx = k + end
        else:
            idx = k + 1
    return best


def run_verify(script, target, extra, label, timeout=7200):
    t = time.time()
    cmd = [sys.executable, str(script), str(target)] + list(extra)
    log('[%s] running %s' % (label, ' '.join(cmd)))
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             env=ENV, timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        log('[%s] TIMEOUT' % label)
        return {'status': 'TIMEOUT'}
    res = extract_json(out)
    if not res:
        # fall back: some verifiers prefix the JSON with a banner line
        for ln in reversed(out.splitlines()):
            s = ln.strip()
            if s.startswith('{') and s.endswith('}'):
                try:
                    p = json.loads(s)
                except Exception:
                    continue
                if isinstance(p, dict) and 'status' in p:
                    res = p
                    break
    log(f'[{label}] dt={time.time()-t:.0f}s status={res.get("status")} '
        f'score={res.get("score")}')
    if not res:
        log(f'[{label}] tail:', out[-500:].replace(chr(10), ' | '))
    res['_dt'] = round(time.time() - t, 1)
    res['_raw_tail'] = out[-700:]
    return res

INV = paths['invsqrt.kmb']
DQI = paths['dqi.kmb']

# invsqrt: the official 200,540,928-shot run.
inv = run_verify(VER / 'invsqrt' / 'verify_submission_invsqrt.py', INV, [],
                 'invsqrt', timeout=10800)

# dqi: default 102,400 shots, default (empty) salt = the public draw.
dqi = run_verify(VER / 'dqi' / 'verify_submission_dqi.py', DQI, [],
                 'dqi', timeout=10800)

# dfthcsos: the verifier takes the directory holding angle_k_* + submission.npz.
chem_root = root / 'dfthcsos'
if not chem_root.is_dir():
    chem_root = Path('/kaggle/working') / 'dfthcsos_v153'
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
# shot draw is NOT the default salt, so a non-zero default-salt count is a
# lottery draw, not a verdict.  A DQI leg with failed shots is therefore
# admissible ONLY when PUBLIC_DQI_EVIDENCE names the EXACT bytes we ship
# together with a public leaderboard score for them.  No evidence -> REJECT.
PUBLIC_DQI_EVIDENCE = [
    {'release': 'goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-29012 (V33)',
     'public_lb': 33.29012,
     'dqi_sha256': 'b183c793b6b7c7a2a246b7756958cbdad943abc3350dcf0ff61c8857bb441e3d',
     'note': 'the public-frontier tree that ships these exact DQI bytes; its '
             'own in-kernel receipt ran the unchanged official verifier '
             '(PASS, 1 value error on the default salt) and the tree scored '
             '33.29012 on the board'},
    {'release': 'zhuangbility/qcc-v23-our-refit-b183c793-lb-33-25737',
     'public_lb': 33.25737,
     'dqi_sha256': 'b183c793b6b7c7a2a246b7756958cbdad943abc3350dcf0ff61c8857bb441e3d',
     'note': 'the release that ships these exact DQI bytes together with '
             'invsqrt 6b592145 and the V23 chemistry table; its notebook '
             'states the board draw of b183c793 is clean and about 0.82M '
             'cheaper than 6f78ecdd, and the tree scored 33.25737'},
    {'release': 'evgendvorkin V81 (same circuits, public release)',
     'public_lb': 33.25229,
     'dqi_sha256': 'b183c793b6b7c7a2a246b7756958cbdad943abc3350dcf0ff61c8857bb441e3d',
     'note': 'an independent public submission of the same DQI bytes; the '
             'notebook quotes 33.25229 vs 33.25226 for the 6f78ecdd tree '
             'with the same circuits (~+3e-5 GM)'},
]
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
    'portfolio': 'v153_gpw_v33_frontier',
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
        'release': 'goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-29012',
        'public_lb': 33.29012,
        'note': 'the public frontier tree (V33, 2026-11-27 23:35 UTC): '
                'invsqrt b08370f2 (37 q, 60,769.4213), DQI b183c793, and '
                'chemistry npz f2b6cc37 with 15 re-solved loaders '
                '(T 13,108, lambda_eff 46.912012524, cost 249,043,677.37). '
                'Its shipped receipt.json reports the same three official '
                'verifier PASSes and GM 33.239187 on the DEFAULT salt; the '
                'board draw of b183c793 is the clean one (33.29012).',
    },
    'verdict': 'V153-RECEIPT-PASS' if ok and gm else 'V153-RECEIPT-FAIL',
}
Path('/kaggle/working/V153_RECEIPT.json').write_text(json.dumps(receipt, indent=1))
print('=== VERDICT', receipt['verdict'], '| GM', gm, '===', flush=True)
print(json.dumps(receipt['verifies'], indent=1), flush=True)
'''

META = {
    'id': 'badboyhalo1801/moat-lab',
    'title': 'moat-lab v153 — release receipt (goodpjw V33 frontier)',
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
