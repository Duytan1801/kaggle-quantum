# RESEARCH STATE — live hypothesis queue (agent-maintained; rewrite freely)
# Format: H# | claim | mechanism | est GM | cheapest discriminating test | status | evidence | updated
# Rules: never re-run a KILLED test; re-rank by expected-GM/effort after each resolution.
# Last full re-rank: 2026-11-18 (post v131 = 28.18084, public harvest complete)

## QUEUE (ranked)

H1 | DQI width is compressible below 890 | score = rep×Q²×T (verify_submission_dqi.py:420); Q² dominates
    | +1–2 GM if Q→750; dead end if width is genuinely simultaneous | per-wire live-span anatomy of
    base_5f901c55.kmb (wa4.py) → KILL if peak-live ≈ 890; SUCCESS if peak-live << 890 | **KILLED
    2026-11-18 — evidence: ALL 890 wires first-touched within op window [351793, 352459] (a 667-op
    window at 0.6% into the circuit) and last-touched ≥52.86M of 57.52M ops; zero untouched wires;
    peak-live = 890 = declared width (cumsum sweep; note: np.maximum.accumulate on ±1 deltas is a
    running-max bug trap — use cumsum); spans overlap for 889/890 wire pairs. The circuit is FLAT-WIDE
    by construction: no live-span slack exists for mechanical relabel/repack. Head ops [0,351793) are
    all type-194 (0xC2) bit-writes.** Any width cut must come from generator-level redesign (H3:
    what top-2 does differently) — this is now the only DQI width path | 2026-11-18

