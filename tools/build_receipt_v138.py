#!/usr/bin/env python3
"""Build the v138 two-receipt-gate receipt.

The candidate is the public OUTPUT of
``goodpjw2008/qcc-dead-word-loader-chain-dp-lb-33-10186``.  Its Kaggle kernel
ran the unchanged official verifiers on all three tasks.  We independently
re-run the unchanged official chemistry verifier locally on the exact tree
bytes and require both results to agree exactly.

The receipt is deliberately fail-closed: every static member hash, every
official PASS leg, the unchanged-leg circuit hashes, and the computed GM must
match before ``V138-RECEIPT-PASS`` can be emitted.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v138_goodpjw'
TABLE = ROOT / 'work/sha_tables/sha_table_v138.txt'
OUT = ROOT / 'work/receipts/V138_RECEIPT.json'
CHEM_LOG = ROOT / 'work/receipts/V138_LOCAL_CHEM_VERIFY.log'
SOURCE = ROOT / 'work/receipts/GOODPJW_V138_KERNEL_RECEIPT.json'
REF = {
    'invsqrt': 2076774.233715282,
    'dqi': 24439463583672.93,
    'dfthcsos': 3355599588.3155375,
}


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

    source = json.loads(SOURCE.read_text())
    source_members = source.get('members') or {}
    if source_members != {k: v[0] for k, v in files.items()}:
        raise RuntimeError('source kernel receipt member SHA table differs from v138 tree')

    verify = source.get('verify') or {}
    for leg in ('invsqrt', 'dqi', 'dfthcsos'):
        if (verify.get(leg) or {}).get('status') != 'PASS':
            raise RuntimeError(f'source in-kernel official verifier did not PASS: {leg}')
    if verify['invsqrt'].get('circuit_sha256') != files['invsqrt.kmb'][0]:
        raise RuntimeError('source invsqrt receipt is for different bytes')
    if verify['dqi'].get('circuit_sha256') != files['dqi.kmb'][0]:
        raise RuntimeError('source DQI receipt is for different bytes')
    if verify['dqi'].get('value_errors') != 0 or verify['dqi'].get('phase_errors') != 0:
        raise RuntimeError('source DQI receipt contains shot errors')

    local_chem = json_block(CHEM_LOG)
    source_chem = verify['dfthcsos']
    if local_chem.get('status') != 'PASS':
        raise RuntimeError(f'local chemistry verifier status={local_chem.get("status")}')
    for key in ('score', 'lambda_eff', 'toffoli_count', 'num_qubits', 'submission_sha256'):
        if local_chem.get(key) != source_chem.get(key):
            raise RuntimeError(
                f'local/source chemistry mismatch for {key}: '
                f'{local_chem.get(key)!r} != {source_chem.get(key)!r}'
            )

    legs = {
        'invsqrt': {
            **verify['invsqrt'],
            'note': 'official verifier PASS in the source Kaggle kernel; exact source bytes',
        },
        'dqi': {
            **verify['dqi'],
            'note': 'official verifier PASS in the source Kaggle kernel; exact source bytes',
        },
        'dfthcsos': {
            **local_chem,
            'note': 'our own local run of the unchanged official chemistry verifier; '
                    'exact score agrees with source in-kernel PASS',
        },
    }
    ratios = {k: REF[k] / float(legs[k]['score']) for k in legs}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3)
    source_gm = float(source['gm'])
    if abs(gm - source_gm) > 1e-10:
        raise RuntimeError(f'GM mismatch: computed {gm}, source {source_gm}')

    ok = shas_ok and all(legs[k].get('status') == 'PASS' for k in legs)
    receipt = {
        'portfolio': 'v138_public_goodpjw_dead_word_loader_chain_dp',
        'shas_ok': shas_ok,
        'verifiers': [
            'verify_submission_invsqrt.py',
            'verify_submission_dqi.py',
            'verifiers/dfthcsos/verify.py',
        ],
        'verifies': legs,
        'official_in_kernel': {
            'kernel': 'goodpjw2008/qcc-dead-word-loader-chain-dp-lb-33-10186',
            'receipt': str(SOURCE),
            'gm': source_gm,
            'verified_shots': {
                'invsqrt': verify['invsqrt'].get('verified_shots'),
                'dqi': verify['dqi'].get('verified_shots'),
                'dfthcsos': verify['dfthcsos'].get('verified_shots'),
            },
        },
        'ratios': ratios,
        'gm': gm,
        'previous_gm': 33.10189299494091,
        'delta_gm': gm - 33.10189299494091,
        'source': 'kernel output; v137 loader chain plus ozertuu table fc4b4c01',
        'sha_table': 'work/sha_tables/sha_table_v138.txt',
        'verdict': 'V138-RECEIPT-PASS' if ok else 'V138-RECEIPT-FAIL',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'verdict: {receipt["verdict"]}')
    print(f'GM: {gm:.14f}  delta: {receipt["delta_gm"]:+.14f}')
    for k, entry in legs.items():
        print(f'  {k:9} {entry["status"]:4} score {entry["score"]!s:>22} ratio {ratios[k]:.9f}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
