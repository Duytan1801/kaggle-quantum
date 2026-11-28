#!/usr/bin/env python3
"""chem_bankrank.py -- the structural obstruction behind the group-start loaders.

goodpjw2008's method note (v21 notebook) says a normal loader's delta has the
form

    D_o(bank, low) = sum_products  c(bank) . q(low)

with only **68 bank functions** c (fits in the 82 ancillas), while the
group-start loaders (batches 0,1,5,7,11) need **143 bank functions**, more than
the ancillas can hold, which is why they slide and cost 240 Toffolis.

This tool measures that quantity exactly: for each loader k, the GF(2) rank of
the set of bank functions { D_o(., low) : o in outputs, low in generic columns }.
That rank is the number of distinct bank directions the loader must realise,
so it is a lower bound on the number of cached bank features.

Usage: chem_bankrank.py <tree> [k ...]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219
ADDR = CE.ADDR
BANK = ADDR >> 4
NBANK = 76            # the notebook counts "all 76 banks"; bank 76 is partial
OUTS = [o for o in range(35) if o % 7 != 6]


def bank_rank(tree, k):
    z = np.load(pathlib.Path(tree) / 'submission.npz')
    W = np.asarray(z['angle_words'])
    rows = []
    for o in OUTS:
        j, i = divmod(o, 7)
        col = 5 * k + j
        bit = ((W[:, col] >> i) & 1).astype(bool)
        prev = np.zeros(NV, bool) if k == 0 else ((W[:, col - 5] >> i) & 1).astype(bool)
        d = bit ^ prev
        for low in range(16):
            rows.append(d[(np.arange(NBANK) * 16) + low])
    M = np.asarray(rows, dtype=np.uint8)
    # GF(2) rank via Gaussian elimination on uint64 rows
    piv = {}
    for r in M:
        v = int.from_bytes(np.packbits(r, bitorder='little').tobytes(), 'little')
        while v:
            b = v.bit_length() - 1
            if b in piv:
                v ^= piv[b]
            else:
                piv[b] = v
                break
    # also: rank of only the 14 generic columns (drop the 2 special ones,
    # which are columns with the most dead words)
    return len(piv), M


def main() -> int:
    tree = sys.argv[1]
    ks = [int(a) for a in sys.argv[2:]] or list(range(15))
    print(f'{"k":>3} {"bank rank (all 16 cols)":>24} {"distinct bank fns":>18}')
    for k in ks:
        r, M = bank_rank(tree, k)
        print(f'{k:3d} {r:24d} {len({tuple(x) for x in M}):18d}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
