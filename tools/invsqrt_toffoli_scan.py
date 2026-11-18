#!/usr/bin/env python3
"""invsqrt_toffoli_scan.py — hunt removable Toffoli-like ops in an invsqrt .kmx.

Only Toffoli-like ops (CCX/CCZ/CSWAP) and T-costing Z_POW rotations affect the
score (score = Q * (toffoli_mean + T/4)); CX/CZ/HMR/X/Z are free.

Candidate classes found here:

  A. cancel-pair   two CCX with identical (c1,c2,target) and no read/measure of
                   the target between them  ->  the pair is the identity, drop both.
  B. dead-x        CCX whose target is overwritten by X (or another *known* value)
                   before it is read or measured -> the write is dead, drop the CCX.
  C. dead-hmr      CCX whose target's next event is HMR and whose measured bit is
                   never used afterwards (no conditional gate, no BIT_* op) ->
                   the write cannot influence anything, drop the CCX.

Usage: invsqrt_toffoli_scan.py FILE.kmx [--show N] [--verbose]
"""
import sys
from collections import defaultdict

TOF = ('CCX', 'CSWAP')


def parse(path):
    ops = []
    for i, l in enumerate(open(path).read().splitlines()):
        t = l.split()
        if t:
            ops.append((i, t))
    return ops


def main(path, show=12, verbose=False):
    ops = parse(path)
    n_ops = len(ops)
    reads = defaultdict(list)     # wire -> op indices where wire is read (control)
    writes = defaultdict(list)    # wire -> op indices where wire is written
    measures = defaultdict(list)  # wire -> op indices of HMR/R on wire
    bituse = defaultdict(list)    # classical bit -> op indices where used
    tofs = []

    for n, (i, t) in enumerate(ops):
        name = t[0]
        if name == 'CCX':
            c1, c2, tg = t[1], t[2], t[3]
            reads[c1].append(n); reads[c2].append(n); writes[tg].append(n)
            tofs.append((n, c1, c2, tg))
        elif name == 'CCZ':
            # symmetric phase gate: all three are "read", no dedicated target
            reads[t[1]].append(n); reads[t[2]].append(n); reads[t[3]].append(n)
        elif name == 'CSWAP':
            a, b, c = t[1], t[2], t[3]
            reads[a].append(n); reads[b].append(n); reads[c].append(n)
            writes[a].append(n); writes[b].append(n); writes[c].append(n)
        elif name == 'HMR':
            q, b = t[1], t[2]
            writes[q].append(n); measures[q].append(n)
            bituse[b].append(n)          # the measurement itself defines the bit
        elif name == 'R':
            writes[t[1]].append(n); measures[t[1]].append(n)
        elif name in ('CX', 'CZ'):
            reads[t[1]].append(n)
            if name == 'CX':
                writes[t[2]].append(n)
            else:
                reads[t[2]].append(n)
        elif name == 'SWAP':
            reads[t[1]].append(n); reads[t[2]].append(n)
            writes[t[1]].append(n); writes[t[2]].append(n)
        elif name in ('X', 'Z', 'Z_POW'):
            writes[t[1]].append(n)
        elif name.startswith('BIT_'):
            pass
        elif name == 'PUSH_CONDITION':
            bituse[t[1]].append(n)
        elif name == 'POP_CONDITION':
            pass
    # conditional gates: "<OP> a b if bit"
    for n, (i, t) in enumerate(ops):
        if len(t) > 2 and t[-2] == 'if':
            bituse[t[-1]].append(n)

    import bisect
    idxr = {w: sorted(v) for w, v in reads.items()}
    idxw = {w: sorted(v) for w, v in writes.items()}
    idxm = {w: sorted(v) for w, v in measures.items()}

    def first_after(lst, lo):
        if not lst:
            return None
        p = bisect.bisect_right(lst, lo)
        return lst[p] if p < len(lst) else None

    def any_between(lst, lo, hi):
        if not lst:
            return False
        a = bisect.bisect_right(lst, lo)
        b = bisect.bisect_left(lst, hi)
        return b > a

    candA = []   # cancel pairs
    candB = []   # dead via X overwrite
    candC = []   # dead via unused HMR bit
    reasons = defaultdict(int)

    # ---- A: identical CCX pairs -------------------------------------------
    by_key = defaultdict(list)
    for (n, c1, c2, tg) in tofs:
        by_key[(c1, c2, tg)].append(n)
        by_key[(c2, c1, tg)].append(n)
    for key, lst in by_key.items():
        if len(lst) < 2:
            continue
        lst = sorted(set(lst))
        for a, b in zip(lst, lst[1:]):
            tg = key[2]
            if any_between(idxr.get(tg, []), a, b):
                continue
            if any_between(idxm.get(tg, []), a, b):
                continue
            candA.append((a, b, tg))

    # ---- B / C: dead writes ----------------------------------------------
    for (n, c1, c2, tg) in tofs:
        w = first_after(idxw.get(tg, []), n)
        if w is None:
            reasons['no later write (target must be restored)'] += 1
            continue
        if any_between(idxr.get(tg, []), n, w):
            reasons['target read before next write'] += 1
            continue
        if any_between(idxm.get(tg, []), n, w):
            reasons['target measured before next write'] += 1
            continue
        wname = ops[w][1][0]
        if wname == 'X':
            candB.append((n, c1, c2, tg, w))
        elif wname == 'HMR':
            b = ops[w][1][2]
            # bit used after the measurement?  (a conditional gate or BIT_* op)
            uses = [u for u in bituse.get(b, []) if u > w]
            if uses:
                reasons['HMR bit used later'] += 1
            else:
                candC.append((n, c1, c2, tg, w, b))
        else:
            reasons[f'next write is {wname}'] += 1

    print(f'file: {path}  ops: {n_ops}')
    print(f'  CCX total            : {len(tofs)}')
    print(f'  A cancel pairs       : {len(candA)}  (Toffolis saved {2*len(candA)})')
    print(f'  B dead (X overwrite) : {len(candB)}')
    print(f'  C dead (unused HMR)  : {len(candC)}')
    print('  other reasons:', dict(reasons))
    tot = 2 * len(candA) + len(candB) + len(candC)
    print(f'  TOTAL removable Toffolis: {tot}  (~{tot*0.00552:.3f} GM)')

    if candA:
        print('\n=== A: cancel pairs ===')
        for a, b, tg in candA[:show]:
            print(f'  ops {a} & {b}: {" ".join(ops[a][1])}   (target {tg})')
            if verbose:
                for k in range(a, min(b + 1, a + 8)):
                    print(f'      {k}: {" ".join(ops[k][1])}')
    if candB:
        print('\n=== B: dead write, target overwritten by X ===')
        for n, c1, c2, tg, w in candB[:show]:
            print(f'  op {n}: {" ".join(ops[n][1])}   ->  X at op {w} (line {ops[w][0]})')
            if verbose:
                for k in range(n, min(w + 1, n + 8)):
                    print(f'      {k}: {" ".join(ops[k][1])}')
    if candC:
        print('\n=== C: dead write, HMR bit never used ===')
        for n, c1, c2, tg, w, b in candC[:show]:
            print(f'  op {n}: {" ".join(ops[n][1])}   ->  HMR {tg} {b} at op {w}')
            if verbose:
                for k in range(n, min(w + 1, n + 8)):
                    print(f'      {k}: {" ".join(ops[k][1])}')
    return candA, candB, candC


if __name__ == '__main__':
    p = sys.argv[1]
    sh = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 12
    main(p, sh, '--verbose' in sys.argv)
