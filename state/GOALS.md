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
