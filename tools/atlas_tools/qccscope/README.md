# qccscope: fast diagnosis of kmx circuits (no kickmix)

A small numpy library and CLI that reads a kickmix `.kmx` text circuit (also `.kmx.gz` / `.kmx.xz`) into a compact op
table and reports, in seconds, where Toffolis or qubits might be saved. It is the library we used to find the
invsqrt dead-write fix that is in `contributions/invsqrt/` (one `CCX` whose target is only measured afterwards).

```bash
cd /kaggle/input/qcc-circuit-atlas/tools
python -m qccscope report ../kmx/invsqrt/9c708f7b9abc.kmx --task invsqrt            # 256 sampled inputs, ~1 s
python -m qccscope report ../kmx/invsqrt/9c708f7b9abc.kmx --task invsqrt --exhaustive  # every x (minutes, a few GB RAM)
python -m qccscope report FAMDIR/angle_k_*.kmx --task chem --npz FAMDIR/submission.npz  # a chemistry family
```

```python
import sys; sys.path.insert(0, "/kaggle/input/qcc-circuit-atlas/tools")
from qccscope import kmx, liveness, structure, cost
c = kmx.load("/kaggle/input/qcc-circuit-atlas/kmx/invsqrt/9c708f7b9abc.kmx")
lv = liveness.compute(c); S = structure.scan(c)
print(c.n_ops, c.num_qubits, lv.peak, len(S.dead_writes), cost.saving_points("invsqrt", d_toffoli=1))
```

| Module | What it does |
|---|---|
| `kmx.py` | Streaming parser to numpy arrays (op, operands, HMR/condition bits, PUSH_CONDITION depth, registers, Z_POW angles), with an optional on-disk cache for very large (DQI) files. |
| `cost.py` | The three task cost models (copied from the official verifiers' formulas) and exact exchange rates: leaderboard points per Toffoli, per qubit, per rotation margin. The default numbers are the official results of the public files of 2026-11-14 named in the file; pass your own. |
| `liveness.py` | Static width profile, peak episodes, idle-gap cover: what blocks removing one qubit. |
| `structure.py` | Static motif detectors: Toffoli-erased ANDs (measurement-based uncompute candidates), cancelling Toffoli pairs, dead writes, statically-zero controls, Toffoli kinds. |
| `values.py` | Bit-sliced sampled simulation (one bit per input lane): executed-Toffoli mean, constant/affine Toffolis, repeated products (retention candidates), zero gaps, end-state check. Sampled properties are candidates only: prove them on all inputs (invsqrt: `tools/kmsim.py`, or `--exhaustive`) or with the official verifier. |
| `motifs.py` | Turns detector output into findings with an estimated saving in task units and leaderboard points and a confidence label (exact / sampled / bound / info). |
| `report.py`, `__main__.py` | Markdown report (single circuit or a chemistry loader family) and the CLI. |
| `tests/test_qccscope.py` | Unit tests on tiny hand-written circuits (`cd tools && python -m pytest -q qccscope/tests`, under a second). |

A finding is a hint, not a result: confirm every change with the official verifier before you submit it.
Licence: Apache-2.0 (our code). The kmx format, kickmix and the verifiers are by Google Quantum AI / Qualtran.
