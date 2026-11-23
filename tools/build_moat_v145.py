#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v145."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v144.generated.py'
OUT = ROOT / 'work/tools/build_moat_v145.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        ('v144_three_t_phase_latest_leotang_chem', 'v145_ozertuu_33170350'),
        ('v144', 'v145'),
        ('V144', 'V145'),
        ('4b5721411adc239f', '141f02ac69638c78'),
        ('305,041,647,011.3978', '305,041,160,753.34'),
        ('fd02c7f730b024a1', '05387b5d160fe2df'),
        ('251,688,794.860736', '251,089,557.508397'),
        ('46.923423019552565', '46.917982145460'),
        ('public 33.14398 tree', 'public 33.170350 tree'),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v145_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
