# Quantum 2026 v150: dqi generator source (private)

Rebuilds the v150 dqi member(s) from this archive alone: candidate `dqi/721_dqi_release_698r2/release_698r2`.
Run `python -B build.py OUTDIR`; every file in `SHA256SUMS` must match. Needs Python 3.13 and numpy.

## Lineage, original builder first

1. Syed Asad Ali, VQCC Own-Circuit Portfolio v12 DQI builder (Apache-2.0)
2. Ertuğrul Özer
3. Areeb Ali
4. Quantum 2026 DQI 541-568c1 generator (no stored plans)
5. Quantum 2026 DQI 580 piece stack (GPT D68b, D67, D66e/f)
6. GPT chat D74 (quotient lifecycle, conditional flag); owner chats 701 and 705; Codex lane 677 round 2; DQI 698 stack

## Contents

- `repo/experiments/dqi/iterations/721_dqi_release_698r2/package/`: the coordinator's handoff package (q2026-handoff-v1); its `RECIPE.json` lists every build file and repository input with its SHA-256, from a traced build.
- `repo/...`: every repository file the traced build read (same paths as in the repository).
- `build.py` + `BUILD.json`: the generic entry point; `MANIFEST.json`: every archived file and where it came from.

## Files that are not ours

`repo/host_provided/` holds competition files, used under the competition terms. Public inputs keep their own licence files (listed in the lineage above).
