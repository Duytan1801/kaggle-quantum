#!/usr/bin/env python3
"""chem_oldops.py -- dump the op structure of an old chemistry loader.

The five old loaders (k = 0,1,5,7,11) cost 240-245 Toffolis while the ten
re-solved ones cost 205-215.  This tool prints the .kmx text of a loader
(the unambiguous view: the binary opcodes have several operand-order
variants) and classifies the Toffolis.

Usage: chem_oldops.py <file.kmb> [--window N] [--at N]
"""
from __future__ import annotations

import io
import pathlib
import sys
from collections import Counter

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
import kickmix as km  # noqa: E402


def to_kmx(path):
    c = km.Circuit.from_file(str(path), 'kmb')
    buf = io.BytesIO()
    c.to_file(buf, format='kmx')
    return buf.getvalue().decode().splitlines()


def main() -> int:
    path = pathlib.Path(sys.argv[1])
    window = 30
    at = None
    for i, a in enumerate(sys.argv):
        if a == '--window':
            window = int(sys.argv[i + 1])
        if a == '--at':
            at = int(sys.argv[i + 1])
    lines = to_kmx(path)
    hdr = [l for l in lines if l.startswith('REGISTER') or l.startswith('APPEND_TO')]
    ops = []
    for l in lines:
        t = l.split()
        if not t or t[0] in ('REGISTER', 'APPEND_TO_REGISTER'):
            continue
        ops.append(l)
    print(f'=== {path.name}: {len(ops)} ops')
    hist = Counter(o.split()[0] for o in ops)
    print(f'    histogram: {dict(hist)}')
    cond = [o for o in ops if ' if ' in o]
    print(f'    conditioned ops: {len(cond)}  e.g. {cond[:4]}')
    ccx = [o for o in ops if o.startswith('CCX') or o.startswith('CCZ')]
    tof = [o for o in ccx if ' if ' not in o]
    ctof = [o for o in ccx if ' if ' in o]
    print(f'    CCX unconditional {len(tof)}, conditioned {len(ctof)}')
    tgt = Counter()
    for o in tof:
        q = o.split()
        tgt[q[4]] += 1
    print(f'    unconditional CCX targets: {dict(Counter(tgt.values()))}')
    print(f'    distinct unconditional targets: {len(tgt)}')
    if at is None:
        # show the first conditioned op and a window around it
        idx = next((i for i, o in enumerate(ops) if ' if ' in o and o.startswith('CCX')), None)
        if idx is None:
            idx = next((i for i, o in enumerate(ops) if o.startswith('CCX')), 0)
    else:
        idx = at
    lo = max(0, idx - window)
    print(f'    --- window at op {idx} ---')
    for i in range(lo, min(len(ops), idx + window)):
        print(f'      {i:6d}: {ops[i]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
