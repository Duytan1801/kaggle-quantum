#!/usr/bin/env python3
"""probe_chain.py — dump wire values around a chain/repair block using QHDL's bitsim.

Usage: probe_chain.py <circuit.kmx> <start> <end> [x_value]
Prints, at every op in [start,end), the op and the values of the interesting wires
for a single concrete x (bit-packed rows are unpacked for one row).
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, '/tmp/opencode/recon/datasets/vqcc-tools-0.1.0/scripts')
import numpy as np
import qhdl_bitsim as B


def main() -> None:
    path = pathlib.Path(sys.argv[1])
    start, end = int(sys.argv[2]), int(sys.argv[3])
    xval = int(sys.argv[4]) if len(sys.argv) > 4 else 0b1010101010101010101011
    ops, header, xq, nq = B.load(str(path))
    print('ops:', len(ops), 'nq:', nq, 'xq:', xq[:5], '...')
    watch = [12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 30, 35, 37, 38, 39, 40, 41, 42, 43, 4, 3, 0, 1, 2, 5]
    sim = B.BitSim(ops, rows=np.array([xval], dtype=np.int64), num_qubits=nq,
                   x_qubits=list(xq), outcome='zero')

    def snap(i, s):
        vals = {q: int((s.q[q][0] & 1)) for q in watch}
        live = ' '.join(f'q{q}={vals[q]}' for q in watch)
        print(f'{i:6d} {ops[i].text if hasattr(ops[i], "text") else ops[i].kind:<18} {live}')

    sim.run(stop=end, snaps=list(range(start, end)), on_snap=snap)
    print('sign (phase parity):', int(sim.sign[0] & 1))


if __name__ == '__main__':
    main()
