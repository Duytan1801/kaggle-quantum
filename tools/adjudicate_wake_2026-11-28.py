#!/usr/bin/env python3
"""adjudicate_wake_2026-11-28.py — close the 2026-11-28 public-release queue.

Every row is closed through `harvest_queue.py done REF VERDICT NOTE`.

MEASUREMENTS behind the verdicts (official dfthcsos verifier, unchanged,
`--shots-per-address 1`, on each release's OWN 15 loaders):

  goodpjw2008 V33 tree (npz f2b6cc37 + its 15 loaders)
        249,043,677.36582175  lambda_eff 46.912012523842144  T 13,108  Q 405
        invsqrt b08370f2 60,769.42127769003 (local official PASS)
        -> ADOPTED as v153 (public LB 33.29012)

  areebbb 33.29008 tree (npz 533234e6 + its loaders)
        249,044,466.67980605  lambda_eff 46.91216120582399  T 13,108
        -> dominated by V33 by 789.3 cost units (~3e-5 GM)

  rishabhbafnaiiitd "33.2905" tree (npz 54b9ecdb + V29 loaders)
        249,055,638.4226583   lambda_eff 46.91426561154969  T 13,108
        -> dominated (this is the V29 table, 11,961 cost above V33)

  yalickj 33.28959 tree (npz 0395a644 + V29 loaders)
        249,055,638.4895167   lambda_eff 46.91426562414372  T 13,108
        -> dominated (the V29 table again)

  dennis6886 fused-DQI fork (npz 3fd97e2b + its loaders)
        249,055,638.4895167   lambda_eff 46.91426562414372  T 13,108
        -> dominated (the V29 table)

  maoxin123 75e43352 invsqrt: 60,774 (release title)
  evgendvorkin b08370f2 invsqrt: 60,769.42127769003 (measured locally, PASS)
        -> 75e43352 dominated by b08370f2 by 4.58 cost units

No release in the queue claims a score above V33's 33.29012.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/bandoc/Downloads/opencode")
PY = ROOT / "work/toolchain/venv/bin/python"
TOOL = ROOT / "work/tools/harvest_queue.py"

V153 = ("tree = our v153 exactly: goodpjw2008 V33 (invsqrt b08370f2 + DQI b183c793 + "
        "chem npz f2b6cc37, measured PASS 249,043,677.36582175)")
V29CHEM = ("measured on the release's own loaders: 249,055,638.49 "
           "(lambda_eff 46.914265624, T 13,108) = the V29 table, "
           "11,961 cost units above V33")

VERDICTS: dict[str, tuple[str, str]] = {
    # ---- adopted ---------------------------------------------------------
    "goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-29012": (
        "adopted", "SOURCE of v153: public frontier LB 33.29012 (2026-11-27 23:35). "
        "Official local PASS on all three legs (invsqrt 60,769.4213, chem "
        "249,043,677.37, DQI b183c793); its own receipt.json reports the same."),
    "evgendvorkin/google-quantum-ai-deep-eda-with-analogies": (
        "component-adopted", "SOURCE of the v153 invsqrt b08370f2 (V86): evgendvorkin's "
        "rewrite of maoxin123's 75e43352 (4 T gates -> 3 + Clifford corrections). "
        "Local official PASS 60,769.42127769003, 37 q, 1405.375 Toffoli."),
    "dennis6886/quantum-circuits-21-37712-fused-dqi-reproduction": (
        "adopted", "fork of goodpjw2008 V29; its tree measured 249,055,638.49 on its own "
        "loaders (V29 chemistry), superseded by V33. Its fused-DQI refit is a no-op "
        "(coefficients [0,0,0]) -- recorded as a negative result."),
    # ---- dominated (measured) -------------------------------------------
    "areebbb/qai-trim-the-loader-tune-the-circuit-33-29008": (
        "dominated", "measured 249,044,466.68 (lambda_eff 46.912161206, T 13,108); "
        "789.3 cost units above V33. Its LB 33.29008 matches."),
    "rishabhbafnaiiitd/qcc-33-2905-3-task-sota-portfolio-visual-guide": (
        "dominated", "despite the title, its chemistry is the V29 table: measured "
        "249,055,638.42 (lambda_eff 46.914265612, T 13,108), 11,961 above V33."),
    "yalickj/qcc-shorter-chemistry-loaders-lb-33-28959": (
        "dominated", V29CHEM + "; its LB 33.28959 is below V33's 33.29012."),
    "ghazarosbarseghyan91/vqcc-33-28872-goodpjw-13108-t-clean-dqi": (
        "dominated", "13108-T goodpjw chemistry with the clean DQI: this is V29's "
        "249,055,638.49, 11,961 above V33; its LB 33.28872 is below 33.29012."),
    "ghazarosbarseghyan91/vqcc-33-25735-13112-t-chemistry-clean-dqi": (
        "dominated", "13112-T chemistry (v151/v152 family), 200.9 cost above V33 at "
        "best; LB 33.25735 is below 33.29012."),
    "ghazarosbarseghyan91/vqcc-dennis-fused-dqi-25735-clean-pick": (
        "dominated", "the 25735 family again (13112-T); below V33."),
    "ghazarosbarseghyan91/vqcc-28-23441-verified-portfolio": (
        "dominated", "a 28.23 portfolio, far below the 33.29 frontier."),
    "ghazarosbarseghyan91/vqcc-goodpjw-13106-t-clean-dqi-v30-gate": (
        "research-ledger", "kernel ships NO output zip (scan: NO_ZIP), so there is no "
        "tree to verify; the 13106-T claim (2 fewer Toffolis than V33) is a pointer for "
        "the loader lane, not an adoptable artifact."),
    "ghazarosbarseghyan91/vqcc-combo-candidates": (
        "research-ledger", "candidate-combination dataset; every combination is a "
        "three-leg product and the legs are measured individually -- nothing above V33."),
    "rdaccel/qcc-33-25906-reproduction-goodpjw2008": (
        "dominated", "reproduction of the 33.25906 milestone (13110-T family), below V33."),
    "rdaccel/qcc-33-25906-bundle-goodpjw2008": (
        "dominated", "dataset of the same 33.25906 bundle; below V33."),
    "ranjeet258/qcc-final-v32": ("dominated", "V32 family (LB 33.29008 at best), below V33."),
    "ranjeet258/qcc-final-verified-v31": ("dominated", "V31 (LB 33.29000), below V33."),
    "ozertuu/google-quantum-ai-vqcc-33-25906-sota-apex": (
        "dominated", "33.25906 milestone, below V33."),
    "asteriospanoras/qcc-33-25229-best-public-merge-and-credits": (
        "dominated", "33.25229 milestone, below V33."),
    "maoxin123/qcc-33-287-37-qubit-invsqrt-at-60-774": (
        "dominated", "its invsqrt 75e43352 costs 60,774; evgendvorkin's b08370f2 "
        "(measured 60,769.4213, PASS) is 4.58 cheaper and is what v153 ships."),
    "pablodiegoo/google-quantum-compilation-starter-notebook": (
        "dominated", "starter notebook; no tree above the frontier."),
    # ---- research ledgers (no candidate tree) ---------------------------
    "alexchilton/33-29-lb-which-circuits-survive-private-salt": (
        "research-ledger", "private-salt survival study of the 33.29 trees; no new bytes."),
    "mizeroluckygall/qcc-chemistry-word-descent-inverse-sqrt-phase": (
        "research-ledger", "word-descent + invsqrt phase notes; the V33 release already "
        "implements the descent (lambda_eff 46.9120125)."),
    "manwithacat/vqcc-chemistry-negative-results": (
        "research-ledger", "negative-results ledger; harvested (it agrees with our "
        "chem_share/chem_demote/chem_feature_dup zero-savings measurements)."),
    "manwithacat/vqcc-apache-public-circuits": (
        "research-ledger", "Apache-2.0 public circuit catalogue; harvested for the floor."),
    "manwithacat/the-real-150k-was-the-friends-we-made": (
        "research-ledger", "release-history write-up; no tree."),
    "darkgobelin/qc-dqi-salt-robustness": (
        "research-ledger", "DQI salt-robustness study; no candidate tree."),
    "darkgobelin/qc-multi-salt-verified-baseline": (
        "research-ledger", "multi-salt baseline study; no candidate tree."),
    "darkgobelin/qc-frontier-gated-submission": (
        "dominated", "measured tree: invsqrt bb676b95 (60,927.5774, worse than "
        "b08370f2's 60,769.4213) + DQI dbb2ada3 (the known 2-error board draw, "
        "33.16196) + chem 25ac10da (v151); strictly below V33."),
    "kozykappa/vqcc-tests": ("no-candidate", "test notebook; no tree."),
    "mos3santos/circuit-optimization-test": ("no-candidate", "test notebook; no tree."),
    "hermesrmtupinamba/notebook6c1f027398": ("no-candidate", "no QCC tree in output."),
    "taylorclark637/vqcc-submission-notebook-v1-v16-assemblies": (
        "no-candidate", "scan: NO_ZIP (assemblies notebook ships no submission.zip)."),
    "topeseun100/quantum-circuit-compilation-original-work-sprint": (
        "no-candidate", "sprint notebook; no 18-file tree."),
    "letusassume/verifiable-quantum-circuit-compilation-three-smal": (
        "research-ledger", "three small-optimisation notes; no tree."),
    "dariushafshar/quantum-circuits-silver-line-is-a-113-team-tie": (
        "research-ledger", "leaderboard analysis (113-team tie); no tree."),
    "dariushafshar/kaggle-board-snapshots-santa-quantum-ntl-ptcg": (
        "research-ledger", "board snapshots dataset; no tree."),
    "muhakabartay/vqcc-salt-lottery-unit-prices-width-maps": (
        "research-ledger", "salt-lottery / unit-price analysis; no tree."),
    "teddybrown414/where-the-points-are-vqcc-score-exchange-rates": (
        "research-ledger", "score exchange-rate analysis; no tree."),
    "ozertuu/quantum-sim-linalg-cache": (
        "research-ledger", "simulator linear-algebra cache; tooling, no tree."),
    "suravimandalgmail/vqcc-chem-kit": (
        "research-ledger", "chemistry toolkit dataset; no full tree."),
    "bigbag1983/vqcc-maoxin-v4-pack": (
        "research-ledger", "maoxin123 v4 chemistry pack (3,357-T family); dominated by "
        "the V33 loaders (T 13,108 for the whole pass)."),
    "bigbag1983/vqcc-v28-circuit-generator": (
        "research-ledger", "generator source bundle; harvested, no tree."),
    "bigbag1983/vqcc-v28-eligible-a": ("research-ledger", "V28 eligibility pack; no tree."),
    "bigbag1983/vqcc-v28-eligible-b": ("research-ledger", "V28 eligibility pack; no tree."),
    "evgendvorkin/proba-2": ("out-of-scope", "SOL circuit atlas, not a QCC tree."),
    "evgendvorkin/santa-2026-arithmetic-program-atlas": (
        "out-of-scope", "Santa 2026 dataset."),
    "toshiaki517/qcc-dqi-frontier-row-measure": (
        "no-candidate", "scan: NO_ZIP (measurement kernel)."),
    "toshiaki517/qcc-dqi-salt-failure-campaign": (
        "no-candidate", "scan: NO_ZIP (salt campaign kernel)."),
    "toshiaki517/qcc-input-diag": ("no-candidate", "scan: NO_ZIP (diagnostic kernel)."),
    "toshiaki517/qcc-chem-loader-scan": ("no-candidate", "scan-only loader analysis."),
    "toshiaki517/qcc-dqi-camp5-16-salts": ("research-ledger", "16-salt DQI study; no tree."),
    "toshiaki517/qcc-dqi-motif-scan": ("no-candidate", "motif scan; no tree."),
    "toshiaki517/qcc-h8-live-loader-search": ("no-candidate", "loader search; no tree."),
    "toshiaki517/qcc-invsqrt-splice-campaign": ("no-candidate", "invsqrt splice search; no tree."),
    "toshiaki517/qcc-prv-h8-live-search-v3": ("no-candidate", "loader search v3; no tree."),
    "toshiaki517/qv2-beat-1-h8-search-private-dqi-q831": (
        "no-candidate", "private-DQI Q831 experiment; no tree."),
    "orel1986/qcc-v23-refit-fork": ("dominated", "V23 family (33.25737), below V33."),
}

OUT_OF_SCOPE = {
    "ishankarnick/santa-2026-frontier-programs",
    "royalacecat/santa-2026-verified-frontier-inputs-126963",
    "hillsidecollective/hillside-santa-2026-frontier",
    "georgymamarin/santa-2026-two-program-lineages",
    "hillsidecollective/santa-2026-elf-r27-frontier",
    "evgendvorkin/squares-in-squares-dataset-v1",
    "royalacecat/santa-2026-public-frontier-score-127-359",
    "royalacecat/santa-2026-verified-frontier-127460",
    "royalacecat/santa-2026-verified-frontier-128070",
    "ishankarnick/santa-2026-frontier-programs-127-985",
    "ishankarnick/santa-2026-frontier-programs-127-994",
    "ishankarnick/santa-2026-frontier-programs-128-004",
    "ozertuu/santa-2026-multi-engine-frontier-lb-127-984",
    "ozertuu/santa-2026-multi-engine-frontier-lb-127-991",
    "royalacecat/santa-2026-public-frontier-score-128-023",
    "uniquedomains/one-word-domain-lists",
    "leadchangegroup/us-employer-cost-2026-2027-hiring-cost-atlas",
    "nonamecode/heritage-shorts",
    "maialghadhouri/autism-spectrum-disorder-arff-file",
    "maialghadhouri/autism-spectrum-disorder-arff-files",
    "specstream/sec-investment-advisers-sample",
}


def main() -> int:
    pending = [ln.split("\t") for ln in
               (ROOT / "work/harvest/PENDING.tsv").read_text().splitlines() if ln.strip()]
    closed = 0
    for row in pending:
        ref = row[1]
        if ref in VERDICTS:
            verdict, note = VERDICTS[ref]
        elif ref in OUT_OF_SCOPE:
            verdict, note = "out-of-scope", "not a QCC release (other competition / unrelated dataset)"
        else:
            print(f"!! NO VERDICT for {ref} -- left queued")
            continue
        p = subprocess.run([str(PY), str(TOOL), "done", ref, verdict, note],
                           capture_output=True, text=True)
        if p.returncode != 0:
            print(f"FAIL {ref}: {p.stdout}{p.stderr}")
            continue
        closed += 1
    left = [ln for ln in (ROOT / "work/harvest/PENDING.tsv").read_text().splitlines() if ln.strip()]
    print(f"closed {closed}; {len(left)} left")
    for ln in left:
        print("  LEFT:", ln.split("\t")[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