H2 | invsqrt Q45/43 reachable by re-implementing minand_sat.py | Syed generator source local + byte-exact
    (74 s rebuild); maoxin proved 46→44 exists | +0.08–0.16 GM direct — BUT its real value is the
    STEPPING-STONE: exact-AND retirement machinery + endpoint surgery is the scaffold class needed for
    any future width attack (Navier–Stokes pattern: solve Euler first, then prompt the big problem with
    the Euler solution) | exact-AND synthesizer + owner retirement + endpoint/cleanup helper scheduling,
    then generator full-domain proof | **TESTING / INCONCLUSIVE** | v8-specific 9-dependency retirement
    route KILLED (not repeated).  v10 product route has an exact 5-input/2-AND certificate (0/4096
    mismatches).  Q45 progression reaches cleanup: h0 pack + v10 retirement + disposable divider
    feed carry + alternate endpoint holds (`W2_E_HOLD=1,3,5,7,9,11`,
    `W2_F_HOLD=0..7`) + borrow HMR-reset v11 for the last v9-form intermediate fit product,
    divider forward, the full endpoint, and endpoint v9/v10 rebuild at Q45.  A full-emission trace found
    and fixed one invalid CX(q,q) in the endpoint-borrow prototype (terminal v9 gate is already the
    target); the corrected prototype still stops at cleanup sign-15, whose pinned form needs six live
    helpers plus one output (46th qubit).  No full-domain proof yet, so NOT CONFIRMED.  Evidence:
    work/recon/h2_v10_form.json, work/recon/h2_post_product_map.json,
    work/recon/h2_q45_disposable_divider_build.log, work/recon/h2_q45_endpoint_borrow_build.log,
    work/recon/h2_q45_prototype_recipe.md.
    **CLEANUP TEST PRE-REGISTERED 2026-11-18 06:24 UTC:** derive/adapt the exact sign-15 cleanup form
    (same Boolean function, no domain shortcut) to <=2 simultaneous helper wires, or borrow an
    already-retired cleanup owner without semantic conflict.  SUCCESS = Q45 generator emission plus
    `PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS`, then official verifier PASS.
    INCONCLUSIVE = allocation fits but proof differs.  KILL this Q45 route if the exact cleanup form
    provably needs >2 simultaneous helpers and no already-retired owner can be borrowed; do not spend a
    submission slot before the full-domain proof.
    **EXPLORATORY KEEP-SIGN15 RESULT 2026-11-18 06:55 UTC:** retaining (rather than retiring/rebuilding)
    history sign 15 passes the entire divider cleanup at Q45 and reaches the second table loader.  The
    next blocker is the pinned second-framed loader's work cap 19 (27+19=46).  This does not satisfy the
    cleanup-form success criterion and is not a proof.
    **LOADER TEST PRE-REGISTERED 2026-11-18 06:55 UTC:** search a second-framed loader certificate at
    work cap 18 (27+18=45), using the published exact 128-row loader constructor in a disposable tree.
    SUCCESS = complete cap-18 certificate with exact replay and native loader peak 45, followed by Q45
    generator emission and the full-domain proof.  INCONCLUSIVE = bounded search finds no complete
    certificate or replay differs; refine the loader/search only.  KILL this keep-sign15 branch if an
    exact cap-18 second-framed loader is impossible, but do not kill the separate sign-15 synthesis route
    **LOADER OUTCOME 2026-11-18 07:10 UTC:** SUCCESS at the loader subtest.  Eight seeds produced exact
    cap-18 second-framed certificates; the selected seed has 92 Toffolis and independent exact replay PASS
    (27+18=45).  Native Q45 integration passes the loader and exposes the next blocker: second coefficient
    rows need an incoming and outgoing quantum carry simultaneously (45+1>45).
    **COEFFICIENT TEST PRE-REGISTERED 2026-11-18 07:15 UTC:** retire v10 for the duration of the second
    coefficient forward (v10 is not used by its five rows or overflow), restoring its exact quantum value
    and HMR phase before H3 cleanup.  SUCCESS = Q45 emission beyond coefficient cleanup plus the generator
    full-domain exact proof.  INCONCLUSIVE = allocation fits but phase/owner proof differs.  KILL this
    v10-retirement route if v10 is in fact live in a row/overflow or the restored owner cannot repay the
    HMR sign exactly; do not repeat it unchanged.  The separate sign-15 synthesis route remains active
    **WAKE 2026-11-19 07:xx UTC — THE Q45 STACK NOW REACHES THE TAIL; ONLY THE TAIL REMAINS.**
    The previous wake's stack (h0 packing + v10 retirement + endpoint borrow + disposable divider +
    exact cap-18 second loader + dirty-terminal coefficient inverse + keep-sign15) was reconstructed
    as work/evo/configs/v013.json and instrumented with a width profiler
    (work/evo/patches/patch_width_profile.py).  Every phase now fits Q45 EXCEPT the tail: the T2
    donor-block replay (agents/width/plans/T2_decoder_capture.json + agents/width/src/block_replay.py)
    allocates 7 donor scratch wires (q8,q21,q34,q36,q38,q47,b276), 2 freed by ZERO items, so **6 are
    simultaneously live → tail peak = 40 base + 6 scratch = 46**.  The published Q46 build peaks at the
    same place, so the tail is binding in both.  Our live set at A_restored is EXACTLY the 40 wires the
    plan maps (v8+h10+flags4+A13+H5) and all 40 are live again at block exit (45 = v12+h10+flags4+A13+H5
    +phase_snapshot1), so no entry wire can be freed.  **Stage map: work/evo/WIDTH_MAP.md.**
    **KILL CRITERION for the tail: the T2 tail needs a native re-derivation with ≤5 simultaneous scratch
    wires, or ≥5 extra "wire is identically zero" points in the donor block (the plan records only 2 ZERO
    items).  The alternative SNAPSHOT2_TAIL path is unusable — decoder_snapshot_cleanup_q48.py is absent
    from the published tree.**  COST REALITY CHECK (new, important): even a successful Q45 emission is NOT
    a score win — Q45×1743.42 = 78,454 vs our public leg 74,560.91 (Q44).  The competitive threshold is
    **Q42** (73,206 ✓) or Q43 with ≤1733.9/shot (−10 Toffolis) or Q44 with ≤1694.6 (−49 Toffolis).  The
    invsqrt lane therefore needs **3 more wires** below the Q45 stack, i.e. Q45 is a method milestone, not
    a submission milestone | 2026-11-19

H3 | Top-2 mechanism is discoverable from public traces | aadi_stonks 31.50404 / Z³C¹oherence 31.42723;
    gap = ×2.87 product; if all-DQI-width ⇒ Q≈526 (41% cut) — likely a mix (their invsqrt/chem also better?)
    | unknown, potentially +1–2 GM | deep recon pass: pull ALL aadi_stonks + Z³C¹oherence public
    kernels/datasets/votes timestamps, diff submission cadence vs score jumps to infer per-leg improvements;
    check kaggle forum posts | NEW | only surface recon done (LB rows) | 2026-11-18

