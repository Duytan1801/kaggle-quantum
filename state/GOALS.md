# GOALS — breakthrough goals + leverage map (agent-maintained; rewrite freely)
# Last refresh: 2026-11-19 (post v132 = 28.23163; the public-release radar was repaired)

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

## Leverage map refreshed 2026-11-21 12:25 UTC (post H26 kill, post v136 = 33.10018)

| move | GM delta | note |
|---|---:|---|
| **invsqrt generator 39 q -> 38 q** | **+0.153** | generator build 39 q / 24,387 instr / 1,452 Toffoli-like = 61,696; at 38 q it would be 60,114 (GM 33.253) |
| **invsqrt generator 39 q -> 37 q** | **+0.452** | 58,532 -> GM 33.5518, BEATS the board #1 by 0.20 |
| invsqrt -1 qubit @37 q (our lineage) | +0.2984 | DEAD: 36 is the spec floor for this lineage (all 37 wires live ~80 % of the stream) |
| invsqrt -1 rotation | +0.0487 | **DEAD**: the 33 angles are minimax-optimal (H26), the basis is full rank |
| invsqrt +1 salt-invariant basis function | +0.02..+0.05 | only if the margin improves > x2.96; ceiling for the whole leg is +0.13 GM |
| chem -1 % of T (13,292) | +0.110 | DEAD: loaders are at the public floor (T 13,292), Q is verifier-pinned |
| chem -1 qubit @405 q | +0.0272 | DEAD: Q = persistent + max(heuristic_temp, loader_temp); heuristic 287 > loader 82 |
| dqi -1 qubit @900 q | +0.0245 | **DEAD (H22)**: 900 wires simultaneously live to the last stage, 0 disjoint pairs |
| dqi -1 % of T (316,131) | +0.110 | the only editable quantum part holds 850 of 318,972 Toffolis (0.27 %) |
| dqi salt insurance (cleaner draw) | +0.05 expected | OPEN (H23): a public DQI with fewer failed shots is strictly better at equal clean cost |

**Frontier:** #1 Z3C1oherence 33.34845, #2 codebeforework 33.12761, #3 No Bodies
33.11359, #4 Almond Labs 33.10687, #5 Frost Cerberus 33.10523, #6 VKAS 33.10522;
~40 teams sit at 33.10020-33.10032 (the boristown tree family).  Our row: v136
**33.10018** (predicted 33.100221 — the board rounds to 5 decimals), rank ~42.

**Equivalent targets for the 0.24827 gap:** 1 invsqrt qubit in the GENERATOR
lineage (38 q) | 2 generator qubits (37 q) | 2.26 % chem T | 10.1 DQI qubits |
2.5 % DQI T | 5.1 invsqrt rotations.

**Lanes closed this wake (evidence on disk):**
- invsqrt angle refit (H26): the fit is minimax-optimal and the margin ceiling
  is +0.13 GM — work/recon/invsqrt_refit_2026-11-21.md
- DQI qubit cut (H22): 900 wires live to the last stage, 0 disjoint pairs
- rotation merge: 0 mergeable pairs under the correct commutation rule
- chemistry: Q verifier-pinned, T at the public loader floor
