#!/usr/bin/env python3
"""Build the byte-exact v146 candidate tree and static 18-file SHA table.

v146 mixes the best measured members found by the 2026-11-23 queue sweep:

  invsqrt   bb676b95f94c  — byte-identical to v144/v145 (37 q)
  dqi       4b572141…     — v144's DQI, the member that the official verifier
                            accepted with 0 value / 0 phase errors in moat-lab
                            v58 (ozertuu's 141f02ac FAILED the same verifier in
                            moat-lab v59 with 2 value errors)
  chemistry npz e7f08627… — the best measured table (official local PASS
                            251,089,557.46576697 with the shared 3,357-T loaders)
  15 loaders               — ozertuu's 3,357-Toffoli loaders (identical in all
                            candidate releases)

The chemistry leg was measured locally with the unchanged official verifier;
the DQI and inverse-square-root members are byte-identical to the members
already accepted in-kernel, but the gate still requires a fresh official
in-kernel receipt on the exact v146 snapshot bytes.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import shutil
from decimal import Decimal, getcontext

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
V145 = ROOT / 'work/trees/v145_ozertuu_33170350'
V144 = ROOT / 'work/trees/v144_leotang_chem_refit'
SRC = pathlib.Path('/tmp/opencode/adjudicate/asteriospanoras__qcc-33-1702-ablation-floors-human-vs-ai-next/submission__extracted')
DST = ROOT / 'work/trees/v146_hybrid_dqi_chem'
TABLE = ROOT / 'work/sha_tables/sha_table_v146.txt'

NPZ_SRC_SHA = 'e7f08627208c'

REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
COST = {
    'invsqrt': Decimal('60927.57739905387'),
    'dqi': Decimal('305041647011.3978'),
    'dfthcsos': Decimal('251089557.46576697'),
}


def digest(path: pathlib.Path) -> tuple[str, int]:
    b = path.read_bytes()
    return hashlib.sha256(b).hexdigest(), len(b)


def main() -> int:
    if not SRC.is_dir():
        raise SystemExit('missing source candidate tree')
    if not digest(SRC / 'dfthcsos/submission.npz')[0].startswith(NPZ_SRC_SHA):
        raise SystemExit('source chemistry table SHA mismatch')

    if DST.exists():
        shutil.rmtree(DST)
    shutil.copytree(V145, DST)
    # DQI: v144's member, the one the official verifier accepted with 0/0 errors
    shutil.copyfile(V144 / 'dqi.kmb', DST / 'dqi.kmb')
    shutil.copyfile(SRC / 'dfthcsos/submission.npz', DST / 'dfthcsos/submission.npz')

    files = {}
    for p in sorted(x for x in DST.rglob('*') if x.is_file()):
        files[p.relative_to(DST).as_posix()] = list(digest(p))
    if len(files) != 18:
        raise SystemExit(f'expected exactly 18 files, got {len(files)}')

    changed = [rel for rel in files
               if digest(V145 / rel) != tuple(files[rel])]
    if sorted(changed) != ['dfthcsos/submission.npz', 'dqi.kmb']:
        raise SystemExit(f'expected only dqi+npz to change vs v145, got {changed}')
    if digest(DST / 'dqi.kmb') != digest(V144 / 'dqi.kmb'):
        raise SystemExit('v146 DQI must be v144\'s verifier-clean member')
    for p in (DST / 'dfthcsos').glob('angle_k_*.kmb'):
        if digest(p) != digest(V145 / 'dfthcsos' / p.name):
            raise SystemExit(f'loader differs from the v145/ozertuu loader: {p.name}')

    getcontext().prec = 60
    ratios = {k: REF[k] / COST[k] for k in REF}
    gm = (ratios['invsqrt'] * ratios['dqi'] * ratios['dfthcsos']) ** (Decimal(1) / Decimal(3))
    previous = Decimal('33.1439847224675759169083408104802578161029519713326461544372')
    table = {
        'tree': (
            'v146 hybrid = invsqrt bb676b95f94c unchanged + verifier-clean DQI '
            '4b5721411adc239f (0 value / 0 phase errors, moat-lab v58) + best '
            'measured chemistry table e7f08627208c on the shared 3,357-T loaders '
            '(official local PASS 251089557.46576697 @405q); predicted GM '
            + str(gm)
        ),
        'files': files,
    }
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    TABLE.write_text(json.dumps(table, indent=1) + '\n')
    print(f'built {DST}')
    print(f'changed vs v145: {changed}')
    print(f'predicted GM: {gm}  delta vs v144: {gm - previous:+}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
