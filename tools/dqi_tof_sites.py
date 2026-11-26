#!/usr/bin/env python3
"""dqi_tof_sites.py — classify every DQI Toffoli-like op by WHERE it writes.

The measure-first identity (Tymchishin & Hosen; implemented by arsen123 in
work/gens/arsen123_measurefirst_2026-11-23/) turns

    CCX(c1, c2, qw)        ->   CZ(c1, c2) if b{m}

when `qw` is written by that op, is NOT read quantumly afterwards, and is
MEASURED (HMR) later -- the measurement then carries the phase correction.
CZ is not a Toffoli, so the executed-Toffoli count drops.

Our executed Toffoli budget is 316,123/shot:
    267,934  unconditional (always executed)
     46,285  inside conditional regions (usually executed)

This tool classifies every static Toffoli-like op by:
  * target wire class: syndrome output qubit (S0..S69) vs ancilla (workspace)
  * conditional depth at the op (0 = always executed)
  * whether the target is later MEASURED (HMR) and whether the target is READ
    quantumly in between (which would block the measure-first rewrite)

Usage: dqi_tof_sites.py <dqi.kmb> [--json OUT.json]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
from kmb_cols import Kmb
import kickmix as km

TOF3 = (0x30, 0x31, 0x32)


def main() -> int:
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                        '/home/bandoc/Downloads/opencode/work/trees/v147/dqi.kmb')
    c = km.Circuit.from_file(str(path))
    regs = c.register_data
    sq = []
    for n in regs:
        if n.startswith('S'):
            sq.extend([int(x.id) for x in regs[n] if isinstance(x, km.q)])
    sq = np.array(sorted(sq), dtype=np.int64)
    anc = np.array(sorted(set(range(c.num_qubits)) - set(sq.tolist())), dtype=np.int64)
    is_anc = np.zeros(c.num_qubits, dtype=bool)
    is_anc[anc] = True
    print(f'qubits={c.num_qubits}  syndrome={len(sq)}  ancilla={len(anc)}')
    print(f'  ancilla indices: {anc[:20]} ... {anc[-10:]}')

    k = Kmb(path)
    ops = np.frombuffer(k.read_col(1), dtype=np.uint8)
    n = len(ops)
    base = ops & 127
    flagged = ops & 0x80
    lut3 = np.zeros(256, bool); lut3[list(TOF3)] = True
    lut2 = np.zeros(256, bool); lut2[[0x20, 0x21, 0x22]] = True
    lut1 = np.zeros(256, bool); lut1[[0x10, 0x11, 0x12, 0x13, 0x50]] = True
    p3 = np.flatnonzero(lut3[base]).astype(np.int32)
    p2 = np.flatnonzero(lut2[base]).astype(np.int32)
    p1 = np.flatnonzero(lut1[base]).astype(np.int32)
    del lut3, lut2, lut1
    # int32 views -- NO copy (the columns are already little-endian uint32)
    c3a = np.frombuffer(k.read_col(2), dtype=np.int32)
    c3b = np.frombuffer(k.read_col(3), dtype=np.int32)
    c3t = np.frombuffer(k.read_col(4), dtype=np.int32)
    c2a = np.frombuffer(k.read_col(5), dtype=np.int32)
    c2b = np.frombuffer(k.read_col(6), dtype=np.int32)
    c1q = np.frombuffer(k.read_col(7), dtype=np.int32)
    b3 = base[p3]; b2 = base[p2]; b1 = base[p1]

    # ---- conditional depth (raw bytes) -----------------------------------
    depth = np.zeros(n, dtype=np.int32)
    pp = np.flatnonzero((ops == 0x81) | (ops == 0x01))
    cur = 0; prev = 0
    for p in pp:
        if p > prev:
            depth[prev:p] = cur
        if ops[p] == 0x81:
            depth[p] = cur; cur += 1
        else:
            cur -= 1; depth[p] = cur
            if cur < 0: cur = 0
        prev = p + 1
    if prev < n: depth[prev:] = cur

    # ---- Toffoli inventory ----------------------------------------------
    tof = np.flatnonzero(is3 := np.isin(base, list(TOF3)))
    tof3 = np.searchsorted(p3, tof)
    tgt = c3t[tof3].astype(np.int64)
    kind = b3[tof3]
    dep = depth[tof]
    cond = flagged[tof] != 0
    tgt_anc = is_anc[tgt]
    print(f'\nToffoli-like ops: {len(tof)}')
    print('  by opcode: ', {hex(int(k)): int((kind == k).sum()) for k in (0x30, 0x31, 0x32)})
    print('  by depth:  ', dict(collections.Counter(dep.tolist())))
    print('  target is an ANCILLA (workspace):', int(tgt_anc.sum()))
    print('  target is a SYNDROME (output)  :', int((~tgt_anc).sum()))
    print('  unconditional (depth 0):', int((dep == 0).sum()),
          ' of which target ancilla:', int(((dep == 0) & tgt_anc).sum()))
    print('  per-target-wire Toffoli counts (top 12):')
    cnt = collections.Counter(tgt.tolist())
    for w, c_ in cnt.most_common(12):
        print(f'    wire {w:4d} ({"anc" if is_anc[w] else "syn"}): {c_:,}')

    # ---- HMR (measurement) inventory ------------------------------------
    hmr = p1[b1 == 0x50]
    hmr_w = c1q[b1 == 0x50].astype(np.int64)
    print(f'\nHMR measurements: {len(hmr)}  distinct wires: {len(set(hmr_w.tolist()))}')
    meas_wire = set(hmr_w.tolist())
    anc_meas = sorted(w for w in meas_wire if is_anc[w])
    print(f'  measurements on ANCILLA wires: {len(anc_meas)} -> {anc_meas[:20]}')

    # ---- per-wire events restricted to the 60 ANCILLA wires -------------
    # (the syndrome wires are outputs: their value is the answer, so a
    #  measure-first rewrite cannot apply to them)
    anc_set = set(anc.tolist())
    reads = collections.defaultdict(list)
    writes = collections.defaultdict(list)
    swcz = (b2 == 0x20) | (b2 == 0x22)
    ccz3 = (b3 == 0x30) | (b3 == 0x32)
    iscx = b2 == 0x21; issw2 = b2 == 0x22; isccx3 = b3 == 0x31; issw3 = b3 == 0x32

    def collect(wires, poss, sink):
        m = lut_anc[wires]
        if m.any():
            for ww, pp in zip(wires[m].tolist(), poss[m].tolist()):
                sink[ww].append(pp)

    # cheap membership test via a 1024-entry LUT
    lut_anc = np.zeros(1024, dtype=bool); lut_anc[anc] = True

    def collect2(wires, poss, sink):
        m = lut_anc[wires]
        if m.any():
            for ww, pp in zip(wires[m].tolist(), poss[m].tolist()):
                sink[ww].append(pp)

    collect2(c2a, p2, reads)                      # every 2q op reads operand 1
    collect2(c2b[swcz], p2[swcz], reads)          # CZ/SWAP read operand 2
    collect2(c3a, p3, reads)
    collect2(c3b, p3, reads)
    collect2(c3t[ccz3], p3[ccz3], reads)
    collect2(c1q, p1, reads)
    for w in reads: reads[w].sort()

    meas_by_wire = collections.defaultdict(list)
    for w, p in zip(hmr_w.tolist(), hmr.tolist()): meas_by_wire[w].append(p)
    for w in meas_by_wire: meas_by_wire[w].sort()

    # ---- per-Toffoli site analysis --------------------------------------
    # A Toffoli CCX(c1,c2,T) is a MEASURE-FIRST candidate if:
    #   (a) T is an ancilla (a workspace wire, never an output),
    #   (b) T is later MEASURED (HMR) -- the phase can be replayed,
    #   (c) T is not READ quantumly between this Toffoli and that HMR.
    # (d) additionally the Toffoli must be EXECUTED: depth 0 or a hot region.
    # ---- MEASURE-FIRST site test -----------------------------------------
    # A Toffoli CCX(c1,c2,T) is a MEASURE-FIRST candidate when
    #   (a) T is an ANCILLA (a workspace wire -- the syndrome wires carry the
    #       circuit's ANSWER, so their value cannot be traded for a phase);
    #   (b) T is MEASURED (HMR) at some position m with p < m < next_read(T),
    #       i.e. between the gate and that measurement T is not read quantumly
    #       (only written, and writes commute as XORs);
    #   (c) the measurement m is itself unconditional (depth 0), so the
    #       measurement always happens and the phase replay is well defined.
    # arsen123's implementation additionally handles sites inside nested
    # conditions by popping/restoring the condition masks around the hoisted
    # measurement, so a site at depth >= 1 is still usable PROVIDED the
    # measurement is at depth 0.
    cand = 0; cand_uncond = 0; reasons = collections.Counter()
    first_site = []
    per_wire_cand = collections.Counter()
    per_wire_cand_uncond = collections.Counter()
    cand_by_depth = collections.Counter()
    # group the Toffolis by target ancilla for a per-wire scan
    order = np.argsort(tgt, kind='stable')
    cur_T = None
    ccx_idx = np.flatnonzero(kind == 0x31)
    for i in ccx_idx:
        T = int(tgt[i]); p = int(tof[i])
        if not is_anc[T]:
            reasons['target_is_syndrome'] += 1; continue
        ms = meas_by_wire.get(T)
        if not ms:
            reasons['target_never_measured'] += 1; continue
        rr = reads.get(T, [])
        # next read of T strictly after p
        lo_r = int(np.searchsorted(rr, p, side='right'))
        r_next = rr[lo_r] if lo_r < len(rr) else (1 << 62)
        # first measurement of T strictly after p
        lo_m = int(np.searchsorted(ms, p, side='right'))
        if lo_m >= len(ms):
            reasons['no_later_measurement'] += 1; continue
        mpos = ms[lo_m]
        if mpos >= r_next:
            reasons['read_before_measurement'] += 1; continue
        # the measurement must be unconditional
        mdep = int(depth[mpos])
        if mdep != 0:
            reasons['measurement_conditional'] += 1; continue
        cand += 1
        cand_by_depth[int(dep[i])] += 1
        per_wire_cand[T] += 1
        if dep[i] == 0:
            cand_uncond += 1
            per_wire_cand_uncond[T] += 1
            if len(first_site) < 12:
                first_site.append((int(tof[i]), T, int(c3a[tof3[i]]), int(c3b[tof3[i]]),
                                   int(dep[i]), mpos - p))
    print(f'\nMEASURE-FIRST candidate sites (CCX targeting an ancilla, measured '
          f'unconditionally before its next read): {cand}')
    print(f'  of which at depth 0 (ALWAYS executed): {cand_uncond}')
    print(f'  by depth of the gate: {dict(cand_by_depth)}')
    print('  rejection reasons:', dict(reasons))
    for s in first_site:
        print(f'    pos={s[0]} ancT={s[1]} c1={s[2]} c2={s[3]} depth={s[4]} '
              f'meas_in={s[5]}')
    print('  per-wire unconditional candidate counts (top 15):')
    for w, c_ in per_wire_cand_uncond.most_common(15):
        print(f'    ancilla {w:4d}: {c_:,} unconditional candidates '
              f'({per_wire_cand[w]:,} total)')

    out = {
        'qubits': int(c.num_qubits), 'syndrome': int(len(sq)), 'ancilla': int(len(anc)),
        'tof_total': int(len(tof)),
        'tof_target_ancilla': int(tgt_anc.sum()),
        'tof_target_syndrome': int((~tgt_anc).sum()),
        'tof_depth_hist': {str(k): int(v) for k, v in collections.Counter(dep.tolist()).items()},
        'tof_uncond_ancilla_target': int(((dep == 0) & tgt_anc).sum()),
        'hmr_total': int(len(hmr)), 'hmr_ancilla_wires': int(len(anc_meas)),
        'measure_first_candidates': int(cand),
        'measure_first_depth0': int(cand_uncond),
        'reasons': dict(reasons),
    }
    if '--json' in sys.argv:
        p = sys.argv[sys.argv.index('--json') + 1]
        pathlib.Path(p).write_text(json.dumps(out, indent=1))
        print('wrote', p)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
