#!/usr/bin/env python3
"""Build the byte-exact v144 candidate tree and static 18-file SHA table.

v144 keeps v143's certified three-T inverse-square-root and byte-exact DQI
member.  It adopts Leo Tang's newly published chemistry table and the two
corresponding loader members.  The unchanged local official chemistry
verifier PASSes at 251,688,794.86073643 (405 q, 1,219 shots).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
BASE = ROOT / 'work/trees/v143_three_t_phase'
SRC = pathlib.Path('/tmp/opencode/leotang_round4/tree/dfthcsos')
DST = ROOT / 'work/trees/v144_leotang_chem_refit'
TABLE = ROOT / 'work/sha_tables/sha_table_v144.txt'
BASE_NPZ_SHA = '0d4459fbd3d517c4cce7851444763d863e4c455f98554bd28f31f7a9cd081444'
NEW_NPZ_SHA = 'fd02c7f730b024a157cc8196a9b6345f9dc55a33c4ee9032d9d5777b3298c733'
# The two loaders printed as new in Leo Tang's log are byte-identical to the
# already adopted loader members; only the factorization NPZ changed.
UNCHANGED_LOADERS = {
    'angle_k_8.kmb': 'cb689cf38c0c820a776b9ff8cac5eee4564f8359c5cd907d6db7e6bf3937ef99',
    'angle_k_9.kmb': '8698ddcd7b05e4489f4340f59d04ac661da2cb950084cef793f2d7ebeb4fd9a0',
}
REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
COST = {
    'invsqrt': Decimal('60927.57739905387'),
    'dqi': Decimal('305041647011.3978'),
    'dfthcsos': Decimal('251688794.86073643'),
}


def digest(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    if not BASE.is_dir() or not SRC.is_dir():
        raise SystemExit('missing v143 tree or Leo Tang round4 chemistry tree')
    if digest(SRC / 'submission.npz')[0] != NEW_NPZ_SHA:
        raise SystemExit('Leo Tang round4 chemistry table SHA mismatch')
    for name, want in UNCHANGED_LOADERS.items():
        if digest(SRC / name)[0] != want:
            raise SystemExit(f'Leo Tang round4 {name} SHA mismatch')

    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(BASE, DST)
    shutil.copyfile(SRC / 'submission.npz', DST / 'dfthcsos/submission.npz')

    files: dict[str, list[object]] = {}
    for path in sorted(p for p in DST.rglob('*') if p.is_file()):
        rel = path.relative_to(DST).as_posix()
        files[rel] = list(digest(path))
    if len(files) != 18:
        raise SystemExit(f'expected exactly 18 files, got {len(files)}')

    changed = []
    for rel, entry in files.items():
        base_sha, base_size = digest(BASE / rel)
        if entry[0] != base_sha or entry[1] != base_size:
            changed.append(rel)
    expected = ['dfthcsos/submission.npz']
    if changed != expected:
        raise SystemExit(f'expected only {expected} to change, got {changed}')

    getcontext().prec = 60
    ratios = {k: REF[k] / COST[k] for k in REF}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (Decimal(1) / Decimal(3))
    previous = Decimal('33.1439220823404781609380739820350565305934107352740789700917')
    table = {
        'tree': (
            'v144 = v143 three-T phase compiler bb676b95f94c and DQI '
            '4b572141 unchanged + Leo Tang latest chemistry table fd02c7f730b0 '
            'and the same 15 Leo Tang loaders '
            '(official local PASS 251688794.86073643 @405q); predicted GM '
            + str(gm)
        ),
        'files': files,
    }
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(json.dumps(table, indent=1) + '\n')
    print(f'built {DST}')
    print(f'changed members: {changed}')
    print(f'predicted GM: {gm}')
    print(f'delta GM vs v143: {gm - previous:+}')
    print(f'wrote {TABLE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
