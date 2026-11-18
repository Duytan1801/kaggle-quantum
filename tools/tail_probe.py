#!/usr/bin/env python3
"""tail_probe.py — where does the invsqrt circuit actually finish?

The official verifier only checks (a) x restored, (b) every scratch qubit back to |0>,
(c) the tracked phase.  It does NOT check the measurement record.  So if the circuit
reaches "x restored + all scratch clean + final phase" at some op index p, everything
after p can be truncated -- every Toffoli in the tail is then free money.

This probe simulates a batch of random task inputs x with the exact simulator (kmsim)
and reports, per op index:
  * the last op that changes the phase (per shot and in aggregate),
  * the first op index at which all scratch qubits are 0 and x is restored,
  * how many Toffoli-like gates execute after that point,
  * whether the phase at the clean point equals the final phase.

Usage: tail_probe.py <circuit.kmx> [--shots 64] [--seed 1]
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, '/tmp/opencode/recon/datasets/asteriospanoras_qcc-circuit-atlas/tools')
import kmsim  # noqa: E402

XMAX = 3133452
WIDTH = 22


def main():
    path = sys.argv[1]
    shots = 64
    seed = 1
    if '--shots' in sys.argv:
        shots = int(sys.argv[sys.argv.index('--shots') + 1])
    if '--seed' in sys.argv:
        seed = int(sys.argv[sys.argv.index('--seed') + 1])

    ops, regs = kmsim.parse(path)
    names = kmsim.register_names(path)
    xreg_id = names.get('x')
    xreg = regs[xreg_id]
    nq, nb = kmsim.sizes(ops, regs)
    print(f'file: {path}  ops {len(ops)}  qubits {nq}  bits {nb}  x register {xreg[:3]}...{xreg[-2:]}')

    sim = kmsim.Sim(ops, nq, nb, shots, seed=seed)
    rng = np.random.default_rng(seed)
    xs = rng.integers(1, XMAX + 1, size=shots)
    for i, q in enumerate(xreg):
        sim.q[q] = ((xs >> i) & 1).astype(bool)

    scratch = [q for q in range(nq) if q not in set(xreg)]
    state = {'last_phase_change': -1, 'first_clean': -1, 'clean_at_phase_end': None,
             'toff_after_clean': 0, 'last_toff': -1, 'phase_hist': []}
    prev_ph = sim.ph.copy()
    prev_toff = sim.toff.copy()
    toff_at_clean = None
    ph_at_clean = None

    def hook(k, s):
        nonlocal toff_at_clean, ph_at_clean
        changed = int(np.count_nonzero(s.ph != prev_ph))
        if changed:
            state['last_phase_change'] = k
        if int(s.toff.sum()) > int(prev_toff.sum()):
            state['last_toff'] = k
        prev_ph[:] = s.ph
        prev_toff[:] = s.toff
        # clean + restored?
        if state['first_clean'] < 0:
            if not s.q[scratch].any() and np.array_equal(s.q[xreg], sim.q[xreg] ^ False) is False:
                pass
            if not s.q[scratch].any():
                # x restored? compare with the initial x bits
                ok = True
                for i, q in enumerate(xreg):
                    if bool(s.q[q][0]) != bool(((xs >> i) & 1)[0]):
                        ok = False
                        break
                if ok:
                    state['first_clean'] = k
                    toff_at_clean = int(s.toff.sum())
                    ph_at_clean = s.ph.copy()
        else:
            state['toff_after_clean'] = int(s.toff.sum()) - toff_at_clean

    sim.run(hook=hook)
    final_ph = sim.ph.copy()
    print(f'  shots {shots}  total Toffoli executions (sum over shots): {int(sim.toff.sum())}'
          f'  mean/shot: {sim.toff.mean():.3f}')
    print(f'  last op that changes the phase: {state["last_phase_change"]} / {len(ops)-1}')
    print(f'  last op that executes a Toffoli: {state["last_toff"]} / {len(ops)-1}')
    print(f'  first op index with all scratch clean (and x restored): {state["first_clean"]}')
    if state['first_clean'] >= 0:
        same = int(np.count_nonzero(ph_at_clean == final_ph))
        print(f'  shots whose phase at the clean point equals the final phase: {same}/{shots}')
        print(f'  Toffolis executed after the clean point: {state["toff_after_clean"]}'
              f'  (mean/shot {state["toff_after_clean"]/shots:.3f})')
        print(f'  => truncating there would save {state["toff_after_clean"]/shots:.3f} Toffoli/shot'
              f' = {44*state["toff_after_clean"]/shots:.1f} cost units'
              f' (GM +{0.0055*state["toff_after_clean"]/shots:.4f})')
    print(f'  final phase matches expected 1/sqrt(x)? (checked by the verifier, not here)')


if __name__ == '__main__':
    main()
