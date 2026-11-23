#!/usr/bin/env python3
"""Stage the private badboyhalo1801/qcc-release-v146 snapshot dataset."""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TREE = ROOT / 'work/trees/v146_hybrid_dqi_chem'
TABLE = ROOT / 'work/sha_tables/sha_table_v146.txt'
STAGE = pathlib.Path('/tmp/opencode/snap_v146')

CREDITS = """# v146 — QCC release snapshot (hybrid: clean DQI + best measured chemistry)

Built 2026-11-23 from publicly released components, each independently checked
with the unchanged official verifiers.

| leg | member | source | official-verifier score |
|-----|--------|--------|--------------------------|
| invsqrt | `bb676b95f94c923c` (37 q, 33 rotations) | byte-identical to v144/v145 | 60,927.57739905387 (200,540,928 shots; moat-lab PASS) |
| dqi | `4b5721411adc239f` (900 q) | v144's DQI — the member the official verifier accepts with 0 value / 0 phase errors | 305,041,647,011.3978 (102,400 shots, 0/0, moat-lab PASS) |
| dfthcsos | npz `e7f08627208c…` + 15 3,357-T loaders (T=13,214) | best measured public chemistry table (published by asteriospanoras / evgendvorkin / hassanabdulhafid / manwithacat) with ozertuu's 3,357-Toffoli loaders | 251,089,557.46576697 (local official PASS, Q 405, lambda_eff 46.91798213749483) |

Predicted GM 33.1703303503537523913065411197878713240478112544176321620074.
The static SHA table is authoritative. The moat-lab kernel runs the
unchanged official verifiers on these exact bytes.

Note: the public `ozertuu/google-quantum-ai-vqcc-33-170350` tree was NOT
adopted: its DQI member `141f02ac69638c78` (v144's DQI minus one conditional
CCZ) failed the unchanged official verifier in moat-lab v59 with 2 value
errors out of 102,400 shots.

Licence: Apache-2.0 for the public components; see the source notebooks and
their licences for complete third-party notices.
"""

META = {
    'title': 'QCC release snapshot v146',
    'id': 'badboyhalo1801/qcc-release-v146',
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
        'portfolio': 'v146_hybrid_dqi_chem',
        'files': [
            {'file': name, 'bytes': size, 'sha256': sha,
             'stored_as': name.replace('/', '__')}
            for name, (sha, size) in sorted(files.items())
        ],
        'source': ('invsqrt bb676b95f94c (v144/v145), verifier-clean DQI '
                   '4b5721411adc239f (v144), best measured chemistry table '
                   'e7f08627208c + 15 three-thousand-three-hundred-fifty-seven '
                   'Toffoli loaders (public releases)'),
        'licence': 'Apache-2.0 (see CREDITS.md)',
    }
    (STAGE / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(manifest, indent=1) + '\n')
    shutil.copyfile(TABLE, STAGE / 'SHA_TABLE_v146.json')
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
