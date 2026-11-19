#!/usr/bin/env python3
"""chem_j_sizes.py — which (J, sizes, trials) can the tensor QROM actually cover?

The chem J-lever (more words per ANGLE circuit => fewer circuits => fewer
Toffolis) is only reachable if the repo's generator can decompose the mixed
tensor for that J.  `build_family` asserts "decomposition does not cover the
tensor" for J != 5 with the default partition, so this probe searches the
partition space directly on `tensorqrom.shared` (no circuit build) and reports
the first partition that covers, for each J and each trial budget.

The cover test is EXACTLY the one `build_circuit` uses:
    mixed_of(terms, L-1, H-1, O) == C[1:, 1:]
"""
from __future__ import annotations

import argparse
import itertools
import pathlib
import sys
import time

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
REFIT = ROOT / 'work/tools/dfthc_refit'
KICK = ROOT / 'work/toolchain/kickmix'
VER = ROOT / 'work/toolchain/verifiers'


def partitions(j: int, brot: int) -> list[list[int]]:
    """Candidate output-bit partitions for J words of (brot-1) bits."""
    bits = j * (brot - 1)
    out = []
    # uniform groups of g bits
    for g in range(4, 9):
        if bits % g == 0:
            out.append([g] * (bits // g))
    # one full word (7) plus the rest in equal chunks, like the repo's J=5 default
    for rest in range(4, 9):
        rem = bits - (brot - 1)
        if rem and rem % rest == 0:
            out.append([brot - 1] + [rest] * (rem // rest))
    # two levels: a few big groups then small ones
    for a in range(5, 8):
        for b in range(4, 8):
            for c in range(4, 8):
                if (bits - a - b) >= 0 and (bits - a - b) % c == 0 and (bits - a - b) // c <= 4:
                    out.append([a, b] + [c] * ((bits - a - b) // c))
    # the repo's own J=5 partition, generalised by scaling
    seen, uniq = set(), []
    for p in out:
        t = tuple(p)
        if t not in seen:
            seen.add(t)
            uniq.append(list(p))
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--npz', required=True)
    ap.add_argument('--js', default='6,7,8')
    ap.add_argument('--trials', default='6,32')
    ap.add_argument('--circuits', type=int, default=2, help='how many deltas of the family to test')
    ap.add_argument('--brot', type=int, default=8)
    ap.add_argument('--groups', action='store_true',
                    help='test the GROUPED low-cache path (the one build_circuit uses when the '
                         'full low cache does not fit in 128 qubits)')
    a = ap.parse_args()

    sys.path.insert(0, str(REFIT))
    sys.path.insert(0, str(KICK))
    sys.path.insert(0, str(VER))
    import tensorqrom  # noqa: E402
    from fourqrom import batch_deltas  # noqa: E402
    import onebody  # noqa: E402

    with np.load(a.npz, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64)
        edges = np.asarray(z['tree_edges'], np.int64)
    brot = a.brot
    words = onebody.signed_gauge(words, edges, brot)

    results = []
    for j in [int(x) for x in a.js.split(',')]:
        deltas = list(batch_deltas(words, j))
        nsel = max(1, (len(words) - 1).bit_length())
        cands = partitions(j, brot)
        print(f'\n=== J={j}: {len(deltas)} circuits, {j*(brot-1)} output bits, '
              f'{len(cands)} candidate partitions ===', flush=True)
        for sizes in cands:
            for trials in [int(t) for t in a.trials.split(',')]:
                t0 = time.time()
                ok_all, nterms, err = True, 0, ''
                for k in range(min(a.circuits, len(deltas))):
                    d = deltas[k]
                    C = tensorqrom.anf_tensor(d, brot, 4)
                    try:
                        terms = tensorqrom.shared(C, list(sizes), transpose=True, trials=trials,
                                                  seed=k,
                                                  groups=tensorqrom.low_groups(4) if a.groups else None)
                    except Exception as e:
                        ok_all, err = False, f'{type(e).__name__}: {e}'
                        break
                    mixed = tensorqrom.mixed_of(terms, C.shape[0] - 1, C.shape[1] - 1, C.shape[2])
                    if not np.array_equal(mixed, C[1:, 1:]):
                        ok_all, err = False, 'cover FAIL'
                        break
                    nterms += len(terms)
                dt = time.time() - t0
                row = {'j': j, 'sizes': sizes, 'trials': trials, 'cover': ok_all,
                       'terms': nterms, 'sec': round(dt, 1), 'err': err}
                results.append(row)
                print(f'  sizes={str(sizes):<28} trials={trials:<4} cover={ok_all} '
                      f'terms={nterms:<5} {dt:>5.1f}s {err[:60]}', flush=True)
                if ok_all:
                    break   # first cover found for this partition family
            if any(r['j'] == j and r['sizes'] == sizes and r['cover'] for r in results):
                continue
        best = [r for r in results if r['j'] == j and r['cover']]
        if best:
            b = min(best, key=lambda r: (r['terms'], r['sec']))
            print(f'  --> J={j}: first covering partition {b["sizes"]} '
                  f'(trials={b["trials"]}, terms={b["terms"]})')
        else:
            print(f'  --> J={j}: NO covering partition found')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
