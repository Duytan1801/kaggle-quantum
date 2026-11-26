#!/usr/bin/env python3
"""chem_extract.py -- recover the LOGICAL PLAN of an old chemistry loader.

The five loaders goodpjw2008 did not re-solve (k = 0,1,5,7,11) cost
240-245 Toffolis each.  Their plans are not public, but the CIRCUITS are, so
the plan can be recovered by function tracking:

  * every ancilla is initialised by a CCX, so it carries a product of two
    address functions -- that is a CACHED FEATURE;
  * every CCX whose target is a word register is a PRODUCT of two feature
    combinations (u . v) XORed into that output;
  * the CNOTs from ancillas to word registers at the end are the LINEAR REST
    (free).

This tool recovers, for one loader:
  * the number of features and products,
  * for every product: the two factors as GF(2) combinations of the feature
    basis, and the output mask (which word bits it feeds),
  * whether the products are "wired" (a product feeding several outputs) or
    "unwired" (every product feeds exactly one output).

Usage: chem_extract.py <tree-dir> [batch ...]
"""
from __future__ import annotations

import io
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import kickmix as km                                      # noqa: E402
import chem_plan as CP                                    # noqa: E402

NV = 1219
ADDR = np.arange(NV)


def fun(a):
    return int.from_bytes(np.packbits(np.asarray(a, bool), bitorder='little').tobytes(), 'little')


ALL = (1 << NV) - 1


def parse_kmx(path):
    c = km.Circuit.from_file(str(path), 'kmb')
    b = io.BytesIO()
    c.to_file(b, format='kmx')
    regs, items, ops = {}, {}, []
    for line in b.getvalue().decode().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == 'REGISTER':
            regs[t[1]] = t[2].strip('"')
        elif t[0] == 'APPEND_TO_REGISTER':
            items.setdefault(t[2], []).append(int(t[1][1:]))
        else:
            ops.append((t[0], [int(x[1:]) for x in t[1:] if x[0] == 'q'],
                        t[-1] if t[-1].startswith('b') else None))
    by = {regs[r]: items[r] for r in regs}
    sel = by['selection']
    wq = [q for j in range(5) for q in by[f'word_{j}']]
    return ops, sel, wq


def chain_states(npz):
    """incoming word values for each loader: state_{k-1} = XOR of deltas."""
    z = np.load(npz)
    W = np.asarray(z['angle_words'], dtype=np.int64)
    states = [np.zeros((35, NV), bool)]
    for k in range(15):
        d = CP.word_bits(W, k) ^ CP.word_bits(W, k - 1)
        states.append(states[-1] ^ d)
    return states


class Basis:
    """GF(2) basis of known functions, with provenance names."""

    def __init__(self):
        self.rows = []          # (int mask, frozenset of support labels)

    def add(self, v, label):
        v, sup = self.reduce(v)
        if v:
            self.rows.append((v, sup | {label}))
        return sup | {label}

    def reduce(self, v, extra=frozenset()):
        sup = set(extra)
        for m, s in self.rows:
            if v >> m.bit_length() - 1 & 1:
                v ^= m
                sup ^= set(s)
        return v, frozenset(sup)


def extract(tree, k, states):
    path = pathlib.Path(tree) / f'angle_k_{k}.kmb'
    ops, sel, wq = parse_kmx(path)
    zin = states[k]
    f = {}
    for i, q in enumerate(sel):
        f[q] = fun((ADDR >> i) & 1)
    for j, q in enumerate(wq):
        f[q] = fun(zin[j])
    labels = {q: f'sel{i}' for i, q in enumerate(sel)}
    for j, q in enumerate(wq):
        labels[q] = f'w{j}'

    bas = Basis()
    for i, q in enumerate(sel):
        bas.add(f[q], f'sel{i}')
    # the QUADS features are computed into word qubits 7j+6 by a CX
    quads = {}
    basis = Basis()
    for i, q in enumerate(sel):
        basis.add(f[q], f'sel{i}')

    features = {}          # ancilla -> function at creation
    feat_label = {}
    products = []
    cb = {}
    pending_fan = set()
    for idx, (t, a, c) in enumerate(ops):
        if t == 'CX':
            f[a[1]] = f.get(a[1], 0) ^ f.get(a[0], 0)
            if 11 <= a[0] < 46 and 11 <= a[1] < 46:
                pending_fan.add(a[1])
            elif a[0] >= 46 and 11 <= a[1] < 46:
                pass          # linear rest / fan-out from ancilla
        elif t == 'X':
            f[a[0]] = f.get(a[0], 0) ^ ALL
        elif t == 'CCX':
            u, v = f.get(a[0], 0), f.get(a[1], 0)
            f[a[2]] = f.get(a[2], 0) ^ (u & v)
            if a[2] >= 46:
                features[a[2]] = u & v
            else:
                # a product: the controls are combinations of known features
                products.append(dict(idx=idx, tgt=a[2], u=u, v=v,
                                     fan=sorted(pending_fan)))
            pending_fan = set()
        elif t == 'HMR':
            cb[c] = f.get(a[0], 0)
            f[a[0]] = 0
        # Z / CZ are phase-only: no effect on the computational-basis values
    return ops, sel, wq, f, features, products, cb


def main() -> int:
    tree = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'work/trees/v149/dfthcsos')
    ks = [int(a) for a in sys.argv[2:]] or [0]
    npz = pathlib.Path(tree) / 'submission.npz'
    states = chain_states(npz)
    for k in ks:
        ops, sel, wq, f, features, products, cb = extract(tree, k, states)
        # check the output
        out = np.zeros((35, NV), bool)
        for j, q in enumerate(wq):
            bits = np.unpackbits(np.frombuffer(f[q].to_bytes((NV + 7) // 8, 'little'),
                                               dtype=np.uint8), bitorder='little')[:NV].astype(bool)
            out[j] = bits
        want = states[k + 1]
        ok = bool((out == want).all())
        print(f'=== batch k={k}: {len(features)} feature CCX, {len(products)} product CCX, '
              f'{len(cb)} classical bits')
        print(f'    output matches the target delta chain: {ok}')
        masks = {}
        for p in products:
            m = tuple(sorted(set(p['fan']) | {p['tgt']}))
            masks[m] = masks.get(m, 0) + 1
        multi = {m: c for m, c in masks.items() if len(m) > 1}
        print(f'    distinct output masks: {len(masks)}; masks with >1 output: {len(multi)} '
              f'(products {sum(multi.values())})')
        sizes = {}
        for m, c in masks.items():
            sizes[len(m)] = sizes.get(len(m), 0) + c
        print(f'    mask-size histogram (products per size): {dict(sorted(sizes.items()))}')
        print(f'    output bits touched: {len(set(masks))} -> '
              f'{sorted(set(q for m in masks for q in m))[:40]}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
