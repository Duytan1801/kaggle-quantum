#!/usr/bin/env python3
"""publish_codeevolve_chem_bundle.py — publish the chemistry CodeEvolve bundle.

Kaggle datasets are FLAT (the CLI's `dir_mode="skip"` default), so the bundle
is uploaded with `__` separators and a MANIFEST.json that maps every flat name
back to its path inside the bundle.  The kernel cell rebuilds the tree from
the manifest, so the evaluator sees the exact directory layout it expects
(`problem/input/evaluate.py`, `tree/dfthcsos/*`, `tools/*`, `kickmix/*`).

Usage:
  publish_codeevolve_chem_bundle.py --root /tmp/opencode/chem_ce_root
                                    --slug badboyhalo1801/qcc-chem-codeevolve
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path("/home/bandoc/Downloads/opencode")
KAGGLE = ROOT / "qaenv/bin/kaggle"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=pathlib.Path, required=True)
    ap.add_argument("--slug", default="badboyhalo1801/qcc-chem-codeevolve")
    ap.add_argument("--title", default="QCC chemistry CodeEvolve bundle")
    ap.add_argument("--subtitle",
                    default="Exact-evaluator chemistry loader search bundle (tree, tools, kickmix, codeevolve)")
    ap.add_argument("--description",
                    default="Bundle for the Kaggle-side CodeEvolve search over the 15 chemistry "
                            "loaders: the exact evaluator, the seed program, the search config, "
                            "the v153 loader bytes, the plan-recovery tools and the competition's "
                            "kickmix extension.")
    ap.add_argument("--stage", type=pathlib.Path, default=pathlib.Path("/tmp/opencode/chem_ce_stage"))
    ap.add_argument("--version", action="store_true")
    a = ap.parse_args()

    files = sorted(p for p in a.root.rglob("*") if p.is_file())
    if a.stage.exists():
        shutil.rmtree(a.stage)
    a.stage.mkdir(parents=True)
    manifest = []
    for p in files:
        rel = p.relative_to(a.root).as_posix()
        flat = rel.replace("/", "__")
        shutil.copyfile(p, a.stage / flat)
        manifest.append({"flat": flat, "path": rel,
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                         "bytes": p.stat().st_size})
    (a.stage / "BUNDLE_MANIFEST.json").write_text(json.dumps(
        {"root": "bundle", "files": manifest}, indent=1))
    (a.stage / "dataset-metadata.json").write_text(json.dumps({
        "title": a.title,
        "id": a.slug,
        "licenses": [{"name": "CC0-1.0"}],
        "keywords": [],
        "subtitle": a.subtitle,
        "description": a.description,
    }, indent=1))

    cmd = ([str(KAGGLE), "datasets", "version", "-p", str(a.stage),
            "-m", "chemistry CodeEvolve bundle refresh"] if a.version else
           [str(KAGGLE), "datasets", "create", "-p", str(a.stage)])
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(p.stdout[-3000:])
    if p.returncode != 0:
        print(p.stderr[-3000:])
        raise SystemExit("dataset upload failed")

    q = subprocess.run([str(KAGGLE), "datasets", "files", a.slug],
                       capture_output=True, text=True)
    listed = q.stdout
    print(listed[-2000:])
    missing = [m["flat"] for m in manifest if m["flat"] not in listed]
    if missing:
        raise SystemExit(f"upload incomplete: {len(missing)} files missing, e.g. {missing[:5]}")
    print(f"upload verified complete: {len(manifest)} files")


if __name__ == "__main__":
    main()
