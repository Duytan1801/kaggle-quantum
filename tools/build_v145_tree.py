#!/usr/bin/env python3
"""Build the byte-exact v145 candidate tree and static 18-file SHA table.

v145 is the exact 18-member output of `ozertuu/google-quantum-ai-vqcc-33-170350`:
inverse-square-root is byte-identical to v144, DQI is v144's DQI with exactly
one conditional CCZ removed (141f02ac69638c78), and the chemistry tree is the
3,357-Toffoli loader family.  Chemistry was independently PASSed locally at
251,089,557.508397 (405 q, 1,219 shots).

The official in-kernel DQI receipt is the remaining gate; this script only
builds the tree + static table and rejects any byte deviation from the
pre-registered hashes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
SRC = pathlib.Path('/tmp/opencode/rel_ozertuu_33170350/tree')
DST = ROOT / 'work/trees/v145_ozertuu_33170350'
TABLE = ROOT / 'work/sha_tables/sha_table_v145.txt'

# Pinned expected members (source output, 2026-11-22T22:59Z).
EXPECTED = {
    'invsqrt.kmb': ('bb676b95f94c923cc5482f6cd8d457ab5ff3e8180c8f7cfd2c9678335d0ba56b', 523327),
    'dqi.kmb': ('141f02ac69638c7852ed377dd216c6f7a765797a090c5e785a2dbeca38c5f8aa', 617641604),
    'dfthcsos/submission.npz': ('05387b5d160fe2dfbcd452648cede3032318eec4593cdf5b0dc899b6d702f0a5', 1864916),
}
LOADERS = {
    'angle_k_0.kmb': ('f2004c1f1d12f4a0028252aa3febd713856d246ff21134ca91a92348c4bf2994', 501906),
    'angle_k_1.kmb': ('55d06dd8ca615a9347d1f5e7f56995dbfc98271a9e7dcd41afcfa1471322e1ab', 495144),
    'angle_k_2.kmb': ('ad15e5f7a198103af1fba6af7f36048948395853464b5876191844c8f2c4a539', 281142),
    'angle_k_3.kmb': ('5ded23f357ebfa0ed1fe639f1cffd92d31957fb3845509d70abbb37c0bac5773', 278967),
    'angle_k_4.kmb': ('c083539bde81b2b88f377fde85ac3b1ded11d1b2bcda246c59ec6a80597205fd', 284075),
    'angle_k_5.kmb': ('6596b8f24e9fe2591ae5a9cfd63d3f4ed10d1b740cab1799b91eed55d1350da5', 494427),
    'angle_k_6.kmb': ('5ea8a2182ae7c70bb6b7f095970b9abe7dde84d8ca4c6940713a75a70655a0cd', 280016),
    'angle_k_7.kmb': ('f76cbba9b71e0f0601b2e906dd4c698438c1d8be7e65bb858c7f1626f3710c6e', 494173),
    'angle_k_8.kmb': ('227472385bffce8eb08c31ee93d635755901b29107bb32177885e1b7e212f898', 265777),
    'angle_k_9.kmb': ('62a3c1d1fb44df40a57df87b0907402fed4e581ec0dfe7f7647b92e75e0d4b3d', 279368),
    'angle_k_10.kmb': ('6821f925554fec08153670bcc9ff83dc893d8cde72003727139c754b4ebbbbd9', 275433),
    'angle_k_11.kmb': ('6d8ca06817049162d67d89aaf1ae0fd88acbb7ee984c4c28d222cd14e512ffda', 495152),
    'angle_k_12.kmb': ('ddde7ec28d025883a9a789f4d313696d61797f26ab20016033362736cdf8bc72', 280926),
    'angle_k_13.kmb': ('acaee97f692c612dddcac3bc1978f3f58348504fba3881bdd4a6b440aa2ed7e6', 267412),
    'angle_k_14.kmb': ('5cef55cf6208b2cfd4f52a13b63241b4ce7b5196f9dddfe0349e484030db07cd', 275201),
}

REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
COST = {
    'invsqrt': Decimal('60927.57739905387'),
    # ozertuu's published verifier value; must be reproduced in-kernel.
    'dqi': Decimal('305041160753.3364'),
    'dfthcsos': Decimal('251089557.508397'),
}


def digest(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit('missing extracted ozertuu tree')
    want = {**EXPECTED, **{f'dfthcsos/{k}': v for k, v in LOADERS.items()}}
    if len(want) != 18:
        raise SystemExit(f'expected 18 pinned members, got {len(want)}')

    actual = {p.relative_to(SRC).as_posix(): p for p in SRC.rglob('*') if p.is_file()}
    if set(actual) != set(want):
        raise SystemExit(f'tree mismatch: {set(actual) ^ set(want)}')
    for rel, (sha, size) in want.items():
        got = digest(actual[rel])
        if got != (sha, size):
            raise SystemExit(f'{rel}: expected {(sha, size)}, got {got}')

    # inverse-square-root must still be v144's certified member
    v144 = ROOT / 'work/trees/v144_leotang_chem_refit/invsqrt.kmb'
    if digest(v144) != want['invsqrt.kmb']:
        raise SystemExit('invsqrt is not byte-identical to v144')

    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(SRC, DST)

    files = {}
    for rel in sorted(want):
        files[rel] = list(digest(DST / rel))
    if len(files) != 18:
        raise SystemExit(f'expected exactly 18 files, got {len(files)}')

    getcontext().prec = 60
    ratios = {k: REF[k] / COST[k] for k in REF}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (Decimal(1) / Decimal(3))
    previous = Decimal('33.1439847224675759169083408104802578161029519713326461544372')
    table = {
        'tree': (
            'v145 = exact ozertuu 33.170350 output: invsqrt bb676b95f94c unchanged, '
            'DQI 141f02ac69638c78 (v144 DQI minus one CCZ), chemistry npz '
            '05387b5d160fe2df + 15 three-thousand-three-hundred-fifty-seven Toffoli '
            'loaders (official local PASS 251089557.508397 @405q); predicted GM '
            + str(gm)
        ),
        'files': files,
    }
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(json.dumps(table, indent=1) + '\n')
    print(f'built {DST}')
    print(f'files: {len(files)} (18 pinned)')
    print(f'predicted GM: {gm}')
    print(f'delta GM vs v144: {gm - previous:+}')
    print(f'wrote {TABLE}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
