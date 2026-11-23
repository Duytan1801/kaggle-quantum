#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v142.

v142 is the v141 Apache-inverse-sqrt tree with Leo Tang's newly measured
chemistry table.  This builder reuses the mechanically tested v141 notebook
builder and changes only versioned identifiers, the v142 SHA table/snapshot
dataset, and the chemistry description.  The resulting notebook remains
fail-closed: it checks all 18 hashes, runs the unchanged official invsqrt,
DQI, and chemistry verifiers, rejects DQI shot errors, and emits
V142-RECEIPT-PASS only if every leg passes.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v141.generated.py'
OUT = ROOT / 'work/tools/build_moat_v142.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        ('build_moat_v141.py', 'build_moat_v142.py'),
        ('v141', 'v142'),
        ('V141', 'V142'),
        ('baa8b2966e889ef6 + 15 3,372-T loaders',
         '0d4459fbd3d517c4 + 15 3,372-T loaders'),
        ('251,692,071.475490 (405 q, lambda_eff 46.92403389291401)',
         '251,690,221.895943 (405 q, lambda_eff 46.923689067855136)'),
        ('Apache invsqrt + GoodpJW chemistry tree',
         'Apache invsqrt + Leo Tang chemistry tree'),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v142_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
