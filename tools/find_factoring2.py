#!/usr/bin/env python3
"""find_factoring2.py — locate shared-control factoring windows in a DQI .kmb (correct streams).

.kmb instruction stream (kickmix):
  col1  types          : one opcode byte per instruction
  col2/3/4 qqq0/1/2    : uint32 per 3-qubit instruction (CCX 0x31, CCZ 0x30, CSWAP 0x32)
  col5/6 qq0/qq1      : uint32 per 2-qubit instruction (CZ 0x20, CX 0x21, SWAP 0x22)
  col7 q0, col8 b0, col9 bc, col10/11 angles

Toffoli-like ops = the 3-qubit instructions (counts[1]).

Factoring identity (thomasgamet's exact column-stream patch):
  OLD  36 consecutive CCX, three groups of 12:
         gA: CCX(A, B+k, C+k)   gD: CCX(D, B+k, C+k)   gE: CCX(E, B+k, C+k)   k=0..11
  NEW  60 instructions, 12 CCX + 48 CX:
         per k: CX(E->A); CX(D->A); CCX(B+k, A, C+k); CX(D->A); CX(E->A)
  because C+k receives (B+k) & (A xor D xor E) either way.
"""
import sys
import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb

CCX = 0x31
CX = 0x21


def load3q(path):
    k = Kmb(path)
    types = k.read_col(1, np.uint8)
    is3 = (types & 0x30) == 0x30
    tri_pos = np.flatnonzero(is3)                 # instruction index of each 3-qubit op
    tri_type = types[tri_pos]
    q0 = k.read_col(2, np.uint32)
    q1 = k.read_col(3, np.uint32)
    q2 = k.read_col(4, np.uint32)
    return k, types, tri_pos, tri_type, q0, q1, q2


def runs_of(tri_pos):
    """maximal runs of 3-qubit instructions contiguous in the instruction stream"""
    if len(tri_pos) == 0:
        return []
    d = np.diff(tri_pos)
    brk = np.flatnonzero(d != 1)
    starts = np.concatenate(([0], brk + 1))
    ends = np.concatenate((brk, [len(tri_pos) - 1]))
    return [(int(s), int(e)) for s, e in zip(starts, ends) if e > s]


def find_shared_control(tri_pos, tri_type, q0, q1, q2, m=12, groups=3):
    """windows of 3*m consecutive CCX with the m x groups shared-control shape"""
    hits = []
    ar = np.arange(m)
    for s, e in runs_of(tri_pos):
        L = e - s + 1
        if L < m * groups:
            continue
        for j in range(s, e - m * groups + 2):
            if not (tri_type[j:j + m * groups] == CCX).all():
                continue
            g0 = []
            ok = True
            for gi in range(groups):
                idx = np.arange(j + m * gi, j + m * gi + m)
                av, bv, cv = q0[idx], q1[idx], q2[idx]
                if not (av == av[0]).all() or not (bv == bv[0] + ar).all() or not (cv == cv[0] + ar).all():
                    ok = False
                    break
                g0.append((int(av[0]), int(bv[0]), int(cv[0])))
            if not ok:
                continue
            if len({g[0] for g in g0}) != groups:
                continue
            if any(g[1:] != g0[0][1:] for g in g0):
                continue
            A, B, C = g0[0]
            D, E = g0[1][0], g0[2][0]
            wires = [A, D, E] + [B + t for t in range(m)] + [C + t for t in range(m)]
            if len(set(wires)) != len(wires):
                continue
            hits.append({'tri': j, 'instr': int(tri_pos[j]), 'A': A, 'D': D, 'E': E,
                         'B': B, 'C': C, 'm': m, 'saving': m * (groups - 1)})
    return hits


if __name__ == '__main__':
    path = sys.argv[1]
    k, types, tri_pos, tri_type, q0, q1, q2 = load3q(path)
    print('file:', path)
    print(' counts:', k.counts)
    print(' instructions:', len(types), ' 3-qubit:', len(tri_pos),
          ' CCX:', int((tri_type == CCX).sum()), ' CCZ:', int((tri_type == 0x30).sum()),
          ' CSWAP:', int((tri_type == 0x32).sum()))
    rs = runs_of(tri_pos)
    rs.sort(key=lambda r: -(r[1] - r[0]))
    print(' contiguous 3q runs: %d (longest %d)' % (len(rs), rs[0][1] - rs[0][0] + 1 if rs else 0))
    for m in (12, 8, 6, 4, 3, 2):
        h = find_shared_control(tri_pos, tri_type, q0, q1, q2, m=m)
        if h:
            print(' m=%d -> %d windows' % (m, len(h)))
            for x in h:
                print('    instr=%d tri=%d  A=%d D=%d E=%d  B=%d..%d C=%d..%d saving=%d'
                      % (x['instr'], x['tri'], x['A'], x['D'], x['E'], x['B'], x['B'] + m - 1,
                         x['C'], x['C'] + m - 1, x['saving']))
