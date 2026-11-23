#!/usr/bin/env python3
"""Build the byte-exact v142 candidate tree and static 18-file SHA table.

v142 keeps the independently official-PASS v141 inverse-sqrt and DQI members
and replaces the chemistry table with Leo Tang's newly published
``0d4459fbd3d517c4...`` table.  The unchanged local official chemistry
verifier PASSes at 251,690,221.89594275 with the same 15 loader members.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
BASE = ROOT / 'work/trees/v141_goodpjw_chem'
SRC_NPZ = pathlib.Path('/tmp/opencode/leotang_round3/submission.npz')
DST = ROOT / 'work/trees/v142_leotang_chem'
TABLE = ROOT / 'work/sha_tables/sha_table_v142.txt'
NEW_NPZ_SHA = '0d4459fbd3d517c4cce7851444763d863e4c455f98554bd28f31f7a9cd081444'
BASE_NPZ_SHA = 'baa8b2966e889ef6be581c85e440ef856c025687c2ff2f1a0fa13033f7e35c84'
REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
COST = {
    'invsqrt': Decimal('60955.29842169718'),
    'dqi': Decimal('305041647011.3978'),
    'dfthcsos': Decimal('251690221.89594275'),
}


def digest(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    if not BASE.is_dir() or not SRC_NPZ.is_file():
        raise SystemExit('missing v141 tree or Leo Tang chemistry table')
    if digest(SRC_NPZ)[0] != NEW_NPZ_SHA:
        raise SystemExit('Leo Tang chemistry table SHA mismatch')
    if digest(BASE / 'dfthcsos/submission.npz')[0] != BASE_NPZ_SHA:
        raise SystemExit('v141 chemistry table SHA mismatch')

    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(BASE, DST)
    shutil.copyfile(SRC_NPZ, DST / 'dfthcsos/submission.npz')

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
    if changed != ['dfthcsos/submission.npz']:
        raise SystemExit(f'expected only chemistry table to change, got {changed}')

    getcontext().prec = 50
    ratios = {k: REF[k] / COST[k] for k in REF}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (Decimal(1) / Decimal(3))
    previous = Decimal('33.138815789366048864455589556675054991449123594135')
    table = {
        'tree': (
            'v142 = v141 Apache public-circuits v170 inverse-sqrt 52e8d4e6649b '
            '(official local and moat PASS 60955.29842169718 @37q) + Leo Tang '
            'T7421 3,372-T loader chain and table 0d4459fbd3d51 (official '
            'source and independent local official PASS 251690221.89594275 '
            '@405q) + DQI 4b572141 unchanged; predicted GM ' + str(gm)
        ),
        'files': files,
    }
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(json.dumps(table, indent=1) + '\n')
    print(f'built {DST}')
    print(f'changed members: {changed}')
    print(f'predicted GM: {gm}')
    print(f'delta GM vs v141: {gm - previous:+}')
    print(f'wrote {TABLE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
