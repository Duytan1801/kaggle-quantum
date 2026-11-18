#!/usr/bin/env python3
"""quad_pair.py — find 'quadratic rank' pairs in a .kmx circuit.

Identity (GF(2) on the target):
    T ^= b*x        and        T ^= a*x      (same source x, same target T,
                                                 different controls a, b)
      =>  T ^= (a xor b) * x
implemented exactly as
    CX(a -> b); CCX(x, b -> T); CX(a -> b)
which replaces TWO Toffolis by ONE.

Validity conditions between the two original ops:
  * T  (target) is not read or written in between (its value differs there),
  * x  (source)  is not read or written in between,
  * a, b (controls) are not read or written in between (the CX modifies b),
  * no CZ between touches T, x, a or b (CZ phases depend on wire values).
Everything else in between is irrelevant.

Usage: quad_pair.py FILE.kmx [--show N] [--verbose]
"""
import sys
from collections import defaultdict


def parse(path):
    lines = open(path).read().splitlines()
    ops = []
    for i, l in enumerate(lines):
        t = l.split()
        if t:
            ops.append((i, t))
    return lines, ops


def wires_of(t):
    """(controls, targets) of an op, ignoring classical bits."""
    name = t[0]
    if name in ('CCX', 'CSWAP'):
        return t[1:4], []
    if name in ('CX', 'CZ', 'SWAP'):
        return [t[1]], [t[2]]
    if name in ('X', 'Z', 'Z_POW', 'HMR', 'R'):
        return [], [t[1]]
    if name.startswith('BIT_'):
        return [], []
    return [], []


def main(path, show=10, verbose=False):
    lines, ops = parse(path)
    counts = defaultdict(int)
    for _, t in ops:
        counts[t[0]] += 1
    print('file:', path, ' ops:', len(ops))
    print(' counts:', dict(sorted(counts.items(), key=lambda kv: -kv[1])))

    # per-wire event lists: (op_index, kind) kind: 'r' read, 'w' write
    ev = defaultdict(list)
    cz_ev = defaultdict(list)
    ccx_by_key = defaultdict(list)
    for n, (i, t) in enumerate(ops):
        name = t[0]
        if name == 'CCX':
            c1, c2, tg = t[1], t[2], t[3]
            ev[c1].append((n, 'r'))
            ev[c2].append((n, 'r'))
            ev[tg].append((n, 'w'))
            # key: (source=c2, target=tg) and also (source=c1, target=tg)
            ccx_by_key[(c2, tg)].append((n, c1))
            ccx_by_key[(c1, tg)].append((n, c2))
        elif name == 'CZ':
            ev[t[1]].append((n, 'r'))
            ev[t[2]].append((n, 'r'))
            cz_ev[t[1]].append(n)
            cz_ev[t[2]].append(n)
        elif name == 'CX':
            ev[t[1]].append((n, 'r'))
            ev[t[2]].append((n, 'r', 'w'))
        elif name == 'SWAP':
            ev[t[1]].append((n, 'r', 'w'))
            ev[t[2]].append((n, 'r', 'w'))
        elif name in ('X', 'Z', 'Z_POW', 'HMR', 'R'):
            ev[t[1]].append((n, 'r', 'w'))
        elif name.startswith('BIT_'):
            pass

    # index events per wire for fast range queries
    idx = {}
    for w, lst in ev.items():
        lst.sort()
        idx[w] = ([e[0] for e in lst], [e[1] for e in lst])

    def touched(w, lo, hi):
        """any event on wire w strictly between lo and hi (exclusive)"""
        if w not in idx:
            return False
        pos, kinds = idx[w]
        # binary search
        import bisect
        a = bisect.bisect_right(pos, lo)
        b = bisect.bisect_left(pos, hi)
        return b > a

    cands = []
    seen = set()
    for (x, T), lst in ccx_by_key.items():
        if len(lst) < 2:
            continue
        lst.sort()
        for ii in range(len(lst)):
            for jj in range(ii + 1, len(lst)):
                i, b = lst[ii]
                j, a = lst[jj]
                if a == b:
                    continue
                key = (i, j, x, T)
                if key in seen:
                    continue
                seen.add(key)
                # safety: no event on x, T, a, b strictly between i and j
                bad = False
                for w in (x, T, a, b):
                    if touched(w, i, j):
                        bad = True
                        break
                if bad:
                    continue
                cands.append((i, j, a, b, x, T))
    cands.sort()
    print('\nquadratic-rank pair candidates:', len(cands))
    for i, j, a, b, x, T in cands[:show]:
        print(f'   op {i}: CCX {b} {x} {T}   op {j}: CCX {a} {x} {T}'
              f'   ->  CX {a} {b}; CCX {x} {b} {T}; CX {a} {b}   (saves 1 Toffoli)')
        if verbose:
            for n in range(i, min(j + 1, i + 12)):
                print(f'        {n}: {" ".join(ops[n][1])}')
            if j > i + 11:
                print('        ...')
    return cands


if __name__ == '__main__':
    p = sys.argv[1]
    sh = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 10
    vb = '--verbose' in sys.argv
    main(p, sh, vb)
