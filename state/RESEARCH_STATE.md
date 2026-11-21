# RESEARCH STATE — live hypothesis queue (agent-maintained; rewrite freely)
# Format: H# | claim | mechanism | est GM | cheapest discriminating test | status | evidence | updated
# Rules: never re-run a KILLED test; re-rank by expected-GM/effort after each resolution.
# Last full re-rank: 2026-11-21 12:20 UTC (post H26 kill + H22 kill; H24 generator-lend is top, H25 is the last angle-level probe)

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

H24 | **NEW, TOP PRIORITY — invsqrt generator 39 q -> 38/37 q (+0.15 / +0.45 GM).**
    The public invsqrt generator (`/tmp/opencode/gens/x/invsqrt/`, sha
    `68eb8c13ebc75c5e443ed5a8c6357c2c77e6676c499ed1324108bf025faf1489`)
    builds a **39 q / 24,387 instr / 1,452 Toffoli-like** circuit worth
    61,696 (worse than our 37 q tree only because of the 2 extra qubits).  At
    38 q it would score 60,114 (GM 33.253) and at 37 q 58,532 (**GM 33.5518,
    +0.45 over the board**).  The generator already ships the lend machinery
    (`lend29.py` locate/transplant, `carry.py` `carry_window()`): a wire that
    holds an AFFINE function of other live wires is XOR-ed out, reused as
    scratch, and restored afterwards, so it does not need its own physical
    wire.  The public patch `invsqrt_lend29.patch` does this for block 29 but
    keeps 39 q (it only saves 0.5 Toffoli).  Success criterion: a rebuilt
    generator circuit with **38 q** whose official verifier score <= 60,114 and
    whose phase is identical to the 39 q build on all 3,133,452 inputs.
    Kill criterion: if no second lendable affine wire exists (measured by a
    per-wire affine-dependency scan of the 39 q build), the lane is dead and
    invsqrt is closed at 37 q / 60,955.

H25 | **NEW — the only surviving angle-level lever: an extra salt-invariant
    basis function.**  H26 killed the *angle* refit, but the circuit's phase is
    a sum of indicator functions and a NEW indicator (an extra Z_POW on a
    scratch wire whose value is a function of x) enlarges the span.  The
    x-register bit basis was tried and does not pay (margin x1.33 at best for
    +22 rotations).  A scratch wire holding a half-cell-like function could do
    far better.  Test: instrument the simulator to record every wire's value
    at each of the 33 priced-rotation positions (keep only salt-invariant
    ones), then run the LP with the best candidate added.  Break-even: one
    extra rotation pays only if the margin improves by **> x2.96** (each
    rotation costs ~268 score).  Kill criterion: if the best candidate gives
    < x2.96, drop the lane for good (the +0.13 GM ceiling applies here too).

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

## FACTS PINNED
- Best row v131 = 28.18084 (ref 58487983, clean draw). Best public tree, adopted verbatim.
- DQI score = rep × Q² × toffoli_mean. 1 DQI qubit ≈ +0.021 GM at Q=890. 1 DQI toffoli ≈ +2.6e-5 GM.
- invsqrt score = Q × (T_mean + T/4 + n_rot·rot_price(eps)/4); 1 invsqrt qubit ≈ +0.077 GM.
- Frontier: #1 31.50404, #2 31.42723 ⇒ ×2.867 ratio product over us.
