#!/usr/bin/env python3
"""invsqrt_basis_probe.py — enumerate salt-invariant scratch-wire basis functions.

H25 asks whether one additional priced Z_POW can enlarge the inverse-square-root
phase span enough to pay for itself.  A legal new rotation at an existing priced
rotation's position contributes the indicator of the value of the wire on which
it is placed.  This tool records every scratch-wire value immediately before
each *priced* rotation, over several independent HMR outcome streams.

Only functions whose complete bit-vector is identical in every outcome stream
are retained.  X-register bits are excluded: they were already tested by H26.
The output is a compact, deduplicated catalogue suitable for an offline LP.

Usage:
    python invsqrt_basis_probe.py <circuit.kmx> <out.npz> [--streams 4]
"""
from __future__ import annotations

import argparse
import hashlib
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kmxsim as K  # noqa: E402

MASK64 = (1 << 64) - 1


def zpow_class(units: int) -> str:
    u = int(units) & MASK64
    if u % (1 << 62) == 0:
        return "clifford"
    if u % (1 << 61) == 0:
        return "t"
    return "rotation"


def trim_last_word(plane: np.ndarray) -> np.ndarray:
    """Trim padding bits after MAX_X, retaining the packed uint64 layout."""
    out = plane.copy()
    rem = K.MAX_X % 64
    if rem:
        out[-1] &= np.uint64((1 << rem) - 1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("out")
    ap.add_argument("--streams", type=int, default=4)
    ap.add_argument("--include-forced", action="store_true",
                    help="also compare all-zero and all-one HMR outcome streams")
    args = ap.parse_args()

    path = pathlib.Path(args.circuit).resolve()
    out_path = pathlib.Path(args.out).resolve()
    ops, xreg = K.parse_kmx(path)
    nq = K.num_wires(ops)
    priced = [i for i, op in enumerate(ops)
              if op.name == "Z_POW" and zpow_class(op.units) == "rotation"]
    if not priced:
        raise SystemExit("no priced Z_POW gates")

    seeds = [1 + 1000 * k for k in range(args.streams)]
    modes = ["rand"] * args.streams
    if args.include_forced:
        modes += ["zero", "one"]
        seeds += [0, 0]
    sims = [K.Sim(nq, mode, seed) for mode, seed in zip(modes, seeds)]
    for sim in sims:
        sim.load_x(xreg)

    # A candidate is (priced-op index, scratch wire).  Deduplicate by the exact
    # packed value vector, but retain every occurrence as metadata.
    unique: dict[bytes, int] = {}
    bits: list[np.ndarray] = []
    occurrences: list[tuple[int, int]] = []
    priced_seen = 0
    stream_mismatches = 0

    for op_index, op in enumerate(ops):
        if op_index in priced:
            # Values are sampled before the rotation; Z_POW itself does not
            # change a wire's quantum value.
            for wire in range(22, nq):
                same = all(np.array_equal(sims[0].Q[wire], s.Q[wire])
                           for s in sims[1:])
                if not same:
                    stream_mismatches += 1
                    continue
                plane = trim_last_word(sims[0].Q[wire])
                key = plane.tobytes()
                idx = unique.get(key)
                if idx is None:
                    idx = len(bits)
                    unique[key] = idx
                    bits.append(plane)
                occurrences.append((op_index, wire, idx))
            priced_seen += 1
        for sim in sims:
            sim.apply(op)

    if len(bits) != len(unique):
        raise AssertionError("deduplication accounting mismatch")
    bit_matrix = np.stack(bits) if bits else np.zeros((0, K.NPAD // 64), np.uint64)
    occ = np.asarray(occurrences, dtype=np.int64)

    # Scalar frequency metadata is useful for quickly rejecting near-trivial
    # candidates without unpacking every vector.
    frequencies = np.asarray([int(np.bitwise_count(row).sum())
                               for row in bit_matrix], dtype=np.int64)

    np.savez(
        out_path,
        bits=bit_matrix,
        occurrences=occ,
        frequencies=frequencies,
        priced_ops=np.asarray(priced, dtype=np.int64),
        nq=np.asarray([nq], dtype=np.int64),
        seeds=np.asarray(seeds, dtype=np.int64),
        modes=np.asarray(modes),
        stream_mismatches=np.asarray([stream_mismatches], dtype=np.int64),
    )
    print(f"{path}: {len(ops)} ops, {nq} wires, {len(priced)} priced rotations")
    print(f"retained {len(occ)} salt-invariant occurrences -> "
          f"{len(bits)} unique functions ({stream_mismatches} stream mismatches)")
    if len(bits):
        print("frequency range:",
              int(frequencies.min()), "..", int(frequencies.max()),
              f"(MAX_X={K.MAX_X})")
    print(f"wrote {out_path} ({out_path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
