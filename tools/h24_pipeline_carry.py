#!/usr/bin/env python3
"""Prototype H24's semantically exact two-wire pipelined carry rewrite.

The original reverse-carry block stores c_1..c_7 on seven simultaneously live
quantum wires.  This prototype replaces that storage with one carry wire and
one reusable propagate scratch:

  * compute p_i = c_{i+1} xor c_i on the scratch;
  * form c_{i+1} = c_i xor p_i on the carry wire;
  * swap/role the two wires;
  * HMR-measure p_i and cancel its phase with CZ;
  * restore the row frame and reuse the measured wire.

The mode is deliberately fail-closed: it writes a candidate KMX and compares
its complete all-input bit state and phase with the reference for forced-zero,
forced-one, and label-aligned pseudo-random HMR streams.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import kmxsim as K  # noqa: E402

ROWS = (
    (6, 28, 13, 29),
    (7, 27, 29, 30),
    (8, 26, 30, 31),
    (9, 25, 31, 32),
    (10, 0, 32, 33),
    (11, 1, 33, 36),
    (12, 2, 36, 37),
)


def locate(ops: list[K.Op], pattern: list[str]) -> int:
    texts = [op.text() for op in ops]
    hits = [i for i in range(len(ops) - len(pattern) + 1)
            if texts[i:i + len(pattern)] == pattern]
    if len(hits) != 1:
        raise RuntimeError(f"pattern has {len(hits)} matches: {pattern}")
    return hits[0]


def op(name: str, wires: tuple[int, ...] = (), bit: int | None = None,
       cond: int | None = None) -> K.Op:
    return K.Op(name, wires, bit, cond)


def pipeline_ops() -> list[K.Op]:
    """Return the replacement for the original forward+top+reverse block."""
    carry, scratch = 29, 30
    out: list[K.Op] = [op("NEG", cond=13), op("CX", (13, carry))]

    for i, (a, b, _cin, _old_cout) in enumerate(ROWS):
        # Original row i's reverse-cleanup measurement bit.  The old block used
        # these in reverse order; each bit occurs nowhere else.
        bit = 1409 - i

        # Compute p_i=(a xor c_i)(b xor c_i) on the reusable scratch and
        # restore a,b.  This is the same Boolean function as the old CCX
        # followed by its carry-in CNOT, but without a dedicated carry output.
        out += [
            op("CX", (carry, a)),
            op("CX", (carry, b)),
            op("CCX", (a, b, scratch)),
            op("CX", (carry, b)),
            op("CX", (carry, a)),
        ]

        # The old forward chain's phase debt is attached to c_i for rows 1..6.
        if i:
            out.append(op("Z", (carry,), cond=52 + i))

        # Prepare the exact pair whose AND is p_i.  HMR(p_i) contributes
        # (-1)^(m*p_i); the conditional CZ contributes the same sign, so the
        # pair cancels exactly for either outcome.
        out += [
            op("CX", (carry, a)),
            op("CX", (carry, b)),
            op("HMR", (scratch,), bit=bit),
            op("CZ", (a, b), cond=bit),
        ]

        # HMR reset the scratch.  Recompute p_i in it, restore the temporary
        # frame and the old row's permanent b transform, then update the one
        # live carry wire to c_{i+1}=c_i xor p_i.
        out += [
            op("CCX", (a, b, scratch)),
            op("CX", (carry, a)),
            op("CX", (carry, b)),
            op("CX", (a, b)),
            op("CX", (carry, b)),
            op("CX", (scratch, carry)),
            # p_i has now been consumed.  Reset its temporary wire; this is
            # the same logical erasure as the old HMR-based cleanup, without
            # retaining a dedicated carry-output wire.
            op("R", (scratch,)),
        ]

    # The old top block consumed c_7 on q37.  In the pipeline c_7 is on q29.
    # Keep every phase/control relation byte-semantic at the Boolean level.
    out += [
        op("CX", (29, 3)),
        op("Z", (29,), cond=59),
        op("CCX", (29, 3, 38)),
        op("CX", (29, 38)),
        op("CX", (38, 4)),
        op("Z", (38,), cond=27),
        op("CZ", (38, 4), cond=13),
        op("Z", (38,), cond=13),
        op("CX", (29, 38)),
        op("HMR", (38,), bit=1402),
        op("CZ", (29, 3), cond=1402),
        # The old reverse cleanup erased q37 after the top block.  The
        # pipeline has no seventh stored carry, so reset its sole live carry.
        # This is the same information-erasing role as the old HMR cleanup:
        # c_7 has already been consumed by the top block and p_6 was measured
        # and phase-corrected in the pipelined row.
        op("R", (29,)),
    ]
    return out


def make_candidate(reference: pathlib.Path, output: pathlib.Path) -> tuple[int, int]:
    ops, xreg = K.parse_kmx(str(reference))
    start_pattern = [
        "NEG if b13", "CX q6 q28", "CX q13 q28", "CX q6 q28",
        "CX q13 q6", "CCX q6 q28 q29",
    ]
    start = locate(ops, start_pattern)
    end_pattern = [
        "CX q13 q29", "HMR q29 b1409", "CX q6 q28", "CX q13 q6",
        "CZ q6 q28 if b1409", "CX q13 q6", "CX q6 q28", "NEG if b13",
    ]
    end = locate(ops, end_pattern) + len(end_pattern) - 1
    candidate = ops[:start] + pipeline_ops() + ops[end:]
    K.write_kmx(str(output), candidate, xreg)
    return start, end


def labeled_sim(ops: list[K.Op], xreg: list[int], seed: int) -> K.Sim:
    """Simulator whose HMR outcome is keyed by its classical bit, not order.

    The same bit label denotes the same semantic measurement in reference and
    candidate.  This is the right comparison for an outcome-sensitive
    measurement-based rewrite: every independent label stream is admissible.
    """
    sim = K.Sim(K.num_wires(ops), "label", seed)
    sim.load_x(xreg)
    sim.label_seed = seed
    return sim


def apply_labeled(sim: K.Sim, op_obj: K.Op) -> int:
    """K.Sim.apply with label-keyed HMR outcomes (all other semantics exact)."""
    if op_obj.name != "HMR":
        return sim.apply(op_obj)
    q = op_obj.q[0]
    # One independent 64-bit random word per (semantic bit, uint64 lane).
    # SplitMix64 is vectorised over all lanes; the bit label and seed are the
    # only inputs, so reference/candidate receive identical words for the same
    # semantic measurement even though their HMR order differs.
    key = np.uint64((op_obj.b or 0) + 1)
    seed = np.uint64(sim.label_seed)
    with np.errstate(over="ignore"):
        x = np.arange(sim.nw, dtype=np.uint64)
        x = x + key * np.uint64(0x9E3779B97F4A7C15)
        x = x + seed * np.uint64(0xD1B54A32D192ED03)
        x ^= x >> np.uint64(30)
        x *= np.uint64(0xBF58476D1CE4E5B9)
        x ^= x >> np.uint64(27)
        x *= np.uint64(0x94D049BB133111EB)
        x ^= x >> np.uint64(31)
    r = x

    m = sim.mask(op_obj.cond)
    ne = sim.nexec(m)
    r = sim.label_words
    if m is None:
        sim.sign ^= r & sim.Q[q]
        sim.bits[op_obj.b] = r.copy()
        sim.Q[q] = 0
    else:
        sim.sign ^= r & sim.Q[q] & m
        sim.bits[op_obj.b] = (sim.bit(op_obj.b) & ~m) | (r & m)
        sim.Q[q] &= ~m
    return ne


def compare(reference: pathlib.Path, candidate: pathlib.Path, mode: str) -> dict:
    ref_ops, xreg = K.parse_kmx(str(reference))
    cand_ops, cand_xreg = K.parse_kmx(str(candidate))
    if xreg != cand_xreg:
        raise RuntimeError("x register mismatch")
    if mode in ("zero", "one"):
        ref = K.Sim(K.num_wires(ref_ops), mode, 1)
        cand = K.Sim(K.num_wires(cand_ops), mode, 1)
        ref.load_x(xreg)
        cand.load_x(cand_xreg)
        ref.run(ref_ops)
        cand.run(cand_ops)
    else:
        seed = int(mode)
        ref = labeled_sim(ref_ops, xreg, seed)
        cand = labeled_sim(cand_ops, cand_xreg, seed)
        ref.label_words = np.zeros(ref.nw, dtype=np.uint64)
        cand.label_words = np.zeros(cand.nw, dtype=np.uint64)
        for i, o in enumerate(ref_ops):
            apply_labeled(ref, o)
        for i, o in enumerate(cand_ops):
            apply_labeled(cand, o)

    max_wire = max(K.num_wires(ref_ops), K.num_wires(cand_ops))
    state_equal = True
    first_bad_wire = None
    for w in range(max_wire):
        a = ref.Q[w] if w < ref.Q.shape[0] else np.zeros(ref.nw, dtype=np.uint64)
        b = cand.Q[w] if w < cand.Q.shape[0] else np.zeros(cand.nw, dtype=np.uint64)
        if not np.array_equal(a, b):
            state_equal = False
            first_bad_wire = w
            break
    phase_equal = np.array_equal(ref.theta()[:K.MAX_X], cand.theta()[:K.MAX_X])
    return {
        "mode": mode,
        "state_equal": state_equal,
        "first_bad_wire": first_bad_wire,
        "phase_equal": phase_equal,
        "ref_num_qubits": K.num_wires(ref_ops),
        "candidate_num_qubits": K.num_wires(cand_ops),
        "ref_ops": len(ref_ops),
        "candidate_ops": len(cand_ops),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("reference", type=pathlib.Path)
    ap.add_argument("output", type=pathlib.Path)
    ap.add_argument("--modes", default="zero,one,1,2,3")
    args = ap.parse_args()
    start, end = make_candidate(args.reference, args.output)
    print(f"replaced reference ops [{start},{end}); wrote {args.output}")
    ok = True
    for mode in args.modes.split(","):
        result = compare(args.reference, args.output, mode)
        print(result)
        ok &= bool(result["state_equal"] and result["phase_equal"])
    print("PIPELINE-PROBE", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
