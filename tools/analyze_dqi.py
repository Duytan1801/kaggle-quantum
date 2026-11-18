#!/usr/bin/env python3
"""analyze_dqi.py — structural analysis of a DQI .kmb: 3-qubit op runs, duplicate
(source,target) pairs with differing controls (the 'quadratic rank' opportunity).

The identity used by thomas' chain-1 plans is
    T ^= a*x   and   T ^= b*x   (same source x, same target T, different controls)
        =>  CX(a->b); CCX(x, b, T); CX(a->b)      (one Toffoli instead of two)
valid when nothing between the two writes reads T or x, and b is not disturbed.
"""
import sys
import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from find_factoring2 import load3q, runs_of, CCX


def main(path):
    k, types, tri_pos, tri_type, q0, q1, q2 = load3q(path)
    print('file:', path)
    print(' counts:', k.counts)
    print(' instructions:', len(types), ' 3q:', len(tri_pos))
    rs = runs_of(tri_pos)
    rs.sort(key=lambda r: -(r[1] - r[0]))
    print('\n=== 3-qubit runs (length >= 8), top 15 ===')
    for s, e in rs[:15]:
        if e - s + 1 < 8:
            break
        L = e - s + 1
        # group the run by control q0
        ctrl = q0[s:e + 1]
        uq, cnt = np.unique(ctrl, return_counts=True)
        seq = []
        for u in uq:
            idx = np.flatnonzero(ctrl == u) + s
            b = q1[idx]
            c = q2[idx]
            consec = bool((np.diff(b) == 1).all()) and bool((np.diff(c) == 1).all())
            seq.append('ctrl=%d n=%d%s src=%d..%d tgt=%d..%d' %
                       (u, len(idx), '+' if consec else '*', b[0], b[-1], c[0], c[-1]))
        print('  run tri=%d..%d len=%d instr=%d..%d : %s' %
              (s, e, L, tri_pos[s], tri_pos[e], ' | '.join(seq)))

    print('\n=== duplicate (source,target) pairs across the whole file ===')
    key = q1.astype(np.int64) * 4096 + q2.astype(np.int64)
    order = np.argsort(key, kind='stable')
    ks = key[order]
    dupmask = ks[1:] == ks[:-1]
    print('  repeated (src,tgt) pairs:', int(dupmask.sum()))
    # group
    starts = np.flatnonzero(np.concatenate(([True], ks[1:] != ks[:-1])))
    ends = np.concatenate((starts[1:], [len(ks)]))
    groups = []
    for s, e in zip(starts, ends):
        if e - s > 1:
            groups.append((s, e))
    print('  distinct repeated pairs:', len(groups))
    # how many have >1 distinct control?
    multi = 0
    total_extra = 0
    examples = []
    for s, e in groups:
        idxs = order[s:e]
        cs = q0[idxs]
        u = np.unique(cs)
        if len(u) > 1:
            multi += 1
            total_extra += (e - s) - 1
            if len(examples) < 8:
                examples.append((int(q1[idxs[0]]), int(q2[idxs[0]]), e - s, len(u),
                                 [int(x) for x in u[:6]], [int(tri_pos[i]) for i in idxs[:6]]))
    print('  pairs with >1 distinct control:', multi, ' extra ops if merged:', total_extra)
    for ex in examples:
        print('    src=%d tgt=%d count=%d controls=%s instr=%s' % ex)


if __name__ == '__main__':
    main(sys.argv[1])