H6 | GENERATOR-LEVEL EVOLUTIONARY SEARCH (AlphaEvolve-style) can beat hand-patched public trees |
    LLM proposes CODE mutations to the generator; automated evaluator verifies+scores; a population
    DB keeps the best; next-generation prompts are assembled from the best-so-far. Their closest
    result to us: "proposed a Verilog rewrite that REMOVED UNNECESSARY BITS in a key, highly
    optimized arithmetic circuit… must pass robust verification" (DeepMind, May 2025) |
    +0.1–1.0 GM (any width cut at invsqrt or DQI; the objective function is exact, so every
    improvement is measurable) | BUILD the evaluator + population harness for the CHEAP leg first
    (invsqrt: 74 s rebuild + exact score formula) — cheapest discriminating test: evaluate ≥6
    generator variants (knob settings + patch toggles) through ONE reproducible pipeline and
    produce a scored ranking. SUCCESS = a variant scores strictly better than baseline
    (→ SPRINT) or the harness proves baseline locally optimal (still a usable search substrate).
    KILL = baseline score cannot be reproduced within ±0.01 across 2 runs (evaluator too noisy →
    search impossible). NOTE: H1 proved the DQI circuit is flat-wide (no instance-level slack), so
    the search MUST operate on the generator, not the instance — that is exactly what H6 does |
    NEW | doctrine rules 22–26 added 2026-11-18; population store to live in work/evo/population.json |
    **TESTING 2026-11-19 — EVALUATOR LIVE AND REPRODUCIBLE.** work/tools/evo_build.py (emit + exact
    cost model) + evo_sweep.py (build → score → population DB → ranking) + evo_pop.py (population store)
    work; baseline v001 reproduces EXACTLY: cost_model 80,565.24511023414, kmb_sha256 5bd8d9d3… in ~10 s
    per variant (reproducibility criterion met; same bytes → same score, as the no-resampling rule
    requires).  Population work/evo/population.json holds v001–v015 with scores, score parts and
    artifact pointers (SCORED = emitted+modelled; VERIFIED is reserved for the proved ones).  Sweep
    ranking so far (lower cost is better): v001 baseline 80,565.25 · v004 (retire 13,14,15) 80,565.25
    (byte-identical kmb — retiring 15 is a no-op because _SAT already forces 15 into RETIRE) · v005
    (W2_V10_G1=0) 80,611.25 (worse).  **Four cheap kills recorded:** (a) kickmix's builder ALREADY reuses
    freed wire indices (alloc3→free q1→alloc1 returns q1) ⇒ a free-list wrapper is not an untapped
    lever; (b) loader work_cap only sets the TRANSIENT peak (the loader frees all but its 16 outputs) ⇒
    lowering the cap does not lower the global peak unless the loader's own transient peak binds; (c) the
    divider is NOT the binding phase (39–40 live while the global peak is 46) ⇒ retiring MORE signs
    cannot lower the global peak, and retiring fewer (v002/v003) overflows at 47; (d) the published syed
    tree contains NO Q43/Q44/Q45 variant anywhere (all research artifacts are Q48/Q49) ⇒ Q46 is the
    narrowest available configuration.  Full stage map: work/evo/WIDTH_MAP.md.  H6 is therefore
    CONFIRMED as a working search substrate but has NOT yet produced a better variant; the search space
    is now measured (width ledger + cost ledger), not guessed | 2026-11-19

H7 | DQI width is bounded by the verifier's syndrome INPUTS: Q ≥ n·b = 70·12 = 840 | the verifier
    writes the syndromes into the circuit's S0..S_{n-1} registers (verify_submission_dqi.py:376-382:
    write_across_shots(syndrome_array, input_syndromes) then requires them restored) and
    validate_registers forces exactly those registers to exist ⇒ our 890 = 840 input wires + 50
    ancillas; the DQI width prize is therefore capped at (890/840)² = 1.121× ⇒ **+1.1 GM max**, and the
    real DQI lever is T (mean Toffolis, currently 367,789) and not Q | +1.1 GM (width) / up to +3 GM (T)
    | read the DQI verifier's score formula and our dqi.kmb's register map; confirm 840 input wires and
    count our ancilla wires | **CONFIRMED (source-read) 2026-11-19** — the width ceiling is 840; H1's
    flat-wide finding is now explained (the 840 input wires are held for the whole circuit).  ⇒ any DQI
    improvement must come from fewer ancillas (50 → 0) or fewer Toffolis; both need a DQI *generator*,
    which is not public | 2026-11-19

