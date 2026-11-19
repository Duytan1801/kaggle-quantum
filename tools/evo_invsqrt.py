#!/usr/bin/env python3
"""Deterministic invsqrt generator-variant evaluator for H6.

The evaluator turns a build report into the competition objective:

    score = Q * (toffoli_like + T/4 + n_rot * rotation_price(eps)/4)

where `eps` uses the generator's pinned exact minimum margin.  It deliberately
does not use the false population baseline fields (Q=44/T=120): those describe
the public 44q file, not the local Q46 source generator.  Every scored record
therefore includes both the modelled score and the source/config identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import pathlib
import tempfile
from typing import Any

DEFAULT_MARGIN = 124_370_688
MASK64 = (1 << 64) - 1


def rotation_price(eps: float) -> float:
    return 0.56 * math.log2(1.0 / eps) + 5.3


def score_report(report: dict[str, Any], *, margin: int = DEFAULT_MARGIN) -> dict[str, Any]:
    resources = report["exact_native_expectation"]
    mean = resources["mean_numeric"]
    q = int(report["Q"])
    toffoli = float(mean["toffoli_like"])
    t_base = float(mean["T"])
    rotations = float(mean["generic_rotations"])
    eps = math.pi * margin / 2**64 / rotations if rotations else None
    charge = rotations * rotation_price(eps) / 4.0 if eps is not None else 0.0
    per_shot = toffoli + t_base / 4.0 + charge
    return {
        "status": report.get("status", "EMITTED_VARIANT_NOT_YET_PROVED_OR_QUALIFIED"),
        "score_model": q * per_shot,
        "Q": q,
        "toffoli_like": toffoli,
        "T": t_base,
        "generic_rotations": rotations,
        "margin_units64": margin,
        "rotation_eps": eps,
        "rotation_charge_total": charge,
        "per_shot_toffoli_equivalent": per_shot,
        "kmb_sha256": report.get("kmb_sha256"),
        "native_text_sha256": report.get("native_text_sha256"),
        "patch_sha256": report.get("patch_sha256", []),
        "proof_required": "PASS_EXACT_NATIVE_TEXT_ALL_REQUESTED_INPUTS_ALL_HMR_TRANSCRIPTS",
    }


def score_build(build: pathlib.Path) -> dict[str, Any]:
    if build.is_dir():
        candidates = sorted(build.glob("*.build.json"))
    else:
        candidates = [build]
    if not candidates:
        raise FileNotFoundError(f"no .build.json under {build}")
    report = json.loads(candidates[0].read_text())
    out = score_report(report)
    out["build_report"] = str(candidates[0])
    out["build_report_sha256"] = hashlib.sha256(candidates[0].read_bytes()).hexdigest()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("build", type=pathlib.Path)
    ap.add_argument("--margin", type=int, default=DEFAULT_MARGIN)
    ap.add_argument("--out", type=pathlib.Path)
    args = ap.parse_args()
    result = score_build(args.build)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
