# moat-lab research loop — ledger

Autonomous loop on `badboyhalo1801/moat-lab` (research kernel; never score-bearing).
Discipline: each iteration = one build → one push → one harvest → docs updated;
auto-push only when builder `ITERATION == harvest dir number`; ≤8 pushes/day;
scripts live in `/tmp/opencode/kernel_moat/build_moat.py` (REBUILDABLE — Kaggle
holds every version + output; the ledger below holds the knowledge).
Kernel-side mirror: `/home/bandoc/Downloads/opencode/KERNEL_WATCH.md`.

**⸻ 2026-11-07 ~11:5x: /tmp workspace WIPED (server restart).** Builder source,
all local harvests, MOAT_LOOP.md, daemon state lost. Nothing Kaggle-side lost.
Durable rebuild: this file (repo), harvests under `work/run_moat/`, harness
copies in `harness/`. Rule absorbed: anything precious → repo or Kaggle, never /tmp alone.

## Locked facts (do not re-derive)

| # | Lock | Numbers |
|---|------|---------|
| L1 | LB row transform | `row = (r_invsqrt · r_dqi · r_dfthcsos)^(1/3)`, higher=better; 3-point calibration 24.79783 / 24.94147 / 24.82604 EXACT ⇒ any bundle's row pre-computable |
| L2 | verify.py reads **only** the `dfthcsos/` subtree | lite-mix PASS @ 303,866,734.2253015 — byte-identical to anchor official (λ ours, angles ours ⇒ invsqrt/dqi swaps are kernel-score-neutral; MIX value lives only on the LB side, already banked) |
| L3 | CCX ≡ max_magic per group | v803 k4 270/270; anchor 276/276; Σmax_magic 4,152 vs 4,220 (T_static 8,304/8,440); axis = Toffoli budget; owner bought −6 CCX with −2,759 CX in k4 |
| L4 | recover_words ⇄ npz angle_words **elem-equal BOTH universes** `elem_eq:true` (sha 0604…a5cb / c9e7…2919); 3rd return = angle-toffoli total (8304.0 / 8440.0 = verify.py exact) |
| L5 | v803 universe ≠ anchor universe (NOT same-physics recompilation) | npz tensor shas differ in `H2_I, U, W, angle_words, offset_W, tree_edges`; same only `H1_I, Hsym_lower, brot` ⇒ cross-universe compile-quality comparisons invalid; the game = improving our OWN universe tree |
| L6 | text surgery loop closed | `Circuit(text)` + `repr(circ)` body-strip (`chr(10).join(repr(c).splitlines()[1:-1])`); rebuild recosts `equal:true`; peel = drop adjacent-identical stripped lines (k4: 37,299→37,264 instr, score-neutral) |
| L7 | true-kmb writer | `to_file(path, format)` / `from_file(path, format='auto')`; `format Literal['auto','kmx','kmb']`; default 'kmx' = TEXT (the v9 verify FAIL "magic bytes" = kmx text given as kmb); kmb orig header 16 B: `d750c7d5c329d326e3cc9f6834f2b8bf02000000…` |
| L8 | oracle free | `c.circuit_costs([circuit])` ~0.1 s/family; recost-after-surgery equality = pre-verify predictor |
| L9 | compiler ISA | `CircuitBuilder` + 61 ops (`init_and`/`del_and`, `gf2_*`, `push_condition`, `multi_controlled_x`, `z_pow`, `unary_iteration`…); `Simulator`, `GF2Field`, `UnaryIterationCursor` on `km` surface; 69 docstrings harvested |
| L10 | verify recipe (official PASS ×3) | `[sys.executable, /kaggle/input/<comp>/verifiers/dfthcsos/verify.py, <tree>/dfthcsos]`; assembled trees carry NO manifest; FAIL mode for wrong container: "File didn't start with the magic bytes identifying a kickmix binary format file." |

## Kernel-side anchor history

| date (UTC) | event |
|------------|-------|
| 11-07 | anchor release official 303,866,734.2253015 (= λ 46.87647033 × T 15,182 × Q 427); v803 verified 299,667,305.05730116 (T 14,966) |
| 11-07 08:36 | **v21 (rev5-anchor) PUBLISHED 303,866,719.4248164** (tag `ee2c3c97e713ab33`, Δ−14.5504 vs anchor) — new best-so-far; floor policy: never publish > best-so-far |
| 11-08 (LB pull) | 2,597 teams; #266 = 25.09058 (clumps: 313@25.1, 325@24.9); 508 teams in 24.70–25.00 ⇒ v0.9 row 24.94393 ≈ rank #541 — NOT top-300; to re-enter top-300 the mix needs dfthcsos ≈ −3.2% vs current (~294 M, T ≲ 14.7 k) |

## Iterations

