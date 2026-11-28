#!/usr/bin/env python3
"""snapshot_dataset.py — publish a QCC submission tree as a Kaggle snapshot dataset.

WHY THIS TOOL EXISTS (the 2026-11-26 moat-lab failure)
---------------------------------------------------------
The moat-lab in-kernel gate reads the tree from a Kaggle **dataset**, because a
kernel cannot attach local files.  The first attempt at the v151 snapshot
uploaded only 3 of the 19 files:

    $ kaggle datasets create -p .
    ...
    $ kaggle datasets files badboyhalo1801/qcc-release-v151
    datasets-metadata.json  dqi.kmb  invsqrt.kmb

`kaggle datasets create` has `dir_mode="skip"` **by default**: the
`dfthcsos/` DIRECTORY was silently ignored.  The kernel then failed its SHA
gate with "SHA GATE FAILED" and no useful diagnostic.

This tool fixes that by construction:

  * it verifies every file against the 18-file SHA table BEFORE uploading;
  * it flattens the tree with a `__` separator (`dfthcsos/angle_k_0.kmb` ->
    `dfthcsos__angle_k_0.kmb`), because the Kaggle CLI would skip a real
    directory -- the moat-lab cell already understands both layouts;
  * it writes `dataset-metadata.json` (the name this CLI version actually
    looks for) and never leaves the stale `datasets-metadata.json` behind;
  * it prints the dataset's file list AFTER the upload so the omission is
    impossible to miss again.

Usage:
    snapshot_dataset.py --tree work/trees/v151 --sha-table work/sha_tables/sha_table_v151.txt \\
                        --slug badboyhalo1801/qcc-release-v151 --title "QCC release v151" \\
                        [--version] [--wait]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
KAGGLE = ROOT / "qaenv/bin/kaggle"


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", type=pathlib.Path, required=True)
    ap.add_argument("--sha-table", type=pathlib.Path, required=True)
    ap.add_argument("--slug", required=True, help="owner/name")
    ap.add_argument("--title", default="QCC release snapshot")
    ap.add_argument("--subtitle", default="")
    ap.add_argument("--description", default="")
    ap.add_argument("--stage", type=pathlib.Path,
                    default=pathlib.Path("/tmp/opencode/snapshot_stage"))
    ap.add_argument("--version", action="store_true",
                    help="publish a new VERSION of an existing dataset")
    ap.add_argument("--wait", action="store_true", help="wait until the dataset is ready")
    a = ap.parse_args()

    table = json.loads(a.sha_table.read_text())
    files = table["files"]
    assert len(files) == 18, f"expected 18 files in the table, got {len(files)}"

    # ---- 1. verify the tree against the table, byte for byte ----------------
    bad = []
    for rel, (sha, size) in sorted(files.items()):
        p = a.tree / rel
        if not p.is_file():
            bad.append((rel, "missing"))
            continue
        if p.stat().st_size != size:
            bad.append((rel, f"size {p.stat().st_size} != {size}"))
            continue
        if sha256(p) != sha:
            bad.append((rel, "sha mismatch"))
    if bad:
        print("TREE DOES NOT MATCH THE SHA TABLE:")
        for rel, why in bad:
            print(f"  {rel}: {why}")
        raise SystemExit(1)
    print(f"tree verified against the sha table: {len(files)} files")

    # ---- 2. stage it flat (Kaggle's CLI skips directories) -----------------
    if a.stage.exists():
        shutil.rmtree(a.stage)
    a.stage.mkdir(parents=True)
    staged = []
    for rel, (sha, size) in sorted(files.items()):
        flat = rel.replace("/", "__")
        shutil.copyfile(a.tree / rel, a.stage / flat)
        staged.append(flat)
    meta = {
        "title": a.title,
        "id": a.slug,
        "licenses": [{"name": "CC0-1.0"}],
        "keywords": ["quantum"],
        "subtitle": a.subtitle,
        "description": a.description,
        "resources": [],
        "isPrivate": True,
    }
    (a.stage / "dataset-metadata.json").write_text(json.dumps(meta, indent=1))
    print(f"staged {len(staged)} files (flat, '__' separator) in {a.stage}")

    # ---- 3. publish --------------------------------------------------------
    if a.version:
        # `datasets version` reads the target dataset from the id inside
        # dataset-metadata.json -- it takes no -d flag.
        cmd = [str(KAGGLE), "datasets", "version", "-p", str(a.stage),
               "-m", a.subtitle or a.title]
    else:
        cmd = [str(KAGGLE), "datasets", "create", "-p", str(a.stage)]
    p = subprocess.run(cmd, capture_output=True, text=True)
    print(p.stdout[-1500:])
    if p.returncode != 0:
        print(p.stderr[-2500:], file=sys.stderr)
        raise SystemExit("publish failed")

    # ---- 4. PROVE the upload is complete (the lesson of v151 v1) ----------
    for _ in range(60):
        p = subprocess.run([str(KAGGLE), "datasets", "files", a.slug],
                           capture_output=True, text=True)
        listed = [ln.split()[0] for ln in p.stdout.splitlines()[2:]
                  if ln.strip() and not ln.startswith("---")]
        if a.slug in listed or "dataset-metadata.json" in listed:
            break
        time.sleep(5)
    listed = [ln.split()[0] for ln in p.stdout.splitlines()[2:]
              if ln.strip() and not ln.startswith("---")]
    missing = sorted(set(staged) - set(listed))
    print(f"dataset lists {len(listed)} files; expected {len(staged)}")
    if missing:
        print("MISSING FROM THE UPLOAD:", missing)
        raise SystemExit("the upload is incomplete -- do NOT push the gate kernel")
    print("upload verified complete")


if __name__ == "__main__":
    main()
