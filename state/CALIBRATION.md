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



## 2026-11-19 — v133 adoption and the chem J lever (prediction vs actual)

**v133 (public combo `ghazarosbarseghyan91/vqcc-combo-candidates`):** the publisher's notebook states
invsqrt 74,383.70, dqi 3.45257e11 (zero-error), chem 294,642,169.51, expected GM 28.2344.  OUR OWN runs of
the UNCHANGED official verifiers on the exact bytes:
invsqrt **74,383.69875786705** (200,540,928 shots, PASS, 44 q, 33 rotations, eps 2.005423596e-13,
worst err/tol 0.9994556024791729 at x=231) · dqi **345,256,821,433.9815** (102,400 shots, 0 value / 0 phase
errors) · chem **294,642,169.5116752** (PASS, lambda_eff 46.92156262935824, T 14,706, Q 427) ⇒
GM **28.23440992** (local) vs **28.234409967092166** (moat-lab in-kernel, kernel v50).  The two receipts
agree to 7 decimals; the published numbers were right to their precision.

**Chem J lever (H12) — PREDICTION FALSIFIED.**  marculera's design note claims fewer ANGLE circuits ⇒ fewer
Toffolis.  Measured with the official verifier on our own words:
| J | circuits | angles_toffoli | angles_qubits | Q_total | chem score | vs shipped |
|---|---|---|---|---|---|---|
| 4 (shipped) | 15 | **8,044** | 128 | 427 | **294,642,170.565** | — |
| 5 (marculera) | 15 | 9,864 | 119 | 427 | 331,106,793.88 | +12.4% |
| 6 (marculera) | 13 | 9,722 | 126 | 435 | 334,411,854.92 | +13.5% |
| 7 (marculera) | 11 | — | 133 | — | REJECTED (>128-qubit cap) | — |
| 8 (marculera) | 10 | — | 140 | — | REJECTED (>128-qubit cap) | — |
So a J step buys −1.4% T but costs +1.87% Q, and J≥7 is structurally impossible (the 128-qubit ANGLE cap).

**Leverage constants re-derived (chem leg, score = lambda_eff × T × Q, Q = 427):**
1 chem Toffoli = **+0.000640 GM**; 1 chem qubit = **+0.02204 GM**; chem lambda_eff −1e-7 ≈ +0.0000001 GM.
**invsqrt:** 1 unit of invsqrt cost = **+1.264e-4 GM**; 1 invsqrt Toffoli ≈ 55 cost units ≈ **+0.00695 GM**;
1 invsqrt wire at Q=44 = **+0.2168 GM** (unchanged).  **DQI:** 1 DQI Toffoli ≈ **+2.6e-5 GM**; 1 DQI wire
at Q=890 = +0.0211 GM (unchanged).  **v133's +0.00278 GM decomposes as:** invsqrt cost −21.97 → +0.002778,
chem cost −1.05 → +0.0000004.

**DQI salt fact (H16, CONFIRMED by source):** `verify_submission_dqi.py::_initial_seed(circuit_hash, salt)`
hashes the .kmb bytes; the draw is a property of the DQI circuit alone, not of the 18-file tree.  Same DQI
bytes ⇒ same draw ⇒ the board-clean v132/v133 DQI draw is preserved by any change to the other legs.

## 2026-11-21 — the 2-day frontier jump and v135 (prediction vs actual)

**Why we were 838th.**  The radar was alive but the *adjudicator* was not keeping
pace: 378 rows had been closed and then resurrected by the radar's flush bug
(fixed 2026-11-19), and between 11-19 10:34 and 11-21 01:39 the public board
moved 31.74002 -> 33.34845 and the public tree from 28.23441 to 33.07536.  Two
days of releases (ThemBones' three new circuits on 11-20, then three cheaper
files overnight) went unread.  **The lesson: the queue must be adjudicated every
wake, and a kernel's OUTPUT (submission.zip) is where the tree lives —
`kaggle kernels pull` never fetches it.**

**v133 prediction vs actual:** predicted 28.23441; the board scored
**28.23441** exactly (rank 838).  The verifier-dominated model is exact when the
bytes are exact.

**v135 (public best, adopted 2026-11-21):**
| leg | bytes | our own verifier run | ratio |
|---|---|---|---|
| invsqrt | d2148a7cd7a4d0a0 | PASS 60,955.32670759028 (200,540,928 shots, 37 q, 1406.3123 Toffolis, eps 1.888e-13, worst/tol 0.9994718 @252) | 34.070431 |
| dqi | 4b5721411adc239f | PASS 305,041,647,011.3978 (102,400 shots, **0 value / 0 phase**, 900 q, 316,131.22 T, rep 1.19126) | 80.118449 |
| dfthcsos | npz 6b9903dda33a + loader_k_2 046679fe | PASS 253,143,456.48793402 (405 q, T 13,322, lambda_eff 46.918298421794454) | 13.255723 |
Predicted **33.07535601** (local) = **33.07535601389506** (in-kernel), submitted
as ref 58645864.  **+4.84095 GM over v133.**

**Leverage at the v135 operating point:**
| move | GM | note |
|---|---|---|
| invsqrt -1 qubit @37 q | **+0.30** | 1/37 of the cost; the single biggest lever |
| invsqrt -1 Toffoli-eq | +0.0002 | 1/1647 of the cost |
| dqi -1 qubit @900 q | +0.00074 | cost is proportional to Q^2 (2/900 / 3) |
| dqi -1 Toffoli (of 316,131) | +0.0000011 | needs an algorithmic cut |
| chem -1 qubit @405 q | +0.00082 | cost is proportional to Q |
| chem -1 Toffoli (of 13,322) | +0.000025 | 1/13,322 / 3 |
| chem T -1 % | +0.0033 | the heuristic 6,500 is 51 % of T |
