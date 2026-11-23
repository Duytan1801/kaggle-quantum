#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v140.

This reuses the mechanically tested v139 notebook builder, changing only the
versioned identifiers, the v140 SHA table, snapshot dataset, and inverse-sqrt
description.  The generated notebook itself remains fail-closed: it checks all
18 member hashes, runs the unchanged official invsqrt/DQI/chemistry verifiers,
rejects DQI shot errors, and emits V140-RECEIPT-PASS only if every leg passes.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v139.py'
OUT = ROOT / 'work/tools/build_moat_v140.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        ('build_moat_v139.py', 'build_moat_v140.py'),
        ('v139', 'v140'),
        ('V139', 'V140'),
        ('d2148a7cd7a4d0a0', '52e8d4e6649b30ff'),
        ('60,955.32670759028', '60,955.29842169718'),
        ('leotang09/vqcc-t7421-submission', 'Apache public-circuits v170'),
        ('leotang09 T7421 kernel output', 'Apache invsqrt + Leo T7421 tree'),
        ('public_leotang_t7421_33_13881', 'apache_invsqrt_leotang_t7421'),
        ('public 33.13881 tree', 'public 33.13882 tree'),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v140_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
