#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v144."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v143.generated.py'
OUT = ROOT / 'work/tools/build_moat_v144.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        ('v143_three_t_phase_leotang_t7421',
         'v144_three_t_phase_latest_leotang_chem'),
        ('v143', 'v144'),
        ('V143', 'V144'),
        ('0d4459fbd3d517c4', 'fd02c7f730b024a1'),
        ('251,690,221.895943', '251,688,794.860736'),
        ('46.923689067855136', '46.923423019552565'),
        ('public 33.14392 tree', 'public 33.14398 tree'),
        ('three-T phase compiler + Leo Tang chemistry tree',
         'three-T phase compiler + latest Leo Tang chemistry tree'),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v144_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
