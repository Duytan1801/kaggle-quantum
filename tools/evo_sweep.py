#!/usr/bin/env python3
"""evo_sweep.py — H6 search driver: evaluate a population of generator variants,
rank them by the exact objective, and keep the population store current.

This is the AlphaEvolve loop in miniature:
  variant config → build (emit) → deterministic score → population DB → ranking
The next generation's prompt is assembled from this ranking (evo_pop.py prompt).

Usage:
  python3 evo_sweep.py --configs work/evo/configs/v00*.json [--work-root DIR]
  python3 evo_sweep.py --configs ... --parallel 2
"""
from __future__ import annotations

import argparse, json, os, pathlib, subprocess, sys, time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "work/tools"))
import evo_pop  # noqa: E402

PY = str(ROOT / "work/toolchain/venv/bin/python")
RUN_CAPPED = str(ROOT / "harness/run_capped.sh")


def run_one(cfg_path: pathlib.Path, work_root: pathlib.Path, cap: str):
    cfg = json.loads(cfg_path.read_text())
    name = cfg["name"]
    work = work_root / name
    if work.exists():
        import shutil; shutil.rmtree(work)
    work.mkdir(parents=True)
    cmd = [RUN_CAPPED, cap, PY, str(ROOT / "work/tools/evo_build.py"),
           "--config", str(cfg_path), "--work", str(work),
           "--out", str(work / "result.json")]
    began = time.monotonic()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    except subprocess.TimeoutExpired:
        return {"name": name, "status": "TIMEOUT", "elapsed_seconds": time.monotonic() - began,
                "config": cfg, "work": str(work)}
    res = json.loads((work / "result.json").read_text()) if (work / "result.json").exists() else {
        "name": name, "status": "NO_RESULT", "returncode": proc.returncode,
        "stderr": proc.stderr[-2000:], "config": cfg, "work": str(work)}
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--configs", nargs="+", type=pathlib.Path, required=True)
    ap.add_argument("--work-root", type=pathlib.Path, default=pathlib.Path("/tmp/opencode/evo_sweep"))
    ap.add_argument("--cap", default="4G")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--from-results", type=pathlib.Path,
                    help="register a saved sweep JSON into the population DB without re-running builds")
    args = ap.parse_args()
    args.work_root.mkdir(parents=True, exist_ok=True)

    results = []
    if args.from_results:
        # Register-only mode: backfill the population DB from a saved sweep file.
        # Never re-run a variant (rule 3: identical bytes are deterministic).
        results = json.loads(args.from_results.read_text())
    elif args.parallel > 1:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=args.parallel) as ex:
            futs = {ex.submit(run_one, c, args.work_root, args.cap): c for c in args.configs}
            for f in futs:
                results.append(f.result())
    else:
        for c in args.configs:
            results.append(run_one(c, args.work_root, args.cap))

    ranked = []
    for r in results:
        cfg = r.get("config", {})
        key = {"name": r["name"], "Q": cfg.get("Q"), "env": cfg.get("env", {}),
               "patches": [p.get("dst") for p in cfg.get("patches", [])]}
        score = r.get("score") or {}
        model = score.get("score_model")
        # register in the population DB (dedupe by config hash; returns the id)
        vid = None
        try:
            vid = evo_pop.cmd_add(type("A", (), {"config": json.dumps(key), "parent": None,
                                                 "note": r.get("status")})())
            if vid and model is not None:
                evo_pop.cmd_set(type("A", (), {"id": vid, "score": model,
                                               "parts": {"Q": score.get("Q"), "toffoli_like": score.get("toffoli_like"),
                                                         "T": score.get("T"), "rot": score.get("generic_rotations")},
                                               "artifacts": {"work": r.get("work"), "kmb_sha256": score.get("kmb_sha256"),
                                                             "elapsed_seconds": r.get("elapsed_seconds")},
                                               "status": "SCORED",
                                               "note": r.get("status")})())
            elif vid:
                evo_pop.cmd_fail(type("A", (), {"id": vid, "note": r.get("status")})())
        except SystemExit:
            pass
        except Exception as e:
            print(f"  (population registration failed for {r['name']}: {e})")
        ranked.append({"name": r["name"], "pop_id": vid, "status": r.get("status"), "score_model": model,
                       "Q": score.get("Q"), "elapsed": round(r.get("elapsed_seconds", 0), 1),
                       "kmb_sha256": score.get("kmb_sha256"),
                       "stderr_tail": (r.get("stderr") or "")[-300:] if r.get("status") != "EMITTED" else ""})

    # LOWER cost is better: score_model is the modelled official cost.
    ranked.sort(key=lambda x: (x["score_model"] is None, x["score_model"] if x["score_model"] is not None else 0))
    print("\n=== H6 sweep ranking (lower score_model = better) ===")
    for r in ranked:
        print(f"{r['name']:<34} {r['status']:<12} Q={str(r['Q']):<4} score={str(round(r['score_model'],2) if r['score_model'] else '—'):>12} "
              f"({r['elapsed']}s) {r['stderr_tail'][:120]}")
    if args.out:
        args.out.write_text(json.dumps(ranked, indent=2) + "\n")


if __name__ == "__main__":
    main()
