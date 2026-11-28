#!/usr/bin/env python3
"""gline_build.py — build the Syed Asad Ali invsqrt generator line at a chosen Q.

WHY THIS TOOL EXISTS (the 2026-11-26 pipeline fix)
----------------------------------------------------
The campaign's first evolutionary search (CodeEvolve v5) explored the
q2026-v154 ISR generator, whose width knob is a per-stage cap allow-list
that bottoms out at 36 q and whose builds cost 13 minutes each.

Meanwhile the **incumbent's own lineage** — the generator line of Syed Asad
Ali, the family that produced the shipped 37 q circuit
(prvsiyan `6b592145` / varianceofx `bb676b95` / Rithvik `d2148a7c`) — has a
*direct width knob* and builds in **74 seconds**:

    src/patches/PATCH_ORDER.txt   ->  "Q 46"  (the only width line)
    src/tools/pipeline.sh IN OUT NAME Q
    src/tools/hold_pass.py --Q Q  (the hold / narrowing pass)

`build.sh` reproduces the pinned Q=46 artifact exactly (sha
321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177) in 74 s
on this box.  That makes a Q-sweep a ~13-minute experiment instead of a
13-minute-per-candidate search, and it searches the lineage the frontier is
actually made of.

This tool drives that: it copies the source tree, rewrites the single `Q`
line, runs the UNMODIFIED build, and reports the emitted width, the sha and
the build log.  It never modifies the pinned source in place.

Usage:
    gline_build.py --q 44
    gline_build.py --q 40 37 35 --jobs 4
    gline_build.py --q 33 --patch-order path/to/PATCH_ORDER.txt
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
GLINE = ROOT / "work/gens/vqcc_generator_line_2026-11-23/invsqrt_source"
KICKMIX = ROOT / "work/toolchain/kickmix"
VERIFIERS = ROOT / "work/toolchain/verifiers"
PY313 = ROOT / "work/toolchain/venv/bin/python3.13"
SCRATCH = pathlib.Path(os.environ.get("GLINE_SCRATCH", "/tmp/opencode/gline_builds"))

EXPECTED_46 = "321aff83636214196daa9cbc9dcc9c5e12a155bcff8d9989e98b8cee40935177"


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_one(q: int, patch_order: pathlib.Path | None = None,
              timeout: int = 1800) -> dict:
    """Build the gline tree at width Q.  Returns a result dict (never raises)."""
    t0 = time.time()
    work = SCRATCH / f"q{q}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    src = work / "src_tree"
    shutil.copytree(GLINE, src, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # the ONE width knob
    po = src / "src/patches/PATCH_ORDER.txt"
    text = po.read_text()
    if patch_order is not None:
        text = patch_order.read_text()
    if not re.search(r"^Q\s+\d+\s*$", text, flags=re.M):
        return {"q": q, "ok": False, "error": "no Q line in PATCH_ORDER"}
    text = re.sub(r"^Q\s+\d+\s*$", f"Q {q}", text, flags=re.M)
    po.write_text(text)
    out = work / "out"
    out.mkdir()
    env = dict(os.environ)
    env["PY"] = str(PY313)
    env["WORK"] = str(work / "wtree")
    (work / "wtree").mkdir()
    cmd = ["bash", str(src / "build.sh"), str(KICKMIX), str(VERIFIERS), str(out)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return {"q": q, "ok": False, "error": f"timeout after {timeout}s",
                "seconds": round(time.time() - t0, 1)}
    res: dict = {"q": q, "rc": p.returncode,
                 "seconds": round(time.time() - t0, 1),
                 "log_tail": (p.stdout + p.stderr)[-1500:]}
    kmb = out / "invsqrt.kmb"
    if p.returncode == 0 and kmb.exists():
        res["ok"] = True
        res["kmb"] = str(kmb)
        res["sha256"] = sha256(kmb)
        res["bytes"] = kmb.stat().st_size
        # the emitted width comes from the build report or the kmb itself
        rep = out / "invsqrt.build.json"
        if rep.exists():
            try:
                r = json.loads(rep.read_text())
                res["width"] = r.get("Q")
                res["cost_model"] = r.get("cost_model")
                res["resources"] = r.get("exact_native_expectation")
            except Exception:
                pass
        if "width" not in res:
            m = re.search(r"at Q(\d+)", p.stdout)
            if m:
                res["width"] = int(m.group(1))
        res["matches_pinned_q46"] = (q == 46 and res["sha256"] == EXPECTED_46)
    else:
        res["ok"] = False
        res["error"] = "build failed"
    # keep the artifact only for the successful low widths (disk)
    if res.get("ok") and q > 40:
        shutil.rmtree(src, ignore_errors=True)
        shutil.rmtree(work / "wtree", ignore_errors=True)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--q", type=int, nargs="+", required=True)
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--patch-order", type=pathlib.Path)
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--out", type=pathlib.Path)
    a = ap.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = []
    if a.jobs > 1 and len(a.q) > 1:
        with cf.ThreadPoolExecutor(max_workers=a.jobs) as ex:
            futs = {ex.submit(build_one, q, a.patch_order, a.timeout): q for q in a.q}
            for f in cf.as_completed(futs):
                r = f.result()
                results.append(r)
                print(f"Q={r['q']:>3} ok={r.get('ok')} "
                      f"width={r.get('width')} sha={str(r.get('sha256'))[:16]} "
                      f"{r.get('seconds')}s {r.get('error','')}", flush=True)
    else:
        for q in a.q:
            r = build_one(q, a.patch_order, a.timeout)
            results.append(r)
            print(f"Q={r['q']:>3} ok={r.get('ok')} width={r.get('width')} "
                  f"sha={str(r.get('sha256'))[:16]} {r.get('seconds')}s "
                  f"{r.get('error','')}", flush=True)
    results.sort(key=lambda r: r["q"])
    txt = json.dumps(results, indent=1)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(txt)
        print(f"wrote {a.out}")
    else:
        print(txt)


if __name__ == "__main__":
    main()
