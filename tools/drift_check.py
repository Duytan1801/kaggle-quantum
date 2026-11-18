#!/usr/bin/env python3
"""drift_check.py — did the owner's live tree drift from our scored tree?

Pulls `heliosli/qcc-circuits-live`, verifies the 18 files against the release
manifest's SHA-256 table (the static receipt), and compares them with a local
sha table (the tree we last scored).

    drift_check.py [--table work/sha_tables/sha_table_v119g.txt] [--pull]

Exit code 0 = no drift, 1 = drift, 2 = the live tree fails its own manifest.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import lzma
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/bandoc/Downloads/opencode")
KAGGLE = ROOT / "qaenv" / "bin" / "kaggle"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def read_table(path: Path) -> dict[str, str]:
    """Parse a sha table file: a python dict literal, a `"file": ("sha", n),`
    fragment, or `sha  path` lines."""
    text = path.read_text()
    out: dict[str, str] = {}
    try:
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Dict):
                for k, v in zip(node.keys, node.values):
                    if isinstance(k, ast.Constant) and isinstance(v, ast.Constant):
                        out[k.value] = v.value
                if out:
                    return out
    except SyntaxError:
        pass
    # fragment form: "file": ("sha256", bytes),
    for m in re.finditer(r"[\"']([^\"']+)[\"']\s*:\s*\(\s*[\"']([0-9a-f]{64})[\"']", text):
        out[m.group(1)] = m.group(2)
    for line in text.splitlines():
        m = re.match(r"([0-9a-f]{64})\s+\*?(.+)", line.strip())
        if m:
            out[m.group(2).strip()] = m.group(1)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=str(ROOT / "work/sha_tables/sha_table_v119g.txt"))
    ap.add_argument("--pull", action="store_true", help="re-download the live dataset first")
    ap.add_argument("--dir", default="/tmp/opencode/live_pull")
    a = ap.parse_args()

    live_dir = Path(a.dir)
    manifest_path = live_dir / "QCC_RELEASE_MANIFEST.json"
    if a.pull or not manifest_path.exists():
        if live_dir.exists():
            shutil.rmtree(live_dir)
        live_dir.mkdir(parents=True)
        subprocess.run([str(KAGGLE), "datasets", "download", "-d", "heliosli/qcc-circuits-live",
                        "-p", str(live_dir), "--unzip"], check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    manifest = json.loads(manifest_path.read_text())
    print(f"live portfolio: {manifest.get('portfolio')}  salt: {manifest.get('salt')}  "
          f"files: {len(manifest['files'])}")

    live: dict[str, str] = {}
    bad = 0
    for entry in manifest["files"]:
        stored = live_dir / entry["stored_as"]
        if entry["stored_as"].endswith(".xz"):
            data = lzma.open(stored, "rb").read()
            got = hashlib.sha256(data).hexdigest()
        else:
            got = sha256(stored)
        live[entry["file"]] = got
        if got != entry["sha256"]:
            print(f"  MANIFEST MISMATCH {entry['file']}: {got[:12]} != {entry['sha256'][:12]}")
            bad += 1
    if bad:
        print(f"LIVE TREE FAILS ITS OWN MANIFEST ({bad} files) -> adopt the new tree")
        return 2

    table = read_table(Path(a.table))
    same = [f for f, h in live.items() if table.get(f) == h]
    diff = [f for f, h in live.items() if f in table and table[f] != h]
    new = [f for f in live if f not in table]
    print(f"vs {a.table}: match {len(same)}, differ {len(diff)}, unknown {len(new)}")
    for f in diff:
        print(f"  DIFF {f}: live {live[f][:12]} ours {table[f][:12]}")
    for f in new:
        print(f"  NEW  {f}: live {live[f][:12]}")
    if diff or new:
        print("=> DRIFT: run the full adoption gate")
        return 1
    print("=> NO DRIFT: the scored tree is still the live tree")
    return 0


if __name__ == "__main__":
    sys.exit(main())
