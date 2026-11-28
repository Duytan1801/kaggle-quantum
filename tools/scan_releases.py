#!/usr/bin/env python3
"""scan_releases.py — pull a public release and report its 18-file tree shas.

Used by the harvest adjudicators: it turns a kernel/dataset ref into the three
member shas (invsqrt / dqi / chemistry npz) plus the loader shas, so a verdict
can be a FACT rather than an opinion.

Usage:
  scan_releases.py --kernel ref1 ref2 ...
  scan_releases.py --dataset ref1 ...
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path("/home/bandoc/Downloads/opencode")
KAGGLE = ROOT / "qaenv/bin/kaggle"
SCRATCH = pathlib.Path("/tmp/opencode/scan_releases")


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def report_tree(name: str, root: pathlib.Path) -> dict:
    out: dict = {"ref": name, "root": str(root), "files": {}}
    inv = root / "invsqrt.kmb"
    dqi = root / "dqi.kmb"
    npz = root / "dfthcsos" / "submission.npz"
    if not npz.exists():
        hits = list(root.rglob("submission.npz"))
        npz = hits[0] if hits else npz
    for label, p in (("invsqrt", inv), ("dqi", dqi), ("chem_npz", npz)):
        if p.is_file():
            out["files"][label] = {"sha256": sha256(p), "bytes": p.stat().st_size}
    loaders = sorted(root.rglob("angle_k_*.kmb"))
    if loaders:
        out["loaders"] = {p.name: sha256(p)[:12] for p in loaders}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kernel", nargs="*", default=[])
    ap.add_argument("--dataset", nargs="*", default=[])
    a = ap.parse_args()
    SCRATCH.mkdir(parents=True, exist_ok=True)
    results = []
    for ref in a.kernel:
        d = SCRATCH / ("k_" + ref.replace("/", "_"))
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        p = subprocess.run([str(KAGGLE), "kernels", "output", ref, "-p", str(d),
                            "--force"], capture_output=True, text=True)
        zips = list(d.rglob("submission.zip"))
        if not zips:
            results.append({"ref": ref, "status": "NO_ZIP",
                            "stderr": p.stderr[-300:], "stdout": p.stdout[-300:]})
            print(f"{ref}: NO_ZIP", flush=True)
            continue
        t = d / "tree"
        t.mkdir(exist_ok=True)
        subprocess.run(["unzip", "-q", "-o", str(zips[0]), "-d", str(t)],
                       capture_output=True)
        r = report_tree(ref, t)
        r["status"] = "OK"
        results.append(r)
        print(f"{ref}: " + json.dumps(r["files"]), flush=True)
    for ref in a.dataset:
        d = SCRATCH / ("d_" + ref.replace("/", "_"))
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        p = subprocess.run([str(KAGGLE), "datasets", "download", "-d", ref,
                            "-p", str(d), "--force"], capture_output=True, text=True)
        zips = list(d.rglob("*.zip"))
        for z in zips:
            t = d / ("tree_" + z.stem)
            t.mkdir(exist_ok=True)
            subprocess.run(["unzip", "-q", "-o", str(z), "-d", str(t)],
                           capture_output=True)
        for t in sorted(d.glob("tree_*")):
            r = report_tree(ref, t)
            r["status"] = "OK"
            results.append(r)
            print(f"{ref} [{t.name}]: " + json.dumps(r["files"]), flush=True)
        if not zips:
            results.append({"ref": ref, "status": "NO_ZIP"})
            print(f"{ref}: NO_ZIP", flush=True)
    print(json.dumps(results, indent=1))


if __name__ == "__main__":
    main()
