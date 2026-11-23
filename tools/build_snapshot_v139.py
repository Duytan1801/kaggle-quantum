#!/usr/bin/env python3
"""Stage the private `badboyhalo1801/qcc-release-v139` snapshot dataset.

v139 is the exact 18-file OUTPUT of Leo Tang's public
`leotang09/vqcc-t7421-submission` kernel.  The tree changes only the chemistry
leg relative to v138; invsqrt and DQI are byte-identical to the already
official-PASS v138 members.  The independent local run of the unchanged
official chemistry verifier PASSes at 251,692,077.714951 (T=13,244, Q=405,
lambda_eff=46.92403505616352).

The static SHA table is authoritative: every staged byte is checked before the
dataset is created, and the in-kernel moat-lab re-checks the same 18 hashes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v139_leotang_t7421'
TABLE = ROOT / 'work/sha_tables/sha_table_v139.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v139')

CREDITS = """# v139 — QCC release snapshot (public 33.13881 tree)

Adopted 2026-11-22 from the public-release queue. The exact 18 bytes are the
output of `leotang09/vqcc-t7421-submission`.

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `d2148a7cd7a4d0a0` (37 q, 33 rotations) | rithvikredrouthu / syed3000 public lineage | 60,955.32670759028 (200,540,928 shots, PASS; exact bytes inherited from v138) |
| dqi | `4b5721411adc239f` (900 q) | tonylica public generator | 305,041,647,011.3978 (102,400 shots, 0 value / 0 phase errors; exact bytes inherited from v138) |
| dfthcsos | npz `b3683e07cf033989` + 15 ANGLE loaders (T=13,244) | Leo Tang T7421 public output; Apache-2.0 lineage documented in the source notebook | 251,692,077.714951 (PASS, lambda_eff 46.92403505616352, Q 405) |

Predicted GM 33.13881038958233. The chemistry score was independently
reproduced with the unchanged official local verifier. The moat-lab kernel
re-runs the unchanged official verifiers on these exact snapshot bytes.

Licence: Apache-2.0 / CC0 for the credited public components; see the source
notebook and upstream NOTICE files for the complete third-party notices.
"""

META = {
    'title': 'QCC release v139 (public 33.13881 snapshot)',
    'id': 'badboyhalo1801/qcc-release-v139',
    'subtitle': 'Public 33.13881 18-file tree, sha-pinned for in-kernel verification',
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
        'portfolio': 'v139_public_leotang_t7421_33_13881',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': 'output of leotang09/vqcc-t7421-submission; chemistry npz '
                  'b3683e07 + 15 loaders T13244 Q405',
        'licence': 'Apache-2.0 / CC0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v139.json')
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
