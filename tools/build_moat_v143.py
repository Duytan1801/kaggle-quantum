#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v143."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v142.generated.py'
OUT = ROOT / 'work/tools/build_moat_v143.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        ('v142_apache_invsqrt_leotang_t7421',
         'v143_three_t_phase_leotang_t7421'),
        ('v142', 'v143'),
        ('V142', 'V143'),
        ('52e8d4e6649b30ff', 'bb676b95f94c923c'),
        ('60,955.29842169718', '60,927.57739905387'),
        ('public 33.13882 tree', 'public 33.14392 tree'),
        ('Apache invsqrt + Leo Tang chemistry tree',
         'three-T phase compiler + Leo Tang chemistry tree'),
        ('import glob, hashlib, json, os, subprocess, sys, time',
         'import glob, hashlib, json, os, shutil, subprocess, sys, time'),
        ("""chem_root = root / 'dfthcsos'
if not chem_root.is_dir():
    idx = next((p.parent for r, p in paths.items() if r.endswith('angle_k_0.kmb')), None)
    if idx is None:
        raise SystemExit('dfthcsos directory not found')
    chem_root = idx
log('chem dir:', chem_root, sorted(p.name for p in chem_root.iterdir())[:4])""",
         """chem_root = root / 'dfthcsos'
if not chem_root.is_dir():
    # Kaggle's current dataset CLI may flatten the chemistry directory.
    # Materialize the verifier's required angle_k_*.kmb names locally.
    chem_root = Path('/kaggle/working') / 'dfthcsos_v143'
    chem_root.mkdir(parents=True, exist_ok=True)
    copied = 0
    for rel, src in paths.items():
        if rel.startswith('dfthcsos/'):
            shutil.copyfile(src, chem_root / Path(rel).name)
            copied += 1
    if copied != 16:
        raise SystemExit(f'expected 16 chemistry files, copied {copied}')
log('chem dir:', chem_root, sorted(p.name for p in chem_root.iterdir())[:4])"""),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v143_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
