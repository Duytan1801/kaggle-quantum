#!/usr/bin/env python3
"""Build the v137 two-receipt-gate receipt.

The candidate is the public OUTPUT of boristown/vqcc-33-102-lb-dag-splicing-visual-guide.
Its chemistry bytes are independently re-verified locally with the unchanged
competition verifier; the unchanged invsqrt and DQI bytes inherit the v136
in-kernel PASS receipts only after exact SHA-256 checks.  The source kernel's
own receipt is retained as evidence for the chemistry leg.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v137_bt33102'
TABLE = ROOT / 'work/sha_tables/sha_table_v137.txt'
OUT = ROOT / 'work/receipts/V137_RECEIPT.json'
CHEM_LOG = pathlib.Path('/tmp/opencode/v137_chem_verify.log')
SOURCE = ROOT / 'work/receipts/BORISTOWN_V137_KERNEL_RECEIPT.json'
PRIOR = ROOT / 'work/receipts/V136_MOAT_RECEIPT.json'
REF = {'invsqrt': 2076774.233715282, 'dqi': 24439463583672.93,
       'dfthcsos': 3355599588.3155375}


def json_block(path: pathlib.Path) -> dict:
    text = path.read_text()
    i, j = text.find('{'), text.rfind('}')
    if i < 0 or j < 0:
        raise RuntimeError(f'no JSON object in {path}')
    obj = json.loads(text[i:j + 1])
    if not isinstance(obj, dict):
        raise RuntimeError(f'not a JSON object in {path}')
    return obj


def main() -> int:
    table = json.loads(TABLE.read_text())
    files = table['files']
    actual = {str(p.relative_to(TREE)): p for p in TREE.rglob('*') if p.is_file()}
    if set(actual) != set(files):
        raise RuntimeError(f'tree/table mismatch: {set(actual) ^ set(files)}')
    if len(files) != 18:
        raise RuntimeError(f'expected 18 files, got {len(files)}')

    shas_ok = True
    for name, (want_sha, want_size) in files.items():
        got = hashlib.sha256(actual[name].read_bytes()).hexdigest()
        if got != want_sha or actual[name].stat().st_size != want_size:
            shas_ok = False
            print('SHA MISMATCH', name)

    chem = json_block(CHEM_LOG)
    source = json.loads(SOURCE.read_text())
    prior = json.loads(PRIOR.read_text())
    source_members = source.get('members_sha256') or {}
    if source_members != {k: v[0] for k, v in files.items()}:
        raise RuntimeError('source kernel receipt member SHA table differs from v137 tree')
    source_chem = source.get('dfthcsos_live_2salt') or {}
    for salt, entry in source_chem.items():
        if entry.get('status') != 'PASS' or entry.get('score') is None:
            raise RuntimeError(f'source chemistry receipt not PASS for {salt}')

    inv = (prior.get('verifies') or {}).get('invsqrt') or {}
    dqi = (prior.get('verifies') or {}).get('dqi') or {}
    if inv.get('circuit_sha256') != files['invsqrt.kmb'][0]:
        raise RuntimeError('prior invsqrt receipt is for different bytes')
    if dqi.get('circuit_sha256') != files['dqi.kmb'][0]:
        raise RuntimeError('prior DQI receipt is for different bytes')
    if inv.get('status') != 'PASS' or dqi.get('status') != 'PASS':
        raise RuntimeError('prior in-kernel receipt lacks PASS for unchanged legs')
    if dqi.get('value_errors') not in (0, None) or dqi.get('phase_errors') not in (0, None):
        raise RuntimeError('prior DQI receipt contains shot errors')

    if chem.get('status') != 'PASS':
        raise RuntimeError(f'local chemistry verifier status={chem.get("status")}')
    if abs(float(chem['score']) - float(source_chem['default']['score'])) > 1e-6:
        raise RuntimeError('local chemistry score differs from source kernel receipt')

    legs = {
        'invsqrt': {**inv, 'note': 'exact v136 bytes; inherited PASS from our in-kernel V136 receipt'},
        'dqi': {**dqi, 'note': 'exact v136 bytes; inherited PASS from our in-kernel V136 receipt'},
        'dfthcsos': {
            **{k: chem.get(k) for k in (
                'status', 'score', 'num_qubits', 'toffoli_count', 'lambda_eff',
                'batch_size', 'verified_shots', 'submission_sha256')},
            'note': 'our own local run of the unchanged official dfthcsos verifier',
        },
    }
    ratios = {k: REF[k] / float(legs[k]['score']) for k in legs}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3)
    source_gm = float(source.get('default_salt_gm'))
    if abs(gm - source_gm) > 1e-8:
        raise RuntimeError(f'GM mismatch: computed {gm}, source {source_gm}')

    ok = shas_ok and all(legs[k].get('status') == 'PASS' for k in legs)
    receipt = {
        'portfolio': 'v137_public_boristown_33_10189',
        'shas_ok': shas_ok,
        'verifiers': ['verify_submission_invsqrt.py', 'verify_submission_dqi.py',
                      'verifiers/dfthcsos/verify.py'],
        'verifies': legs,
        'official_in_kernel': {
            'kernel': 'boristown/vqcc-33-102-lb-dag-splicing-visual-guide',
            'receipt': str(SOURCE),
            'chemistry': source_chem,
            'default_salt_gm': source_gm,
        },
        'ratios': ratios,
        'gm': gm,
        'previous_gm': 33.100220972901965,
        'delta_gm': gm - 33.100220972901965,
        'source': 'kernel output; v136 invsqrt/DQI bytes plus boristown chemistry k6/npz',
        'sha_table': 'work/sha_tables/sha_table_v137.txt',
        'verdict': 'V137-RECEIPT-PASS' if ok else 'V137-RECEIPT-FAIL',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'verdict: {receipt["verdict"]}')
    print(f'GM: {gm:.12f}  delta: {receipt["delta_gm"]:+.12f}')
    for k, e in legs.items():
        print(f'  {k:9} {e["status"]:4} score {e["score"]!s:>22} ratio {ratios[k]:.9f}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
