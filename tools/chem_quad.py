#!/usr/bin/env python3
"""chem_quad.py -- the PLAN MODEL of a chemistry loader, in the quadratic form.

WHAT THIS TOOL ESTABLISHES (2026-11-26)
========================================
The chemistry loader ANGLE_k computes, for every output word bit o, a delta

    D_o(addr) = sum over TERMS of  q_term(addr) * [o in mask_term]

where a TERM is a *quadratic form in the selection bits*:

    q(addr) = (XOR_{i in U} sel_i) * (XOR_{j in V} sel_j)     U, V subsets of [11]

because a loader can only build such a form with ONE Toffoli: the two
controls are prepared by free CNOTs (the "pre" ops), the CCX evaluates the
product, and the CNOTs are undone.

Each TERM costs exactly ONE Toffoli, so

    cost(loader) = #terms = #features + #products

MEASURED STRUCTURE OF THE SHIPPED v151 TREE
    k = 2  (wired)       82 features + 131 products = 213 Toffolis
    k = 11 (group-start) 144 features +  96 products = 240 Toffolis
    (the group-start loaders RECYCLE ancilla slots: 144 computations into
     82 slots, max slot use 4-15)

The group-start loaders therefore pay MORE terms than the wired ones.  This
tool answers the two questions that decide whether a cheaper re-plan exists:

  Q1  Are all the terms degree-<=2 polynomials in the selection bits?
      (if yes, the whole loader lives in a 67-dimensional space -- 1 linear
       + 11 linear + 55 quadratic -- and a re-plan is a discrete optimisation
       in that space)
  Q2  How does each output's delta look in that space, and how many TERMS
      would a minimum-term decomposition need?

It also reports the MERGE opportunity that the term structure creates:

      if q_a XOR q_b is itself a quadratic form, then the two terms q_a and
      q_b can be replaced by ONE term (q_a XOR q_b) whenever they feed the
      SAME set of outputs -- saving one Toffoli each.

Usage:
    chem_quad.py <tree-dir> [batch ...]
    chem_quad.py <tree-dir> --all
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
NSEL = 11


# ------------------------------------------------------------------- basis --
def build_basis():
    """{1, sel_i, sel_i AND sel_j} as 1219-bit masks."""
    addr = CE.ADDR
    sel = []
    for i in range(NSEL):
        m = 0
        for a in range(NV):
            if (int(addr[a]) >> i) & 1:
                m |= 1 << a
        sel.append(m)
    mono = [ALL]
    mono += sel
    for i in range(NSEL):
        for j in range(i, NSEL):
            mono.append(sel[i] & sel[j])
    return mono, sel


class Span:
    """GF(2) span membership / reduction over a list of basis masks."""

    def __init__(self, basis):
        self.basis = basis
        self.rows = []          # reduced echelon rows (mask, pivot bit)

    def reduce(self, v):
        for m, p in self.rows:
            if (v >> p) & 1:
                v ^= m
        return v

    def add(self, v):
        v = self.reduce(v)
        if v == 0:
            return False
        p = v.bit_length() - 1
        # keep the echelon form simple: insert and re-reduce the others
        self.rows.append((v, p))
        self.rows.sort(key=lambda r: -r[1])
        out = []
        for m, pp in self.rows:
            mm = self.reduce(m)
            if mm:
                out.append((mm, pp))
        self.rows = out
        return True

    def in_span(self, v):
        return self.reduce(v) == 0

    def coords(self, v):
        """coefficient vector of v in the ORIGINAL basis (or None)."""
        if not self.in_span(v):
            return None
        # solve by elimination over the basis
        rows = []
        for idx, b in enumerate(self.basis):
            m = b
            coeff = 1 << idx
            for rm, rc, rp in rows:
                if (m >> rp) & 1:
                    m ^= rm
                    coeff ^= rc
            rows.append((m, coeff, b.bit_length() - 1))
        # gaussian elimination
        rows.sort(key=lambda r: -r[2])
        piv = {}
        for m, coeff, p in rows:
            for pm, pc, pp in piv.values():
                if (m >> pp) & 1:
                    m ^= pm
                    coeff ^= pc
            if m:
                piv[p] = (m, coeff)
        v2 = v
        out = 0
        for p in sorted(piv, reverse=True):
            pm, pc = piv[p]
            if (v2 >> p) & 1:
                v2 ^= pm
                out ^= pc
        return out if v2 == 0 else None


# ---------------------------------------------------------------- extraction --
def extract_terms(tree: pathlib.Path, k: int):
    """Return (features, products, R) for loader k.

    features : [{t, q, fn}]                 a cached quadratic form
    products : [{t, tgt, fn, mask_out}]     a quadratic form applied to outputs
    R        : {feature index -> set of output indices}
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
    out_index = {q: i for i, q in enumerate(wq)}
    # the linear phase: CX from an ancilla into a word output
    R = defaultdict(set)
    # a feature is "used" by a product when the product's control wire is that
    # ancilla, or by the linear phase when a CX copies it into a word output.
    live = {}
    # value provenance: for every wire, the GF(2) combination of FEATURE values
    # currently on it (bitmask over feature indices), plus the set of selection
    # bits linearly mixed into it.
    prov = {}
    for idx, (t, a, c) in enumerate(ops):
        if t == "CX":
            src, dst = a[0], a[1]
            if src >= 46 and dst < 46:
                # a CX out of an ancilla: either the linear fan-out of a
                # feature into an output, or a "pre" op that copies a feature
                # into a control wire.
                if dst in out_index:
                    if src in live:
                        R[live[src]].add(out_index[dst])
                elif src in live:
                    prov[dst] = prov.get(dst, 0) ^ (1 << live[src])
            elif src in live:
                prov[dst] = prov.get(dst, 0) ^ (1 << live[src])
            f[dst] = f.get(dst, 0) ^ f.get(src, 0)
        elif t == "X":
            f[a[0]] = f.get(a[0], 0) ^ ALL
        elif t == "CCX":
            u, v = f.get(a[0], 0), f.get(a[1], 0)
            f[a[2]] = f.get(a[2], 0) ^ (u & v)
            if a[2] >= 46:
                live[a[2]] = len(features)
                features.append({"t": idx, "q": a[2], "fn": u & v,
                                 "c1": a[0], "c2": a[1]})
                prov[a[2]] = 0
            else:
                # the product consumes the two control wires' current values
                sup = prov.get(a[0], 0) | prov.get(a[1], 0)
                products.append({"t": idx, "tgt": a[2], "fn": u & v,
                                 "c1": a[0], "c2": a[1], "sup": sup})
                for bit in range(len(features)):
                    if (sup >> bit) & 1:
                        R[bit].add(out_index[a[2]])
        elif t == "HMR":
            live.pop(a[0], None)
            prov.pop(a[0], None)
            f[a[0]] = 0
    # the products also consume the two control wires' VALUES; record which
    # feature each control wire holds at that moment
    return features, products, R, ops, sel, wq, live


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    tree = pathlib.Path(args[0])
    batches = [int(x) for x in args[1:]] or [11]
    if "--all" in sys.argv:
        batches = list(range(15))
    mono, sel = build_basis()
    span = Span(mono)
    for b in mono:
        span.add(b)
    out = []
    for k in batches:
        feats, prods, R, ops, selq, wq, live = extract_terms(tree, k)
        bad_f = [i for i, x in enumerate(feats) if not span.in_span(x["fn"])]
        bad_p = [i for i, x in enumerate(prods) if not span.in_span(x["fn"])]
        # the targets: output deltas
        states = CE.chain_states(tree / "submission.npz")
        import numpy as np
        Dm = []
        for j in range(len(wq)):
            d = np.asarray(states[k + 1][j], bool) ^ np.asarray(states[k][j], bool)
            m = 0
            for a in np.nonzero(d)[0]:
                m |= 1 << int(a)
            Dm.append(m)
        bad_d = sum(0 if span.in_span(m) else 1 for m in Dm)
        # merge opportunities: q_a XOR q_b in the span?
        fns = [x["fn"] for x in feats]
        merges = 0
        merge_same_mask = 0
        fmask = {i: frozenset(R.get(i, ())) for i in range(len(feats))}
        for i in range(len(fns)):
            for j in range(i + 1, len(fns)):
                if span.in_span(fns[i] ^ fns[j]):
                    merges += 1
                    if fmask[i] == fmask[j] and fmask[i]:
                        merge_same_mask += 1
        rec = {
            "k": k,
            "features": len(feats),
            "products": len(prods),
            "terms_total": len(feats) + len(prods),
            "features_outside_quad_span": len(bad_f),
            "products_outside_quad_span": len(bad_p),
            "target_deltas_outside_quad_span": bad_d,
            "feature_pairs_whose_xor_is_quadratic": merges,
            "feature_pairs_mergeable_same_mask": merge_same_mask,
            "distinct_feature_output_masks": len({fmask[i] for i in range(len(feats))}),
        }
        print(f"k={k:2d}: terms {rec['terms_total']:3d} (F {len(feats)} + P {len(prods)}) "
              f"| outside quad span: F {len(bad_f)}, P {len(bad_p)}, D {bad_d} "
              f"| mergeable pairs {merges} (same-mask {merge_same_mask}) "
              f"| distinct feature masks {rec['distinct_feature_output_masks']}", flush=True)
        out.append(rec)
    p = ROOT / "work/recon/chem_quad.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(out, indent=1))
    print(f"\nwrote {p}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
