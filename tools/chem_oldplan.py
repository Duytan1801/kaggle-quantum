#!/usr/bin/env python3
"""chem_oldplan.py -- recover the FULL logical plan of an old chemistry loader.

Why
    The five loaders goodpjw2008 did not re-solve (k = 0,1,5,7,11) cost
    240-245 Toffolis each.  Their plans are not public, but their CIRCUITS
    are, and a plan is recoverable from a circuit by function tracking:

      * every CCX into an ancilla computes a CACHED FEATURE  f = u AND v,
        where u and v are GF(2) combinations of the address bits and of the
        earlier features;
      * every CCX into a word register applies a PRODUCT  g = u AND v to one
        output;
      * the CNOTs are free, so a factor may be a parity of many features.

    This tool recovers, for one loader:
      * the feature DAG (each feature's two factors, as label sets),
      * every product's two factors (label sets) and its output,
      * how often each feature is used.

Usage: chem_oldplan.py <tree-dir> [batch ...] [--json OUT.json]
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_extract as CE                                  # noqa: E402

NV = 1219


class GF2:
    """Reduced row echelon basis over GF(2) with provenance labels.

    Invariant: a row (m, L) means  m = XOR_{l in L} value(l).
    """

    def __init__(self):
        self.piv: dict[int, tuple[int, frozenset]] = {}

    def reduce(self, v, labels=frozenset()):
        v = int(v)
        lab = set(labels)
        while v:
            b = v.bit_length() - 1
            row = self.piv.get(b)
            if row is None:
                break
            m, s = row
            v ^= m
            lab ^= set(s)
        return v, frozenset(lab)

    def add(self, v, label):
        v, lab = self.reduce(v)
        if v:
            b = v.bit_length() - 1
            newlab = lab | {label}
            for b2, (m, s) in list(self.piv.items()):
                if b2 != b and (m >> b) & 1:
                    self.piv[b2] = (m ^ v, s ^ newlab)
            self.piv[b] = (v, newlab)
        return lab | {label}


def analyse(tree, k, states):
    ops, sel, wq = CE.parse_kmx(pathlib.Path(tree) / f'angle_k_{k}.kmb')
    zin = states[k]
    cur = {}
    for i, q in enumerate(sel):
        cur[q] = CE.fun((CE.ADDR >> i) & 1)
    for j, q in enumerate(wq):
        cur[q] = CE.fun(zin[j])

    bas = GF2()
    for i, q in enumerate(sel):
        bas.add(cur[q], f'S{i}')

    features = []          # dicts: idx, target, u, v (label sets), ufun, vfun
    products = []
    word_word_cx = 0
    for idx, (t, a, c) in enumerate(ops):
        if t == 'CX':
            if 11 <= a[0] < 46 and 11 <= a[1] < 46:
                word_word_cx += 1
            cur[a[1]] = cur.get(a[1], 0) ^ cur.get(a[0], 0)
        elif t == 'X':
            cur[a[0]] = cur.get(a[0], 0) ^ CE.ALL
        elif t == 'CCX':
            u, v = cur.get(a[0], 0), cur.get(a[1], 0)
            ru, lu = bas.reduce(u)
            rv, lv = bas.reduce(v)
            if a[2] >= 46:
                fid = f'F{len(features)}'
                feats = dict(idx=idx, target=a[2], u=sorted(lu), v=sorted(lv),
                             ufun=u, vfun=v, ru=ru, rv=rv)
                features.append(feats)
                # insert the new element: f = u AND v
                bas.add(u & v, fid)
                cur[a[2]] = u & v
            else:
                products.append(dict(idx=idx, target=a[2], u=sorted(lu), v=sorted(lv),
                                     ufun=u, vfun=v, ru=ru, rv=rv))
                cur[a[2]] = cur.get(a[2], 0) ^ (u & v)
        elif t == 'HMR':
            cur[a[0]] = 0
    return dict(features=features, products=products, word_word_cx=word_word_cx,
                sel=sel, wq=wq, cur=cur)


def main() -> int:
    tree = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / 'work/trees/v149/dfthcsos')
    args = [a for a in sys.argv[2:] if not a.startswith('--')]
    ks = [int(a) for a in args] or [0]
    jsonout = None
    if '--json' in sys.argv:
        jsonout = sys.argv[sys.argv.index('--json') + 1]
    states = CE.chain_states(pathlib.Path(tree) / 'submission.npz')
    allout = {}
    for k in ks:
        r = analyse(tree, k, states)
        feats, prods = r['features'], r['products']
        use = Counter()
        for p in prods:
            use.update(p['u'])
            use.update(p['v'])
        print(f'=== batch k={k}: {len(feats)} feature CCX, {len(prods)} product CCX, '
              f'{r["word_word_cx"]} word-word CX')
        print(f'    total Toffolis: {len(feats)+len(prods)}')
        su = Counter(len(p['u']) for p in prods)
        sv = Counter(len(p['v']) for p in prods)
        print(f'    factor u support sizes: {dict(sorted(su.items()))}')
        print(f'    factor v support sizes: {dict(sorted(sv.items()))}')
        print(f'    features used by products: {len(use)} of {len(feats)}; '
              f'usage histogram {dict(sorted(Counter(use.values()).items()))}')
        print(f'    products with an unreducible factor: '
              f'{sum(1 for p in prods if p["ru"] or p["rv"])}')
        # the linear rest: CX from ancillas into word registers after the products
        print(f'    distinct product targets: {len(set(p["target"] for p in prods))}')
        allout[k] = dict(features=[{kk: vv for kk, vv in f.items()
                                    if kk not in ("ufun", "vfun")} for f in feats],
                         products=[{kk: vv for kk, vv in p.items()
                                    if kk not in ("ufun", "vfun")} for p in prods],
                         word_word_cx=r['word_word_cx'])
    if jsonout:
        pathlib.Path(jsonout).write_text(json.dumps(allout, indent=1))
        print(f'wrote {jsonout}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
