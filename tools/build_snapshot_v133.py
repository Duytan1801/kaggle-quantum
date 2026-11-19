#!/usr/bin/env python3
"""build_snapshot_v133.py — create the `badboyhalo1801/qcc-release-v133` snapshot dataset.

The moat-lab kernel discovers the tree through a Kaggle *dataset* (the anchor
`qcc-release-v133`), so a submission-grade tree needs its own immutable
snapshot: the 18 files plus a manifest and a README that carry the credits.

Layout follows the v124/v131/v132 convention:
  <file>                      -> the exact bytes that go into submission.zip
  <subdir>/<file>             -> kept as a subdirectory (dfthcsos/)
  flat fallback               -> <subdir>__<file> for datasets that flatten names

The 18-file SHA table is the authority; this script verifies every file against
`work/sha_tables/sha_table_v133.txt` BEFORE staging anything.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v133_combo'
TABLE = ROOT / 'work/sha_tables/sha_table_v133.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v133')

CREDITS = """# v133 — QCC release snapshot

Public mix adopted from the public-release queue on 2026-11-19.

| leg | member | source | local official-verifier score |
|-----|--------|--------|--------------------------------|
| invsqrt | `ecf908fec987b61a` (44 q, 33 rotations) | maoxin123's 28.23 invsqrt lineage, released via `ghazarosbarseghyan91/vqcc-combo-candidates` | 74,383.69875786705 (200,540,928 shots, PASS) |
| dqi | `15a4b7403356092e` (890 q) | ozertuu's board-clean DQI decoder (same bytes as v132) | 345,256,821,433.9815 (102,400 shots, 0 value / 0 phase errors) |
| dfthcsos | npz `6ef06081cb9c5752` + 15 ANGLE loaders | marculera's DF-THC refit weights + the 4,022-Toffoli loader family | 294,642,169.5116752 (PASS, lambda_eff 46.92156262935824) |

Projected GM 28.23441 (v132 was 28.23163).

Licence: Apache-2.0 for the code in the public notebooks; the circuits themselves
are derived from the public competition starter kit and the public releases
credited above.
"""


def main() -> int:
    table = json.loads(TABLE.read_text())
    files = table['files']
    assert len(files) == 18, f'expected 18 files, got {len(files)}'

    # --- verify the tree against the table (no silent drift) ---
    actual = {str(p.relative_to(TREE)): p for p in TREE.rglob('*') if p.is_file()}
    assert set(actual) == set(files), f'tree/table mismatch: {set(actual) ^ set(files)}'
    for name, (sha, size) in files.items():
        h = hashlib.sha256(actual[name].read_bytes()).hexdigest()
        assert h == sha, f'{name}: {h} != {sha}'
        assert actual[name].stat().st_size == size, f'{name}: size mismatch'
    print(f'OK: {len(files)} files verified against {TABLE.name}')

    # --- stage ---
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    for name, (sha, size) in files.items():
        dst = STAGE / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(actual[name], dst)

    manifest = {
        'portfolio': 'v133_ghazaros_combo_28_23441',
        'files': [
            {
                'file': name,
                'bytes': size,
                'sha256': sha,
                'stored_as': name.replace('/', '__'),
            }
            for name, (sha, size) in sorted(files.items())
        ],
        'source': 'ghazarosbarseghyan91/vqcc-combo-candidates (2026-11-19): invsqrt ecf908fec987b61a '
                  '(maoxin123 lineage), dqi 15a4b7403356092e (ozertuu), chemistry npz 6ef06081cb9c5752 '
                  '(marculera DF-THC refit) + the 4,022-Toffoli ANGLE loader family',
        'licence': 'Apache-2.0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v133.json')
    (STAGE / 'CREDITS.md').write_text(CREDITS)

    # sanity: the manifest must round-trip
    man = json.loads((STAGE / 'QCC_RELEASE_MANIFEST.json').read_text())
    assert man['portfolio']
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
