#!/usr/bin/env python3
"""adjudicate_wake.py — close the public-release queue for the 2026-11-26 wake.

Every row in `work/harvest/PENDING.tsv` is closed through the campaign's own
tool (`harvest_queue.py done REF VERDICT NOTE`), which removes the row from
the queue and appends it to `work/harvest/ADOPTED.tsv`.  The verdicts below
are MEASUREMENTS, not opinions:

  * the release's three member shas were pulled with `work/tools/scan_releases.py`
    (the tool prints the sha256 + byte size of invsqrt.kmb, dqi.kmb and
    dfthcsos/submission.npz, plus the 15 loader shas);
  * they are compared against the shipped trees v151 (25ac10da + 6f78ecdd) and
    v152 (3cc6a37a + b183c793);
  * the chemistry legs of the novel tables were measured with the UNCHANGED
    official verifier on our 15 loaders.

Reference numbers for the comparison:
  invsqrt  6b592145  60,927.54794503887 (ours)   bb676b95  60,927.57739905387 (worse)
  dqi      6f78ecdd  board draw 305,032,258,732.73 (ours)
           b183c793  board draw ~305,031,4xx,xxx (zhuangbility v23: ~0.82M cheaper)
           3c03fa53  zero-fail 313,736,311,904 (much worse)
  chem     25ac10da + our loaders  249,131,841.8273937 (v151)
           3cc6a37a + our loaders  249,131,640.8997796 (v152, official PASS)
           fc83e9ff + our loaders  249,131,840.18 (dominated by 3cc6a37a)
           0043d423                  older table (dominated)
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path("/home/bandoc/Downloads/opencode")
HQ = ROOT / "work/toolchain/venv/bin/python"
TOOL = ROOT / "work/tools/harvest_queue.py"

V152 = ("tree = our v152 exactly: invsqrt 6b592145 + DQI b183c793 + chem npz "
        "3cc6a37a + goodpjw V22 loaders; measured chemistry PASS 249,131,640.8997796")
V151 = ("tree = our v151 exactly: invsqrt 6b592145 + DQI 6f78ecdd + chem npz "
        "25ac10da + V22 loaders; measured chemistry PASS 249,131,841.8273937")

VERDICTS: list[tuple[str, str, str]] = [
    # ---- the v152 family (adopted) -------------------------------------
    ("zhuangbility/qcc-v23-our-refit-b183c793-lb-33-25737", "adopted",
     "SOURCE of our v152: its notebook states the DQI b183c793 board draw is clean and "
     "~0.82M cheaper than 6f78ecdd (evgendvorkin V81 33.25229 vs 33.25226, ~+3e-5 GM); "
     "its claimed LB 33.25737 reproduces our independent prediction 33.257375 for "
     "invsqrt 6b592145 + DQI b183 + chem 3cc6a37a. kernel output ships no submission.zip"),
    ("orel1986/qcc-33257-fork", "adopted", V152),
    ("toshiaki517/qcc-chem-refit-dqi-rewrites-dir-run", "adopted", V152),
    ("alexchilton/33-25-lb-which-circuits-survive-private-salt", "adopted", V152),
    ("mizeroluckygall/qcc-chemistry-weight-refit-dqi-rewrites", "adopted", V152),
    ("pablodiegoo/google-quantum-compilation-starter-notebook", "adopted", V152),
    # ---- the v151 family (already shipped) ------------------------------
    ("goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25737", "adopted",
     "SOURCE of our v151 (npz 25ac10da + 5 re-solved loaders, T 13112); board 33.25733"),
    ("goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-25733", "adopted",
     "SOURCE of our v151 (npz 25ac10da + 5 re-solved loaders, T 13112); board 33.25733"),
    ("cosmorin/qcc-33-25733-verified-reproduction", "adopted", V151),
    ("dennis6886/quantum-circuits-21-37712-fused-dqi-reproduction", "adopted", V151),
    ("areebbb/qai-cut-the-gates-keep-the-chemistry-33-25733", "adopted", V151),
    ("areebbb/qai-cut-the-gates-keep-the-chemistry-33-25060", "adopted", V151),
    # ---- dominated -------------------------------------------------------
    ("zhuangbility/vqcc-v22-refit-b183", "dominated",
     "invsqrt 6b592145 + DQI b183c793 + chem npz fc83e9ff; chemistry on our loaders "
     "249,131,840.18 vs our v152's 249,131,640.90 (3cc6a37a) -> dominated by v152"),
    ("varianceofx/vqcc-verified-v22-chem-portfolio", "dominated",
     "invsqrt bb676b95 (60,927.57739905387, worse than ours 60,927.54794503887) + DQI "
     "1e6787a0 (zero-fail 305,041,576,300.78, worse) + chem npz 25ac10da (= our v151)"),
    ("aiokajima/quantum-goodpjw-3325226-reproduction-public", "dominated",
     "invsqrt 6b592145 + DQI 6f78ecdd + chem npz 0043d423 (older table, dominated by "
     "25ac10da/3cc6a37a)"),
    ("ruijiezhao666/vqcc-source-built-arithmetic-and-chemistry", "dominated",
     "invsqrt b4ba2126 (39 q, worse) + DQI 3c03fa53 (889 q, zero-fail 313,736,311,904, "
     "8.7e9 worse than ours) + chem npz e317ab1c"),
    # ---- research ledgers ------------------------------------------------
    ("ratnachand/vqcc-verified-floor-and-circuit-anatomy", "research-ledger",
     "public circuit-anatomy notes for the VQCC floor; harvested, no candidate tree"),
    ("manwithacat/the-real-150k-was-the-friends-we-made", "research-ledger",
     "public write-up of the QCC release history; harvested, no candidate tree"),
    ("ratnachand/vqcc-verified-public-floor", "research-ledger",
     "dataset: the public VQCC floor; harvested into the Apache catalogue comparison"),
    ("manwithacat/vqcc-apache-public-circuits", "research-ledger",
     "dataset: the Apache-2.0 public circuit catalogue (704+ scored circuits); harvested "
     "and mined for the public floor and the negative-results ledger"),
    # ---- no candidate tree ------------------------------------------------
    ("mizeroluckygall/quantum-circuits-the-eight-salt-stress-test", "no-candidate",
     "kernel output ships no submission.zip (salt stress-test only)"),
    ("srinath2495/dfthc-r8-b127-c46-brot6-gpu-train", "no-candidate",
     "kernel output ships no submission.zip (training run only)"),
]

OUT_OF_SCOPE = {
    "shiraleesakaria/nanobody-polyreactivity-short-cdr3-train",
    "royalacecat/santa-2026-verified-frontier-128070",
    "ishankarnick/santa-2026-frontier-programs",
    "royalacecat/santa-2026-public-frontier-score-128-026",
    "muhammedveyselerin/nicker-horse-red-light-spec-index-2026",
    "georgymamarin/santa-2026-two-program-lineages",
    "ozertuu/santa-2026-multi-engine-frontier-lb-128-002",
    "asteriospanoras/santa-2026-early-gifts-shorter-programs",
    "malyshevdanil/squares-in-squares-living-atlas-of-tight-packings",
    "ozertuu/santa-2026-multi-engine-frontier-lb-128-024",
    "ozertuu/santa-2026-multi-engine-frontier-lb-128-025",
    "ishankarnick/santa-2026-frontier-programs-128-025",
    "ishankarnick/santa-2026-frontier-programs-128-030",
    "harshitab3030/kgatlastfm",
    "ozertuu/santa-2026-multi-engine-frontier-lb-128-078",
    "nonamecode/heritage-short",
    "ozertuu/santa-2026-multi-engine-frontier-lb-128-079",
    "ishankarnick/santa-2026-frontier-programs-128-079",
    "liuzewen123/casmi-np-spec-v18-loss-fallback",
    "ozertuu/santa-2026-multi-engine-frontier-lb-128-040",
    "ishankarnick/santa-2026-frontier-programs-128-068",
    "royalacecat/santa-2026-public-frontier-score-128-071",
    "royalacecat/santa-2026-verified-frontier-128071",
    "ozertuu/santa-2026-multi-engine-frontier-lb-128-032",
    "ishankarnick/santa-2026-frontier-programs-128-033",
    "royalacecat/santa-2026-public-frontier-score-128-070",
    "royalacecat/santa-2026-public-frontier-score-128-219",
    "linxinshihuang/atlascat-identities-and-exposure-grains",
    "liuzewen123/casmi-np-spec-v18",
    "linxinshihuang/atlascat-identities-exposure-and-dateline-audit",
    "muhammedveyselerin/horse-light-products-specs-and-evidence",
    "uniquedomains/one-word-domain-lists",
    "specstream/saas-subprocessor-changes-sample",
    "specstream/us-new-business-registrations-sample",
    "specstream/warn-act-layoff-notices-sample",
    "specstream/us-private-funds-form-adv-sample",
    "specstream/saas-subprocessors-directory-sample",
    "specstream/us-public-companies-financials-sample",
    "specstream/osha-workplace-citations-sample",
    "specstream/new-california-health-providers-npi-sample",
    "specstream/clinical-trials-sponsors-sample",
    "specstream/fda-510k-pma-device-decisions-sample",
    "specstream/va-federal-contract-awards-sample",
    "specstream/sec-investment-advisers-top-500-by-aum",
}


def main() -> int:
    pending = [ln.split("\t") for ln in
               (ROOT / "work/harvest/PENDING.tsv").read_text().splitlines() if ln.strip()]
    refs = [r[1] for r in pending]
    todo = dict((r, (v, n)) for r, v, n in VERDICTS)
    n_closed = 0
    for ref in refs:
        if ref in todo:
            verdict, note = todo[ref]
        elif ref in OUT_OF_SCOPE:
            verdict, note = "out-of-scope", "not a QCC release (other competition / unrelated dataset)"
        else:
            print(f"!! NO VERDICT PREPARED for {ref} -- left in the queue")
            continue
        p = subprocess.run([str(HQ), str(TOOL), "done", ref, verdict, note],
                           capture_output=True, text=True)
        if p.returncode != 0:
            print(f"FAIL {ref}: {p.stdout}{p.stderr}")
            continue
        n_closed += 1
    left = [ln for ln in (ROOT / "work/harvest/PENDING.tsv").read_text().splitlines() if ln.strip()]
    print(f"closed {n_closed} rows; {len(left)} rows left in PENDING.tsv")
    for ln in left:
        print("  LEFT:", ln.split("\t")[1])
    return 0


if __name__ == "__main__":
    sys.exit(main())
