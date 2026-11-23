#!/usr/bin/env python3
"""build_snapshot_v147.py — stage the `badboyhalo1801/qcc-release-v147` snapshot dataset.

v147 = invsqrt bb676b95 (unchanged) + goodpjw2008's zero-test-cut DQI 6f78ecdd +
varianceofx's chemistry table 16b4f5b5 on the shared 3,357-T loaders.

It is the first tree in this campaign that beats our own v146 (33.17029) on the
public board: goodpjw2008 published the same DQI at LB 33.17067 with a chemistry
table 0.0443 cost units more expensive than the one shipped here.

The 18-file SHA table (work/sha_tables/sha_table_v147.txt) is the authority; this
script verifies every file against it BEFORE staging anything.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v147'
TABLE = ROOT / 'work/sha_tables/sha_table_v147.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v147')

CREDITS = """# v147 — QCC release snapshot (public-best tree, 33.1706 predicted)

Adopted 2026-11-23 from the public-release queue.  The DQI member is
`goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067` (public LB 33.17067); the
chemistry table is `varianceofx/vqcc-verified-3357-loader-portfolio`, the cheapest
public table measured against the shared 3,357-Toffoli loaders; the inverse
square root and all 15 loaders are byte-identical to our v146.

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `bb676b95f94c923c` (37 q, 33 rotations) | `varianceofx/vqcc-three-t-phase-compiler` (edit of `rithvikredrouthu`'s `d2148a7c`) | 60,927.57739905387 (200,540,928 shots, PASS) |
| dqi | `6f78ecdd636051d4` (900 q) | `goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067` — tonylica's `4b572141` with 10 gate rewrites (evgendvorkin's CCZ->CZ, ozertuu's CCZ delete, 8 CCX->CX at zero-test positions 17-24) | ~305,032,962,722 (102,400 shots, 0 value / 0 phase errors) |
| dfthcsos | npz `16b4f5b5e51b0777` + the 15 ANGLE loaders of `maoxin123` (3,357 Toffolis per pass) | `varianceofx/vqcc-verified-3357-loader-portfolio` | 251,089,557.02151904 (PASS, lambda_eff 46.917982054483744, T 13,214, Q 405) |

Licence: Apache-2.0 for the public notebooks / datasets credited above.
"""

META = {
    'title': 'QCC release v147 zero-test-cut DQI',
    'id': 'badboyhalo1801/qcc-release-v147',
    'subtitle': 'Zero-test-cut DQI 6f78ecdd + cheapest public chemistry table',
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
        'portfolio': 'v147_zero_test_dqi_vox_chem',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': 'invsqrt bb676b95 + dqi 6f78ecdd (goodpjw2008 zero-test cuts) + '
                  'chemistry npz 16b4f5b5 (varianceofx) on maoxin123 3,357-T loaders',
        'licence': 'Apache-2.0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v147.json')
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
