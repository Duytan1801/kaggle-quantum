#!/usr/bin/env python3
"""deadwrite.py — find "dead-write" Toffolis in a kickmix circuit (invsqrt / dqi).

Identity (verified against the official verifier's contract and kmsim's HMR semantics):

    HMR q b   ==   Hadamard + measure + reset:
                   random outcome m into bit b, global phase x (-1)^(m*v),
                   qubit q -> |0>, where v is q's value before the measurement.

So a Toffoli `CCX(a, b -> w)` whose target `w` is never read again (its only later
touch is that HMR) can be replaced by

    HMR(w) ; CZ(a, b) if b_m

because the original contributes the phase
    (-1)^(m*(v xor a.b)) = (-1)^(m*v) * (-1)^(m*a.b)
while the replacement contributes
    (-1)^(m*v)         * (-1)^(a.b)*[m=1] = (-1)^(m*v) * (-1)^(m*a.b)
— identical for every draw of the randomness, with one Toffoli less per shot.

Preconditions checked here (all necessary):
  * the CCX is unconditional (not inside a PUSH_CONDITION block, no own `if b`)
  * the only later touch of the target w is the HMR (nothing after it touches w)
  * the HMR is unconditional
  * the HMR's output bit is not read or written between the CCX and the HMR
  * the HMR's output bit is not written before the CCX (it must be a fresh bit)

For invsqrt each Toffoli removed is worth Q * 1 = 44 cost units => about +0.0055 GM.

Usage: deadwrite.py <circuit.kmx> [--ctx N] [--all]
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, '/tmp/opencode/recon/datasets/asteriospanoras_qcc-circuit-atlas/tools')
from qccscope import kmx  # noqa: E402

_N = {n: i for i, n in enumerate(kmx.OPS)}
CX, CCX, CSWAP, CZ, CCZ = _N['CX'], _N['CCX'], _N['CSWAP'], _N['CZ'], _N['CCZ']
X, Z, SWAP, ZPOW, HMR, R, NEG = _N['X'], _N['Z'], _N['SWAP'], _N['Z_POW'], _N['HMR'], _N['R'], _N['NEG']
BINV, BST0, BST1 = _N['BIT_INVERT'], _N['BIT_STORE0'], _N['BIT_STORE1']
PUSH, POP = _N['PUSH_CONDITION'], _N['POP_CONDITION']
TOUCH_ARITY = {CX: 2, CZ: 2, SWAP: 2, CCX: 3, CCZ: 3, CSWAP: 3, X: 1, Z: 1, ZPOW: 1, HMR: 1, R: 1, NEG: 1}


def fmt(k, c):
    o = kmx.OPS[c.op[k]]
    a, b, cc, bit, cond = int(c.a[k]), int(c.b[k]), int(c.c[k]), int(c.bit[k]), int(c.cond[k])
    if o in ('CX', 'CZ', 'CCX', 'CCZ', 'CSWAP', 'SWAP'):
        s = f'{o}({a},{b},{cc})'
    elif o in ('X', 'Z', 'HMR', 'R', 'Z_POW', 'NEG'):
        s = f'{o}({a}) bit{bit}'
    elif o in ('BIT_INVERT', 'BIT_STORE0', 'BIT_STORE1'):
        s = f'{o}(bit{bit})'
    elif o in ('PUSH_CONDITION', 'POP_CONDITION'):
        s = f'{o}(cond{cond}) bit{bit}'
    else:
        s = f'{o}(a={a},b={b},c={cc},bit={bit},cond={cond})'
    if cond >= 0:
        s += f'  if b{cond}'
    if c.depth[k] > 0:
        s += f'  [depth {c.depth[k]}]'
    return s


def wires_of(c, k):
    o = int(c.op[k])
    ar = TOUCH_ARITY.get(o)
    if ar is None:
        return []
    out = []
    for arr in (c.a, c.b, c.c)[:ar]:
        w = int(arr[k])
        if w >= 0:
            out.append(w)
    return out


def main():
    path = sys.argv[1]
    ctx = 8
    if '--ctx' in sys.argv:
        ctx = int(sys.argv[sys.argv.index('--ctx') + 1])
    show_all = '--all' in sys.argv
    c = kmx.load(path)
    OP, A, B, Cc, BIT, COND, DEPTH = c.op, c.a, c.b, c.c, c.bit, c.cond, c.depth
    n = len(OP)
    nq = c.num_qubits
    touches = {q: [] for q in range(nq)}
    bit_writes = {}   # bit -> [op indices that write it]
    bit_reads = {}    # bit -> [op indices that read it as a condition]
    for k in range(n):
        o = int(OP[k])
        for w in wires_of(c, k):
            touches[w].append(k)
        if o == HMR:
            bit_writes.setdefault(int(BIT[k]), []).append(k)
        elif o in (BINV, BST0, BST1):
            bit_writes.setdefault(int(BIT[k]), []).append(k)
        elif o == PUSH:
            bit_reads.setdefault(int(COND[k]), []).append(k)
        if int(COND[k]) >= 0:
            bit_reads.setdefault(int(COND[k]), []).append(k)

    cands = []
    for k in range(n):
        if int(OP[k]) != CCX:
            continue
        if DEPTH[k] > 0 or COND[k] >= 0:
            continue          # conditional CCX: the fix would need nested conditions
        w = int(Cc[k])
        later = [t for t in touches[w] if t > k]
        if not later:
            continue
        j = later[0]
        if int(OP[j]) != HMR or int(A[j]) != w:
            continue
        if any(t > j for t in touches[w]):
            continue                      # wire used again after the measurement
        if DEPTH[j] > 0 or COND[j] >= 0:
            continue                      # conditional HMR: cannot move it
        mbit = int(BIT[j])
        if any(k < t < j for t in bit_writes.get(mbit, [])):
            continue                      # the bit is written in between
        if any(k < t < j for t in bit_reads.get(mbit, [])):
            continue                      # the bit is read in between
        if bit_writes.get(mbit) and min(bit_writes[mbit]) < k:
            continue                      # the bit is not fresh
        cands.append((k, j, w, int(A[k]), int(B[k]), mbit))

    print(f'file: {path}  qubits {nq}  ops {n}')
    print(f'  dead-write CCX candidates (unconditional, target only ever measured): {len(cands)}')
    for (k, j, w, a, b, mbit) in cands[:60]:
        print(f'--- CCX op {k}: CCX({a},{b}->{w})   next use: HMR op {j} (bit {mbit})')
        if show_all:
            for t in range(max(0, k - ctx), min(n, j + ctx + 1)):
                mark = '>>' if t in (k, j) else '  '
                print(f'   {mark} {t:6d} {fmt(t, c)}')
    return cands


if __name__ == '__main__':
    main()
