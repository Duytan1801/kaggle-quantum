# Quantum 2026 v154: isr generator source (private)

Rebuilds the v154 isr member(s) from this archive alone: candidate `isr/772_isr_769_dial_w8/official_a`.
Run `python -B build.py OUTDIR`; every file in `SHA256SUMS` must match. Needs Python 3.13 and numpy.

## Lineage, original builder first

1. Syed Asad Ali, original v12/v13 ISR builder (Apache-2.0)
2. Danish Ali / team ThemBones, the ISR generator (VQCC ThemBones milestone generators, Apache-2.0), run end to end
3. Quantum 2026 ISR 758 lanes (Codex): F our own m9 phase form, A affine DIV2 carry, I dial rewrite (w8 on an existing parity); ISR 769/772 build and packaging

## Contents

- `repo/experiments/isr/iterations/772_isr_769_dial_w8/package/`: the coordinator's handoff package (q2026-handoff-v1); its `RECIPE.json` lists every build file and repository input with its SHA-256, from a traced build.
- `repo/...`: every repository file the traced build read (same paths as in the repository).
- `build.py` + `BUILD.json`: the generic entry point; `MANIFEST.json`: every archived file and where it came from.

## Files that are not ours

`repo/host_provided/` holds competition files, used under the competition terms. Public inputs keep their own licence files (listed in the lineage above).
