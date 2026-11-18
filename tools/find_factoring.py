#!/usr/bin/env python3
"""find_factoring.py — locate shared-control factoring windows in a DQI .kmb.

The factoring identity (thomasgamet's exact column-stream patch):

  OLD (36 consecutive type-49 ops, three groups of 12):
      group A: for k in 0..11:  CCX(A, B+k, C+k)
      group D: for k in 0..11:  CCX(D, B+k, C+k)
      group E: for k in 0..11:  CCX(E, B+k, C+k)
  NEW (60 ops, 12 Toffolis + 48 CX):
      for k in 0..11:  CX(E->A); CX(D->A); CCX(B+k, A, C+k); CX(D->A); CX(E->A)

because C+k receives (B+k) & (A xor D xor E) either way.  36 Toffolis -> 12.

A second shape (thomas' chain-1 plans, 14 -> 16 ops) is detected as well.

Usage: find_factoring.py FILE.kmb [--dump]
"""
import sys
import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb

T49 = 49
T33 = 33


def load(path):
    k = Kmb(path)
    types = k.read_col(1, np.uint8)
    pos49 = np.flatnonzero(types == T49)
    a = k.read_col(2, np.uint32)
    b = k.read_col(3, np.uint32)
    c = k.read_col(4, np.uint32)
    return k, types, pos49, a, b, c


def contiguous_runs(pos):
    """maximal runs of type-49 ops that are also contiguous in the op stream"""
    if len(pos) == 0:
        return []
    d = np.diff(pos)
    brk = np.flatnonzero(d != 1)
    starts = np.concatenate(([0], brk + 1))
    ends = np.concatenate((brk, [len(pos) - 1]))
    return [(int(s), int(e)) for s, e in zip(starts, ends) if e > s]


def find36(pos49, a, b, c):
    """windows of 36 contiguous type-49 ops with the 3-group shape"""
    hits = []
    for s, e in contiguous_runs(pos49):
        L = e - s + 1
        for j in range(s, e - 35 + 1):
            ok = True
            groups = []
            for gi in range(3):
                idx = np.arange(j + 12 * gi, j + 12 * gi + 12)
                av = a[idx]
                bv = b[idx]
                cv = c[idx]
                if not (av == av[0]).all():
                    ok = False
                    break
                if not (bv == bv[0] + np.arange(12)).all():
                    ok = False
                    break
                if not (cv == cv[0] + np.arange(12)).all():
                    ok = False
                    break
                groups.append((int(av[0]), int(bv[0]), int(cv[0])))
            if not ok:
                continue
            A, B, C = groups[0]
            D = groups[1][0]
            E = groups[2][0]
            if len({A, D, E}) != 3:
                continue
            if groups[1][1:] != groups[0][1:] or groups[2][1:] != groups[0][1:]:
                continue
            hits.append({'j': j, 'A': A, 'B': B, 'C': C, 'D': D, 'E': E,
                         'op_start': int(pos49[j]), 'n': 12})
    return hits


def find14(pos49, a, b, c):
    """thomas' chain-1 shape: 14 consecutive type-49 ops -> 16 ops (2 Toffolis saved)"""
    hits = []
    for s, e in contiguous_runs(pos49):
        for j in range(s, e - 13):
            idx = np.arange(j, j + 14)
            av = a[idx]
            bv = b[idx]
            cv = c[idx]
            # shape guess: 14 ops = ? groups; inspect and report candidates
            hits.append((j, idx))
    return hits


if __name__ == '__main__':
    path = sys.argv[1]
    k, types, pos49, a, b, c = load(path)
    s = k.summary()
    print('file:', path)
    print(' counts:', s['counts'])
    print(' cols  :', s['cols'])
    print(' ops:', len(types), ' type49:', len(pos49), ' type33:', int((types == 33).sum()))
    runs = contiguous_runs(pos49)
    runs.sort(key=lambda r: -(r[1] - r[0]))
    print(' contiguous type-49 runs: %d (longest %d)' % (len(runs), runs[0][1] - runs[0][0] + 1 if runs else 0))
    h = find36(pos49, a, b, c)
    print(' 36-op factoring windows found:', len(h))
    for x in h:
        print('   j=%d op_start=%d  A=%d D=%d E=%d  B=%d..%d  C=%d..%d' %
              (x['j'], x['op_start'], x['A'], x['D'], x['E'], x['B'], x['B'] + 11, x['C'], x['C'] + 11))
    # quick look at a 14-op window shape (chain-1 style) for inspection
    for s0, e0 in runs[:3]:
        j = s0
        if e0 - s0 + 1 < 14:
            continue
        print(' sample 14-op window at j=%d:' % j)
        for t in range(14):
            print('    [%d, %d, %d, %d]' % (T49, a[j + t], b[j + t], c[j + t]))
        break
