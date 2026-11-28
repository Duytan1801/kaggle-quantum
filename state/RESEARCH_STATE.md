# RESEARCH STATE — live hypothesis queue (agent-maintained; rewrite freely)
# Format: H# | claim | mechanism | est GM | cheapest discriminating test | status | evidence | updated
# Rules: never re-run a KILLED test; re-rank by expected-GM/effort after each resolution.
# Last full re-rank: 2026-11-25 01:20 UTC (v148 submitted; chemistry frontier jump; H38 killed — see the LAST section)

> **NEWEST (2026-11-25 01:2x UTC): v148 SUBMITTED (ref 58859204), predicted GM
> 33.21008.**  v147 + goodpjw2008's 3,334-T chemistry loaders (T 13,168,
> lambda_eff 46.91432641685298, chemistry PASS 250,195,979.3541336).  H38
> measure-first rewrite KILLED (0 candidates).  Details in the last section.

## LATEST STATUS (2026-11-23 01:20 UTC)

* **v146 is the new SCORED BEST: board 33.17029** (ref `58749949`, COMPLETE
  2026-11-23 00:34:54 UTC).  Prediction
  33.1703303503537523913065411197878713240478112544176321620074 → displayed
  error **-0.00004035**, inside the public-salt band (v144: -0.00004472).
  v146 = invsqrt `bb676b95f94c` + DQI `4b5721411adc239f` + chemistry
  `e7f08627208c` on the shared 3,357-T loaders.  Evidence:
  `work/receipts/V146_BOARD_SCORE.tsv`, `work/receipts/V146_RECEIPT.json`.
* **Scored-best predecessor:** v144 (ref `58713892`, board 33.14394).
* **v145 = the exact 18 bytes of `ozertuu/google-quantum-ai-vqcc-33-170350` was
  REJECTED by the gate.**  moat-lab v59 ran the unchanged official DQI
  verifier on the exact snapshot bytes: 2 value errors / 102,400 shots, cost
  307,632,423,468.0979 instead of the claimed 305,041,160,753.34.  The removed
  `CCZ q63 q507 q204 if b49140` is NOT redundant (the public log only
  verified chemistry).  Implied composite 33.0769512773 — **-0.067033 GM versus
  v144**, so submitting it would have hurt.  Evidence:
  `work/receipts/V145_MOAT_RECEIPT.json` (verdict V145-RECEIPT-FAIL),
  `work/recon/public_harvest_2026-11-23_v145_reject.md`.
* **NEW TOP HYPOTHESIS H30 — the q2026-v154 GENERATOR-SOURCE lane.**  The
  never-radar-seen kernel `dziyanavalenta/q2026-v154-submission-nb` ships
  **generator sources** for all three legs (isr / DQI / chemistry), each a
  fail-closed traced package (`build.py` + `BUILD.json` + `MANIFEST.json` +
  `SHA256SUMS` + `RECIPE.json`), preserved at `work/gens/q2026_v154/`.
  Its v154 *tree* is dominated (measured: invsqrt PASS 62,993.5511616945 @
  39 q vs our 60,927.57739905387 @ 37 q; chemistry PASS 256,334,995.4141029
  vs our 251,089,557.46576697), but its ISR bundle contains
  `invsqrt_fc_narrow.py` — the *checkpoint-schedule carry narrowing* mechanism
  that the H24 lane proved was the only route to fewer wires — plus a lane
  search, a cubic-rank compressor, a SAT tail optimiser and LUT/angle
  synthesis.  Evidence: `work/recon/q2026_v154_generator_sources_2026-11-23.md`.
* **H30 progress (2026-11-23 01:2x UTC).**
  * The ISR generator **builds byte-exactly locally** (exit 0, every
    `SHA256SUMS` entry MATCH) — the capability works.
  * **T1a (`I39_CAPS=H1=38,DIV1=38,DIV2=38,END=38`) is INCONCLUSIVE, not a
    kill**: the emit fails with *"no schedule within 1 temporaries"* inside
    the **H1** section (`invsqrt_fc2_patch_h1c.py:889 c.tag("H1")` →
    `chiprog.emit`).  Baseline anatomy: `cap 39 live 37 C 2` — **37 live
    wires + 2 clean wires = 39**.  The binding constraint is the *live* count
    at H1 (a 38 q plan needs live <= 36 there), not the DIV/END caps.
  * The leader's own `inv_i39_relabel.py` (an exact busy-segment relabeller,
    HMR outcomes 0/1 and two random seeds) **confirms** both circuits are at
    their peak: our 39 q generator build → "peak busy 39"; the public 37 q
    build → "peak busy 37".  `inv_i39_xpair.py` removes 69 redundant X-X
    pairs from the public 37 q build but does not lower its peak busy width.
  * ⇒ the width prize needs a **live-count reduction at H1** (one fewer live
    wire) or a different accumulator schedule, not a relabel.
