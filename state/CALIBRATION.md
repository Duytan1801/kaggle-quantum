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

## 2026-11-21 — v135 scored exactly; v136 (multi-block chem splice) submitted

**v135 prediction vs actual.**  Predicted GM 33.07535601389506 from our own three
official-verifier runs; the board scored **33.07531** (33.075356... to the
displayed precision).  Exact, as for v133 (28.23441).  Rank after scoring: 25.

**v136 (boristown's multi-block DAG chemistry splice) — adopted and submitted.**
Public tree = the OUTPUT of `boristown/qcc-gap-3-residue-repair-and-c43-native-compiler`
(kernel outputs are where competitor trees live; `kernels pull` never fetches them).
invsqrt and dqi are byte-identical to v135; 8 of the 15 chemistry loaders change
(k = 2,3,4,8,9,10,12,13,14 from rupam2020 instead of rithvik, spliced only at
matching batch boundaries).

| leg | bytes | our own official run | ratio |
|---|---|---|---|
| invsqrt | d2148a7cd7a4d0a0 | PASS 60,955.32670759028 (200,540,928 shots, local + in-kernel) | 34.070431 |
| dqi | 4b5721411adc239f | PASS 305,041,647,011.3978 (102,400 shots, 0 value / 0 phase, in-kernel) | 80.118449 |
| dfthcsos | npz 6b9903dda33a + 15 loaders | PASS 252,573,399.16210923 (T 13,292, Q 405, lambda 46.918298421794454; local + in-kernel) | 13.285641 |

Predicted **33.10022097**, published receipt 33.100220972901965.  Submitted as
ref **58646682** (+0.02486 over v135).  Our local chem verifier reproduced the
public receipt to the last digit.

**The corrected leverage table (the old one was under-stated by the Q factor).**
At the v136 operating point (GM 33.10022):

| move | dGM | note |
|---|---:|---|
| invsqrt -1 qubit @37 q | **+0.2984** | cost = Q x T_eq |
| invsqrt -1 rotation (29.07 T = 7.27 T_eq) | +0.0487 | 33 rotations cost 959 T = 240 T_eq |
| invsqrt -1 Toffoli-equivalent | +0.00670 | |
| dqi -1 qubit @900 q | **+0.0245** | cost = R x Q^2 x T |
| dqi -1 Toffoli (of 316,131) | +0.0000349 | |
| chem -1 qubit @405 q | **+0.0272** | cost = lambda x T x Q |
| chem -1 Toffoli (of 13,292) | +0.00083 | |
| chem -1 % of T | **+0.110** | |
| chem -1 % of lambda_eff | +0.110 | lambda is at its floor (46.9183 vs 46.9160 best known) |

Gap to #1 (33.34845) = **0.24823**, which is worth any one of:
8.5 chem qubits OR 2.26 % chem T OR 300 chem Toffolis OR 10.1 DQI qubits OR
2.5 % DQI T OR 5.1 invsqrt rotations OR 37 invsqrt Toffolis OR 1 invsqrt qubit.

**H21 salt probe (CONFIRMED).**  The official DQI verifier at five salts on our
exact bytes: clean at the default salt and at salt-v135-d, **one value error at
salt-v135-a/b/c**.  Cost 305,041,647,011.4 -> 306,442,8xx,xxx (+0.459 %).
The per-shot failure probability of this decoder is ~1e-5, so
P(at least one failed shot at the unknown private salt) ~= 64 %, and the expected
private-board penalty is ~ -0.05 GM (bounded, not a zero).
See `work/recon/dqi_salt_probe_2026-11-21.md`.

## 2026-11-21 — v135 / v136 predictions vs actual, and the corrected leverage map

**v135 (ref 58645864):** predicted GM 33.07535601389506 (from our own three
official-verifier runs).  The board scored **33.07531** — exact to the 5
published decimals.  The verifier-dominated model is exact when the bytes are
exact; the 5th decimal is the board's rounding.

**v136 (ref 58646682):** boristown's multi-block chemistry splice, predicted
GM **33.100220972901965**; our own local chemistry run reproduced
252,573,399.16210923 exactly (T 13,292, Q 405, lambda 46.918298421794454) and
the in-kernel moat-lab v52 run agreed.  Board row at adoption time: 33.10018
(public best = 33.1002).

### CORRECTION — the leverage table in earlier notes was 33x too small per Toffoli

GM = (PROD REF_i / cost_i)^(1/3), and cost = Q * (Toffoli-equivalents).  So one
Toffoli removed changes the leg cost by Q/cost = 1/T_eq, and the GM moves by
GM/3 * 1/T_eq.  At the v136 operating point (GM 33.10022):

| move | GM delta (correct) |
|---|---:|
| invsqrt -1 qubit @37 q | **+0.2984** |
| invsqrt -1 rotation (29.07 T = 7.27 T_eq) | **+0.0487** |
| invsqrt -1 Toffoli-equivalent | **+0.00670** |
| invsqrt -1 T gate | +0.00168 |
| dqi -1 qubit @900 q (cost ~ Q^2 T) | **+0.0245** |
| dqi -1 failed-shot penalty (private board only) | up to **+0.0507** expected |
| dqi -1 Toffoli (of 316,131) | +0.0000349 |
| chem -1 qubit @405 q | **+0.0272** |
| chem -1 % of T | **+0.110** |
| chem -1 Toffoli (of 13,292) | +0.00083 |

The earlier notes quoted the *relative* fractions (1/37, 1/405, 2/900) instead
of the GM deltas, which made Toffoli-level moves look worthless.  They are not:
**37 invsqrt Toffolis = 1 invsqrt qubit = 8.5 chem qubits = 300 chem Toffolis
= 2.26 % of chem T = 10.1 DQI qubits = 2.5 % of DQI T.**

Gap to #1 (Z3C1oherence 33.34845) from 33.10022 = **0.24823**, i.e. ONE invsqrt
qubit, or 2.26 % of chem T, or 10.1 DQI qubits, or 5.1 invsqrt rotations.

### Salt probe (H21, CONFIRMED) — see work/recon/dqi_salt_probe_2026-11-21.md

Our DQI (4b572141) drew **1 value error** at 3 of 4 non-default salts.  The
verifier's repetition factor then costs +0.459 % of the DQI leg (-0.051 GM).
Per-shot failure probability ~1e-5, so P(at least one failure at the unknown
private salt) ~ 64 %.  Expected private-board penalty ~ **-0.05 GM**, bounded,
not a zero.

### v136 board row (2026-11-21 12:0x UTC) — prediction vs actual

| | predicted | actual board row | delta |
|---|---:|---:|---:|
| GM | 33.100220972901965 | **33.10018** | -0.00004 (board rounds to 5 decimals) |
| invsqrt | 60,955.3267 @37 q | 60,955.33 (local official run, 200,540,928 shots) | exact |
| dqi | 3.050416470113978e11 @900 q, 0 err | same bytes as v135 | exact |
| chem | 252,573,399.16210923 @405 q, lambda 46.918298421794454 | same | exact |

The prediction was right to the board's precision.  The rank is ~42 because
~40 teams independently published the same boristown tree family (33.10020).

### H26 (invsqrt angle refit) — predicted vs measured

Predicted: "a minimax refit of the 33 priced angles enlarges min_margin; +0.25 GM
needs a x256 margin factor, +0.5 GM needs x65,536."
Measured: the margin factor ceiling is **x16.98** (`min_margin <= min_x tol(x)
= tol(max_x) = 6.21e8 units`), and the LP found **no** improvement at all
(m = 36,584,657.8 = the current optimum).  The prediction was wrong on the
mechanism (the fit was already minimax-optimal) and wrong by 4x on the
ceiling (+0.13 GM, not +0.25).  Lesson: before promising a margin-driven GM
gain, compute the tolerance ceiling `min_x tol(x)` — it bounds the whole lane.

### H25 (extra salt-invariant basis function) — predicted vs measured

**Prediction:** one additional priced `Z_POW` on a scratch wire could enlarge
the phase span. The pre-registered break-even was a margin improvement
greater than **x2.96**, because the added rotation costs about 268 score
units.

**Measured:** the complete legal catalogue contained 495 wire/position
occurrences, 104 distinct functions, and zero mismatches across six
independent HMR outcome streams (four random, all-zero, all-one). The exact
all-input Chebyshev LP for every candidate produced a best margin of
39,585,698.8 versus 36,584,657.8: only **x1.0820**, a factor 2.74 short of
break-even. The best one-rotation circuit scores **61,210.8541**, versus
**60,955.3267** for the baseline, so it is **255.5274 cost units worse**.

**Verdict:** H25 is killed. The prediction overestimated the incremental
phase-span value of a legal scratch-wire basis function by more than 2.7x in
the decisive ratio. The complete catalogue had to be enumerated before this
could be rejected; a sampled search would not have been sufficient evidence.

### Public-release sweep — predicted vs actual

**Prediction:** the two new 37 q kernel releases might contain a better DQI
or chemistry splice, and the Apache catalog's 7,930 files might expose a
width-reduced component hidden outside the release radar.

**Measured:** both 37 q kernel outputs are component-byte-identical to v136
on all 18 files; the older ThomasG tree is worse on every leg; and all 660
scored Apache rows have zero invsqrt, DQI, or chemistry component cheaper
than v136. Actual release-lane gain: **0 GM**. No slot was spent. This is a
successful negative calibration: advertised width labels were not treated as
evidence without component-byte and measured-cost checks.

## 2026-11-22 — v137 through v144 predictions vs actual

| release | predicted GM | board row | displayed error |
|---|---:|---:|---:|
| v137, ref `58658870` | 33.10189299494091 | **33.10185** | -0.000043 (board rounds to 5 decimals) |
| v138, ref `58659698` | 33.10190185550799 | **33.10186** | -0.000042 (board rounds to 5 decimals) |
| v139, ref `58694635` | 33.13881038958233 | **33.13877** | -0.00004039 |
| v140, ref `58697756` | 33.1388155155283337620293485875 | **33.13876** | -0.00005552 |
| v142, ref `58704506` | 33.138896964186566120113950746488050643547143089038 | **33.13885** | -0.00004696 |
| v143, ref `58711337` | 33.1439220823404781609380739820350565305934107352740789700917 | **33.14388** | -0.00004208 |
| v144, ref pending | 33.1439847224675759169083408104802578161029519713326461544372 | PENDING | — |

The v137/v138 predictions came from exact local official-verifier receipts
and again matched the board's five-decimal row.  v139 was the first prediction
in this cycle with a chemistry-only mechanism move: Leo Tang's T7421 tree
changes the chemistry table to `b3683e07` and replaces the loader family,
while invsqrt `d2148a7c` and DQI `4b572141` remain byte-identical.

v139's predicted legs are:

| leg | exact official-verifier result | ratio |
|---|---:|---:|
| invsqrt | 60,955.32670759028 | 34.070430688983215 |
| DQI | 305,041,647,011.3978, 0 value / 0 phase errors | 80.11844881876 |
| dfthcsos | 251,692,077.714951, T=13,244, Q=405 | 13.332162135495805 |

The local unchanged chemistry verifier and moat-lab v53's unchanged in-kernel
verifier agree exactly.  The runner-up Areeb tree predicts 33.138735205848945
at chemistry cost 251,693,790.80323407; Leo is better by 1,713.08828307 cost
units and therefore **+0.0000751837 GM** in predicted composite score.
This is a useful calibration: a very small chemistry-cost margin can decide
between two public releases, but it is too small to survive the board's
five-decimal display or any private-salt perturbation by itself.

v142 then established the new scored best at **33.13885**.  v143 replaced
only the inverse-square-root member with varianceofx's certified three-T
phase compiler (60,927.57739905387 at 37 q), predicting
**33.1439220823404781609380739820350565305934107352740789700917** and
scoring **33.14388**, a new best.  The displayed error of -0.00004208 is
consistent with the -0.00004039 to -0.00005552 errors on the preceding
same-cycle rows; predictions from exact local receipts therefore remain
systematically useful at the five-decimal board precision but should not be
presented as exact public-score matches.

v144 changes only Leo Tang's chemistry factorization NPZ to
`fd02c7f730b024a1`; the unchanged local official chemistry verifier PASSes
at **251,688,794.86073643**, 1,427.03520632 cost units below v143's
251,690,221.89594275.  With the same inverse-square-root and DQI bytes, the
predicted gain is **+0.0000626401270977559702668284452012855095412360585671843455
GM**.  This is a real but deliberately small release gain; it must not be
inflated by presenting the board's five-decimal display as an exact score.

v144 scored **33.14394** on the public board (ref `58713892`), against the
exact-receipt prediction **33.1439847224675759169083408104802578161029519713326461544372**
— a displayed error of **-0.00004472**, inside the established
-0.00004039 to -0.00005552 public-salt band.  It remains the current scored
best.

v145 adopted the exact 18-member output of `ozertuu/google-quantum-ai-vqcc-33-170350`.
The inverse-square-root member is byte-identical to v144; the DQI member
`141f02ac69638c78` is v144's DQI with exactly one conditional `CCZ` removed;
chemistry is the 3,357-Toffoli loader tree, independently PASSed locally at
**251,089,557.50839654** (405 q, lambda_eff 46.917982145460485).  Using
ozertuu's published DQI cost 305,041,160,753.34 the exact prediction was
**33.1703479737831408066848265849219924110754769688805472789162**
(+0.0263632513 GM over v144).

**That prediction was wrong, and the gate caught it.**  moat-lab v59 ran the
UNCHANGED official DQI verifier on the exact v145 snapshot bytes: the DQI leg
came back `PASS` mechanically but with **2 value errors out of 102,400 shots**
and a cost of **307,632,423,468.0979** (not 305,041,160,753.34).  The
removed `CCZ q63 q507 q204 if b49140` is NOT redundant: the public release's
own log only verified the chemistry leg, so its 33.17035 claim was never
backed by a DQI verification.  The implied composite would have been
**33.07695127730162880252628437417097183896**, i.e. **-0.067033 GM versus
v144** — a public-tree adoption that would have made our row WORSE.

Calibration lesson: a public scorecard that quotes a DQI cost without running
the official DQI verifier must be treated as an unverified claim.  The
Toffoli-model check (the removed conditional CCZ implied a mean Toffoli
reduction of 0.5039 per shot, which matched ozertuu's number exactly) was
*consistent* with a legal edit and still wrong, because the edit changed the
syndrome values, not the gate count.  Only the official verifier's shot-error
counter distinguishes the two, so **every DQI member must be officially
verified before it enters a tree**, regardless of how small the edit is.

v146 therefore keeps v144's verifier-clean DQI (`4b5721411adc239f`, 0 value /
0 phase errors) and swaps only the chemistry table for the best measured
public one, `e7f08627208c`, on the shared 3,357-Toffoli loaders: official
local chemistry PASS **251,089,557.46576697** (T 13,214, Q 405, lambda_eff
46.91798213749483), i.e. 599,237.39496946 cost units below v144's chemistry.
With the unchanged inverse-square-root and DQI bytes the predicted score is
**33.1703303503537523913065411197878713240478112544176321620074**
(**+0.0263456279 GM** over v144's
33.1439847224675759169083408104802578161029519713326461544372).

**v146 scored 33.17029** (ref `58749949`, board COMPLETE 2026-11-23 00:34:54
UTC, read at 01:07 UTC).  The prediction was
**33.1703303503537523913065411197878713240478112544176321620074**, so the
displayed error is **-0.00004035** — inside the established public-salt band
(v144: -0.00004472) and **v146 is the new scored best** (33.17029 vs v144's
33.14394), i.e. the prediction model is still exact to the fifth decimal after
the chemistry swap.

Frontier refresh (2026-11-23 00:2x UTC): the public leaderboard moved to
**33.83493** (`Entangled Team`), with codebeforework 33.54018, Two-Qubit Gate
33.51863, Schrodingers Cats Lived 33.51568.

**Correction to an earlier note.**  The "inverse-square-root cost <=
58,237.0814940" figure quoted for the new 33.83493 leader is **wrong**; that
number is the threshold for the *old* leader 33.67349.  Recomputed exactly
from the v146 receipt (ratios 34.08594797907608 / 80.11844881876 /
13.364154296910707, product 36,499.14):

| target GM | inverse-square-root cost needed |
|-----------|----------------------------------|
| 33.83493 (`Entangled Team`) | **<= 57,407.3438787498** |
| 33.54018 (codebeforework) | <= 58,934.1648 |
| 33.51863 (Two-Qubit Gate) | <= 59,047.9088 |
| 33.51568 (Schrodingers Cats Lived) | <= 59,063.5021 |

With the 39 q generator build's per-wire cost 61,696.23146663024/39 =
**1,581.954652990519**, this means: a **37 q** build of that generator scores
58,532.10 → GM **33.6168** (enough for **2nd place**, above codebeforework),
and a **36 q** build scores 56,950.16 → GM **33.9252** (enough for **1st
place**).  Every Toffoli removed from a 37 q circuit is worth ≈ **+0.0067 GM**
and a 1 % cut in any single leg is worth **+0.1105 GM** at GM 33.17.

Evidence: `work/receipts/V145_MOAT_RECEIPT.json` (verdict V145-RECEIPT-FAIL),
`work/receipts/OZERTUU_33170350_LOCAL_CHEM_VERIFY.log`,
`work/receipts/V146_LOCAL_CHEM_VERIFY.log`,
`work/receipts/V146_BOARD_SCORE.tsv` (board 33.17029),
`work/harvest/VERDICTS_2026-11-23.tsv`.

**Frontier calibration after v143:** the current leader remains 33.67349.
Holding the latest public DQI/chemistry legs fixed, matching that leader
requires an inverse-square-root cost no greater than 58,097.5763957674.
H24's nominal 37 q/58,532 build remains above that threshold by 434.4236
cost units, so width plus an additional mechanism is still required.

Evidence: `work/receipts/V139_RECEIPT.json`,
`work/receipts/V139_MOAT_RECEIPT.json`,
`work/receipts/V139_LOCAL_CHEM_VERIFY.log`,
`work/receipts/V143_RECEIPT.json`, `work/receipts/V143_MOAT_RECEIPT.json`,
`work/receipts/V143_LOCAL_INVSQRT_VERIFY.log`,
`work/receipts/LEOTANG_ROUND4_LOCAL_CHEM_VERIFY.log`, and
`work/recon/public_harvest_2026-11-22_v139.md`,
`work/receipts/V146_RECEIPT.json`, `work/receipts/V146_MOAT_RECEIPT.json`.


## 2026-11-23 06:2x UTC — v146 board calibration + v147 prediction

| # | submitted | predicted GM | board GM | displayed error | note |
|---|---|---|---|---|---|
| v144 | ref 58713892 | 33.1439847224675759169083408104802578161029519713326461544372 | 33.14394 | **-0.00004472** | public-salt band |
| v146 | ref 58749949 | 33.1703303503537523913065411197878713240478112544176321620074 | 33.17029 | **-0.00004035** | public-salt band |
| v147 | ref 58763051 | **33.17067** (clean DQI draw) / 33.00336 (default-salt 4-error draw) | pending | — | two-branch prediction, see below |

**Two-branch calibration rule (measured from three public trees).**  The public
board re-runs the official verifiers with an **unknown salt**; the failed-shot
count is drawn from the file's own `sha256 + salt`, and the board's draw is
**not** the default salt.  Evidence: DQI `4b572141` drew 0 default-salt errors
and the board scored its tree 33.17029 (= the clean prediction); `141f02ac`
drew 2 and the board scored 33.170350 (= its CLEAN prediction, not the
33.07695 implied by 2 errors); `6f78ecdd` drew 4 and the board scored 33.17067
(= its CLEAN prediction).  ⇒ predict the **clean-draw** GM, and treat the
default-salt number as a lottery draw, not as the score.

**v147 predicted GM, computed from the receipt's measured leg costs with the
clean repetition factor 1.1912604648115832:**
* DQI clean = 1.1912604648115832 × 900² × 316,122.95665039064 =
  **305,033,672,024.33**
* invsqrt = 60,927.57739905387 (37 q, unchanged from v146)
* chemistry = 251,089,557.02151904 (v146 had 251,089,557.46576697; −0.44424793)
⇒ composite **33.17067**, i.e. **+0.00038 GM** over the v146 board score
33.17029, and equal to goodpjw2008's published 33.17067 for the same DQI bytes
with a 0.0426-worse chemistry table.  The band to expect on the five-decimal
board display: **33.17062 … 33.17067** (the same ±0.000045 public-salt band as
v144/v146).  If the board's DQI draw happens to be the default salt's
4-failed-shot draw, the score is 33.00336 instead — that branch has never
been observed publicly for a tree that scored cleanly.

**New measurement facts recorded this wake** (unchanged official verifiers):
* chemistry floor 251,089,557.02151904 (`16b4f5b5`); rivals `b6f06794`
  251,089,557.72428524, `508364c7` 251,090,780.9397702, `e337917c`
  251,089,557.50839654, `14d5cc25` FAIL.
* DQI clean: `6f78ecdd` 305,033,672,024.33 < `1e6787a0` 305,041,576,300.78 <
  `4b572141` 305,041,647,011.3978.
* invsqrt floor 60,927.57739905387 (`bb676b95`), runner-up 60,955.298422
  (`52e8d4e6649b`).

## 2026-11-25 01:2x UTC — v148 prediction

* **Predicted public GM 33.21008** (clean DQI draw), from
  invsqrt 60,927.57739905387 / DQI clean 305,033,672,024.33 /
  chemistry 250,195,979.3541336, using the same REF constants as v147.
* The public board for the same three legs (goodpjw2008 / ozertuu) reads
  **33.2101** ⇒ calibration error expected ≤ 5e-5, inside the public-salt band
  (v144 −0.0000447, v146 −0.0000404).
* If the board draws the default-salt DQI (4 failed shots) the score is
  ≈33.0429; that branch has never been observed for a tree that scored cleanly.
* Chemistry measurement is exact (deterministic, no salt): the three public
  variants and our assembled tree reproduce to 1e-7 relative.

## 2026-11-25 01:53 UTC — v148 ACTUAL

* **v148 public score 33.21011** (ref 58859204), predicted **33.21008**.
  Residual **+0.00003** — the clean-DQI-draw branch was right, and the
  prediction model (invsqrt / DQI / chemistry local PASS values with the
  v147 REF constants) is unbiased to ~3e-5.
* Public-salt band history: v144 −0.0000447, v146 −0.0000404, v148 +0.00003.
  The band is asymmetric-but-tiny: ±5e-5 covers every observed draw.
* Consequence for v149: predicted 33.21174403 ⇒ expected public ≈
  **33.2117–33.2118** (goodpjw2008's identical bytes read 33.21179 on the
  public board, i.e. +4.6e-5 vs our prediction — same order).
* No-silent-day: v148 submitted 01:16 UTC, v147 on 2026-11-23 06:11 UTC
  (>43 h). v149 will be the second submission of the 2026-11-25 UTC day;
  budget after v149 = 3/5.

## 2026-11-25 12:0x UTC — v149 ACTUAL

* **v149 public score 33.21179** (ref 58861394, submitted 2026-11-25
  02:13:04 UTC), predicted **33.21174403**.  Residual **+0.0000459**.
  The bytes are identical to goodpjw2008's public release, which also reads
  33.21179 — a third independent confirmation that the clean-DQI-draw
  prediction model is unbiased.
* Public-salt band history: v144 −0.0000447, v146 −0.0000404, v148 +0.00003,
  v149 +0.0000459.  ±5e-5 covers every observed draw.
* Predictions vs actuals this wake:
  * `brot` 7 → 6 (chem_brot.py): **predicted** −3.5 % score ⇒ +0.40 GM;
    **actual** the official metric FAILS (error_1 4.150, error_2 0.858 Ha vs
    the 0.020 Ha gate).  The prediction was wrong because it ignored the
    20 mHa accuracy gate, which our shipped words sit exactly on.  Lesson:
    any chemistry word change must be scored with `evaluate_words` BEFORE
    costing the loaders.
  * factorisation shape C = 46 → 16 (chem_shape.py): **predicted** T_state
    4550 → 2101 (−18.6 % of T_total, ≈ +2 GM if `lambda_eff` held);
    **actual** untested — the 20 mHa error_2 gate pins C, and changing the
    weights changes the words (⇒ 15 loader rebuilds).  Do not report a score
    for this cell until the metric passes.

## 2026-11-26 01:0x UTC — v150 (goodpjw2008 v21 chemistry) adopted + submitted

* **Prediction:** chemistry score 249,169,842.41339546, T 13,114, lambda_eff
  46.91430370584927 ⇒ GM = 33.21179 × (13166/13114)^(1/3) = **33.25562955**.
  The release's own title claims 33.25564.
* **Actual (local official verifier):** PASS, score 249,169,842.41339546,
  T 13,114, lambda_eff 46.91430370584927, error_1 0.019999999880108168,
  error_2 0.019999999880538476, E_gap 3.914898000017274.
* **Board:** submission ref 58918753 (2026-11-26 01:03 UTC); score pending at
  write time.  Expect 33.25564 ± 5e-5 (public-salt band).
* **Lesson:** the chemistry leg is now a pure adoption race on the goodpjw2008
  line; their version cadence is ~1/day and each version is worth +0.003 to
  +0.044 GM.  Check the queue for their slug every wake.
