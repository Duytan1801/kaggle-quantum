#!/usr/bin/env python3
"""dqi_gen_probe.py — rebuild the DQI reference decoder with a different EEA iteration count.

The official reference decoder (`taylorclark637/dqi-reference-decoder-source`,
`dqi_reference_circuit.py`, byte-identical to the competition's
`verifiers/dqi/dqi_reference_circuit.py`) runs

    n_iters = default_n_iters(n) = 3 * (n + 1) + 9

synchronised EEA iterations (222 for the competition's n = 70).  The iteration
count is the ONLY thing that scales the EEA block, and the EEA block is the bulk
of the decoder's Toffolis.  The Euclidean algorithm on the key equation for an
RS(4095, 70) code converges after at most ~n iterations, so 3n may be a very
generous bound.  Each iteration that is not needed is pure cost.

This probe rebuilds the circuit for a list of iteration counts and reports
(static Toffolis, qubits, build time).  The official verifier is the oracle:
a decoder with too few iterations decodes wrongly and the verifier FAILS it.
So the sweep is: build cheaply, then let `verify_submission_dqi.py` decide.

Usage:
    dqi_gen_probe.py --out-dir DIR [--n-iters 222,180,150,120] [--m 4095 --n 70 --degree 12]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KICK = ROOT / 'work/toolchain/kickmix'
GEN = pathlib.Path('/home/bandoc/Downloads/opencode/work/tools/dqi_reference_circuit.py')


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out-dir', required=True)
    ap.add_argument('--n-iters', default='222')
    ap.add_argument('--m', type=int, default=4095)
    ap.add_argument('--n', type=int, default=70)
    ap.add_argument('--degree', type=int, default=12)
    a = ap.parse_args()

    sys.path.insert(0, str(KICK))
    sys.path.insert(0, str(GEN.parent))
    if not GEN.exists():
        print(f'ERROR: generator source missing at {GEN}', file=sys.stderr)
        return 2

    import dqi_reference_circuit as drc  # noqa: E402

    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    counts = [int(x) for x in str(a.n_iters).split(',') if x.strip()]
    rows = []
    for n_iters in counts:
        t0 = time.time()
        builder = None
        try:
            import kickmix as km
            builder = km.CircuitBuilder()
            syndromes = [builder.create_quantum_register(a.degree, name=f'S{i}') for i in range(a.n)]
            error_mbuc = [builder.create_classical_register(a.degree, name=f'E{j}') for j in range(a.m)]
            drc.ProosAndZalkaDecoder(a.n, km.GF2Field(a.degree)).build_syndrome_decoding_mbuc(
                builder, syndromes=syndromes, error_mbuc=error_mbuc, n_iters=n_iters)
            circuit = builder.finish_circuit()
            path = out / f'dqi_niters{n_iters}.kmb'
            circuit.to_file(path, format='kmb')
            st = circuit.operation_statistics()
            row = {'n_iters': n_iters, 'num_toffoli_like': int(st.num_toffoli_like),
                   'num_qubits': int(circuit.num_qubits), 'build_s': round(time.time() - t0, 1),
                   'file': str(path), 'bytes': path.stat().st_size}
            print(f'  n_iters={n_iters:4d}  Toffolis={row["num_toffoli_like"]:>9,}  '
                  f'Q={row["num_qubits"]}  build={row["build_s"]}s', flush=True)
            rows.append(row)
            del circuit, builder
        except Exception as e:
            print(f'  n_iters={n_iters:4d}  BUILD FAILED: {type(e).__name__}: {e}', flush=True)
            rows.append({'n_iters': n_iters, 'error': f'{type(e).__name__}: {e}'})
        (out / 'probe_results.json').write_text(json.dumps(rows, indent=1) + '\n')
    print(f'\nwrote {out / "probe_results.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
