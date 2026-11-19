# Tools (Apache-2.0)

Pure Python + numpy; none of them imports `kickmix`. Every tool reads `.kmx` (and also gzip-compressed `.kmx.gz`). The files are uploaded gzip-compressed and Kaggle serves them decompressed, so on Kaggle they are plain `.kmx` / `.npz`.

| Tool | What it does | Example |
|---|---|---|
| `kmsim.py` | Exact batch simulator of the kickmix op subset used here (qubits, bits, phase in 2^-64 turns, Toffoli and rotation counters) plus the invsqrt accuracy check. On circuit 9c708f7b9abc over every x its worst error/tolerance equals the official verifier's (0.9993237694056958). | `python kmsim.py ../kmx/invsqrt/<sha12>.kmx --xmax 4096` |
| `liveness.py` | Static qubit liveness: peak number of simultaneously live qubits, a lower bound for a re-allocation of the same op sequence. | `python liveness.py ../kmx/invsqrt/<sha12>.kmx` |
| `splice_dp.py` | Cheapest splice of several passing invsqrt circuits at "clean cuts" with identical state, by shortest path. Checked on sampled inputs only. | `python splice_dp.py A.kmx B.kmx --out splice.json` |
| `build_splice.py` | Writes the kmx circuit described by a `splice_dp.py` result. | `python build_splice.py splice.json out.kmx --kmx-dir ../kmx/invsqrt` |
| `loader_check.py` | Local emulation of the chemistry loader contract on a family folder (clean workspace, unchanged selection, no phase, forward and reverse word blocks). | `python loader_check.py FAMDIR` |
| `atlas_family.py` | Rebuilds one chemistry family folder (angle_k_*.kmx + submission.npz) from this dataset. | `python atlas_family.py FAMILY_ID FAMDIR` |
| `atlas_io.py` | Find the dataset root under /kaggle/input, look up a file by sha12 (`circuit`, `local_path`), read `contributions/index.json`, convert kmx -> kmb with the competition's kickmix (`to_kmb`). | `import atlas_io as A; A.local_path("e46d90c36d1b")` |
| `refit/` | Chemistry DF-THC weight refit at fixed angle words (GRG; numpy port of prvsiyan's refit_grg.py) and exact metrics with the verifier's math; reads the competition verifier at run time. See `refit/README.md`. | `python -m refit run --start NPZ --minutes 20 --out DIR` |
| `qccscope/` | Circuit diagnosis library: kmx parser, cost models and exchange rates, liveness, motif detectors, sampled value scan, report. See `qccscope/README.md`. | `python -m qccscope report FILE.kmx --task invsqrt` |
| `build/` | The builders of this dataset (`build_atlas.py`, `atlas_docs.py`, `build_contrib.py`, `scan_local.py`, `kmxstats.py`; they need the scan outputs and are kept for provenance). | `python build_atlas.py --help` |

Tests (seconds, no network, no competition data): `python tools/tests/test_tools.py`, `cd tools && python -m pytest -q
refit/tests qccscope/tests tests` (or run each test file with python).
The competition's verifiers, kickmix and FCIDUMP are Competition Data and are not included: attach the competition
data to your notebook for `refit` and `atlas_io.to_kmb`.

Always confirm a circuit with the official verifier before you submit it: these tools are for analysis.
