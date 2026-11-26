#!/usr/bin/env python3
"""chem_anf.py — analyse the chemistry loader delta functions.

For each batch k the ANGLE_k loader XORs the batch delta

    D_k(a) = words_k(a) XOR words_{k-1}(a)      (35 bits, 30 of them live)

into the word registers, for each of the 1,219 addresses a.  The cost of the
loader is the number of Toffolis in the circuit that realises D_k.

This tool reports, per batch, the algebraic structure of D_k over the 11
address bits, so we can see WHY five batches cost 240-245 Toffolis while the
other ten cost 205-215.

Reported per batch:
  * the live-bit Hamming weight of D_k (how many of the 30 outputs actually
    change at all),
  * the ANF monomial census (how many monomials of each degree appear in the
    30 output functions), over the 11 address variables,
  * the number of *distinct* monomials shared by several outputs (a shared
    monomial costs ONE Toffoli for all its outputs, which is exactly why the
    goodpjw plan format is so cheap),
  * the same census restricted to the 7 bank bits and to the 4 low bits.

Usage: chem_anf.py <submission.npz> [--per-batch]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

NV = 1219
ADDR = np.arange(NV)
OUTS = [o for o in range(35) if o % 7 != 6]
NADDR = 11                      # address bits: 0-3 low, 4-10 bank


def word_bits(W, k):
    if k < 0:
        return np.zeros((35, NV), bool)
    return np.stack([((W[:, 5 * k + j] >> i) & 1).astype(bool)
                     for j in range(5) for i in range(7)])


def anf_monomials(f: np.ndarray):
    """Möbius transform of truth tables over n vars -> boolean mask of monomials.

    f: (nfun, 2**nvars) bool.  Returns (nfun, 2**nvars) bool: entry [g, x] is
    the coefficient of the monomial given by x in output function g.
    """
    nvars = f.shape[1].bit_length() - 1
    g = f.astype(np.uint8).copy()
    for i in range(nvars):
        bit = 1 << i
        g[:, bit:2 * bit] ^= g[:, :bit]
    return g.astype(bool)


def monomial_sets(f: np.ndarray):
    """-> list of frozensets: the ANF support of each of the n output functions."""
    g = anf_monomials(f)
    nvars = f.shape[1].bit_length() - 1
    out = []
    for i in range(f.shape[0]):
        s = set()
        for x in np.nonzero(g[i])[0]:
            s.add(frozenset(np.nonzero([(x >> j) & 1 for j in range(nvars)])[0].tolist()))
        out.append(frozenset(s))
    return out


def main() -> int:
    path = pathlib.Path(sys.argv[1]).resolve()
    z = np.load(path)
    W = z['angle_words']
    print(f'{path}  angle_words shape {W.shape} dtype {W.dtype}')
    print(f'NV={NV}  live outputs={len(OUTS)}  address bits={NADDR}')

    # truth table of the 11 address variables over the 1,219 addresses
    vars_ = np.stack([((ADDR >> i) & 1).astype(bool) for i in range(NADDR)])
    # expand to the full 2**11 cube, marking the 1,219 used addresses
    full = np.zeros((NADDR, 1 << NADDR), bool)
    used = np.zeros(1 << NADDR, bool)
    for a in range(NV):
        full[:, a] = vars_[:, a]
        used[a] = True

    rows = []
    for k in range(15):
        wk = word_bits(W, k)
        wprev = word_bits(W, k - 1)
        d = wk ^ wprev
        live = d[OUTS]
        # the five dead word bits (o % 7 == 6) must be identical in consecutive
        # batches: the loader does not write them.
        dead = [o for o in range(35) if o % 7 == 6]
        dead_same = all(np.array_equal(wk[o], wprev[o]) for o in dead)

        # ANF per live output (restricted to the used addresses; the transform
        # needs the full cube, so fill the unused addresses with 0)
        f = np.zeros((len(OUTS), 1 << NADDR), bool)
        for j in range(len(OUTS)):
            f[j, :NV] = live[j]
        ms = monomial_sets(f)

        deg = {}
        for m in ms:
            for mono in m:
                deg[len(mono)] = deg.get(len(mono), 0) + 1
        # shared monomials: a monomial in >=2 outputs costs one Toffoli total
        cnt = {}
        for m in ms:
            for mono in m:
                cnt[mono] = cnt.get(mono, 0) + 1
        shared = sum(1 for v in cnt.values() if v >= 2)
        total_mono = sum(len(m) for m in ms)
        weight = int(live.sum())

        # bank-only / low-only monomials
        bank_only = sum(1 for mono in cnt if all(b >= 4 for b in mono))
        low_only = sum(1 for mono in cnt if all(b < 4 for b in mono))

        rows.append(dict(k=k, weight=weight, total_mono=total_mono,
                         shared=shared, distinct=len(cnt), deg=deg,
                         bank_only=bank_only, low_only=low_only,
                         dead_same=dead_same))

    print()
    hdr = (f'{"k":>3s} {"liveWt":>7s} {"monos":>7s} {"distinct":>9s} {"shared":>7s} '
           f'{"bankOnly":>9s} {"lowOnly":>7s}  degrees')
    print(hdr)
    for r in rows:
        dd = ','.join(f'{k}:{v}' for k, v in sorted(r['deg'].items()))
        print(f'{r["k"]:3d} {r["weight"]:7d} {r["total_mono"]:7d} {r["distinct"]:9d} '
              f'{r["shared"]:7d} {r["bank_only"]:9d} {r["low_only"]:7d}  {dd}')

    print()
    print('dead bits (o%7==6) identical in consecutive batches: '
          f'{all(r["dead_same"] for r in rows)}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
