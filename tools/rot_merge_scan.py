#!/usr/bin/env python3
"""rot_merge_scan.py — refined search for MERGEABLE rotation pairs (same wire).

WHY THIS MATTERS
    The invsqrt cost is

        score = Q * (toffoli_count + t_base/4 + n_rot * rot_t(eps) / 4),
        rot_t(eps) = 0.56 * log2(1/eps) + 5.3,  eps = pi * min_margin / 2^64 / n_rot

so `n_rot` (the number of Z_POW gates that are NOT at Clifford hierarchy level
<= 4) is priced TWICE: once directly, and once through eps (fewer rotations ->
each rotation gets a bigger eps -> cheaper synthesis).  At the v136 operating
point one removed rotation is worth ~+0.0487 GM.

    A rotation pair on the SAME wire can be merged into a single Z_POW with the
    summed angle without changing the phase at all (Z is diagonal), as long as
    the phase bookkeeping between them is untouched.

BLOCKERS between two Z_POWs on wire w (the refined rule):
    * another Z_POW on w            (it is part of the chain, not a blocker)
    * CZ involving w                (adds a value-dependent phase to w)
    * SWAP involving w              (moves w's phase to another wire)
    * HMR / R on w                  (measurement or reset destroys the phase)
    * a different PUSH_CONDITION stack (the two rotations live in different
      classical branches)

NOT blockers: X, CX, CCX, CSWAP, CZ on other wires, NEG (a global phase, which
commutes with every Z_POW), and any gate that only changes w's VALUE (X, CX
with w as target, CCX with w as target) — Z is diagonal, so the phase of w is
independent of its value.

Angles are exact multiples of 2^-64 turns in these circuits, so the merged sum
is phase-exact (the simulator tracks phase in uint64 mod 2^64).

Usage:  rot_merge_scan.py <circuit.kmx> [--counted-only]
"""
from __future__ import annotations

import collections
import re
import sys
from fractions import Fraction

ZPOW_RE = re.compile(r'^Z_POW q(\d+) (\S+)$')
OP_RE = re.compile(r'^([A-Z_0-9]+)(?:\s+(.*))?$')
Q_RE = re.compile(r'q(\d+)')
B_RE = re.compile(r'b(\d+)')


def classify(line: str):
    """-> (kind, qargs, bargs, angle) for a KMX gate line."""
    m = ZPOW_RE.match(line)
    if m:
        return 'ZPOW', [int(m.group(1))], [], m.group(2)
    m = OP_RE.match(line)
    if not m:
        return None, [], [], None
    kind = m.group(1)
    rest = m.group(2) or ''
    return kind, [int(x) for x in Q_RE.findall(rest)], B_RE.findall(rest), None


