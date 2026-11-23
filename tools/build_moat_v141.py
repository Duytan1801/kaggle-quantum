#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v141.

v141 is the v140 Apache-inverse-sqrt tree with GoodpJW's newly measured
chemistry table.  This builder reuses the mechanically tested v140 notebook
builder and changes only versioned identifiers, the v141 SHA table/snapshot
dataset, and the chemistry description.  The resulting notebook remains
fail-closed: it checks all 18 hashes, runs the unchanged official invsqrt,
DQI, and chemistry verifiers, rejects DQI shot errors, and emits
V141-RECEIPT-PASS only if every leg passes.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v140.generated.py'
OUT = ROOT / 'work/tools/build_moat_v141.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        ('build_moat_v140.py', 'build_moat_v141.py'),
        ('v140', 'v141'),
        ('V140', 'V141'),
        ('b3683e07cf033989 + 15 T7421 loaders',
         'baa8b2966e889ef6 + 15 3,372-T loaders'),
        ('251,692,077.714951 (405 q, lambda_eff 46.92403505616352)',
         '251,692,071.475490 (405 q, lambda_eff 46.92403389291401)'),
        ('Apache invsqrt + Leo T7421 tree',
         'Apache invsqrt + GoodpJW chemistry tree'),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v141_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
