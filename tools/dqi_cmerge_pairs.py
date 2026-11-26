#!/usr/bin/env python3
"""dqi_cmerge_pairs.py — find PAIRWISE cmerge opportunities in a DQI .kmb.

IDENTITY (exact, algebraic):

    CCX(a, x, T)   CCX(b, x, T)          ->   CX(a->b)  CCX(x, b, T)  CX(a->b)

    T ^= x*a xor x*b  ==  x*(a xor b)

kickmix's `num_toffoli_like` counts CCX=1, CCZ=1, CSWAP=1 and **CX=0**, so this
rewrite removes ONE Toffoli from the DQI cost metric while adding two free CX
gates.  The DQI score is rep_factor * Q^2 * mean_Toffoli, and one Toffoli is
worth ~2.94e-5 GM (1,000 Toffolis ~= +0.029 GM).

WHY A NEW TOOL (the 2026-11-23 09:2x scan was unsound / too coarse):
  1. `dqi_cmerge_scan.py` tested the WHOLE GROUP interval (all m gates of one
     (x,T) group at once).  All 38,799 multi-control groups failed, almost all
     because T is READ somewhere inside the group span.  A *pair* window is
     typically far shorter, so the pair test is a genuinely different (and
     much more permissive) question.
  2. The old tool's read/write model had TWO HOLES, found by reading
     `work/run_moat/decode_it15/kmbparse.py`:
       * 0x20 is CZ (not CX): CZ READS both operands.  The old tool treated
         operand 2 of a non-SWAP 2-qubit op as a WRITE, so a CZ with T in
         operand 2 was silently missed -> false-positive merges.
       * 0x30 is CCZ: it has NO target; all three operands are READ.  The old
         tool treated operand 3 of a CCZ as a write -> another missed T read.
     Both holes are fixed here.

OPCODE TABLE (kickmix v2 binary format, from kmbparse.py):
    0x00 NEG   0x01 POP_COND   0x06 INFO   0x07 DBG
    0x10 Z     0x11 X          0x12 R      0x13 ZAPOW   0x50 HMR
    0x20 CZ    0x21 CX         0x22 SWAP
    0x30 CCZ   0x31 CCX        0x32 CSWAP
    0x40 BS0   0x41 BS1        0x42 BINVR          (classical bit registers)
  the 0x80 bit marks a CONDITIONAL op.

READ / WRITE sets used here:
    3q:  CCZ  reads {a,b,t}          writes {}
         CCX  reads {a,b}            writes {t}
         CSWAP reads {a,b,t}         writes {b,t}
    2q:  CZ   reads {a,b}            writes {}
         CX   reads {a}              writes {b}
         SWAP reads {a,b}            writes {a,b}
    1q:  Z/X/R/ZAPOW/HMR  read+write {q}
    bit: BS0/BS1/BINVR act on classical bit registers, never on qubits.

VALIDITY of one pair (op_i at p_i < op_j at p_j), both STATIC CCX with the same
target T, sharing control x, other controls a != b:
    * a, b, x, T pairwise distinct (a != b; x != a, x != b; x != T; a,b != T);
    * in the open interval (p_i, p_j):
        - T must not be READ by any op (a CX/CZ/SWAP/CCX/CCZ/CSWAP that uses T
          as a control, a CZ/SWAP/CCZ/CSWAP that uses T as a non-target
          operand, or any 1-qubit op on T other than a *static* X, which
          commutes with the CCX);
        - x, a, b must not be WRITTEN by any op.
      T may be the target of a CX/CCX or the operand of a static X in the
      interval: those are XORs and commute with the merged CCX.
    * the two CX gates are inserted contiguously at p_i, so no other
      instruction ever observes the temporarily modified wire b.

Usage:
  dqi_cmerge_pairs.py <dqi.kmb> [--json OUT.json] [--max-span N] [--pairs]
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb

B_CCZ, B_CCX, B_CSWAP = 0x30, 0x31, 0x32
B_CZ, B_CX, B_SWAP = 0x20, 0x21, 0x22
B_X = 0x11
COND = 0x80


def main() -> int:
    path = pathlib.Path(sys.argv[1])
    max_span = 200_000
    if '--max-span' in sys.argv:
        max_span = int(sys.argv[sys.argv.index('--max-span') + 1])

    k = Kmb(path)
    ops = np.frombuffer(k.read_col(1), dtype=np.uint8)
    n = len(ops)
    base = (ops & 127).astype(np.uint8)
    iscond = (ops & COND) != 0

    p3 = np.flatnonzero(np.isin(base, [B_CCZ, B_CCX, B_CSWAP])).astype(np.int32)
    p2 = np.flatnonzero(np.isin(base, [B_CZ, B_CX, B_SWAP])).astype(np.int32)
    p1 = np.flatnonzero(np.isin(base, [0x10, 0x11, 0x12, 0x13, 0x50])).astype(np.int32)
    print(f'{path}: {n} ops; 3q={len(p3)} 2q={len(p2)} 1q={len(p1)}', flush=True)

    c3a = np.frombuffer(k.read_col(2), dtype=np.uint32)
    c3b = np.frombuffer(k.read_col(3), dtype=np.uint32)
    c3t = np.frombuffer(k.read_col(4), dtype=np.uint32)
    c2a = np.frombuffer(k.read_col(5), dtype=np.uint32)
    c2b = np.frombuffer(k.read_col(6), dtype=np.uint32)
    c1q = np.frombuffer(k.read_col(7), dtype=np.uint32)

    # ---- candidate gates: STATIC CCX only --------------------------------
    cand_pos = np.flatnonzero((base == B_CCX) & (~iscond))
    cand3 = np.searchsorted(p3, cand_pos).astype(np.int64)
    ca = c3a[cand3].astype(np.int64)     # operand 1 (control)
    cb = c3b[cand3].astype(np.int64)     # operand 2 (control)
    ct = c3t[cand3].astype(np.int64)     # operand 3 (target)
    gpos = p3[cand3].astype(np.int64)
    print(f'static CCX gates: {len(cand3)}', flush=True)

    # ---- group by (target, control) -------------------------------------
    # a pair shares ONE control and the same target.  Build both keyings so
    # that the shared control may be operand 1 or operand 2.
    def groups_for(shared, other):
        key = ct * 1024 + shared
        order = np.argsort(key, kind='stable')
        ks = key[order]
        brk = np.flatnonzero(ks[1:] != ks[:-1]) + 1
        starts = np.concatenate(([0], brk))
        ends = np.concatenate((brk, [len(ks)]))
        out = []
        for gi in range(len(starts)):
            s, e = int(starts[gi]), int(ends[gi])
            if e - s < 2:
                continue
            idx = order[s:e]
            out.append((int(ct[idx[0]]), int(shared[idx[0]]), idx))
        return out

    grpA = groups_for(ca, cb)   # shared control = operand 1
    grpB = groups_for(cb, ca)   # shared control = operand 2
    print(f'groups: {len(grpA)} (shared=op1) + {len(grpB)} (shared=op2)', flush=True)

    # ---- interval helpers ----------------------------------------------
    def ordinal(pos_arr, lo, hi):
        i0 = int(np.searchsorted(pos_arr, lo, side='right'))
        i1 = int(np.searchsorted(pos_arr, hi, side='left'))
        return i0, i1

    def interval_ok(pi, pj, T, x, a, b):
        """return None if valid, else a failure tag"""
        # ---- 3-qubit ops in (pi, pj) ------------------------------------
        i0, i1 = ordinal(p3, pi, pj)
        if i1 > i0:
            oa = c3a[i0:i1]
            ob = c3b[i0:i1]
            ot = c3t[i0:i1]
            obase = base3[i0:i1]
            # T read: CCX reads {oa,ob}; CCZ/CSWAP read {oa,ob,ot}
            if (oa == T).any() or (ob == T).any():
                return 'fail_t_read_3q'
            notccx = obase != B_CCX
            if notccx.any() and (ot[notccx] == T).any():
                return 'fail_t_read_3q'
            # guard writes: CCX writes ot; CSWAP writes ob,ot; CCZ writes none
            isccx = obase == B_CCX
            issw = obase == B_CSWAP
            hit = isccx & ((ot == x) | (ot == a) | (ot == b))
            if issw.any():
                sw = issw
                hit |= sw & ((ob[sw] == x) | (ob[sw] == a) | (ob[sw] == b))
                hit |= sw & ((ot[sw] == x) | (ot[sw] == a) | (ot[sw] == b))
            if hit.any():
                return 'fail_guard_written_3q'
        # ---- 2-qubit ops in (pi, pj) ------------------------------------
        j0, j1 = ordinal(p2, pi, pj)
        if j1 > j0:
            oa = c2a[j0:j1]
            ob = c2b[j0:j1]
            obase = base2[j0:j1]
            iscx = obase == B_CX
            issw = obase == B_SWAP
            iscz = obase == B_CZ
            # T read: EVERY 2q op reads operand 1 (CX: control; CZ/SWAP: both).
            # CZ and SWAP also read operand 2.
            if (oa == T).any():
                return 'fail_t_read_2q'
            read2 = iscz | issw
            if read2.any() and (ob[read2] == T).any():
                return 'fail_t_read_2q'
            # guard writes: CX writes ob; SWAP writes oa,ob; CZ writes none
            hit = iscx & ((ob == x) | (ob == a) | (ob == b))
            if issw.any():
                sw = issw
                hit |= sw & ((oa[sw] == x) | (oa[sw] == a) | (oa[sw] == b))
                hit |= sw & ((ob[sw] == x) | (ob[sw] == a) | (ob[sw] == b))
            if hit.any():
                return 'fail_guard_written_2q'
        # ---- 1-qubit ops in (pi, pj) ------------------------------------
        k0, k1 = ordinal(p1, pi, pj)
        if k1 > k0:
            oq = c1q[k0:k1]
            obase = base1[k0:k1]
            ocond = iscond[p1[k0:k1]]
            # a 1q op on T reads T, unless it is a STATIC X (commutes)
            onT = oq == T
            if onT.any():
                okx = (obase == B_X) & (~ocond)
                if (onT & ~okx).any():
                    return 'fail_t_read_1q'
            # every 1q op writes its qubit
            if ((oq == x) | (oq == a) | (oq == b)).any():
                return 'fail_guard_written_1q'
        return None

    stats = {
        'static_ccx': int(len(cand3)),
        'candidate_pairs': 0,
        'pairs_distinct_controls': 0,
        'pairs_valid': 0,
        'toffolis_saved_raw': 0,
        'skipped_span': 0,
        'fail_t_read_3q': 0,
        'fail_t_read_2q': 0,
        'fail_t_read_1q': 0,
        'fail_guard_written_3q': 0,
        'fail_guard_written_2q': 0,
        'fail_guard_written_1q': 0,
        'fail_bad_controls': 0,
        'fail_dup_gate': 0,
    }
    valid = []
    seen = set()

    # pre-extract the per-stream base opcodes (avoids repeated fancy indexing)
    base3 = base[p3]
    base2 = base[p2]
    base1 = base[p1]

    for shared_arr, other_arr in ((ca, cb), (cb, ca)):
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
            x = int(sh[0])
            for u in range(len(idx) - 1):
                for v in range(u + 1, len(idx)):
                    i, j = int(idx[u]), int(idx[v])
                    pi, pj = int(pos[u]), int(pos[v])
                    stats['candidate_pairs'] += 1
                    if pj - pi > max_span:
                        stats['skipped_span'] += 1
                        continue
                    a = int(ot[u])
                    b = int(ot[v])
                    if a == b:
                        stats['fail_dup_gate'] += 1
                        continue
                    if x == a or x == b or a == T or b == T:
                        stats['fail_bad_controls'] += 1
                        continue
                    stats['pairs_distinct_controls'] += 1
                    tag = interval_ok(pi, pj, T, x, a, b)
                    if tag is not None:
                        stats[tag] += 1
                        continue
                    pair = (min(i, j), max(i, j))
                    if pair in seen:
                        continue
                    seen.add(pair)
                    stats['pairs_valid'] += 1
                    stats['toffolis_saved_raw'] += 1
                    valid.append({
                        'i': int(i), 'j': int(j),
                        'p_i': pi, 'p_j': pj,
                        'T': T, 'x': x, 'a': a, 'b': b,
                        'span': pj - pi,
                    })
            if gi % 5000 == 0 and gi:
                print(f'  ... group {gi}/{len(starts)} valid={stats["pairs_valid"]}',
                      flush=True)

    # ---- greedy disjoint selection ---------------------------------------
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
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        pathlib.Path(out).write_text(json.dumps({'stats': stats,
                                                 'chosen': chosen}, indent=1))
        print('wrote', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
