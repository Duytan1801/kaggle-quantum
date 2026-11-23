#!/usr/bin/env python3
"""Build the fail-closed v139 two-receipt-gate receipt.

v139 is Leo Tang's public ``leotang09/vqcc-t7421-submission`` output.  The
private snapshot dataset contains the exact 18 bytes pinned by
``work/sha_tables/sha_table_v139.txt``.  moat-lab version 53 ran the
UNCHANGED official invsqrt, DQI, and chemistry verifiers in-kernel on those
bytes; the chemistry leg was also reproduced locally with the unchanged
official verifier.

The receipt is not a claim based on a title or an advertised score.  It is
emitted only after all of the following agree:

* the tree contains exactly the 18 table members and every SHA-256/size matches;
* every official verifier leg in the in-kernel receipt is PASS;
* the in-kernel invsqrt and DQI circuit hashes match the pinned members;
* the DQI draw has zero value and phase errors;
* the local and in-kernel chemistry scores agree exactly; and
* the recomputed geometric mean agrees with the in-kernel GM.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v139_leotang_t7421'
TABLE = ROOT / 'work/sha_tables/sha_table_v139.txt'
OUT = ROOT / 'work/receipts/V139_RECEIPT.json'
MOAT = ROOT / 'work/receipts/V139_MOAT_RECEIPT.json'
CHEM_LOG = ROOT / 'work/receipts/V139_LOCAL_CHEM_VERIFY.log'
REF = {
    'invsqrt': 2076774.233715282,
    'dqi': 24439463583672.93,
    'dfthcsos': 3355599588.3155375,
}
EXPECTED = {
    'invsqrt': 60955.32670759028,
    'dqi': 305041647011.3978,
    'dfthcsos': 251692077.714951,
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
    if len(files) != 18:
        raise RuntimeError(f'expected 18 files, got {len(files)}')
    if set(actual) != set(files):
        raise RuntimeError(f'tree/table mismatch: {set(actual) ^ set(files)}')

    shas_ok = True
    for name, (want_sha, want_size) in files.items():
        got = hashlib.sha256(actual[name].read_bytes()).hexdigest()
        if got != want_sha or actual[name].stat().st_size != want_size:
            shas_ok = False
            print('SHA/SIZE MISMATCH', name)
    if not shas_ok:
        raise RuntimeError('static 18-file SHA table mismatch')

    moat = json.loads(MOAT.read_text())
    if moat.get('shas_ok') is not True:
        raise RuntimeError('in-kernel receipt did not pass the SHA gate')
    if moat.get('dataset') != 'badboyhalo1801/qcc-release-v139':
        raise RuntimeError(f'unexpected in-kernel dataset: {moat.get("dataset")!r}')
    if moat.get('verdict') != 'V139-RECEIPT-PASS':
        raise RuntimeError(f'in-kernel verdict is not PASS: {moat.get("verdict")!r}')

    verifies = moat.get('verifies') or {}
    for leg in ('invsqrt', 'dqi', 'dfthcsos'):
        entry = verifies.get(leg) or {}
        if entry.get('status') != 'PASS':
            raise RuntimeError(f'official in-kernel verifier did not PASS: {leg}')
        if entry.get('score') != EXPECTED[leg]:
            raise RuntimeError(
                f'unexpected {leg} score: {entry.get("score")!r} != {EXPECTED[leg]!r}')
    if verifies['invsqrt'].get('circuit_sha256') != files['invsqrt.kmb'][0]:
        raise RuntimeError('in-kernel invsqrt receipt is for different bytes')
    if verifies['dqi'].get('circuit_sha256') != files['dqi.kmb'][0]:
        raise RuntimeError('in-kernel DQI receipt is for different bytes')
    if verifies['dqi'].get('value_errors') != 0 or verifies['dqi'].get('phase_errors') != 0:
        raise RuntimeError('in-kernel DQI receipt contains shot errors')

    local_chem = json_block(CHEM_LOG)
    in_kernel_chem = verifies['dfthcsos']
    if local_chem.get('status') != 'PASS':
        raise RuntimeError(f'local chemistry status={local_chem.get("status")!r}')
    for key in ('score', 'toffoli_count', 'num_qubits', 'batch_size'):
        if local_chem.get(key) != in_kernel_chem.get(key):
            raise RuntimeError(
                f'local/in-kernel chemistry mismatch for {key}: '
                f'{local_chem.get(key)!r} != {in_kernel_chem.get(key)!r}')
    # The two runs differ only in serialization of the last few ULPs.
    if abs(float(local_chem.get('lambda_eff'))
           - float(in_kernel_chem.get('lambda_eff'))) > 1e-12:
        raise RuntimeError('local/in-kernel chemistry lambda_eff mismatch')

    legs = {
        'invsqrt': {
            **verifies['invsqrt'],
            'note': 'official verifier PASS in moat-lab v53 on exact v139 snapshot bytes',
        },
        'dqi': {
            **verifies['dqi'],
            'note': 'official verifier PASS in moat-lab v53 on exact v139 snapshot bytes',
        },
        'dfthcsos': {
            **local_chem,
            'note': 'official verifier PASS in moat-lab v53 and independently reproduced locally',
        },
    }
    ratios = {k: REF[k] / float(legs[k]['score']) for k in legs}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3)
    if abs(gm - float(moat['gm'])) > 1e-12:
        raise RuntimeError(f'GM mismatch: computed {gm}, in-kernel {moat["gm"]}')

    ok = (shas_ok and all(legs[k].get('status') == 'PASS' for k in legs)
          and verifies['dqi'].get('value_errors') == 0
          and verifies['dqi'].get('phase_errors') == 0)
    receipt = {
        'portfolio': 'v139_public_leotang_t7421_33_13881',
        'shas_ok': shas_ok,
        'verifiers': [
            'verify_submission_invsqrt.py',
            'verify_submission_dqi.py',
            'verifiers/dfthcsos/verify.py',
        ],
        'verifies': legs,
        'official_in_kernel': {
            'kernel': 'badboyhalo1801/moat-lab',
            'version': 53,
            'dataset': 'badboyhalo1801/qcc-release-v139',
            'receipt': str(MOAT),
            'gm': float(moat['gm']),
            'verified_shots': {
                'invsqrt': verifies['invsqrt'].get('verified_shots'),
                'dqi': verifies['dqi'].get('verified_shots'),
                'dfthcsos': 1219,
            },
        },
        'local_chemistry_receipt': str(CHEM_LOG),
        'ratios': ratios,
        'gm': gm,
        'previous_gm': 33.10190185550799,
        'delta_gm': gm - 33.10190185550799,
        'source': 'leotang09/vqcc-t7421-submission public output',
        'sha_table': 'work/sha_tables/sha_table_v139.txt',
        'verdict': 'V139-RECEIPT-PASS' if ok else 'V139-RECEIPT-FAIL',
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
