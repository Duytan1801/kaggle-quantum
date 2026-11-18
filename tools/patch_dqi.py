#!/usr/bin/env python3
"""patch_dqi.py — generalized boristown DQI patcher (cmerge + HW-27) for candidate search.

Derived from boristown's deterministic patcher (`4b350932 -> ccc2ab84`, recovered from
their public kernel's embedded bundle). We generalize it so we can search for MORE
savings on any dqi .kmb:

  * `_apply_cmerge` merges runs of static CCX ops that share controls into an
    anchor-control form with CX ops (each merged CCX is one fewer Toffoli).
  * `_apply_hw27` rewrites a CCX whose target is later HMR-measured into
    HMR + conditional op (the "HW-27" identity).

Both are structural rewrites; correctness is checked by the official verifier
(in-kernel, 102,400 shots) — never by this script.

Usage:
  python patch_dqi.py <src.kmb> <dst.kmb> [--cmerge] [--hw27] [--report]
"""
from __future__ import annotations

import hashlib
import pathlib
import struct
import sys

import numpy as np

MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")


def _unpack_kmb(raw: bytes):
    assert raw[:16] == MAGIC, "not a kickmix .kmb"
    h = struct.unpack_from("<4I9Q", raw, 16)
    pos, regs, secs = 104, [], {}
    while pos < len(raw):
        idx, size = struct.unpack_from("<QQ", raw, pos)
        pay = raw[pos + 16: pos + 16 + size]
        if idx == 0:
            regs.append(pay)
        else:
            secs[idx] = np.frombuffer(pay, dtype=np.uint8 if idx == 1 else np.uint32).copy() if idx <= 9 else pay
        pos += 16 + size
    return h, regs, secs


def _pack_kmb(h, regs, secs) -> bytes:
    ops = secs[1]
    static_t = int(np.isin(ops & 127, [0x30, 0x31, 0x32]).sum())
    hdr = MAGIC + struct.pack(
        "<4I9Q", h[0], h[1], h[2], h[3], len(ops), static_t, len(secs[5]), len(secs[7]), len(secs[8]), len(secs[9]), h[10], h[11], h[12]
    )
    chunks = [hdr] + [struct.pack("<QQ", 0, len(r)) + r for r in regs]
    for i in range(1, 12):
        pay = secs[i].tobytes() if i <= 9 else secs[i]
        chunks.append(struct.pack("<QQ", i, len(pay)) + pay)
    return b"".join(chunks)


def static_counts(secs):
    ops = secs[1] & 127
    return {
        'ops': int(len(ops)),
        'CCX': int((ops == 0x31).sum()),
        'CCZ': int((ops == 0x32).sum()),
        'CCX_dyn': int((ops == 0x30).sum()),
        'CX': int((ops == 0x21).sum()),
        'CZ': int((ops == 0x22).sum()),
        'HMR': int((ops == 0x50).sum()),
    }


