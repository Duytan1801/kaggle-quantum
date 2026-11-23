#!/usr/bin/env python3
"""Build the byte-exact v143 candidate tree and static 18-file SHA table.

v143 keeps v142's byte-exact DQI decoder and Leo Tang chemistry family and
adopts varianceofx's certified three-T phase-compiler inverse-square-root
member.  The unchanged local official invsqrt verifier PASSes the exact bytes
at 60,927.57739905387 (37 q, 200,540,928 shots).
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
BASE = ROOT / 'work/trees/v142_leotang_chem'
SRC_INV = pathlib.Path('/tmp/opencode/variance_three_t/tree/invsqrt.kmb')
DST = ROOT / 'work/trees/v143_three_t_phase'
TABLE = ROOT / 'work/sha_tables/sha_table_v143.txt'
NEW_INV_SHA = 'bb676b95f94c923cc5482f6cd8d457ab5ff3e8180c8f7cfd2c9678335d0ba56b'
BASE_INV_SHA = '52e8d4e6649b30ff7b46f173cffc1ea47566ff11a841520484f0d6cf08777f54'
REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
COST = {
    'invsqrt': Decimal('60927.57739905387'),
    'dqi': Decimal('305041647011.3978'),
    'dfthcsos': Decimal('251690221.89594275'),
}


def digest(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    if not BASE.is_dir() or not SRC_INV.is_file():
        raise SystemExit('missing v142 tree or varianceofx inverse-square-root member')
    if digest(SRC_INV)[0] != NEW_INV_SHA:
        raise SystemExit('varianceofx inverse-square-root SHA mismatch')
    if digest(BASE / 'invsqrt.kmb')[0] != BASE_INV_SHA:
        raise SystemExit('v142 inverse-square-root SHA mismatch')

    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(BASE, DST)
    shutil.copyfile(SRC_INV, DST / 'invsqrt.kmb')

    files: dict[str, list[object]] = {}
    for path in sorted(p for p in DST.rglob('*') if p.is_file()):
        rel = path.relative_to(DST).as_posix()
        sha, nbytes = digest(path)
        files[rel] = [sha, nbytes]
    if len(files) != 18:
        raise SystemExit(f'expected exactly 18 files, got {len(files)}')

    changed = []
    for rel, entry in files.items():
        base_sha, base_size = digest(BASE / rel)
        if entry[0] != base_sha or entry[1] != base_size:
            changed.append(rel)
    if changed != ['invsqrt.kmb']:
        raise SystemExit(f'expected only inverse-square-root to change, got {changed}')

    getcontext().prec = 60
    ratios = {k: REF[k] / COST[k] for k in REF}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (Decimal(1) / Decimal(3))
    previous = Decimal('33.138896964186566120113950746488050643547143089038')
    table = {
        'tree': (
            'v143 = v142 Leo Tang chemistry 0d4459fbd3d51 and DQI 4b572141 '
            'unchanged + varianceofx certified three-T phase-compiler inverse '
            'bb676b95f94c (official local PASS 60927.57739905387 @37q); '
            'predicted GM ' + str(gm)
        ),
        'files': files,
    }
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(json.dumps(table, indent=1) + '\n')
    print(f'built {DST}')
    print(f'changed members: {changed}')
    print(f'predicted GM: {gm}')
    print(f'delta GM vs v142: {gm - previous:+}')
    print(f'wrote {TABLE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
