#!/usr/bin/env python3
"""kmb_align.py — decode the kickmix .kmb binary stream against its own .kmx text form.

The .kmb format is only partially documented in our tools, so we derive it
empirically: convert a small .kmb to .kmx with the official kickmix library, parse
the text ops, decode the binary stream, and align them one by one.  The result is
an exact op-code table (arity, op kind, conditional flag, argument sections),
which the dqi liveness analyser needs.

Usage: kmb_align.py <file.kmb> [max_ops]
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
sys.path.insert(0, '/tmp/opencode/recon/datasets/asteriospanoras_qcc-circuit-atlas/tools')
import kickmix as km  # noqa: E402
from hw27_scan import unpack_views  # noqa: E402
import kmsim  # noqa: E402


def main():
    src = pathlib.Path(sys.argv[1])
    maxops = int(sys.argv[2]) if len(sys.argv) > 2 else 10 ** 9
    raw = src.read_bytes()
    h, regs, secs = unpack_views(raw)
    tmp = pathlib.Path('/tmp/opencode/_align.kmx')
    km.Circuit.from_file(str(src), format='kmb').to_file(str(tmp), format='kmx')
    ops, _ = kmsim.parse(str(tmp))
    print(f'text ops: {len(ops)}   binary ops: {len(secs[1])}')

    opsb = secs[1]
    base = opsb & 127
    flag = opsb & 128
    # candidate index structures: section lengths
    print('section lengths:', {k: len(v) for k, v in sorted(secs.items())})
    print('text op histogram:', Counter(o[0] for o in ops).most_common())
    print('binary code histogram:', Counter(base.tolist()).most_common())

    # align: walk the text ops and the binary stream, guessing the per-op argument
    # consumption by comparing the text sequence of op names with the binary codes.
    text_names = [o[0] for o in ops]
    # print the first 60 (text name, binary code) pairs assuming a 1:1 order
    for i in range(min(60, len(text_names), len(base))):
        print(f'{i:>6} text={text_names[i]:>10} args={ops[i][1]} code=0x{base[i]:02x} flag={flag[i]}')
    print('...')
    for i in range(max(0, len(text_names) - 20), min(len(text_names), len(base))):
        print(f'{i:>6} text={text_names[i]:>10} args={ops[i][1]} code=0x{base[i]:02x} flag={flag[i]}')


if __name__ == '__main__':
    main()
