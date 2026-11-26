#!/usr/bin/env python3
"""kmb_mix.py -- the gate mix and the rewrite opportunity of a .kmb file.

Reports the opcode histogram and, for the Toffoli-like ops, the structure
that the exact peephole rewrites need:

  * how many Toffolis share the SAME target (the "same target + one shared
    control" rule turns 2 Toffolis into 1),
  * how many pairs are ADJACENT modulo commuting gates (the rule only fires
    on such pairs),
  * the number of measurements with a target-only op right before them (the
    "measure-first" rule).
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kmb_opt as KO                                      # noqa: E402

NAMES = {0x00: 'NOP', 0x01: '?', 0x06: '?', 0x10: 'X', 0x11: 'X',
         0x12: 'X?', 0x13: 'ROT', 0x20: 'CX', 0x21: 'CX', 0x22: 'CX?',
         0x30: 'CCX', 0x31: 'CCX', 0x32: 'CCX?',
         0x40: 'M', 0x41: 'M', 0x42: 'M', 0x50: 'HMR'}


def main() -> int:
    for path in sys.argv[1:]:
        p = pathlib.Path(path)
        raw = p.read_bytes()
        k = KO.parse_raw_kmb(raw)
        g = KO.decode_instructions(k)
        hist = Counter(h[0] & 127 for h in g)
        magic = sum(hist[o] for o in KO.MAGIC_OPS)
        print(f'=== {p.name}: {len(g)} instructions, magic(Toffoli-like)={magic}')
        print('    ' + '  '.join(f'{NAMES.get(o, hex(o))}={hist[o]}'
                                for o in sorted(hist)))
        # same-target analysis
        by_target = Counter()
        for op, cond, a, r in g:
            if (op & 127) == 0x31:
                by_target[a[2]] += 1
        rep = Counter(by_target.values())
        print(f'    Toffolis: {sum(by_target.values())} on '
              f'{len(by_target)} distinct targets; multiplicity {dict(sorted(rep.items()))}')
        # adjacent-pair opportunities (the pair rule)
        opp = 0
        for i in range(len(g) - 1):
            p0 = KO.pair(g[i], g[i + 1])
            if p0 is not None:
                opp += 1
        # window opportunities
        opp48 = 0
        for i in range(len(g)):
            if (g[i][0] & 127) != 0x31:
                continue
            for j in range(i + 1, min(len(g), i + 49)):
                if KO.rw(g[j]) is None:
                    break
                if KO.pair(g[i], g[j]) is not None:
                    opp48 += 1
                    break
        print(f'    pair-rule opportunities: adjacent={opp}, window48={opp48}')
        # measurement opportunities
        meas = sum(1 for h in g if (h[0] & 127) == 0x50)
        print(f'    measurements: {meas}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