def main() -> None:
    path = sys.argv[1]
    lines = [l.strip() for l in open(path).read().splitlines() if l.strip()]
    cond_stack: list[str] = []
    cond_of: list[tuple[str, ...]] = []
    events = []            # (idx, kind, qargs, bargs, angle)
    for i, l in enumerate(lines):
        if l.startswith('PUSH_CONDITION'):
            cond_stack.append(l)
            cond_of.append(tuple(cond_stack))
            continue
        if l.startswith('POP_CONDITION'):
            if cond_stack:
                cond_stack.pop()
            cond_of.append(tuple(cond_stack))
            continue
        cond_of.append(tuple(cond_stack))
        kind, qa, ba, ang = classify(l)
        if kind is None:
            continue
        events.append((i, kind, qa, ba, ang))

    # ---- PHASE / VALUE BLOCKERS -------------------------------------------------
    # Two Z_POWs on the same wire w can be merged into one Z_POW(w, a1+a2) at the
    # position of the FIRST one only if Z_POW(w, a2) COMMUTES with every gate in
    # between.  Z_POW is diagonal, so it commutes with
    #   * every diagonal gate (Z, CZ, CCZ) on w,
    #   * every gate that does not touch w,
    #   * every gate that touches w only as a CONTROL (X/CX/CCX leave the
    #     control's value unchanged, so Z on the control commutes).
    # It does NOT commute with a gate that acts NON-DIAGONALLY on w:
    #   X w, CX ... w (w is the target), CCX ... w (w is the target),
    #   SWAP/CSWAP involving w, H w, HMR w, R w.
    # (A CZ on w is diagonal and commutes, but it ADDS its own phase, which is
    # unaffected by the merge, so it is not a blocker.)
    NONDIAG_TARGET = {'X': 1, 'CX': 1, 'CCX': 1}          # last q arg is the target
    NONDIAG_ALL = {'SWAP', 'CSWAP', 'HMR', 'H', 'R', 'RESET', 'CLEAR'}

    def blocks(kind: str, qa: list[int], w: int) -> bool:
        if kind in NONDIAG_ALL:
            return w in qa
        if kind in NONDIAG_TARGET and qa:
            return qa[-1] == w
        return False

    blockers: dict[int, list[tuple[int, bool]]] = collections.defaultdict(list)
    rotations: dict[int, list[tuple[int, str]]] = collections.defaultdict(list)
    for ei, (i, kind, qa, ba, ang) in enumerate(events):
        if kind == 'ZPOW':
            rotations[qa[0]].append((ei, ang))
            continue
        for w in qa:
            blockers[w].append((ei, blocks(kind, qa, w)))

    def is_counted(angle: str) -> bool:
        """A Z_POW is PRICED (counted as a rotation) iff its angle is not a
        multiple of 1/16 turns (Clifford hierarchy level <= 4 is free)."""
        f = Fraction(angle)
        return (f * 16).denominator != 1

    # maximal chains of rotations per wire
    groups = []
    total_pairs = 0
    for w, rots in sorted(rotations.items()):
        if len(rots) < 2:
            continue
        bl = blockers.get(w, [])
        chain = [rots[0]]
        for (e1, a1), (e2, a2) in zip(rots, rots[1:]):
            between = [(e, blocking) for e, blocking in bl if e1 < e < e2]
            blocked = any(blocking for _, blocking in between)
            same_ctx = cond_of[events[e1][0]] == cond_of[events[e2][0]]
            if blocked or not same_ctx:
                if len(chain) >= 2:
                    groups.append((w, list(chain)))
                chain = [(e2, a2)]
                if blocked or not same_ctx:
                    total_pairs += 0
            else:
                chain.append((e2, a2))
                total_pairs += 1
        if len(chain) >= 2:
            groups.append((w, list(chain)))

    print(f'== {path}')
    print(f'   wires with rotations: {len(rotations)}   rotation gates: {sum(len(v) for v in rotations.values())}')
    counted_total = sum(1 for w in rotations for e, a in rotations[w] if is_counted(a))
    print(f'   priced rotations (level > 4): {counted_total}')
    print(f'   mergeable adjacent pairs: {total_pairs}   merge groups: {len(groups)}')

    n_rot_before = counted_total
    n_rot_after = counted_total
    for w, chain in groups:
        ang = sum((Fraction(a) for e, a in chain), Fraction(0))
        counted_in_group = sum(1 for e, a in chain if is_counted(a))
        after = 0 if (ang * 16).denominator == 1 else 1
        n_rot_after -= counted_in_group - after
        exact = 'EXACT-2^-64' if (ang * 2 ** 64).denominator == 1 else 'NOT-binary-exact'
        level = '-> CLIFFORD(free)' if (ang * 16).denominator == 1 else '-> priced'
        print(f'   q{w:<3} n={len(chain):<2} lines {events[chain[0][0]][0]:>6}..{events[chain[-1][0]][0]:>6}'
              f'  sum={float(ang):.18g}  {exact} {level}  counted_in_group={counted_in_group}'
              f'  n_rot {counted_in_group} -> {after}')
    print(f'\n   projected n_rot: {n_rot_before} -> {n_rot_after}  '
          f'(saves {n_rot_before - n_rot_after} rotations)')
    for k in range(n_rot_before - n_rot_after):
        print(f'     rotation {k+1}: ~+0.0487 GM (and a bit more through the eps term)')


if __name__ == '__main__':
    main()
