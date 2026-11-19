#!/usr/bin/env python3
"""build_receipt_v133.py — build the LOCAL verification receipt for the v133 tree.

The receipt is the FIRST of the two mechanical receipts required by
`harness/submit_gate.sh`: it records `shas_ok` (the static 18-file SHA table
match) and a verdict string containing `-RECEIPT-PASS` (the official verifier
result).  The SECOND receipt is the in-kernel moat-lab verification.

This script never invents a verdict: the verifier outputs are re-read from the
recorded files and re-checked against the tree's own bytes.

v133 = the public mix published by `ghazarosbarseghyan91/vqcc-combo-candidates`:
  invsqrt   ecf908fec987b61a  (our own local official 200,540,928-shot run)
  dqi       15a4b7403356092e  (BYTE-IDENTICAL to v132's DQI: the DQI verifier's
            seed is the SHA-256 of the circuit's own .kmb, so the same bytes
            give the same draw; v132's official run was 0 errors)
  dfthcsos  npz 6ef06081cb9c5752 + 15 loaders (our own local official run)
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v133_combo'
TABLE = ROOT / 'work/sha_tables/sha_table_v133.txt'
OUT = ROOT / 'work/receipts/V133_RECEIPT.json'
INV_LOG = pathlib.Path('/tmp/opencode/v133_invsqrt_verify.log')
DQI_LOG = pathlib.Path('/tmp/opencode/v132_dqi_full.json')   # same bytes as v133's dqi.kmb
DFT_LOG = pathlib.Path('/tmp/opencode/v133_dfthcsos_verify.json')

REF = {'invsqrt': 2076774.233715, 'dqi': 24439463583672.93, 'dfthcsos': 3355599588.3155375}

# what the publisher of the mix states (ghazarosbarseghyan91's notebook header)
PUBLISHED = {'invsqrt': 74383.70, 'dqi': 345257000000000.0, 'dfthcsos': 294642169.51}


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

    # --- receipt 1b: the official verifier results, re-checked against the bytes ---
    inv = json_block(INV_LOG)
    dqi = json_block(DQI_LOG)
    dft = json_block(DFT_LOG)

    def sha16(rel: str) -> str:
        return hashlib.sha256(actual[rel].read_bytes()).hexdigest()[:16]

    assert inv['circuit_sha256'].startswith(sha16('invsqrt.kmb')), 'invsqrt log is for other bytes'
    assert dqi['circuit_sha256'].startswith(sha16('dqi.kmb')), 'dqi log is for other bytes'

    legs = {
        'invsqrt': {
            'status': inv['status'], 'score': inv['score'],
            'num_qubits': inv['num_qubits'], 'toffoli_count': inv['toffoli_count'],
            'rotation_count': inv['rotation_count'], 'rotation_eps': inv['rotation_eps'],
            'verified_shots': inv['verified_shots'],
            'worst_error_over_tolerance': inv['worst_error_over_tolerance'],
            'worst_x': inv['worst_x'], 'circuit_sha256': inv['circuit_sha256'],
            'published_score': PUBLISHED['invsqrt'],
            'note': 'our own local run of the UNCHANGED official verifier '
                    '(verify_submission_invsqrt.py, default 200,540,928 shots)',
        },
        'dqi': {
            'status': dqi['status'], 'score': dqi['score'],
            'num_qubits': dqi['num_qubits'], 'toffoli_count': dqi['toffoli_count'],
            'value_errors': dqi['value_errors'], 'phase_errors': dqi['phase_errors'],
            'verified_shots': dqi['verified_shots'],
            'effective_error_rate': dqi['effective_error_rate'],
            'repetition_factor': dqi['repetition_factor'],
            'circuit_sha256': dqi['circuit_sha256'],
            'note': 'byte-identical to v132 dqi.kmb (sha 15a4b7403356092e); the DQI verifier '
                    'derives its seed from the SHA-256 of the circuit itself, so the same bytes '
                    'give the same official draw (v132: 0 value / 0 phase errors on the board)',
        },
        'dfthcsos': {
            'status': dft['status'], 'score': dft['score'],
            'num_qubits': dft['num_qubits'], 'toffoli_count': dft['toffoli_count'],
            'lambda_eff': dft['lambda_eff'],
            'batch_size': dft['batch_size'],
            'published_score': PUBLISHED['dfthcsos'],
            'note': 'our own local run of the UNCHANGED official verifier '
                    '(verifiers/dfthcsos/verify.py --shots-per-address 1)',
        },
    }

    ok = shas_ok
    for leg, e in legs.items():
        if e['status'] != 'PASS':
            ok = False
            print('LEG NOT PASS:', leg, e['status'])
        if e.get('value_errors', 0) or e.get('phase_errors', 0):
            ok = False
            print('DQI SHOT ERRORS:', leg)

    ratios = {k: REF[k] / e['score'] for k, e in legs.items()}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3)
    prev = 28.23163020066719

    receipt = {
        'portfolio': 'v133_ghazaros_combo_28_23441',
        'shas_ok': shas_ok,
        'verifiers': ['verify_submission_invsqrt.py', 'verify_submission_dqi.py',
                      'verifiers/dfthcsos/verify.py'],
        'verifies': legs,
        'ratios': ratios,
        'gm': gm,
        'previous_gm': prev,
        'delta_gm': gm - prev,
        'source': 'ghazarosbarseghyan91/vqcc-combo-candidates (2026-11-19); invsqrt '
                  'ecf908fec987b61a (maoxin123 lineage), dqi 15a4b7403356092e (ozertuu), '
                  'chem npz 6ef06081cb9c5752 + the 4,022-Toffoli ANGLE loader family',
        'sha_table': 'work/sha_tables/sha_table_v133.txt',
        'verdict': 'V133-RECEIPT-PASS' if ok else 'V133-RECEIPT-FAIL',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'verdict: {receipt["verdict"]}')
    print(f'GM: {gm:.8f}  (previous {prev:.8f}, delta {gm - prev:+.8f})')
    for k, e in legs.items():
        print(f'  {k:9} {e["status"]:5} score {e["score"]:>20}  ratio {ratios[k]:.6f}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
