#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v146."""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v145.generated.py'
OUT = ROOT / 'work/tools/build_moat_v146.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        ('v145_ozertuu_33170350', 'v146_hybrid_dqi_chem'),
        ('v145', 'v146'),
        ('V145', 'V146'),
        ('141f02ac69638c78', '4b5721411adc239f'),
        ('305,041,160,753.34', '305,041,647,011.3978'),
        ('05387b5d160fe2df', 'e7f08627208c'),
        ('251,089,557.508397', '251,089,557.46576697'),
        ('46.917982145460', '46.91798213749483'),
        ('public 33.170350 tree', 'public 33.170330 tree'),
        ('3,372-T loaders', '3,357-T loaders'),
        ('(T=13244, Q=405)', '(T=13214, Q=405)'),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v146_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
