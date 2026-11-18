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

## Context engineering for a perpetual scheduled loop (Anthropic, Sep 2025 + Claude Code best practices)
Sources: anthropic.com/engineering/effective-context-engineering-for-ai-agents (context rot,
attention budget, just-in-time retrieval, compaction / note-taking / subagents),
code.claude.com/docs/en/claude-code-best-practices (CLAUDE.md discipline, scheduled runs, unattended runs).

15. **Context is a finite attention budget, not a transcript.** Long contexts cause context rot —
    recall degrades as token count grows. Therefore: the wake prompt is a MAP (pointers), never a
    manual. All long-form rules live in on-disk files read on demand (just-in-time retrieval), not
    re-injected every wake.
16. **Scheduled runs use FRESH sessions.** Anthropic is explicit that repeated turns in one session
    accumulate context; for a scheduled loop, start a new session per wake. All campaign state is
    on disk (RESEARCH_STATE.md, ledgers, GitHub mirror), so continuity does not depend on history.
    → our loop creates a NEW session id each wake (campaign_wake.sh generates it).
17. **Bounded reads.** Never dump a whole file into context: use `tail -N`, `grep`, `head`. The
    wake prompt specifies the exact bounded commands (tail -60 etc.), so context stays small and
    high-signal.
18. **Procedures belong in skills/files, not the always-loaded prompt.** A long procedure in a
    always-loaded file weighs on every task. Our analogue: RESEARCH_DOCTRINE.md, RESEARCH_STATE.md,
    GOALS.md are loaded only when the turn needs them.
19. **Deterministic vs non-deterministic instructions.** "Never submit ungated bytes" is a
    non-deterministic instruction if it lives in prose; it is deterministic when the harness enforces
    it. Ours is enforced by harness/submit_gate.sh (invariants, not implementations).
20. **Unattended runs need caps and an exit condition.** A scheduled agent must know what "done"
    looks like, what it may touch, what stops it, and where output goes. Ours: one wake = one
    hypothesis state change or one adoption; wall-clock cap (WAKE_TIMEOUT); stop file; output goes
    to the ledgers + GitHub mirror; the user can stop everything with harness/STOP_WAKE.
21. **Cadence should match the work.** Re-injecting every 45 s floods context and burns quota with
    no new evidence between wakes; a 2 h cadence matches the campaign's actual signal rate (public
    releases land on the order of hours) and keeps each wake's context clean.

## Evolutionary discovery (Google DeepMind, AlphaEvolve, May 2025)
Source: deepmind.google/blog/alphaevolve-a-gemini-powered-coding-agent-for-designing-advanced-algorithms/
22. **Evolve the CODE, not the instance.** AlphaEvolve's core loop: an LLM proposes *program
    mutations*; automated evaluators verify + score them; a programs database keeps the best; a
    prompt sampler feeds the current best programs back into the next generation's prompt. Their
    flagship result is closest to our exact problem: "AlphaEvolve proposed a Verilog rewrite that
    removed unnecessary bits in a key, highly optimized arithmetic circuit… must pass robust
    verification to confirm functional correctness." We have the same shape: an optimized arithmetic
    circuit (kmb), an automated verifier (moat-lab + local verifier), and an exact score formula.
    → Our build lane becomes an EVOLUTIONARY SEARCH over generator variants, scored by the real
    objective function — not hand-guessed one-off patches (H6).
23. **The evaluator is the scarce asset — build it first.** AlphaEvolve works "in domains where
    progress can be clearly and systematically measured". Our score formulas (invsqrt Q·T-ish, DQI
    rep·Q²·T) are exactly such an objective. A lane without a cheap, reproducible, automated
    evaluator is not a search lane; it is a manual lane wearing a search costume.
24. **Breadth comes from the cheap model, depth from the strong one.** Their ensemble splits the
    work: a fast model maximises the number of ideas explored, a strong model adds depth. Ours:
    many cheap variant probes per wake (breadth) + one deep build on the best (depth).
25. **Prompt the next generation with the best-so-far.** The sampler assembles each prompt from the
    database's top programs and their scores — so proposals are targeted, not random. Ours: each
    subagent gets the current variant population + scores + the generator source pointers, and
    returns a NEW VARIANT (a diff), not prose.
26. **A search needs a scoreboard that survives restarts.** Their "programs database" is the
    campaign's population store: every variant, its config diff, its verified score, its build
    artifacts. Ours: work/evo/population.json (+ per-variant dirs). Without a persisted
    population, every wake re-learns what the last wake already tried — that is the circling bug
    in a new costume.
