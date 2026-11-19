"""Static motif detectors over the op table (one streaming pass + vectorized helpers).

All detectors are sound only in the static sense stated next to them: they look at wire identities and write
versions, not at values (see values.py for the value-level checks).  Every finding carries the op indices so it
can be checked by simulation before anything is rebuilt.
"""
from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np

from . import kmx

CHUNK = 1_000_000


@dataclass
class StructScan:
    census: dict = field(default_factory=dict)
    toffoli_kinds: Counter = field(default_factory=Counter)
    cond_toffolis: int = 0
    depth_hist: Counter = field(default_factory=Counter)          # multiplicative depth of each Toffoli output
    cancel_pairs: list = field(default_factory=list)              # (op1, op2): identical Toffoli twice, nothing changed
    toffoli_uncompute: list = field(default_factory=list)         # (op1, op2, reset op): 2nd CCX zeroes a fresh AND -> MBU
    same_operands: list = field(default_factory=list)             # (op1, op2, t1 still holds product?) repeated product
    dead_writes: list = field(default_factory=list)               # CCX whose target is only written until an HMR
    const_control: list = field(default_factory=list)             # Toffoli with a never-written (|0>) control
    mbu_erasures: int = 0                                         # HMR of a wire whose last write was a CCX
    ladders: list = field(default_factory=list)                   # (start op, end op, length) carry-like chains
    fanout_runs: Counter = field(default_factory=Counter)         # CX runs with one control: run length histogram
    n_and_compute: int = 0                                        # CCX into a fresh (|0>) wire


def census(circ: kmx.Circuit) -> dict:
    cnt = np.bincount(circ.op, minlength=len(kmx.OPS))
    condm = circ.conditional()
    ccnt = np.bincount(circ.op[condm], minlength=len(kmx.OPS))
    out = {}
    for i, n in enumerate(kmx.OPS):
        if cnt[i]:
            out[n] = dict(total=int(cnt[i]), conditional=int(ccnt[i]))
    tof = int(cnt[kmx.CCX] + cnt[kmx.CCZ] + cnt[kmx.CSWAP])
    out["_static_toffoli"] = tof
    out["_conditional_toffoli"] = int(ccnt[kmx.CCX] + ccnt[kmx.CCZ] + ccnt[kmx.CSWAP])
    return out


