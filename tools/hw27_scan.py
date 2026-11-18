#!/usr/bin/env python3
"""hw27_scan.py — find *all* HW-27 (CCX -> HMR+conditional) rewrite sites in a dqi .kmb.

boristown's deterministic patcher (`patch_dqi_ccc2ab84.py`, recovered from their public
kernel) applied the HW-27 identity at 8 sites, all on hard-coded wire 864.  The identity
is structural and does not depend on the wire:

    static CCX(a, b -> w)   ...later...   HMR(w)

can be rewritten as

    HMR(w) ; conditional-op(a, b) [on the bit the HMR reads]

provided that (i) wire w is not touched between the CCX and the HMR, and (ii) the
classical bit read by the HMR is not touched in between.

This scanner generalizes the wire filter to *every* wire and reports the sites, so we
can see whether the 8-site patch left money on the table.

Memory: the .kmb is read once and the sections are exposed as zero-copy numpy views over
the byte buffer (the machine has 7 GB and soft_oomd kills fat pythons).

Usage: hw27_scan.py <file.kmb> [--apply out.kmb]
"""
from __future__ import annotations

import hashlib
import pathlib
import struct
import sys

import numpy as np

MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")

# kickmix op bytes (low 7 bits); bit 7 = conditional flag
OP_CX = 0x21
OP_CZ = 0x22
OP_CCX = 0x31
OP_CCZ = 0x32
OP_HMR = 0x50


def unpack_views(raw: bytes):
    """Return (header, register payloads, sections) with numpy views (no copies)."""
    assert raw[:16] == MAGIC, "not a kickmix .kmb"
    h = struct.unpack_from("<4I9Q", raw, 16)
    pos, regs, secs = 104, [], {}
    while pos < len(raw):
        idx, size = struct.unpack_from("<QQ", raw, pos)
        pay = raw[pos + 16: pos + 16 + size]
        if idx == 0:
            regs.append(pay)
        else:
            secs[idx] = np.frombuffer(pay, dtype=np.uint8 if idx == 1 else np.uint32)
        pos += 16 + size
    return h, regs, secs


def pack_kmb(h, regs, secs) -> bytes:
    ops = secs[1]
    static_t = int(np.isin(ops & 127, [0x30, 0x31, 0x32]).sum())
    hdr = MAGIC + struct.pack(
        "<4I9Q", h[0], h[1], h[2], h[3], len(ops), static_t, len(secs[5]), len(secs[7]),
        len(secs[8]), len(secs[9]), h[10], h[11], h[12]
    )
    chunks = [hdr] + [struct.pack("<QQ", 0, len(r)) + r for r in regs]
    for i in range(1, 12):
        pay = secs[i].tobytes() if i <= 9 else secs[i]
        chunks.append(struct.pack("<QQ", i, len(pay)) + pay)
    return b"".join(chunks)


def prefix_flags(ops):
    base = ops & 127
    is1 = np.isin(base, [0x10, 0x11, 0x12, 0x50])
    is2 = np.isin(base, [0x20, 0x21, 0x22])
    is3 = np.isin(base, [0x30, 0x31, 0x32])
    isb = np.isin(base, [0x40, 0x41, 0x42, 0x50])
    isc = (ops & 128) != 0
    # int32 prefixes: the op stream is < 2^31 long, and int64 would cost 2.3 GB
    return (np.cumsum(is1, dtype=np.int32), np.cumsum(is2, dtype=np.int32),
            np.cumsum(is3, dtype=np.int32), np.cumsum(isb, dtype=np.int32),
            np.cumsum(isc, dtype=np.int32))


def scan_sites(secs, wire_filter=None, verbose=True):
    ops = secs[1]
    pref1, pref2, pref3, prefb, prefc = prefix_flags(ops)
    a3, b3, t3 = secs[2], secs[3], secs[4]
    a2, t2, a1, cb, conds = secs[5], secs[6], secs[7], secs[8], secs[9]
    pos3 = np.flatnonzero(np.isin(ops & 127, [0x30, 0x31, 0x32]))
    hmr_pos = np.flatnonzero(ops == OP_HMR)
    # HMR target wire
    hmr_target = a1[pref1[hmr_pos] - 1]
    # static CCX ops grouped by target wire
    static_ccx = pos3[ops[pos3] == OP_CCX]
    ccx_target = t3[pref3[static_ccx] - 1]

    if wire_filter is None:
        wires = np.unique(np.concatenate([hmr_target, ccx_target]))
    else:
        wires = np.asarray(list(wire_filter))

    sites = []
    for w in wires.tolist():
        q_hmrs = hmr_pos[hmr_target == w]
        if len(q_hmrs) == 0:
            continue
        cand = static_ccx[ccx_target == w]
        if len(cand) == 0:
            continue
        for op_c in cand.tolist():
            op_c = int(op_c)
            i3 = int(pref3[op_c]) - 1
            idx_h = int(np.searchsorted(q_hmrs, op_c + 1))
            if idx_h >= len(q_hmrs):
                continue
            op_h = int(q_hmrs[idx_h])
            i1_lo, i1_hi = int(pref1[op_c]), int(pref1[op_h - 1])
            i2_lo, i2_hi = int(pref2[op_c]), int(pref2[op_h - 1])
            i3_lo, i3_hi = int(pref3[op_c]), int(pref3[op_h - 1])
            if (np.any(a1[i1_lo:i1_hi] == w) or np.any(a2[i2_lo:i2_hi] == w)
                    or np.any(t2[i2_lo:i2_hi] == w) or np.any(a3[i3_lo:i3_hi] == w)
                    or np.any(b3[i3_lo:i3_hi] == w) or np.any(t3[i3_lo:i3_hi] == w)):
                continue
            ib_h = int(prefb[op_h]) - 1
            b_out = int(cb[ib_h])
            ib_c = int(prefb[op_c])
            ic_c, ic_h = int(prefc[op_c]), int(prefc[op_h])
            if (np.any(cb[ib_c:ib_h] == b_out)
                    or np.any(conds[ic_c:ic_h] == b_out)):
                continue
            sites.append((op_c, i3, op_h))
    sites.sort()
    if verbose:
        by_wire = {}
        for op_c, i3, op_h in sites:
            by_wire.setdefault(int(t3[i3]), []).append(op_c)
        print(f"  HW-27 sites found: {len(sites)} on {len(by_wire)} wires")
        top = sorted(by_wire.items(), key=lambda kv: -len(kv[1]))[:15]
        print("  sites per wire (top 15):", [(w, len(v)) for w, v in top])
    return sites


