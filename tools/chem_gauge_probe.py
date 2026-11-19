#!/usr/bin/env python3
"""chem_gauge_probe.py — is the signed gauge metric-preserving for the chem leg?

The official verifier scores the words it RECOVERS FROM THE CIRCUITS:
    metrics = evaluate_words(inputs, recovered_words, tree_edges, brot)
so the npz's `angle_words` are not the scored object — the loaded words are.
The repo's own generator (marculera's tensorqrom) refuses to build from words
that are not in the signed gauge (bit brot-1 == bit brot-2), while our shipped
loaders load the raw npz table (only 79.06% gauge-compliant).

If the signed-gauge transform preserves the chemistry EXACTLY (same lambda_eff,
same error_1/error_2), then we can rebuild the family with the repo generator at
any J and the chemistry is untouched: only T and Q move.

This probe evaluates the metrics for:
  * the raw npz words,
  * onebody.signed_gauge(npz words)   (edge-aware, the repo's own transform),
  * a naive per-word gauge fix        (no edge sign propagation),
using the OFFICIAL verifier code, with no simulation.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
VER = ROOT / 'work/toolchain/verifiers'
KICK = ROOT / 'work/toolchain/kickmix'
REFIT = ROOT / 'work/tools/dfthc_refit'


def metrics_for(inputs, words, edges, brot):
    from dfthcsos.verify import evaluate_words
    m = evaluate_words(inputs, words, edges, brot)
    return {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
            for k, v in m.items()}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--npz', required=True)
    a = ap.parse_args()
    sys.path.insert(0, str(VER))
    sys.path.insert(0, str(KICK))
    sys.path.insert(0, str(REFIT))
    os_env = {'DFTHC_DATA': str(ROOT / 'work/toolchain')}
    import os
    os.environ.setdefault('DFTHC_DATA', os_env['DFTHC_DATA'])

    npz = pathlib.Path(a.npz)
    with np.load(npz, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64)
        edges = np.asarray(z['tree_edges'], np.int64)
        brot = int(z['brot']) if 'brot' in z.files else 8

    from dfthcsos.verify import load_inputs
    inputs = load_inputs(npz)
    print(f'inputs loaded: num_vectors={inputs.num_vectors} num_angles={inputs.num_orbitals - 1}')

    import onebody
    signed = onebody.signed_gauge(words, edges, brot)

    mod = 1 << brot
    half, quarter = mod >> 1, mod >> 2
    naive = np.where((words >= quarter) & (words < 3 * quarter), (words + half) % mod, words)

    def gfrac(w):
        return 1.0 - float(np.mean((((w >> (brot - 1)) ^ (w >> (brot - 2))) & 1)))

    variants = [('npz', words), ('onebody.signed_gauge', signed), ('naive per-word', naive)]
    base = None
    for name, w in variants:
        m = metrics_for(inputs, w, edges, brot)
        if base is None:
            base = m
        keys = ['lambda_eff', 'error_1', 'error_2', 'Lambda', 'E_gap']
        line = '  '.join(f'{k}={m.get(k)!r}' for k in keys if k in m)
        print(f'\n[{name}] gauge_ok={gfrac(w):.6f}  equal_to_npz={np.array_equal(w, words)}')
        print(f'   {line}')
        if name != 'npz':
            same = all(abs(float(m[k]) - float(base[k])) < 1e-12
                       for k in keys if k in m and isinstance(base.get(k), (int, float)))
            print(f'   metrics identical to npz: {same}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
