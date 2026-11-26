# GOALS — breakthrough goals + leverage map (agent-maintained; rewrite freely)
# Last refresh: 2026-11-23 05:3x UTC (post v146 score 33.17029 + DQI zero-test-cut discovery)
#
# 2026-11-23 05:3x UTC refresh notes
# -------------------------------
# * **The public release lane is now EXHAUSTED at every leg**, all measured:
#   - chemistry: `varianceofx`'s table `16b4f5b5` = **251,089,557.02151904**
#     (beats our `e7f08627` = 251,089,557.46576697 by 0.44424793; the floor);
#   - DQI: `goodpjw2008`'s zero-test-cut `6f78ecdd` = **-9.00 Toffolis/shot**
#     (public LB 33.17067); their own scan rejects the other 62 of 72
#     candidate gates with measured reasons, so the mechanism is closed;
#   - invsqrt: `bb676b95` = 60,927.57739905387 (37 q) is still the public best.
# * **The public board's draw is NOT the default salt.**  alexchilton proved the
#   private board re-runs the verifiers with an unknown salt and that each DQI
#   file's shot draw is hashed from its own bytes; the default-salt verifier
#   number must therefore be calibrated against the board (our biases:
#   -0.00004472 for v144, -0.00004035 for v146).
# * **Frontier (2026-11-23 04:1x UTC board):** #1 `Entangled Team` **33.85279**,
#   #2 `codebeforework` 33.56726, #3 `Two-Qubit Gate` 33.51863; we are **rank
#   214 at 33.17029**.  With v147's DQI + chemistry fixed:
#     match #1  -> invsqrt <= **57,318.1631**
#     beat #2   -> invsqrt <= **58,793.3204**
#   With the 39 q generator build's per-wire cost 1,581.954652990519:
#     Q=38 -> 60,114.28 (GM 33.319567)
#     **Q=37 -> 58,532.32 (GM 33.617079, 2nd place)**
#     **Q=36 -> 56,950.37 (GM 33.925509, 1st place)**
# * **H31 (the evolutionary lane) is now LIVE on Kaggle**: the CodeEvolve
#   framework (inter-co/science-codeevolve, Apache-2.0, vendored unchanged)
#   evolves the *build plan* of the q2026-v154 ISR generator inside a private
#   Kaggle kernel, scored by the unchanged official invsqrt verifier.
#   3 islands run as PARALLEL processes and the build is single-threaded
#   (644 s on 2 cores), so the search really does use Kaggle's 12 cores.
# ⇒ **The inverse-square-root leg is the only meaningful lever** (one wire =
#   ten DQI wires), and it must come from the 39 q generator lineage (H24) or
#   from the q2026-v154 ISR generator (H30/H31).


