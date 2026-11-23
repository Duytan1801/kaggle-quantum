#!/usr/bin/env python3
"""Build the byte-exact v141 candidate tree and static 18-file SHA table.

v141 combines the two independently verified public component improvements
found in the 2026-11-22 sweep:

* inverse-sqrt `52e8d4e6649b...` from Apache public-circuits v170
  (unchanged official verifier PASS: 60,955.29842169718, 37 q); and
* chemistry table `baa8b2966e88...` from GoodpJW's
  `qcc-3-372-t-loaders-refit-table-lb-33-13877` output, paired with the exact
  15 loader members (source official PASS and an independent unchanged local
  official-verifier PASS: 251,692,071.475490).

The DQI member remains the byte-exact official-PASS v139 member.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
BASE = ROOT / 'work/trees/v140_apache_invsqrt'
SRC_NPZ = pathlib.Path('/tmp/opencode/newqueue/goodpjw/submission.npz')
DST = ROOT / 'work/trees/v141_goodpjw_chem'
TABLE = ROOT / 'work/sha_tables/sha_table_v141.txt'
NEW_NPZ_SHA = 'baa8b2966e889ef6be581c85e440ef856c025687c2ff2f1a0fa13033f7e35c84'
BASE_NPZ_SHA = 'b3683e07cf033989f945a4625cd3a2b34a505e44991340caf09b88162286f3cf'
REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
COST = {
    'invsqrt': Decimal('60955.29842169718'),
    'dqi': Decimal('305041647011.3978'),
    'dfthcsos': Decimal('251692071.47549'),
}


def digest(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    if not BASE.is_dir() or not SRC_NPZ.is_file():
        raise SystemExit('missing v140 tree or GoodpJW chemistry table')
    if digest(SRC_NPZ)[0] != NEW_NPZ_SHA:
        raise SystemExit('GoodpJW chemistry table SHA mismatch')
    if digest(BASE / 'dfthcsos/submission.npz')[0] != BASE_NPZ_SHA:
        raise SystemExit('v140 chemistry table SHA mismatch')

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
    previous = Decimal('33.138815515528333762029348587518900386419687678795')
    table = {
        'tree': (
            'v141 = v140 Apache public-circuits v170 inverse-sqrt 52e8d4e6649b '
            '(official local and moat PASS 60955.29842169718 @37q) + GoodpJW '
            '3,372-T loader chain and table baa8b2966e88 (official source and '
            'independent local official PASS 251692071.475490 @405q) + DQI '
            '4b572141 unchanged; predicted GM ' + str(gm)
        ),
        'files': files,
    }
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(json.dumps(table, indent=1) + '\n')
    print(f'built {DST}')
    print(f'changed members: {changed}')
    print(f'predicted GM: {gm}')
    print(f'delta GM vs v140: {gm - previous:+}')
    print(f'wrote {TABLE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
