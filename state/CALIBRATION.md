# CALIBRATION LOG — predicted vs actual (OpenAI deep-research weakness remedy)
# Format: date | submission | predicted GM (model + assumptions) | actual | error
2026-11-16 | v121 (58409216) | 28.06406 (predicted from local receipts) | 28.06404 | -2e-5
2026-11-16 | v122 (58411160) | 28.09092 | 28.09090 | -2e-5
2026-11-18 | v131 (58487983) | 28.18084 clean (P(clean)≈0.54; 1-err case 28.1378) | 28.18084 | 0
2026-11-19 | v132 (58539070) | 28.23163 (atlas receipt + our own 3-leg official verifiers, all exact) | PENDING | —
# Calibration summary: GM point-predictions exact to <1e-4 when receipts are local;
# distributional calls (clean-draw probability) so far 1/1 correct.

## 2026-11-19 — CALIBRATION CORRECTION: the invsqrt width leverage was 2.8× understated

**Prediction (as recorded in the goal files before this correction):** "invsqrt ≈ +0.077 GM per
qubit dropped", derived with the wrong marginal formula.

**Actual (re-derived this wake from the authoritative constants):** maoxin123's public
notebook carries the reference values
`REF = {invsqrt: 2076774.233715, dqi: 24439463583672.93, dfthcsos: 3355599588.3155375}`
and `GM = (Π REF_i/cost_i)^(1/3)`. Our own row reproduces **exactly** from these:
costs `{invsqrt: 74560.90687312803, dqi: 346404203610.11, dfthcsos: 294642299.7630277}`
→ ratios `27.853393 × 70.551868 × 11.388723` → **GM 28.180837** (row = 28.18084 ✓).
The marginal value of a fractional cost cut in one leg is `dGM = GM/3 × d(cost)/cost`,
so one wire off a Q44 tree (a 2.2727% cost cut) is worth
`28.18084/3 × 0.022727 = +0.2135 GM`, and recomputed exactly at the frontier's costs
**+0.2168 GM**.

| width move | old (wrong) | actual | error factor |
|---|---|---|---|
| invsqrt −1 wire @Q44 | +0.077 | **+0.2168** | 2.8× understated |
| invsqrt −1 wire @Q46 | +0.077 | +0.2042 | 2.7× understated |
| DQI −1 wire @Q890 | +0.021 | +0.0211 | correct |
| DQI width → 840 | — | +1.1075 | n/a |

**Consequence:** the invsqrt width lane was de-prioritised because the goal text said a wire
was worth ~1/3 of a DQI wire; the truth is the opposite — **one invsqrt wire is worth TEN
DQI wires**. Any prior ranking that put DQI width above invsqrt width was inverted.
Corrected table is now in `work/GOALS.md`.

**Secondary calibration check — the atlas frontier tree:** predicted GM 28.23163 from the
atlas receipt's own verifier numbers; our own unchanged official verifiers on the exact
bytes reproduced all three legs to the last digit
(invsqrt 74,405.67238374705 · dqi 345,256,821,433.9815 · dfthcsos 294,642,170.565169),
so the local receipt and the moat-lab in-kernel receipt agree exactly.

