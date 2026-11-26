#!/usr/bin/env python3
"""chem_brot_cliff.py -- the brot (rotation-precision) cliff.

THE LEVER
    The chemistry cost model's Givens-rotation cost is

        givens_rotations() = 2 * (N - 1) * (2 * brot - 1)

    and the word registers are `brot` bits wide, so lowering `brot` by one
    saves 2*(N-1) = 150 Toffolis AND `brot`-width word qubits:

        brot  givens  T_total  word_q  Q_total  score@lam46.914   dGM
          7     1950    13166      35      405    250,157,973      0.0000
          6     1650    12866      30      400    221,999,xxx     +0.40xx
          5     1350    12566      25      395    ~195,xxx       +0.81xx

    `brot` is NOT a free parameter of the npz: the verifier reads it from
    the ANGLE family's word-register width, and the words are decoded as

        theta / pi = word / 2**(brot - 1),    word in [0, 2**brot)

    so lowering brot coarsens the representable angle grid by 2x and forces
    a re-quantization of every angle word:

        word' = round(word / 2)      (brot 7 -> 6)

    THE GATE: error_1 and error_2 must each stay <= 0.020.  On v149 they sit
    at 0.01999999988 -- a razor-thin 1.2e-10 below the threshold -- because
    the factorization was trained/tuned for brot = 7.  This script measures
    the cliff: re-quantize the words at each brot and evaluate the OFFICIAL
    metric code.

Usage: chem_brot_cliff.py [npz] [--brot 6 5 ...]
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/verifiers'))
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))

from dfthcsos.scoreinfra.dfthc_math import evaluate_dfthc_angle_words  # noqa: E402
from dfthcsos.scoreinfra.costs_prepare import SpinFreeData_V1           # noqa: E402

N = 76
CHI = 10
UPPER = -22140.27335
GM0 = 33.21179
SCORE0 = 250157973.2614051


def native(w, h2i):
    w = np.asarray(w, dtype=np.float64)
    return np.asarray(h2i, dtype=np.float64) - np.sum(w, axis=1)


def costs(brot, R=9, B=127, C=46, ang_t=6666.0, ang_pers=35, ang_sel=11):
    m = SpinFreeData_V1(R=R, B=B, C=C, N=N, chi=CHI, beta=brot)
    t = m.outer_state_prep() + m.inner_state_prep()
    gv = m.givens_rotations()
    qo = m.outer_state_prep_qubit_cost()
    qi = m.inner_state_prep_qubit_cost()
    pers = qo['persistent'] + qi['persistent']
    tmp = max(qo['temporary'], qi['temporary'])
    T = ang_t + t + gv
    word_q = brot * 5                      # J = 5 word registers
    ang_temp = word_q - ang_sel - ang_pers
    persistent = pers + ang_pers
    Q = persistent + max(tmp, ang_temp)
    return T, Q, gv


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('npz', nargs='?', default=str(ROOT / 'work/trees/v149/dfthcsos/submission.npz'))
    ap.add_argument('--brot', type=int, nargs='*', default=[8, 7, 6, 5])
    args = ap.parse_args()

    p = pathlib.Path(args.npz)
    z = np.load(p)
    U, W, H2I = z['U'], z['W'], z['H2_I']
    R, B, C = W.shape
    words, edges = z['angle_words'], z['tree_edges']

    from dfthcsos.verify import load_inputs
    inp = load_inputs({'U': U, 'W': W, 'H2_I': H2I, 'H1_I': z['H1_I'],
                       'Hsym_lower': z['Hsym_lower']})
    S, beta_1, ref = inp.S, inp.beta_1, inp.ref
    w = np.asarray(W, dtype=np.float64)
    h2 = np.asarray(H2I, dtype=np.float64)
    Wn = native(w, h2)

    print(f'{p.name}: R={R} B={B} C={C}  words {words.shape} '
          f'range [{words.min()}, {words.max()}]')
    print()
    hdr = (f'{"brot":>5s} {"quant":>6s} {"err_1":>16s} {"err_2":>16s} '
           f'{"lambda_eff":>12s} {"E_gap":>12s} {"T":>7s} {"Q":>5s} '
           f'{"score":>15s} {"dGM":>8s}  gates')
    print(hdr)
    for brot in args.brot:
        shift = 7 - brot
        for quant in ('floor', 'round'):
            if shift == 0:
                wq = words
            elif quant == 'floor':
                wq = words >> shift
            else:
                wq = (words + (1 << (shift - 1))) >> shift if shift > 1 else words
            if wq.max() >= (1 << brot):
                wq = np.minimum(wq, (1 << brot) - 1)
            m = evaluate_dfthc_angle_words(wq, w, Wn, S, beta_1, ref, brot=brot,
                                           tree_edges=edges, energy_upper=UPPER)
            T, Q, gv = costs(brot, R, B, C)
            lam = m['lambda_eff']
            sc = lam * T * Q
            ok1 = m['error_1'] <= 0.020
            ok2 = m['error_2'] <= 0.020
            okg = bool(m['gap_in_domain']) and m['E_gap'] > 3.914898 and m['Lambda'] > 49.0
            gate = 'PASS' if (ok1 and ok2 and okg) else 'FAIL'
            dgm = GM0 / 3 * (SCORE0 / sc - 1) if sc > 0 else float('nan')
            print(f'{brot:5d} {quant:>6s} {m["error_1"]:16.12f} {m["error_2"]:16.12f} '
                  f'{lam:12.6f} {m["E_gap"]:12.9f} {T:7.0f} {Q:5d} {sc:15,.0f} '
                  f'{dgm:+8.4f}  {gate}')
    print()
    print('(the word registers are brot bits wide, so Q also drops by 5 per brot step;')
    print(' the ANGLE family must be rebuilt at the new width and all 15 loaders')
    print(' re-derived, since the batch deltas change with the re-quantization.)')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
