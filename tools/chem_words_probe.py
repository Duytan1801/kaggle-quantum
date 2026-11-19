#!/usr/bin/env python3
"""chem_words_probe.py — what words do the SHIPPED dfthcsos loaders actually load?

The official verifier (work/toolchain/verifiers/dfthcsos/verify.py) does NOT use
the npz's `angle_words` for scoring: it *recovers* the words from the circuits
(`recover_words_from_circuits`) and evaluates the chemistry on those.  So the
gauge (the signed-gauge convention bit(brot-1) == bit(brot-2)) of the LOADED
words is what decides lambda_eff and the error gates.

This probe:
  1. recovers the words from a family with the official code,
  2. compares them with the npz's `angle_words` (exact / per-bit),
  3. reports the signed-gauge property of both tables,
  4. checks whether the edge-aware signed-gauge transform (dfthc_refit/onebody.py)
     maps the npz table onto the recovered table,
so we know exactly which transform a rebuild must apply.
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--dir', required=True, help='directory with angle_k_*.kmb + submission.npz')
    ap.add_argument('--shots', type=int, default=1)
    ap.add_argument('--seed', type=int, default=12345)
    a = ap.parse_args()

    sys.path.insert(0, str(VER))
    sys.path.insert(0, str(KICK))
    from dfthcsos.scoreinfra.circuits import (  # noqa: E402
        load_circuits, recover_words_from_circuits, register_layout,
    )

    d = pathlib.Path(a.dir)
    family = load_circuits(d, format='auto')
    layout = register_layout(family)
    print(f'family: {len(family)} circuits, J={layout.batch_size}, brot={layout.brot}, '
          f'selection={len(layout.selection)}')

    with np.load(d / 'submission.npz', allow_pickle=False) as z:
        npz_words = np.asarray(z['angle_words'], np.int64)
        edges = np.asarray(z['tree_edges'], np.int64)
    print(f'npz angle_words: {npz_words.shape}')

    words, _layout, toffoli = recover_words_from_circuits(
        family, num_vectors=npz_words.shape[0], num_angles=npz_words.shape[1],
        shots_per_address=a.shots, seed=a.seed)
    print(f'recovered words: {words.shape}  mean toffolis/shot={toffoli:.2f}')

    def gauge_ok(w):
        top, below = w.shape[1] - 1, 0  # placeholder, replaced below
        return None

    def signed_fraction(w, brot):
        return 1.0 - float(np.mean((((w >> (brot - 1)) ^ (w >> (brot - 2))) & 1)))

    brot = layout.brot
    same = np.array_equal(words, npz_words)
    frac = float(np.mean(words == npz_words))
    print(f'\nexact match npz vs recovered: {same}   elementwise equal fraction {frac:.6f}')
    print(f'signed-gauge fraction: npz {signed_fraction(npz_words, brot):.6f}  '
          f'recovered {signed_fraction(words, brot):.6f}')
    if not same:
        diff = words != npz_words
        rows = np.where(diff.any(axis=1))[0]
        print(f'differing rows: {len(rows)} / {words.shape[0]}')
        print(f'first differing rows: {rows[:10].tolist()}')
        for r in rows[:5]:
            cols = np.where(diff[r])[0]
            print(f'  row {r}: cols {cols.tolist()[:12]}  npz={npz_words[r, cols[:6]].tolist()} '
                  f'rec={words[r, cols[:6]].tolist()}')

    # the repo's own edge-aware transform
    sys.path.insert(0, str(REFIT))
    import onebody  # noqa: E402
    signed = onebody.signed_gauge(npz_words, edges, brot)
    print(f'\nonebody.signed_gauge(npz) signed-gauge fraction: {signed_fraction(signed, brot):.6f}')
    print(f'signed == recovered exactly: {np.array_equal(signed, words)}')
    eq = float(np.mean(signed == words))
    print(f'signed == recovered elementwise fraction: {eq:.6f}')
    # does signed differ from npz only by negation/half-turn per row?
    print(f'signed vs npz elementwise fraction: {float(np.mean(signed == npz_words)):.6f}')
    np.savez(d.parent / 'words_probe.npz', recovered=words, npz=npz_words, signed=signed,
             edges=edges, brot=brot)
    print(f'\nwrote {d.parent / "words_probe.npz"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
