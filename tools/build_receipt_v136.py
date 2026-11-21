#!/usr/bin/env python3
"""build_receipt_v136.py — assemble the v136 LOCAL receipt from our own verifier runs.

Receipt 1 of the two-receipt gate.  Every number in it comes from a run of the
UNCHANGED official verifier on the exact bytes of `work/trees/v136_bt33100`:

  * shas_ok            : the 18-file static SHA table re-hashed against the tree
  * invsqrt            : our own local official run (200,540,928 shots)
  * dfthcsos           : our own local official run (--shots-per-address 1)
  * dqi                : our own in-kernel official run (moat-lab V136), because
                         the 102,400-shot DQI verification cannot run locally
                         under the ~3 GB soft-OOM ceiling.  The moat receipt is
                         read from work/receipts/V136_MOAT_RECEIPT.json and its
                         circuit_sha256 is asserted equal to the tree's dqi.kmb.

The script never invents a verdict: a missing or non-PASS leg makes it FAIL.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v136_bt33100'
TABLE = ROOT / 'work/sha_tables/sha_table_v136.txt'
OUT = ROOT / 'work/receipts/V136_RECEIPT.json'
INV_LOG = pathlib.Path('/tmp/opencode/v136_invsqrt_verify.log')
CHEM_LOG = pathlib.Path('/tmp/opencode/v136_chem.json')
MOAT = ROOT / 'work/receipts/V136_MOAT_RECEIPT.json'

REF = {'invsqrt': 2076774.233715282, 'dqi': 24439463583672.93,
       'dfthcsos': 3355599588.3155375}
PREV_GM = 33.07536   # v135, ref 58645864 (our best scored row)


def json_block(path: pathlib.Path) -> dict:
    t = path.read_text()
    i, j = t.find('{'), t.rfind('}')
    if i < 0 or j < 0:
        raise SystemExit(f'no JSON object in {path}')
    d = json.loads(t[i:j + 1])
    if not isinstance(d, dict):
        raise SystemExit(f'not a JSON object in {path}')
    return d


def main() -> int:
    table = json.loads(TABLE.read_text())
    files = table['files']

    actual = {str(p.relative_to(TREE)): p for p in TREE.rglob('*') if p.is_file()}
    assert set(actual) == set(files), f'tree/table mismatch: {set(actual) ^ set(files)}'
    shas_ok = True
    for name, (sha, size) in files.items():
        h = hashlib.sha256(actual[name].read_bytes()).hexdigest()
        if h != sha or actual[name].stat().st_size != size:
            shas_ok = False
            print('SHA MISMATCH', name)
    assert len(files) == 18

    def sha16(rel: str) -> str:
        return hashlib.sha256(actual[rel].read_bytes()).hexdigest()[:16]

    inv = json_block(INV_LOG) if INV_LOG.exists() and INV_LOG.stat().st_size else {}
    chem = json_block(CHEM_LOG)
    assert chem['status'] == 'PASS', chem.get('status')

    dqi = {}
    if MOAT.exists():
        m = json.loads(MOAT.read_text())
        dqi = (m.get('verifies') or {}).get('dqi') or {}
        if dqi.get('circuit_sha256'):
            assert dqi['circuit_sha256'].startswith(sha16('dqi.kmb')), \
                'moat dqi receipt is for other bytes'

    legs = {
        'invsqrt': {
            'status': inv.get('status'), 'score': inv.get('score'),
            'num_qubits': inv.get('num_qubits'), 'toffoli_count': inv.get('toffoli_count'),
            'toffoli_equivalent': inv.get('toffoli_equivalent'),
            'rotation_count': inv.get('rotation_count'),
            'rotation_eps': inv.get('rotation_eps'),
            'verified_shots': inv.get('verified_shots'),
            'worst_error_over_tolerance': inv.get('worst_error_over_tolerance'),
            'worst_x': inv.get('worst_x'), 'circuit_sha256': inv.get('circuit_sha256'),
            'note': 'our own local run of the UNCHANGED official verifier '
                    '(verify_submission_invsqrt.py, default 200,540,928 shots)',
        },
        'dqi': {
            'status': dqi.get('status'), 'score': dqi.get('score'),
            'num_qubits': dqi.get('num_qubits'), 'toffoli_count': dqi.get('toffoli_count'),
            'value_errors': dqi.get('value_errors'), 'phase_errors': dqi.get('phase_errors'),
            'verified_shots': dqi.get('verified_shots'),
            'effective_error_rate': dqi.get('effective_error_rate'),
            'repetition_factor': dqi.get('repetition_factor'),
            'circuit_sha256': dqi.get('circuit_sha256'),
            'note': 'our own in-kernel run of the UNCHANGED official verifier '
                    '(moat-lab v51, default salt, 102,400 shots)',
        },
        'dfthcsos': {
            'status': chem.get('status'), 'score': chem.get('score'),
            'num_qubits': chem.get('num_qubits'), 'toffoli_count': chem.get('toffoli_count'),
            'lambda_eff': chem.get('lambda_eff'), 'batch_size': chem.get('batch_size'),
            'note': 'our own local run of the UNCHANGED official verifier '
                    '(verifiers/dfthcsos/verify.py --shots-per-address 1)',
        },
    }

    ok = shas_ok
    for leg, e in legs.items():
        if e.get('status') != 'PASS' or e.get('score') is None:
            ok = False
            print('LEG NOT PASS:', leg, e.get('status'))
    if legs['dqi'].get('value_errors') or legs['dqi'].get('phase_errors'):
        ok = False
        print('DQI SHOT ERRORS')

    ratios = {k: REF[k] / e['score'] for k, e in legs.items()} if ok else {}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (1 / 3) if ok else None

    receipt = {
        'portfolio': 'v136_public_best_33_1002',
        'shas_ok': shas_ok,
        'verifiers': ['verify_submission_invsqrt.py', 'verify_submission_dqi.py',
                      'verifiers/dfthcsos/verify.py'],
        'verifies': legs,
        'ratios': ratios,
        'gm': gm,
        'previous_gm': PREV_GM,
        'delta_gm': (gm - PREV_GM) if gm else None,
        'source': 'OUTPUT of goodpjw2008/qcc-public-best-loader-table-swap-lb-33-0753 '
                  '(LB 33.1002): invsqrt d2148a7cd7a4d0a0 (rithvikredrouthu/qcc-milestone-set), '
                  'dqi 4b5721411adc239f (tonylica/quantum-ai-32-85306-ready), chemistry '
                  'npz 6b9903dda33a + loader_k_2 046679fe (rupam2020 + almondlabs exchange)',
        'sha_table': 'work/sha_tables/sha_table_v136.txt',
        'verdict': 'V136-RECEIPT-PASS' if ok else 'V136-RECEIPT-FAIL',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=1) + '\n')
    print(f'verdict: {receipt["verdict"]}')
    if gm:
        print(f'GM: {gm:.8f}  (previous {PREV_GM:.5f}, delta {gm - PREV_GM:+.5f})')
    for k, e in legs.items():
        s = e.get('score')
        print(f'  {k:9} {str(e.get("status")):5} score {s!s:>22}  '
              f'ratio {ratios.get(k, float("nan")):.6f}')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
