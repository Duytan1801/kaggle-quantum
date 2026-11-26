#!/usr/bin/env python3
"""chem_brot.py — how much does lambda_eff pay for a narrower word register?

WHY THIS MATTERS
    The chemistry score is

        score = lambda_eff * T_total * Q_total

    and the scoring model adds

        T_total = <ANGLE Toffolis, both passes>
                  + outer_state_prep() + inner_state_prep()
                  + 2 * (N - 1) * (2 * brot - 1)

    with `brot` the width of ONE word register -- the number of bits per
    angle word.  Our submission ships 5 words of 7 bits each, so brot = 7
    and the Givens term is 2*75*13 = 1950 Toffolis.  Dropping to brot = 6
    saves 300 Toffolis of T_total (2.3 % of 13166) and 5 qubits of
    Q_total (J*brot, 35 -> 30).  The price is the precision of the angle
    words, which enters through lambda_eff.

    This script measures the price: it rounds the shipped words to 6 and 5
    bits and runs the OFFICIAL metric code (evaluate_words) on them.  No
    circuit is built here -- only the metric, which is the cheap half.

Usage: chem_brot.py [tree]   (default work/trees/v149)
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))
sys.path.insert(0, str(ROOT / 'work/toolchain/verifiers'))
from dfthcsos.verify import evaluate_words, load_inputs, passes_accuracy   # noqa: E402

# our shipped numbers (v149)
OUR_T = 13166.0
OUR_Q = 405.0
OUR_LAMBDA = 46.91432538757801
OUR_GM = 33.21179


def main():
    tree = sys.argv[1] if len(sys.argv) > 1 else 'v149'
    d = ROOT / 'work/trees' / tree / 'dfthcsos'
    npz = d / 'submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    edges = z['tree_edges']
    print(f'{npz}   angle_words {W.shape} dtype {W.dtype}  max word {int(W.max())} '
          f'(=> brot {int(W.max()).bit_length()})')
    print(f'tree_edges {edges.shape}')
    print()

    inputs = load_inputs(str(npz))
    print('loaded official reference inputs')
    print()

    print(f'{"brot":>4s} {"lambda_eff":>12s} {"ratio":>8s} {"error_1":>10s} {"error_2":>10s} '
          f'{"Lambda":>10s} {"E_gap":>10s} {"pass":>5s}')
    rows = []
    for brot in (7, 6, 5, 4):
        words = W >> (7 - brot) if brot < 7 else W.copy()
        m = evaluate_words(inputs, words, edges, brot)
        ok = passes_accuracy(m)
        lam = float(m['lambda_eff'])
        print(f'{brot:4d} {lam:12.6f} {lam / OUR_LAMBDA:8.4f} {m["error_1"]:10.6f} '
              f'{m["error_2"]:10.6f} {m["Lambda"]:10.4f} {m["E_gap"]:10.6f} {str(ok):>5s}')
        rows.append((brot, lam, ok))

    print()
    print('--- projected score if the loaders were rebuilt at that width ---')
    print('    T_total  = 6666 (ANGLE Toffolis, both passes) + 4550 (state prep) + 150*(2*brot-1)')
    print('    Q_total  = 370 + J*brot  with J = 5')
    for brot, lam, ok in rows:
        T = 6666 + 4550 + 150 * (2 * brot - 1)
        Q = 370 + 5 * brot
        ratio = (lam / OUR_LAMBDA) * (OUR_T / T) * (OUR_Q / Q)
        gm = OUR_GM * ratio ** (-1 / 3)
        print(f'    brot={brot}: T={T:.0f} Q={Q:.0f} lambda={lam:.4f} '
              f'score ratio={ratio:.5f}  GM {OUR_GM:.5f} -> {gm:.5f} '
              f'({"WIN" if gm > OUR_GM else "loss"}){"  [metrics FAIL]" if not ok else ""}')


if __name__ == '__main__':
    raise SystemExit(main())
