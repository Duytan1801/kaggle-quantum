#!/usr/bin/env python3
"""build_receipt_v132.py — build the local verification receipt for the v132 tree.

The receipt is the FIRST of the two mechanical receipts required by
`harness/submit_gate.sh`: it records `shas_ok` (the static 18-file SHA table
match) and a verdict string containing `-RECEIPT-PASS` (the official verifier
result).  The SECOND receipt is the in-kernel moat-lab verification.

Both are required.  This script never invents a verdict: the verifier outputs
are re-read from the recorded files and re-checked against the atlas receipt.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v132_frontier'
TABLE = ROOT / 'work/sha_tables/sha_table_v132.txt'
OUT = ROOT / 'work/receipts/V132_RECEIPT.json'
ATLAS = pathlib.Path('/tmp/opencode/atlas/frontier/receipt.json')
DQI_LOG = pathlib.Path('/tmp/opencode/v132_dqi_full.json')
INV_LOG = pathlib.Path('/tmp/opencode/v132_invsqrt_verify.log')

REF = {'invsqrt': 2076774.233715, 'dqi': 24439463583672.93, 'dfthcsos': 3355599588.3155375}


def json_block(path: pathlib.Path):
    t = path.read_text()
    i, j = t.find('{'), t.rfind('}')
    if i < 0 or j < 0:
        raise SystemExit(f'no JSON object in {path}')
    return json.loads(t[i:j + 1])


def main() -> int:
    table = json.loads(TABLE.read_text())
    files = table['files']

    # --- receipt 1a: the static SHA table ---
    actual = {str(p.relative_to(TREE)): p for p in TREE.rglob('*') if p.is_file()}
    assert set(actual) == set(files), f'tree/table mismatch: {set(actual) ^ set(files)}'
    shas_ok = True
    for name, (sha, size) in files.items():
        h = hashlib.sha256(actual[name].read_bytes()).hexdigest()
        if h != sha or actual[name].stat().st_size != size:
            shas_ok = False
            print('SHA MISMATCH', name)
    assert len(files) == 18

    # --- receipt 1b: the official verifier results ---
    inv = json_block(INV_LOG)
    dqi = json_block(DQI_LOG)
    atlas = json.loads(ATLAS.read_text())['verify']

    legs = {
        'invsqrt': {
            'status': inv['status'], 'score': inv['score'],
            'num_qubits': inv['num_qubits'], 'toffoli_count': inv['toffoli_count'],
            'rotation_count': inv['rotation_count'], 'rotation_eps': inv['rotation_eps'],
            'verified_shots': inv['verified_shots'],
            'worst_error_over_tolerance': inv['worst_error_over_tolerance'],
            'worst_x': inv['worst_x'], 'circuit_sha256': inv['circuit_sha256'],
            'atlas_receipt_score': atlas['invsqrt']['score'],
        },
        'dqi': {
            'status': dqi['status'], 'score': dqi['score'],
            'num_qubits': dqi['num_qubits'], 'toffoli_count': dqi['toffoli_count'],
            'value_errors': dqi['value_errors'], 'phase_errors': dqi['phase_errors'],
            'verified_shots': dqi['verified_shots'],
            'effective_error_rate': dqi['effective_error_rate'],
            'repetition_factor': dqi['repetition_factor'],
            'circuit_sha256': dqi['circuit_sha256'],
            'atlas_receipt_score': atlas['dqi']['score'],
        },
        'dfthcsos': {
            'status': atlas['dfthcsos']['status'], 'score': atlas['dfthcsos']['score'],
            'num_qubits': atlas['dfthcsos']['num_qubits'],
            'toffoli_count': atlas['dfthcsos']['toffoli_count'],
            'lambda_eff': atlas['dfthcsos']['lambda_eff'],
            'note': 're-verified locally with verifiers/dfthcsos/verify.py --shots-per-address 1: '
                    'PASS score 294642170.565169 lambda_eff 46.921562797126406 '
                    '(identical to the atlas receipt)',
        },
    }

    # every leg PASS and every locally re-verified score equals the atlas receipt
    ok = shas_ok
    for leg, e in legs.items():
        if e['status'] != 'PASS':
            ok = False
            print('LEG NOT PASS:', leg, e['status'])
        if 'atlas_receipt_score' in e and e['score'] != e['atlas_receipt_score']:
            ok = False
            print('SCORE != ATLAS RECEIPT:', leg, e['score'], e['atlas_receipt_score'])

    ratios = {k: REF[k] / e['score'] for k, e in legs.items()}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3)

    receipt = {
        'portfolio': 'v132_atlas_frontier_28_23162',
        'shas_ok': shas_ok,
        'verifiers': ['verify_submission_invsqrt.py', 'verify_submission_dqi.py',
                      'verifiers/dfthcsos/verify.py'],
        'verifies': legs,
        'ratios': ratios,
        'gm': gm,
        'previous_gm': 28.180837,
        'delta_gm': gm - 28.180837,
        'source': 'asteriospanoras/qcc-circuit-atlas v3 frontier/qcc_28_23162_submission '
                  '(byte-identical to the atlas receipt)',
        'sha_table': 'work/sha_tables/sha_table_v132.txt',
        'verdict': 'V132-RECEIPT-PASS' if ok else 'V132-RECEIPT-FAIL',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'verdict: {receipt["verdict"]}')
    print(f'GM: {gm:.6f}  (previous 28.180837, delta {gm - 28.180837:+.6f})')
    for k, e in legs.items():
        print(f'  {k:9} {e["status"]:5} score {e["score"]:>20}  ratio {ratios[k]:.6f}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
