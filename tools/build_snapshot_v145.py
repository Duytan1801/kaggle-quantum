#!/usr/bin/env python3
"""Stage the private badboyhalo1801/qcc-release-v145 snapshot dataset."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v145_ozertuu_33170350'
TABLE = ROOT / 'work/sha_tables/sha_table_v145.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v145')

CREDITS = """# v145 — QCC release snapshot (ozertuu 33.170350 tree)

Built 2026-11-23 from the exact 18-member output of the public Apache-2.0
kernel `ozertuu/google-quantum-ai-vqcc-33-170350`.

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `bb676b95f94c923c` (37 q, 33 rotations) | byte-identical to v144 | 60,927.57739905387 (200,540,928 shots) |
| dqi | `141f02ac69638c78` (900 q) | v144 DQI with exactly one conditional `CCZ` removed | 305,041,160,753.34 claimed; official in-kernel receipt required |
| dfthcsos | npz `05387b5d160fe2df` + 15 3,357-T loaders (T=13,214) | `ozertuu/google-quantum-ai-vqcc-33-170350` output | 251,089,557.508397 (local official PASS, Q 405) |

Predicted GM 33.1703479737831408066848265849219924110754769688805472789162.
The static SHA table is authoritative. The moat-lab kernel runs the
unchanged official verifiers on these exact bytes.

Licence: Apache-2.0 for the public components; see the source notebook and
its licences for complete third-party notices.
"""

META = {
    'title': 'QCC release snapshot v145',
    'id': 'badboyhalo1801/qcc-release-v145',
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
        if '/' in name:
            shutil.copyfile(actual[name], STAGE / name.replace('/', '__'))

    manifest = {
        'portfolio': 'v145_ozertuu_33170350',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': ('exact output of ozertuu/google-quantum-ai-vqcc-33-170350; '
                   'invsqrt bb676b95f94c, DQI 141f02ac69638c78, chemistry '
                   '05387b5d160fe2df + 15 three-thousand-three-hundred-fifty-seven '
                   'Toffoli loaders'),
        'licence': 'Apache-2.0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v145.json')
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
