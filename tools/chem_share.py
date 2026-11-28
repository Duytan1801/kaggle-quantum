#!/usr/bin/env python3
"""chem_share.py -- share duplicated cached AND features in a chemistry loader.

THE MECHANISM (2026-11-26)
--------------------------
The chemistry leg's cost is

    cost = lambda_eff * T_total * Q_total ,   T = Toffoli-like gates executed

and every CCX in an ANGLE_k loader is one Toffoli of T.  The five expensive
group-start loaders (k = 0,1,5,7,11) cost 240-245 Toffolis each against
205-214 for the ten cheap ones, and the campaign's H48 lane is exactly "re-solve
the five".

Their circuits are public even though their plans are not, and the circuits
contain a LOT of duplicated work: the loader caches an AND feature by computing

        ancilla ^= sel_a AND sel_b            (a CCX: one Toffoli)

where `sel_a`, `sel_b` are ADDRESS bits, so the product is a CONSTANT function
of the address.  The same product is cached many times over -- into different
ancillas, and sometimes into the same ancilla again:

        k=0:  CCX(sel0, sel1, anc11) appears TEN times
        k=2:  CCX(sel0, sel1, anc12) appears NINE times, anc14 SIX times
        k=11: 240 CCX but only 172 distinct (controls,target) pairs

**Every one of those duplicates is a Toffoli that can be replaced by a CNOT
from a wire that already holds the product** -- a CNOT is free in the cost
model.  The replacement is exact, and this tool proves it with an EXACT
symbolic simulation (every qubit tracked as a boolean function of the address,
every qubit's phase tracked too, all 1,219 valid addresses at once).

Algorithm (one pass, greedy, exact):

    for each gate:
        CCX(c1, c2, t):
            p = value(c1) & value(c2)
            if some OTHER wire f currently holds exactly p:
                replace the gate by CX(f, t)          # free
            else:
                keep the CCX and update value(t)
        ... every other gate updates the value masks as usual

The rewritten loader is then re-simulated and compared with the original, bit
for bit and phase for phase, over all valid addresses.  Only a loader that
passes that comparison is reported.

Usage:
    chem_share.py <tree-dir> [batch ...]
    chem_share.py <tree-dir> --all
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path("/home/bandoc/Downloads/opencode")
sys.path.insert(0, str(ROOT / "work/toolchain/kickmix"))
sys.path.insert(0, str(ROOT / "work/tools"))
import chem_extract as CE  # noqa: E402

NV = CE.NV
ALL = CE.ALL
VALID = 0
for a in range(NV):
    VALID |= 1 << int(CE.ADDR[a])


def cellmask(a: int) -> int:
    return 1 << int(a)


def simulate(ops, sel_vals, word_vals, nq):
    bits = [0] * nq
    phase = [0] * nq
    for q, v in sel_vals.items():
        bits[q] = v
    for q, v in word_vals.items():
        bits[q] = v
    for t, a, _ in ops:
        if t == "CX":
            bits[a[1]] ^= bits[a[0]]
        elif t == "X":
            bits[a[0]] ^= VALID
        elif t == "CCX":
            bits[a[2]] ^= bits[a[0]] & bits[a[1]]
        elif t == "CZ":
            phase[a[1]] ^= bits[a[0]] & bits[a[1]]
        elif t == "Z":
            phase[a[0]] ^= bits[a[0]]
        elif t == "HMR":
            bits[a[0]] = 0
            phase[a[0]] = 0
        else:
            raise SystemExit(f"unknown op {t}")
    return bits, phase


def initial_state(states_k, sel):
    sel_vals = {}
    addr = CE.ADDR
    for i, q in enumerate(sel):
        m = 0
        for a in range(NV):
            if (int(addr[a]) >> i) & 1:
                m |= cellmask(a)
        sel_vals[q] = m
    word_vals = {}
    for j, q in enumerate(states_k["wq"]):
        f = np.asarray(states_k["vals"][j], bool)
        m = 0
        for a in range(NV):
            if f[a]:
                m |= cellmask(a)
        word_vals[q] = m
    return sel_vals, word_vals


def share(ops, sel_vals, word_vals, nq, prefer=None):
    """Greedy exact rewrite: replace a CCX by a CNOT when the product is
    already held by another wire.  Returns (new_ops, n_saved, rewrites)."""
    bits = [0] * nq
    phase = [0] * nq
    for q, v in sel_vals.items():
        bits[q] = v
    for q, v in word_vals.items():
        bits[q] = v
    # index of wires currently holding each value -> list of wires
    holders: dict[int, list[int]] = {}

    def note(q):
        v = bits[q]
        holders.setdefault(v, []).append(q)

    def unnote(q):
        v = bits[q]
        lst = holders.get(v)
        if lst and q in lst:
            lst.remove(q)
            if not lst:
                holders.pop(v, None)

    for q in range(nq):
        if bits[q]:
            note(q)
    new_ops = []
    saved = 0
    rewrites = []
    for i, (t, a, extra) in enumerate(ops):
        if t == "CCX":
            c1, c2, tg = a[0], a[1], a[2]
            p = bits[c1] & bits[c2]
            cands = holders.get(p, [])
            src = None
            for f in cands:
                if f not in (c1, c2, tg) and bits[f] == p:
                    src = f
                    break
            if src is not None and p != 0:
                new_ops.append(("CX", [src, tg], extra))
                unnote(tg)
                bits[tg] ^= p
                note(tg)
                saved += 1
                rewrites.append({"op_index": i, "from": ["CCX", c1, c2, tg],
                                 "to": ["CX", src, tg]})
                continue
        new_ops.append((t, a, extra))
        if t == "CX":
            unnote(a[1]); bits[a[1]] ^= bits[a[0]]; note(a[1])
        elif t == "X":
            unnote(a[0]); bits[a[0]] ^= VALID; note(a[0])
        elif t == "CCX":
            unnote(a[2]); bits[a[2]] ^= bits[a[0]] & bits[a[1]]; note(a[2])
        elif t == "CZ":
            phase[a[1]] ^= bits[a[0]] & bits[a[1]]
        elif t == "Z":
            phase[a[0]] ^= bits[a[0]]
        elif t == "HMR":
            unnote(a[0]); bits[a[0]] = 0; phase[a[0]] = 0
    return new_ops, saved, rewrites


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tree = pathlib.Path(args[0])
    batches = [int(x) for x in args[1:]] or [11]
    if "--all" in sys.argv:
        batches = list(range(15))
    states = CE.chain_states(tree / "submission.npz")
    summary = []
    total_saved = 0
    for k in batches:
        t0 = time.time()
        ops, sel, wq = CE.parse_kmx(tree / f"angle_k_{k}.kmb")
        nq = 1 + max(max(a) for _, a, _ in ops)
        # INPUT STATE: the verifier chains the loaders (loader k sees batch
        # k-1 in the word registers; loader 0 sees zero).  chain_states()[k]
        # is word_bits(W, k-1), i.e. exactly that input state.
        sel_vals, word_vals = initial_state(
            {"wq": wq, "vals": states[k]}, sel)
        ref_bits, ref_phase = simulate(ops, sel_vals, word_vals, nq)
        new_ops, saved, rewrites = share(ops, sel_vals, word_vals, nq)
        b, p = simulate(new_ops, sel_vals, word_vals, nq)
        ok = all(b[q] == ref_bits[q] and p[q] == ref_phase[q] for q in range(nq))
        nccx0 = sum(1 for t, _, _ in ops if t == "CCX")
        nccx1 = sum(1 for t, _, _ in new_ops if t == "CCX")
        status = "EXACT-OK" if ok else "MISMATCH"
        print(f"k={k:2d}: CCX {nccx0} -> {nccx1}  (saved {saved})  "
              f"[{status}]  [{time.time()-t0:.1f}s]", flush=True)
        if not ok:
            for q in range(nq):
                if b[q] != ref_bits[q] or p[q] != ref_phase[q]:
                    print(f"    first differing wire {q}")
                    break
        total_saved += (nccx0 - nccx1) if ok else 0
        summary.append({"k": k, "ccx_before": nccx0, "ccx_after": nccx1,
                        "exact_ok": ok, "rewrites": rewrites})
    out = ROOT / "work/recon/chem_share.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1))
    print(f"\ntotal Toffolis saved (exact): {total_saved}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