def _apply_cmerge(secs, verbose=False) -> int:
    ops = secs[1]
    is31 = ops == 0x31
    pad = np.concatenate([[False], is31, [False]])
    starts = np.flatnonzero(pad[1:] & ~pad[:-1])
    ends = np.flatnonzero(~pad[1:] & pad[:-1])
    is3 = np.isin(ops & 127, [0x30, 0x31, 0x32])
    is2 = np.isin(ops & 127, [0x20, 0x21, 0x22])
    pref3 = np.cumsum(is3, dtype=np.int64)
    pref2 = np.cumsum(is2, dtype=np.int64)
    a3, b3, t3 = secs[2], secs[3], secs[4]
    a2, t2 = secs[5], secs[6]

    op_parts, a3_p, b3_p, t3_p, a2_p, t2_p = [], [], [], [], [], []
    po = p3 = p2 = 0
    merged = 0
    for s, e in zip(starts.tolist(), ends.tolist()):
        if e - s < 4:
            continue
        i3 = int(pref3[s]) - 1
        L = e - s
        aa, bb, tt = a3[i3:i3 + L].tolist(), b3[i3:i3 + L].tolist(), t3[i3:i3 + L].tolist()
        if len(set(zip(bb, tt))) >= L:
            continue
        if not (set(aa).isdisjoint(set(bb) | set(tt)) and len(set(tt)) == len(set(zip(bb, tt)))):
            if verbose:
                print('  cmerge: skipped block (structure not the full-equal partition)')
            continue
        by_ctrl: dict[int, list[tuple[int, int]]] = {}
        for x, y, z in zip(aa, bb, tt):
            by_ctrl.setdefault(x, []).append((y, z))
        anchor = max(by_ctrl, key=lambda k: (len(by_ctrl[k]), k))
        others = sorted(k for k in by_ctrl if k != anchor)
        shared = set.intersection(*(set(by_ctrl[k]) for k in [anchor] + others))
        unshared_anchor = [p for p in by_ctrl[anchor] if p not in shared]
        if not (all(set(by_ctrl[k]) == shared for k in others) and len(shared) >= 2):
            if verbose:
                print('  cmerge: skipped block (partition not exact)')
            continue
        i2 = int(pref2[s])
        op_parts.append(ops[po:s])
        a3_p.append(a3[p3:i3]); b3_p.append(b3[p3:i3]); t3_p.append(t3[p3:i3])
        a2_p.append(a2[p2:i2]); t2_p.append(t2[p2:i2])
        new_triples = [(anchor, y, z) for y, z in unshared_anchor] + [(anchor, y, z) for y, z in by_ctrl[anchor] if (y, z) in shared]
        new_ops = ([0x31] * len(unshared_anchor)) + ([0x21] * len(others)) + ([0x31] * len(shared)) + ([0x21] * len(others))
        new_2q = [(o, anchor) for o in others] + [(o, anchor) for o in reversed(others)]
        op_parts.append(np.array(new_ops, dtype=np.uint8))
        a3_p.append(np.array([u[0] for u in new_triples], dtype=np.uint32))
        b3_p.append(np.array([u[1] for u in new_triples], dtype=np.uint32))
        t3_p.append(np.array([u[2] for u in new_triples], dtype=np.uint32))
        a2_p.append(np.array([u[0] for u in new_2q], dtype=np.uint32))
        t2_p.append(np.array([u[1] for u in new_2q], dtype=np.uint32))
        po, p3, p2 = e, i3 + L, i2
        merged += 1
    op_parts.append(ops[po:])
    a3_p.append(a3[p3:]); b3_p.append(b3[p3:]); t3_p.append(t3[p3:])
    a2_p.append(a2[p2:]); t2_p.append(t2[p2:])
    secs[1] = np.concatenate(op_parts)
    secs[2], secs[3], secs[4] = np.concatenate(a3_p), np.concatenate(b3_p), np.concatenate(t3_p)
    secs[5], secs[6] = np.concatenate(a2_p), np.concatenate(t2_p)
    return merged


def _hw27_sites(secs, wire_filter=None):
    """Detect HW-27 sites (boristown's pattern, generalized off the hard-coded wire)."""
    ops = secs[1]
    base = ops & 127
    is3 = np.isin(base, [0x30, 0x31, 0x32])
    is2 = np.isin(base, [0x20, 0x21, 0x22])
    is1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
    isb = np.isin(base, [0x40, 0x41, 0x42, 0x50])
    isc = (ops & 128) != 0
    pos3 = np.flatnonzero(is3)
    hmr_pos = np.flatnonzero(ops == 0x50)
    pref1 = np.cumsum(is1, dtype=np.int64)
    pref2 = np.cumsum(is2, dtype=np.int64)
    pref3 = np.cumsum(is3, dtype=np.int64)
    prefb = np.cumsum(isb, dtype=np.int64)
    prefc = np.cumsum(isc, dtype=np.int64)
    a3, b3, t3 = secs[2], secs[3], secs[4]
    a2, t2, a1, cb, conds = secs[5], secs[6], secs[7], secs[8], secs[9]
    if wire_filter is None:
        wires = [864]
    else:
        wires = list(wire_filter)
    sites = []
    for w in wires:
        q_hmrs = hmr_pos[a1[pref1[hmr_pos] - 1] == w]
        ccx_w = np.flatnonzero((ops[pos3] == 0x31) & (t3 == w))
        for i3 in ccx_w.tolist():
            op_c = int(pos3[i3])
            idx_h = int(np.searchsorted(q_hmrs, op_c + 1))
            if idx_h >= len(q_hmrs):
                continue
            op_h = int(q_hmrs[idx_h])
            i1_lo, i1_hi = int(pref1[op_c]), int(pref1[op_h - 1])
            i2_lo, i2_hi = int(pref2[op_c]), int(pref2[op_h - 1])
            i3_lo, i3_hi = int(pref3[op_c]), int(pref3[op_h - 1])
            if (np.any(a1[i1_lo:i1_hi] == w) or np.any(a2[i2_lo:i2_hi] == w) or np.any(t2[i2_lo:i2_hi] == w)
                    or np.any(a3[i3_lo:i3_hi] == w) or np.any(b3[i3_lo:i3_hi] == w) or np.any(t3[i3_lo:i3_hi] == w)):
                continue
            b_out = int(cb[int(prefb[op_h]) - 1])
            if np.any(cb[int(prefb[op_c]):int(prefb[op_h - 1])] == b_out) or np.any(conds[int(prefc[op_c]):int(prefc[op_h])] == b_out):
                continue
            sites.append((op_c, i3, op_h))
    sites.sort()
    return sites


