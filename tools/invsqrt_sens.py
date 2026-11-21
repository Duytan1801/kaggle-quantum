#!/usr/bin/env python3
"""invsqrt_sens.py — extract the invsqrt circuit's phase SENSE matrix.

WHAT THIS EXTRACTS
    The invsqrt phase is

        theta(x) = sum_k u_k * v_k(x) + sign(x)      (mod 2^64 units of 2^-64 turns)

    where u_k is the angle of Z_POW gate k (in units of 2^-64 turns) and
    v_k(x) in {0,1} is the indicator "rotation k fires on input x".  `sign(x)`
    is the pi-phase bookkeeping contributed by Z / CZ / CCZ / NEG / HMR
    kickback.

    `v_k` and `sign` do NOT depend on the angles, so one instrumented
    simulation of the circuit yields the COMPLETE linear model of the phase.
    From then on the angles can be optimised offline (milliseconds per
    iteration) instead of re-simulating the 60k-op circuit every time.

DETERMINISM CHECK
    The official verifier runs 64 random shots per x and checks EVERY shot.
    The phase must therefore be independent of the measurement outcomes, or
    the fit would be overfitted to one draw.  This tool simulates with two
    different outcome streams and compares v_k and sign bit-for-bit.

OUTPUT (.npz)
    V       (n_rot, MAX_X) bool   indicator matrix of the Z_POW gates
    sign    (MAX_X,) uint64       0 or 2^63 (the pi-phase part)
    units   (n_rot,) uint64       current angle of each Z_POW (units of 2^-64 turns)
    texts   (n_rot,) str          current KMX exponent text (half turns)
    err     (MAX_X,) int64        signed phase error of the current circuit
    tol     (MAX_X,) uint64       official tolerance (units of 2^-64 turns)
    target  (MAX_X,) uint64       official target (units of 2^-64 turns)
    rot_idx (n_rot,) int64        index of each rotation in the op list

Usage:
    python invsqrt_sens.py <circuit.kmx> <out.npz> [--seed 1]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kmxsim as K  # noqa: E402

MASK64 = (1 << 64) - 1


class RecordingSim(K.Sim):
    """Simulator that records the execution indicator of every Z_POW gate."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.records: list[np.ndarray] = []

    def apply(self, op):
        if op.name == 'Z_POW':
            m = self.mask(op.cond)
            t = self.Q[op.q[0]] if m is None else (self.Q[op.q[0]] & m)
            self.records.append(K.unpack(t).copy())
        return super().apply(op)


def run(ops, xreg, seed=1):
    nq = K.num_wires(ops)
    sim = RecordingSim(nq, 'rand', seed)
    sim.load_x(xreg)
    sim.run(ops)
    return sim


def main() -> None:
    path = pathlib.Path(sys.argv[1]).resolve()
    out = pathlib.Path(sys.argv[2])
    seed = 1
    if '--seed' in sys.argv:
        seed = int(sys.argv[sys.argv.index('--seed') + 1])

    ops, xreg = K.parse_kmx(path)
    ridx = [i for i, op in enumerate(ops) if op.name == 'Z_POW']
    print(f'{path}: {len(ops)} ops, {len(ridx)} Z_POW, {K.num_wires(ops)} wires')

    sim = run(ops, xreg, seed)
    V = np.stack([r[:K.MAX_X] for r in sim.records]) if sim.records else np.zeros((0, K.MAX_X), bool)
    sign = (K.unpack(sim.sign)[:K.MAX_X].astype(np.uint64) << np.uint64(63))

    # --- determinism: a second, independent outcome stream must give the same
    # indicator matrix and the same pi-phase bookkeeping.
    sim2 = run(ops, xreg, seed + 1000)
    V2 = np.stack([r[:K.MAX_X] for r in sim2.records])
    sign2 = (K.unpack(sim2.sign)[:K.MAX_X].astype(np.uint64) << np.uint64(63))
    same_V = bool(np.array_equal(V, V2))
    same_sign = bool(np.array_equal(sign, sign2))
    print(f'determinism: indicator matrix identical = {same_V}; pi-phase identical = {same_sign}')
    if not same_sign:
        n = int((sign != sign2).sum())
        print(f'   !! pi-phase differs on {n} inputs -> the fit is outcome-dependent; be careful')

    target, tol = K.reference()
    units = np.array([ops[i].units for i in ridx], dtype=np.uint64)
    texts = np.array([ops[i].expo for i in ridx])

    # current phase error, exactly as the official verifier computes it
    theta = (sim.phase[:K.MAX_X] + sign).astype(np.uint64)
    err = (theta - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    ratio = used.astype(np.float64) / tol.astype(np.float64)
    margin = tol.astype(np.int64) - err.astype(np.int64)
    print(f'current: max ratio {ratio.max():.9f} at x={int(np.argmax(ratio)) + 1}, '
          f'min margin {int(margin.min())} units')

    np.savez_compressed(out, V=V, sign=sign, units=units, texts=texts, err=err,
                        tol=tol, target=target, rot_idx=np.array(ridx, dtype=np.int64),
                        same_V=same_V, same_sign=same_sign)
    print(f'wrote {out}  V={V.shape} ({V.nbytes / 1e6:.1f} MB uncompressed)')


if __name__ == '__main__':
    main()
