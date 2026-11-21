#!/usr/bin/env python3
"""invsqrt_affine.py — find LENDABLE wires in an invsqrt circuit.

WHY
    The public invsqrt generator builds a 39 q circuit.  At 38 q it would score
    60,114 (GM 33.253) and at 37 q 58,532 (GM 33.5518) — the whole gap to the
    board.  The generator already ships one "lend": `carry.py` borrows q29 for
    the carry chain by XOR-ing out the affine function q29 holds
    (q5 ^ q7 ^ q9 ^ q10 ^ 1), using the wire as scratch, and XOR-ing it back
    after the last HMR.  A second lend would give the second qubit.

    A wire W can be lent iff, during some window, its value is an EXACT affine
    function of other wires that stay live across the window:

        Q[W] = XOR_{u in S} Q[u]  XOR  c        (c in {0,1})

    over ALL 3,133,452 inputs x (and, for salt-safety, over every measurement
    outcome stream).  This is a GF(2) linear-algebra question: the 39 wire
    bit-vectors (plus the all-ones vector for the constant) span a space, and
    every linear dependency is a lend candidate.

    The tool runs the exact bit-sliced simulator and, at sampled op indices,
    computes the GF(2) null space of the wire-value matrix.  A dependency
    {W} = {u1..uk} means W could be re-derived from the others at that point.

Usage:
    python invsqrt_affine.py <circuit.kmx> [--stride 100] [--out out.json]
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kmxsim as K  # noqa: E402

MASK64 = (1 << 64) - 1


def gf2_nullspace(planes: list[np.ndarray]) -> list[list[int]]:
    """Null space (over GF(2)) of the matrix whose COLUMNS are `planes`.

    Each plane is a packed uint64 array (bit i of word w = input 64w+i).
    Returns a list of dependency vectors: for each, the indices whose columns
    XOR to zero.  The basis is kept in reduced row-echelon form so that one
    pass over it clears every pivot bit.
    """
    n = len(planes)
    basis: list[list] = []   # [pivot_word, pivot_bit, vector, coeff_mask]
    deps: list[list[int]] = []
    for col in range(n):
        v = planes[col].copy()
        coeff = 1 << col
        for b in basis:
            if (int(v[b[0]]) >> b[1]) & 1:
                v ^= b[2]
                coeff ^= b[3]
        nz = np.flatnonzero(v)
        if len(nz) == 0:
            deps.append([i for i in range(n) if (coeff >> i) & 1])
            continue
        pw = int(nz[0])
        w = int(v[pw])
        pb = int((w & -w).bit_length() - 1)
        # keep the basis reduced: clear the new pivot in the existing rows
        for b in basis:
            if (int(b[2][pw]) >> pb) & 1:
                b[2] = b[2] ^ v
                b[3] ^= coeff
        basis.append([pw, pb, v, coeff])
        basis.sort(key=lambda t: (t[0], t[1]))
    return deps


def main() -> None:
    path = pathlib.Path(sys.argv[1]).resolve()
    stride = 100
    out_path = None
    start = 0
    stop = None
    args = sys.argv[2:]
    if '--stride' in args:
        stride = int(args[args.index('--stride') + 1])
    if '--start' in args:
        start = int(args[args.index('--start') + 1])
    if '--end' in args:
        stop = int(args[args.index('--end') + 1])
    if '--out' in args:
        out_path = pathlib.Path(args[args.index('--out') + 1])

    ops, xreg = K.parse_kmx(path)
    nq = K.num_wires(ops)
    nwords = (K.NPAD + 63) // 64
    ones = np.full(nwords, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
    ones[(K.NPAD % 64) // 8:] = 0 if (K.NPAD % 64) else ones[(K.NPAD % 64) // 8:]
    # mask off the padding bits of the constant vector
    pad = K.NPAD % 64
    if pad:
        ones[-1] &= np.uint64((1 << pad) - 1)

    sim = K.Sim(nq, 'rand', 1)
    sim.load_x(xreg)
    findings = []
    last_wires = None

    class Probe(K.Sim):
        pass

    for i, op in enumerate(ops):
        sim.apply(op)
        if i < start or (stop is not None and i >= stop):
            continue
        if (i - start) % stride:
            continue
        planes = [sim.Q[w].copy() for w in range(nq)] + [ones]
        deps = gf2_nullspace(planes)
        live = [w for w in range(nq) if sim.Q[w].any()]
        rec = {'op_index': i, 'op': op.text(), 'n_live': len(live),
               'dependencies': []}
        for dep in deps:
            if len(dep) <= 2:
                continue  # trivial: a wire equals the constant, or two wires equal
            rec['dependencies'].append(dep)
        if rec['dependencies']:
            findings.append(rec)
            print(f'op {i:>7} ({op.text()[:40]:<40}) live {len(live):>3}: '
                  f'{len(rec["dependencies"])} dependency sets', flush=True)
            for dep in rec['dependencies'][:8]:
                print(f'     {dep}', flush=True)
    print(f'\n{len(findings)} op indices with a non-trivial affine dependency '
          f'(stride {stride}, {len(ops)} ops)')
    if out_path:
        out_path.write_text(json.dumps(findings, indent=1))
        print(f'wrote {out_path}')


if __name__ == '__main__':
    main()
