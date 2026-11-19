#!/usr/bin/env python3
"""build_snapshot_v132.py — create the `badboyhalo1801/qcc-release-v132` snapshot dataset.

The moat-lab kernel discovers the tree through a Kaggle *dataset* (the anchor
`qcc-release-v132`), so a submission-grade tree needs its own immutable
snapshot: the 18 files plus a manifest and a README that carry the credits.

Layout follows the v124/v131 convention:
  <file>                      -> the exact bytes that go into submission.zip
  <subdir>/<file>             -> kept as a subdirectory (dfthcsos/)
  flat fallback               -> <subdir>__<file> for datasets that flatten names

The 18-file SHA table is the authority; this script verifies every file against
`work/sha_tables/sha_table_v132.txt` BEFORE staging anything.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v132_frontier'
TABLE = ROOT / 'work/sha_tables/sha_table_v132.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v132')


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

    # MANIFEST CONTRACT (moat-lab): the kernel reads
    #   man["portfolio"]                       -> a label string
    #   man["files"] : list of {file, bytes, sha256, stored_as}
    # and resolves each file through local_path(file, stored_as), which tries
    #   <mount>/<file>  then  <mount>/<stored_as>  then  <mount>/<file with / -> __>
    # so `stored_as` may carry the flat fallback name even when the nested
    # directory form is what was uploaded.
    manifest = {
        'portfolio': 'v132_atlas_frontier_28_23162',
        'files': [
            {
                'file': name,
                'bytes': size,
                'sha256': sha,
                'stored_as': name.replace('/', '__'),
            }
            for name, (sha, size) in sorted(files.items())
        ],
        'source': 'asteriospanoras/qcc-circuit-atlas v3 frontier/qcc_28_23162_submission '
                  '(byte-identical to the atlas receipt); tree credits: maoxin123 (invsqrt), '
                  'ozertuu (dqi), leotang09 (chemistry weights), syed3000 + ahoirg (invsqrt lineage)',
        'licence': 'Apache-2.0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(ROOT / 'work/sha_tables/sha_table_v132.txt',
                    STAGE / 'SHA_TABLE_v132.json')

    # sanity: the manifest must round-trip through the moat-lab's own reader
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
