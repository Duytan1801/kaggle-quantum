"""Semistatic analysis: bit-sliced sampled simulation (Python big ints, one bit per sample lane).

One pass over the circuit with S lanes (default 256 samples) gives, per Toffoli, the operand values on every lane.
From those:
* executed-Toffoli mean (conditional Toffolis only count where their condition holds);
* constant / equal / complementary controls (the Toffoli is a no-op or a CX on every sample);
* product fingerprints: two Toffolis with the same product value on every lane compute the same function
  (sharing / retention candidates);
* zero gaps: windows in which a statically live wire holds 0 on every lane between two touches
  (value-level liveness; a free slot for borrowing or for retention);
* the end-state check (inputs restored, ancillas 0, R never resets a 1) that validates the simulator itself.
Phases are not tracked (no Z_POW / CZ semantics needed for value analysis).
Sampling caveat: a property seen on S samples may fail on rare inputs. Every saving it suggests must be
verified exhaustively (invsqrt: kmsim over all x) or on official draws before use.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np

from . import kmx

CHUNK = 1_000_000


@dataclass
class ValueScan:
    lanes: int
    toffoli_exec_mean: float = 0.0
    const0: list = field(default_factory=list)        # Toffoli with product 0 on all active lanes (no-op)
    affine: list = field(default_factory=list)        # CCX whose product equals one control (or a control is 1): a CX
    swap_noop: list = field(default_factory=list)     # CSWAP control 0 or swapped values equal on all lanes
    swap_always: list = field(default_factory=list)   # CSWAP control 1 on all active lanes (plain SWAP)
    repeats: list = field(default_factory=list)       # (first op, op): same nonzero product value as an earlier Toffoli
    repeat_groups: int = 0
    zero_gaps: list = field(default_factory=list)     # (wire, after op, before op) wire is 0 between touches
    end_ok: dict = field(default_factory=dict)
    bad_resets: int = 0
    ops_seen: int = 0
    final: list = field(default_factory=list)       # final lane values per qubit
    snaps: dict = field(default_factory=dict)       # op -> wire values before that op


def _rand(rng: random.Random, S: int) -> int:
    return rng.getrandbits(S)


def lanes_from_ints(values, width: int) -> list[int]:
    """values[l] (one int per lane) -> width lane-ints (bit j of value l at lane l of entry j)."""
    if len(values) > 4096 and width <= 63:
        arr = np.asarray(values, dtype=np.uint64)
        out = []
        for j in range(width):
            bitsj = ((arr >> np.uint64(j)) & np.uint64(1)).astype(np.uint8)
            out.append(int.from_bytes(np.packbits(bitsj, bitorder="little").tobytes(), "little"))
        return out
    out = [0] * width
    for l, v in enumerate(values):
        j = 0
        while v:
            if v & 1:
                out[j] |= 1 << l
            v >>= 1; j += 1
    return out


def inputs_invsqrt(circ: kmx.Circuit, S: int, seed: int = 1, exhaustive: bool = False) -> dict:
    """S random x plus edge cases; exhaustive=True: every x in 1..max_x (S is then max_x = 3,133,452)."""
    rng = random.Random(seed)
    max_x = 3 * (2 ** 10 - 2) ** 2
    if exhaustive:
        reg = circ.regs[next(iter(circ.regs))]
        return {"qubits": dict(zip(reg, lanes_from_ints(np.arange(1, max_x + 1, dtype=np.uint64), len(reg)))), "bits": {},
                "lanes": max_x}
    edge = [1, 2, 3, 4, 63, 64, 65, 255, 256, 4095, 4096, 65535, 65536, 1 << 20, max_x - 1, max_x]
    xs = edge + [rng.randint(1, max_x) for _ in range(S - len(edge))]
    reg = circ.regs[next(iter(circ.regs))]
    return {"qubits": dict(zip(reg, lanes_from_ints(xs[:S], len(reg)))), "bits": {}}


def inputs_chem(circ: kmx.Circuit, S: int = 0, seed: int = 1, n_rows: int = 1220, exhaustive: bool = True,
                k: int | None = None, words=None) -> dict:
    """Loader inputs in the FAMILY context: circuit k sees (a, z) with z = batch k-1 of row a in the forward pass and
    z = batch k in the reverse pass (the circuit is its own inverse on the words: z -> z XOR f_k(a)).

    words: (n_rows, 75) angle words (npz 'angle_words'); k: circuit index (from the file name if None).
    Without words, z = 0 is used, which is only the forward input of circuit 0 (NOT valid for k > 0: the loaders
    read the old word bits, e.g. the gauge bits).  Lanes: 2 * n_rows (forward + reverse inputs), exhaustive.
    """
    import re
    names = {circ.reg_names.get(k_, k_): k_ for k_ in circ.regs}
    sel = circ.regs[names["selection"]]
    wregs = [circ.regs[names[f"word_{j}"]] for j in range(len(names)) if f"word_{j}" in names]
    J = len(wregs)
    if k is None:
        m = re.search(r"angle_k_(\d+)", circ.path or "")
        k = int(m.group(1)) if m else 0
    rows = np.arange(n_rows)
    if words is None:
        addrs = rows; zs = [np.zeros(n_rows, dtype=np.int64)] * J
    else:
        W = np.asarray(words)
        def batch(b):
            cols = [b * J + j for j in range(J)]
            return [W[:, c] if 0 <= c < W.shape[1] and b >= 0 else np.zeros(n_rows, dtype=np.int64) for c in cols]
        prev, cur = batch(k - 1), batch(k)
        addrs = np.r_[rows, rows]
        zs = [np.r_[prev[j], cur[j]] for j in range(J)]
    qubits = dict(zip(sel, lanes_from_ints(addrs.astype(np.uint64) if len(addrs) > 4096 else addrs.tolist(), len(sel))))
    for j in range(J):
        qubits.update(zip(wregs[j], lanes_from_ints(zs[j].tolist(), len(wregs[j]))))
    return {"qubits": qubits, "bits": {}, "lanes": len(addrs), "k": k}


def inputs_dqi(circ: kmx.Circuit, S: int, seed: int = 1) -> dict:
    """Official distribution: weight k ~ w_k^2, k positions, nonzero values; S_i = sum e_j alpha^{(i+1) pos_j};
    GF(2^12) modulus x^12+x^6+x^4+x+1 (0x1053), alpha = x (as in Syed's sources); MBUC bits uniform."""
    import math
    m, nn, deg = 4095, 70, 12
    q = 1 << deg; r = (q - math.isqrt(q)) // 2; l = nn // 2
    kk = np.arange(l + 1, dtype=np.float64)
    off = np.sqrt(kk[1:] * (m - kk[1:] + 1))
    d = (q - 2 * r) / math.sqrt(r * (q - r))
    _, vecs = np.linalg.eigh(np.diag(kk * d) + np.diag(off, 1) + np.diag(off, -1))
    w = np.abs(vecs[:, -1]); w /= np.linalg.norm(w); p = w ** 2; p /= p.sum()
    exp = [0] * (2 * 4095); log = [0] * 4096; x = 1
    for i in range(4095):
        exp[i] = x; log[x] = i; x <<= 1
        if x & 4096:
            x ^= 0x1053
    for i in range(4095, 2 * 4095):
        exp[i] = exp[i - 4095]
    nrng = np.random.default_rng(seed)
    syn = [[0] * nn for _ in range(S)]
    for l_ in range(S):
        k = int(nrng.choice(len(p), p=p))
        pos = nrng.choice(m, size=k, replace=False).tolist()
        vals = nrng.integers(1, q - 1, size=k, endpoint=True).tolist()
        for i in range(nn):
            acc = 0
            for ps, v in zip(pos, vals):
                acc ^= exp[(log[v] + (i + 1) * ps) % 4095]
            syn[l_][i] = acc
    names = {circ.reg_names.get(k, k): k for k in circ.regs}
    qubits = {}
    for i in range(nn):
        reg = circ.regs[names[f"S{i}"]]
        qubits.update(zip(reg, lanes_from_ints([syn[l_][i] for l_ in range(S)], len(reg))))
    rng = random.Random(seed + 7)
    bits = {}
    for nm, bl in circ.bit_regs.items():
        for b in bl:
            bits[b] = rng.getrandbits(S)
    return {"qubits": qubits, "bits": bits}


def run(circ: kmx.Circuit, inputs: dict, S: int = 256, seed: int = 1, min_gap: int = 16,
        max_list: int = 500_000, track_gaps: bool = True, snapshots=None) -> ValueScan:
    """Bit-sliced simulation. ~1-2 us per op in CPython (DQI 53 M ops: a few minutes)."""
    MASK = (1 << S) - 1
    rng = random.Random(seed)
    nq = circ.num_qubits
    nb = max(circ.num_bits, 1)
    q = [0] * nq
    for w, v in inputs["qubits"].items():
        q[w] = v
    init_q = list(q)
    bits = [0] * nb
    for b, v in inputs.get("bits", {}).items():
        bits[b] = v
    reg = set(circ.input_qubits().tolist())
    V = ValueScan(lanes=S)
    tcount = 0
    stack = []          # cumulative masks
    cur = MASK
    seen: dict = {}
    last_touch = [-1] * nq
    zero_after = [w not in reg for w in range(nq)]
    gaps = V.zero_gaps
    OP = circ.op; A = circ.a; B = circ.b; Cc = circ.c; BIT = circ.bit; CON = circ.cond
    n = circ.n_ops
    snap_at = set(snapshots or ())
    V.snaps = {}
    for s in range(0, n, CHUNK):
        e = min(n, s + CHUNK)
        ops = OP[s:e].tolist(); aa = A[s:e].tolist(); bb = B[s:e].tolist(); cc = Cc[s:e].tolist()
        bt = BIT[s:e].tolist(); cn = CON[s:e].tolist()
        for i in range(e - s):
            o = ops[i]
            k = s + i
            if snap_at and k in snap_at:
                V.snaps[k] = list(q)      # wire values just before op k
            if o == kmx.PUSH:
                stack.append(cur); cur &= bits[bt[i]]
                continue
            if o == kmx.POP:
                cur = stack.pop()
                continue
            act = cur if cn[i] < 0 else cur & bits[cn[i]]
            if o >= kmx.BINV:
                b_ = bt[i]
                if o == kmx.BINV:
                    bits[b_] ^= act
                elif o == kmx.BST0:
                    bits[b_] &= ~act
                elif o == kmx.BST1:
                    bits[b_] |= act
                continue
            a = aa[i]
            if track_gaps:
                ws = (a,) if o in (kmx.X, kmx.Z, kmx.ZPOW, kmx.HMR, kmx.R) else \
                     ((a, bb[i]) if o in (kmx.CX, kmx.CZ, kmx.SWAP) else ((a, bb[i], cc[i]) if a >= 0 else ()))
                for w in ws:
                    lt = last_touch[w]
                    if zero_after[w] and lt >= 0 and k - lt >= min_gap and len(gaps) < max_list:
                        gaps.append((w, lt, k))
            if o == kmx.CX:
                b = bb[i]
                q[b] ^= q[a] & act
            elif o == kmx.CCX:
                b = bb[i]; c = cc[i]
                va = q[a] & act; vb = q[b] & act
                p = va & vb
                q[c] ^= p
                tcount += act.bit_count()
                if p == 0:
                    if len(V.const0) < max_list: V.const0.append(k)
                elif p == va or p == vb:
                    if len(V.affine) < max_list: V.affine.append(k)
                else:
                    # isolated: the product lands on a |0> wire, so a CX can copy it out for retention
                    iso = q[c] == p          # (after the XOR) the target was 0 before
                    f = seen.get(p)
                    if f is None:
                        seen[p] = (k, iso)
                    else:
                        fk, ok = f
                        if ok and len(V.repeats) < max_list:
                            V.repeats.append((fk, k))
                        seen[p] = (k, ok or iso)
            elif o == kmx.CCZ:
                b = bb[i]; c = cc[i]
                p = q[a] & q[b] & q[c] & act
                tcount += act.bit_count()
                if p == 0 and len(V.const0) < max_list:
                    V.const0.append(k)
            elif o == kmx.CSWAP:
                b = bb[i]; c = cc[i]
                m = q[a] & act
                tcount += act.bit_count()
                dlt = (q[b] ^ q[c]) & m
                q[b] ^= dlt; q[c] ^= dlt
                if dlt == 0:
                    if len(V.swap_noop) < max_list: V.swap_noop.append(k)
                elif m == act:
                    if len(V.swap_always) < max_list: V.swap_always.append(k)
            elif o == kmx.X:
                q[a] ^= act
            elif o == kmx.SWAP:
                b = bb[i]
                dlt = (q[a] ^ q[b]) & act
                q[a] ^= dlt; q[b] ^= dlt
            elif o == kmx.HMR:
                r_ = rng.getrandbits(S) & act
                b_ = bt[i]
                bits[b_] = (bits[b_] & ~act) | r_
                q[a] &= ~act
            elif o == kmx.R:
                if q[a] & act:
                    V.bad_resets += 1
                q[a] &= ~act
            # CZ, Z, Z_POW, NEG: no value effect
            if track_gaps:
                for w in ws:
                    last_touch[w] = k
                    zero_after[w] = q[w] == 0
    V.ops_seen = n
    V.toffoli_exec_mean = tcount / S
    V.repeat_groups = len(seen)          # distinct nonzero product values
    restored = all(q[w] == init_q[w] for w in reg)
    dirty = [w for w in range(nq) if w not in reg and q[w] != 0]
    V.end_ok = dict(inputs_restored=restored, dirty_ancillas=len(dirty), bad_resets=V.bad_resets)
    V.final = q
    return V


def gap_width_reduction(n_ops: int, gaps: list, width: np.ndarray, block: int = 1) -> np.ndarray:
    """Number of statically-live wires that hold 0 (untouched) at each op, from the zero gaps."""
    d = np.zeros(n_ops + 1, dtype=np.int32)
    if gaps:
        g = np.array(gaps, dtype=np.int64)
        np.add.at(d, g[:, 1] + 1, 1)
        np.add.at(d, g[:, 2], -1)
    return np.cumsum(d)[:n_ops]


def retention_plan(repeats: list, width: np.ndarray, cap: int, block: int = 256, max_len: int | None = None) -> dict:
    """Greedy: keep the product of the first Toffoli on a spare qubit until the repeat (saves 1 Toffoli each).

    Spare capacity per block = cap - (block max of width). Earliest-end-first greedy (optimal for unit capacity).
    Upper bound on free retention at the current qubit count (the qubit must also be clean-able: the kept
    product is erased by MBU at its last use, 0 Toffolis).
    """
    if not repeats:
        return dict(candidates=0, free=0)
    n = len(width)
    nb = (n + block - 1) // block
    pad = np.zeros(nb * block, dtype=np.int64); pad[:n] = width
    occ = pad.reshape(nb, block).max(1)
    spare = cap - occ
    iv = sorted(((f // block, k // block) for f, k in repeats), key=lambda x: (x[1], x[1] - x[0]))  # earliest end first
    if max_len is not None:
        iv = [x for x in iv if (x[1] - x[0]) * block <= max_len]
    used = np.zeros(nb, dtype=np.int64)
    free = 0
    for s, e in iv:
        if (used[s:e + 1] < spare[s:e + 1]).all():
            used[s:e + 1] += 1
            free += 1
    return dict(candidates=len(repeats), free=free)


def linear_products(circ: kmx.Circuit, inputs: dict, S: int, seed: int = 1, kinds=(kmx.CCX,),
                    max_report: int = 10_000) -> list[tuple[int, list[int], bool]]:
    """Toffolis whose product a*b (on every lane) is an XOR of current wire values (+ constant 1).

    Such a Toffoli can be replaced by CX gates from those wires (0 Toffolis), exactly on the simulated input set.
    Returns (op index, wires of the XOR combination, uses_constant). Cost O(Toffolis * nq^2) big-int ops: use the
    exhaustive input set for invsqrt (3.1 M lanes, slow) only on candidates found with sampled lanes first.
    Conditional Toffolis are tested with their active-lane mask (product & act).
    """
    MASK = (1 << S) - 1
    rng = random.Random(seed)
    nq = circ.num_qubits
    nb = max(circ.num_bits, 1)
    q = [0] * nq
    for w, v in inputs["qubits"].items():
        q[w] = v
    bits = [0] * nb
    for b, v in inputs.get("bits", {}).items():
        bits[b] = v
    stack = []; cur = MASK
    found = []
    OP = circ.op.tolist(); A = circ.a.tolist(); B = circ.b.tolist(); Cc = circ.c.tolist()
    BIT = circ.bit.tolist(); CON = circ.cond.tolist()
    for k, o in enumerate(OP):
        if o == kmx.PUSH:
            stack.append(cur); cur &= bits[BIT[k]]; continue
        if o == kmx.POP:
            cur = stack.pop(); continue
        act = cur if CON[k] < 0 else cur & bits[CON[k]]
        if o >= kmx.BINV:
            if o == kmx.BINV: bits[BIT[k]] ^= act
            elif o == kmx.BST0: bits[BIT[k]] &= ~act
            elif o == kmx.BST1: bits[BIT[k]] |= act
            continue
        a = A[k]
        if o == kmx.CX:
            q[B[k]] ^= q[a] & act
        elif o == kmx.CCX:
            b = B[k]; c = Cc[k]
            p = q[a] & q[b] & act
            if o in kinds and p:
                # basis of current wire values except the target, plus the constant (augmented with a tag)
                basis = {}
                vecs = [(q[w], 1 << w) for w in range(nq) if w != c and q[w]] + [(MASK, 1 << nq)]
                for v, tag in vecs:
                    x, tg = v, tag
                    while x:
                        hb = x.bit_length() - 1
                        e = basis.get(hb)
                        if e is None:
                            basis[hb] = (x, tg); break
                        x ^= e[0]; tg ^= e[1]
                x, tg = p, 0
                while x:
                    hb = x.bit_length() - 1
                    e = basis.get(hb)
                    if e is None:
                        break
                    x ^= e[0]; tg ^= e[1]
                if x == 0 and len(found) < max_report:
                    ws = [w for w in range(nq) if tg >> w & 1]
                    found.append((k, ws, bool(tg >> nq & 1)))
            q[c] ^= p
        elif o == kmx.CSWAP:
            b = B[k]; c = Cc[k]
            d = (q[b] ^ q[c]) & q[a] & act
            q[b] ^= d; q[c] ^= d
        elif o == kmx.X:
            q[a] ^= act
        elif o == kmx.SWAP:
            b = B[k]; d = (q[a] ^ q[b]) & act; q[a] ^= d; q[b] ^= d
        elif o == kmx.HMR:
            bits[BIT[k]] = (bits[BIT[k]] & ~act) | (rng.getrandbits(S) & act)
            q[a] &= ~act
        elif o == kmx.R:
            q[a] &= ~act
    return found


def drop_ops(circ: kmx.Circuit, ops) -> kmx.Circuit:
    """A copy of circ without the given op indices (for checking a proposed deletion)."""
    keep = np.ones(circ.n_ops, dtype=bool)
    keep[list(ops)] = False
    return kmx.Circuit(op=circ.op[keep], a=circ.a[keep], b=circ.b[keep], c=circ.c[keep], bit=circ.bit[keep],
                       cond=circ.cond[keep], depth=circ.depth[keep], regs=circ.regs, bit_regs=circ.bit_regs,
                       reg_names=circ.reg_names, angles=circ.angles, path=circ.path + " (edited)")


def same_values(c1: kmx.Circuit, c2: kmx.Circuit, inputs: dict, S: int) -> dict:
    """Run both circuits on the same lanes (same HMR seed) and compare every final qubit value."""
    v1 = run(c1, inputs, S=S, track_gaps=False)
    v2 = run(c2, inputs, S=S, track_gaps=False)
    diff = [w for w in range(min(len(v1.final), len(v2.final))) if v1.final[w] != v2.final[w]]
    return dict(equal=not diff, differing_qubits=diff[:10], toffoli_before=v1.toffoli_exec_mean,
                toffoli_after=v2.toffoli_exec_mean, end_after=v2.end_ok)


def span_basis(vectors: list[tuple[int, int]]):
    """GF(2) elimination of (value, tag) pairs; returns (basis dict pivot -> (value, tag), dependent tags)."""
    basis = {}
    deps = []
    for v, tag in vectors:
        x, tg = v, tag
        while x:
            hb = x.bit_length() - 1
            e = basis.get(hb)
            if e is None:
                basis[hb] = (x, tg); break
            x ^= e[0]; tg ^= e[1]
        if x == 0:
            deps.append(tg)
    return basis, deps


def in_span(basis: dict, v: int):
    x, tg = v, 0
    while x:
        hb = x.bit_length() - 1
        e = basis.get(hb)
        if e is None:
            return None
        x ^= e[0]; tg ^= e[1]
    return tg


def affine_rebuild(snap_start: list, snap_end: list, live_start, live_end, wire: int, S: int):
    """Is `wire` (idle over the window) an XOR of other live wires (+1) both at the window start and end?

    If yes it can be erased by CX at the start (0 Toffolis) and rebuilt by CX at the end: one qubit freed over the
    window, exactly on the simulated input set. Returns (start_combo, end_combo) as wire lists, or None.
    """
    MASK = (1 << S) - 1
    out = []
    for snap, live in ((snap_start, live_start), (snap_end, live_end)):
        vecs = [(snap[w], 1 << w) for w in live if w != wire and snap[w]] + [(MASK, 1 << len(snap))]
        basis, _ = span_basis(vecs)
        tg = in_span(basis, snap[wire])
        if tg is None:
            return None
        out.append([w for w in range(len(snap) + 1) if tg >> w & 1])
    return tuple(out)


def episode_rebuild(circ: kmx.Circuit, lv, inputs: dict, S: int, episodes=None, seed: int = 1) -> list[dict]:
    """Width test (catalog E2/E3): for each peak episode, the live wires that stay idle across it and are an XOR of the
    other live wires (+1) at both its start and its end. Such a wire can be erased by CX before the episode and rebuilt
    by CX after it (0 Toffolis), so the episode no longer needs it. If every episode has one, the circuit fits in
    peak-1 qubits (after relabeling). Needs S > number of live wires for a meaningful rank test."""
    eps = lv.episodes() if episodes is None else episodes
    iv = np.array(lv.intervals) if lv.intervals else np.zeros((0, 3), dtype=np.int64)
    reg = set(circ.input_qubits().tolist())

    def live_at(t):
        if len(iv):
            m = (iv[:, 1] <= t) & (iv[:, 2] > t)
            return sorted(set(iv[m, 0].tolist()) | reg)
        return sorted(reg)
    snaps = set()
    for s, e in eps:
        snaps.add(s); snaps.add(e + 1)
    V = run(circ, inputs, S=S, track_gaps=False, snapshots=snaps, seed=seed)
    MASK = (1 << S) - 1
    out = []
    for s, e in eps:
        ls, le = live_at(s), live_at(e + 1)
        touched = set()
        for col in (circ.a, circ.b, circ.c):
            seg = col[s:e + 1]
            touched |= set(seg[seg >= 0].tolist())
        idle = [w for w in ls if w not in touched and w in le]
        dep = []
        for t in (s, e + 1):
            snap = V.snaps.get(t)
            if snap is None:            # e + 1 == n_ops: use the final state
                snap = V.final
            live = ls if t == s else le
            _, deps = span_basis([(snap[w], 1 << w) for w in live] + [(MASK, 1 << circ.num_qubits)])
            d = set()
            for tg in deps:
                d.update(w for w in live if tg >> w & 1)
            dep.append(d)
        ok = [w for w in idle if w in dep[0] and w in dep[1]]
        out.append(dict(s=s, e=e, length=e - s + 1, live=len(ls), idle=len(idle), rebuildable=ok))
    return out