| it | push (v) | cell | harvest verdict | next-fire |
|----|----------|------|-----------------|-----------|
| 1–2 | v1–v2 | ×2-universe clones, verify.py on competition input = official PASS both universes | pipeline is real; official verdicts live in-kernel | it3 LB row measuring |
| 3 | v3 | census + LB cell | census identity L3; MIX-A pending | M3 |
| 4 | v4 | M3 TESTS | M3 three-point calibration banked | mix row precompute forever |
| 5 | v5 | surgery workplan E3b | strip deltas per-k; oracle hunt | E3c |
| 6 | v6 | SURFACE_MAP | text mutation path open; Builder ISA | E3d |
| 7 | v7 | SURGE_PROBE | roundtrip exact; CCX identity; repr-wrapper bug found | E3e |
| 8 | v8 | SURGE2 | rebuild equal, peel ran, **word-arrays differ same shape; toffoli total in recover_words**; swap-verify plumbing broken (manifest glob) | E3e v2 |
| 9 | v9 | SURGE2 v2 | peel-k4 verify FAIL = "magic bytes" (to_file default 'kmx' = TEXT); lit-mix Killed on manifest-glob; L2 hint | E3f forensics |
| 10 | v10 | KMB_FORENSICS | **L2 LOCKED** (lite-mix PASS @ anchor exact); writer = format param (L7); dir(km) + 69 docstrings | E3g |
| 11 | v11 | ROUND_RESULT | **L4 LOCKED** (elem-eq round-trip both universes); **L5 LOCKED** (universes ≠ same-physics); kmb-writer cell died on MY plumbing (FileNotFoundError in tree-copy) — still the one open checkpoint | **it12 compiler session** |
| 12 | v12/v13 (same content; v12 pushed with a wrong rebuilt v803 dataset slug → re-pushed v13 with the correct input `heliosli/qcc-circuits-live` + ours `qcc-release-anchor`) | E2-lite (census_lite + regs + words), E4a (true-kmb writer closure → peel→kmb→swap→verify @ 299,667,305.05730116 EXACT expected), E4b (words-vs-registers encoding probe), E4c (CCX context atlas), E4d (word-objective lever map via load_inputs/evaluate_words) | *(running)* | E4a EXACT PASS ⇒ bundle loop CLOSED → it13 = rewrite-library hunt (CCX ladders from the atlas; encode/decode words if E4b locates them), recost-gated, one full verify/session |
| 13 | v14 (adds dataset `qcc-release-v091`; **DRIVER_ENV fix**: driver sp.run calls now get env PYTHONPATH = verifier pkg parent + kickmix dirs — the it12 kill-bug) | E2-lite verify on THREE universes (v803/anchor/**v091** — M16 sanity: v091 must verify at 303,866,719.4248164), E4a writer closure re-run, E4c CCX atlas, E4d v2 (per-column ±1 profile @ row 501, 90-probe no-op rate, λ-lowerer ⊗ e-lowerer PAIR lanes with feas = e1/e2 ≤ 0.02 AND E_gap ≥ rail − 7e-7), **E4e cross-check discriminator** (npz-only no-op swap) + *positive mover probe* (npz-only live mover: official score must equal in-process λ×14,966×427 prediction ⇒ npz drives the score) | **M16 LOCKED** (v091 PASS @ 303,866,719.4248164 EXACT; anchor PASS @ floor+14.8; **live owner → v89oz15i_oz15_ay3: PASS 299,662,412.45034325 = λ 46.89198912544362 × SAME 14,966×427** — overnight −4,892.6 pts, pure λ move; our λ still +1.552e-2 better, owner T lead 215 unchanged); **M11 writer recost-identical** (head byte-equal, −315 B = exactly 35×9 B) but official verify **FAIL** → writer-vs-peel isolation = it14 probe #1; **M14 rail closed** (150 profile cells, 36 pair lanes, 0 feasible); **M15 crashed** (copytree FileNotFoundError; noop [5,0] reconfirmed in-process) → E4e-v2 to it14 | it14 = writer forensics (zero-delta rewrite → recover_words diff) → and-ref/Gray-ladder tightenings per CCX atlas → one full-tree verify; paper map banked in `RESEARCH.md` §10 (Gidney and-pools, QROM SelectCopy, parity-network toolbox, warm-start λ_max + delta evaluator) |

## it14 plan (executed — v15 running)

| 14 | v15 (**it14**) — pushed 2026-11-08 ~04:5x UTC (budget 4/8) | **M17 writer forensics**: probe1 = zero-delta rewrite (untouched k4 → from_file → to_file("kmb") → byte_diag vs orig: equal? prefix/suffix/diff-runs → swap into m17_tree → official verify, EXPECTED parsed from universe_report's live score); probe2 = the exact it13 peel re-run → verify again with FULL verifier error capture (it13 tail was clamped at 240 chars); recover_words round-trip on orig family vs swapped-tree family (sha compare vs npz angle_words sha). **M18 toffoli hunt**: recost FIXTURES (2 same-controls CCX vs shared-AND `R w/CCX c1 c2 w/CX w t/CX w t2/HMR w b/CZ c1 c2 if b` — does the metric pay the and-pool? + triple-use + no-uncompute negative control) + per-k GREEDY same-controls clean-window pair census (W=64; chain_sav = Σ(m−1); same_t identity pairs ×2) vs −68/pass strip target (per-k ours−their deltas). **M15 v2**: universe = LOWEST verify score in universe_report (never hardcode), dangling-symlink-proof walker copy, noop [5,0]-first npz-swap probe then npz-only LIVE MOVER (official == in-process λ×T×Q pred ⇒ NPZ-ONLY proven). **M16** re-check on every run. E4D cell DROPPED (M14 closed-banked; ~12 min saved). build_moat.py edited via it14/patch.py; builder printed cells=10 ALL OK; footer MATRIX rows M17/M18/M15/M14-banked/M16 + it15 directives; ITERATION=14 (auto-repush gate wants 15 ⇒ safe) | **HARVESTED `work/run_moat/v15/`** — **M17 WRITER FAITHFUL** (zero-delta rewrite PASS @ live base 299,662,412.45034325 EXACT → **kmb modify→verify loop OPEN**); probe2 peel re-FAIL with full error text = *"ANGLE_4: uncorrected phase (measurement kickback)"* (adjacency-peel path dead; rewrite path open); **M18 fixture PAYS** (2 same-control CCX → 1 CCX + shared-AND + HMR-uncompute: max_magic 2→1 ⇒ the metric rewards and-pools; reuse-without-uncompute stays 1, recompute re-pays 2); greedy census chain_sav 0 / same_t 2×0 on the shallow windows tested (uni0/anchor/v091) — window too narrow, decode pass parked locally (`work/run_moat/decode_it15/`) → **it15 hunts wider clean-window chunks**; **M15 ambiguous** (noop PASS @ EXACT but mover skipped/missing → probe re-rides it15); M14 closed-banked; M16 substrate LOCKED (live-parse v803 299,662,412.45034325 / anchor 303,866,734.2253015 / v091 303,866,719.4248164 ALL EXACT) | if M17 writer-FAITHFUL + M18 fixture pays → it15 = chain-collapse rewrite on ONE group (live k4 lane −6): R w/CCX/CX uses/HMR/CZ block per census chunk, recost gate per member, recover_words ≡ npz, full-tree write + ONE verify at λ×(T−2Δ)×Q; if writer FAIL → binary 9-B op-block patch fallback |

## it12 plan (compiler session — the decisive one)

Goal: **our words recompiled to ≤ v803's per-group CCX on OUR tasks**, i.e., a
dfthcsos tree with T ≤ 15,182 → stretch T ≤ 14,966 (v803 parity) → stretch
T ≲ 14.7 k (top-300 mix). Sketch:
1. fix the kmb-writer checkpoint (peel → `to_file(format='kmb')` → head/size vs orig → swap → verify @ exact 303,866,719.4248164) — closes the modify→bundle→verify loop.
2. forward-compiler probe: words → `CircuitBuilder` ISA → circuit ⊨ recompile; validate via L4 round-trip (`recover_words` ≡ input words) + recost oracle; hunt CCX templates via `gf2_*` / `multi_controlled_x` ladders.
3. per-group strip emulation: apply the v803-style tighter ladders per-k (k4–k12 richest) on our words; recost; sum Σmax_magic ⇒ T forecast before any verify.
4. when T forecast ≤ 14,966: real-tree swap + official verify. PASS ⇒ dataset `qcc-release-v091` (v21's improved tree + compiled dfthcsos) ⇒ qqqqqq rev6 publish ⇒ MIX-B submission with pre-computed row.

## Nothing-hard-blocked checklist (post-wipe rebuild)

- [x] v21 harvest in repo (`work/run_qqqqqq_v21/`) — PUBLISHED 303,866,719.4248164
- [x] v11 harvest in repo (`work/run_moat/v11/`) — L4/L5 locked, kmb checkpoint pending
- [x] LB pull banked (`work/lb/`) — 2597 teams, wall at 25.09
- [x] MOAT_LOOP.md durable (this file)
- [x] KERNEL_WATCH.md updated (v21 publish + v11 read + LB)
- [x] build_moat.py rebuilt (fresh, it12 cells) — pushed v12/v13
- [x] it12 harvested (`work/run_moat/v13/`) — E4d word-lever banked; env bug found
- [x] dataset `qcc-release-v091` created + qqqqqq v22 (rev6-flat091) pushed
- [x] it13 built (syntax ALL OK, 11 cells) + **pushed as v14** — E4a writer closure, E4c atlas, E4d v2 lanes, NEW E4e cross-check + mover probe; DRIVER_ENV fix wired
- [x] daemon restarted (repo copy `harness/moat_daemon.sh`, pid 25336; **harvest bug fixed** — slug args + durable work/-side max+1 dirs)
- [x] it13 harvested (`work/run_moat/v14/`) — M16 LOCKED; M11 → it14 isolation (3-verify sequence); M14 rail closed (0/36); M15 crash → E4e-v2 carry
- [x] RESEARCH.md §10 addendum banked — paper map for the compiler hunt + compute-trick list
- [x] RESEARCH.md §10 addendum banked — paper map for the compiler hunt + compute-trick list
- [x] it14 built per RESEARCH §10.6 order (writer forensics → ladder tightenings → and-ref census → E4e-v2) + pushed as v15; ≤8 pushes/day (**4 spent today** — budget file 4/8)
- [x] it14 harvested (`work/run_moat/v15/`) — M17 writer FAITHFUL (**modify→verify loop OPEN**), M18 fixture PAYS, peel dead (kickback), greedy census 0 → decode pass local

## L11 · Q18 SUBSTRATE LOCK (2026-11-09) — new baseline = the community's conditional-uncompute bundle

**Baseline moved to the Q18 audit bundle** (`work/audit_q18/`; notebook
`badboyhalo1801/quantum-circuits-conditional-uncompute-audit`, run 367215593 →
submission `58156056` scored **25.15083 LIVE**, team **rank 207/2681**, above
Heliosli 219; same-bytes confirm `58157251` pending). Verified costs (all PASS,
sha-pinned, details in `work/audit_q18/BRIEF.md`):

| task | cost | provenance |
|---|---:|---|
| dfthcsos | **299,654,755.4367362** | v95mxf angles + Maoxin npz refit; λ 46.89079093513388 × T 14,966 × Q 427 |
| invsqrt | **95,345.55433569029** | Maoxin V3 line (62-q, toffoli_equiv 1537.83) |
| dqi | **374,690,183,327.0319** | Özer V70 48-CSWAP readout rewrite (−45,619,890 vs Maoxin baseline) |

- **M3 re-proven 5th time**: row = (r_inv·r_dqi·r_dft)^⅓ = 25.15083 exact; ~30-team
  live tieband incl. the collab cohort (Кирилл Тымчишин). Bundle sha `dd85f1e8…`.
- **Never-regress publish floor moves**: next qqqqqq push (rev7) must lift
  `DFTH_FLOOR = 299_654_755.4367362` (`rel_cost = min(ref/10.915, 299,654,755.4367362)`),
  i.e. rev7 adopts the Q18 dfthcsos bytes as substrate before any further strip.
- **Tier gate**: 174 teams above; the 25.16 tier holds only 4 teams ⇒ to enter it,
  each arm needs −0.1193% (chemistry −17.9 angles-toffoli · dqi −447 M · invsqrt −113.7).

### it15 directive (the 25.16+ ladder, two lanes)

1. **Lane A — chemistry toffoli strip (angles domain, −17.9 toffoli = −0.1193%)**:
   M18 shared-AND identity (fixture-validated: 2 CCX → 1 CCX + HMR re-pays 2) applied
   as chain-collapse per census chunk; M17 writer is FAITHFUL so the text-kmb rewrite
   path is PRIMARY (binary 9-B op-block patch only as fallback). Gates per member:
   recost `max_magic−Δ` instant-local, `recover_words ≡ npz` sha, THEN full-tree write +
   **ONE** official verify — expected score λ×(T−2Δ)×Q EXACT.
2. **Lane B — DQI window family #2 (biggest lever)**: extend the Özer 48-pair
   controlled-swap readout rewrite to the remaining eligible CSWAPs in `dqi.kmb`
   (58 M ops / 892 qubits). Measured −950,414 pts per toffoli-like (48-pair evidence)
   ⇒ −447 M needs ≈ −470 toffoli-like. Window form (proven): `CX`→measure(u=r⊕s)→
   `CZ(c,d)`→measure(v=r), common control preserved, invertible outcome map.
3. **Riders**: M15 npz-only mover probe re-run (robust walker copy) on the same
   iteration; M14 stays closed (no word-lane work until the T-structural win lands).
4. **Tooling**: local decode pass `work/run_moat/decode_it15/`
   (kmbparse/census2/ccxstrip/kdiff/strip_head, mirrors `/tmp/opencode/kernel_moat/it15/`)
   — ALL heavy parse/census runs go through the 4 G cage (`harness/run_capped.sh`);
   moat pushes ≤8/day (checklist budget file), moat-lab push #1 done today ⇒ budget 1/8-style check before v16.

### Sequence (banked template: it13→it14 flow)

local decode census (caged) → pick ONE lane-A group with ≥ −6 per block →
builder cell rebuild (`moat14.py` → it15 patch, ITERATION=15, cells carry the M17-writer
swap path) → syntax gate → push **moat-lab v16** → harvest verdicts → if EXACT-verify PASS:
qqqqq v23 = rev7 substrate (Q18 dfthcsos + stripped angles) with lifted floor → controlled
M3 pre-submit row check → then Lane B window scan on dqi.kmb (MPS-lite pre-check first:
outcome-map invertibility + phase-exponent identity per window before any submission).

- [x] **L11 REBASE checklist**: Q18 bundle banked (`work/audit_q18/`); row 25.15083 live; M3 point 5 banked; publish-bar rebase communicated to KERNEL_WATCH v22/rev7; it15 local decode toolchain present + OOM-safe (all compute ≥2 GB runs caged)
- [x] it15 builder patch (chain-collapse cell) → **CENSUS VERDICT 2026-11-09**: naive chain-collapse = 0 eligible clean-run chunks on all 3 universes (`work/run_moat/decode_it15/CENSUS_Q18.json`); Lane A angle-strip surgery parked pending the Gray/parity-ladder compiler pass (moved to it16+)
- [x] qqqqqq v23 rev7: DFTH_FLOOR lift to 299,654,755.4367362 + Q18 dfthcsos intake (**PUSHED + RUNNING**) — v24 rev8 on top (dqi census stage + marginal scheduler) **PUSHED + RUNNING**
- [x] Lane-B window census on dqi.kmb — **CONCLUSIVE, family #2 EXTINCT**: Maoxin's public baseline dqi (`4432ec5f…` = prior_full_DQI_control receipts) vs Q18 `4e9b50b1…` byte-witnessed the exact Özer splice (per pair `CSWAP(c,x,y)+HMR(x,b1)+HMR(y,b2)` → `CX(y,x)+HMR(y,b1′)+CZ_IF(c,x,u)+HMR(x,b2′)+BINVR_IF`, nops+96/n3−48/b0+48/nc1+96, register ids reused, −950,414.38 pts/pair EXACT); eligibility census = 4 sites/48 swaps in Maoxin, **0 in Q18** ⇒ nothing left to extend in this family; the −470 extrapolation in the brief is dead; family #3 (same splice engine, NEW eligibility gate = CCZ/CCX/SWAP + measure-uncompute classes) becomes the it16 charter

### it16 directive (the post-family-#2 reality, banked 2026-11-09 ~17:0x UTC)

### OFFICIAL it16 RETURN (2026-11-09 ~19:00 UTC, moat-lab v17 DQI_F3_RECEIPT.json)

- **R1 control (Q18 original, 102,400 shots): PASS structurally** — status PASS,
  value_errors 0, phase_errors 0, max_toffoli 395,593 ✓ — BUT score
  **374,690,051,360.2488 = −131,966.79 vs the banked floor**. ⇒ SAMPLING
  JITTER FACT (campaign-wide): official dqi scores are NOT run-to-run
  deterministic at the ±1.0 level; observed jitter ≈ 1.3e5 pts (~3.5e-7 rel).
  Future score-exactness gates must use jitter-tolerant windows (structural
  PASS + |Δscore−pred| ≲ 3σ_jitter), never "EXACT ±1.0" across different runs.
- **R2 four-site family-#3 splice (102,400 shots): FAIL — REAL** —
  `phase_errors 51,205/102,400 (~50%), value_errors 0/102,400`. The file
  parses + boots (encode verified), but the transplanted strip computes
  WRONG PHASES in half the shots ⇒ logical breakage, not sampling.
  Verdict FAIL; no M3 submission made; row untouched (25.15083 stands).
- Root-cause hypothesis (it15 census "sibling sites have NO own stores" +
  R1-vs-R2 asymmetry): the inserted strips REUSED the partner's global bit
  IDs (by/bx pool bits ~101,242–101,266) — those same bits are read/written
  by retained BS0/BINVR_IF pool logic elsewhere/earlier ⇒ the strip's own
  HMR stores clobber bits that other conditioning logic reads ⇒ ~50% phase
  corruption. In the ORIGINAL Q18 the partner's strip works because its
  pool slice is exclusive to its window.
- It16 byproducts: `qcc-release-q18f3` dataset (4-site splice, sha
  `af5ee75b…`, ROUNDTRIP/PASS + region_check2 ALL-8-cols byte-equal; the
  WRITE-ENGINE receipts are all valid — only the sibling-site ELIGIBILITY
  failed); submission_f3.zip was prebuilt but never submitted (correct).

### family-#4 census return (2026-11-10 ~11:3x UTC, all local/caged/free) — ALL 1-charter ALLELES DEAD-OR-PARKED

Facts (family4_census{,2,3,4}.py + .json in dqi_work/; raw counts asserted exact):
- n3 anatomy: CCX base 382,204 (96.6%) + CSWAP base 12,012 + CCZ base 1,377;
  ZERO IF-variant n3 ops (compiler already stripped them). 936 twelve-runs/chunks.
- alleles with 0 yield:
  (a) exact-tuple / symmetric-set dedupe: 0 clean pairs (every sandwich touches
      the trio; CCZ 0/442, CCX 0/8000-sample of 161,941, CSWAP 0/4,130);
  (b) constant-rail degradation: NO constant qubits (E0/E1 0..23 all state-written
      ~20kx 1q + heavy 2q/3q use; qubit 18 written 349x + HMR 227x);
  (c) CSWAP readout-rewrite extension (family-#2): banked exactly 4/4 windows
      already rewritten (strips @16,083,438/16,233,726/42,100,286/42,250,574,
      each 1,338 ops after its run twin, identical pair multisets). The audit
      notebook (pulled to audit_pull/src) states the mechanism: CSWAP before
      X-basis readout == [CX(d=a+b), HMR(b)->u, CZ_IF(c,d|u), HMR(d)->v,
      BINVR_IF(v|u)]x12, phase-exponent-equal, MPS 2,048-verified. Census v4:
      of 936 chunks, 909 ENTANGLED, 27 READSOON (non-HMR touches <=64 ops),
      0 ELIGIBLE — extension closed. NOTE the it17 fresh-bits value-break is
      now explained: a correct synth must REUSE the window's own readout-bit
      ids (the BINVR_IF writes (v, u+v) = (r,s) into the ORIGINAL readout bits
      — fresh bits sever the map => value_errors 1024/1024). Morphology-level
      extension is closed even under the correct synth (0 candidates).
  (d) CCX fan-out ancilla stacks: real (15,223 ctl-pairs own >=2 targets; top
      stacks 4,034 targets) but every exact rescue needs REORDERING through
      dirty sandwiches + a clean ancilla (nq/header surgery) => PARKED as
      family charter material, not actionable today.
- score math locked for any future family: 1 net n3 op = 950,414.382 dqi pts.

Budget today: 2/8 moat pushes (it17 v19 + one boot-fail v18). NO further moat
pushes queued — nothing new to verify. qqqqqq rev9 (struct-fix + Q18-assembly
force) remains the compute lane; BRIEF.md's alternate levers live on:
chemistry ANGLES toffoli surgery (-17.9 equiv via M18 shared-AND, it15
toolchain) and invsqrt (-1.83 equiv) — both explicitly "do later" per gate math.

| moat it18 | V107 release adoption receipt (two-receipt gate) | 2026-11-11 ~09:2x UTC (v20; manual push) | sha-gate all 18 v107 files vs mounted manifest (portfolio v107axr_ax_ay3) + verify_submission_dqi/invsqrt @1024 structural verifies + dfth verifier if shipped + per-task score/RATIO extraction (owner decomposition) | PENDING — running; submission of `/tmp/opencode/v107/submission.zip` (f632e8ea…) gated on PASS. Est GM anchor: heliosli 25.29380 @ rank 326. Fallback if receipt FAILs: mix zip `/tmp/opencode/mix_25155/` (85ad1153…, est 25.15532, all components individually receipted). Budget 1/8 |
| moat it18 (v20-v24) | V107 adoption receipt — 4 pushes to converge the gate | 2026-11-11 02:16–02:35 UTC | sha-gate evolutions: label-drift aborts (v20: live mount moved to v109pv mid-session; v21: OUR snapshot manifest was the v109-labeled zip — discovered the owner re-releases the SAME tree under drifting labels, v107≡v109 byte-identical) → v22 hardcoded 18-file SHA_TABLE (tree identity) → flat-name resolution fix (v23) | **v23: shas_ok TRUE (tree identity gate PASSED in-kernel)**; dqi @1024 = known low-shot quirk FAIL (it17 precedent); invsqrt instant-crash = wrong CLI flag. **v24: dqi structural PASS @4096** — value/phase errors 0, circuit_sha256 9fcda0c1… = manifest sha EXACT, num_ops 58,287,123, num_qubits 892, num_bits 600,002, max_toffoli 395,584 (release dqi = Maoxin-baseline family vs our 48-window rewrite). 4096-shot score 938.8G = SHOTS-ARTIFACT (official = 102,400; it16 control reproduced 374.69G there). invsqrt verifier CLI = --shots-per-x (not --num-shots). Verdict PARTIAL → v25 pushed: dqi @102,400 (real score = owner decomposition) + invsqrt @--shots-per-x 4096 + tails. Budget 6/8 |
| moat it18 final (v25) | V107 adoption receipt — CLOSED | 2026-11-11 02:41–03:15 UTC | dqi @102,400 official-grade + invsqrt probe | **dqi PASS 374,685,006,335.9395 @102,400 (0 errors) = −5,176,991 pts vs our audit dqi banked 374,690,183,327.0319 ⇒ release dqi BETTER (r 65.2299 vs 65.2258)**; num_ops 58,287,123 / 892 q / 600,002 bits / max_toffoli 395,584. invsqrt @--shots-per-x 4096 TIMEOUT 5400s (needs 200M-shot scale; not a gate blocker — bundle anchored by owner's Kaggle 25.29380 on identical bytes). Verdict: ADOPTION-CLEAR → **submission 58224607 pushed 04:16 UTC, PENDING**. Budget 6/8 |
| submission 58224607 | V107 tree adoption | 2026-11-11 04:16 UTC → scored ~11:47 | two-receipt: in-kernel 18-sha tree identity + official-grade dqi PASS @102,400 + owner 25.29380 anchor | **COMPLETE 25.29663 — RANK 279/2808** (row was 25.15083/rank 740). +0.1458 GM. Beat owner's v107 by +0.0028 (jitter). Owner re-drifted to 25.30000 (rank 237) at 03:31. M3 discipline held end-to-end; mix fallback (85ad1153) retired unused |
| moat it19 (v26) | v115m4 adoption receipt | 2026-11-12 ~10:1x UTC (1 push, budget 1/8) | v115 SHA_TABLE (18-entry tree identity) + qcc-release-v115 snapshot mount + invsqrt probe dropped + dqi @102,400 | **FULL PASS in one push**: shas_ok TRUE; **dqi official-grade PASS @102,400 = 373,534,939,340.6408** (0 value/phase errors, num_ops 61,460,043, max_toffoli 401,313) — **−1,150,066,995 pts vs v107's release dqi** (−0.31%): owner's new dqi work is genuine. File grew 529→557.7 MB but scores better. dt 91.1s. → submission 58269379 (zip cb2ca76b…) PENDING, owner anchor 25.40482. NOTE: prior turn's splice bug (missing table brace) caught by ast gate pre-push |
| submission 58269379 | v115m4 tree adoption | 2026-11-12 10:16 UTC → scored ~11:44 | receipt it19 v26 FULL PASS (tree identity + official-grade dqi 373.53G @102,400 + owner anchor) | **COMPLETE 25.40482 — RANK 234/2809, exact tie with heliosli's own 25.40482** (row was 25.39570/rank 389). +0.00912 GM, +155 places. Zero-jitter match on identical bytes — the anchor-based prediction is now exact to 5 decimals. Budget 1/8 used |
| moat it20 (v27) | v119_acx adoption receipt | 2026-11-14 ~03:1x UTC (1 push; day fresh) | v119 18-entry SHA_TABLE (invsqrt 198,590 / dqi 455,584,321 / k-files regrew 350–420 KB) + qcc-release-v119 snapshot discovery + dqi @102,400 official-grade | PENDING — running; poller armed. Static receipt done locally (18/18, zip 09a4b3a394263e5d, 49,304,325 B). Owner anchor: 27.28999 @11-14 00:28 (sub predates release by 2h05m — v119 is same-or-better than their scored bundle). Auto-wake loop now drives these iterations every 2 h |
| moat it20 (v27) — CLOSED | v119_acx adoption receipt | 2026-11-14 ~02:55–03:02 UTC (1 push) | v119 SHA_TABLE + snapshot discovery + dqi @102,400 | **FULL PASS single push**: shas_ok TRUE; **dqi official-grade PASS @102,400 = 360,209,905,486.0156** (0 value/phase errors; num_ops 52,930,180 / max_toffoli 383,414) = **−13,325,033,854 pts vs v115 dqi (−3.56%)** — owner's new dqi axis is massive. → submission 58329439 (zip 09a4b3a3…, 49,304,325 B) PENDING; anchor 27.28999 (owner 00:28 sub on ≥-equal tree). 4 slots left |
| moat it21 (v28) | v119b in-place tree update receipt | 2026-11-14 ~16:0x UTC (2nd push today) | v119b SHA_TABLE (new invsqrt + npz shas) + qcc-release-v119b snapshot discovery + dqi @102,400 | **FULL PASS**: shas_ok TRUE; dqi official-grade PASS 360,209,905,486.0156 (0 errors; num_ops 52,930,180 / max_toffoli 383,414 — unchanged leg, as expected: only invsqrt + npz moved). → **submitted v119b** (zip 8716e4c5c65aee35, 49,304,887 B); 1 slot left today. Wake resample 58330276 also in flight (old v119 bytes) |
| moat it22 (v29) | v119c in-place npz update receipt | 2026-11-14 ~09:4x UTC (3rd push today) | v119c SHA_TABLE (npz sha moved again) + qcc-release-v119c snapshot + dqi @102,400 | **FULL PASS**: shas_ok TRUE, dqi 360,209,905,486.0156 (0 errors, unchanged leg). → **submitted v119c** (zip 454270509514b5ff, 49,304,120 B) = last slot of the day (0 remaining). Expected ≈27.29709 (owner's 09:15 score on the same npz) |
| moat v31 (it24) | v119e owner-tree receipt | 2026-11-15 ~09:1x UTC (push 1 today→2 incl v32/v33) | v119e SHA_TABLE (owner full-chem k-file refit + micro-invsqrt; npz d5493daaa102) + qcc-release-v119e snapshot + dqi @102,400 | **FULL PASS**: shas_ok TRUE; dqi PASS 360,209,905,486.0156 @102,400 (unchanged leg). → **submitted v119e** (zip fc1b364b7b9b0730, 49,293,445 B); 3 slots left. Chemistry leg unknown (owner private npz) — score arbitrates vs out40 |
| moat v32 | out40 gate — FAILED PRE-PUSH CATCH | 2026-11-15 ~09:3x UTC (push 2) | qcc-release-v119f snapshot initially carried OWNER's manifest (npz sha d5493… vs atlas npz 5a7538…) | **ERROR (sha mismatch)** — correct failure mode; no false receipt. Root cause: gate checks manifest vs files, SHA_TABLE constant is unused. Fix: patched snapshot manifest (npz → 5a75386681c8…, 1,847,692 B), re-versioned dataset, rebuilt SHA_TABLE with real bytes |
| moat v33 | out40 tree gate (27.3122 target) | 2026-11-15 ~09:4x UTC (push 3) | v119f snapshot (fixed manifest: 17 live files + atlas GRG refit npz) + dqi @102,400 | PENDING — poller armed. On FULL PASS → submit out40 zip 0a0d6dcaf40db427 (expected score EXACTLY 27.31220, deterministic: asteriospanoras' row). Tree-identity = 18/18 shas vs official out40 receipt + our manifest-anchored gate |
| moat v33 | out40 tree gate (27.3122 target) | 2026-11-15 ~09:4x–10:0x UTC (push 3) | v119f snapshot (fixed manifest: 17 live files + atlas GRG refit npz 5a75386681c8) + dqi @102,400; log confirms mount /kaggle/input/qcc-release-v119f (NO fallback) | **FULL PASS**: shas_ok TRUE (0 BAD), dqi PASS 360,209,905,486.0156 @102,400 (= out40 official receipt). **NEW CLI RULE learned: uploads MUST be named submission.zip** (400 FAILED_PRECONDITION otherwise — 3 wasted attempts, no slot consumed). → **submitted out40 zip 0a0d6dcaf40db427** as ref **58364696** (2 slots left); expected score EXACTLY 27.31220 (deterministic; asteriospanoras rank 228 row). Two-receipt gate: (a) 18/18 local shas vs official out40 receipt, (b) in-kernel manifest-anchored tree identity + official-grade dqi PASS + verified anchor row |
| subs 58364427 + 58364696 | v119e + out40 adoption scores | 2026-11-15 ~02:0x–02:4x UTC | both gate-PASSed (v31 / v33) | **v119e COMPLETE 27.31221 (owner private npz) = NEW BEST ROW, RANK 238** (+209 places, +0.00979 GM); **out40 COMPLETE 27.31220** (exact deterministic match to asteriospanoras' row). Owner's private npz > public GRG refit by 0.00001 ⇒ owner's live tree = best known chem tree, now ours too. 2 slots left today |
| wake-shell fix | user-steered model-chain repair | 2026-11-15 ~10:0x UTC | harness/campaign_wake.sh rewritten | Fallback now fires ONLY on real free-route exhaustion (rc≠0 or first-line error JSON) + limit signature; transcript pollution can no longer trigger duplicate nvidia wakes (the 02:43 "exhausted (rc=0)" bug). bash -n OK; free route verified live via throwaway session |
| sub 58365725 | v119g owner 2nd-chem-refit tree | 2026-11-15 02:50:43 UTC (gate v34 FULL PASS) | **COMPLETE 27.31513 = NEW BEST ROW, RANK 181** (+57 places over 238; +0.00292 over v119e's 27.31221). Owner's npz refit axis is live and compounding. 1 slot left today |
| wake 4 | no-drift wake + local toolchain | 2026-11-15 ~04:0x UTC | tree identical to scored v119g | NO submission (slot preserved for a real new tree); instead: kickmix local compile pipeline established (§17), kmb↔kmx lossless round-trip verified on the live invsqrt, kmsim local verification matches official values, official PDF cost model extracted (rotation price 0.56·log2(1/ϵ)+5.3T, ϵ=π·margin/n_rot) ⇒ local rotation-ladder optimisation lane opened (est. +0.9..+2.3 GM if half the rotation cost is recoverable) |
| wake 5 | no-drift wake + official-verifier-localisation | 2026-11-15 ~06:0x UTC | tree identical to scored v119g | NO submission (slot preserved for a real new tree); instead: downloaded the OFFICIAL verifiers (competition-file listing is paginated!) and got all three tasks scoring LOCALLY (kickmix + CPython 3.13 venv) ⇒ exact pre-flight scoring of any tree (§18: our live tree reproduces 27.31513 exactly); baselines invsqrt 78,673.57 / dqi 3.6021e11 / chem 294,887,972; exchange rates banked (1 invsqrt qubit = +0.20 GM); background full dqi verify of the best public candidate launched |
| wake 6 | no-drift wake + L2 decoder (chem loader pipeline) | 2026-11-15 ~07:3x UTC | live tree v119_acx_ay3 identical to scored v119g (18/18 shas) | NO submission (slot preserved); decoded the chem loader as a rebuildable artifact (marculera's tensor QROM, official verifier scores the RECOVERED words) and started the loader-cost sweep (owner L=4,030/pass at J=5; rank bounds say 20 % is available) |
| sub 58407899 | v120 live tree (16/18 changed vs v119g) | 2026-11-16 00:32:42 UTC (gate v35 V120-RECEIPT-PASS) | PENDING → predicted 27.31676 | 4 slots left today |
| sub 58407899 | v120 live tree | 2026-11-16 00:58 UTC | **COMPLETE 27.31675 = NEW BEST ROW** (predicted 27.31676 — exact) | 4 slots left |
| gate v36 | v121 C8 best-of-each (invsqrt 44q-LP + dqi 890q-retained + chem c8-refit) | 2026-11-16 01:09:12 UTC | RUNNING → expected V121-RECEIPT-PASS → submit ≈28.06 | next wake |
| gate v36 | v121 receipt | 2026-11-16 ~01:13 UTC | **V121-RECEIPT-PASS** (18/18 shas, dqi 347.76e9 @102400, chem 294.76M) | |
| sub 58409216 | v121 C8 best-of-each | 2026-11-16 01:14:24 UTC | PENDING → predicted **28.06406** | 3 slots left |
| sub 58409216 | v121 C8 best-of-each | 2026-11-16 01:35 UTC | **COMPLETE 28.06404 = NEW BEST ROW, rank ≈223** (+0.747 GM, +300 places) | 3 slots left |
| gate v37 | v122 super-SOTA receipt (8b410e77 + ccc2ab84 + f6e12f02) | 2026-11-16 02:17:32 UTC | RUNNING → expected V122-RECEIPT-PASS → submit ≈28.09092 | 3 slots left |
| gate v37 | v122 receipt | 2026-11-16 ~02:21 UTC | **FULL PASS** (18/18 shas; dqi 347,375.5M @102400 0err; chem 294,762,733; invsqrt 75,038.0) | |
| sub 58411160 | v122 super-SOTA | 2026-11-16 02:23:08 UTC | PENDING → predicted **28.09092** | 2 slots left |
| gate v38 | v123 receipt (f2cdab0b invsqrt + ccc2ab84 dqi + f6e12f02 chem) | 2026-11-16 03:03:43 UTC | RUNNING → expected V123-RECEIPT-PASS → submit ≈28.09487 | 2 slots left |
| sub 58411160 | v122 super-SOTA | 2026-11-16 02:50 UTC | **COMPLETE 28.09090 = NEW BEST ROW** | 1 slot left after v123 |
| gate v38 | v123 receipt | 2026-11-16 ~03:07 UTC | **V123-RECEIPT-PASS** (18/18 shas; dqi 0err @102400; chem PASS) | |
| sub 58412822 | v123 rescheduled invsqrt | 2026-11-16 03:11:01 UTC | PENDING → predicted **28.09487** | 1 slot left |
| sub 58412822 | v123 rescheduled invsqrt | 2026-11-16 03:39 UTC | **COMPLETE 28.09486 = NEW BEST ROW, rank 73/3143** | 1 slot left |
| cycle 23 | public-frontier exhaustion proof + chem cost-only analysis | 2026-11-16 ~05:0x–06:5x UTC | invsqrt 96-file sweep (best public 75,082 > ours 75,006), dqi 99-file header sweep (0 better), chem compatibility matrix (best 294,762,981 > ours 294,762,733) ⇒ **no adoption candidate anywhere** | no submission (1 slot left, preserved) |
| unit chemk8 | syed3000 v18 planner, batch k=8, our words | 2026-11-16 06:31 UTC | RUNNING → cuts 145 ⇒ products 190 (vs our 264–293/batch) → emit + exact all-branch proof; only if L < 4,025/pass does a v124 chem tree exist | 1 slot left |

| sub 58425713 | v124 (our tree, drpatrickchan chem) | 2026-11-16 09:47 UTC | **COMPLETE 28.09486**, official rank 409/3,222 | — |
| cycle 24 | server-restart rebuild + v125 public adoption | 2026-11-17 00:54–02:33 UTC | `/tmp/opencode` rebuilt from Kaggle; v125 = public 28.1277 best-per-task mix (invsqrt `0af21cb8` maoxin123 + dqi `66b4f18b` Balram + chem `703843d3` Atakan); **gate v39 V125-RECEIPT-PASS** (18/18 shas, dqi @102,400 PASS 347,128,304,010.81165 with 0 value / 0 phase errors, dfthcsos in-kernel PASS 294,762,512.8596263, invsqrt local official PASS 74,797.36535717871) | 5 slots/day, 0 used |
| sub 58452912 | v125 public 28.1277 mix | 2026-11-17 02:33:08 UTC | **COMPLETE 28.12769 = NEW BEST ROW** (predicted 28.127697 — exact), **official rank 294/3,233** | 4 left |
| gate v40 | v126 (Grant Prater dqi `61c8348d`) | 2026-11-17 03:03 UTC | **V126-RECEIPT-PASS but REJECTED**: official dqi **348,004,440,260.46 with 1 value error** (rep 1.19673) vs v125's 347,128,304,010.81 (0 errors) ⇒ projected GM 28.10407 < 28.12770 ⇒ **NOT submitted** (the author's "clean draw" 346,413e9 did not materialise) | 4 left |
| gate v41 | v127 (manwithacat HW-29 dqi `957d6733` + maoxin chem) | 2026-11-17 03:24 UTC | **V127-RECEIPT-PASS but REJECTED**: official dqi **348,246,849,661.48 with 1 value error** ⇒ GM 28.10134 ⇒ **NOT submitted**. Chem leg PASS 294,643,137.73357135 (T 14,706, λ_eff 46.921716818) — kept for v128 | 4 left |
| gate v42 | v128 (manwithacat HW-28 dqi `b0983d55` + maoxin chem) | 2026-11-17 03:36 UTC | **V128-RECEIPT-PASS**: dqi **347,045,216,047.3212, 0 value / 0 phase errors**, rep 1.1912604648115832, T_mean 367,789.4946; chem 294,643,137.73357135; invsqrt 74,797.36535717871 | 4 left |
| sub 58454579 | v128 best measured public file per task | 2026-11-17 03:39 UTC | PENDING → projected **GM 28.133740** (+0.00604 over v125) | 3 left |
| method | **the gate is a free oracle** | 2026-11-17 02:50–03:36 UTC | The DQI official score is deterministic per file (seed = circuit hash + salt), so an in-kernel @102,400 verify predicts the competition score exactly — v125's in-kernel 347,128,304,010.81165 scored 28.12769 = predicted 28.127697. Kernel pushes cost no submission slot ⇒ **probe every candidate DQI, submit only the winner**. The DQI draw is a lottery: ~6e-6 failures/shot ⇒ P(0 errors in 102,400) ≈ 0.54; one error costs +0.46% cost (rep 1.19126 → 1.19673), two errors +0.85% | — |

| sub 58454579 | v128 (HW-28 dqi `b0983d55` + maoxin chem) | 2026-11-17 03:37 UTC | **COMPLETE 28.09080** — the projection (28.133740) was WRONG: the official draw lost **1 value error** (official DQI cost 348,639,070,923.37 = exactly the 1-error rep factor 1.1967314991687559 × 890² × 367,789.4946) while our default-salt in-kernel draw was clean. ⇒ **the in-kernel default-salt verify is NOT a score oracle** (see the cycle-25 note) | 3 left |
| method | **the gate-as-oracle claim was falsified** | 2026-11-17 04:40–06:00 UTC | The official harness draws the DQI shots with a **different salt** than the default (empty) one: for `b0983d55` our draw was clean and the official lost a shot; for `61c8348d` our draw lost a shot and the official was clean (Grant Prater's public entry 28.14703 inverts to the clean cost). The verifier's seed = sha256(circuit bytes + salt) and the official run uses 102,400 shots (the official v128 cost matches the 1-error rep factor to 1.8e-5), so only the salt/seed differs. The in-kernel verify remains a **correctness gate** (PASS = the file decodes) and **one sample** of the loss distribution, not a predictor of the official draw | — |
| cycle 25 | **public-pool sweep** | 2026-11-17 04:10–06:20 UTC | Harvested 28 public portfolios (834 MB + 1.5 GB) and indexed every DQI / invsqrt / chemistry set inside them. **DQI**: only `575b043f` (Grant Prater, T_mean 367,116.06) and `f0e646c7d2ea` (leotang09 via ratnachand, T_mean 367,477.59) are new and beat HW-28 (T 367,789.49). **invsqrt**: the two fresh 44q files score 75,038.57 and 75,038.13 vs our 74,797.37 ⇒ `0af21cb8` stays. **chem**: 57 public sets verified locally (15 s each) ⇒ `a73b25d2` + the 4,022-T loaders (294,643,137.73) is the best public set | — |
| probe | `dqi-probe` kernel v1 (free oracle, no slot) | 2026-11-17 04:47–04:58 UTC | 6 distinct 890q candidates discovered in the mounted public datasets; measured `575b043f` = **346,409,762,292.7187, 0 err, T_mean 367,116.0572** and `f0e646c7d2ea` = **346,750,900,116.7399, 0 err, T_mean 367,477.5862** at 102,400 shots | — |
| gate v44 | v129 (Grant Prater `575b043f` + maoxin chem + our invsqrt) | 2026-11-17 06:11 UTC | **V129-RECEIPT-PASS**: 18/18 shas; dqi **346,409,762,292.7187** 0 value / 0 phase errors @102,400, rep 1.1912604648115832; chem 294,643,137.73357135 (T 14,706, λ 46.921716818) | 2 left |
| sub 58459080 | v129 best-public DQI by mean Toffolis | 2026-11-17 06:20 UTC | PENDING → clean-draw **GM 28.150932** (1-error case 28.1079) | 2 left |
| build | `dqi-build` kernel v1 (free search) | 2026-11-17 06:22 UTC | Runs Grant Prater's public measured-uncomputation tools on `575b043f` with every flag combination (`--retain`, `--symclean`, `--condsym`, `--lin`, `--extra 1`), applies what the pass proves exactly and measures each candidate with the official verifier. His README leaves open: "14 more Toffoli-likes in each closing (686 in all) wait for a second helper wire that is idle between the two computations" | — |

| gate v46 | v131 receipt (asterios 28.18084 portfolio: invsqrt 563d0583 + dqi 5f901c55 + chem f05297b4 + maoxin loaders) | 2026-11-18 07:4x UTC | RUNNING → expected V131-RECEIPT-PASS → submit (clean GM 28.18084; 1-err case 28.1378) | 5 slots left |

| gate v48 | v131 receipt (asterios 28.18084 portfolio) | 2026-11-18 07:5x UTC | **V131-RECEIPT-PASS** (18/18 shas; dqi official @102400 PASS 346,404,203,610.11, 0 value/0 phase errors; chem in-kernel PASS 294,642,299.76 λ 46.92158337179646) | |
| sub 58487983 | v131 asterios portfolio | 2026-11-18 00:48 UTC | PENDING → clean GM **28.18084** (1-err case 28.1378; LB keeps best) | 4 slots left |

| sub 58487983 | v131 asterios portfolio | 2026-11-18 01:05 UTC | **COMPLETE 28.18084 = CLEAN DRAW (0 lost shots), NEW BEST ROW** (+0.0299 over v129 28.15094). Frontier still #1 aadi_stonks 31.50404 | 4 slots left |