def _apply_hw27(secs, sites) -> None:
    ops = secs[1]
    base = ops & 127
    is3 = np.isin(base, [0x30, 0x31, 0x32])
    is2 = np.isin(base, [0x20, 0x21, 0x22])
    is1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
    isb = np.isin(base, [0x40, 0x41, 0x42, 0x50])
    isc = (ops & 128) != 0
    pref1 = np.cumsum(is1, dtype=np.int64)
    pref2 = np.cumsum(is2, dtype=np.int64)
    pref3 = np.cumsum(is3, dtype=np.int64)
    prefb = np.cumsum(isb, dtype=np.int64)
    prefc = np.cumsum(isc, dtype=np.int64)
    a3, b3, t3 = secs[2], secs[3], secs[4]
    a2, t2, a1, cb, conds = secs[5], secs[6], secs[7], secs[8], secs[9]
    op_out, a3_keep = [], np.ones(len(a3), dtype=bool)
    a2_p, t2_p, a1_p, cb_p, cd_p = [], [], [], [], []
    po = p2 = p1 = pb = pc = 0
    for op_c, i3, op_h in sites:
        a3_keep[i3] = False
        i2_c, i1_c, ib_c, ic_c = int(pref2[op_c]), int(pref1[op_c]), int(prefb[op_c]), int(prefc[op_c])
        i2_h, i1_h, ib_h, ic_h = int(pref2[op_h]), int(pref1[op_h]) - 1, int(prefb[op_h]) - 1, int(prefc[op_h])
        b_out = cb[ib_h]
        w = int(t3[i3])
        op_out.extend([ops[po:op_c], np.array([0x50, 0xA0], dtype=np.uint8), ops[op_c + 1:op_h]])
        a2_p.extend([a2[p2:i2_c], np.array([a3[i3]], dtype=np.uint32), a2[i2_c:i2_h]])
        t2_p.extend([t2[p2:i2_c], np.array([b3[i3]], dtype=np.uint32), t2[i2_c:i2_h]])
        a1_p.extend([a1[p1:i1_c], np.array([w], dtype=np.uint32), a1[i1_c:i1_h]])
        cb_p.extend([cb[pb:ib_c], np.array([b_out], dtype=np.uint32), cb[ib_c:ib_h]])
        cd_p.extend([conds[pc:ic_c], np.array([b_out], dtype=np.uint32), cd_p[ic_c:ic_h]])
        po, p2, p1, pb, pc = op_h + 1, i2_h, i1_h + 1, ib_h + 1, ic_h
    op_out.append(ops[po:])
    a2_p.append(a2[p2:]); t2_p.append(t2[p2:])
    a1_p.append(a1[p1:]); cb_p.append(cb[pb:]); cd_p.append(conds[pc:])
    secs[1] = np.concatenate(op_out)
    secs[2], secs[3], secs[4] = a3[a3_keep], b3[a3_keep], t3[a3_keep]
    secs[5], secs[6] = np.concatenate(a2_p), np.concatenate(t2_p)
    secs[7], secs[8], secs[9] = np.concatenate(a1_p), np.concatenate(cb_p), np.concatenate(cd_p)


def main():
    src = pathlib.Path(sys.argv[1])
    dst = pathlib.Path(sys.argv[2])
    do_cmerge = '--cmerge' in sys.argv
    do_hw27 = '--hw27' in sys.argv
    raw = src.read_bytes()
    h, regs, secs = _unpack_kmb(raw)
    print('source sha256:', hashlib.sha256(raw).hexdigest())
    print('before:', static_counts(secs))
    if do_cmerge:
        m = _apply_cmerge(secs, verbose=True)
        print('cmerge blocks merged:', m)
        print('after cmerge:', static_counts(secs))
    if do_hw27:
        sites = _hw27_sites(secs)
        print('hw27 sites found:', len(sites), sites[:12])
        if sites:
            _apply_hw27(secs, sites)
            print('after hw27:', static_counts(secs))
    out = _pack_kmb(h, regs, secs)
    dst.write_bytes(out)
    print('written:', dst, dst.stat().st_size, 'sha256:', hashlib.sha256(out).hexdigest())


if __name__ == '__main__':
    main()
