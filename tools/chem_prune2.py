#!/usr/bin/env python3
"""chem_prune2.py -- LINEAR-DEPENDENCE pruning of the cached features.

THE QUESTION
    A chemistry loader costs  (#cached features) + (#products) Toffolis.  The
    cached features are the AND-gates; the products are the AND-gates that
    XOR into the word registers; every CNOT is free.

    The cached features span a subspace F of the function space GF(2)^1219.
    If F is OVER-PROVISIONED -- if some feature is a linear combination of
    the others -- then it can be dropped: every parity that used it can be
    rewritten with the remaining ones, and the feature's own AND-gate (1
    Toffoli) disappears.

    goodpjw2008's published plans were checked for UNUSED features ("none
    unused") but never for LINEAR DEPENDENCE.  This tool measures:

      * dim(F)            -- the rank of the cached features,
      * dim(W)            -- the rank of the space of all parities the plan
                             actually uses (product factors, the linear rest
                             and every feature's own definition factors),
      * the minimal subset F' of the features that still spans W.

    If |F'| < |F| the loader can be re-emitted with fewer Toffolis.

Usage: chem_prune2.py <tree-dir> [batch ...]
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219
BANK, LOW = CE.ADDR >> 4, CE.ADDR & 15


def gf2_rank(vectors):
    piv = {}
    rank = 0
    for v in vectors:
        v = int(v)
        while v:
            b = v.bit_length() - 1
            row = piv.get(b)
            if row is None:
                piv[b] = v
                rank += 1
                break
            v ^= row
    return rank


def gf2_span(vectors):
    piv = {}
    for v in vectors:
        v = int(v)
        while v:
            b = v.bit_length() - 1
            row = piv.get(b)
            if row is None:
                piv[b] = v
                break
            v ^= row
    return piv


def in_span(v, piv):
    v = int(v)
    while v:
        b = v.bit_length() - 1
        row = piv.get(b)
        if row is None:
            return False
        v ^= row
    return True


def extract_plan(tree, k, states):
    """-> features (functions), products (u, v, mask), targets D_i."""
    ops, sel, wq = CE.parse_kmx(pathlib.Path(tree) / f'angle_k_{k}.kmb')
    zin = states[k]
    cur = {}
    feat_at = {}
    for i, q in enumerate(sel):
        cur[q] = CE.fun((CE.ADDR >> i) & 1)
    for j, q in enumerate(wq):
        cur[q] = CE.fun(zin[j])
    feats = []            # (target, function, u, v)
    prods = []            # (u, v, mask, target)
    fan = []
    anc_word_cx = 0
    R = {q: 0 for q in wq}
    for idx, (t, a, c) in enumerate(ops):
        if t == 'CX':
            if 11 <= a[0] < 46 and 11 <= a[1] < 46:
                fan.append((a[0], a[1]))
            elif a[0] >= 46 and 11 <= a[1] < 46:
                anc_word_cx += 1
                R[a[1]] ^= feat_at.get(a[0], 0)
            cur[a[1]] = cur.get(a[1], 0) ^ cur.get(a[0], 0)
        elif t == 'X':
            cur[a[0]] = cur.get(a[0], 0) ^ CE.ALL
        elif t == 'CCX':
            u, v = cur.get(a[0], 0), cur.get(a[1], 0)
            if a[2] >= 46:
                feat_at[a[2]] = u & v
                feats.append((a[2], u & v, u, v))
            else:
                prods.append((u, v, list(fan), a[2]))
                fan = []
            cur[a[2]] = cur.get(a[2], 0) ^ (u & v)
        elif t == 'HMR':
            feat_at[a[0]] = 0
            cur[a[0]] = 0
    return feats, prods, anc_word_cx, cur, wq, R


def main() -> int:
    tree = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'work/trees/v149/dfthcsos')
    ks = [int(a) for a in sys.argv[2:] if not a.startswith('--')] or [0]
    states = CE.chain_states(pathlib.Path(tree) / 'submission.npz')
    for k in ks:
        feats, prods, anc_word_cx, cur, wq, Rc = extract_plan(tree, k, states)
        # the masks: the fan CXs after a product copy the product value into
        # the other output word qubits.  A CX (src,dst) with src == the
        # product's target means dst is in the mask.
        masks = []
        for u, v, fan, tgt in prods:
            m = {tgt}
            for src, dst in fan:
                if src == tgt:
                    m.add(dst)
            masks.append(m)
        # the linear rest, read from the circuit (ancilla -> word CNOTs)
        R = [Rc[q] for q in wq]
        # the space of every parity the plan uses
        parities = []
        for u, v, _, _ in prods:
            parities += [u, v]
        parities += R
        for _, _, u, v in feats:
            parities += [u, v]
        # the features themselves
        ffuncs = [f[1] for f in feats]
        dimF = gf2_rank(ffuncs)
        dimW = gf2_rank(parities)
        # minimal subset of the features spanning the parities
        Wpiv = gf2_span(parities)
        kept = []
        piv = {}
        for f in ffuncs:
            v = f
            while v:
                b = v.bit_length() - 1
                row = piv.get(b)
                if row is None:
                    piv[b] = v
                    break
                v ^= row
            else:
                continue                      # dependent on what we kept
            kept.append(f)
            # is the span now enough?
            if all(in_span(p, piv) for p in parities):
                break
        # maybe fewer are needed: try dropping kept features greedily
        need = list(kept)
        i = 0
        while i < len(need):
            trial = need[:i] + need[i + 1:]
            piv2 = gf2_span(trial)
            if all(in_span(p, piv2) for p in parities):
                need = trial
            else:
                i += 1
        print(f'=== batch k={k}: {len(feats)} feature CCX, {len(prods)} product CCX, '
              f'{anc_word_cx} ancilla->word CX')
        print(f'    dim(span of features) = {dimF}   dim(span of used parities) = {dimW}')
        print(f'    minimal feature subset spanning the parities: {len(need)}'
              f'   => saving {len(feats)-len(need)} Toffolis')
        print(f'    total Toffolis now {len(feats)+len(prods)} -> '
              f'{len(need)+len(prods)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
