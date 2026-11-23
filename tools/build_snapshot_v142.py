#!/usr/bin/env python3
"""Stage the private badboyhalo1801/qcc-release-v142 snapshot dataset."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v142_leotang_chem'
TABLE = ROOT / 'work/sha_tables/sha_table_v142.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v142')

CREDITS = """# v142 — QCC release snapshot (Apache invsqrt + Leo Tang chemistry)

Built 2026-11-22 from two independently verified public component releases.

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `52e8d4e6649b30ff` (37 q, 33 rotations) | Apache public-circuits v170; original release `sachchidanandadaki/vqcc-spliced-loader`; Apache-2.0 | 60,955.29842169718 (200,540,928 shots; local + moat-lab PASS) |
| dqi | `4b5721411adc239f` (900 q) | inherited byte-exact from v139 | 305,041,647,011.3978 (102,400 shots, 0 value / 0 phase errors) |
| dfthcsos | npz `0d4459fbd3d517c4` + 15 3,372-T loaders (T=13,244) | Leo Tang `vqcc-t7421-submission` | 251,690,221.89594275 (PASS, lambda_eff 46.923689067855136, Q 405) |

Predicted GM 33.138896964186566120113950746488050643547143089038.
The static SHA table is authoritative.  The moat-lab kernel runs the
unchanged official verifiers on these exact bytes.

Licence: Apache-2.0 / CC0 for the credited public components; see source
notebooks and their licences for complete third-party notices.
"""

META = {
    'title': 'QCC release v142',
    'id': 'badboyhalo1801/qcc-release-v142',
    'subtitle': 'Byte-exact 18-file tree, sha-pinned for in-kernel verification',
    'description': CREDITS,
    'licenses': [{'name': 'Apache 2.0'}],
}


def main() -> int:
    files = json.loads(TABLE.read_text())['files']
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
        'portfolio': 'v142_apache_invsqrt_leotang_chem',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': ('Apache public-circuits v170 inverse-sqrt 52e8d4e6649b plus '
                   'Leo Tang T7421 3,372-T loader chain and table 0d4459fbd3d51'),
        'licence': 'Apache-2.0 / CC0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v142.json')
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
