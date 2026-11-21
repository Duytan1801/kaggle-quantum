#!/usr/bin/env python3
"""build_snapshot_v135.py — stage the `badboyhalo1801/qcc-release-v135` snapshot dataset.

v135 = the public-best tree published as the OUTPUT of
`goodpjw2008/qcc-public-best-loader-table-swap-lb-33-0753` (LB 33.0753), whose
own receipt.json is a full official-verifier run at the default salt.

  invsqrt   d2148a7cd7a4d0a0  60,955.32670759028   (37 qubits, 1406.31 Toffolis)
  dqi       4b5721411adc239f  305,041,647,011.3978 (0 value / 0 phase errors)
  dfthcsos  npz 6b9903dda33a + loader_k_2 046679fe exchanged in
            253,143,456.48793402 (405 q, T 13,322, lambda_eff 46.918298421794454)

The 18-file SHA table (work/sha_tables/sha_table_v135.txt) is the authority; this
script verifies every file against it BEFORE staging anything.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v135_pub33075'
TABLE = ROOT / 'work/sha_tables/sha_table_v135.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v135')

CREDITS = """# v135 — QCC release snapshot (public best 33.0753)

Adopted 2026-11-21 from the public-release queue. The exact 18 bytes are the
output of `goodpjw2008/qcc-public-best-loader-table-swap-lb-33-0753`, which the
public leaderboard scored 33.0753 (the best public tree at adoption time).

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `d2148a7cd7a4d0a0` (37 q, 33 rotations) | `rithvikredrouthu/qcc-milestone-set` | 60,955.32670759028 (200,540,928 shots, PASS) |
| dqi | `4b5721411adc239f` (900 q) | `tonylica/quantum-ai-32-85306-ready` kernel output | 305,041,647,011.3978 (102,400 shots, 0 value / 0 phase errors) |
| dfthcsos | npz `6b9903dda33a` + 15 ANGLE loaders, loader_k_2 `046679fe` | table from `almondlabs/almond-labs-qcc-31-70105` output, loader_k_2 from `rupam2020/qcc-no-bodies-milestone`; rest `rithvikredrouthu/qcc-milestone-set` | 253,143,456.48793402 (PASS, lambda_eff 46.918298421794454, T 13,322, Q 405) |

GM 33.07535601389506 (published receipt), reproduced by our own local chemistry
verifier to the last digit; invsqrt and DQI receipts come from our own runs of
the UNCHANGED official verifiers on these exact bytes.

Licence: Apache-2.0 for the public notebooks / datasets credited above.
"""

META = {
    'title': 'QCC release v135 (public best 33.0753 snapshot)',
    'id': 'badboyhalo1801/qcc-release-v135',
    'subtitle': 'Public-best 33.0753 18-file tree, sha-pinned for in-kernel verification',
    'description': CREDITS,
    'licenses': [{'name': 'Apache 2.0'}],
}


def main() -> int:
    table = json.loads(TABLE.read_text())
    files = table['files']
    assert len(files) == 18, f'expected 18 files, got {len(files)}'

    actual = {str(p.relative_to(TREE)): p for p in TREE.rglob('*') if p.is_file()}
    assert set(actual) == set(files), f'tree/table mismatch: {set(actual) ^ set(files)}'
    for name, (sha, size) in files.items():
        h = hashlib.sha256(actual[name].read_bytes()).hexdigest()
        assert h == sha, f'{name}: {h} != {sha}'
        assert actual[name].stat().st_size == size, f'{name}: size mismatch'
    print(f'OK: {len(files)} files verified against {TABLE.name}')

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    for name, (sha, size) in files.items():
        dst = STAGE / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(actual[name], dst)

    manifest = {
        'portfolio': 'v135_public_best_33_0753',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': 'output of goodpjw2008/qcc-public-best-loader-table-swap-lb-33-0753 '
                  '(LB 33.0753): invsqrt d2148a7c (rithvikredrouthu/qcc-milestone-set), '
                  'dqi 4b572141 (tonylica/quantum-ai-32-85306-ready), chemistry '
                  'npz 6b9903dd + loader_k_2 046679fe exchange (rupam2020 / almondlabs)',
        'licence': 'Apache-2.0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v135.json')
    (STAGE / 'CREDITS.md').write_text(CREDITS)
    (STAGE / 'dataset-metadata.json').write_text(json.dumps(META, indent=1) + '\n')

    man = json.loads((STAGE / 'QCC_RELEASE_MANIFEST.json').read_text())
    assert len(man['files']) == 18
    for e in man['files']:
        p = STAGE / e['file']
        assert p.exists(), e['file']
        assert p.stat().st_size == e['bytes'], e['file']
        assert hashlib.sha256(p.read_bytes()).hexdigest() == e['sha256'], e['file']
    print(f'staged {len(list(STAGE.rglob("*")))} entries in {STAGE}')
    print('manifest OK: portfolio=%r files=%d' % (man['portfolio'], len(man['files'])))
    return 0


if __name__ == '__main__':
    sys.exit(main())
