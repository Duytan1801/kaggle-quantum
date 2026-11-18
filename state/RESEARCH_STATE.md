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
    the Euler solution) | implement ANF-based exact-AND synthesizer (schema fully known from v9_form_e2.json /
    hret_s15k7a_s15.json: gates = AND of two XOR-sets, output = XOR of terms; validity exactly checkable
    over full domain), then endpoint retirement of a 4th bit (v8 — note ordering conflict: v8 feeds v9's
    rebuild form) + solve the product-forward carry peak (needs 1 wire at Q45: h0-pack gets body to 45,
    carry wants 46) | TESTING | Q45 probe rc=1 at patch_proddisp→arithmetic._compute_carry alloc (45+1>45);
    PACK=True loader fit confirmed (25+20=45); NOW TOP after H1 killed — all effort points here
    | 2026-11-18

H3 | Top-2 mechanism is discoverable from public traces | aadi_stonks 31.50404 / Z³C¹oherence 31.42723;
    gap = ×2.87 product; if all-DQI-width ⇒ Q≈526 (41% cut) — likely a mix (their invsqrt/chem also better?)
    | unknown, potentially +1–2 GM | deep recon pass: pull ALL aadi_stonks + Z³C¹oherence public
    kernels/datasets/votes timestamps, diff submission cadence vs score jumps to infer per-leg improvements;
    check kaggle forum posts | NEW | only surface recon done (LB rows) | 2026-11-18

H4 | DQI rep_factor has headroom | our 5f901c55 rep ≈ 1.1911 vs floor 1.19126 ⇒ likely ~0 room, but the
    formula R(eps) = ln2/−ln(½+2√eps) depends on decoder epsilon | tiny | read verify_submission_dqi.py
    scoring path end-to-end; check if rep is schedule-controllable | NEW | — | 2026-11-18

H5 | Public release ride | maoxin123 iterates fastest (v27→28.17 in one day, owns rescheduler); asterios/
    boristown/ozertuu active | unknown, historically +0.03–0.3/release | watchpub timer (active, 20 min)
    → on any leg improvement: two-receipt gate → submit | ACTIVE (passive) | v130→v131 adoption gave +0.030
    | 2026-11-18

## KILLED (evidence recorded — DO NOT re-enter)
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