def apply_sites(secs, sites):
    """boristown's rewrite: replace each CCX by (HMR on target, conditional 2q op)."""
    ops = secs[1]
    pref1, pref2, pref3, prefb, prefc = prefix_flags(ops)
    a3, b3, t3 = secs[2], secs[3], secs[4]
    a2, t2, a1, cb, conds = secs[5], secs[6], secs[7], secs[8], secs[9]
    op_out, a3_keep = [], np.ones(len(a3), dtype=bool)
    a2_p, t2_p, a1_p, cb_p, cd_p = [], [], [], [], []
    po = p2 = p1 = pb = pc = 0
    for op_c, i3, op_h in sites:
        a3_keep[i3] = False
        i2_c, i1_c = int(pref2[op_c]), int(pref1[op_c])
        ib_c, ic_c = int(prefb[op_c]), int(prefc[op_c])
        i2_h, i1_h = int(pref2[op_h]), int(pref1[op_h]) - 1
        ib_h, ic_h = int(prefb[op_h]) - 1, int(prefc[op_h])
        b_out = cb[ib_h]
        w = int(t3[i3])
        op_out.extend([ops[po:op_c], np.array([OP_HMR, 0xA0], dtype=np.uint8), ops[op_c + 1:op_h]])
        a2_p.extend([a2[p2:i2_c], np.array([a3[i3]], dtype=np.uint32), a2[i2_c:i2_h]])
        t2_p.extend([t2[p2:i2_c], np.array([b3[i3]], dtype=np.uint32), t2[i2_c:i2_h]])
        a1_p.extend([a1[p1:i1_c], np.array([w], dtype=np.uint32), a1[i1_c:i1_h]])
        cb_p.extend([cb[pb:ib_c], np.array([b_out], dtype=np.uint32), cb[ib_c:ib_h]])
        cd_p.extend([conds[pc:ic_c], np.array([b_out], dtype=np.uint32), conds[ic_c:ic_h]])
        po, p2, p1, pb, pc = op_h + 1, i2_h, i1_h + 1, ib_h + 1, ic_h
    op_out.append(ops[po:])
    a2_p.append(a2[p2:]); t2_p.append(t2[p2:])
    a1_p.append(a1[p1:]); cb_p.append(cb[pb:]); cd_p.append(conds[pc:])
    secs[1] = np.concatenate(op_out)
    secs[2], secs[3], secs[4] = a3[a3_keep].copy(), b3[a3_keep].copy(), t3[a3_keep].copy()
    secs[5], secs[6] = np.concatenate(a2_p), np.concatenate(t2_p)
    secs[7], secs[8], secs[9] = np.concatenate(a1_p), np.concatenate(cb_p), np.concatenate(cd_p)


def counts(secs):
    ops = secs[1] & 127
    return dict(ops=int(len(ops)), CCX=int((ops == OP_CCX).sum()),
                CCZ=int((ops == OP_CCZ).sum()), CCX_dyn=int((ops == 0x30).sum()),
                CX=int((ops == OP_CX).sum()), CZ=int((ops == OP_CZ).sum()),
                HMR=int((ops == OP_HMR).sum()))


def main():
    src = pathlib.Path(sys.argv[1])
    raw = src.read_bytes()
    print("source:", src, len(raw), "bytes  sha256:", hashlib.sha256(raw).hexdigest())
    h, regs, secs = unpack_views(raw)
    print("before:", counts(secs))
    sites = scan_sites(secs)
    if "--apply" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--apply") + 1])
        # need writable copies for the rewrite
        for i in range(1, 12):
            secs[i] = np.array(secs[i], copy=True)
        apply_sites(secs, sites)
        print("after :", counts(secs))
        blob = pack_kmb(h, regs, secs)
        out.write_bytes(blob)
        print("written:", out, out.stat().st_size,
              "sha256:", hashlib.sha256(blob).hexdigest())


if __name__ == "__main__":
    main()
