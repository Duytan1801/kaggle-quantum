#!/usr/bin/env python3
"""dqi_equiv_check.py — fast QUANTUM EQUIVALENCE check for a .kmb rewrite.

Runs the UNCHANGED kickmix Simulator on two circuits with the SAME random
input registers and compares EVERY output qubit bit-by-bit, plus the phase.

This is the cheap local gate for a circuit rewrite (the full official DQI
verifier needs 102,400 shots and >3 GB for the GF(2) reference decoder, so it
only runs in moat-lab).  It needs no reference decoder at all: it just asks
"does the patched circuit compute the same permutation+phase as the original?".

Usage:
  dqi_equiv_check.py <a.kmb> <b.kmb> [--shots N] [--seed S] [--batch B]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
import kickmix as km  # noqa: E402


def registers(circuit):
    """returns (syndrome_qubits, mbuc_bits, all_qubits) for a DQI circuit"""
    regs = circuit.register_data
    s_names = sorted([n for n in regs if n.startswith('S') and n[1:].isdigit()],
                      key=lambda n: int(n[1:]))
    e_names = sorted([n for n in regs if n.startswith('E') and n[1:].isdigit()],
                      key=lambda n: int(n[1:]))
    s_q = []
    for n in s_names:
        s_q.extend([x for x in regs[n] if isinstance(x, km.q)])
    e_b = []
    for n in e_names:
        e_b.extend([x for x in regs[n] if isinstance(x, km.b)])
    allq = [km.q(k) for k in range(circuit.num_qubits)]
    return s_q, e_b, allq


def main() -> int:
    a = pathlib.Path(sys.argv[1])
    b = pathlib.Path(sys.argv[2])
    shots = 64
    seed = 12345
    batch = 64
    if '--shots' in sys.argv:
        shots = int(sys.argv[sys.argv.index('--shots') + 1])
    if '--seed' in sys.argv:
        seed = int(sys.argv[sys.argv.index('--seed') + 1])
    if '--batch' in sys.argv:
        batch = int(sys.argv[sys.argv.index('--batch') + 1])

    ca = km.Circuit.from_file(str(a))
    cb = km.Circuit.from_file(str(b))
    print(f'A: {a.name}  qubits={ca.num_qubits} bits={ca.num_bits} ops={len(ca)}')
    print(f'B: {b.name}  qubits={cb.num_qubits} bits={cb.num_bits} ops={len(cb)}')
    if ca.num_qubits != cb.num_qubits or ca.num_bits != cb.num_bits:
        print('FAIL: register geometry differs')
        return 1
    sa = ca.operation_statistics()
    sb = cb.operation_statistics()
    print(f'A toffoli_like={sa.num_toffoli_like}  B toffoli_like={sb.num_toffoli_like} '
          f'(saved {sa.num_toffoli_like - sb.num_toffoli_like})')

    s_q, e_b, all_q = registers(ca)
    s_q2, e_b2, _ = registers(cb)
    if len(s_q) != len(s_q2) or len(e_b) != len(e_b2):
        print('FAIL: register partition differs')
        return 1

    rng = np.random.default_rng(seed)
    arr_s = km.array(s_q)
    arr_e = km.array(e_b)
    arr_q = km.array(all_q)
    # kickmix wants (num_register_items, batch)
    qin = rng.integers(0, 2, size=(len(s_q), shots)).astype(bool)
    bin_ = rng.integers(0, 2, size=(len(e_b), shots)).astype(bool)

    def run(c):
        sim = km.Simulator(batch_size=batch, debug_print=False,
                           counting_operations=True, seed=seed)
        sim.use_same_registers_as(c)
        sim.write_across_shots(arr_s, qin)
        if len(e_b):
            sim.write_across_shots(arr_e, bin_)
        sim.do(c)
        out = sim.read_across_shots(arr_q)
        phase = sim.read_phase_flipped_across_shots()
        return out, phase

    oa, pa = run(ca)
    ob, pb = run(cb)
    diff = int((oa != ob).sum())
    pdiff = int((pa != pb).sum())
    print(f'output-bit differences: {diff}   phase differences: {pdiff} '
          f'(over {shots} shots x {len(all_q)} qubits)')
    if diff or pdiff:
        print('FAIL: circuits are NOT equivalent')
        return 1
    print('PASS: circuits are equivalent on the sampled inputs')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
