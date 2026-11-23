#!/usr/bin/env python3
"""Build the fail-closed two-receipt gate receipt for v141.

Requirements enforced here:
* the tree has exactly the 18 members in sha_table_v141.txt and every hash/size
  matches;
* moat-lab v55 ran the unchanged official invsqrt, DQI, and chemistry verifiers
  in-kernel on badboyhalo1801/qcc-release-v141 and all three PASSed;
* the in-kernel circuit hashes equal the pinned tree members;
* the DQI draw has zero value and phase errors;
* independent local official-verifier receipts reproduce the in-kernel
  inverse-sqrt and GoodpJW-chemistry results;
* the recomputed geometric mean agrees with the in-kernel GM.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v141_goodpjw_chem'
BASE = ROOT / 'work/trees/v140_apache_invsqrt'
TABLE = ROOT / 'work/sha_tables/sha_table_v141.txt'
OUT = ROOT / 'work/receipts/V141_RECEIPT.json'
MOAT = ROOT / 'work/receipts/V141_MOAT_RECEIPT.json'
INV_LOG = ROOT / 'work/receipts/V140_LOCAL_INVSQRT_VERIFY.log'
CHEM_LOG = ROOT / 'work/receipts/GOODPJW_V140_LOCAL_CHEM_VERIFY.log'
REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
EXPECTED = {
    'invsqrt': 60955.29842169718,
    'dqi': 305041647011.3978,
    'dfthcsos': 251692071.47549,
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


def sha_size(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    table = json.loads(TABLE.read_text())
    files = table['files']
    actual = {p.relative_to(TREE).as_posix(): p for p in TREE.rglob('*') if p.is_file()}
    if len(files) != 18:
        raise RuntimeError(f'expected 18 files, got {len(files)}')
    if set(actual) != set(files):
        raise RuntimeError(f'tree/table mismatch: {set(actual) ^ set(files)}')

    shas_ok = True
    for name, (want_sha, want_size) in files.items():
        got_sha, got_size = sha_size(actual[name])
        if got_sha != want_sha or got_size != want_size:
            shas_ok = False
            print('SHA/SIZE MISMATCH', name)
    if not shas_ok:
        raise RuntimeError('static 18-file SHA table mismatch')

    # The v141 invsqrt and DQI members are byte-exact v140 members, so the
    # independent v140 inverse-sqrt receipt applies.  The chemistry member is
    # new and therefore uses its own independent unchanged-verifier receipt.
    for name in files:
        if name == 'invsqrt.kmb' or name == 'dqi.kmb':
            if sha_size(actual[name]) != sha_size(BASE / name):
                raise RuntimeError(f'inherited local receipt is not applicable: {name}')
    if sha_size(actual['dfthcsos/submission.npz'])[0] != (
            'baa8b2966e889ef6be581c85e440ef856c025687c2ff2f1a0fa13033f7e35c84'):
        raise RuntimeError('v141 GoodpJW chemistry table SHA mismatch')

    moat = json.loads(MOAT.read_text())
    if moat.get('shas_ok') is not True:
        raise RuntimeError('in-kernel receipt did not pass the SHA gate')
    if moat.get('dataset') != 'badboyhalo1801/qcc-release-v141':
        raise RuntimeError(f'unexpected in-kernel dataset: {moat.get("dataset")!r}')
    if moat.get('verdict') != 'V141-RECEIPT-PASS':
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

    local_inv = json_block(INV_LOG)
    local_chem = json_block(CHEM_LOG)
    for label, local, kernel in (
        ('invsqrt', local_inv, verifies['invsqrt']),
        ('dfthcsos', local_chem, verifies['dfthcsos']),
    ):
        if local.get('status') != 'PASS':
            raise RuntimeError(f'local {label} status={local.get("status")!r}')
        if local.get('score') != kernel.get('score'):
            raise RuntimeError(
                f'local/in-kernel {label} score mismatch: '
                f'{local.get("score")!r} != {kernel.get("score")!r}')
        if local.get('circuit_sha256') and local.get('circuit_sha256') != kernel.get('circuit_sha256'):
            raise RuntimeError(f'local/in-kernel {label} SHA mismatch')
    for key in ('toffoli_count', 'num_qubits', 'batch_size'):
        if local_chem.get(key) != verifies['dfthcsos'].get(key):
            raise RuntimeError(
                f'local/in-kernel chemistry mismatch for {key}: '
                f'{local_chem.get(key)!r} != {verifies["dfthcsos"].get(key)!r}')
    if abs(float(local_chem.get('lambda_eff'))
           - float(verifies['dfthcsos'].get('lambda_eff'))) > 1e-12:
        raise RuntimeError('local/in-kernel chemistry lambda_eff mismatch')

    getcontext().prec = 50
    legs = {
        'invsqrt': {
            **verifies['invsqrt'],
            'note': 'official verifier PASS in moat-lab v55 on exact v141 snapshot bytes',
        },
        'dqi': {
            **verifies['dqi'],
            'note': 'official verifier PASS in moat-lab v55 on exact v141 snapshot bytes',
        },
        'dfthcsos': {
            **local_chem,
            'note': 'official verifier PASS in moat-lab v55 and independently reproduced locally',
        },
    }
    ratios = {k: REF[k] / Decimal(str(legs[k]['score'])) for k in legs}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (Decimal(1) / Decimal(3))
    previous = Decimal('33.138815515528333762029348587518900386419687678795')
    if abs(gm - Decimal(str(moat['gm']))) > Decimal('1e-12'):
        raise RuntimeError(f'GM mismatch: computed {gm}, in-kernel {moat["gm"]}')

    ok = (shas_ok and all(legs[k].get('status') == 'PASS' for k in legs)
          and verifies['dqi'].get('value_errors') == 0
          and verifies['dqi'].get('phase_errors') == 0)
    receipt = {
        'portfolio': 'v141_apache_invsqrt_goodpjw_chem',
        'shas_ok': shas_ok,
        'verifiers': [
            'verify_submission_invsqrt.py',
            'verify_submission_dqi.py',
            'verifiers/dfthcsos/verify.py',
        ],
        'verifies': legs,
        'official_in_kernel': {
            'kernel': 'badboyhalo1801/moat-lab',
            'version': 55,
            'dataset': 'badboyhalo1801/qcc-release-v141',
            'receipt': str(MOAT),
            'gm': float(moat['gm']),
            'verified_shots': {
                'invsqrt': verifies['invsqrt'].get('verified_shots'),
                'dqi': verifies['dqi'].get('verified_shots'),
                'dfthcsos': 1219,
            },
        },
        'local_invsqrt_receipt': str(INV_LOG),
        'local_chemistry_receipt': str(CHEM_LOG),
        'ratios': {k: str(v) for k, v in ratios.items()},
        'gm': str(gm),
        'previous_gm': str(previous),
        'delta_gm': str(gm - previous),
        'source': (
            'Apache public-circuits v170 invsqrt 52e8d4e6649b grafted onto '
            'GoodpJW 3,372-T loader chain and table baa8b2966e88, with '
            'v140 DQI bytes unchanged'
        ),
        'sha_table': 'work/sha_tables/sha_table_v141.txt',
        'verdict': 'V141-RECEIPT-PASS' if ok else 'V141-RECEIPT-FAIL',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'verdict: {receipt["verdict"]}')
    print(f'GM: {gm}  delta: {gm - previous:+}')
    for k, entry in legs.items():
        print(f'  {k:9} {entry["status"]:4} score {entry["score"]!s:>22} ratio {ratios[k]}')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
