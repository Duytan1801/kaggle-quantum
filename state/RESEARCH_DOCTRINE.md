# RESEARCH DOCTRINE — patterns distilled from OpenAI / Anthropic / Google discovery systems
# Sources: anthropic.com/engineering/multi-agent-research-system (Jun 2025),
# openai.com/index/introducing-deep-research (Feb 2025), Google AI co-scientist pattern (Feb 2025).
# Mapped to the QCC campaign. The wake prompt + RESEARCH_STATE.md enforce the operational rules.

## What their systems actually do (evidence, not folklore)
- **Anthropic (Research)**: orchestrator spawns parallel subagents with non-overlapping mandates;
  subagents write artifacts to files and return pointers ("game of telephone" avoidance); effort is
  SCALED TO QUERY CLASS with explicit budgets (1 agent/3–10 calls for facts, 10+ subagents for hard
  problems); "start wide, then narrow"; token spend explains 80% of search-performance variance —
  COVERAGE, not cleverness, is the bottleneck; evaluate end-states, not process; errors compound →
  checkpoint + resume.
- **OpenAI (Deep Research)**: learned multi-step trajectories with BACKTRACKING on real-time evidence;
  "the ability to synthesize knowledge is a prerequisite for creating new knowledge"; known weakness:
  confidence calibration — remedy = record predictions vs outcomes.
- **Google (AI co-scientist)**: hypothesis GENERATION → pairwise tournament ranking (Elo) → evolve
  (merge/children) → citation-grounded deep-verify → human review. Tournaments beat single-shot ranking
  because pairwise comparisons surface relative strength better than absolute scores.

## Rules adopted here (mapped to our machinery)
1. **Pre-registration**: before running any discriminating test, WRITE the kill criterion and the
   success criterion into the hypothesis entry FIRST (RESEARCH_STATE.md). No post-hoc moves.
   (Fixes motivated reasoning + makes kills permanent and fair.)
2. **Breadth-first fan-out on strategy cycles**: a Strategy cycle spawns 2–4 parallel subagents
   (explore/general) with NON-OVERLAPPING mandates (e.g. one: top-team forensics; one: unmined public
   corpora; one: external techniques/papers; one: verifier-internal mechanisms). Each writes findings
   to its own file under work/recon/ and returns only a pointer + 5-line summary. Then the lead
   synthesizes into new hypotheses.
3. **Effort budgets per class** (explicit, avoids both circling and over-investment):
   - PROBE ≤ 30 min local (counts, scans, formula checks) — any hypothesis must start here.
   - BUILD ≤ 1 day (kernels, rewrites, full verifies).
   - SPRINT (days) only for CONFIRMED mechanisms with expected GM ≥ +0.05.
   No SPRINT without a CONFIRMED mechanism. No PROBE repeated twice.
4. **Tournament re-rank**: at every Strategy cycle, pairwise-compare adjacent hypotheses in the queue
   ("would I rather spend the next 2 h on A or B?") and reorder. Replaces the static GM/effort ratio.
5. **End-state evaluation**: a hypothesis turn is done when its STATE changed (KILLED with evidence,
   CONFIRMED with artifact, or refined with a better test) — not when time is spent.
6. **Calibration log**: every adopted/submitted prediction vs actual score goes in
   work/CALIBRATION.md (predicted vs scored). We have this data in MOAT_LOOP.md; the log formalizes
   prediction quality tracking (OpenAI's named weakness).
7. **Coverage over depth for generation**: when generating hypotheses, prefer breadth (many cheap
   probes across distinct mechanisms) over depth (one lane polished). The 80%-variance lesson.
8. **Wide-then-narrow queries**: recon passes start broad ("what mechanisms exist at all?") then
   narrow; never start with a hyper-specific query that returns nothing.
9. **Artifacts over narration**: all findings land as files (work/recon/, RESEARCH.md sections) with
   shas/paths/commands — reproducible, and safe against context compaction.
10. **Variant fan-out** (Navier–Stokes lesson, Sep 2026): big hypotheses are attacked from MULTIPLE
    framings simultaneously — e.g. for a width claim: (a) compress the existing file, (b) rebuild the
    generator at lower width, (c) hunt slack in conditionals/bits, (d) alternate public constructions.
    Don't bet on one interpretation of an open problem; farm all of them.
11. **Stepping-stone rule**: maintain an explicit "easier adjacent problem" ladder. Solve the small
    cousin FIRST, then re-attack the big problem prompted with the smaller solution as scaffold
    (their Euler→Navier–Stokes move). Concretely here: the invsqrt width machinery (H2) is the
    stepping stone to the DQI width prize (H1) — its value is the transferable machinery, not its
    direct +0.08 GM.
12. **Cross-pollination**: in Strategy cycles, consolidate each recon group's intermediate results
    into prompts/inputs for the OTHER groups (their Codex consolidation step). Groups must feed
    each other, not run siloed.
13. **Concentrate on confirmation**: when a hypothesis CONFIRMS, immediately re-point all available
    effort at it and demote the rest (their "abandon the other Millennium problems" moment).
    No sunk-cost loyalty to the old queue order.
14. **Mid-effort upgrades**: when a better tool/model lands mid-campaign (parser, simulator, new
    public file), re-run the key earlier analyses with it instead of trusting stale results.
