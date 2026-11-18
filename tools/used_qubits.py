#!/usr/bin/env python3
"""used_qubits.py — which qubit ids does a DQI .kmb actually touch?

If some ancilla wires (ids >= the syndrome set) are never used by any operand,
the file can be renumbered to a smaller num_qubits: the DQI score is
rep * Q^2 * T, so every removed qubit shrinks the cost quadratically.

Usage: used_qubits.py FILE.kmb
"""
import sys
import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb


def main(path):
    k = Kmb(path)
    print('file:', path)
    print(' counts:', k.counts)
    with open(path, 'rb') as f:
        head = f.read(104)
    import struct
    version, nq, nb, nreg, nops = struct.unpack('<IIIIQ', head[16:40])
    print(f' header: version={version} num_qubits={nq} num_bits={nb} nreg={nreg} nops={nops}')

    used = np.zeros(nq, dtype=bool)
    who = {c: [] for c in range(1, 12)}

    def scan(col, label, step=4):
        raw = k.read_col(col)
        if not raw:
            return
        arr = np.frombuffer(raw, dtype=np.uint32)
        arr = arr[arr < nq]
        if len(arr):
            used[arr] = True
            who[col].append((label, len(arr), int(arr.min()), int(arr.max())))

    scan(2, 'qqq0')
    scan(3, 'qqq1')
    scan(4, 'qqq2')
    scan(5, 'qqq0(2q)')
    scan(6, 'qqq1(2q)')
    scan(7, 'q0(1q)')
    # col8 = b0 (classical bits) -> not qubits; col9 = bc (condition bits) -> not qubits
    print(' qubit ids referenced per column:')
    for c, rows in who.items():
        if rows:
            print(f'   col{c}: {rows}')

    free = np.flatnonzero(~used)
    print(f'\n unused qubit ids: {len(free)}')
    if len(free):
        print('  list:', free.tolist()[:80])
        # syndrome qubits are 0..839? check with register data
        print(f'  unused below 840: {int((free < 840).sum())}   unused >= 840: {int((free >= 840).sum())}')
    usedids = np.flatnonzero(used)
    print(f' used qubits: {len(usedids)}  (max id {usedids.max() if len(usedids) else -1})')

    # register data -> which ids belong to S registers
    with open(path, 'rb') as f:
        pos = 104
        regs = []
        for _ in range(nreg):
            ptype, plen = struct.unpack('<QQ', f.read(16))
            nl, rl = struct.unpack('<II', f.read(8))
            name = f.read(nl).decode()
            ids = np.frombuffer(f.read(4 * rl), dtype=np.uint32)
            f.seek(plen - 8 - nl - 4 * rl, 1)
            regs.append((name, ids))
    sq = set()
    for name, ids in regs:
        if name.startswith('S'):
            for i in ids:
                if i & (1 << 31):
                    sq.add(i & ~(1 << 31))
    print(f'\n syndrome qubit ids from registers: {len(sq)} (min {min(sq)}, max {max(sq)})')
    anc = np.array(sorted(set(range(nq)) - sq))
    print(f' ancilla ids: {len(anc)}  -> {anc.tolist()[:60]}')
    unused_anc = [q for q in anc if not used[q]]
    print(f' UNUSED ancillas: {len(unused_anc)} -> {unused_anc}')
    # also: syndrome qubits that are never touched
    unused_syn = [q for q in sorted(sq) if not used[q]]
    print(f' unused syndrome qubits: {len(unused_syn)}')


if __name__ == '__main__':
    main(sys.argv[1])
