#!/usr/bin/env python3
"""Stage the private badboyhalo1801/qcc-release-v140 snapshot dataset.

The snapshot contains the exact 18 bytes pinned by sha_table_v140.txt.  It is
v139's official-PASS DQI and Leo T7421 chemistry tree plus Apache
public-circuits v170 inverse-sqrt member 52e8d4e6649b.  The moat-lab kernel
rechecks all 18 hashes and runs the unchanged official verifiers on these
snapshot bytes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v140_apache_invsqrt'
TABLE = ROOT / 'work/sha_tables/sha_table_v140.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v140')

CREDITS = """# v140 — QCC release snapshot (Apache invsqrt + Leo T7421 chemistry)

Built 2026-11-22 from the exact v139 tree plus one byte-distinct component
from Apache public-circuits dataset version 170.

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `52e8d4e6649b30ff` (37 q, 33 rotations) | Apache public-circuits v170; original release `sachchidanandadaki/vqcc-spliced-loader`; Apache-2.0 | 60,955.29842169718 (200,540,928 shots, local unchanged official verifier PASS) |
| dqi | `4b5721411adc239f` (900 q) | inherited byte-exact from v139 | 305,041,647,011.3978 (102,400 shots, 0 value / 0 phase errors) |
| dfthcsos | npz `b3683e07cf033989` + 15 T7421 loaders (T=13,244) | Leo Tang T7421 public output; inherited byte-exact from v139 | 251,692,077.714951 (PASS, lambda_eff 46.92403505616352, Q 405) |

Predicted GM 33.1388155155283337620293485875.  The inverse-sqrt replacement
is semantically the v139 circuit plus `INFO_TAG "reroll:b"`; the complete KMX
diff is exactly that one metadata line.  The static SHA table is authoritative.
The moat-lab kernel runs the unchanged official verifiers on these exact bytes.

Licence: Apache-2.0 / CC0 for the credited public components; see the source
notebooks and Apache dataset NOTICE for complete third-party notices.
"""

META = {
    'title': 'QCC release v140',
    'id': 'badboyhalo1801/qcc-release-v140',
    'subtitle': 'Byte-exact 18-file tree, sha-pinned for in-kernel verification',
    'description': CREDITS,
    'licenses': [{'name': 'Apache 2.0'}],
}


def main() -> int:
    table = json.loads(TABLE.read_text())
    files = table['files']
    if len(files) != 18:
        raise RuntimeError(f'expected 18 files, got {len(files)}')
    actual = {p.relative_to(TREE).as_posix(): p for p in TREE.rglob('*') if p.is_file()}
    if set(actual) != set(files):
        raise RuntimeError(f'tree/table mismatch: {set(actual) ^ set(files)}')
    for name, (sha, size) in files.items():
        b = actual[name].read_bytes()
        if hashlib.sha256(b).hexdigest() != sha or len(b) != size:
            raise RuntimeError(f'{name}: SHA/size mismatch')

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    for name, (sha, size) in files.items():
        dst = STAGE / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(actual[name], dst)

    manifest = {
        'portfolio': 'v140_apache_invsqrt_leotang_t7421',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': (
            'v139 Leo T7421 DQI/chemistry plus Apache public-circuits v170 '
            'inverse-sqrt 52e8d4e6649b'
        ),
        'licence': 'Apache-2.0 / CC0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v140.json')
    (STAGE / 'CREDITS.md').write_text(CREDITS)
    (STAGE / 'dataset-metadata.json').write_text(json.dumps(META, indent=1) + '\n')

    check = json.loads((STAGE / 'QCC_RELEASE_MANIFEST.json').read_text())
    if len(check['files']) != 18:
        raise RuntimeError('manifest member count mismatch')
    for e in check['files']:
        p = STAGE / e['file']
        if not p.exists() or p.stat().st_size != e['bytes']:
            raise RuntimeError(f'manifest file mismatch: {e["file"]}')
        if hashlib.sha256(p.read_bytes()).hexdigest() != e['sha256']:
            raise RuntimeError(f'manifest SHA mismatch: {e["file"]}')
    print(f'OK: staged {len(files)} SHA-pinned members in {STAGE}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
