"""Static qubit liveness: width profile, peak episodes, what opens them, and the idle-gap cover.

Model (wire based, conservative):
* register (input/output) qubits are live from the start and never die;
* any other qubit opens at its first touch after the start or after an unconditional HMR/R, and closes at an
  unconditional HMR or R (the wire is free after that op);
* conditional HMR/R count as touches only.
width_during[t] = wires live while op t executes (the circuit's qubit count is max(width_during) when every
qubit index is used).  Processing is chunked and vectorized, so the 53 M-op DQI file runs in about a minute.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import kmx

CHUNK = 2_000_000


def _touches(circ: kmx.Circuit, s: int, e: int):
    """(op index, wire, closes) for all qubit operands of ops s..e-1."""
    op = circ.op[s:e]
    cond = circ.conditional()[s:e] if (circ.cond[s:e].max(initial=-1) >= 0 or circ.depth[s:e].max(initial=0) > 0) \
        else np.zeros(e - s, dtype=bool)
    idx = np.arange(s, e, dtype=np.int64)
    outs_o, outs_w, outs_c = [], [], []
    closing = ((op == kmx.HMR) | (op == kmx.R)) & ~cond
    for col, is_a in ((circ.a[s:e], True), (circ.b[s:e], False), (circ.c[s:e], False)):
        m = col >= 0
        outs_o.append(idx[m]); outs_w.append(col[m].astype(np.int64))
        outs_c.append(closing[m] if is_a else np.zeros(int(m.sum()), dtype=bool))
    o = np.concatenate(outs_o); w = np.concatenate(outs_w); c = np.concatenate(outs_c)
    order = np.lexsort((o, w))
    return o[order], w[order], c[order]


@dataclass
class Liveness:
    width: np.ndarray                 # width_during per op (int16/int32)
    peak: int
    nq: int
    intervals: list = field(default_factory=list)   # (wire, open op, close op or n_ops) for non-register wires
    opens_at: np.ndarray | None = None              # wire opened at op (or -1) (first opened wire only)

    def peak_ops(self, level: int | None = None) -> np.ndarray:
        lv = self.peak if level is None else level
        return np.flatnonzero(self.width >= lv)

    def episodes(self, level: int | None = None) -> list[tuple[int, int]]:
        """Maximal op ranges [s, e] (inclusive) with width >= level."""
        ops = self.peak_ops(level)
        if len(ops) == 0:
            return []
        brk = np.flatnonzero(np.diff(ops) > 1)
        starts = np.r_[ops[0], ops[brk + 1]]
        ends = np.r_[ops[brk], ops[-1]]
        return list(zip(starts.tolist(), ends.tolist()))


def compute(circ: kmx.Circuit, keep_intervals: bool = True) -> Liveness:
    n = circ.n_ops
    nq = circ.num_qubits
    live = np.zeros(nq, dtype=bool)
    reg = circ.input_qubits()
    live[reg] = True
    open_since = np.full(nq, -1, dtype=np.int64)
    width = np.empty(n, dtype=np.int32)
    opens_at = np.full(n, -1, dtype=np.int32)
    cur = int(live.sum())
    intervals = []
    is_reg = np.zeros(nq, dtype=bool); is_reg[reg] = True
    for s in range(0, n, CHUNK):
        e = min(n, s + CHUNK)
        o, w, c = _touches(circ, s, e)
        if len(o) == 0:
            width[s:e] = cur
            continue
        first = np.r_[True, w[1:] != w[:-1]]
        prev_live = np.empty(len(o), dtype=bool)
        prev_live[first] = live[w[first]]
        nf = ~first
        # live after the previous entry of the same wire = not (previous entry closed it)
        prev_live[nf] = ~c[:-1][nf[1:]] if len(o) > 1 else prev_live[nf]
        # (several operands of one op on the same wire cannot occur in valid kmx)
        opened = ~prev_live & ~c          # HMR/R of a free wire is a no-op on |0>: not an open
        closed = c & prev_live
        d_open = np.bincount(o[opened] - s, minlength=e - s)
        d_close = np.bincount(o[closed] - s, minlength=e - s)
        after = cur + np.cumsum(d_open - d_close)
        before = np.r_[cur, after[:-1]]
        width[s:e] = before + d_open
        oo = o[opened]
        opens_at[oo] = w[opened]
        if keep_intervals:
            # intervals: an open entry and the next close entry of the same wire
            ev_o = np.r_[o[opened], o[closed]]
            ev_w = np.r_[w[opened], w[closed]]
            ev_k = np.r_[np.zeros(int(opened.sum()), dtype=np.int8), np.ones(int(closed.sum()), dtype=np.int8)]
            order = np.lexsort((ev_k, ev_o))
            for oi, wi, ki in zip(ev_o[order].tolist(), ev_w[order].tolist(), ev_k[order].tolist()):
                if is_reg[wi]:
                    continue
                if ki == 0:
                    open_since[wi] = oi
                else:
                    if open_since[wi] >= 0:
                        intervals.append((wi, int(open_since[wi]), oi))
                        open_since[wi] = -1
        # carry state
        last = np.r_[w[1:] != w[:-1], True]
        live[w[last]] = ~c[last]
        cur = int(after[-1])
    for wi in np.flatnonzero(open_since >= 0).tolist():
        intervals.append((wi, int(open_since[wi]), n))
    peak = int(width.max()) if n else 0
    dt = np.int16 if peak < 32000 else np.int32
    return Liveness(width=width.astype(dt), peak=peak, nq=nq, intervals=intervals, opens_at=opens_at)


def episode_report(circ: kmx.Circuit, lv: Liveness, level: int | None = None, max_eps: int = 200_000) -> dict:
    """Peak episodes, the op kinds that open them, and which live wires stay untouched (idle) across each."""
    level = lv.peak if level is None else level
    eps = lv.episodes(level)
    out = dict(level=level, n_episodes=len(eps), ops_at_level=int((lv.width >= level).sum()))
    if not eps:
        return out
    eps = eps[:max_eps]
    starts = np.array([s for s, _ in eps]); ends = np.array([e for _, e in eps])
    # opener: the op at the episode start (it raised the width to `level`)
    opener_kind = {}
    for s in starts.tolist():
        k = kmx.OPS[circ.op[s]]
        if circ.op[s] == kmx.CCX and lv.opens_at[s] == circ.c[s]:
            k = "CCX->fresh (AND/carry temp)"
        elif circ.op[s] == kmx.CX and lv.opens_at[s] == circ.b[s]:
            k = "CX->fresh (copy/accumulator)"
        elif circ.op[s] == kmx.CSWAP:
            k = "CSWAP (touches fresh wire)"
        opener_kind[k] = opener_kind.get(k, 0) + 1
    out["openers"] = dict(sorted(opener_kind.items(), key=lambda kv: -kv[1]))
    # idle matrix: touched[e, w]
    nq = lv.nq
    touched = np.zeros((len(eps), nq), dtype=bool)
    lo, hi = int(starts.min()), int(ends.max()) + 1
    for s in range(lo, hi, CHUNK):
        e = min(hi, s + CHUNK)
        o, w, _ = _touches(circ, s, e)
        k = np.searchsorted(starts, o, side="right") - 1
        ok = (k >= 0) & (o <= ends[np.clip(k, 0, None)])
        touched[k[ok], w[ok]] = True
    # live across the whole episode: from intervals (non-register) + registers
    live_all = np.zeros((len(eps), nq), dtype=bool)
    reg = circ.input_qubits()
    live_all[:, reg] = True
    if lv.intervals:
        iw = np.array([x[0] for x in lv.intervals]); io = np.array([x[1] for x in lv.intervals])
        ic = np.array([x[2] for x in lv.intervals])
        for j, (s, e) in enumerate(eps):
            m = (io < s) & (ic > e)
            live_all[j, iw[m]] = True
    idle = live_all & ~touched
    out["idle_wires_per_episode_min"] = int(idle.sum(1).min())
    out["idle_wires_per_episode_mean"] = float(idle.sum(1).mean())
    # greedy cover: fewest wires such that every episode has an idle chosen wire
    chosen = []
    unc = np.ones(len(eps), dtype=bool)
    weights = (ends - starts + 1)
    while unc.any() and len(chosen) < 64:
        score = (idle[unc] * weights[unc, None]).sum(0)
        wbest = int(score.argmax())
        if score[wbest] == 0:
            break
        cov = idle[:, wbest] & unc
        chosen.append((wbest, int(cov.sum()), int(weights[cov].sum())))
        unc &= ~idle[:, wbest]
    out["greedy_cover"] = chosen
    out["uncoverable_episodes"] = int(unc.sum())
    out["episodes"] = eps[:50]
    return out


def long_lived(lv: Liveness, top: int = 20) -> list[tuple[int, int, int, int]]:
    """Longest non-register live intervals (wire, open, close, length)."""
    iv = sorted(lv.intervals, key=lambda x: -(x[2] - x[1]))[:top]
    return [(w, s, e, e - s) for w, s, e in iv]
