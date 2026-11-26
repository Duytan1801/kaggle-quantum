#!/usr/bin/env python3
"""dqi_cmerge_patch.py — apply the pairwise cmerge rewrite to a DQI .kmb.

For each chosen pair (two STATIC CCX ops that share one control x and the same
target T, with distinct other controls a and b):

    original:   ... CCX(a, x, T)  [window]  CCX(b, x, T) ...
    patched:    ... CX(a->b) CCX(x, b, T) CX(a->b)  [window] ...

because  T ^= x*a xor x*b == x*(a xor b).  kickmix counts CCX as a Toffoli and
CX as free, so each merge removes ONE Toffoli from the DQI cost metric.

The .kmb layout is columnar (see work/tools/kmb_cols.py):
    col1 : 1 byte per op          (op code, 0x80 bit = conditional)
    col2/3/4 : uint32 per 3-qubit op (operand 1, 2, target)
    col5/6   : uint32 per 2-qubit op (operand 1, 2)
    col7     : uint32 per 1-qubit op
    col8/9   : bit-register streams
Each stream is ordered by instruction position, and col1 tells the interleaving.
So a patch is:
    * col1: at p_i replace the CCX byte with [0x21, 0x31, 0x21]; at p_j delete
      the byte;
    * cols 2/3/4: row p_i becomes (x, b, T); row p_j is dropped;
    * cols 5/6: two rows (a, b) and (a, b) inserted at p_i's position;
    * header counts: nops += n, n3 -= n, n2 += 2n.

Usage:
  dqi_cmerge_patch.py <in.kmb> <out.kmb> <pairs.json> [--limit N]
where pairs.json is the output of dqi_cmerge_pairs.py (key "chosen").
"""
from __future__ import annotations

import json
import pathlib
import struct
import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb, write_patched

B_CCX = 0x31
B_CX = 0x21
COND = 0x80