H8 | invsqrt rotation cost is a function of the circuit's numerical MARGIN, not of its gate count |
    official verifier: eps = π·min_margin/2^64/n_rot, price = 0.56·log2(1/eps)+5.3, score =
    Q·(toffolis + T/4 + n_rot·price/4).  min_margin = min over shots of (tol(x) − |phase error(x)|) in
    units of 2^-64 turns ⇒ **a more accurate circuit (bigger margin) has CHEAPER rotations.**  Our syed
    emit: margin 124,370,688 units ⇒ eps 6.42e-13 ⇒ charge 230.85/shot.  tol(x) = 2^-24·β/√x, so
    tol_min ≈ 6.2e8 units ⇒ the best achievable charge is ≈219 (−12/shot = −0.7% of the leg) | +0.08 GM
    if the public leg's margin is at the syed level | read the official verifier's reported rotation_eps
    and margin for our PUBLIC 44q file and compare with the syed emit | NEW — cheapest test is one
    verifier run with a margin report; the prize is bounded and small, so it only matters if the public
    file's margin is far from tol_min | 2026-11-19

H4 | DQI rep_factor has headroom | our 5f901c55 rep ≈ 1.1911 vs floor 1.19126 ⇒ likely ~0 room, but the
    formula R(eps) = ln2/−ln(½+2√eps) depends on decoder epsilon | tiny | read verify_submission_dqi.py
    scoring path end-to-end; check if rep is schedule-controllable | NEW | — | 2026-11-18


    formula R(eps) = ln2/−ln(½+2√eps) depends on decoder epsilon | tiny | read verify_submission_dqi.py
    scoring path end-to-end; check if rep is schedule-controllable | NEW | — | 2026-11-18

H5 | Public release ride | maoxin123 iterates fastest (v27→28.17 in one day, owns rescheduler); asterios/
    boristown/ozertuu active | unknown, historically +0.03–0.3/release | watchpub timer (active, 20 min)
    → on any leg improvement: two-receipt gate → submit | ACTIVE (passive) | v130→v131 adoption gave +0.030
    | 2026-11-18

## KILLED (evidence recorded — DO NOT re-enter)
- H2 v8-specific product retirement: after adding explicit post-product P/seed/h owners, v8 still
  requires 9 independent dependencies (D6,D9,D11,v7,v11,h1,h2,h3,h4); the dependency certificate is
  too wide for the critical interval.  Do not repeat this route (work/recon/h2_post_product_map.json,
  2026-11-18).
- Z_POW same-wire merges on 563d0583/0af21cb8: 0 mergeable pairs (work/tools/merge_scan_kmx.py; all 43
  angles exact 2⁻⁶⁴ multiples so merges would be phase-exact, but no candidates). 2026-11-18.
- Functional Z_POW merge (Syed's merge_zpow.py, same-Boolean-feature, full-domain): groups_merged = 0 on
  563d0583 (t_before 1, 33 rotations, 38 Z_POWs). 2026-11-18.
- DQI measure-out extra-0 (Grant's pass, all flag combos): 0/3979 pairs servable on BOTH 575b043f and
  5f901c55 (boristown's six-product patch left nothing). 2026-11-18.
- DQI extra-1 joint-pair serving: 162 pairs servable but score ∝ Q² ⇒ +1 wire costs 0.2246% vs 0.0441%
  saved ⇒ NET LOSS. Any pass that adds wires loses. 2026-11-18.
- Chem loader lanes: cache/payload fusion net-zero (268→268); narrower local loaders can't move global
  Q=427; chem Q/T pinned by SpinFreeData_V1 analytic model (boristown published failed-experiments).
- Chem angle-LP re-costing: +0.0002 GM (prior cycles).
- ozertuu "Residual Sibling Gating Apex" = Name-That-LLM competition, not QCC. 2026-11-18.
- heliosli drift: dataset unchanged since 11-15 13:32, owner dormant. 2026-11-18.

## FACTS PINNED
- Best row v131 = 28.18084 (ref 58487983, clean draw). Best public tree, adopted verbatim.
- DQI score = rep × Q² × toffoli_mean. 1 DQI qubit ≈ +0.021 GM at Q=890. 1 DQI toffoli ≈ +2.6e-5 GM.
- invsqrt score = Q × (T_mean + T/4 + n_rot·rot_price(eps)/4); 1 invsqrt qubit ≈ +0.077 GM.
- Frontier: #1 31.50404, #2 31.42723 ⇒ ×2.867 ratio product over us.
