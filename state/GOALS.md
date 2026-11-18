# GOALS — breakthrough goals + leverage map (agent-maintained; rewrite freely)
# Last refresh: 2026-11-18 (post v131 = 28.18084; public harvest complete)

## Leverage map (cost-formula anatomy, GM per unit)
| Leg | Score formula | Dominant factor | Marginal value |
|-----|--------------|-----------------|----------------|
| invsqrt | Q × (T_mean + T/4 + n_rot·price/4) | Q | +0.077 GM/qubit; rotations ~+0.05 each |
| DQI | rep × Q² × T_mean | **Q² (quadratic)** | +0.021 GM/qubit; +2.6e-5 GM/toffoli |
| chem | λ_eff × (T + qubit terms) | analytic-pinned | ~0 public headroom |

⇒ WIDTH is the currency of this competition. Toffoli micro-cuts are dust.

## Goals (ranked)
G1 (breakthrough): Reduce DQI width below 890 — even 850 = +0.26 GM, 750 = +1.0 GM.
   Success: one verified-narrower dqi.kmb. Falsified if live-span anatomy shows peak ≈ declared width
   AND no packing structure exists (then record and re-aim).
G2 (stepping stone, elevated): invsqrt Q45/43 via minand_sat — direct value +0.08–0.16 GM, but the
   retirement/endpoint machinery is the SCAFFOLD for G1 (Euler→Navier–Stokes pattern). Build it once,
   transfer the method.
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

## Non-goals (with reasons)
- Public-LB rank vanity: the $150k pays on the PRIVATE split at 2027-01-20; only tree quality at freeze
  matters. Rank is a sensor, not a target.
- Toffoli-count micro-squeezes < +0.005 GM: dust; do not spend slots or wakes on them.
- Re-running any KILLED experiment (see RESEARCH_STATE.md).