def scan(circ: kmx.Circuit, window_ladder: int = 64, max_list: int = 200_000) -> StructScan:
    """One pass over all qubit ops. Python loop, about 1 us/op (DQI: 1-2 minutes).

    Per wire it tracks: write version, read counter, |0>-freshness, multiplicative depth, last Toffoli source.
    """
    S = StructScan()
    S.census = census(circ)
    nq = circ.num_qubits
    reg = set(circ.input_qubits().tolist())
    ver = [0] * nq
    rd = [0] * nq
    fresh = [q not in reg for q in range(nq)]
    depth = [0] * nq
    last_tof = [-1] * nq
    last_write_ccx = [-1] * nq
    pend_write = [None] * nq
    prods: dict = {}
    tofkey: dict = {}
    ladder_len = {}
    ladder_start = {}
    cur_run_src = -1; cur_run = 0
    OP = circ.op; A = circ.a; B = circ.b; Cc = circ.c; CON = circ.cond; DEP = circ.depth
    n = circ.n_ops
    for s in range(0, n, CHUNK):
        e = min(n, s + CHUNK)
        ops = OP[s:e].tolist(); aa = A[s:e].tolist(); bb = B[s:e].tolist(); cc = Cc[s:e].tolist()
        cn = CON[s:e].tolist(); dp = DEP[s:e].tolist()
        for i in range(e - s):
            o = ops[i]
            if o >= kmx.BINV:
                continue
            k = s + i
            a = aa[i]
            conditional = cn[i] >= 0 or dp[i] > 0
            if o == kmx.CX:
                b = bb[i]
                if a == cur_run_src:
                    cur_run += 1
                else:
                    if cur_run:
                        S.fanout_runs[cur_run] += 1
                    cur_run_src = a; cur_run = 1
                rd[a] += 1; pend_write[a] = None
                ver[b] += 1
                depth[b] = depth[a] if fresh[b] else max(depth[b], depth[a])
                if last_tof[a] > last_tof[b]:
                    last_tof[b] = last_tof[a]
                fresh[b] = fresh[b] and fresh[a] and not conditional
                last_write_ccx[b] = -1
                continue
            if cur_run:
                S.fanout_runs[cur_run] += 1
                cur_run = 0; cur_run_src = -1
            if o == kmx.CCX:
                b = bb[i]; t = cc[i]
                if conditional:
                    S.cond_toffolis += 1
                rd[a] += 1; rd[b] += 1; pend_write[a] = None; pend_write[b] = None
                if (fresh[a] or fresh[b]) and len(S.const_control) < max_list:
                    S.const_control.append(k)
                x, y = (a, b) if a < b else (b, a)
                pk = (x, ver[x], y, ver[y])
                was_fresh = fresh[t]
                d = max(depth[a], depth[b]) + 1
                prev = tofkey.pop(pk + (t, ver[t]), None)
                ver[t] += 1
                if prev is not None:
                    k1, rd1, fresh1 = prev
                    if rd[t] == rd1:
                        S.cancel_pairs.append((k1, k))
                        S.toffoli_kinds["CCX cancels an earlier identical CCX"] += 1
                    elif fresh1:
                        S.toffoli_uncompute.append((k1, k))
                        S.toffoli_kinds["CCX uncompute (Toffoli-erases an AND)"] += 1
                    else:
                        S.toffoli_kinds["CCX xor-out (same product, target unchanged)"] += 1
                    fresh[t] = fresh1 and not conditional
                    depth[t] = 0 if fresh[t] else depth[t]
                    last_write_ccx[t] = -1
                    pend_write[t] = None
                    continue
                tofkey[pk + (t, ver[t])] = (k, rd[t], was_fresh and not conditional)
                lst = prods.get(pk)
                if lst is not None:
                    p_op, p_t, p_vt = lst[-1]
                    holds = (ver[p_t] == p_vt) and p_t != t
                    if len(S.same_operands) < max_list:
                        S.same_operands.append((p_op, k, holds))
                    lst.append((k, t, ver[t]))
                else:
                    prods[pk] = [(k, t, ver[t])]
                if was_fresh and not conditional:
                    S.n_and_compute += 1
                    S.toffoli_kinds["CCX->fresh (AND compute)"] += 1
                    last_write_ccx[t] = k
                else:
                    S.toffoli_kinds["CCX conditional" if conditional else "CCX->busy (accumulate)"] += 1
                    last_write_ccx[t] = -1
                par = max(last_tof[a], last_tof[b])
                if par >= 0 and k - par <= window_ladder and par in ladder_len:
                    ladder_len[k] = ladder_len[par] + 1
                    ladder_start[k] = ladder_start[par]
                else:
                    ladder_len[k] = 1; ladder_start[k] = k
                if pend_write[t] is None:
                    pend_write[t] = [k]
                else:
                    pend_write[t].append(k)
                depth[t] = d if was_fresh else max(depth[t], d)
                last_tof[t] = k
                fresh[t] = False
                S.depth_hist[d] += 1
                continue
            if o == kmx.CSWAP:
                b = bb[i]; c = cc[i]
                if conditional:
                    S.cond_toffolis += 1
                S.toffoli_kinds["CSWAP"] += 1
                for w in (a, b, c):
                    rd[w] += 1; pend_write[w] = None
                if fresh[a] and len(S.const_control) < max_list:
                    S.const_control.append(k)
                d = max(depth[a], depth[b], depth[c]) + 1
                both = fresh[b] and fresh[c]
                for w in (b, c):
                    ver[w] += 1; depth[w] = d; last_tof[w] = k; last_write_ccx[w] = -1
                    fresh[w] = both
                S.depth_hist[d] += 1
                continue
            if o == kmx.CCZ:
                b = bb[i]; c = cc[i]
                if conditional:
                    S.cond_toffolis += 1
                S.toffoli_kinds["CCZ"] += 1
                if (fresh[a] or fresh[b] or fresh[c]) and len(S.const_control) < max_list:
                    S.const_control.append(k)
                key = ("Z",) + tuple(sorted(((a, ver[a]), (b, ver[b]), (c, ver[c]))))
                prev = tofkey.pop(key, None)
                if prev is not None:
                    S.cancel_pairs.append((prev[0], k))
                else:
                    tofkey[key] = (k, 0, False)
                for w in (a, b, c):
                    rd[w] += 1; pend_write[w] = None
                S.depth_hist[max(depth[a], depth[b], depth[c]) + 1] += 1
                continue
            if o == kmx.HMR or o == kmx.R:
                if not conditional:
                    if o == kmx.HMR:
                        if last_write_ccx[a] >= 0:
                            S.mbu_erasures += 1
                        pw = pend_write[a]
                        if pw is not None and len(S.dead_writes) < max_list:
                            S.dead_writes.extend((w, k) for w in pw)
                    pend_write[a] = None
                    fresh[a] = a not in reg
                    ver[a] += 1; depth[a] = 0; last_tof[a] = -1; last_write_ccx[a] = -1
                else:
                    rd[a] += 1; pend_write[a] = None; ver[a] += 1; fresh[a] = False
                continue
            if o == kmx.X:
                ver[a] += 1; fresh[a] = False; last_write_ccx[a] = -1
                continue
            if o == kmx.SWAP:
                b = bb[i]
                rd[a] += 1; rd[b] += 1; pend_write[a] = None; pend_write[b] = None
                ver[a] += 1; ver[b] += 1
                fresh[a], fresh[b] = fresh[b], fresh[a]
                depth[a], depth[b] = depth[b], depth[a]
                last_tof[a], last_tof[b] = last_tof[b], last_tof[a]
                last_write_ccx[a] = last_write_ccx[b] = -1
                continue
            if o == kmx.CZ:
                b = bb[i]
                rd[a] += 1; rd[b] += 1; pend_write[a] = None; pend_write[b] = None
            elif a >= 0:
                rd[a] += 1; pend_write[a] = None
    if cur_run:
        S.fanout_runs[cur_run] += 1
    ends = defaultdict(int)
    for k, L in ladder_len.items():
        st = ladder_start[k]
        if L > ends[st]:
            ends[st] = L
    S.ladders = sorted(((st, L) for st, L in ends.items() if L >= 4), key=lambda x: -x[1])
    return S