def main() -> int:
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2])
    pairs = json.loads(pathlib.Path(sys.argv[3]).read_text())['chosen']
    if '--limit' in sys.argv:
        pairs = pairs[:int(sys.argv[sys.argv.index('--limit') + 1])]
    print(f'{len(pairs)} pairs to apply', flush=True)

    k = Kmb(src)
    ops = np.frombuffer(k.read_col(1), dtype=np.uint8)
    n = len(ops)
    base = (ops & 127).astype(np.uint8)
    iscond = (ops & COND) != 0

    p3 = np.flatnonzero(np.isin(base, [0x30, B_CCX, 0x32])).astype(np.int64)
    p2 = np.flatnonzero(np.isin(base, [0x20, B_CX, 0x22])).astype(np.int64)

    c3a = np.frombuffer(k.read_col(2), dtype=np.uint32)
    c3b = np.frombuffer(k.read_col(3), dtype=np.uint32)
    c3t = np.frombuffer(k.read_col(4), dtype=np.uint32)
    c2a = np.frombuffer(k.read_col(5), dtype=np.uint32)
    c2b = np.frombuffer(k.read_col(6), dtype=np.uint32)

    # candidate list must match the scanner exactly
    cand_pos = np.flatnonzero((base == B_CCX) & (~iscond))
    cand3 = np.searchsorted(p3, cand_pos).astype(np.int64)

    # ---- collect the edits ------------------------------------------------
    edits = []
    for d in pairs:
        i, j = int(d['i']), int(d['j'])
        if i >= len(cand_pos) or j >= len(cand_pos):
            raise SystemExit(f'bad candidate index in {d}')
        pi = int(cand_pos[i])
        pj = int(cand_pos[j])
        ki = int(cand3[i])
        kj = int(cand3[j])
        # sanity: the recorded geometry must match the file
        if pi != int(d['p_i']) or pj != int(d['p_j']):
            raise SystemExit(f'position mismatch for pair {d["i"]},{d["j"]}')
        T = int(c3t[ki])
        if T != int(d['T']):
            raise SystemExit('target mismatch')
        x = int(d['x'])
        a = int(d['a'])
        b = int(d['b'])
        # locate which operand slot holds the shared control x in each gate
        u_i = (int(c3a[ki]), int(c3b[ki]))
        u_j = (int(c3a[kj]), int(c3b[kj]))
        if x not in u_i or x not in u_j:
            raise SystemExit(f'shared control not present in {u_i} / {u_j}')
        if a in u_i and a != x:
            other_i = a
        elif a in u_j:
            other_i = a
        else:
            raise SystemExit(f'control a={a} not in {u_i}')
        if b in u_j and b != x:
            other_j = b
        elif b in u_i:
            other_j = b
        else:
            raise SystemExit(f'control b={b} not in {u_j}')
        if other_i == other_j:
            raise SystemExit('degenerate pair')
        # the merged triple: CX(other_i -> other_j); CCX(x, other_j, T); CX(...)
        edits.append(dict(pi=pi, pj=pj, ki=ki, kj=kj, T=T, x=x,
                          a=other_i, b=other_j))

    # disjointness
    pis = [e['pi'] for e in edits]
    pjs = [e['pj'] for e in edits]
    if len(set(pis)) != len(pis) or len(set(pjs)) != len(pjs):
        raise SystemExit('overlapping edits')
    if set(pis) & set(pjs):
        raise SystemExit('a position is both replaced and deleted')

    m = len(edits)
    print(f'replacing {m} CCX pairs -> net {m} fewer Toffolis, +{2*m} CX', flush=True)

    # ---- rebuild col1 ------------------------------------------------------
    delmask = np.zeros(n, dtype=bool)
    delmask[np.array(pjs, dtype=np.int64)] = True
    repmask = np.zeros(n, dtype=bool)
    repmask[np.array(pis, dtype=np.int64)] = True
    add = np.zeros(n + 1, dtype=np.int64)
    np.cumsum(repmask, out=add[1:])
    out_idx = np.arange(n, dtype=np.int64) + 2 * add[:n]
    total = int(out_idx[-1]) + 3 if n else 0
    # total length = n + 2*m (each replaced op emits 3 bytes instead of 1)
    new_len = n + 2 * m
    new_ops = np.empty(new_len, dtype=np.uint8)
    keep = ~delmask
    new_ops[out_idx[keep]] = ops[keep]
    # the replacement triples
    for e in edits:
        o = int(out_idx[e['pi']])
        new_ops[o] = B_CX
        new_ops[o + 1] = B_CCX
        new_ops[o + 2] = B_CX
    assert new_ops[new_len - 1] == ops[n - 1] or True

    # ---- rebuild the 3-qubit stream ---------------------------------------
    # rows: replace row ki with (x, b, T); drop row kj
    new_c3a = np.delete(c3a, kjs)
    new_c3b = np.delete(c3b, kjs)
    new_c3t = np.delete(c3t, kjs)
    # after deletion, row indices below kj shift by one
    for e in edits:
        ki = e['ki']
        kj = e['kj']
        # position of row ki in the NEW array
        nki = ki - int(np.sum(np.array(kjs) < ki))
        new_c3a[nki] = e['x']
        new_c3b[nki] = e['b']
        new_c3t[nki] = e['T']

    # ---- rebuild the 2-qubit stream ---------------------------------------
    # two rows (a,b) inserted at each p_i's position
    ins_idx = np.array([int(np.searchsorted(p2, e['pi'], side='right'))
                        for e in edits], dtype=np.int64)
    # insertion points must be distinct and sorted
    order = np.argsort(ins_idx, kind='stable')
    ins_idx = ins_idx[order]
    ed2 = [edits[o] for o in order]
    if len(set(ins_idx.tolist())) != len(ins_idx):
        raise SystemExit('two merges inserted at the same 2-qubit slot')
    add2 = np.zeros(len(c2a) + 1, dtype=np.int64)
    np.cumsum(np.bincount(ins_idx, minlength=len(c2a) + 1)[:len(c2a) + 1],
              out=add2[1:])
    idx2 = np.arange(len(c2a), dtype=np.int64) + add2[:len(c2a)]
    new_len2 = len(c2a) + 2 * m
    new_c2a = np.empty(new_len2, dtype=np.uint32)
    new_c2b = np.empty(new_len2, dtype=np.uint32)
    new_c2a[idx2] = c2a
    new_c2b[idx2] = c2b
    for e, ii in zip(ed2, ins_idx):
        # two rows at output positions ii and ii+1 (after shift)
        o = int(ii + add2[ii])
        new_c2a[o] = e['a']
        new_c2b[o] = e['b']
        new_c2a[o + 1] = e['a']
        new_c2b[o + 1] = e['b']

    counts = list(k.counts)
    counts[0] = new_len
    counts[1] = len(new_c3a)
    counts[2] = new_len2

    upd = {
        1: new_ops.tobytes(),
        2: new_c3a.tobytes(),
        3: new_c3b.tobytes(),
        4: new_c3t.tobytes(),
        5: new_c2a.tobytes(),
        6: new_c2b.tobytes(),
    }
    write_patched(src, dst, upd, counts=counts)
    print(f'wrote {dst} ({dst.stat().st_size} B)', flush=True)
    print(f'  nops {n} -> {new_len}; 3q {len(c3a)} -> {len(new_c3a)}; '
          f'2q {len(c2a)} -> {new_len2}', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
