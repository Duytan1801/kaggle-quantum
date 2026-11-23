#!/usr/bin/env python3
"""Build the byte-exact v140 candidate tree and its static 18-file SHA table.

v140 keeps all 17 members of the official-PASS v139 tree and replaces only the
inverse-sqrt member with Apache public-circuits v170's
``52e8d4e6649b30ff7b46f173cffc1ea47566ff11a841520484f0d6cf08777f54``.
The replacement is semantically the same circuit plus ``INFO_TAG "reroll:b"``;
its unchanged official verifier PASSes locally at 60,955.29842169718.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
BASE = ROOT / 'work/trees/v139_leotang_t7421'
SRC_INV = pathlib.Path('/tmp/opencode/apache_v170/circuits/invsqrt/circuits/invsqrt/52e8d4e6649b.kmb')
DST = ROOT / 'work/trees/v140_apache_invsqrt'
TABLE = ROOT / 'work/sha_tables/sha_table_v140.txt'
NEW_SHA = '52e8d4e6649b30ff7b46f173cffc1ea47566ff11a841520484f0d6cf08777f54'
BASE_SHA = 'd2148a7cd7a4d0a004eca1e7b18f9fd1282df4ed3be4a9aa970842f9119fa307'
REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
COST = {
    'invsqrt': Decimal('60955.29842169718'),
    'dqi': Decimal('305041647011.3978'),
    'dfthcsos': Decimal('251692077.714951'),
}


def digest(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    if not BASE.is_dir() or not SRC_INV.is_file():
        raise SystemExit('missing v139 tree or Apache invsqrt member')
    got, size = digest(SRC_INV)
    if got != NEW_SHA:
        raise SystemExit(f'Apache invsqrt SHA mismatch: {got}')
    if digest(BASE / 'invsqrt.kmb')[0] != BASE_SHA:
        raise SystemExit('v139 invsqrt SHA mismatch')

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
        raise SystemExit(f'expected only invsqrt.kmb to change, got {changed}')

    getcontext().prec = 50
    ratios = {k: REF[k] / COST[k] for k in REF}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (Decimal(1) / Decimal(3))
    previous = Decimal('33.13881038958233')
    table = {
        'tree': (
            'v140 = v139 Leo T7421 tree with Apache public-circuits v170 inverse-sqrt '
            '52e8d4e6649b (official local PASS 60955.29842169718 @37q); DQI '
            '4b572141 and chemistry b3683e07 unchanged; predicted GM '
            f'{gm}'
        ),
        'files': files,
    }
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(json.dumps(table, indent=1) + '\n')
    print(f'built {DST}')
    print(f'changed members: {changed}')
    print(f'predicted GM: {gm}')
    print(f'delta GM: {gm - previous:+}')
    print(f'wrote {TABLE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
