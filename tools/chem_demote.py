#!/usr/bin/env python3
"""chem_demote.py -- exact "can this gate be removed or demoted?" analysis of a
chemistry loader.

WHY THIS TOOL EXISTS (the 2026-11-26 pipeline fix)
----------------------------------------------------
The chemistry leg's cost is

    cost = lambda_eff * T * Q ,      T = total Toffoli-like gates executed

and the 15 ANGLE_k loaders contribute their CCX count to T (the loaders run
twice).  Five of the fifteen loaders (k = 0,1,5,7,11) cost 240-245 Toffolis
each while the other ten cost 205-214; re-solving the five is the campaign's
top lane (H48, +0.24 GM).

The five expensive loaders have no public PLAN, but their CIRCUITS are public.
This tool therefore works directly on the circuit, with an EXACT semantic
model (no shots, no verifier):

  * every qubit is tracked as a boolean function of the address (a 1,232-bit
    mask: 77 bank x 16 low cells, 1,219 of them valid), and every qubit's
    accumulated PHASE is tracked the same way;
  * the loader's effect is compared, cell by cell, against the reference run.

With that model it answers, for every gate in the loader, the question a
search actually needs:

    drop_ok      -- can this gate be DELETED with the semantics unchanged?
    demote_ok    -- can this CCX(c1,c2,t) become the FREE CX(c1,t) or
                    CX(c2,t)?  (a control that is constant 1 over all valid
                    cells makes the other control the only one that matters)

A Toffoli that can be demoted to a CNOT is worth 1 T; five loaders x 28 T is
+0.24 GM, so this is the exact measurement the lane needs.

Usage:
    chem_demote.py <tree-dir> <batch> [...]      # e.g. chem_demote.py work/trees/v151/dfthcsos 11 7 5 1 0
"""
from __future__ import annotations

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
NBANK, NLOW = 77, 16
NCELL = NBANK * NLOW
VALID = 0
for a in range(NV):
    VALID |= 1 << int(CE.ADDR[a])


def cellmask(a: int) -> int:
    """the 1-cell mask of address a"""
    return 1 << int(a)


# ---------------------------------------------------------------- simulation --
def simulate(ops, sel_vals, word_vals, nq):
    """Return (bits, phase) per qubit after running `ops`.

    bits[q]   : int mask over cells, the qubit's value
    phase[q]  : int mask over cells, where the qubit carries a -1 phase
    """
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


def initial_state(k, states):
    """selection-qubit values and word-register values for batch k."""
    sel_vals, word_vals = {}, {}
    addr = CE.ADDR
    for i in range(11):
        m = 0
        for a in range(NV):
            if (int(addr[a]) >> i) & 1:
                m |= cellmask(a)
        sel_vals[i] = m
    return sel_vals, word_vals


def word_state_masks(states_k):
    """states_k[j] is a boolean function of the address (numpy array)."""
    out = []
    for j in range(len(states_k)):
        f = np.asarray(states_k[j], bool)
        m = 0
        for a in range(NV):
            if f[a]:
                m |= cellmask(a)
        out.append(m)
    return out


def main() -> int:
    tree = pathlib.Path(sys.argv[1])
    batches = [int(x) for x in sys.argv[2:]] or [11]
    states = CE.chain_states(tree / "submission.npz")
    summary = []
    for k in batches:
        t0 = time.time()
        ops, sel, wq = CE.parse_kmx(tree / f"angle_k_{k}.kmb")
        nq = 1 + max(max(a) for _, a, _ in ops)
        sel_vals, _ = initial_state(k, states)
        # INPUT STATE: the official verifier chains the loaders -- loader k is
        # applied with the word registers holding batch k-1 (and loader 0 with
        # them at zero), and the reverse traversal must restore batch k-1.
        # chain_states()[j] is word_bits(W, j-1), so the input is states[k].
        wm = word_state_masks(states[k])
        word_vals = {wq[j]: wm[j] for j in range(len(wq))}
        ref_bits, ref_phase = simulate(ops, sel_vals, word_vals, nq)
        nccx = sum(1 for t, _, _ in ops if t == "CCX")
        ncz = sum(1 for t, _, _ in ops if t == "CZ")
        nz = sum(1 for t, _, _ in ops if t == "Z")
        print(f"\n=== k={k}: {len(ops)} ops, {nccx} CCX, {ncz} CZ, {nz} Z, "
              f"Q={nq}  [{time.time()-t0:.1f}s]", flush=True)

        droppable, demotable = [], []
        for i, (t, a, _) in enumerate(ops):
            if t not in ("CCX", "CZ", "Z"):
                continue
            mod = list(ops)
            del mod[i]
            b, p = simulate(mod, sel_vals, word_vals, nq)
            same = all(b[q] == ref_bits[q] and p[q] == ref_phase[q]
                       for q in range(nq))
            if same:
                droppable.append(i)
                continue
            if t == "CCX":
                for keep in (0, 1):
                    other = 1 - keep
                    mod = list(ops)
                    mod[i] = ("CX", [a[other], a[2]], None)
                    b, p = simulate(mod, sel_vals, word_vals, nq)
                    if all(b[q] == ref_bits[q] and p[q] == ref_phase[q]
                           for q in range(nq)):
                        demotable.append((i, a[keep], a[other], a[2]))
                        break
        print(f"    droppable gates : {len(droppable)}")
        print(f"    demotable CCX   : {len(demotable)}")
        for i, c1, c2, tg in demotable[:20]:
            print(f"      op {i}: CCX({c1},{c2},{tg}) -> CX({c2},{tg})")
        summary.append({"k": k, "ccx": nccx, "cz": ncz, "z": nz,
                        "droppable": droppable, "demotable": demotable})
    out = ROOT / f"work/recon/chem_demote_{batches[0]}.json"
    import json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=1))
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
