#!/usr/bin/env python3
"""chem_feature_dup.py -- are the chemistry loader's cached features DISTINCT?

THE STRUCTURE (measured 2026-11-26)
-----------------------------------
A chemistry loader ANGLE_k is built as:

    (a) FEATURE phase   : nF CCX gates compute nF *address functions* into
                           ancilla slots (one CCX each);
    (b) PRODUCT phase   : nP CCX gates XOR a product of two live features into
                           the word registers (one CCX each);
    (c) LINEAR phase    : CX fan-out of features into word registers (FREE);
    (d) UNCLEAN phase   : HMR resets each ancilla slot (and a CZ for phase).

The cost model charges ONLY the Toffoli-like gates, so

    cost(loader) = nF + nP        (in Toffoli units)

Measured on the shipped v151 tree:

    k = 2  (wired)       82 feature CCX + 131 product CCX = 213
    k = 11 (group-start) 144 feature CCX +  96 product CCX = 240
                         ^^^^^^^^^^^^^^^^^^^^^
                         144 computations into only 82 ancilla slots:
                         the group-start loaders RECYCLE ancillas.

THE QUESTION THIS TOOL ANSWERS
------------------------------
How many of those nF feature computations compute a function that has ALREADY
been computed?  A duplicate feature costs a full Toffoli (CCX) but could
instead be a free CNOT copy from a wire that still holds the same function:

    CCX(c1, c2, A)   computes   g = c1 AND c2   into ancilla A
    CX(B, A)         copies     g               into ancilla A   (FREE)

so every duplicate feature that can be served by a copy instead of a
recomputation is worth exactly 1 Toffoli = +0.00169 GM on the leaderboard.

This tool extracts, per loader:
  * the ordered list of feature computations (time, ancilla, function mask),
  * the number of DISTINCT functions,
  * the number of computations that duplicate an earlier function,
  * the ancilla slot occupancy schedule (which slot holds which function when),
so that a plan-level rewrite can be built.

Usage:
    chem_feature_dup.py <tree-dir> [batch ...]
    chem_feature_dup.py <tree-dir> --all
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter, defaultdict

ROOT = pathlib.Path("/home/bandoc/Downloads/opencode")
sys.path.insert(0, str(ROOT / "work/toolchain/kickmix"))
sys.path.insert(0, str(ROOT / "work/tools"))
import chem_extract as CE  # noqa: E402

NV = CE.NV
ALL = CE.ALL


def fun_from_mask(m: int) -> int:
    return m


def extract_schedule(tree: pathlib.Path, k: int):
    """Return (features, products, order) for loader k.

    features : list of dicts {t: op index, q: ancilla, f: function mask}
    products : list of dicts {t: op index, tgt: word qubit, u: mask, v: mask}
    """
    ops, sel, wq = CE.parse_kmx(tree / f"angle_k_{k}.kmb")
    states = CE.chain_states(tree / "submission.npz")
    f = {}
    for i, q in enumerate(sel):
        f[q] = CE.fun((CE.ADDR >> i) & 1)
    for j, q in enumerate(wq):
        f[q] = CE.fun(states[k][j])

    features = []
    products = []
    for idx, (t, a, c) in enumerate(ops):
        if t == "CX":
            f[a[1]] = f.get(a[1], 0) ^ f.get(a[0], 0)
        elif t == "X":
            f[a[0]] = f.get(a[0], 0) ^ ALL
        elif t == "CCX":
            u, v = f.get(a[0], 0), f.get(a[1], 0)
            f[a[2]] = f.get(a[2], 0) ^ (u & v)
            if a[2] >= 46:
                features.append({"t": idx, "q": a[2], "f": u & v,
                                 "c1": a[0], "c2": a[1]})
            else:
                products.append({"t": idx, "tgt": a[2], "u": u, "v": v,
                                 "c1": a[0], "c2": a[1]})
        elif t == "HMR":
            f[a[0]] = 0
    return features, products, ops


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tree = pathlib.Path(args[0])
    batches = [int(x) for x in args[1:]] or [11]
    if "--all" in sys.argv:
        batches = list(range(15))
    out = []
    for k in batches:
        feats, prods, ops = extract_schedule(tree, k)
        masks = [f["f"] for f in feats]
        cnt = Counter(masks)
        distinct = len(cnt)
        dups = sum(v - 1 for v in cnt.values())
        # which functions are duplicated, and how often
        dupf = {m: v for m, v in cnt.items() if v > 1}
        # how many DISTINCT functions are needed by the products?
        needed = set()
        for p in prods:
            needed.add(p["u"])
            needed.add(p["v"])
        # occupancy: how many ancilla slots, and the reuse depth
        slots = Counter(f["q"] for f in feats)
        # per-slot sequence of functions (to see if a slot is reused for the
        # SAME function twice -> that is a pure recomputation)
        slot_seq = defaultdict(list)
        for f in feats:
            slot_seq[f["q"]].append(f["f"])
        same_slot_same_fn = 0
        for q, seq in slot_seq.items():
            c = Counter(seq)
            same_slot_same_fn += sum(v - 1 for v in c.values() if v > 1)
        rec = {
            "k": k,
            "n_features": len(feats),
            "n_products": len(prods),
            "n_slots_used": len(slots),
            "distinct_feature_functions": distinct,
            "duplicate_computations": dups,
            "distinct_functions_needed_by_products": len(needed),
            "needed_but_never_computed": len(needed - set(masks)),
            "same_slot_same_function_recomputes": same_slot_same_fn,
            "max_slot_use": max(slots.values()) if slots else 0,
        }
        print(f"k={k:2d}: features {len(feats):3d} (distinct fn {distinct:3d}, "
              f"dupes {dups:3d}) products {len(prods):3d} slots {len(slots):3d} "
              f"(max use {rec['max_slot_use']}) | product-needed fns {len(needed):3d}, "
              f"never-computed {rec['needed_but_never_computed']}", flush=True)
        out.append(rec)
    p = ROOT / "work/recon/chem_feature_dup.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
