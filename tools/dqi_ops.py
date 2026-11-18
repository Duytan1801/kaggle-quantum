#!/usr/bin/env python3
"""dqi_ops.py — op-code histogram and semantics probe for a kickmix .kmb.

Prints the histogram of op codes (low 7 bits; bit 7 = conditional) and, for the
rare codes, the first few decoded instances with their arguments.  Used to pin
down the binary encoding before writing a liveness analyser.

Usage: dqi_ops.py <file.kmb> [--examples N]
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from hw27_scan import unpack_views  # noqa: E402

NAMES = {
    0x10: 'X?', 0x11: 'Z?', 0x12: 'NEG?', 0x13: 'R?',
    0x20: 'SWAP?', 0x21: 'CX', 0x22: 'CZ', 0x23: '?',
    0x30: 'CSWAP?', 0x31: 'CCX', 0x32: 'CCZ', 0x33: '?',
    0x40: 'BIT_STORE0?', 0x41: 'BIT_STORE1?', 0x42: 'BIT_INVERT?', 0x43: '?',
    0x50: 'HMR',
}


def main():
    src = pathlib.Path(sys.argv[1])
    raw = src.read_bytes()
    h, regs, secs = unpack_views(raw)
    print('header (4I9Q):', h)
    print('sections:', {k: len(v) for k, v in sorted(secs.items())})
    ops = secs[1]
    base = ops & 127
    hist = Counter(base.tolist())
    print(f'{"code":>6} {"name":>12} {"count":>12} {"cond":>12}')
    for code, n in sorted(hist.items(), key=lambda kv: -kv[1]):
        cond = int(((ops & 128) != 0)[base == code].sum())
        print(f'0x{code:02x} {NAMES.get(code, "?"):>12} {n:>12,} {cond:>12,}')

    nex = 3
    if '--examples' in sys.argv:
        nex = int(sys.argv[sys.argv.index('--examples') + 1])
    # decode a few instances of each rare code with the prefix-indexed arg sections
    is1 = np.isin(base, [0x10, 0x11, 0x12, 0x13, 0x50])
    is2 = np.isin(base, [0x20, 0x21, 0x22, 0x23])
    is3 = np.isin(base, [0x30, 0x31, 0x32, 0x33])
    isb = np.isin(base, [0x40, 0x41, 0x42, 0x43, 0x50])
    p1 = np.concatenate([[0], np.cumsum(is1)])
    p2 = np.concatenate([[0], np.cumsum(is2)])
    p3 = np.concatenate([[0], np.cumsum(is3)])
    pb = np.concatenate([[0], np.cumsum(isb)])
    for code in sorted(hist):
        idx = np.flatnonzero(base == code)[:nex]
        if len(idx) == 0:
            continue
        print(f'--- examples of 0x{code:02x} ({NAMES.get(code, "?")}):')
        for i in idx.tolist():
            parts = [f'op=0x{ops[i]:02x}']
            if is1[i]:
                parts.append(f'a1={int(secs[7][p1[i + 1] - 1])}')
            if is2[i]:
                parts.append(f'a2={int(secs[5][p2[i + 1] - 1])}')
                parts.append(f't2={int(secs[6][p2[i + 1] - 1])}')
            if is3[i]:
                parts.append(f'a3={int(secs[2][p3[i + 1] - 1])}')
                parts.append(f'b3={int(secs[3][p3[i + 1] - 1])}')
                parts.append(f't3={int(secs[4][p3[i + 1] - 1])}')
            if isb[i]:
                parts.append(f'cb={int(secs[8][pb[i + 1] - 1])}')
            print('   ', ' '.join(parts))


if __name__ == '__main__':
    main()
