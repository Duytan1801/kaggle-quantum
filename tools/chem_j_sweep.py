#!/usr/bin/env python3
"""chem_j_sweep.py — rebuild the chem ANGLE_k family at different `j` (words per circuit).

WHY THIS IS A REAL LEVER
-------------------------
The official dfthcsos verifier scores the chemistry leg as

    score = lambda_eff * T_total * Q_total

where (see work/toolchain/verifiers/dfthcsos/verify.py):
  * `lambda_eff` comes from the FACTORIZATION npz (U, W, H2_I, H1_I, Hsym_lower)
    via `evaluate_words` -> it is a property of the ANGLES, not of the circuits.
  * `T_total` = angles_toffoli (the simulator's mean Toffolis per shot over the
    forward and reverse passes of the ANGLE family) + the fixed heuristic costs
    (outer/inner state prep + Givens rotations).
  * `Q_total` = persistent_qubits + max(heuristic_temporary, angles_temporary),
    where `angles_persistent_qubits = J * brot` and `J` is the number of word
    registers per circuit.

`J` is read back from the CIRCUIT REGISTER LAYOUT (`layout.batch_size`), not
from the npz, and the verifier requires exactly `ceil(num_angles / J)` circuits
(`num_angles = N-1 = 75`).  So J is a FREE STRUCTURAL PARAMETER of the
submission: re-partitioning the same 75 angle columns into fewer, wider
circuits changes T_total and Q_total while leaving `lambda_eff` (and therefore
the chemistry itself) EXACTLY unchanged.

The generator is `tensorqrom.build_family(words, brot, j=...)` from
`marculera/dfthc-merge-pipeline` (Apache-2.0), which is the same product-cache
design that produced the public "4,022-Toffoli" loaders we already ship.

This script rebuilds the family from the npz's OWN `angle_words` at each j and
scores every candidate with the OFFICIAL verifier.  Nothing is invented: the
words are read from the shipped npz and the verifier is the oracle.

Usage:
  chem_j_sweep.py --npz work/trees/v132_frontier/dfthcsos/submission.npz \
                  --out-root /tmp/opencode/chem_j --j 5,4,3,6,7,8
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
PY = ROOT / 'work/toolchain/venv/bin/python'
KICK = ROOT / 'work/toolchain/kickmix'
VER = ROOT / 'work/toolchain/verifiers'
REFIT = ROOT / 'work/tools/dfthc_refit'

# Official reference costs (maoxin123 public notebook).
REF = 3355599588.3155375


def build_family(j: int, brot: int, words: np.ndarray, out_dir: pathlib.Path,
                 coded=(), sizes=None) -> tuple[list, int]:
    """Build the ANGLE_k family for `j` words per circuit; write kmb files."""
    sys.path.insert(0, str(REFIT))
    sys.path.insert(0, str(KICK))
    sys.path.insert(0, str(VER))
    import tensorqrom  # noqa: E402

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    kw = {}
    if sizes:
        # NOTE: `build_family` ignores its own `sizes` argument for the non-coded
        # path -- `coded_layout()` returns the module-global SIZES (J=5's
        # partition) whenever there are no coded words, which covers only 35 of
        # the 7*J output bits and makes build_circuit assert
        # "decomposition does not cover the tensor" for every J != 5.
        # `coded_layout` reads SIZES as a module global, so setting it here is
        # the supported way to install the partition.
        tensorqrom.SIZES = tuple(sizes)
    family = tensorqrom.build_family(words, brot, j=j, coded=coded, **kw)
    from dfthcsos.example_submission.angle_k_reference_circuit import write_kmx_family  # noqa: E402
    write_kmx_family(family, out_dir, format='kmb')
    return family, len(family)


def auto_sizes(j: int, brot: int) -> list[int]:
    """Output-bit groups: J*(brot-1) bits in groups of 7 (the repo's coded_layout rule)."""
    bits = j * (brot - 1)
    return [7] * (bits // 7) + ([bits % 7] if bits % 7 else [])


def verify(dir_: pathlib.Path, timeout: int = 3600, shots: int = 1) -> dict:
    env = {**os.environ, 'PYTHONPATH': f'{KICK}:{VER}'}
    try:
        r = subprocess.run([str(PY), str(VER / 'dfthcsos/verify.py'), str(dir_),
                            '--shots-per-address', str(shots)],
                           capture_output=True, text=True, env=env, timeout=timeout)
        out = (r.stdout or '') + '\n' + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return {'status': 'TIMEOUT'}
    i, j = out.find('{'), out.rfind('}')
    try:
        return json.loads(out[i:j + 1])
    except Exception:
        return {'status': 'PARSE-FAIL', 'tail': out[-400:]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--npz', required=True)
    ap.add_argument('--out-root', required=True)
    ap.add_argument('--j', default='5')
    ap.add_argument('--brot', type=int, default=None)
    ap.add_argument('--coded', default='', help='comma-separated word columns with a coded bit 0')
    ap.add_argument('--sizes', default='', help='per-j output group sizes, e.g. "5:7,6,6,6,5,5;6:7,7,7,7,7,7"')
    ap.add_argument('--shots', type=int, default=1, help='shots per address (official default is 64)')
    ap.add_argument('--timeout', type=int, default=3600)
    a = ap.parse_args()

    npz = pathlib.Path(a.npz)
    with np.load(npz, allow_pickle=False) as z:
        words = np.asarray(z['angle_words'], np.int64)
        brot = a.brot if a.brot is not None else int(z['brot']) if 'brot' in z.files else 8
        npz_payload = {k: np.array(z[k]) for k in z.files}
    print(f'npz {npz.name}: angle_words {words.shape}, brot={brot}', flush=True)

    # The generator (tensorqrom.build_circuit) refuses words that are not in the
    # SIGNED GAUGE (bit brot-1 == bit brot-2); its `scratch` mode borrows the word's
    # top bit as a cache qubit, which is only sound because the top bit equals the
    # one below.  The shipped npz stores the canonical gauge (only 79.06% compliant),
    # so apply the repo's own EDGE-AWARE transform, onebody.signed_gauge:
    #
    #   * it walks the tree backwards, negating an angle whose parent and child
    #     carry different signs, and moving an angle outside [-pi/2, pi/2) by pi;
    #   * the decoded row changes at most by an overall sign, so the chemistry is
    #     preserved EXACTLY (measured with work/tools/chem_gauge_probe.py:
    #     lambda_eff 46.921562797126406 and error_1/error_2 identical to 1e-13).
    #
    # A naive per-word bit flip is WRONG (it gives lambda_eff 187.4, error_1 15.2).
    with np.load(npz, allow_pickle=False) as z:
        edges = np.asarray(z['tree_edges'], np.int64)
    sys.path.insert(0, str(REFIT))
    import onebody  # noqa: E402
    words = onebody.signed_gauge(words, edges, brot)
    top, below = brot - 1, brot - 2
    gauge_ok = not np.any((((words >> top) ^ (words >> below)) & 1))
    frac = 1.0 - float(np.mean((((words >> top) ^ (words >> below)) & 1)))
    print(f'  signed gauge applied (onebody.signed_gauge): compliant={gauge_ok} frac={frac:.6f}',
          flush=True)
    if not gauge_ok:
        raise SystemExit('gauge transform failed')

    coded = tuple(int(x) for x in a.coded.split(',') if x.strip())
    size_map: dict[int, list[int]] = {}
    for part in a.sizes.split(';'):
        if ':' in part:
            jj, vals = part.split(':', 1)
            size_map[int(jj)] = [int(v) for v in vals.split(',') if v.strip()]
    root = pathlib.Path(a.out_root)
    root.mkdir(parents=True, exist_ok=True)
    js = [int(x) for x in a.j.split(',') if x.strip()]

    rows = []
    for j in js:
        t0 = time.time()
        work = root / f'j{j}'
        sizes = size_map.get(j) or auto_sizes(j, brot)
        print(f'--- j={j}: building family (sizes={sizes})', flush=True)
        try:
            family, ncirc = build_family(j, brot, words, work, coded=coded, sizes=sizes)
        except Exception as e:
            print(f'  BUILD FAILED j={j}: {type(e).__name__}: {e}', flush=True)
            rows.append({'j': j, 'status': 'BUILD-FAIL', 'error': f'{type(e).__name__}: {e}'})
            (root / 'sweep_results.json').write_text(json.dumps(rows, indent=1) + '\n')
            continue
        # keep the shipped factorization; only the circuits change
        np.savez(work / 'submission.npz', **npz_payload)
        build_s = time.time() - t0
        print(f'  built {ncirc} circuits in {build_s:.0f}s; verifying...', flush=True)
        r = verify(work, timeout=a.timeout, shots=a.shots)
        score = r.get('score')
        res = r.get('resources', {}) or {}
        row = {'j': j, 'num_circuits': ncirc, 'brot': brot, 'build_s': round(build_s, 1),
               'status': r.get('status'), 'score': score,
               'lambda_eff': r.get('lambda_eff'),
               'toffoli_count': r.get('toffoli_count'), 'num_qubits': r.get('num_qubits'),
               'angles_toffoli': res.get('angles_toffoli'),
               'angles_qubits': res.get('angles_qubits'),
               'angles_persistent_qubits': res.get('angles_persistent_qubits'),
               'angles_temporary_qubits': res.get('angles_temporary_qubits'),
               'persistent_qubits': res.get('persistent_qubits'),
               'temporary_qubits': res.get('temporary_qubits'),
               'error': r.get('error'), 'tail': r.get('tail')}
        if score:
            row['ratio_vs_ref'] = REF / score
        print(f'  j={j}: status={r.get("status")} score={score} '
              f'T={r.get("toffoli_count")} Q={r.get("num_qubits")} '
              f'lambda_eff={r.get("lambda_eff")} circs={ncirc}', flush=True)
        rows.append(row)
        (root / 'sweep_results.json').write_text(json.dumps(rows, indent=1) + '\n')

    print('\n=== ranking (lower score = better) ===')
    ok = [r for r in rows if r.get('score')]
    for r in sorted(ok, key=lambda x: x['score']):
        print(f"  j={r['j']:>2}  score={r['score']:>18,.3f}  T={r['toffoli_count']:>9}  "
              f"Q={r['num_qubits']:>4}  circs={r['num_circuits']:>3}  "
              f"lambda_eff={r['lambda_eff']}")
    for r in rows:
        if not r.get('score'):
            print(f"  j={r['j']:>2}  {r.get('status')}  {str(r.get('error') or r.get('tail'))[:180]}")
    print(f'\nwrote {root / "sweep_results.json"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
