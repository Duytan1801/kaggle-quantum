#!/usr/bin/env python3
"""Build the moat-lab in-kernel official-verifier receipt for v147.

v147 = the first tree that beats our v146 (33.17029) on the public board:

  invsqrt   bb676b95f94c923c   60,927.57739905387   (37 q, unchanged from v146)
  dqi       6f78ecdd636051d4   ~305,032,962,722.6  (900 q)
  dfthcsos  npz 16b4f5b5e51b0777 + the 15 byte-identical 3,357-T loaders
            251,089,557.02151904 (405 q, lambda_eff 46.917982054483744)

The DQI member is goodpjw2008's `qcc-dqi-zero-test-cuts-lb-33-17067` release:
tonylica's `4b572141` with TEN gate rewrites —

  * evgendvorkin's  `CCZ q103 q54 q163` -> `CZ q103 q54`      (-0.50 Toffoli/shot)
  * ozertuu's       delete `CCZ q63 q507 q204 if b49140`      (-0.50 Toffoli/shot)
  * goodpjw2008's   `CCX a b t` -> `CX a t` at positions 17-24 of a 24-bit
                    zero test                               (-8.00 Toffoli/shot)

measured by the OFFICIAL verifier on the same 102,400 shots for both files
(seed 777): 316,133.13 -> 316,124.13 Toffolis per shot.  The chemistry table is
varianceofx's `vqcc-verified-3357-loader-portfolio`, the cheapest public table
measured so far (251,089,557.02151904 vs our v146's 251,089,557.46576697).

The builder is deliberately defensive about the dataset layout and about verifier
CLIs, and it never invents a verdict: every leg must come back PASS from a
parsed JSON block, and the DQI leg must have 0 value / 0 phase errors.

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import pathlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TEMPLATE = ROOT / 'work/tools/build_moat_v146.generated.py'
OUT = ROOT / 'work/tools/build_moat_v147.generated.py'


def main() -> int:
    src = TEMPLATE.read_text()
    replacements = (
        # identity / anchors first
        ('v146_hybrid_dqi_chem', 'v147_zero_test_dqi_vox_chem'),
        ('sha_table_v146.txt', 'sha_table_v147.txt'),
        ('kernel_moat_v146', 'kernel_moat_v147'),
        ('qcc-release-v146', 'qcc-release-v147'),
        # the DQI member
        ('4b5721411adc239f', '6f78ecdd636051d4'),
        ('305,041,647,011.3978', '305,032,962,722.61'),
        ('(0 value / 0 phase errors)', '(0 value / 0 phase errors)'),
        # the chemistry member
        ('e7f08627208c', '16b4f5b5e51b0777'),
        ('251,089,557.46576697', '251,089,557.02151904'),
        ('46.91798213749483', '46.917982054483744'),
        # prose
        ('public 33.170330 tree', 'public 33.17060 tree'),
        ('3,357-T loaders', '3,357-T loaders'),
        ('(T=13214, Q=405)', '(T=13214, Q=405)'),
    )
    for old, new in replacements:
        if old not in src:
            raise RuntimeError(f'template marker missing: {old!r}')
        src = src.replace(old, new)
    src = src.replace('v146', 'v147').replace('V146', 'V147')
    OUT.write_text(src)

    ns = {'__name__': 'build_moat_v147_generated', '__file__': str(OUT)}
    exec(compile(src, str(OUT), 'exec'), ns)
    ns['main']()
    print(f'generated template: {OUT}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