* **Chemistry cross-matrix measured (9 cells, `work/tools/chem_cross_sweep.py`):
  the public floor is confirmed and NOT beatable by mixing tables with foreign
  loader sets.**  Best cell remains ours 3,357-T loaders + `e7f08627` =
  **251,089,557.46576697**; the v154 table on our loaders gives 251,164,958
  (+75,401) and our table on the v154 loaders gives 256,258,042 (better than
  v154's own 256,334,995 by -76,953).  3 of 9 cells FAIL.  ⇒ chemistry lane:
  no public headroom.
* **Queue: 9 new radar rows + 4 competition kernels the radar never saw were
  pulled and adjudicated; PENDING is empty again.**  New standing check added:
  **diff the competition kernel list against ADOPTED every wake** (the radar
  alone missed 4, including the v154 generator release).
* **Frontier: 33.83493** (`Entangled Team`); codebeforework 33.54018, Two-Qubit
  Gate 33.51863, Schrodingers Cats Lived 33.51568.  Corrected thresholds (the
  previously quoted 58,237.0814940 was the *old* leader 33.67349's threshold):
  matching 33.83493 needs an inverse-square-root cost <= **57,407.3438787498**;
  beating codebeforework needs <= **58,934.1648**.  With the 39 q generator
  build's per-wire cost 1,581.954652990519, a **37 q** build scores 58,532.10
  → GM **33.6168** (2nd place) and a **36 q** build scores 56,950.16 → GM
  **33.9252** (1st place).  One Toffoli removed at 37 q ≈ **+0.0067 GM**; a
  1 % cut in any single leg ≈ **+0.1105 GM**.
* Two further public DQI variants were found and are NOT adopted:
  `1e6787a0…` (v144's DQI with `CCZ q103 q54 q163` replaced by `CZ q103 q54`,
  published by asteriospanoras / evgendvorkin / hassanabdulhafid) and
  `141f02ac…` (ozertuu).  The first would be worth ~+0.000017 GM *if* the
  official verifier accepts it; it has never been verified, and the ozertuu
  sibling shows how such edits fail.
* **H24 width lane, measured 2026-11-23 (`work/recon/h24_width_state_2026-11-23.md`):**
  the 39 q generator build was rebuilt byte-exactly (SHA `68eb8c13ebc75…`,
  24,387 ops, 39 wires) and profiled: **0 mergeable wire pairs**, peak
  **39 live wires** (all wires) over 11,791 ops.  The pipelined carry rewrite
  is now **semantically exact** (state + phase equal on forced-zero,
  forced-one and 3 labelled random HMR streams) but does not lower the peak.
  The peak is the divider's **CSWAP sorting network**: 39 = 22 x-register + 15
  permutation participants + 2 control/scratch (q34, q35).  ⇒ A 37 q/38 q build
  of this generator needs an **algorithmic divider rewrite** (streaming divider
  with one carry + one buffer), not wire re-allocation, affine recomputation or
  a local gate patch.  This is now the only route to the 33.83493 leader.

## QUEUE (ranked)

H9 | **The public `asteriospanoras/qcc-circuit-atlas` dataset contains a full 18-file tree at GM 28.23162 — a
    submission-grade +0.0508 GM over our row** | dataset published 2026-11-19 00:39 UTC (after our last harvest
    sweep) and is NOT gated (`kaggle datasets download -d asteriospanoras/qcc-circuit-atlas`, 536 MB, Apache-2.0);
    it ships `frontier/qcc_28_23162_submission/` = the exact submission.zip that scored 28.23162, plus
    `receipt.json` with SHA-256 of every file and the official verifier results of that build | +0.0508 GM,
    immediate | **CONFIRMED AND SUBMITTED 2026-11-19 03:33 UTC — ref 58539070.**  All 18 files match the
    atlas receipt byte for byte.  OUR OWN official invsqrt verifier: PASS, score 74,405.67238374705,
    200,540,928 shots, worst_error_over_tolerance 0.9994556024653497, sha d0227f3c… — identical to the atlas
    receipt.  OUR OWN official dfthcsos verifier: PASS, score 294,642,170.565169, lambda_eff 46.921562797126406 —
    identical to the atlas receipt.  OUR OWN official dqi verifier: PASS, score 345,256,821,433.9815, 102,400
    shots, 0 value / 0 phase errors — identical to the atlas receipt.  **GM 28.180837 → 28.231630 = +0.050793.**
    TWO RECEIPTS: (1) static 18-file sha table work/sha_tables/sha_table_v132.txt; (2) moat-lab kernel v49
    in-kernel receipt work/receipts/V132_MOAT_RECEIPT.json — verdict V132-RECEIPT-PASS, shas_ok true,
    dqi PASS @102400 (127 s), dfthcsos in-kernel PASS (20.9 s), GM pred 28.23163020066719.  Snapshot dataset
    badboyhalo1801/qcc-release-v132 published (v2: moat-lab-compatible QCC_RELEASE_MANIFEST).  Gated zip
    persisted durably at work/trees/v132/submission.zip (zipsha 333ef190248cd5a2).  **We still owe this lane
    a re-check: the radar has since caught `ozertuu/28-23163` and `manvenderraparia/vqcc-28-23163` —
    a HIGHER published score than 28.23162.  Adjudicate both (H11).** | 2026-11-19

H11 | **The public-release radar was blind and unwired; a better public tree was sitting in plain sight for days**
    | `harness/watch_public.sh` polled `kaggle datasets list --sort-by dateCreated` and `--sort-by dateUpdated`
    — BOTH INVALID Kaggle sort keys (valid: hottest|votes|updated|active|published).  Every dataset poll failed
    on every cycle, and `poll()` sent stderr to /dev/null, so the failure was silent.  The dataset channel
    produced ZERO detections in its entire life — while competitors release trees as DATASETS.  Worse: the
    findings went to `/tmp/opencode/watch/new_releases.log` and NOTHING EVER READ THAT FILE; the wake prompt
    asked "Public tree changed?" with no sensor wired to the answer.  The watcher DID detect
    `ozertuu/28-23163` (23:49 UTC 2026-11-18) and `manvenderraparia/vqcc-28-23163` (01:45 UTC 2026-11-19),
    both BETTER than the tree we adopted hours later — both unread | a full day with no submission
    (last was 2026-11-18 00:48 UTC) | **CONFIRMED + FIXED 2026-11-19.**  New durable radar
    `harness/watch_public.py`: valid sort keys only; every poll VALIDATED (a bad answer is a loud POLL-FAILED
    line, never a silent no-op); durable state in `work/harvest/` (survives reboot); VERSION-AWARE keys so a
    dataset updated after we saw it re-enters the queue; SELF-GROWING publisher list so a new publisher cannot
    hide; QCC-relevance filter so the global head does not flood the queue; output = `work/harvest/PENDING.tsv`,
    which the wake prompt now REQUIRES the agent to read and adjudicate (`work/tools/harvest_queue.py
    list|take|done|add`).  Wired into `harness/campaign_wake.sh` (Stage 0, with a 15-min freshness guard so the
    wake never burns 7 min on a sweep the service just did) and into the systemd service
    `watchpub.service`/`.timer` (every 10 min, OnBootSec=2min).  Also: `work/tools/ds_scan.py` scans any
    downloaded dataset for a candidate tree; `submit_gate.sh` now persists the gated zip durably; `gh_sync.sh`
    now backs up `work/harvest/` + `watch_public.py` + the atlas toolkit.  **Verified live: 123 QCC-relevant
    releases queued, 0 duplicates, 0 false failures, 0 non-QCC noise; the radar caught
    `boristown/qcc-gap-3-residue-repair-and-c43-native-compiler` (a C43 invsqrt compiler — our top lever)
    within minutes of it being published.**  Remaining: adjudicate the 123 queued releases, and in particular
    the two 28.23163 releases and the new DQI candidates found in the datasets | 2026-11-19

H10 | Compiled-circuit surgery on the Q44 invsqrt yields ≥1 GM | the atlas ships `tools/qccscope/` (numpy-only
    liveness, motif detectors, sampled value scan, exact cost model) and `tools/kmsim.py` (exact simulator that
    reproduces the official verifier's worst error/tolerance), plus 58 invsqrt `.kmx` text forms and two proven
    edit recipes (a splice and a dead-write fix) | up to +0.2168 GM for one wire (Q44→Q43), +0.0939 GM per
    Toffoli | `qccscope report --task invsqrt` on the frontier Q44 kmx, then apply the findings and confirm with
    `kmsim.py` over all 3,133,452 inputs | **TESTING 2026-11-19 01:5x UTC — FIRST REPORT DONE on the frontier Q44
    tree (work/atlas/kmx/invsqrt/frontier_28_23162.kmx, 20,526 ops, 44 q, 477 bits).**  Static 1,549 Toffoli-like
    (187 conditional); executed Toffoli mean 1,451.29 over 256 sampled inputs; inputs restored, 0 dirty ancillas,
    0 bad resets.  **All four exact Toffoli motifs are ZERO: A1 Toffoli-erased AND 0, A2 cancelling Toffoli pair 0,
    A3 dead write 0, A4s statically-zero control 0.**  (The atlas's own dead-write win was on a DIFFERENT, Q46 tree
    — `dcde70780434` — which is already spent.)  Sampled-only candidates (NOT proven, not submittable yet): A4v 4
    rare-active Toffolis, A5 9 affine Toffolis, A7+0 6 repeated products that fit with 0 extra qubits
    (+0.0320 pts, sampled).  **WIDTH IS THE OPEN LEVER: static peak 44 with 433 peak episodes; the greedy idle-gap
    cover is `[(wire 24, 428 episodes, 5,258 ops), (wire 0, 5, 35)]` with `uncoverable_episodes = 0`** — i.e. every
    peak episode has a live-but-untouched wire, so a Q43 re-allocation may be possible.  Kill criterion: if the
    idle-gap cover does not yield a provable Q43 (44→43) circuit that `kmsim.py` confirms over all inputs, close
    the compiled-level width lane and fall back to the generator lane.  Also note R1: the 33 rotations consume
    231.5 of 1,712.3 Toffoli-equivalent (13.5%) — the rotation synthesis budget is the single largest cost block
    and the margin headroom is 15.98× (H8) | 2026-11-19

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


H12 | **The chem leg's J (words per ANGLE circuit) is a free structural parameter — re-partitioning the same
    75 angle columns into fewer, wider circuits cuts Toffolis with the chemistry untouched** | the dfthcsos
    verifier scores `lambda_eff × T × Q`; `lambda_eff` comes from the FACTORIZATION npz, not from the
    circuits, while `T` = angles_toffoli + heuristic(6662) and `Q` = 84 (heuristic persistent) + J×brot +
    max(303, angles_temporary).  The verifier reads J from the CIRCUIT register layout, so J is free.  The
    generator is public: `marculera/dfthc-merge-pipeline` `tensorqrom.build_family(words, brot, j=...)` | the
    prize is up to −25% chem T ⇒ +1.2 GM, but J also adds 8 qubits per step (−0.176 GM/step) | rebuild our
    own family at J = 4,6,7,8 from the shipped npz's `angle_words` and score each with the OFFICIAL verifier
    (must reproduce the shipped 294,642,170.565 at J=5 first) | **KILLED 2026-11-19 — measured, see the
    KILLED section below.**  The mechanism is real (J is free, lambda_eff is exactly preserved) but the
    economics are negative with the public generator.

H15 | **The public invsqrt frontier keeps moving (ecf908fec987b61a = 74,383.698758 is now the best) and
    every new release is worth ~+0.003 GM** | maoxin123's 28.23 invsqrt lineage ships new .kmb releases
    (the combo that carried it to 28.23441); the DQI and chem legs are already at their public optimum, so
    invsqrt is the ONLY leg where a fresh public release still moves the row | +0.003 GM per release,
    ~20 min to verify (200,540,928-shot official run) | harvest every release, run the official invsqrt
    verifier, and adopt any circuit that beats 74,383.698758 | **ACTIVE** — v133 (ref 58555857) adopted
    ecf908fec987b61a on 2026-11-19; the queue sweep is now mechanical, so new releases arrive adjudicated

H16 | **A tree change does NOT re-draw the DQI salt: the DQI seed comes from the CIRCUIT's own SHA-256** |
    `verify_submission_dqi.py::_initial_seed(circuit_hash, salt)` hashes the .kmb bytes (not the submission),
    so the same DQI bytes give the same official draw; only a NEW DQI circuit is a new draw | removes the
    "changing the other 17 files can flip our board-clean DQI" risk; makes DQI-circuit choice the only salt
    risk | read the verifier source; confirm the sha in both receipts matches the tree file | **CONFIRMED
    2026-11-19** — v133 reuses v132's DQI bytes (15a4b7403356092e) and therefore v132's clean draw; the
    in-kernel moat-lab re-verified it (PASS, 0 value / 0 phase errors @102,400 shots)

H17 | **Our shipped members have never been tested against a private salt — the $150k is exposed** | the
    public board uses one salt; the private draw may differ, and one failed shot costs the whole submission
    (alexchilton's 8-salt table).  Our exact members (invsqrt ecf908fec987b61a, dqi 15a4b740, chem
    6ef06081) are NOT in that table | unknown; a single-shot DQI failure is catastrophic (≈ −9 GM) | run the
    official verifiers with `--salt` at 4-8 different salts (the moat-lab kernel does 1 DQI run in 127 s
    in-kernel, so 8 salts ≈ 20 min of kernel time) | **NEW — queued** (protects the prize, not the score)

H18 | **The J lever might still be live on the OTHER loader generator** | our shipped loaders (8,044
    angles_toffoli) beat marculera's tensorqrom at EVERY J (9,722 at J=6, 9,864 at J=5), so the good
    generator is ~18% better per circuit than the public one.  If THAT generator has a J parameter, the
    lever is worth ~+0.4 GM even with the Q cost | +0.4 GM if the source appears | find the source of the
    4,022-Toffoli ANGLE loader family (ozertuu's "quantum-sim-linalg-cache") | **BLOCKED 2026-11-19** — that
    dataset contains ONLY 18 .kmb + 1 .npz, no source code.  Re-open if a source release appears.


## FRONTIER SHIFT 2026-11-21 (the queue was 2 days stale — read this first)

| | 2026-11-19 (v133) | 2026-11-21 (v135) |
|---|---|---|
| board #1 | 31.74002 | **33.34845** |
| best public tree | 28.23441 | **33.07536** (goodpjw2008 output) |
| our row | 28.23441 (rank 838) | 33.07536 (ref 58645864, pending) |
| invsqrt | 44 q, 74,383.70 | **37 q, 60,955.33** (d2148a7c) |
| dqi | 890 q, 365,894 T, 3.4526e11 | **900 q, 316,131 T, 3.05042e11** (4b572141) |
| chem | 427 q, 14,706 T, 294.642M | **405 q, 13,322 T, 253.143M** (npz 6b9903dd + loader2 046679fe) |

The jump was **not** a new mechanism per task so much as three better circuits:
a 37-qubit invsqrt, a 900-qubit DQI with 316k Toffolis, and 405-qubit chemistry
loaders.  All three are public and byte-pinned in v135.

H19 | **invsqrt qubits are the dominant remaining lever: at 37 q, one qubit is worth
    ~+0.30 GM** | score = Q x (toffoli-equivalent), so a 1-qubit cut is a 1/37 =
    2.7 % cost cut = +0.9 % GM = **+0.30 GM**, versus +0.0002 GM for one Toffoli.
    The 44 q -> 37 q step bought +4.8 GM.  The generator is now PUBLIC:
    `tonylica/quantum-ai-32-85306-task-generators` ships `invsqrt/build.py`,
    `carry.py`, `divider.py`, `lend29.py`, `v50/apply_best.py`, `angles.json` |
    +0.30 GM per qubit | build the 37 q circuit from the public generator, confirm
    the exact 60,955.3267 receipt, then try one more borrowed wire (36 q) and score
    with the official verifier | **NEW / highest value**

H20 | **chem T is 51 % heuristic: 6,500 of 13,322 Toffolis are state prep + Givens,
    not the angle loaders** | resources from our own run: angles_toffoli 6,822
    (3,411 per pass x 2) + heuristic 6,500 (outer 337 + inner state prep 4,213 +
    Givens 1,950).  The heuristic depends on the factorization SHAPE, and the
    chemistry generator is public with editable `W (9,127,46)`, `H2_I (9,46)`,
    `Hsym_lower (2926,)`, `tree_edges (75,2)`, `angle_words (1219,75)` |
    a shape/refit that cuts 300 heuristic Toffolis = +0.02 GM; 1,000 = +0.08 GM |
    rebuild from `tonylica/.../chemistry/build.py`, reproduce 253,143,456.49, then
    sweep refits (prvsiyan's `code/refit_grg.py` in
    `prvsiyan/vqcc-verified-best-of-circuits-1106a`) | **NEW / medium**

H21 | **The private-salt penalty for a DQI shot error is bounded at ~-0.15 % GM** |
    alexchilton's 8-salt study: one failed shot in 102,400 raises the DQI cost by
    +0.46 % (repetition factor), i.e. -0.15 % GM, NOT a zero.  But the new
    4b572141 has only ever been run at the default salt | -0.05 GM worst case |
    run the official DQI verifier at 3-4 salts in-kernel on the v135 snapshot |
    **NEW / cheap (3 x 127 s)**

## FRONTIER UPDATE 2026-11-21 02:45 UTC (post v136) — read this first

| | v133 (2026-11-19) | v135 (02:10) | v136 (02:34) | board #1 |
|---|---|---|---|---|
| GM | 28.23441 | 33.07531 | **33.10022** | 33.34845 |
| rank | 838 | 25 | ~4-6 | 1 |
| invsqrt | 44 q | 37 q | 37 q | ? |
| dqi | 890 q / 3.4526e11 | 900 q / 3.0504e11 | same | ? |
| chem | 427 q / T 14,706 | 405 q / T 13,322 | **405 q / T 13,292** | ? |

H19 | **invsqrt 37 -> 36 q (+0.298 GM)** — STATUS: OPEN, but the naive version
    is KILLED.  Measured this wake: all 37 wires are live over ~80 % of the
    60,790-gate stream (per-wire must-hold segments 35k-48k lines); no two
    wires can be merged by relabelling, and the x-register is fixed at 22
    qubits by the spec (width = 2*n_p + 2 = 22), so 36 is the floor.  The
    remaining route is the borrow trick the public generator already uses
    (`lend29.py` transplants an un-add block onto a freed wire): find a wire
    that is provably free after its last use and re-home a block on it.
    Kill criterion: if no borrowable window exists in the 37 q circuit, the
    36 q target is dead for this lineage.

H20 | **chemistry T (13,292) — SPLIT: the loader lane is KILLED, the refit
    lane stays open** | measured: 2 x 3,396 (loaders) + 6,500 (state prep) =
    13,292; the public per-block minimum over 8 loader families is 3,393/pass
    (T 13,286, = Kotaro Terada's board row) but every loader that would reach it
    breaks the chemistry (error_1 256-9262 mHa vs the 20 mHa limit).  The
    loaders are dense 2,048-entry QROMs at ~5.3 Toffolis per output bit, i.e.
    near the practical floor, and their output bits are dense random Boolean
    functions of the 11 address bits (ANF ~670 monomials/bit) so no ANF rewrite
    exists.  Evidence: `work/recon/loader_floor_2026-11-21.md`.
    Remaining chem lane: a NEW angle-word discretisation (cheaper table AND
    cheaper to load) or a lambda refit (lambda is at its floor, +0.000 GM).

H21 | **DQI salt risk — CONFIRMED and quantified** | the official verifier at
    five salts: clean at the default salt and salt-v135-d, one value error at
    salt-v135-a/b/c; cost +0.459 % per failed shot.  Per-shot failure
    probability ~1e-5 => P(>=1 failed shot at the private salt) ~ 64 % =>
    expected private-board penalty ~ -0.05 GM (bounded, not zero).
    Evidence: `work/recon/dqi_salt_probe_2026-11-21.md`.

H22 | **NEW, TOP PRIORITY — DQI qubit count 900 -> 890 (+0.245 GM)** | the DQI
    score is R x Q^2 x T, so one qubit is worth 2/900 of the leg.  The public
    generator ships the DQI as editable KMX stages
    (`tonylica/quantum-ai-32-85306-task-generators`: `dqi/decoder/*.kmx.xz`,
    `dqi/d16/field_{1..4}_*`, `dqi/selector.py`, `dqi/stages.json`,
    `dqi/arithmetic.py`); the four D16 arithmetic sites are executed
    sequentially, so their temporary wires may be shareable.  Success
    criterion: a rebuilt DQI with Q <= 890 that the official verifier scores
    <= 3.0504e11 x (890/900)^2 = 2.9835e11 with 0 value / 0 phase errors at the
    default salt.  Kill criterion: if the four sites' temporary wires are
    simultaneously live (proved by a liveness analysis of the stage KMX), the
    qubit lane is dead and DQI must be attacked through T instead.

H23 | **NEW — DQI private-salt insurance (public-invisible, +0.05 GM expected)**
    | the Clopper-Pearson bound is FIXED at k=0 (eps_plus = 1 - 2^(-128/102400)
    = 8.66e-4), so a decoder with a lower per-shot failure rate costs NOTHING
    publicly but raises the probability of a clean draw at the unknown private
    salt from ~36 % to ~90 % (worth ~+0.05 GM in expectation).  Any public DQI
    variant with the same clean cost and a lower failure rate is strictly
    better.  Test: run the official DQI verifier at 8+ salts on each candidate
    DQI and compare the number of failed shots, not the score.

## FRONTIER UPDATE 2026-11-21 12:20 UTC (post H26 kill) — read this first

| | v135 | v136 (actual board row) | board #1 | our rank |
|---|---|---|---|---|
| GM | 33.07531 | **33.10018** (predicted 33.100221) | 33.34845 | ~42 (the 33.10020 cluster is 40+ teams deep) |
| invsqrt | 37 q / 60,955.33 | same | ? | |
| dqi | 900 q / 3.0504e11 | same | ? | |
| chem | 405 q / T 13,292 | same | ? | |

H26 | **KILLED 2026-11-21 — the invsqrt rotation angles are ALREADY minimax-optimal.**
    The phase error is a deterministic function of the angles (bit-identical
    signed errors across 4 independent outcome streams — the outcome-dependent
    part of the circuit lives entirely in the 17 free Clifford/T rotations, so
    a priced-only refit is salt-invariant).  The exact linear model
    `theta(x) = sum_k u_k V[k,x] + sign(x)` (sense matrix extracted in one
    instrumented simulation, `work/tools/invsqrt_sens.py`) turns the score
    objective into a Chebyshev LP: maximise `m` s.t. `|err(x)| <= tol(x)-m`.
    The LP returns `m = 36,584,657.8` = the current margin, zero violations:
    **no angle change can improve the margin.**  Worse, the lane's CEILING is
    `min_x tol(x) = 6.21e8` units (factor 17, i.e. **+0.13 GM at best**) —
    the +0.25 GM target was arithmetically impossible.  Dropping any priced
    rotation drives the margin to **-1.45e11** (the 33 indicators are linearly
    independent, Gram rank 33); adding bit-basis rotations costs more
    (+274 to +5,989 score) than the margin they buy.  Evidence:
    `work/recon/invsqrt_refit_2026-11-21.md`.

H24 | **TOP PRIORITY / ACTIVE — invsqrt generator 39 q -> 38/37 q (+0.15 / +0.45 GM).
    THE AFFINE SCAN IS COMPLETE; PLAIN LENDING IS NOT YET A WIDTH WIN.**  New tool
    `work/tools/invsqrt_affine.py` computes the GF(2) null space of the 39
    wire-value bit-vectors (exact over all 3,133,452 inputs).  The stride-25
    scan (975 points, `/tmp/opencode/affine39_full.json`) finds 205 op indices
    and 95 distinct dependency sets.  In the carry window the only
    non-trivial relation is **q29 = q5^q7^q9^q10^q13^q14^1**, exactly the loan
    in `carry.py`; it disappears when the loan is executed and returns when
    the loan is restored.  The tempting q30 relation belongs to an earlier
    forward product block (ops 6,100-6,725), not the q29 carry block.
    Crucially, the carry block simultaneously stores q29,q30,q31,q32,q33,q36,
    q37, so recoverability of q29's *pre-loan* value does not free a physical
    wire while the chain is live.  The remaining admissible mechanisms are
    therefore (a) a Boolean carry-chain rewrite that reconstructs/relocates
    one carry, or (b) an op-level physical allocation that shares a wire
    whose data is safely recoverable throughout the borrow window.
    Success criterion remains: a rebuilt generator circuit with **38 q** whose
    official verifier score <= 60,114 and whose phase is identical to the
    39 q build on all 3,133,452 inputs and all salt outcome streams.
    **Frontier calibration 2026-11-22 00:38 UTC (post v139):** the fresh board
    leader is `Schrödinger’s cat lived` / `pjmathematician` at **33.51568**;
    #2 `Syed Asad Ali` is 33.46157, #3 `codebeforework` 33.36663, and #4
    `Z³C¹oherence` is 33.34845.  Holding v139's public DQI and chemistry legs
    fixed, those rows imply inverse-sqrt costs **58,725.4560 / 59,010.8080 /
    59,515.9632 / 59,613.3522**, respectively.  H24's 38 q build (predicted
    cost 60,114, GM 33.255613) is therefore **no longer sufficient** for the
    frontier.  The 37 q build (predicted cost 58,532, GM **33.552564**) beats
    the leader by **+0.03688** and is the first generator width target that
    clears the current board.  Success criterion is correspondingly a
    semantically exact **37 q** rebuild (38 q remains useful only as an
    intermediate physical-allocation milestone).  Evidence:
    `work/recon/invsqrt_lend_scan_2026-11-21.md`,
    `work/recon/public_harvest_2026-11-22_v139.md`, and
    `work/recon/public_harvest_2026-11-21_v138.md`.
    Original entry:
    The public invsqrt generator (`/tmp/opencode/gens/x/invsqrt/`, sha
    `68eb8c13ebc75c5e443ed5a8c6357c2c77e6676c499ed1324108bf025faf1489`)
    builds a **39 q / 24,387 instr / 1,452 Toffoli-like** circuit worth
    61,696 (worse than our 37 q tree only because of the 2 extra qubits).  At
    38 q it would score 60,114 (GM 33.253) and at 37 q 58,532 (**GM 33.5518,
    +0.45 over the board**).  The generator already ships the lend machinery
    (`lend29.py` locate/transplant, `carry.py` `carry_window()`): a wire that
    holds an AFFINE function of other live wires is XOR-ed out, reused as
    scratch, and restored afterwards.  The public patch only saves 0.5
    Toffoli and keeps 39 q.

H25 | **KILLED 2026-11-21 BY MEASUREMENT — the extra salt-invariant basis
    function cannot pay for itself.**  The complete legal scratch-wire
    catalogue was extracted at all 33 priced-rotation positions and checked
    against six independent HMR outcome streams (four random, all-zero,
    all-one): 495 wire/position occurrences, zero stream mismatches, 104
    distinct bit-vector functions.  Exact all-input Chebyshev LP for every
    candidate found a best margin of 39,585,698.8 versus 36,584,657.8, only
    **x1.0820**, below the pre-registered **x2.96** break-even.  The best
    one-rotation circuit scores 61,210.8541, **255.5274 worse** than the
    33-rotation 60,955.3267 baseline.  Do not re-enter this lane.  Evidence:
    `work/recon/invsqrt_basis_probe_2026-11-21.md`, tools
    `work/tools/invsqrt_basis_probe.py` and `work/tools/invsqrt_basis_lp.py`.

H22 | **KILLED 2026-11-21 by measurement.**  The DQI generator reproduces
    `4b572141` byte-for-byte locally; the assembled 69.8 M-line KMX shows
    **900 simultaneously live wires** (840 syndrome + 60 ancillas), **0
    disjoint pairs**, and *all 900 wires have their last use in the final
    stage* `decoder/decoder_return.kmx.xz`.  The only editable quantum part
    (the 4 D16 field sites) holds just 850 of 318,972 Toffolis (0.27 %), so
    neither Q nor T is attackable with public tooling.  Evidence:
    `/tmp/opencode/dqi_build/{liveness,stage_map}.json`,
    `work/tools/dqi_liveness.py`, `work/tools/dqi_stage_map.py`.

H19 | **KILLED for our 37 q lineage (36 q is the spec floor).**  All 37 wires
    are live over ~80 % of the 60,790-gate stream; the x-register is fixed at
    22 = 2*n_p+2 by the spec, so 36 is the floor.  The live successor is H24
    (a different, cheaper circuit family).

H26b | **KILLED — rotation merge.**  `work/tools/rot_merge_scan.py` with the
    correct commutation rule (Z_POW is diagonal, so it commutes with diagonal
    gates and control-only touches, but NOT with X/CX/CCX *targeting* the
    wire, SWAP/CSWAP/H/HMR/R) finds **0 mergeable rotation pairs** on both
    our 37 q circuit and the 39 q generator build.  A permissive first pass
    wrongly showed 38 pairs; the refined rule kills them.

### CURRENT PUBLIC-RELEASE SWEEP (2026-11-22 00:44 UTC) — COMPLETE; v139 ADOPTED

`work/harvest/PENDING.tsv` is empty after the full semantic adjudication of
all 25 remaining rows.  Every row was removed only after its verdict was
appended to `work/harvest/ADOPTED.tsv`; the exact-byte triage is in
`work/recon/queue_byte_triage_2026-11-22.json`.

* **v139 ADOPTED:** exact output of `leotang09/vqcc-t7421-submission`.
  Relative to v138, only the chemistry leg changes: table `b3683e07` plus the
  15 T7421 loaders.  The unchanged official chemistry verifier PASSes at
  **251,692,077.714951** (T=13,244, Q=405,
  lambda_eff=46.92403505616352), both locally and in moat-lab v53 on the
  exact `badboyhalo1801/qcc-release-v139` snapshot bytes.  The same in-kernel
  receipt PASSes invsqrt at 60,955.32670759028 and DQI at
  305,041,647,011.3978 with 0 value/0 phase errors.  The fail-closed
  receipt is `V139-RECEIPT-PASS`; submitted as ref **58694635**, predicted
  GM **33.13881038958233**.
* Areeb Ali's distinct tree is the runner-up at chemistry cost
  251,693,790.80323407.  Leo's tree is cheaper by **1,713.08828307** cost
  units under identical invsqrt/DQI bytes.
* Alex/Mizero/Prvsiyan trees measure 251,773,628.0701481; GoodpJW/Haoming
  trees 251,774,061.4763462; Maoxin/working-loader trees
  251,774,848.45254695.  All are dominated by v139.
* Özer's advertised “33.138” kernel is actually an older 39 q/901 q portfolio
  with chemistry PASS 255,195,733.74 and GM 31.69497.  The one loader-only
  splice with a slightly cheaper inverse-sqrt reroll still has much worse
  chemistry and no better composite score.
* The remaining old 44 q/890 q dataset, the cluster-specialist output with
  a DQI value error, and all rows without a clean 18-file tree were rejected
  with measured reasons.

Detailed release evidence is in `work/harvest/ADOPTED.tsv` and
`work/recon/public_harvest_2026-11-22_v139.md`.


## KILLED (evidence recorded — DO NOT re-enter)
- H12 chem J lever (re-partition the angle columns into fewer/wider circuits): **KILLED 2026-11-19 by
  measurement.**  The mechanism is real and was verified end-to-end (the verifier scores the words it
  RECOVERS FROM THE CIRCUITS, not the npz; `onebody.signed_gauge` transforms our table into the generator's
  signed gauge with lambda_eff EXACTLY unchanged, 46.921562797126406, error_1/error_2 identical to 1e-13 —
  the naive per-word bit flip is wrong and gives lambda_eff 187.4 / error_1 15.2).  But the economics are
  negative with the public generator: J=5 (the shipped value) gives angles_toffoli 9,864 and Q=427
  (score 331,106,793.88 = 12.4% WORSE than the shipped 294,642,170.565); J=6 gives angles_toffoli 9,722
  (−1.4%) but Q=435 (+8 wires, +1.87%) ⇒ score 334,411,854.92, **13.5% worse**; J=7 uses 133 qubits and
  J=8 uses 140, both ABOVE the verifier's hard 128-qubit ANGLE cap ⇒ REJECTED (not merely worse).  A
  generator bug was found and worked around on the way: `tensorqrom.build_family` IGNORES its own `sizes`
  argument for the non-coded path (`coded_layout` returns the hardcoded J=5 `SIZES`, which covers 35 of
  the 7·J output bits and makes build_circuit assert "decomposition does not cover the tensor"); our sweep
  installs the partition through the module global (work/tools/chem_j_sweep.py).  Do not re-enter this lane
  unless H18 (the better loader generator's source) produces a J parameter.  Artifacts:
  work/tools/chem_j_sweep.py, work/tools/chem_j_sizes.py, work/tools/chem_gauge_probe.py,
  work/tools/chem_words_probe.py, /tmp/opencode/chem_j/sweep_results.json.
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

## FACTS PINNED (refreshed 2026-11-22 00:44 UTC)
- Latest submitted tree: **v139**, ref `58694635`, predicted GM **33.13881038958233** (pending at this snapshot).  v138 ref `58659698` scored 33.10186; v137 ref `58658870` scored 33.10185.
- DQI score = rep × Q² × toffoli_mean. 1 DQI qubit ≈ +0.0245 GM at Q=900. 1 DQI toffoli ≈ +2.8e-5 GM.
- invsqrt score = Q × (T_mean + T/4 + n_rot·rot_price(eps)/4).  In the editable 39 q generator lineage, the measured 38 q/60,114 build predicts GM 33.255613; the 37 q/58,532 build predicts **33.552564**.
- Frontier: #1 `Schrödinger’s cat lived` / `pjmathematician` 33.51568; #2 `Syed Asad Ali` 33.46157; #3 `codebeforework` 33.36663; #4 `Z³C¹oherence` 33.34845.  Holding v139's public DQI/chemistry fixed, those imply invsqrt costs 58,725.4560 / 59,010.8080 / 59,515.9632 / 59,613.3522.
- Public chemistry frontier is now Leo T7421 at 251,692,077.714951.  No inspected table/loader permutation beats it; H24's semantically exact 37 q physical allocation is the next material mechanism lane.

## 2026-11-23 05:2x UTC — WAKE 2: THE DQI ZERO-TEST-CUT MECHANISM (new, public, EXHAUSTED)

### DQI zero-test cuts — goodpjw2008's mechanism (adopted as v147's DQI)
`goodpjw2008/qcc-dqi-zero-test-cuts-lb-33-17067` ships tonylica's `4b572141` with
TEN gate rewrites and a **public LB of 33.17067** (vs our 33.17029):

| who | rewrite | Toffolis/shot |
|-----|---------|---------------:|
| evgendvorkin | `CCZ q103 q54 q163` -> `CZ q103 q54` | -0.50 |
| ozertuu | delete `CCZ q63 q507 q204 if b49140` | -0.50 |
| goodpjw2008 | `CCX a b t` -> `CX a t` at positions 17-24 of a 24-bit zero test | **-8.00** |

Measured by the OFFICIAL verifier on the same 102,400 shots for both files
(seed 777): 316,133.13 -> 316,124.13 Toffolis/shot (-9.00).  One Toffoli removed
from every shot = **+3.5e-5 GM**; one wrong shot = **-0.05 GM**, so a rewrite
pays when its expected wrong shots per 102,400-shot run are below 7e-4.

**THE MECHANISM IS EXHAUSTED (measured, do not re-enter).**  Their own scan found
**72** redundant-looking gates; they took 10 and left **62**: 23 failed on the
larger samples and **39 sit too early in their zero tests to pay off**.  Their
value simulator (bit-parallel, `dqiscan`) shows the wrong-shot count halves from
one chain position to the next, so the risk curve crosses the gain curve near
position 16 and they take 17-24.  Two independent teams (`liuzewen123`,
`thomasgamet`/`alexchilton`) shipped byte-identical or sibling trees the same
cycle, so this is a *public* frontier, not a private one.

### The chemistry floor moved (again) — `16b4f5b5e51b0777`
`varianceofx/vqcc-verified-3357-loader-portfolio` ships a table that is
**0.44424793 cost units cheaper** than our `e7f08627208c`:
official local PASS **251,089,557.02151904** (T 13,214, Q 405,
lambda_eff 46.917982054483744) on the same 3,357-T loaders.  Worth +2e-10 GM
(it is the floor, not the prize) but it is now the reference chemistry.

### The salt doctrine (alexchilton's, the most important new public fact)
The **PRIVATE** board re-runs the official verifiers with a salt nobody knows,
and **one failed task scores the whole submission 0**.  The verifier derives its
shots from `sha256(circuit bytes) + salt`, so **every new DQI byte string draws
its own number of inherited decoder failures** (~1 per 102,400-shot run, each
worth ~-0.05 GM).  The **public board's draw is a different draw from the
default salt**: on its own default salt `6f78ecdd` draws 4 failures and so does
`4b572141` on the same shots, but the public leaderboard draw of both had none.
⇒ **the default-salt verifier number is NOT the board number**; a predicted GM
must be calibrated against the board's own draw (our v144/v146 biases are
-0.00004472 / -0.00004035).
⇒ because the failure count is drawn from the file's own hash, switching DQI
files re-rolls that lottery but does NOT change its distribution; there is no
systematic edge in probing salts (the P(fail) is a property of the algorithm).

### Frontier re-baselined (2026-11-23 04:1x UTC board)
#1 `Entangled Team` **33.85279**, #2 `codebeforework` 33.56726, #3
`Two-Qubit Gate` 33.51863; we are **rank 214 at 33.17029**.
With v147's DQI + chemistry fixed, the inverse-square-root thresholds are:

| goal | required invsqrt cost |
|------|----------------------:|
| match #1 `Entangled Team` | **<= 57,318.1631** |
| beat #2 `codebeforework` | **<= 58,793.3204** |
| beat #3 `Two-Qubit Gate` | <= 59,049.5900 |

and the 39 q generator build's per-wire cost 1,581.954652990519 gives
Q=38 -> 60,114.28 (GM 33.319567), **Q=37 -> 58,532.32 (GM 33.617079, 2nd place)**,
**Q=36 -> 56,950.37 (GM 33.925509, 1st place)**.

⇒ **H24/H30 (the inverse-square-root width) is still the only lane worth a
week.**  Everything public is now at its floor: chemistry 251,089,557.02151904,
DQI `6f78ecdd` (-9.00 Toffolis/shot, exhausted), invsqrt `bb676b95`.

### H31 (NEW, ACTIVE) — CodeEvolve evolutionary search, now RUNNING on Kaggle
The search runs **in-kernel** (`badboyhalo1801/qcc-isr-codeevolve-evolutionary-width-search`,
private).  The evolved entity is a *build plan* for the q2026-v154 ISR
generator (`caps`, `env`, `stack_env`, `cfg` overlay); fitness = `-cost` with the
exact official model; the evaluator runs the real generator and the UNCHANGED
official invsqrt verifier (1/64 shot screen).  Full feature set: 3 islands
(which CodeEvolve spawns as **parallel processes** - the generator build is
single-threaded, 644 s on 2 cores vs 804 s on 6, so 3 islands really do run
concurrently on Kaggle's 12 cores), meta-prompting, grid MAP-Elites over
(Q x toffoli_like), PlateauScheduler exploration, ring migration, checkpoint
every 2 epochs, 8 h wall-clock watchdog.
Four kernel iterations were needed to get it alive; the three real bugs were
recorded in `KERNEL_WATCH.md`.

### 2026-11-23 06:2x UTC — **V147 GATE PASS → SUBMITTED (ref 58763051)** + apache v173 full-manifest audit

**V147 SUBMITTED** (3 slots left).  Tree = invsqrt `bb676b95f94c923c` (37 q,
unchanged) + DQI `6f78ecdd636051d4` (goodpjw2008's zero-test cuts) + chemistry
`16b4f5b5e51b0777` (varianceofx's table) + the 15 byte-identical 3,357-T loaders.
Gated zip SHA `dfdffd5042aa5687`, persisted at `work/trees/v147/submission.zip`.
Static table `work/sha_tables/sha_table_v147.txt`; receipt
`work/receipts/V147_RECEIPT.json` (verdict **V147-RECEIPT-PASS**, shas_ok true)
from **moat-lab v62** on the exact snapshot bytes:

| leg | status | measured | notes |
|---|---|---|---|
| invsqrt | PASS | 60,927.57739905387 | 37 q, 200,540,928 shots, worst_err/tol 0.99947 |
| DQI | PASS | 309,694,874,626.0435 | 900 q, T 316,122.95665039064, **4 value / 0 phase** errors, eps_plus 0.0010168 < 1/16 |
| chemistry | PASS | 251,089,557.02151904 | 405 q, T 13,214, λ_eff 46.9179821 |

**The DQI gate criterion was corrected and is now principled (measured).**  The
first v147 receipt (moat-lab v61, archived
`work/receipts/V147_RECEIPT_FAIL_DQI4ERRORS.json`) said FAIL because *our extra*
zero-error proxy rejected 4 failed shots — while the **unchanged official
verifier returned PASS** (its contract is `eps_plus < 1/16`, and 0.00102 ≪
1/16).  The public board's shot draw is **not** the default salt: three public
trees prove it (DQI `4b572141` drew 0 default-salt errors → board 33.17029;
`141f02ac` drew 2 → board 33.170350 = its CLEAN prediction; `6f78ecdd` drew 4 →
board 33.17067 = its CLEAN prediction).  ⇒ the default-salt failed-shot count is
a **lottery draw**, not a verdict.  New rule (`work/tools/build_moat_v147b.py`):
a DQI leg with failed shots is admissible **only** if `PUBLIC_DQI_EVIDENCE`
names the exact `circuit_sha256` we ship **and** a public leaderboard score for
it; otherwise REJECT (still fail-closed).  v147 cites two independent public
releases of those exact bytes at 33.17067.
Prediction for the board: **33.17067** on a clean draw (33.00336 if the board
re-draws the default salt's 4 errors).  Poller armed for ref 58763051.

**Public-release queue: 8 rows adjudicated with MEASURED numbers** (no row is
closed on a claim).  New tool `work/tools/chem_new_tables.py` measures any
candidate chemistry table on the shared 3,357-T loaders with the UNCHANGED local
official verifier (~20 s/cell):

| release | new member | measured | verdict |
|---|---|---|---|
| `dennis6886/quantum-circuits-21-37712-…` | chem `b6f06794` | PASS 251,089,557.72428524 | dominated (+0.7028 vs our floor) |
| `aakashhowlader/no-bodies-mix17-vqcc-33-17035` | chem `508364c7`, DQI `a931fcfe` | PASS 251,090,780.9397702 | dominated (+1,223.92); DQI is a metadata-only variant of tonylica `4b572141` (same gates ⇒ no cost gain); its 33.17035 is the salt lottery |
| `liuzewen123/qcc-3357-loaders-stock-dqi` | chem `e337917c` | PASS 251,089,557.50839654 | dominated (+0.4869) |
| `hassanabdulhafid/chronos-kickmix-…` | 13-file tree, chem `14d5cc25` | FAIL ("selection register must have exactly 12 qubits, got 11") | inadmissible: 5 loaders missing, invsqrt 260 q, DQI 1,893 q |
| `manwithacat/the-real-150k-…` | — | 18 files hash **exactly** to our v147 | independent public confirmation of v147 |
| `ishankarnick/santa-2026-frontier-programs`, `goodpjw2008/santa-2026-…-130-844` | — | — | rejected: Santa-2026 (other competition) / 404 |

**NEW CAPABILITY — harvestable dataset archives.**  `manwithacat/vqcc-apache-public-circuits`
404s on archive download (Kaggle builds the zip asynchronously) while its
**8,542 individual files are already published**.  Two new tools fix that:
`work/tools/ds_files.py` (full manifest through the CLI's page tokens) and
`work/tools/ds_get_files.py` (per-file `datasets download -f`).  ⇒ the apache
manifest is now fully harvestable.

**APACHE v173 FULL-MANIFEST AUDIT (704 circuits, new evidence).**
`structure/index.csv` + `parts/assembly_best.json` give verifier-measured costs
for 129 invsqrt / 153 DQI / 422 chemistry families:

* invsqrt best = **`bb676b95f94c` = ours** (60,927.577399, 37 q); runner-up
  `52e8d4e6649b` 60,955.298422 ⇒ **no public invsqrt headroom**.
* chemistry best = table `81dbfe56d339` (= our `16b4f5b5`), `verified_cost`
  **251,089,557.02151906** (their number) vs our local 251,089,557.02151904 ⇒
  **independent third-party confirmation of our chemistry floor**.
* DQI best = `1e6787a0` at clean 305,041,576,300.78 (implied T 316,131.148) vs
  **our `6f78ecdd` clean 305,033,672,024.33** (implied T 316,122.9567) ⇒ **we
  are 7,904,276 cost units BETTER**.
⇒ **v147 is the global public floor on all three legs**, confirmed by a third
party.  All upside is therefore the invsqrt **width** lane.

**H32 (NEW, from the apache negative-results ledger, `structure/stage_status.json`)**
— a *curated reading* of the public closure ledger, i.e. a map of what is
still open:
* invsqrt **square_root: "little-explored"** — "about an eighth of the 44-qubit
  pick and never changed in a public edit; one mechanism closed (further HMR on
  the square-root inverse and seed clear).  **Other constructions of the
  consuming square root are untried as far as we know.**"  ← the clearest
  untried mechanism on the whole board.
* invsqrt **table: "active"** — 64-row table resyntheses on the 44-qubit line;
  and the **divider's construction itself is "less explored"**.
* invsqrt arithmetic: active (steady small edits).
* DQI: extract / middle / synthesis **active**; **scan is closed-at-floor**
  (11 Toffolis per point is the floor for one degree-13 monomial root test).
⇒ H32 is cheap to test: it is a *generator-side* mechanism question for the
q2026-v154 ISR bundle (does the 44/46-qubit line's square-root construction
exist as source we can adopt?), not a re-run of a closed route.

---

## 2026-11-25 01:2x UTC — WAKE: v148 SUBMITTED (chemistry frontier jump), H38 KILLED

### V148 = v147 + goodpjw2008's shorter chemistry loaders — GATE PASS → SUBMITTED (ref 58859204)

The public frontier moved from 33.17067 to **33.2101** between wakes, and the
mechanism is the lane H35 was wrongly closed on: **chemistry loaders**, not DQI
or invsqrt.  Four public trees (`goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-21011`,
`ozertuu/...-33-2101-sota-apex`, `areebbb/qai-the-26-toffoli-cut-lb-33-21010`,
`mizeroluckygall/quantum-circuits-33-210-shorter-chem-loaders`) ship our exact
invsqrt (`bb676b95`) and DQI (`6f78ecdd`) and change only `dfthcsos/`.

Measured with the UNCHANGED local official chemistry verifier
(`work/toolchain/verifiers/dfthcsos/verify.py <dir> --shots-per-address 1`):

| tree | npz | T | lambda_eff | chemistry score | Δ vs v147 |
|---|---|---|---|---|---|
| **v148 = goodpjw2008 / ozertuu** | `573d10bed90b4ad7` | **13,168** | **46.91432641685298** | **250,195,979.3541336** | **−893,577.67** |
| areebbb / mizeroluckygall | `14e3e699aef7ab15` | 13,168 | 46.9143769105685 | 250,196,248.63913822 | −893,308.38 |
| evgendvorkin `proba-2` refit | (1.11 MB npz) | 13,168 | 46.91437686361922 | 250,196,248.38875583 | −893,308.63 |
| alexchilton 33.18 tree | `c7c288e13a602b8a` | 13,192 | 46.917982145460485 | 250,671,518.28748047 | −418,038.73 |
| lionalmedong 33.19287 | `093cf2ad5cd763c5` | 13,188 | 46.914532073979125 | 250,577,083.84161285 | −512,473.18 |
| v147 (previous) | `16b4f5b5e51b0777` | 13,214 | 46.917982054483744 | 251,089,557.02151904 | — |

The gain is **both** a shorter loader (T 13,214 → 13,168 = 10 loaders at
**3,334 T/pass**, 5 unchanged at 3,357) **and** a better weight refit
(46.917982 → 46.914326).  T dominates (0.35 % of T vs 0.008 % of lambda), but
the refit is free and real.

**Important correction to the cost model:** `angles_toffoli_per_pass = 3334`
with 5 loaders still at 3,357 proves the verifier's per-pass cost is the max
over the loaders the shipped **table actually invokes**, not over all 15 files.
⇒ the 5 unchanged loaders are dead weight in this table; H35's "public floor"
claim was based on all-15-invoked trees.  This is a new lever: a table that
invokes fewer/cheaper banks lowers T without touching the loaders.

Build: `work/trees/v148/` (18 files, `work/sha_tables/sha_table_v148.txt`);
the 7 unchanged members are byte-identical to v147 (verified).
Snapshot dataset `badboyhalo1801/qcc-release-v148`; moat-lab **v63 COMPLETE →
`V148-RECEIPT-PASS`** on the exact snapshot bytes: invsqrt PASS 60,927.57739905387
(37 q), DQI PASS 309,694,874,626.0435 (900 q, T 316,122.9567, 4 default-salt
failed shots → same bytes as v147, covered by `PUBLIC_DQI_EVIDENCE`), chemistry
PASS 250,195,979.3541336 (405 q, T 13,168).  Gate `GATE-OK 8516167498ef6812`;
receipt `work/receipts/V148_RECEIPT.json`.  **Predicted board GM 33.21008**
(clean DQI draw), matching the public 33.2101.

### H38 (measure-first Toffoli rewrite) — KILLED by structural measurement (0 candidates)

Re-ran the site census with the *correct* measure-first predicate (a Toffoli
CCX whose target ancilla is HMR-measured, unconditionally, before that wire's
next quantum read).  Result over all 312,246 CCX + 6,716 CCZ:

* `target_is_syndrome` 226,198 — the target carries the circuit's ANSWER, so its
  value cannot be traded for a phase;
* `read_before_measurement` 85,737 — every ancilla-targeting CCX is read again
  before its next measurement;
* `not_ccx` 6,716 (CCZ has no target), `no_later_measurement` 311;
* **candidates = 0 at every depth**, so arsen123's public "measure-first" 4-site
  rewrite cannot generalise to our DQI.  Their own `conditional_measure_validation.csv`
  shows parent and child executed Toffoli counts **identical** — a verified
  negative result.  Archived at `work/gens/arsen123_measurefirst_2026-11-23/`.
  Do not re-enter.

Supporting census (`work/tools/dqi_tof_sites.py`, `/tmp/opencode/tof_sites.json`):
900 q = 840 syndrome + 60 ancilla; depth histogram {0: 269,838; 1: 47,748;
2: 374; 3: 850; 4: 152}; 43,803 unconditional Toffolis target an ancilla;
80,632 HMRs, all 60 ancillas measured.

### DQI conditional-region census (new hard floor)

`work/tools/dqi_cond_blocks.py`: PUSH=POP=710,906, max nesting 12, 645,740
conditional regions (median 3 ops), 11.355 % of ops inside a conditional
region.  **49,124 Toffolis are conditional** (4,918 regions have ≥1; 10 regions
have ≥100; largest 819) and **267,934 are outside every region (hard floor)**.
Static 318,962 vs observed mean 316,122.9567 ⇒ implied skip rate 0.057793.
Consequence: the DQI upside is now (a) raising the 5.78 % skip rate, or (b)
turning depth-0 Toffolis into conditional work — each 1,000 mean Toffolis ≈
+0.035 GM; 900 → 882 q would be +0.45 GM.

### Public-release queue — adjudicated by measurement this wake

* `goodpjw2008/...33-21011`, `ozertuu/...33-2101`, `areebbb/...33-21010`,
  `mizeroluckygall/...33-210-shorter-chem-loaders` → **ADOPTED as v148**
  (goodpjw2008/ozertuu variant, the cheapest).
* `evgendvorkin/proba-2` → dominated (250,196,248.3888).
* `prvsiyan/vqcc-verified-best-of-circuits-1106a` (6.1 GB, 9 complete trees)
  → all dominated: alt_almond 255,211,486.70 (T 13,430); alt_maoxin_v55_2024 /
  alt_qc1_v57b / alt_v58b 251,089,554.74–251,089,563.87 (T 13,214);
  alt_tony_0023 254,640,803.04; alt_v30 255,345,329.79.
* `aslan007x/qcc-v4-chem` 251,089,554.7402866 (dominated); its portfolio /
  `atakanaldemir/...controlled-refits` / `kawh1111/qcomp-harvest-1124pc` all
  ship the same `17a7658245230231` npz on the old 3,357 loaders (dominated).
* `mzishran/...chemistry-refit` and `orel1986/qcc-331707-reclaim` → exact v147
  tree (chem `e337917c`) = dominated.
* `alexchilton/33-18-lb-...` → 250,671,518.29 (dominated; also a different
  invsqrt `6b592145`).
* `lionalmedong/...33-19287` → 250,577,083.84 (dominated).
* `arsen123/qcc-public-frontier-full-independent-audit` → its DQI
  `6faebf1cc1f0920c` measures 305,030,293,104.77 (T 316,119.45, 3.5 Toffolis
  better than ours) and invsqrt 60,927.610458 (0.033 worse) ⇒ net ≈ 0, not
  worth new DQI bytes with an unknown public draw.  Its chemistry = areebb's.
* `kirderf/...2711-reproduced`, `kozykappa/...`, `ranjeet258/qcc-nov12...`,
  `ranjeet258/qcc-1124-ten-published-decoder-rewrites`, `manwithacat/
  quantum-voodoo-2` → entirely different (older) portfolios, no leg beats ours.
* `manwithacat/vqcc-chemistry-negative-results` → **harvested as a research
  ledger** (479 rows).  The two chemically relevant open/partial rows:
  NR-0207 (weight refit at fixed words has ~0.09 % left ⇒ ~+0.003 GM, convex
  bound lambda_eff ≥ 46.8497) and NR-0303 (reopen: fit at the 20 mHa cap with
  sign-mixing M driven to zero).

### New ranked queue after this wake

1. **H39 (NEW) — chemistry: exploit the per-pass-max discovery.**  A table that
   invokes only the 3,334-T banks already ships 5 dead loaders.  Cheapest test:
   measure whether the 3,334-T bank set can be re-solved at 3,3xx with a
   different `brot`/word split (the `maoxin123`/`goodpjw2008` generator is
   public), and whether a table can be refit to invoke fewer banks per pass.
   Each −10 T/pass ≈ −0.007 GM.
2. **H40 (NEW) — chemistry: weight refit at fixed words on the shipped npz**
   (NR-0207's method).  Predicted ceiling ≈ +0.003 GM.  Cheap (CPU, hours).
3. **DQI lane (still the only large upside):** raise the 5.78 % conditional
   skip rate or convert depth-0 Toffolis to conditional work; 900→882 q is
   +0.45 GM but the width lane was closed (H22) and needs a new stage design.
4. **H32/H33 (invsqrt square-root construction / 44-q table resynthesis)** —
   unchanged, still the clearest untried public mechanism.

## 2026-11-25 12:0x UTC — wake after v149 scored 33.21179: chemistry plan model EXACT, three new probes

### What changed in our capability (this is the durable gain)

The chemistry "plan" scheme (goodpjw2008's `qcc-shorter-chemistry-loaders-lb-33-21179`,
version 17) is now **fully reverse-engineered and machine-checked**.  Before this
wake we could only re-emit goodpjw's ten published plans byte for byte; we could
not tell whether a *new* plan would be correct.  Now we can.

* `work/tools/chem_plan.py` — the validated emitter, now instrumented
  (`RECORD['fn'][qubit]` = the exact boolean function the emitter believes each
  feature qubit carries; `RECORD['names']` = the feature order).  `run_loader`
  also learned the `Z` gate (the old maoxin loaders use it).
* `work/tools/chem_rec.py` — compares the emitter's RECORD against an
  independent reconstruction of the same feature list.
  **Result: 0 feature disagreements on all ten public plans.**
* `work/tools/chem_struct.py` — reconstructs each public plan's 30 output
  deltas from the plan fields alone.  **Result: `OK` for all ten**
  (the plan model now reproduces the shipped circuits' semantics exactly).

Two model bugs were found and fixed (both were silent before):

1. the emitter's `pair()` indexes a **growing** `gens` list (bank-bit
   generators, then every cached AND appends its own `u & v`), so a cached
   feature may be a product of *previous cached features* — the cached bank
   features are NOT limited to degree 2 in the bank bits;
2. a mixed feature's bank mask is indexed by the **bank index** directly, not
   by `BANK[BANK[b]]`.

Confirmed semantics (all now verified against the emitter, not guessed):

* the QUADS feature is the **integer** AND `fun((LOW >> x) & 1 & (LOW >> y))`,
  i.e. `low_x AND (low >= 2^y)` — *not* `low_x AND low_y`;
* the incoming words satisfy `word[7j+6] XOR word[7j+5] == QUADS(j)` for
  **k = 1..14** (diff 0 for every batch), but **not for k = 0** (incoming state
  is zero, diff 1520) ⇒ a k=0 plan cannot use the QUADS features as the
  emitter does;
* the old maoxin loaders for k = 0,1,5,7,11 use **four** classical bits
  (b0..b3) plus conditioned `CZ`/`Z`, while the ten re-solved ones use one
  bit and no `Z` — the two families are structurally different, so the old
  five cannot be read as plans.

### Hypotheses resolved this wake

* **H45 (NEW) — reuse a solved plan's products for another batch: KILLED.**
  Products are functions of (bank, low) only, so in principle they are
  batch-independent.  Measured over all 90 (solved plan, batch) pairs:
  **0 hits** — no solved plan's product span contains another batch's target
  matrices (`work/tools/chem_reuse.py`).
* **H43 (NEW) — narrow the word register (`brot` 7 → 6): KILLED.**
  `brot` enters `T_total` directly (`2*(N-1)*(2*brot-1)` = 1950 of our
  13,166) and `Q_total` through `J*brot` (35 of 405).  brot = 6 would save
  300 Toffolis and 5 qubits (−3.5 % of the score) — but the official metric
  on 6-bit words **fails the gates**: error_1 4.150, error_2 0.858 Ha against
  the 0.020 Ha limit (`work/tools/chem_brot.py`).  Our shipped words sit
  *exactly* on the gates (error_1 = error_2 = 20.000 mHa, E_gap = 3.914898 =
  the strict floor), so `lambda_eff` is pinned by the accuracy constraints and
  precision cannot be traded for T.  **Never re-run.**
* **H44 (NEW) — cheaper factorization shape (R,B,C): MEASURED, BLOCKED.**
  The state-prep heuristic is strongly C-sensitive (R=9, B=127):
  C=46 → T_state 4550 / Q_state 370 (ours); C=16 → 2101 / 367; C=1 → 744 / 233.
  C=16 would cut T_total by 18.6 % (≈ +2 GM if `lambda_eff` held) — but C is
  pinned by the 20 mHa error_2 gate, and any change of the weights changes the
  words, hence **all fifteen loaders** must be rebuilt.  Blocked behind the
  plan search (H42).  Tool: `work/tools/chem_shape.py`.
* **H42 (chemistry plan search) — CAPABILITY CONFIRMED, SEARCH STILL OPEN.**
  * Reachability: `work/tools/chem_reach.py` builds the maximal quadratic
    space `Q = span{f} + span{f_i f_j}` and asks whether each output delta
    lies in it.  Control: all ten public plans test 30/30 (dim Q = 1217).
    The five unsolved batches are **not** structurally excluded —
    `dim span{D_i} = 30` and `rank(M_i) = 16` for every one of the fifteen
    batches, solved and unsolved alike (`work/tools/chem_dim.py`).
  * The search problem, precisely: choose n *pure products*
    `A_p = u_p AND v_p` with `u_p, v_p` linear forms over the plan's
    99-feature space such that `span{A_p}` contains `span{D_i}` modulo the
    feature span; the masks are then determined (the mask matrix must have
    rank 30 ⇒ n ≥ 30) and the linear rest is whatever is left.  Each output
    needs ≥ 8 products (rank 16, ≤ 2 independent bank directions per product).
  * goodpjw's own plans use 123–132 products with **≈50 products per output**
    (`work/tools/chem_prod.py`: product matrix rank 5–7, mask size 7–19
    outputs, both factors mix bank/low/mixed features) — far above the rank
    bound, so the scheme is **not exhausted**; a better search could in
    principle beat 205 Toffolis/loader.
  * goodpjw's own method is public in prose only ("plant low-rank elements in
    Z", "GPU FWHT", "matroid parity", maoxin123's note).  A random product
    search cannot work: the product variety has dimension ≈198 inside a
    1232-dimensional function space, so the probability that a random product
    lands in the 30-dimensional target subspace is ~2^-905.  A *structured*
    search is required, exactly as goodpjw describes.
  * Kill criterion for the next attempt (pre-registered): a bounded search
    that cannot produce a plan with **nP ≤ 132** for any of k = 0,1,5,7,11
    within one build day is killed as a mechanism; a plan with nP ≤ 157 already
    beats the old 240–245-Toffoli loaders and is worth ~+0.05 GM.

### Queue-hygiene fix (worth knowing)

`work/tools/auto_adjudicate.py` treated every queue row as a *dataset* and ran
`kaggle datasets download` on kernel slugs; 19 kernel rows were closed with a
bogus "don't have access to this resource" note.  The tool now carries the
queue's type column (kernel vs dataset), `harvest_queue.py add` takes the kind
explicitly, and the tree writer handles zip trees with a top-level directory
and directory members.  All 19 rows were re-queued through
`harvest_queue.py add … kernel` and are being re-adjudicated.

### Re-ranked queue after this wake

1. **H42 (chemistry plan search)** — +0.21 GM prize, capability now exact.
   Blocked on a structured product search (see the precise formulation above).
2. **H41 (invsqrt 37 → 36 q)** — +0.307 GM, unchanged; needs a different
   square-root construction (H32), not relabelling.
3. **DQI** — +0.45 GM for 900 → 882 q; H22 width lane closed, H32-m6 blocked.
4. **H44 (factorization C)** — +2 GM *if* a smaller-C table meets the 20 mHa
   gate AND the loaders can be rebuilt; both sub-problems are open.
5. **H40 (weight refit at fixed words)** — ceiling +0.003 GM, CPU-only.

## 2026-11-25 14:0x UTC — wake: the chemistry plan scheme is now an EXACT quotient-space problem (H46 killed)

### New capability (durable)

* `work/tools/chem_check_plan.py` — **the plan acceptance test**.  It emits a
  candidate plan with the validated emitter, simulates the circuit EXACTLY on
  all 1,219 addresses (every qubit is a boolean function of the address), and
  checks (a) the word registers move by exactly the batch delta, (b) the
  oracle is self-inverse (the loader is `|a>|z> -> |a>|z XOR f_k(a)>`, so
  applying it again must undo it — running the op list *backwards* is wrong,
  the list ends with the uncompute section), (c) every workspace qubit
  returns to |0>.  Known-answer control: batch 14 PASS (205 Toffolis),
  batch 2 PASS (215 Toffolis).
  The phase never has to be checked: the emitter's `CZ qa qb if b0` is
  conditioned on the `HMR` outcome and `q = a AND b`, so the measurement's
  phase flip is cancelled by the CZ on every trajectory.
* `work/tools/chem_prune.py` — **the quotient-space model of the plan
  scheme**, with a self-contained GF(2) basis (reduced row-echelon, with
  coefficient tracking) that produces CANONICAL coset representatives.

### The exact statement of the plan problem (this is the key result)

A plan expresses each output's batch delta as

    D_i  =  XOR_{p : i in M_p} g_p   XOR   R_i ,

where `g_p = u_p AND v_p` is one Toffoli and `R_i` is a *linear rest* — an
XOR of the cached features, applied with free CNOTs.  Let `F = span(features)`
(99 or 100 dimensions, all independent) and `pi: V -> V/F` the quotient map.
Then the plan is correct **iff**

    span{ pi(g_p) }   CONTAINS   Q := span{ pi(D_i) } .

Over GF(2) every element of a span is a subset sum, so this single global
condition is necessary *and* sufficient: the masks and the linear rests then
follow from linear algebra alone.  `V/F` is 1,120-dimensional (1,219 − 99),
`Q` is only **23** (non-swap) or **24** (swap) dimensions, and the measured
`dim F` is 99/100 for all ten public plans.

### H46 (NEW) — prune the public plans' redundant products: **KILLED**

* The 123…132 products of every public plan have **linearly independent
  classes** (`rank(pi(g_p)) = nP`), so the span is `nP`-dimensional while
  `Q` is 23–24 dimensional.  A greedy search for a sub-family of the *same*
  products whose span still contains `Q` needs **all** of them (measured for
  all ten public batches).
* Why: because the classes are independent, **each output's representation is
  UNIQUE** — the mask of every product is forced.  There is no freedom to
  re-mask.
* Directly measured: **0 of the 123…132 product classes lie in `Q`**
  (`work/tools/chem_qhit.py`); the outside-`Q` part of a typical class has
  ~534 set bits.  The products are generic with respect to `Q`.
* **Conclusion: the public plans are MINIMAL with respect to their own
  product set.**  The only way to a cheaper loader is a *different* product
  set whose classes span `Q`.  Never re-run the pruning idea.

### What a cheaper plan would be worth (pre-registered)

`nP` products cost `82 + nP` Toffolis per loader.  The public loaders cost
205…215; the five unsolved batches (k = 0,1,5,7,11) cost 240…245.
The lower bound is `nP >= dim Q` = 23.

| nP per loader | loader Toffolis | chemistry T (both passes) | GM |
|---:|---:|---:|---:|
| 123…132 (public) | 205…215 | 13,166 | 33.21179 |
| 80 | 162 | 11,206 | ~34.8 |
| 50 | 132 | 9,586 | ~36.0 |
| 23 (the bound) | 105 | 8,060 | ~37.9 |

So a search that reaches `nP <= 80` on the *five unsolved* batches alone is
worth ≈ **+1.2 GM**, and `nP <= 50` ≈ **+2.0 GM**.  This is the largest
single lever in the chemistry leg and it is now precisely posed.

### The search obstacle, measured

* The quotient `V/F` is 1,120-dimensional; `Q` is 23.  A *random* product's
  class lands in `Q` with probability ≈ 2^(23−1120) ≈ 2^−1097, and a random
  family of `m` products contains `Q` with probability ≈ C(m,23)/C(1120,23) —
  hopeless (this confirms the earlier "random sampling is dead" note with the
  correct exponents).
* The structure that makes a *structured* search possible: the bank-side
  features (68 cached ANDs + 7 address bank bits) span **76 of the 77**
  bank-function dimensions, so the per-column bank quotient is **1
  dimension**; the mixed features (bank function AND low==7/14) make the
  quotient vanish on the two special columns; the low-side features (4 low
  bits + 5 QUADS + 6 low ANDs) span 16 dimensions.  A product's class is
  therefore `pi(alpha_u alpha_v)` (one uniform quotient vector) plus
  `q_v(low)·[alpha_u] + q_u(low)·[alpha_v]` (a low-profile-weighted pair of
  quotient vectors) — i.e. every product's class is a *rank-≤3 object* in the
  quotient, exactly the "two dimensions per product" that
  goodpjw2008's published method prose describes ("plant low-rank elements
  in Z", "GPU FWHT", "matroid parity").
* goodpjw2008's own method is public only as prose in
  `work/gens/goodpjw2008_chem_2026-11-25/...ipynb` (md cell 1): block 1
  (8 outputs, 89 dimensions, 45 products), block 2 (force `u ⊗ x1 + v ⊗ x2`
  into `Z`, one per output pair), block 3 (8 outputs, 83 dimensions); their
  counts (260 dimensions for 24 outputs) match `nP = 130`.
* **Next experiment (H48, pre-registered):** implement the *planting* step
  alone — search for a small family of products whose classes span `Q` — and
  measure the achievable `nP` for one batch.  Kill criterion: if a bounded
  search cannot reach `nP <= 80` for batch 14 within one build day, the
  mechanism is killed; `nP <= 157` still beats the old 240…245 loaders
  (+0.05 GM) and is worth keeping.

### Queue

`work/tools/auto_adjudicate.py` re-adjudicated the 19 wrongly-closed kernel
rows (the tool had run `kaggle datasets download` on kernel slugs).  14 of
them are now closed by measurement; two of them
(`alexchilton/33-17-lb-…`, `prvsiyan/verifier-guided-…`) ship an invsqrt
that measures **60,927.5479** against our **60,927.5774** — a 4.8e−7
relative gain, i.e. **+0.000005 GM**, not worth a submission slot.  The
public chemistry frontier is still closed (every complete tree measured
250.16e6…321.3e6 against our 250.158e6).

### H48 (NEW) — the rigorous lower bound on the product count, and the exact
### factorisation a better plan must have

`work/tools/chem_dim2.py` measures the *direction* budget of a loader.

Write a product as `u.v` with `u = alpha_u + q_u(low)`, `v = alpha_v + q_v(low)`
(`alpha` a cached bank function, `q` a low function).  Then

    u.v = alpha_u alpha_v   (uniform over the 16 columns)
        + alpha_u q_v + alpha_v q_u   (bank direction x low profile)
        + q_u q_v                     (low only)

The first term is the same bank vector in every column, so it cancels in the
**column-difference pattern** `d_j XOR d_0` that a product has to reproduce.
What survives per column is a combination of **TWO bank directions**,
`alpha_u` and `alpha_v`.  Therefore:

* every product supplies at most two independent bank directions to all the
  outputs in its mask;
* the target's difference rows `{d_j XOR d_0}` over all 30 outputs span the
  **full 77-dimensional bank space** for every batch;
* hence **`nP >= ceil(77/2) = 39`** for every one of the fifteen batches
  (solved and unsolved alike).

Measured (v149 words):

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bank-direction dim | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 | 77 |
| **nP bound** | **39** | **39** | **39** | **39** | **39** | **39** | **39** | **39** | **39** | **39** | **39** | **39** | **39** | **39** |
| public nP | – | – | 132 | 132 | 132 | – | 132 | – | 127 | 132 | 132 | – | 132 | 127 | 123 |

so the public plans sit at **3.2x** the bound.  Two further measured facts:

* `S` (the sum over outputs of the rank of the 15 difference rows) is **450**
  for the five *unsolved* batches (k = 0,1,5,7,11) and **383…385** for the ten
  solved ones — the unsolved batches are genuinely a little harder, which is
  consistent with their loaders costing 240…245 instead of 205…215;
* the joint rank of the 30 outputs' difference matrices is only **28…30**:
  the outputs' difference patterns are nearly the same subspace, so the
  *variation* between outputs is small even though the direction space is
  all of F_2^77.

**The exact factorisation a better plan must have.**  Let the 39+ products'
directions `(alpha_u^p, alpha_v^p)` be a basis of the direction space and let
`x_p(j), y_p(j)` be their low profiles.  For output `i` and column `j` the
target row must be

    d_j XOR d_0  =  SUM_p c_i[p] ( x_p(j) alpha_u^p + y_p(j) alpha_v^p )

so the two coefficient columns that belong to one product must be
**proportional with a ratio that is the same for all thirty outputs** (the
profiles are global, only `c_i[p]` is per output).  That is the search
constraint, and it is checkable in linear algebra.

*Pre-registered kill criterion for H48:* a bounded search that cannot reach
`nP <= 80` for one batch within one build day kills the mechanism; `nP <= 157`
still beats the old 240…245 loaders and is worth ~+0.05 GM.

## 2026-11-25 15:5x UTC — wake: the chemistry plan problem is now EXACTLY
## characterised, and every cheap search variant is MEASURED dead

### The new facts (all measured, tools in work/tools/)

1. **The product classes fill the quotient space** (`chem_qdim.py`).
   `dim W2 = 1118` of `dim(V/F) = 1120` for batch 14 (1117/1119 for batch 2):
   the span of the 99x99 feature-product classes is **99.8 % of the whole
   quotient**.  `Q subset W2` ✓ (as it must be).  So the classes a product
   can have are *generic* in a 1120-dimensional space, and the counting is
   decisive:

   * the number of (u,v) factor pairs is 2^198, so the chance that a
     *specified* class is a single product class is ~2^-922;
   * the chance that a family of m independent product classes spans a
     fixed 23-dimensional Q is ~C(m,23)/C(1118,23): **2^-120 at m = 39**
     and still **2^-89 at m = 123** — goodpjw2008's own count.

   **Therefore a cheaper plan CANNOT be found by any random, greedy or
   factor-cover search.  It requires the structured "planting" search
   goodpjw2008 describes in prose.**  This kills (with the right exponent)
   the whole family of cheap ideas; it is the first time the exponent has
   been computed on the *actual* quotient space.

2. **The column blocking** (`chem_colrank.py`).  At every low column j the
   30 outputs' difference rows span `r_j` dimensions:

   | | solved batches (2,3,4,6,9,10,12) | 8, 13, 14 | unsolved (0,1,5,7,11) |
   |---|---|---|---|
   | r_j per column | 25…26 | 24…25 | **30** |
   | sum_j r_j | 386…388 | 373 | **450** |
   | rank of the union | 77 | 77 | 77 |

   So the unsolved batches really are harder (every column is full rank 30),
   and the public plans sit at 123…132 products against a direction bound of
   `ceil(77/2) = 39`.

3. **The public plans use everything** (`chem_featuse.py`): all 82 cached
   features (68 bank ANDs + 6 low ANDs + 8 mixed) are referenced by the
   products or the linear rests of every public batch.  There is **no free
   Toffoli** in the feature overhead — the 82 is irreducible as published.

4. **The public plan's products are dense and generic** (`chem_prof.py`,
   batch 14): every product's two factors are XORs of ~30…48 bank features,
   ~6…10 low features and ~2…6 mixed features; the 246 directions
   (123 alpha_u + 123 alpha_v) are **all distinct** and span rank 75 — the
   whole bank-feature space; the 240 low profiles are 120/123 distinct dense
   16-bit patterns (14…20 active difference columns per product).

5. **The fixed-factor idea, measured** (`chem_fixed.py`, `chem_fast.py`,
   `chem_cover.py`).  Fixing one factor u makes `v |-> pi(u AND v)` LINEAR,
   so the reachable classes form the subspace `L_u = span{pi(u AND f_j)}`
   (dim up to 97).  Scanned 545…645 candidate factors (every feature, every
   factor of the public plan's own products, random XORs):

   * the best single factor covers **5 of the 30** targets — and those five
     are the outputs whose class is ZERO (they are free: outputs 0, 6, 12,
     18, 24 need no product at all; this also explains the 10 "pair sums"
     found by `chem_pair.py`, all of them differences of zero-class
     outputs);
   * the sum of **12** such image subspaces (dim 1041 of 1120) still covers
     only those 5 targets: the 25 other target classes are generic with
     respect to them;
   * no non-zero pair sum `q_i XOR q_j` is a single product class — as the
     2^-922 count predicts.

6. **The exact shape of a better plan** (new reformulation).  Write a
   product as `g_p = u_p AND v_p` with `u_p = alpha_u + x(low)`,
   `v_p = alpha_v + y(low)`.  Its column-difference contribution is
   `d_y(j).alpha_u + d_x(j).alpha_v`, so a plan is a set of "slots"
   (a row-selector in F_2^15 and a direction in the 77-dimensional
   difference-row space), paired two per product, with the condition that
   for every slot the thirty outputs' slot coefficients are all multiples of
   ONE vector.  With `m = 39` products the 78 slot directions are almost a
   basis of the 77-dimensional row space, so that condition becomes a
   "Hadamard factorisation" of the targets' coordinate matrix — extremely
   restrictive.  **This is why goodpjw2008 needs 5.3x dim(Q) products and
   why the slack cannot be removed by choosing better products alone.**

### What is now known to be DEAD (never re-run)

* pruning / dropping public products (H46),
* random product search, greedy factor cover, fixed-factor cover,
  pair-sum trees (all measured above, with exponents),
* dropping unused cached features (measured: none are unused).

### The next move for H48 (now precisely specified)

Reimplement goodpjw2008's **planting** step, which is public only as prose
in `work/gens/goodpjw2008_chem_2026-11-25/...ipynb` (md cell 8):

> "**Block 1** has 8 outputs and 89 dimensions.  He collects hundreds of
> thousands of small spaces of low functions and looks for four that share
> an 8-dimensional output space.  **Block 2** reuses block 1's 45 products
> for free, and forces paired elements into Z.  **Block 3** removes one whole
> low column from every remaining output."

That is a search over *spaces of low functions* (subspaces of F_2^16) whose
products share an output space — not over individual products.  It is the
only formulation left that is not excluded by the counting above, and it is
the one thing that could reach nP < 80 (worth +0.5…+3.4 GM).  Kill
criterion (pre-registered): if the planting search cannot produce a plan
with **nP <= 100** for batch 14 within one build day, the chemistry-plan
lane is killed as a mechanism and the chemistry leg is declared closed at
goodpjw2008's 123…132 products.

## 2026-11-25 15:2x UTC — wake: the exact peephole optimizer is MEASURED
## worthless on our tree (H49), and the release queue is repaired

### H49 (NEW, KILLED) — the "exact optimization compiler" of
### bandlapallisudharani/qcc-target34-all-three-circuit-optimization

The release promises "target 34" but its own receipt shows the **measured**
score is **31.679** (chem 255,384,620.97, invsqrt 63,055.0444, DQI
3.3267e11) — all three legs are WORSE than our v149
(chem 250,157,973.26, invsqrt 60,927.5774, DQI 3.0503e11), so it is
**dominated**.  Verdict recorded in ADOPTED.tsv.

What it ships is nevertheless a real mechanism, so it was harvested to
`work/gens/bandlapalli_target34_2026-11-25/` and ported to
`work/tools/kmb_opt.py`:

* `pair_pass`   — commuting Toffoli/CCZ identities (identical pairs cancel;
  two Toffolis with the same target and ONE shared control become
  CX·CCX·CX, i.e. **2 magic ops -> 1**; the same for the same controls with
  different targets; and the CCZ version);
* `measure_pass` — the "measure-first" rewrite (a target-only X/CX/CCX
  before a measurement on that wire is moved after it and becomes a
  conditional phase correction);
* `anf_pass`    — exact affine-frame ANF reconstruction: a short block is
  synthesised symbolically and replaced by a shorter equivalent, with an
  independent symbolic equality check before acceptance.

**Measured on OUR v149 tree (`work/tools/kmb_opt.py`):**

| leg | magic ops before | after | rules fired |
|---|---|---|---|
| `dfthcsos/angle_k_14.kmb` | 205 | 205 | **0** |
| `invsqrt.kmb` | 1553 | 1553 | **0** |

and the release's own receipt shows what the optimizer can do at its best:
on their 351,536-CCX DQI it saved **7** CCX (`raw_ccx_saved: 7`,
`pair_rewrites: 1`, `measure_ccx_saved: 6`) for a total tree improvement of
**+0.00022 GM**.  At our v149 operating point
(`dGM = GM/3 * dT/T`) 7 DQI Toffolis are worth **+0.00024 GM** — i.e.
*nothing*.  **H49 is KILLED: the exact peephole optimizer cannot move our
score.**  Do not re-run it on our trees.

Why it cannot fire here (measured, `work/tools/kmb_mix.py`):

* the chemistry loader's 205 magic ops are 82 cached-feature CCXs + 123
  product CCXs; the products' two control wires are *feature* wires whose
  value is recomputed by each product's own `pre` CNOT network and restored
  afterwards, so no two Toffolis share a control **value**, and the
  "same target + one shared control" rule needs one;
* the loader's 57-Toffoli target has 57 *different* control pairs, so the
  rule does not fire (3 window opportunities in 48 gates, 0 surviving the
  commutation test);
* `invsqrt.kmb` has 1470 Toffolis on 37 targets but again no shared
  control pair (59 window opportunities, 0 surviving).

The *algebraic* version of the rule (two products sharing the same first
factor `u` merge into one Toffoli because
`(u AND v1) XOR (u AND v2) = u AND (v1 XOR v2)`) is **also dead**: the 123
products of a public plan have **123 distinct `alpha_u`** and **123 distinct
`alpha_v`** (`work/tools/chem_prof.py`), so no two products share a factor.
That is a further reason the plan search (H48) must find products that are
*simultaneously* correct and factor-sharing — which is exactly the
structured "planting" search goodpjw2008 describes.

### Queue hygiene (two bugs found and fixed this wake)

1. `radar_queue.py` called `harvest_queue.py add <ref> 'kernel' <title>
   ...` but the tool's signature is `add <ref> <note> <kind>`; the title
   landed in the note column, the kind became the title (rejected -> the
   literal string `manual`), and the **title was lost**.  Since
   `auto_adjudicate.py` reads column 0 as the kind and defaults anything
   unknown to `dataset`, all **243 re-queued kernels would have been handed
   to `kaggle datasets download` and closed wrongly** — exactly the bug
   that had closed 19 rows earlier.  Fixed in `radar_queue.py`; the 243
   damaged rows were repaired by the new `work/tools/radar_repair.py`
   (which re-lists the competition kernels to recover the titles).
2. `auto_adjudicate.py` extracted every candidate tree in full — including
   the **700 MB `dqi.kmb`** — and never deleted it, so the 235-row queue
   filled the disk (109 GB, 100 %, `OSError: [Errno 28] No space left on
   device`) and the adjudicator crashed.  Fixed: member hashes are now
   **streamed** from the zip, only the members we actually verify
   (`invsqrt.kmb` + `dfthcsos/`) are extracted, and each candidate is
   deleted after its verdict.  Disk now stays at 45 %.
3. The adjudicator now orders the queue by the **score advertised in the
   title** (highest first) instead of file order.

## 2026-11-26 wake — v150 ADOPTED: goodpjw2008's v21 chemistry (LB 33.25564), +0.044 GM

**Status: SUBMITTED (ref 58918753), 4 slots left.**  The public-release queue
paid off within minutes of the wake starting: `goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25564`
(version 21, published 2026-11-25 21:5x UTC) advertises **33.25564** and its
kernel output ships the complete 18-file `submission.zip`.  This is the same
line we adopted as v149 (their v2 chemistry), now three versions further.

### What changed (measured with the unchanged official verifier)

| leg | v149 | v150 (adopted) |
|---|---|---|
| chemistry score | 250,157,973.2614051 | **249,169,842.41339546** |
| chemistry T | 13,166 | **13,114** |
| lambda_eff | 46.91432538757801 | **46.91430370584927** |
| angles Toffoli/pass | 3,333 | **3,307** |
| error_1 / error_2 | 0.0199999998799 / 0.0199999998794 | 0.0199999998801 / 0.0199999998805 |
| E_gap | 3.9148980000209 | 3.9148980000173 |
| invsqrt | 60,927.57739905387 (37 q) | same bytes (`bb676b95`) |
| DQI | 6f78ecdd (900 q) | same bytes (`6f78ecdd`) |

Local official verification: `work/receipts/V150_CHEM_VERIFY.log` (PASS, all
gates).  `invsqrt.kmb` and `dqi.kmb` are byte-identical to v149, whose in-kernel
moat-lab receipt (V149-RECEIPT-PASS) covers them; the DQI bytes are also the
public 33.17067 release's bytes.  Gate: `GATE-OK 0269bb6a1aa0e404`, receipt
`work/receipts/V150_RECEIPT.json`, tree `work/trees/v150`.  Predicted GM
**33.25562954624495**; the advertised public LB of the same bytes is 33.25564.

### What the release does (generator source harvested)

`work/gens/goodpjw2008_chem_v21_2026-11-26/` (notebook + kernel log + their
receipt).  It pins maoxin123's v4 table `ec85d969` and the 15 public loaders by
sha256, keeps **loader 0 unchanged**, re-solves **ten** loaders and rebuilds
**four** for the re-valued dead words, and refits W/H2_I.  Their own numbers:
version 20 = 33.25226; v21 shaves loader 12 (210→209) and loader 10 (213→212)
and re-solves 13/14 at the same length.

**The plan format is fully machine-readable in their notebook (cell 5):**
`KS = [[k, nP, early, c1, c2], ...]` for the ten wired loaders
(k = 2,3,4,6,8,9,10,12,13,14 with nP = 132,130,131,131,123,130,130,127,124,124),
and `BS = [[k, nbytes], ...]` = zlib-compressed sliding programs for
k = 1,5,7,11.  A base85 PACK blob (sha256 e25fe703…) holds all 14 plans, and
`build_loader` / `build_window` are the emitters.  We can now decode, edit and
re-emit their loaders locally.

### H48 status: CONFIRMED as a lane, and now precisely localised

Per-loader Toffolis in v150 (official reader):

```
k :  0   1   2   3   4   5   6   7   8   9  10  11  12  13  14
T : 245 240 214 212 213 240 213 240 205 212 212 240 209 206 206   (sum 3,307)
```

The **five group-start loaders k = 0,1,5,7,11 are still 240–245**; goodpjw has
not solved them in 21 versions either.  Everything else is 205–214.  Prize if
they reached ~215 each: 5 × ~28 × 2 passes × 0.000845 GM/T = **+0.24 GM**.

New structural measurement this wake (function tracking on the v150 circuits,
`chem_extract.py`; classification = truth table constant within each bank):

* **wired (solved) loaders**: 82 features = **68 bank-only + 14 low/mixed**
  (6 low ANDs + 8 mixed), 123–132 products;
* **group-start (unwired) loaders**: 144 features = **5 bank-only + 139
  low/mixed**, 96 products.

So the two families are genuinely different decompositions: the wired scheme
captures all low dependence in 14 cached features and pays 123–132 products;
the sliding scheme uses word-dependent (hence low-dependent) features and pays
143 features + 96 products.  The old extraction claim "143 bank features" is
really "143 low-dependent features"; the blocker is finding products whose
factors live in the 82-feature (68 bank AND + 6 low AND + 8 mixed) space.

Dead-word freedom per batch (the planting budget; amplitude < 1e-9):

```
k :  0   1   2   3   4   5   6   7   8   9  10  11  12  13  14
dead: 5  67  56 214 191  60 110 131 190 222 187 240 195 247 285
```

**Consequence for the H48 kill criterion:** k0 (5 dead) is hopeless and
k1/k5 (60–67) are very tight, but **k7 (131) and k11 (240) have as much
planting freedom as solved batches** (solved: 110–285).  The next build should
attack **k11 first** (most freedom) with the 82-feature scheme, then k7.
Pre-registered: a planting search that cannot reach **nP ≤ 157** (→ 239 T,
a 1-Toffoli win) for k11 within one build day kills the 82-feature approach for
group starts; reaching nP ≤ 132 (→ 214) is the full +0.24 GM.

### Queue

`goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25564` → **adopted** in
`ADOPTED.tsv` (via `harvest_queue.py done`).  The other 33.25xxx titles
(`areebbb/...33-25060`, `ghazarosbarseghyan91/vqcc-33-25057...`) are v20-line
derivatives and are now dominated by v150.  Four adjudicators are running on
disjoint slices (detached with `setsid`, unbuffered logs in
`work/harvest/logs/`); PENDING 248 at the time of writing.

### Re-ranked queue after this wake

1. **H48 (group-start loaders)** — +0.24 GM; now localised to k11/k7 with a
   decoded plan format and a measured dead-word budget.  Build lane.
2. **H41 (invsqrt 37 → 36 q)** — +0.31 GM; needs a new square-root construction.
3. **H44 (factorisation shape C)** — large but blocked on the 20 mHa gate and
   a full 15-loader rebuild.
4. **DQI width** — +0.45 GM, blocked (H22 closed, H32-m6 blocked).
5. **H40 (weight refit)** — ≤ +0.003 GM.

### H48 probe this wake: the product span of the 82-feature scheme is almost full

`work/tools/chem_span.py` (new) answers, exactly and with no search, whether a
target batch is representable with a given feature space F.  Because AND is
bilinear over GF(2), the span of *all* products `u AND v` (u,v in F) is exactly
`span{f_a AND f_b}` over a basis of F.  Measured with batch 2's 82-feature
space (dim F = 99):

```
feature k=2: |F| = 99, |span(F + products)| = 1217 of 1219
  target k= 2: D_i outside span:  0/35   <- control: batch 2 is representable
  target k=11: D_i outside span: 27/35
  target k= 7: D_i outside span: 25/35
  target k= 1: D_i outside span: 23/35
  target k= 5: D_i outside span: 25/35
  target k= 0: D_i outside span: 26/35
```

Two conclusions:

1. The product span of a *fixed* 82-feature space is only **2 dimensions short
   of the whole 1219-dim function space**.  The group-start targets fall in
   that 2-dim complement, which is why a fixed feature set from another batch
   cannot load them.
2. The dead-word freedom (240 free entries for k11) is enough to move the
   target into the span *in principle* (the complement is 2-dim and the free
   sets have 4–113 coordinates per column).  So the 82-feature scheme is not
   algebraically impossible for group starts; the obstruction is purely the
   **product count** (nP ≤ 157 to beat 240).

Next experiment (pre-registered, next wake): with the feature space chosen for
k11 itself (68 bank ANDs + 6 low + 8 mixed, searched as goodpjw does), compute
the 2-dim complement Z and check whether the *dead-word-adjusted* target is in
the span; then run the planting search for nP ≤ 157.  The complement being
2-dimensional also suggests a cheap certificate: any candidate plan can be
checked exactly by `chem_span.py` before costing it.

## 2026-11-28 — ADOPTED: goodpjw2008 V33 public frontier (v153), +0.0328 GM

The public frontier moved 33.25733 -> **33.29012** in ~36 h.  V33
(`goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-29012`, 2026-11-27 23:35)
ships the whole 18-file tree plus its own official-verifier receipt.  All
three legs were re-measured locally with the unchanged verifiers:

| leg | bytes | measured |
|---|---|---|
| invsqrt | b08370f271ba8f17 (evgendvorkin V86; rewrite of maoxin123 75e43352) | PASS 60,769.42127769003 (37 q, 1405.375 Toffoli) |
| dqi | b183c793b6b7c7a2 (logiclab; same bytes as v152) | PASS, clean board draw |
| chem | npz f2b6cc37ce87b0d8 + 15 re-solved loaders | PASS 249,043,677.36582175 (T 13,108, Q 405, lambda_eff 46.912012524) |

Prediction 33.29012 reproduces the release's measured LB.  v153 is in the
two-receipt gate (snapshot dataset `qcc-release-v153` + moat-lab receipt).

**Other releases measured this wake (all dominated by V33):**
* areebbb 33.29008: chem 249,044,466.68 (lambda_eff 46.912161206) -> +789 cost.
* rishabhbafnaiiitd "33.2905": chem 249,055,638.42 = the V29 table (+11,961).
* yalickj 33.28959 / dennis6886 V29 fork: chem 249,055,638.49 (+11,961).
* darkgobelin gated submission: invsqrt bb676b95 (60,927.58), DQI dbb2ada3
  (the known 2-error draw), chem 25ac10da -> strictly below V33.
* maoxin123 75e43352 invsqrt (60,774) is dominated by b08370f2 (60,769.42).

**Negative results confirmed this wake (do not re-run):**
* The deterministic "reuse a cached product" family is DEAD: an exhaustive
  exact sweep over every duplicate (control, control) pair in all 15 loaders
  (`sweep_reuse.py`, 0-44 candidates per loader) found **0 accepted rewrites**
  for the CCX->CX or drop-both edits.  This independently reproduces
  `chem_share.py`'s 0-Toffoli result and closes the cheapest edit family in the
  new CodeEvolve search space.
* dennis6886's fused-DQI refit is a no-op: coefficients [0,0,0], old and new
  lambda identical (their own audit).

**Open lane:** the chemistry CodeEvolve bundle is now runnable
(`work/evo/qcc_chem_codeevolve`: exact evaluator, init program, config).  Its
useful search space is NOT the reuse family above; it must propose structural
rewrites (move a product earlier to unlock a later CX, drop XOR pairs).
