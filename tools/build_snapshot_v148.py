#!/usr/bin/env python3
"""build_snapshot_v148.py — stage the `badboyhalo1801/qcc-release-v148` snapshot dataset.

v148 = v147 (invsqrt bb676b95 + DQI 6f78ecdd) with goodpjw2008's shorter
chemistry loaders: 10 of the 15 ANGLE loaders re-solved from 3,357 to 3,334
Toffolis per pass, plus a refitted table npz `573d10be`.

Official local chemistry verifier on the exact assembled tree:
    PASS 250,195,979.3541336  (lambda_eff 46.91432641685298, T 13,168, Q 405)
vs our v147 251,089,557.02151904  =>  -893,577.67 cost units  =>  +0.0395 GM.

The 18-file SHA table (work/sha_tables/sha_table_v148.txt) is the authority;
this script verifies every file against it BEFORE staging anything.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v148'
TABLE = ROOT / 'work/sha_tables/sha_table_v148.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v148')

CREDITS = """# v148 — QCC release snapshot (public frontier, 33.2101)

Adopted 2026-11-25 from the public-release queue.  invsqrt and DQI are
byte-identical to v147; only the chemistry leg changed, and it is
`goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-21011` (public LB 33.21011).

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `bb676b95f94c923c` (37 q) | `varianceofx/vqcc-three-t-phase-compiler` (edit of `rithvikredrouthu`'s `d2148a7c`) | 60,927.57739905387 (PASS) |
| dqi | `6f78ecdd636051d4` (900 q) | `goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067` | ~305,032,962,722 (official PASS; clean public draw) |
| dfthcsos | npz `573d10bed90b4ad7` + 10 re-solved 3,334-T loaders + 5 unchanged 3,357-T loaders | `goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-21011` | 250,195,979.3541336 (PASS, lambda_eff 46.91432641685298, T 13,168, Q 405) |

Licence: Apache-2.0 for the public notebooks / datasets credited above.
"""

META = {
    'title': 'QCC release v148 shorter chemistry loaders',
    'id': 'badboyhalo1801/qcc-release-v148',
    'subtitle': 'v147 tree + goodpjw2008 3,334-T loaders and refitted chemistry table',
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
        'portfolio': 'v148_shorter_chem_loaders',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': 'invsqrt bb676b95 + dqi 6f78ecdd (unchanged from v147) + '
                  'chemistry npz 573d10be on goodpjw2008 3,334-T loaders',
        'licence': 'Apache-2.0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v148.json')
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