# ---------------------------------------------------------------------------------------------------------
# Segmentation into gadgets (width valleys) and canonical signatures (equal up to wire renaming)
# ---------------------------------------------------------------------------------------------------------

def segments(circ: kmx.Circuit, width: np.ndarray, block: int = 4096, min_toffoli: int = 1) -> list[tuple[int, int]]:
    """Split the op stream at width valleys: ops where width equals the minimum of its block and rises next."""
    n = len(width)
    nb = (n + block - 1) // block
    pad = np.full(nb * block, np.iinfo(np.int32).max, dtype=np.int64)
    pad[:n] = width
    bmin = pad.reshape(nb, block).min(1)
    base = np.repeat(bmin, block)[:n]
    at_base = width == base
    rise = np.r_[width[1:] > width[:-1], False]
    cut = np.flatnonzero(at_base & rise) + 1
    cut = np.r_[0, cut, n]
    istof = np.isin(circ.op, kmx.TOFFOLI_OPS)
    ctof = np.r_[0, np.cumsum(istof)]
    segs = []
    s0 = 0
    for c in cut[1:].tolist():
        if ctof[c] - ctof[s0] >= min_toffoli:
            segs.append((s0, c))
            s0 = c
        # merge tiny Toffoli-free pieces into the next segment
    if s0 < n and segs:
        segs[-1] = (segs[-1][0], n)
    return segs


def signature(circ: kmx.Circuit, s: int, e: int) -> tuple[str, int, int]:
    """Canonical hash of ops s..e-1 (qubit ops only), wires renamed in first-appearance order."""
    op = circ.op[s:e]
    m = op < kmx.BINV
    op = op[m]
    W = np.stack([circ.a[s:e][m], circ.b[s:e][m], circ.c[s:e][m]], 1).astype(np.int64)
    flat = W.ravel()
    valid = flat >= 0
    vals = flat[valid]
    if len(vals):
        uniq, first_idx, inv = np.unique(vals, return_index=True, return_inverse=True)
        rank = np.empty(len(uniq), dtype=np.int64)
        rank[np.argsort(first_idx)] = np.arange(len(uniq))
        canon = np.full(len(flat), -1, dtype=np.int64)
        canon[valid] = rank[inv]
    else:
        canon = flat
        uniq = vals
    condf = ((circ.cond[s:e][m] >= 0) | (circ.depth[s:e][m] > 0)).astype(np.int64)
    blob = np.concatenate([op.astype(np.int64), canon, condf]).tobytes()
    ntof = int(np.isin(op, kmx.TOFFOLI_OPS).sum())
    return hashlib.blake2b(blob, digest_size=10).hexdigest(), ntof, len(uniq)


def gadget_census(circ: kmx.Circuit, width: np.ndarray, block: int = 4096, top: int = 25) -> dict:
    segs = segments(circ, width, block)
    groups: dict = {}
    for s, e in segs:
        h, nt, nw = signature(circ, s, e)
        g = groups.get(h)
        if g is None:
            groups[h] = dict(sig=h, instances=1, toffoli_each=nt, wires=nw, ops=e - s, first=s, peak=int(width[s:e].max()))
        else:
            g["instances"] += 1
    rows = sorted(groups.values(), key=lambda g: -g["instances"] * g["toffoli_each"])
    tot = sum(g["instances"] * g["toffoli_each"] for g in rows)
    return dict(n_segments=len(segs), n_distinct=len(rows), total_toffoli=tot, top=rows[:top],
                repeated_share=sum(g["instances"] * g["toffoli_each"] for g in rows if g["instances"] > 1) / max(1, tot))