## Leverage map (cost-formula anatomy, GM per unit)
Reference values (maoxin123's public notebook, `REFERENCE` dict):
`invsqrt 2,076,774.233715 · dqi 24,439,463,583,672.93 · dfthcsos 3,355,599,588.3155375`
`GM = (Π REF_i / cost_i)^(1/3)`; the marginal value of a *fractional* cost cut in one
leg is `dGM = GM/3 × d(cost)/cost`.

**CORRECTION 2026-11-19:** the old "+0.077 GM/qubit" for invsqrt was 2.8× too small
(it was computed with the wrong marginal formula). The exact numbers:

| move | dGM |
|---|---|
| **invsqrt: −1 wire (Q44→Q43)** | **+0.2168** |
| invsqrt: −1 wire (Q46→Q45) | +0.2042 |
| invsqrt: −1 wire (Q48→Q47) | +0.1928 |
| DQI: −1 wire (Q890→Q889) | +0.0211 |
| DQI: width → 840 hard floor | +1.1075 |
| invsqrt: −1% Toffoli at Q44 | +0.0939 |
| invsqrt: −1 rotation at Q44 | ~+0.05 |

⇒ **one invsqrt wire is worth TEN DQI wires.** The invsqrt leg is the highest-leverage
known lever by a wide margin.

| Leg | Score formula | Dominant factor | Marginal value |
|-----|--------------|-----------------|----------------|
| invsqrt | Q × (T_mean + T/4 + n_rot·price/4) | Q (linear) | **+0.2168 GM/wire @Q44**; +0.0939 per 1% Toffoli |
| DQI | rep × Q² × T_mean | **Q² (quadratic)** | +0.0211 GM/wire @Q890; +1.1075 total to the Q840 floor |
| chem | λ_eff × (T + qubit terms) | analytic-pinned | ~0 public headroom |

⇒ WIDTH is the currency of this competition, and **invsqrt width is the cheapest
currency** (one wire = ten DQI wires). Toffoli micro-cuts are dust by comparison.

## Goals (ranked)
G1 (breakthrough): Reduce DQI width below 890 — even 850 = +0.26 GM, 750 = +1.0 GM.
   Success: one verified-narrower dqi.kmb. Falsified if live-span anatomy shows peak ≈ declared width
   AND no packing structure exists (then record and re-aim).
   **RE-RANKED 2026-11-19 (H7, source-read):** the verifier WRITES the syndromes into the circuit's
   S0..S_{n-1} registers and requires them restored ⇒ **Q ≥ 70·12 = 840 is a hard floor**; our 890 =
   840 input wires + 50 ancillas ⇒ the width prize is capped at +1.1 GM, and the flat-wide anatomy (H1)
   is explained (the input wires are held for the whole circuit).  ⇒ the DQI lever is **T (mean
   Toffolis, 367,789)**, which needs a DQI generator that is not public.  G1 becomes: reduce ancillas
   50→0 or cut T, both generator-level.
G2 (stepping stone, elevated): invsqrt Q45/43 via minand_sat — direct value +0.08–0.16 GM, but the
   retirement/endpoint machinery is the SCAFFOLD for G1 (Euler→Navier–Stokes pattern). Build it once,
   transfer the method.
   **RE-RANKED 2026-11-19:** the Q45 stack now reaches the TAIL (every phase fits 45 except the T2
   donor-block replay, which needs 46).  But the *competitive* threshold is **Q42** (42×1743.42 = 73,206
   < our public 74,560.91) — Q45 alone is 78,454 and is NOT a submission.  The tail needs a native
   re-derivation with ≤5 simultaneous scratch wires (H2 kill criterion).  Method value only until Q43/Q42.
G3: Identify the top-2 mechanism (recon + inference from cadence/score jumps). Even a partial answer
   re-ranks everything. Attack from multiple framings simultaneously (their A/B vs C/D variant fan-out).
G4 (standing): Hold best-public-tree parity — adopt every better public leg within the same day.
G5 (NEW, elevated): Evolutionary generator search (H6, AlphaEvolve-style) — evolve the GENERATOR
   against the exact score formula with an automated evaluator, starting on the cheap invsqrt leg
   (74 s rebuild). This is the only lane that attacks the generator-level gap the top-2 teams keep
   private, and it is the only lane whose progress is measured rather than guessed.
   Success metric: a variant that scores strictly better than baseline, reproducibly.
   Precondition: the evaluator must be cheap and deterministic — build the population store
   (work/evo/population.json) BEFORE generating variants, or the search dies of amnesia.
   **STATUS 2026-11-19: evaluator LIVE and reproducible** (baseline 80,565.24511023414 reproduced
   exactly; ~10 s/variant; population v001–v015 with scores and artifact pointers).  Search space is
   now MEASURED, not guessed: work/evo/WIDTH_MAP.md (per-stage live ledger + the four killed levers:
   free-list reuse already in kickmix, loader work_cap is transient-only, divider is not the binding
   phase, no Q43/44/45 exists in the tree).  Next generation must target the *cost* ledger at Q46/Q45
   (need −7% Toffolis at Q46 to beat the public 44q) or a native tail re-derivation.

## Non-goals (with reasons)
- Public-LB rank vanity: the $150k pays on the PRIVATE split at 2027-01-20; only tree quality at freeze
  matters. Rank is a sensor, not a target.
- Toffoli-count micro-squeezes < +0.005 GM: dust; do not spend slots or wakes on them.
- Re-running any KILLED experiment (see RESEARCH_STATE.md).


## Leverage map refreshed 2026-11-19 (post v133 = 28.23441; measured, not guessed)

| move | GM | note |
|---|---|---|
| invsqrt −1 wire @Q44 | **+0.2168** | 1 wire ≈ TEN DQI wires (2.8× correction already applied) |
| invsqrt −1 Toffoli | +0.00695 | cost unit = 1.264e-4 GM |
| invsqrt −1 cost unit | +1.264e-4 | the unit the public releases trade in (v133: −21.97) |
| DQI −1 wire @Q890 | +0.0211 | hard floor Q ≥ 840 (840 input + 50 ancilla) |
| DQI −1 Toffoli | +2.6e-5 | needs a NEW algorithm (varianceofx: M 7,668 → 5,462) |
| chem −1 Toffoli | +0.000640 | T = angles_toffoli + 6662 heuristic |
| chem −1 qubit @Q427 | +0.02204 | Q = 84 + J×8 + max(303, angles_temp); J steps cost 8 wires each |
| chem λ_eff −1e-7 | +0.0000001 | λ_eff is pinned by the npz (46.9215626) |

**Current best public mix (v133):** invsqrt ecf908fec987b61a 74,383.698758 · dqi 15a4b740 345,256,821,433.9815
· chem npz 6ef06081 294,642,169.5117 ⇒ GM **28.23441**.  Leader #1 31.74002 ⇒ gap **+3.51 GM**, and
varianceofx's measurement attributes the whole gap to DQI T.

## Leverage map refreshed 2026-11-21 (post v135 = 33.07536)

| move | GM | why |
|---|---|---|
| **invsqrt -1 qubit @ 37 q** | **+0.30** | cost = Q x T_eq; the 44->37 step bought +4.8 GM |
| invsqrt -1 Toffoli-equivalent | +0.0002 | 1/1647 of the cost |
| dqi -1 qubit @ 900 q | +0.00074 | cost = rep x Q^2 x T |
| dqi -1 Toffoli | +0.0000011 | needs a new decoder algorithm |
| chem -1 qubit @ 405 q | +0.00082 | cost = lambda x T x Q |
| chem -1 Toffoli | +0.000025 | T 13,322 = 6,822 loaders + 6,500 heuristic |
| chem lambda_eff -1e-7 | +0.0000006 | refit-only, ~0.1 % total |

**Frontier:** #1 Z3C1oherence 33.34845, #2 No Bodies 33.10223, #3 Nic Barthelemy
33.10018, #4 Kotaro Terada 33.07974, #5 goodpjw2008 33.07404.  Public best tree
33.07536 (v135, ours).  Gap to #1: **+0.27 GM**, one invsqrt qubit or ~2.5 % on
one leg.

**Generator sources now public (the real capability unlock):**
- `tonylica/quantum-ai-32-85306-task-generators`: invsqrt (`build.py`, `carry.py`,
  `divider.py`, `lend29.py`, `v50/apply_best.py`, `base_v90.kmx`), chemistry
  (`build.py` + editable `W`/`H2_I`/`Hsym`/`tree_edges`/`angle_words`), DQI
  (decoder stages + selector).
- `prvsiyan/vqcc-verified-best-of-circuits-1106a`: refit code (`code/refit_grg.py`),
  26 versions of salt-verified members, README with measured costs.
- `alexchilton/33-08-lb-which-circuits-survive-private-salt`: the 8-salt table and
  the per-circuit price history.

## Leverage map refreshed 2026-11-21 (post v136 = 33.10022)

| move | dGM | comment |
|---|---:|---|
| **invsqrt -1 qubit @ 37 q** | **+0.2984** | the single biggest lever; 44->37 q once bought +4.8 GM |
| invsqrt -1 rotation (of 33) | +0.0487 | rotations cost 29.07 T each at eps 1.888e-13 |
| invsqrt -1 Toffoli-equivalent | +0.00670 | T_eq = 1,647.44 |
| **dqi -1 qubit @ 900 q** | **+0.0245** | cost = R x Q^2 x T, so qubits are squared |
| dqi -1 Toffoli (of 316,131) | +0.0000349 | needs an algorithmic decoder cut |
| dqi private-salt insurance (no public cost) | up to +0.0507 expected | lower per-shot failure rate at equal clean cost |
| **chem -1 qubit @ 405 q** | **+0.0272** | |
| chem -1 Toffoli (of 13,292) | +0.00083 | loaders are 2 x 3,396 of the 13,292 |
| chem -1 % T | +0.110 | |

**Frontier:** #1 Z3C1oherence 33.34845, #2 Kotaro Terada 33.10520,
#3 No Bodies 33.10223, #4-6 at 33.10018 (boristown's tree = our v136),
#7 Dan Pavlides 33.09354.  Our rows: v135 33.07531 (ref 58645864),
v136 33.10022 (ref 58646682).  Gap to #1: **0.24823**.

**What the public data says is exhausted (measured this wake):**
- chemistry loaders: at their public floor (T 13,292; the unconstrained public
  per-block minimum would be 13,286 but those bytes break the chemistry;
  `work/recon/loader_floor_2026-11-21.md`).
- chemistry lambda_eff: at its floor (46.918298 vs 46.916000 best known).
- invsqrt: every one of the 37 wires is live over ~80 % of the 60,790-gate
  stream; no pair can be merged without new synthesis.

**What is NOT exhausted (the ranked goals):**
1. **DQI qubit count 900 -> 890** (+0.245 GM) — the public DQI generator ships
   editable KMX stages (`dqi/decoder/*.kmx.xz`, `dqi/d16/*`, `dqi/selector.py`,
   `dqi/stages.json`); the four D16 arithmetic sites run sequentially and may
   be able to share their temporary wires.
2. **invsqrt 37 -> 36 q** (+0.298 GM) — needs new synthesis; the public
   generator (`tonylica/.../invsqrt/`) has the carry-borrow machinery
   (`lend29.py` transplants a free wire) that produced the last two steps.
3. **DQI private-salt insurance** (+0.05 expected, invisible publicly).

## Leverage map refreshed 2026-11-21 02:50 UTC (post v136 = 33.10022)

| move | GM delta | note |
|---|---:|---|
| **invsqrt -1 qubit @37 q** | **+0.2984** | closes the whole 0.248 gap by itself |
| invsqrt -1 rotation | +0.0487 | 33 rotations cost 959 T = 240 T_eq (14.6 % of the leg) |
| invsqrt -1 Toffoli-equivalent | +0.00670 | 1,406.31 CCX + 8.50 T + 33 rotations |
| **chem -1 % of T (13,292)** | **+0.110** | loaders 6,792 (2 x 3,396) + heuristic 6,500 |
| chem -1 qubit @405 q | +0.0272 | 118 persistent + 287 temporary |
| chem -1 Toffoli | +0.00083 | public loader floor reached at T = 13,292 |
| dqi -1 qubit @900 q | +0.0245 | cost = R(eps) Q^2 T, R fixed at 1.19126 for a clean draw |
| dqi -1 % of T (316,131) | +0.110 | |
| dqi -1 Toffoli | +0.0000349 | |

**Frontier:** #1 Z3C1oherence 33.34845, #2 Kotaro Terada 33.10520,
#3 No Bodies 33.10223, #4-6 at 33.10018 (boristown's tree = our v136),
#7 Dan Pavlides 33.09354.  Our rows: v135 33.07531, v136 33.10022 (pending).

**Equivalent targets for the 0.24823 gap:** 1 invsqrt qubit | 37 invsqrt
Toffolis | 5.1 invsqrt rotations | 2.26 % chem T | 300 chem Toffolis |
8.5 chem qubits | 10.1 DQI qubits | 2.5 % DQI T.

**Lanes closed this wake (evidence on disk):**
- chemistry loader re-splice: floor is T = 13,292 with public bytes; the
  unconstrained per-k minimum (3,393/pass) is NOT compatible with the base npz
  (4 swap candidates all FAIL the official verifier) — work/recon/loader_floor_2026-11-21.md
- loader ANF rewrite: dead, the 35 output bits are dense functions of the
  11-bit address (~670 ANF monomials each) — same file
- salt risk on the DQI: quantified at -0.05 GM expected, not zero —
  work/recon/dqi_salt_probe_2026-11-21.md

## Leverage map refreshed 2026-11-22 00:44 UTC (post v139, predicted 33.13881039)

| move | GM delta / target | note |
|---|---:|---|
| **public-release adoption v138 -> v139** | **+0.03690853 realized locally** | Leo T7421 chemistry cost 251,692,077.714951; submitted ref 58694635 |
| **invsqrt generator 39 q -> 38 q** | **+0.11680 → GM 33.255613** | predicted cost 60,114; **insufficient for the new frontier** |
| **invsqrt generator 39 q -> 37 q** | **+0.41375 → GM 33.552564** | predicted cost 58,532; beats current leader 33.51568 by **+0.03688** |
| invsqrt -1 qubit @37 q (our current lineage) | +0.2984 | DEAD: 36 is the spec floor for this lineage (all 37 wires live ~80 % of the stream) |
| invsqrt -1 rotation | +0.0487 | DEAD: the 33 angles are minimax-optimal (H26), the basis is full rank |
| invsqrt +1 salt-invariant basis function | +0.02..+0.05 | DEAD: measured margin gain is x1.0820, below the x2.96 break-even |
| chem -1 % of T (13,244) | +0.110 | public table/loader family is now at Leo T7421's measured frontier |
| chem -1 qubit @405 q | +0.0273 | DEAD: Q = persistent + max(heuristic_temp, loader_temp); heuristic 287 > loader 82 |
| dqi -1 qubit @900 q | +0.0246 | DEAD (H22): 900 wires live to the last stage, 0 disjoint pairs |
| dqi -1 % of T (316,131) | +0.110 | the only editable quantum part holds 850 of 318,972 Toffolis (0.27 %) |
| dqi salt insurance (cleaner draw) | +0.05 expected | OPEN (H23): require equal clean cost and a demonstrably lower multi-salt failure rate |

**Frontier:** #1 `Schrödinger’s cat lived` / `pjmathematician` 33.51568, #2
`Syed Asad Ali` 33.46157, #3 `codebeforework` 33.36663, #4 `Z³C¹oherence`
33.34845.  Our latest submitted tree is v139, predicted **33.13881039** (ref
58694635, pending at this snapshot); v138 scored 33.10186.  The predicted gap
to #1 is **0.37686961 GM**.

**Equivalent inverse-sqrt targets with v139's public DQI/chemistry held
fixed:** <=58,725.4560 matches #1, <=59,010.8080 matches #2, <=59,515.9632
matches #3, and <=59,613.3522 matches #4.  H24's 38 q/60,114 build misses
all four; its 37 q/58,532 build clears #1.

**Lanes closed this wake (evidence on disk):**
- invsqrt angle refit (H26): the fit is minimax-optimal and the margin ceiling
  is +0.13 GM — `work/recon/invsqrt_refit_2026-11-21.md`
- extra salt-invariant basis function (H25): x1.0820 measured margin gain
  versus x2.96 break-even — `work/recon/invsqrt_basis_probe_2026-11-21.md`
- DQI qubit cut (H22): 900 wires live to the last stage, 0 disjoint pairs
- rotation merge: 0 mergeable pairs under the correct commutation rule
- public chemistry permutations: Leo T7421's 251,692,077.714951 is the best
  distinct verified chemistry cost found; every other inspected family is
  1,713.08828307 or more cost units worse

## Current operating point — 2026-11-22 00:44 UTC

**Latest submitted tree:** v139, submission `58694635`, predicted GM
**33.13881038958233** (pending).  v138/ref `58659698` scored 33.10186 and
v137/ref `58658870` scored 33.10185.  The leader is 33.51568, so the
predicted remaining gap is **0.37686961 GM**.  One submission has been used
today; **four slots remain**.

### Ranked live goals

1. **H24 — reduce the editable 39 q invsqrt generator to a semantically exact
   37 q physical allocation (+0.41375 GM).**  This is the only active
   mechanism lane with enough upside to clear the current frontier.  A 38 q
   intermediate remains useful for validation, but the 38 q score 33.255613
   is already below #4.  The affine scan is complete: q29's lend relation is
   real, but the carry block simultaneously holds
   q29/q30/q31/q32/q33/q36/q37, so affine recoverability alone does **not**
   remove a physical wire.  Success requires a Boolean carry-chain rewrite or
   op-level allocation with a provably safe shared physical wire.
2. **H23 — DQI private-salt insurance (expected +0.05 GM, invisible on the
   public board).**  Reopen only when a public DQI has the same clean cost and
   a demonstrably lower multi-salt failure rate.
3. **H5 — public-release adoption.**  Passive radar remains mandatory at every
   wake.  v139 was adopted only after an exact 18-file SHA table, unchanged
   official verifiers PASS in moat-lab v53, an independent local chemistry
   PASS, and a full 25-row semantic queue adjudication.

### Guardrail for the next submission

A candidate is eligible only after all of the following hold:

1. exact all-input simulation agrees with the 39 q generator on phase,
   restored x-register, and clean scratch, including forced/random HMR
   outcome streams;
2. the rebuilt circuit compiles to at most 37 physical qubits (38 q is a
   research milestone, not a frontier submission);
3. the unchanged official invsqrt verifier returns PASS with cost <=58,532
   (and <=58,725.4560 to match board #1 with the public other legs);
4. the complete 18-file tree passes `harness/submit_gate.sh` with a static
   SHA receipt and an official in-kernel verifier receipt;
5. the tree bytes are distinct from v139 and every prior submission.

Evidence: `work/recon/public_harvest_2026-11-22_v139.md`,
`work/recon/invsqrt_basis_probe_2026-11-21.md`, and
`work/recon/invsqrt_lend_scan_2026-11-21.md`.


### 2026-11-23 06:2x UTC refresh (post-v147 submission + apache v173 full-manifest audit)

**Lever map after the audit — the board is now provably at its public floor:**

| leg | public floor (verifier-measured) | owner | our status |
|---|---|---|---|
| invsqrt | 60,927.57739905387 (37 q, `bb676b95f94c`) | varianceofx | **= ours**; runner-up 60,955.298422 ⇒ no public headroom |
| DQI | clean 305,033,672,024 (`6f78ecdd`, implied T 316,122.9567) | goodpjw2008 | **= ours**; best rival `1e6787a0` 305,041,576,300.78 (−7.9M behind us) |
| chemistry | 251,089,557.02151906 (table `81dbfe56d339` = `16b4f5b5`) | apache v173 manifest | **= ours** (their number vs our local differ by 2e-8) |

⇒ **Every public-release lane is closed at the floor.**  The only remaining
leverage in the whole competition is the **inverse-square-root physical width**
(one wire ≈ 1,582 cost units ≈ 0.28 GM at 37 q; 36 q ≈ 1st place).

**Ranked goals now:**

1. **H31 (CodeEvolve evolutionary width search, RUNNING on Kaggle since
   05:06 UTC, 8 h budget).**  The only automated route to a sub-39 q build.
   Harvest `search_summary.json` / `best_program.py` / `best_invsqrt.kmb` when
   the kernel completes; re-verify the best plan locally with the unchanged
   official verifier before any use.
2. **H32 (NEW — invsqrt `square_root` stage, "little-explored" in the public
   closure ledger; "other constructions of the consuming square root are
   untried").**  Cheap discriminating test: does the archived q2026-v154 ISR
   bundle contain a *different* square-root construction (the 44/46-qubit
   line's) that can be swapped in, and what does it cost in wires?  Kill
   criterion: if the bundle has only one square-root construction and its
   swap points are the same width, close it.
3. **H33 (NEW — invsqrt `table` stage, "active" on the 44-qubit line).**
   64-row table resyntheses are a public live lane; our H1 blocker is exactly
   the table program's 7-input/6-temporary schedule.  Test: take the public
   44-qubit table resynthesis *source* (if the bundle ships it) and rebuild the
   H1 table with one more input wire.
4. **Public-release radar (always on).**  8 rows adjudicated this wake, all by
   measurement; the apache archive is now harvestable file-by-file, which
   removes the last blind spot in the dataset channel.

**Guardrail unchanged and still binding:** a candidate is eligible only with an
exact 18-file SHA table + an unchanged-official-verifier in-kernel receipt, and
it must beat the incumbent on the *measured* leg costs.  No DQI member without
an official verifier receipt; no chemistry table without a local official PASS.

---

## 2026-11-25 01:2x UTC — leverage map refresh (post v148)

**Scored best:** v148 SUBMITTED (ref 58859204), predicted **33.21008**; previous
scored v147 = 33.17067.  The jump came entirely from the chemistry leg
(−893,577.67 cost units, +0.0395 GM) and is the first move in three wakes.

| leg | shipped | measured score | remaining public/known headroom | GM per unit |
|---|---|---|---|---|
| invsqrt | `bb676b95` 37 q | 60,927.577399 | Q=36 ⇒ GM +0.31; public floor on the 37-q line | largest |
| DQI | `6f78ecdd` 900 q | 305.03e9 clean | 5.78 % conditional skip; 267,934 hard-floor Toffolis; 900→882 q ⇒ +0.45 GM | largest |
| chemistry | `573d10be` + 3,334-T loaders | 250,195,979.354 | H39 (per-pass max discovery), H40 (weight refit ≈ +0.003) | small |

**Ranked goals**
1. **DQI width / skip-rate** — the only ≥+0.1 GM lever left.  H22 (width lane)
   closed on 0 disjoint pairs; the open route is a new stage design (H32-m6 is
   stage-blocked on `T = y >> 9`) or converting depth-0 Toffolis into
   conditional work (H38 proved measure-first cannot do it).
2. **invsqrt Q=37→36** — needs a live-wire count of 36 at H1; every relabeller
   confirms peak busy 37.  Needs a *different square-root construction* (H32).
3. **H39 chemistry per-pass max** — new, cheap: the 3,334 figure is a max over
   the *invoked* banks, and 5 loaders are dead weight.  −10 T/pass ≈ −0.007 GM.
4. **H40 chemistry weight refit at fixed words** — ceiling +0.003 GM (NR-0207).
5. **Public-release radar** — 88-row queue; 21 rows adjudicated by measurement
   this wake; nothing beats v148.

## 2026-11-25 12:0x UTC — leverage refresh after v149 (33.21179)

The chemistry score is `lambda_eff * T_total * Q_total`, and with the shipped
tree the three factors are now *fully* accounted for:

| component | value | lever? |
|---|---:|---|
| `lambda_eff` | 46.914325 | pinned: error_1 = error_2 = 20.000 mHa and E_gap = 3.914898 sit exactly on the gates (H43 killed the `brot` trade) |
| ANGLE Toffolis (both passes) | 6666 = 2 × 3333 | **the live chemistry lever** — 5 old loaders still cost 240–245 each |
| state-prep heuristic | 4550 | C-sensitive (C=16 → 2101) but blocked: C is pinned by error_2 and any change rebuilds all 15 loaders (H44) |
| Givens rotations | 1950 = 2·75·(2·7−1) | fixed by N=76 and brot=7 |
| `Q_total` | 405 = 83 persistent + 35 word regs + 287 inner temp | angles_temp = 82 is below inner_temp = 287, so **shaving loader ancillas buys nothing in Q** |

| leg | shipped | measured score | remaining public/known headroom | GM per unit |
|---|---|---:|---|---|
| invsqrt | `bb676b95` 37 q | 60,927.577399 | Q=36 ⇒ GM +0.31; needs a new square-root construction (H32/H41) | largest single lever |
| DQI | `6f78ecdd` 900 q | 305.03e9 clean | public DQI frontier closed (38 files scanned); 900→882 q ⇒ +0.45 GM | largest total, blocked |
| chemistry | v149 loaders + `573d10be` | 250,157,973.261 | **5 loaders at 240–245 → 215 would be +0.21 GM** (H42); H44 (shape C) and H40 (refit +0.003) | now the best-understood lever |

**Ranked goals**

1. **H42 — chemistry plan search for k = 0,1,5,7,11.** The plan machinery is now
   exact and machine-checked (`chem_plan.py` / `chem_rec.py` / `chem_struct.py`),
   the targets are reachable in principle (all 15 batches have the same
   dimension profile), and goodpjw's own 123–132 products per loader are far
   above the rank bound (≈8 products per output) — so the scheme is not
   exhausted.  Needs a *structured* product search; a random one is dead on
   arrival (probability ≈ 2^-905 per product).
2. **H41 / H32 — invsqrt 37 → 36 q** (+0.307 GM).  Unchanged; 185 leader tools
   confirm 37 is the peak busy width of the published construction.
3. **H44 — factorization shape C** (potentially +2 GM, but only after H42 can
   rebuild the loaders for a new table).
4. **DQI width / skip-rate** (+0.45 GM) — H22 closed, H32-m6 blocked on
   `T = y >> 9`.
5. **H40 — weight refit at fixed words** (+0.003 GM ceiling, CPU-only).
6. **Public-release radar** — the queue tool's kernel/dataset bug is fixed; the
   19 wrongly-closed kernel rows are being re-adjudicated by measurement.

---

# 2026-11-26 01:1x UTC refresh (post v150 = 33.25564, goodpjw v21 chemistry)

**Frontier moved by adoption, not by our own build:** the public line
(goodpjw2008) reached 33.25564 and we adopted it the same wake (v150, ref
58918753).  Board top is still far ahead (Entangled Team 33.85279); the
harvestable public frontier is the 33.25xxx line.

**Leverage map (updated at GM 33.25564, chemistry T 13,114):**

| lever | unit | GM per unit | note |
|---|---|---|---|
| chemistry | 1 loader-Toffoli | **+0.00169** | loaders run twice; 5 group-start loaders at 240–245 vs 205–214 |
| chemistry | 1 heuristic/state-prep T | +0.000845 | 6,500 T, C-sensitive, blocked by error_2 |
| invsqrt | 1 qubit (37→36) | **+0.31** | unchanged construction needed |
| invsqrt | 1 Toffoli | +0.0079 | |
| DQI | 1 qubit (900→882) | +0.45 | blocked |
| DQI | 1 Toffoli | +3.5e-5 | |

**Ranked goals**

1. **H48 — group-start chemistry loaders k = 0,1,5,7,11.**  Now the only
   chemistry headroom: 5 × ~28 loader-Toffolis = **+0.24 GM**.  We have
   goodpjw's decoded plan format (PACK blob + `build_loader`/`build_window`),
   the exact dead-word budget per batch (k11 = 240, k7 = 131; k0 = 5, k1 = 67,
   k5 = 60), and a measured structural difference: wired = 82 features
   (68 bank-only + 14 low/mixed) + 123–132 products; group-start = 144
   features (5 bank-only + 139 low/mixed) + 96 products.  Attack k11 first;
   pre-registered: nP ≤ 157 within one build day or the 82-feature approach for
   group starts is killed.
2. **H41 / H32 — invsqrt 37 → 36 q** (+0.31 GM).  Unchanged.
3. **H44 — factorization shape C** (+ up to 2 GM) — blocked on the 20 mHa gate.
4. **DQI width / skip-rate** (+0.45 GM) — blocked.
5. **H40 — weight refit** (≤ +0.003 GM).
6. **Public-release radar** — v150 came straight out of the queue within one
   wake; keep 4 detached adjudicators running every wake.
