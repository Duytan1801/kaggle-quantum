#!/usr/bin/env python3
"""chem_oldload.py -- dissect the five OLD chemistry loaders (k=0,1,5,7,11).

The ten re-solved loaders (goodpjw2008's v2) cost 205-215 Toffolis each;
the five that were left alone cost 240-245.  They are maoxin123's older
style: "4 classical bits + conditioned CZ/Z".

This tool parses a .kmb file and classifies every Toffoli-like op:
  * CACHE  -- target is an ancilla (q >= 46): one cached feature AND,
  * PRODUCT -- target is a word register (q in 11..45): a product applied
    to one or more output bits,
and counts the measurements (HMR) and the conditioned phase (CZ) ops, so we
can see whether the old loaders' extra cost is
  (a) more products (a bigger plan), or
  (b) the same plan emitted in a more expensive style.

Usage: chem_oldload.py <file.kmb> [...]
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import kmb_opt as KO  # noqa: E402

CCX = 0x31
CZ = 0x61  # guess; the real opcode is resolved below


def decode(path):
    raw = pathlib.Path(path).read_bytes()
    k = KO.parse_raw_kmb(raw)
    hdr = KO.decode_header(k) if hasattr(KO, 'decode_header') else None
    return KO.decode_instructions(k)


def main() -> int:
    for path in sys.argv[1:]:
        g = decode(path)
        hist = Counter(op & 127 for op, cond, a, r in g)
        ccz = [o for o in hist if o not in (0x00, 0x10, 0x11, 0x12, 0x13, 0x20,
                                           0x21, 0x22, 0x30, 0x31, 0x32,
                                           0x40, 0x41, 0x42, 0x50)]
        print(f'=== {pathlib.Path(path).name}: {len(g)} instructions')
        print(f'    opcodes: {dict(sorted(hist.items()))}')
        print(f'    unknown opcodes (possible CZ/CCZ): {[hex(o) for o in ccz]}')

        tof = [(op, cond, a, r) for op, cond, a, r in g if (op & 127) == 0x31]
        byt = Counter(a[2] for op, cond, a, r in tof)
        anc = [t for t in byt if t >= 46]
        wrd = [t for t in byt if 11 <= t < 46]
        sel = [t for t in byt if t < 11]
        print(f'    Toffolis {len(tof)}: targets ancilla={len(anc)} '
              f'(hits {sum(byt[t] for t in anc)}), word={len(wrd)} '
              f'(hits {sum(byt[t] for t in wrd)}), selection={len(sel)}')
        print(f'    word-target multiplicities: '
              f'{dict(sorted((t, byt[t]) for t in wrd))}')
        # measurements
        hmr = [(op, cond, a, r) for op, cond, a, r in g if (op & 127) == 0x50]
        print(f'    HMR {len(hmr)}: targets '
              f'{dict(Counter(a[0] for op, cond, a, r in hmr).most_common(8))}')
        # how many CZ ops and where
        cz = [(op, cond, a, r) for op, cond, a, r in g if (op & 127) in (0x60, 0x61, 0x62)]
        if cz:
            print(f'    CZ-like {len(cz)}: {dict(Counter(op & 127 for op, *_ in cz))} '
                  f'targets {dict(Counter(a[1] for op, cond, a, r in cz).most_common(5))}')
        # print a window of the ops around the first word-target Toffoli
        idx = next((i for i, (op, cond, a, r) in enumerate(g)
                    if (op & 127) == 0x31 and 11 <= a[2] < 46), None)
        if idx is not None:
            lo = max(0, idx - 14)
            print('    --- window before the first product Toffoli ---')
            for i in range(lo, min(len(g), idx + 6)):
                op, cond, a, r = g[i]
                print(f'      {i:6d}: op={op & 127:#04x} cond={cond} a={a} r={r}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
