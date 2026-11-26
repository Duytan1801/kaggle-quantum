#!/usr/bin/env python3
"""dqi_cmerge_scan.py — measure the GENERALIZED cmerge opportunity in a DQI .kmb.

Mechanism (boristown's `_apply_cmerge` / thomasgamet's column patch, generalised
beyond one contiguous-run shape):

    CCX(a, x, T)   CCX(b, x, T)          ->   CX(a->b) CCX(x, b, T) CX(a->b)

    T ^= x*a xor x*b  ==  x*(a xor b)

kickmix's `num_toffoli_like` counts CCX=1, CSWAP=1 and **CX=0**, so this
rewrite removes ONE Toffoli from the DQI cost metric while adding two free CX
gates.  The DQI score is rep * Q^2 * mean_Toffoli.

A whole group of m static CCX/CCZ ops on the same (x, T) with m distinct
controls can be collapsed to 1 Toffoli + 2(m-1) CX (XOR the other controls into
an anchor), saving m-1 Toffolis.

Validity of the anchor form, group gates at positions p_1 < ... < p_m:
  * the anchor control and every other control must be distinct from x and T;
  * in the open interval (p_1, p_m): x, and every control wire, must not be
    WRITTEN (they are read-only there), and T must not be READ (the merged
    version applies the combined XOR at p_1, the original applies only the
    partial XOR there).  Writes to T are harmless (XOR commutes).
  * the CX pairs are inserted contiguously at p_1, so no other instruction ever
    sees the temporarily modified anchor wire.

Usage: dqi_cmerge_scan.py <dqi.kmb> [--json OUT.json] [--max-span N]
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb

# base opcodes (op byte & 127)
B_CCZ = 0x30
B_CCX = 0x31
B_CSWAP = 0x32
B_CZ = 0x20
B_CX = 0x21
B_SWAP = 0x22
B_1Q = (0x10, 0x11, 0x12, 0x50)          # 1-qubit ops (col 7 = qubit)
B_BIT = (0x40, 0x41, 0x42, 0x50)         # bit-register ops (cols 8/9)
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

    is3 = np.isin(base, [B_CCZ, B_CCX, B_CSWAP])
    is2 = np.isin(base, [B_CZ, B_CX, B_SWAP])
    is1 = np.isin(base, B_1Q)
    p3 = np.flatnonzero(is3).astype(np.int32)
    p2 = np.flatnonzero(is2).astype(np.int32)
    p1 = np.flatnonzero(is1).astype(np.int32)
    print(f'{path}: {n} ops; 3q={len(p3)} 2q={len(p2)} 1q={len(p1)}', flush=True)

    c3a = np.frombuffer(k.read_col(2), dtype=np.uint32)
    c3b = np.frombuffer(k.read_col(3), dtype=np.uint32)
    c3t = np.frombuffer(k.read_col(4), dtype=np.uint32)
    c2a = np.frombuffer(k.read_col(5), dtype=np.uint32)
    c2t = np.frombuffer(k.read_col(6), dtype=np.uint32)
    c1q = np.frombuffer(k.read_col(7), dtype=np.uint32)

    # ---- candidate gates: STATIC (non-conditional) CCX/CCZ on the same (x,T)
    cand_pos = np.flatnonzero(is3 & ((ops & COND) == 0) &
                              np.isin(base, [B_CCZ, B_CCX]))
    cand3 = np.searchsorted(p3, cand_pos).astype(np.int64)
    ca = c3a[cand3].astype(np.int64)
    cx = c3b[cand3].astype(np.int64)
    ct = c3t[cand3].astype(np.int64)
    gpos = p3[cand3].astype(np.int64)
    print(f'static CCX/CCZ gates: {len(cand3)}', flush=True)

    key = cx * 4096 + ct
    order = np.argsort(key, kind='stable')
    ks = key[order]
    brk = np.flatnonzero(ks[1:] != ks[:-1]) + 1
    starts = np.concatenate(([0], brk))
    ends = np.concatenate((brk, [len(ks)]))

    # pre-compute ordinal -> position maps for the interval scans
    def ordinal(pos_arr, lo, hi):
        """ordinal range [lo,hi) of the ops at instruction positions in (lo,hi)"""
        i0 = int(np.searchsorted(pos_arr, lo, side='right'))
        i1 = int(np.searchsorted(pos_arr, hi, side='left'))
        return i0, i1

    stats = {
        'static_3q_gates': int(len(cand3)),
        'groups': 0,
        'groups_multi_control': 0,
        'anchor_valid': 0,
        'anchor_toffolis_saved': 0,
        'consecutive_pairs_valid': 0,
        'consecutive_toffolis_saved': 0,
        'skipped_span': 0,
        'fail_t_read_3q': 0,
        'fail_t_read_2q': 0,
        'fail_t_read_1q': 0,
        'fail_guard_written_3q': 0,
        'fail_guard_written_2q': 0,
        'fail_guard_written_1q': 0,
        'fail_dup_controls': 0,
    }
    detail = []

    for gi in range(len(starts)):
        s, e = int(starts[gi]), int(ends[gi])
        if e - s < 2:
            continue
        stats['groups'] += 1
        idx = order[s:e]
        x = int(cx[idx[0]])
        T = int(ct[idx[0]])
        ctr = ca[idx]
        uq = np.unique(ctr)
        if len(uq) < 2:
            continue
        stats['groups_multi_control'] += 1
        # sort the group's gates by instruction position
        so = np.argsort(gpos[idx], kind='stable')
        idx = idx[so]
        pos = gpos[idx]
        ctrl = ca[idx]
        p1_, p_m = int(pos[0]), int(pos[-1])
        if p_m - p1_ > max_span:
            stats['skipped_span'] += 1
            continue
        # wires that must not be WRITTEN in (p1_, p_m): x and every control.
        # (T may be written: XOR commutes.  T must not be READ.)
        guard = np.concatenate(([x], np.unique(ctrl)))
        guard = guard[guard != T]
        # check interval
        i0, i1 = ordinal(p3, p1_, p_m)
        bad = None
        # 3q ops in the interval: col2/col3 are controls (READ), col4 is the
        # target (WRITE).  The group's own middle gates write T -> allowed.
        if i1 > i0:
            if np.isin(c3a[i0:i1], T).any() or np.isin(c3b[i0:i1], T).any():
                bad = 'fail_t_read_3q'
            elif np.isin(c3t[i0:i1], guard).any():
                bad = 'fail_guard_written_3q'
        if bad is None:
            j0, j1 = ordinal(p2, p1_, p_m)
            if j1 > j0:
                op2 = base[p2[j0:j1]]
                sw = op2 == B_SWAP
                if np.isin(c2a[j0:j1], T).any():
                    bad = 'fail_t_read_2q'
                elif sw.any() and np.isin(c2a[j0:j1][sw], T).any():
                    bad = 'fail_t_read_2q'
                elif sw.any() and np.isin(c2t[j0:j1][sw], guard).any():
                    bad = 'fail_guard_written_2q'
                elif np.isin(c2t[j0:j1][~sw], guard).any():
                    bad = 'fail_guard_written_2q'
        if bad is None:
            k0, k1 = ordinal(p1, p1_, p_m)
            if k1 > k0:
                if np.isin(c1q[k0:k1], T).any():
                    bad = 'fail_t_read_1q'
                elif np.isin(c1q[k0:k1], guard).any():
                    bad = 'fail_guard_written_1q'
        if bad is not None:
            stats[bad] += 1
            continue
        m = len(pos)
        distinct_ctrl = len(np.unique(ctrl))
        if distinct_ctrl < m:
            # duplicate controls: the repeated control contributes twice
            # (cancels), so merging is only valid when every control appears
            # exactly once.
            stats['fail_dup_controls'] += 1
            continue
        stats['anchor_valid'] += 1
        stats['anchor_toffolis_saved'] += m - 1
        detail.append({'x': x, 'T': T, 'm': int(m),
                       'p0': p1_, 'p1': p_m,
                       'controls': [int(v) for v in ctrl],
                       'saved': int(m - 1)})
        stats['consecutive_pairs_valid'] += m - 1
        stats['consecutive_toffolis_saved'] += m - 1

    print(json.dumps(stats, indent=1), flush=True)
    if detail:
        detail.sort(key=lambda d: -d['saved'])
        print('top groups by saving:', flush=True)
        for d in detail[:15]:
            print('  ', d, flush=True)
    if '--json' in sys.argv:
        out = sys.argv[sys.argv.index('--json') + 1]
        pathlib.Path(out).write_text(json.dumps({'stats': stats,
                                                 'groups': detail}, indent=1))
        print('wrote', out)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
