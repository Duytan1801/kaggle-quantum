#!/usr/bin/env python3
"""dqi_cmerge_fast.py — PRODUCTION pairwise-cmerge scanner for a DQI .kmb.

IDENTITY (exact, algebraic):

    CCX(a, x, T)   CCX(b, x, T)          ->   CX(a->b)  CCX(x, b, T)  CX(a->b)

    T ^= x*a xor x*b  ==  x*(a xor b)

kickmix's `num_toffoli_like` counts CCX=1, CCZ=1, CSWAP=1 and **CX=0**, so this
rewrite removes ONE Toffoli from the DQI cost metric while adding two free CX
gates.  The DQI score is rep_factor * Q^2 * mean_Toffoli and one Toffoli is
worth ~3.5e-5 GM (1,000 Toffolis ~= +0.035 GM).

VALIDITY of a pair (op_i at p_i < op_j at p_j), both STATIC CCX with the same
target T, sharing one control x, other controls a != b:
    * a, b, x, T pairwise distinct;
    * in the open interval (p_i, p_j):
        - T must not be READ by any op (the merged version applies the combined
          XOR at p_i, so T's value differs from the original until p_j);
        - x, a, b must not be WRITTEN by any op.
      T may be the target of a CX/CCX or the operand of a static X in the
      interval: those are XORs and commute with the merged CCX.
    * the two CX gates are inserted contiguously at p_i, so no other
      instruction ever observes the temporarily modified wire b.

OPCODE TABLE (kickmix v2 binary format; see work/run_moat/decode_it15/kmbparse.py):
    0x10 Z  0x11 X  0x12 R  0x13 ZAPOW  0x50 HMR   (1-qubit, read+write their qubit)
    0x20 CZ  0x21 CX  0x22 SWAP                    (CZ reads BOTH operands)
    0x30 CCZ 0x31 CCX 0x32 CSWAP                   (CCZ has NO target: all 3 are read)
    0x40 BS0 0x41 BS1 0x42 BINVR                   (classical bit registers, not qubits)
  the 0x80 bit marks a CONDITIONAL op.

ALGORITHM.  The naive interval scan is hopeless here: the candidate pairs have
a MEDIAN span of 1.44M instructions.  Instead this tool builds, per wire, the
sorted positions of the ops that READ it and of the ops that WRITE it, then
answers every "is there a read/write of wire w in (p_i, p_j)?" with two
binary searches.  Measured T-quiet window lengths (2026-11-23): 59% of gates
have >= 100 instructions, 81.6% >= 1,000, p99 = 2.4M.

MEMORY.  Everything is sized to stay under the 3 GB cage: the per-wire buckets
are built with an in-place composite-key sort (no argsort index array), and the
READ buckets are restricted to the wires that actually occur as a CCX target.

Usage:
  dqi_cmerge_fast.py <dqi.kmb> [--json OUT.json] [--max-span N]
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb

B_CCZ, B_CCX, B_CSWAP = 0x30, 0x31, 0x32
B_CZ, B_CX, B_SWAP = 0x20, 0x21, 0x22
COND = 0x80
INT_MAX = np.iinfo(np.int64).max
POS_MASK = np.uint64(0xFFFFFFFF)


def fill_key(key, off, wire_src, pos_src, mask=None):
    """write (wire << 32 | pos) keys for one event piece; returns the new offset"""
    if mask is not None:
        w = wire_src[mask]
        p = pos_src[mask]
    else:
        w = wire_src
        p = pos_src
    m = len(w)
    key[off:off + m] = (np.asarray(w, dtype=np.uint64) << np.uint64(32)) \
        | np.asarray(p, dtype=np.uint64)
    return off + m


def build_buckets(pieces):
    """pieces: list of (wire_src, pos_src, mask_or_None)

    Returns dict wire -> np.array(sorted positions).  Memory-lean: the key
    array is filled piece by piece and sorted IN PLACE (no argsort index array,
    no full-length int64 wire copy).
    """
    total = 0
    for w, p, m in pieces:
        total += len(w) if m is None else int(m.sum())
    key = np.empty(total, dtype=np.uint64)
    off = 0
    for w, p, m in pieces:
        off = fill_key(key, off, w, p, m)
    key.sort()
    ps = (key & POS_MASK).astype(np.int32)
    ws = (key >> np.uint64(32)).astype(np.int32)
    del key
    uniq, starts = np.unique(ws, return_index=True)
    ends = np.concatenate((starts[1:], [len(ws)]))
    out = {int(u): ps[s:e] for u, s, e in zip(uniq, starts, ends)}
    del ps, ws
    return out, uniq


def next_after(arr, pos):
    """first position in arr strictly greater than pos (INT_MAX if none)"""
    if arr is None or len(arr) == 0:
        return INT_MAX
    i = int(np.searchsorted(arr, pos, side='right'))
    if i >= len(arr):
        return INT_MAX
    return int(arr[i])


def main() -> int:
    t0 = time.time()
    path = pathlib.Path(sys.argv[1])
    max_span = 2_000_000
    if '--max-span' in sys.argv:
        max_span = int(sys.argv[sys.argv.index('--max-span') + 1])

    k = Kmb(path)
    ops = np.frombuffer(k.read_col(1), dtype=np.uint8)
    n = len(ops)
    base = (ops & 127).astype(np.uint8)
    iscond = (ops & COND) != 0
    del ops

    lut3 = np.zeros(256, dtype=bool); lut3[[B_CCZ, B_CCX, B_CSWAP]] = True
    lut2 = np.zeros(256, dtype=bool); lut2[[B_CZ, B_CX, B_SWAP]] = True
    lut1 = np.zeros(256, dtype=bool); lut1[[0x10, 0x11, 0x12, 0x13, 0x50]] = True
    p3 = np.flatnonzero(lut3[base]).astype(np.int32)
    p2 = np.flatnonzero(lut2[base]).astype(np.int32)
    p1 = np.flatnonzero(lut1[base]).astype(np.int32)
    b3 = base[p3]; b2 = base[p2]
    del lut1, lut2, lut3

    c3a = np.frombuffer(k.read_col(2), dtype=np.uint32)
    c3b = np.frombuffer(k.read_col(3), dtype=np.uint32)
    c3t = np.frombuffer(k.read_col(4), dtype=np.uint32)
    c2a = np.frombuffer(k.read_col(5), dtype=np.uint32)
    c2b = np.frombuffer(k.read_col(6), dtype=np.uint32)
    c1q = np.frombuffer(k.read_col(7), dtype=np.uint32)
    print(f'{path}: {n} ops; 3q={len(p3)} 2q={len(p2)} 1q={len(p1)}  '
          f'[{time.time()-t0:.1f}s]', flush=True)

    # ---------------- candidate static CCX gates ----------------------------
    cand = np.flatnonzero((base == B_CCX) & (~iscond))
    cand3 = np.searchsorted(p3, cand)
    ca = c3a[cand3].astype(np.int64)
    cb = c3b[cand3].astype(np.int64)
    ct = c3t[cand3].astype(np.int64)
    gpos = cand.astype(np.int64)
    twires = np.unique(ct)
    print(f'static CCX gates: {len(cand)}; distinct targets: {len(twires)} '
          f'[{time.time()-t0:.1f}s]', flush=True)

    # ---------------- READ buckets (all ops that READ each wire) -----------
    swcz = (b2 == B_CZ) | (b2 == B_SWAP)
    ccz_or_swap3 = (b3 == B_CCZ) | (b3 == B_CSWAP)
    readb, _ = build_buckets([
        (c2a, p2, None),                 # every 2q op reads operand 1
        (c2b, p2, swcz),                 # CZ/SWAP read operand 2 as well
        (c3a, p3, None), (c3b, p3, None),# CCX/CCZ/CSWAP read operands 1,2
        (c3t, p3, ccz_or_swap3),         # CCZ/CSWAP read operand 3 as well
        (c1q, p1, None),                 # every 1q op reads its qubit
    ])
    print(f'read buckets: {len(readb)} wires, {sum(len(v) for v in readb.values()):,} events '
          f'[{time.time()-t0:.1f}s]', flush=True)

    # ---------------- WRITE buckets (per wire) ------------------------------
    iscx = b2 == B_CX
    issw2 = b2 == B_SWAP
    isccx3 = b3 == B_CCX
    issw3 = b3 == B_CSWAP
    writeb, _ = build_buckets([
        (c2b, p2, iscx),                 # CX writes operand 2
        (c2a, p2, issw2), (c2b, p2, issw2),   # SWAP writes both
        (c3t, p3, isccx3),               # CCX writes operand 3
        (c3b, p3, issw3), (c3t, p3, issw3),   # CSWAP writes operands 2,3
        (c1q, p1, None),                 # every 1q op writes its qubit
    ])
    del c2a, c2b, c1q, c3a, c3b, c3t, p1, p2, p3, base, iscond, b2, b3
    print(f'write buckets: {len(writeb)} wires, '
          f'{sum(len(v) for v in writeb.values()):,} events [{time.time()-t0:.1f}s]',
          flush=True)

    # ---------------- per-gate next-read / next-write -----------------------
    nreadT = np.full(len(cand), INT_MAX, dtype=np.int64)
    for t in twires:
        m = ct == t
        arr = readb.get(int(t))
        if arr is None:
            continue
        idx = np.searchsorted(arr, gpos[m], side='right')
        idx = np.minimum(idx, len(arr) - 1)
        nreadT[m] = np.where(idx < len(arr), arr[idx].astype(np.int64), INT_MAX)

    def next_writes(wires, positions):
        out = np.full(len(wires), INT_MAX, dtype=np.int64)
        for w in np.unique(wires):
            m = wires == w
            arr = writeb.get(int(w))
            if arr is None:
                continue
            idx = np.searchsorted(arr, positions[m], side='right')
            idx = np.minimum(idx, len(arr) - 1)
            out[m] = np.where(idx < len(arr), arr[idx].astype(np.int64), INT_MAX)
        return out

    nw_a = next_writes(ca, gpos)
    nw_b = next_writes(cb, gpos)
    print(f'per-gate lookups done [{time.time()-t0:.1f}s]', flush=True)

    # ---------------- scan the groups ---------------------------------------
    stats = {
        'static_ccx': int(len(cand)),
        'groups': 0,
        'candidate_pairs': 0,
        'pairs_distinct_controls': 0,
        'pairs_valid': 0,
        'fail_t_read': 0,
        'fail_guard_written': 0,
        'fail_bad_controls': 0,
        'fail_dup_gate': 0,
    }
    valid = []
    seen = set()

    for shared_arr, other_arr, tag in ((ca, cb, 'shared=op1'), (cb, ca, 'shared=op2')):
        key = ct * 1024 + shared_arr
        order = np.argsort(key, kind='stable')
        ks = key[order]
        brk = np.flatnonzero(ks[1:] != ks[:-1]) + 1
        starts = np.concatenate(([0], brk))
        ends = np.concatenate((brk, [len(ks)]))
        for gi in range(len(starts)):
            s, e = int(starts[gi]), int(ends[gi])
            if e - s < 2:
                continue
            idx = order[s:e]
            so = np.argsort(gpos[idx], kind='stable')
            idx = idx[so]
            pos = gpos[idx]
            sh = shared_arr[idx]
            ot = other_arr[idx]
            T = int(ct[idx[0]])
            stats['groups'] += 1
            m = len(idx)
            nw_sh = next_writes(sh, pos)
            nw_ot = next_writes(ot, pos)
            for u in range(m - 1):
                i = int(idx[u])
                pi = int(pos[u])
                lim = min(int(nreadT[i]), int(nw_sh[u]), int(nw_ot[u]))
                lim = min(lim, pi + max_span)
                if lim <= pi:
                    continue
                v0 = u + 1
                v1 = int(np.searchsorted(pos, lim, side='left'))
                if v1 <= v0:
                    continue
                a = int(ot[u])
                x = int(sh[u])
                for v in range(v0, v1):
                    j = int(idx[v])
                    pj = int(pos[v])
                    stats['candidate_pairs'] += 1
                    b = int(ot[v])
                    if b == a:
                        stats['fail_dup_gate'] += 1
                        continue
                    if x == a or x == b or a == T or b == T:
                        stats['fail_bad_controls'] += 1
                        continue
                    if pj >= int(nreadT[i]):
                        stats['fail_t_read'] += 1
                        continue
                    if pj >= int(nw_sh[u]) or pj >= int(nw_ot[u]):
                        stats['fail_guard_written'] += 1
                        continue
                    nb = next_after(writeb.get(b), pi)
                    if pj >= nb:
                        stats['fail_guard_written'] += 1
                        continue
                    stats['pairs_distinct_controls'] += 1
                    pair = (min(i, j), max(i, j))
                    if pair in seen:
                        continue
                    seen.add(pair)
                    stats['pairs_valid'] += 1
                    valid.append({
                        'i': int(i), 'j': int(j),
                        'p_i': pi, 'p_j': pj,
                        'T': T, 'x': x, 'a': a, 'b': b,
                        'span': pj - pi,
                    })
            if stats['groups'] % 5000 == 0 and stats['groups']:
                print(f'  [{tag}] groups={stats["groups"]:,} '
                      f'cand={stats["candidate_pairs"]:,} valid={stats["pairs_valid"]:,} '
                      f'[{time.time()-t0:.1f}s]', flush=True)

    # ---------------- greedy disjoint selection -----------------------------
    valid.sort(key=lambda d: (d['span'], d['p_i']))
    used = set()
    chosen = []
    for d in valid:
        if d['i'] in used or d['j'] in used:
            continue
        used.add(d['i'])
        used.add(d['j'])
        chosen.append(d)
    stats['pairs_selected_disjoint'] = len(chosen)
    stats['toffolis_saved_disjoint'] = len(chosen)

    print(json.dumps(stats, indent=1), flush=True)
    if chosen:
        spans = np.array([d['span'] for d in chosen])
        print(f'selected {len(chosen)} disjoint pairs; span median={np.median(spans):.0f} '
              f'p90={np.percentile(spans,90):.0f} max={spans.max()}', flush=True)
    print(f'[{time.time()-t0:.1f}s]', flush=True)
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        pathlib.Path(out).write_text(json.dumps({'stats': stats,
                                                 'chosen': chosen}, indent=1))
        print('wrote', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
