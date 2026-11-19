#!/usr/bin/env python3
"""splice_dp: find the cheapest splice of several invsqrt circuits.

A cut at position p of circuit A is "clean" when the condition stack is empty and no classical bit written before p
is read at or after p. At a clean cut the remaining ops depend only on the qubit values, and the phase so far is a
deterministic function of x. If two circuits reach clean cuts with identical qubit values and identical phase on every
sampled input, the prefix of one can be joined to the suffix of the other. Shortest path over these sync points, with cost = mean Toffolis + ROT_TOFF_EQ x rotations.

Pass only circuits that already pass the task (for example the kmx/invsqrt files of this dataset whose
verified_status is PASS, or those that pass `kmsim.py`); a splice is checked only on the sampled inputs, so verify
the result (build_splice.py, then kmsim.py with --xmax 3133452 or the official verifier).

    python splice_dp.py A.kmx B.kmx C.kmx ... --out splice.json [--samples 4096]

The 12-character prefix of each file name is the circuit's name in the output segments.

Licence: Apache-2.0.
"""
import argparse, sys, os, hashlib, heapq, json
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import kmsim

ROT_TOFF_EQ = 28.8 / 4  # Toffoli-equivalent of one non-Clifford rotation at the frontier eps


def bits_read_after(ops):
    """last_read[b] = last op index reading bit b (as condition or operand of BIT_* / NEG if)."""
    last = {}
    for k, (n, qs, bs, c, a) in enumerate(ops):
        if c is not None: last[c] = k
        if n in ("BIT_INVERT",): last[bs[0]] = k  # read-modify-write
    return last


def analyse(path, xs, seed=7, nq=62):
    """Run one circuit on xs and list its clean cuts as (op position, state hash, cumulative Toffolis, rotations)."""
    ops, regs = kmsim.parse(path)
    nb = 1 + max(max((max(o[2]) for o in ops if o[2]), default=0), max((o[3] for o in ops if o[3] is not None), default=0))
    last_read = bits_read_after(ops)
    # open-bit counter: bits written (HMR/BIT_STORE) whose last read is in the future
    written_until = {}
    s = kmsim.Sim(ops, nq, nb, len(xs), seed)
    for i, qi in enumerate(regs["r0"]):
        s.q[qi] = (xs >> i) & 1 == 1
    nonclif = [o[0] == "Z_POW" and (o[4] % (1 << 61)) != 0 for o in ops]
    cuts = []  # (pos, hash, cum_toff_mean, cum_rot)
    open_until = -1
    depth = 0
    rot = 0.0

    def h():
        return hashlib.blake2b(np.packbits(s.q).tobytes() + s.ph.tobytes(), digest_size=16).hexdigest()

    cuts.append((0, h(), 0.0, 0.0))
    for k, op in enumerate(ops):
        n, qs, bs, c, a = op
        if n == "PUSH_CONDITION": depth += 1
        elif n == "POP_CONDITION": depth -= 1
        s.run(k, k + 1)
        for b in bs:
            open_until = max(open_until, last_read.get(b, -1))
        if c is not None:
            pass
        if nonclif[k]: rot += 1  # unconditional rotations in these circuits
        if depth == 0 and open_until <= k:
            cuts.append((k + 1, h(), float(s.toff.mean()), rot))
    return ops, cuts


def main(paths, xs):
    """Shortest splice over the clean cuts of the given circuits. Returns (segments, cost)."""
    data = {}
    # one common qubit count so that equal states hash equally across circuits (62 for the usual layout)
    nq = max(62, max(kmsim.sizes(kmsim.parse(p)[0])[0] for p in paths))
    for p in paths:
        name = os.path.basename(p)[:12]
        ops, cuts = analyse(p, xs, nq=nq)
        data[name] = cuts
        print(name, "clean cuts", len(cuts), "toff", round(cuts[-1][2], 2), "rot", cuts[-1][3], flush=True)
    # graph: node = (name, idx); edges along circuit; zero-cost jumps between equal hashes
    by_hash = {}
    for name, cuts in data.items():
        for i, (pos, hh, t, r) in enumerate(cuts):
            by_hash.setdefault(hh, []).append((name, i))
    start_hash = next(iter(data.values()))[0][1]
    dist = {}; prev = {}
    pq = []
    for name, i in by_hash[start_hash]:
        dist[(name, i)] = 0.0; heapq.heappush(pq, (0.0, name, i))
    best_end = None
    while pq:
        d, name, i = heapq.heappop(pq)
        if d > dist.get((name, i), 1e18): continue
        cuts = data[name]
        if i == len(cuts) - 1:
            if best_end is None or d < best_end[0]: best_end = (d, name, i)
            continue
        # move along the circuit
        nxt = (name, i + 1)
        w = (cuts[i + 1][2] - cuts[i][2]) + ROT_TOFF_EQ * (cuts[i + 1][3] - cuts[i][3])
        if d + w < dist.get(nxt, 1e18):
            dist[nxt] = d + w; prev[nxt] = (name, i); heapq.heappush(pq, (d + w, *nxt))
        # jump to other circuits at the same state
        for other in by_hash[cuts[i][1]]:
            if other != (name, i) and d < dist.get(other, 1e18):
                dist[other] = d; prev[other] = (name, i); heapq.heappush(pq, (d, *other))
    # reconstruct
    path = []
    node = best_end[1:]
    while node in prev:
        path.append(node); node = prev[node]
    path.append(node); path.reverse()
    segs = []
    for (a, i), (b, j) in zip(path, path[1:]):
        if a == b:
            if segs and segs[-1][0] == a: segs[-1][2] = data[a][j][0]
            else: segs.append([a, data[a][i][0], data[a][j][0]])
    print("best cost (toff + rot eq)", round(best_end[0], 3))
    for name, cuts in data.items():
        print("  single", name, round(cuts[-1][2] + ROT_TOFF_EQ * cuts[-1][3], 3))
    print("segments", segs)
    return segs, best_end[0]


def cli(argv=None):
    ap = argparse.ArgumentParser(description="Cheapest splice of invsqrt kmx circuits at clean cuts.")
    ap.add_argument("kmx", nargs="+", help="invsqrt circuits (.kmx or .kmx.gz) that already pass the task")
    ap.add_argument("--out", default="splice.json", help="output JSON with segments and cost (default splice.json)")
    ap.add_argument("--samples", type=int, default=3072, help="random inputs added to x = 1..1024 and the edge cases")
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args(argv)
    rng = np.random.default_rng(a.seed)
    xs = np.concatenate([np.arange(1, 1025), rng.integers(1, kmsim.INVSQRT_XMAX + 1, a.samples),
                         np.array([161, kmsim.INVSQRT_XMAX])]).astype(np.int64)
    segs, cost = main(a.kmx, xs)
    with open(a.out, "w") as f:
        json.dump({"segments": segs, "cost": cost}, f)
    print("wrote", a.out)


if __name__ == "__main__":
    cli()
