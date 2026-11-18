#!/usr/bin/env python3
"""chem_brot_probe.py — quantization sensitivity of a DF-THC submission.

Takes the official verifier's `evaluate_words` and asks: if the angle words are
re-rounded from their current width to a narrower one (brot), what happens to
error_1, error_2, E_gap and lambda_eff?

Re-rounding: a word w at width b means theta/pi = w / 2**(b-1).  At the
narrower width b' the same angle is represented by w' = round(w / 2**(b-b')),
so the *same* angle rounded to the coarser grid.

Usage: chem_brot_probe.py SUBMISSION.npz [brot ...]
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/verifiers')

from dfthcsos.verify import evaluate_words, load_inputs  # noqa: E402

ERROR_1_THRESHOLD = 0.020
ERROR_2_THRESHOLD = 0.020
E_GAP_FLOOR = 3.914898
LAMBDA_FLOOR = 49.0


def main():
    path = sys.argv[1]
    brots = [int(x) for x in sys.argv[2:]] or [8, 7, 6, 5]
    data = np.load(path, allow_pickle=False)
    words = np.asarray(data['angle_words'], dtype=np.int64)
    tree = np.asarray(data['tree_edges'], dtype=np.int64)
    brot0 = int(words.max()).bit_length()
    # the true width comes from the word register, infer it from the data range
    print(f'file: {path}')
    print(f'  words shape {words.shape}  max word {words.max()}  inferred width {brot0}')
    inputs = load_inputs(path)
    print(f'  Lambda = {inputs.w.__abs__().sum():.6f}   (raw LCU sum |w|)')

    for b in brots:
        if b == brot0:
            w = words
        else:
            shift = brot0 - b
            w = np.round(words.astype(np.float64) / (2 ** shift)).astype(np.int64)
            w = np.clip(w, 0, (1 << b) - 1)
        m = evaluate_words(inputs, w, tree, b)
        ok1 = m['error_1'] <= ERROR_1_THRESHOLD
        ok2 = m['error_2'] <= ERROR_2_THRESHOLD
        okg = m['E_gap'] > E_GAP_FLOOR
        okl = m['Lambda'] > LAMBDA_FLOOR
        print(f'\n  brot={b}:  error_1={m["error_1"]*1000:.6f} mHa [{"OK" if ok1 else "FAIL"}]'
              f'   error_2={m["error_2"]*1000:.6f} mHa [{"OK" if ok2 else "FAIL"}]')
        print(f'          E_gap={m["E_gap"]:.12f} [{"OK" if okg else "FAIL"}]'
              f'   Lambda={m["Lambda"]:.6f} [{"OK" if okl else "FAIL"}]'
              f'   lambda_eff={m["lambda_eff"]:.8f}')
        # cost model at this width, with our current angles Toffoli count scaled
        if b == brot0:
            print(f'          (current width: cost model applies directly)')
        else:
            scale = b / brot0
            ang = 8044 * scale
            giv = 2 * 75 * (2 * b - 1)
            T = 317 + 4095 + giv + ang
            Q = 40 + 44 + 5 * b + max(90, 303, 77)
            score = m['lambda_eff'] * T * Q
            ref = 3_355_599_588.3155375
            print(f'          est score {score:,.0f}  ratio {ref/score:.4f}'
                  f'  (T~{T:.0f} Q~{Q})')


if __name__ == '__main__':
    main()
