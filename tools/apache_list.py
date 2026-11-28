#!/usr/bin/env python3
"""apache_list.py — page through a Kaggle dataset's file list.

WHY THIS TOOL EXISTS
---------------------
`kaggle datasets files -d <ref> --page-size 20000` silently returns only the
FIRST PAGE (~200 rows; the max page size is 200) and prints a
"Next Page Token" line to stdout that the CLI has no flag to consume from the
outside.  The QCC Apache public-circuits dataset has ~8,500 files, so a
single CLI call shows ~2 % of the catalogue and looks like "the catalogue has
no invsqrt members" — which is exactly the false negative that cost the
campaign days in 2026-11-22.

This tool drives the CLI's own `--page-token` pagination until the token is
exhausted, and writes a complete listing to a file.  With `--metadata` it
also downloads the small sidecar `.json` next to each member, so the
width/cost of every published invsqrt / DQI member can be compared against
ours without pulling 10 GB of `.kmb` binaries.

Usage:
  apache_list.py --dataset manwithacat/vqcc-apache-public-circuits \
                 --out work/recon/apache_files_<date>.txt
  apache_list.py --dataset ... --metadata circuits/invsqrt/ --out ...jsonl
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys

KAGGLE = "qaenv/bin/kaggle"


def list_files(dataset: str) -> list[str]:
    """Walk every page of the dataset file list, returning the names."""
    names: list[str] = []
    token = ""
    seen_tokens: set[str] = set()
    page = 0
    while True:
        cmd = [KAGGLE, "datasets", "files", dataset, "--format", "json",
               "--page-size", "200"]
        if token:
            cmd += ["--page-token", token]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if p.returncode != 0:
            sys.stderr.write(p.stderr[-2000:] + "\n")
            raise SystemExit(f"kaggle datasets files failed rc={p.returncode}")
        text = p.stdout
        m = re.search(r"Next Page Token = (\S+)", text)
        token = m.group(1) if m else ""
        rows = []
        # the CLI prints "Next Page Token = <tok>" BEFORE the JSON array, so
        # the JSON starts at the first '[' or '{' after that line.
        start = min((i for i in (text.find("["), text.find("{")) if i >= 0),
                    default=-1)
        if start >= 0:
            try:
                payload, _ = json.JSONDecoder().raw_decode(text[start:])
                if isinstance(payload, dict):
                    rows = payload.get("datasetFiles", [])
                elif isinstance(payload, list):
                    rows = payload
            except json.JSONDecodeError:
                rows = []
        for r in rows:
            n = r.get("name") if isinstance(r, dict) else str(r)
            if n:
                names.append(n)
        page += 1
        if not token or token in seen_tokens:
            break
        seen_tokens.add(token)
        if page % 10 == 0:
            print(f"  ... {page} pages, {len(names)} files", file=sys.stderr, flush=True)
    return names


def fetch_metadata(dataset: str, names: list[str], out: pathlib.Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    def one(name: str):
        cmd = [KAGGLE, "datasets", "download", "-d", dataset, "-f", name,
               "-p", "/tmp/opencode/apache_meta", "--force"]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if p.returncode != 0:
                return name, {"_error": p.stderr[-300:]}
            src = pathlib.Path("/tmp/opencode/apache_meta") / pathlib.Path(name).name
            if not src.is_file():
                return name, {"_error": "not downloaded"}
            return name, json.loads(src.read_text())
        except Exception as exc:  # noqa: BLE001
            return name, {"_error": str(exc)}

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as f, ThreadPoolExecutor(max_workers=4) as ex:
        for name, payload in ex.map(one, names):
            f.write(json.dumps({"name": name, "meta": payload}) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--metadata", default="",
                    help="prefix filter; also fetch the sidecar .json of each member")
    a = ap.parse_args()
    names = list_files(a.dataset)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(names) + "\n")
    print(f"wrote {len(names)} entries -> {a.out}")
    if a.metadata:
        targets = [n for n in names
                   if n.startswith(a.metadata) and n.endswith(".json")]
        print(f"fetching {len(targets)} sidecar metadata files", file=sys.stderr)
        fetch_metadata(a.dataset, targets, a.out.with_suffix(".meta.jsonl"))
        print(f"wrote metadata -> {a.out.with_suffix('.meta.jsonl')}")


if __name__ == "__main__":
    main()
