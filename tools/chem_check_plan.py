#!/usr/bin/env python3
"""chem_check_plan.py — verify a candidate chemistry plan against its batch.

This is the acceptance test for any plan the H42 search produces.  Given a
plan (the dict `chem_plan.decode_plans()` returns) and a batch k it

  1. emits the loader circuit with the validated emitter (`chem_plan`),
  2. simulates the circuit EXACTLY on all 1,219 addresses (every qubit is
     tracked as a boolean function of the address -- no shots),
  3. checks that the word registers move by exactly the batch delta
     D_k = words_k XOR words_{k-1},
  4. checks the reverse pass clears the registers (the circuit is its own
     inverse, which the official verifier requires), and
  5. reports the Toffoli count and the cost in T.

The incoming state is words_{k-1}; for k = 0 it is zero, and in that case the
QUADS features are INVALID (the relation word[7j+6] XOR word[7j+5] ==
QUADS(j) does not hold for the zero state), so a k = 0 plan must not use the
feature indices 12..16 -- the checker enforces that.

Usage:
    chem_check_plan.py --batch K [--plan-file FILE] [--tree v149]

`--plan-file` reads a Python literal plan dict (as produced by
`chem_plan.decode_plans()`); without it the public plan of that batch (if
any) is checked, which is the known-answer control.
"""
from __future__ import annotations

import ast
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402

ADDR = CP.ADDR
NV = CP.NV
QUADS_IDX = set(range(12, 17))


def cellvec(f):
    v = np.zeros(1232, bool)
    v[(ADDR >> 4) * 16 + (ADDR & 15)] = f
    return v


def simulate(ops, sel, wq, zin, keep_all=False):
    """-> the word register values after the circuit (35 x 1219 bool)

    `keep_all=True` returns the full qubit state (for the workspace check).
    """
    nq = 1 + max(max(t[1:]) for t in ops)
    S = np.zeros((nq, NV), bool)
    S[wq] = zin
    for i, q in enumerate(sel):
        S[q] = ((ADDR >> i) & 1).astype(bool)
    for t in ops:
        if t[0] == 'CX':
            S[t[2]] ^= S[t[1]]
        elif t[0] == 'X':
            S[t[1]] ^= True
        elif t[0] == 'CCX':
            S[t[3]] ^= S[t[1]] & S[t[2]]
        elif t[0] == 'HMR':
            S[t[1]] = False
        elif t[0] == 'Z':
            S[t[1]] = False
        elif t[0] == 'CZ':
            pass                       # phase only: the values are unchanged
        else:
            raise AssertionError(t)
    return S if keep_all else S[wq].copy()


def check(P, k, tree='v149', npz=None, verbose=True):
    npz = pathlib.Path(npz) if npz else ROOT / f'work/trees/{tree}/dfthcsos/submission.npz'
    z = np.load(npz)
    W = z['angle_words']
    ref = ROOT / f'work/trees/{tree}/dfthcsos' / f'angle_k_{k}.kmb'
    hdr, pops, sel, wq = CP.read_loader(str(ref))

    # the plan must not use the QUADS features when they are invalid
    if k == 0:
        for name in ('U', 'V', 'R'):
            M = P[name]
            used = set(np.nonzero(M)[1].tolist())
            bad = used & QUADS_IDX
            if bad:
                return False, f'k=0 plan uses the invalid QUADS features {sorted(bad)}'

    ops = CP.build_loader(P, sel, wq)
    ntof = sum(1 for t in ops if t[0] == 'CCX')

    zin = CP.word_bits(W, k - 1)
    zout = simulate(ops, sel, wq, zin)
    want = CP.word_bits(W, k)

    # ---- the oracle contract -------------------------------------------
    # The loader is the XOR oracle |a>|z> -> |a>|z XOR f_k(a)>, so it is
    # self-inverse on the word registers: applying it AGAIN undoes it.
    # (Running the op list backwards would be wrong -- the list ends with
    # the uncompute section, whose inverse is not the list itself.)
    back = simulate(ops, sel, wq, zout)
    ok_rev = np.array_equal(back, zin)

    # all 35 word bits must match, not just the 30 live outputs
    ok_fwd = np.array_equal(zout, want)
    bad = [i for i in range(35) if not np.array_equal(zout[i], want[i])]
    badlive = [i for i in range(30) if not np.array_equal(zout[CP.OUTS[i]], want[CP.OUTS[i]])]

    # workspace qubits must return to |0>
    nq = 1 + max(max(t[1:]) for t in ops)
    full = simulate(ops, sel, wq, zin, keep_all=True)
    keep = set(sel) | set(wq)
    dirty = [q for q in range(nq) if q not in keep and full[q].any()]
    ok_clean = not dirty

    # phase: every CZ in this emitter is conditioned on the HMR outcome
    # (`CZ qa qb if b0`) and q = a AND b, so the phase cancels exactly.
    ncz = sum(1 for t in ops if t[0] == 'CZ')
    nhmr = sum(1 for t in ops if t[0] == 'HMR')

    if verbose:
        print(f'batch {k}: CCX={ntof}  forward-delta-ok={ok_fwd}  self-inverse={ok_rev}  '
              f'workspace-clean={ok_clean}  (CZ={ncz} HMR={nhmr})')
    if ok_fwd and ok_rev and ok_clean:
        return True, f'PASS  batch {k}: {ntof} Toffolis'
    if not ok_fwd:
        return False, (f'FAIL  batch {k}: delta wrong on {len(bad)} of 35 word bits '
                       f'(live outputs wrong: {len(badlive)} of 30; bits {bad[:8]})')
    if not ok_rev:
        return False, f'FAIL  batch {k}: the oracle is not self-inverse'
    return False, f'FAIL  batch {k}: workspace qubits {dirty[:8]} are not returned to |0>'


def main():
    args = sys.argv[1:]
    k = None
    plan_file = None
    tree = 'v149'
    i = 0
    while i < len(args):
        if args[i] == '--batch':
            k = int(args[i + 1])
            i += 2
        elif args[i] == '--plan-file':
            plan_file = args[i + 1]
            i += 2
        elif args[i] == '--tree':
            tree = args[i + 1]
            i += 2
        else:
            raise SystemExit(f'unknown argument {args[i]}')
    if k is None:
        raise SystemExit(__doc__)

    if plan_file:
        P = ast.literal_eval(pathlib.Path(plan_file).read_text())
        for key in ('U', 'V', 'M', 'R', 'B'):
            P[key] = np.asarray(P[key], dtype=np.uint8)
        P['ands'] = np.asarray(P['ands'], dtype=np.uint8)
    else:
        plans = CP.decode_plans()
        if k not in plans:
            raise SystemExit(f'no public plan for batch {k}; pass --plan-file')
        P = plans[k]

    ok, msg = check(P, k, tree=tree)
    print(msg)
    raise SystemExit(0 if ok else 1)


if __name__ == '__main__':
    raise SystemExit(main())
