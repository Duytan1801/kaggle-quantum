#!/usr/bin/env python3
"""Hash scan of downloaded public notebook outputs, without kickmix (QCC Circuit Atlas v2).

The v1 scans ran on Kaggle with the competition's kickmix (qubits, Toffoli count, kmx text). This scan runs anywhere:
it walks folders of public notebook outputs that were downloaded with the read-only `kaggle kernels output OWNER/SLUG`
command, hashes every circuit / factorization file (also inside .zip archives), and writes one scan folder per
download date in the same layout as a v1 scan (scan.csv, kmx/, <scan name>.log), so build_atlas.py can merge it.

Metrics: qubits / toffoli_static / ops are filled only when a kmx text of the exact file is available (exported
with kickmix in an earlier Kaggle run; the file name carries the SHA-256 prefix of the .kmb bytes). They are
counted from the text with the same rules as kickmix (checked equal on 204 v1 circuits). Otherwise they stay empty.

Never copied: anything under a `verifiers/` or `kickmix/` folder, and any file whose hash equals a file of the
competition's own data (`--competition-dir`, hashed locally): competition data is not redistributed.

Usage:
  python scan_local.py --outputs-root DIR --kmx-dir D1 --kmx-dir D2 ... --competition-dir VERIFIERS --out SCANROOT
Folder names in DIR: [<batch>_]<owner>_<slug> (batch = r2..re, ignored); `--map NAME=owner/slug` overrides.
A folder may be a symlink to an output folder (its date is the target's modification date).

Licence: Apache-2.0.
"""
import argparse
import csv
import glob
import hashlib
import io
import json
import lzma
import os
import re
import shutil
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from kmxstats import stats as kmx_stats  # noqa: E402

BATCH = re.compile(r"^r[0-9a-z]_")
SKIP_PARTS = ("verifiers/", "kickmix/", "/verifiers", "/kickmix")


def kind_of(name):
    base = name.rsplit("/", 1)[-1].replace("dfthcsos__", "")
    if base.endswith(".kmb.xz"):
        base = base[:-3]
    if base.startswith("invsqrt") and base.endswith(".kmb"):
        return "invsqrt"
    if base.startswith("dqi") and base.endswith(".kmb"):
        return "dqi"
    if base.startswith("angle_k_") and base.endswith(".kmb"):
        return "chem"
    if base.endswith(".npz"):
        return "npz"
    return None


def is_factorization(data):
    """True for a DF-THC submission.npz (has the arrays the chemistry verifier reads)."""
    import numpy as np
    try:
        with np.load(io.BytesIO(data), allow_pickle=False) as z:
            return {"W", "H2_I", "U", "angle_words"} <= set(z.files)
    except Exception:
        return False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--outputs-root", action="append", required=True, help="folder of downloaded outputs (repeatable)")
    ap.add_argument("--kmx-dir", action="append", default=[])
    ap.add_argument("--competition-dir", action="append", default=[], help="local copy of competition data (hashed, never copied)")
    ap.add_argument("--map", action="append", default=[], help="FOLDER=owner/slug (or FOLDER=dataset:owner/slug)")
    ap.add_argument("--skip", action="append", default=[], help="folder name prefix to skip (e.g. src_)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    comp = set()
    for d in a.competition_dir:
        for p in glob.glob(os.path.join(d, "**", "*"), recursive=True):
            if os.path.isfile(p):
                comp.add(hashlib.sha256(open(p, "rb").read()).hexdigest())
    over = dict(m.split("=", 1) for m in a.map)

    # kmx texts we hold, keyed by the hash prefix in their name (8 or 12 hex)
    kmx_by_prefix = {}
    for d in a.kmx_dir:
        for p in sorted(glob.glob(os.path.join(d, "*.kmx"))):
            m = re.search(r"_([0-9a-f]{8,64})\.kmx$", os.path.basename(p))
            if m:
                kmx_by_prefix.setdefault(m.group(1), p)

    batches = {}   # date -> rows
    found = {}     # sha256 -> (kind, data or None, base name)
    skipped = []
    folders = sorted((f, os.path.join(r, f)) for r in a.outputs_root for f in os.listdir(r))
    for folder, full in folders:
        if not os.path.isdir(full) or any(folder.startswith(s) for s in a.skip):
            continue
        ref = over.get(folder)
        if ref is None:
            name = BATCH.sub("", folder)
            if "_" not in name:
                skipped.append((folder, "cannot split owner_slug"))
                continue
            owner, slug = name.split("_", 1)
            ref = f"{owner}/{slug}"
        typ = "notebooks"
        if ref.startswith("dataset:"):
            typ, ref = "datasets", ref[len("dataset:"):]
        date = time.strftime("%Y-%m-%d", time.gmtime(os.path.getmtime(full)))
        rows = batches.setdefault(date, [])
        for p in sorted(glob.glob(os.path.join(full, "**", "*"), recursive=True)):
            if not os.path.isfile(p):
                continue
            rel = os.path.relpath(p, full).replace(os.sep, "/")
            if any(s in "/" + rel for s in SKIP_PARTS):
                if kind_of(rel) or rel.endswith(".zip"):
                    skipped.append((f"{folder}/{rel}", "competition folder (verifiers/kickmix): not scanned"))
                continue
            src = f"{typ}/{ref}/{rel}"

            def handle(name, data):
                k = kind_of(name)
                if k is None:
                    return
                if name.endswith(".kmb.xz"):
                    data = lzma.decompress(data)
                    name = name[:-3]
                h = hashlib.sha256(data).hexdigest()
                if h in comp:
                    skipped.append((f"{src}:{name}", "identical to a competition data file: not recorded"))
                    return
                if k == "npz" and not is_factorization(data):
                    return
                rows.append(dict(source=src, name=name, kind=k, sha=h))
                if h not in found:
                    loc = (os.path.abspath(p), name if p.endswith(".zip") else "")
                    found[h] = (k, loc if k == "npz" else None, os.path.basename(name))
            try:
                if p.endswith(".zip"):
                    with zipfile.ZipFile(p) as Z:
                        for n in Z.namelist():
                            if any(s in "/" + n for s in SKIP_PARTS):
                                continue
                            if n.endswith((".kmb", ".npz", ".kmb.xz")):
                                handle(n, Z.read(n))
                elif p.endswith((".kmb", ".npz", ".kmb.xz")):
                    handle(rel, open(p, "rb").read())
            except (zipfile.BadZipFile, OSError) as e:
                skipped.append((src, f"unreadable: {e}"))

    # attach kmx texts and metrics by hash prefix (a prefix must identify exactly one scanned file)
    metrics, kmx_for = {}, {}
    for pre, path in kmx_by_prefix.items():
        hits = [h for h in found if h.startswith(pre)]
        if len(hits) == 1 and found[hits[0]][0] in ("invsqrt", "chem"):
            h = hits[0]
            kmx_for[h] = path
            metrics[h] = kmx_stats(path)

    shutil.rmtree(a.out, ignore_errors=True)
    summary = {}
    for i, date in enumerate(sorted(batches)):
        npz_loc = {}
        name = f"atlas-v2-output-scan-{date}"
        d = os.path.join(a.out, f"out-v2-{date}")
        os.makedirs(os.path.join(d, "kmx"))
        open(os.path.join(d, f"{name}.log"), "w").write(
            f"{name}: hash scan of public notebook outputs downloaded on {date} (UTC), no kickmix\n")
        with open(os.path.join(d, "scan.csv"), "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["source", "name", "kind", "sha12", "qubits", "toffoli_static", "ops"])
            for r in batches[date]:
                q, t, o = metrics.get(r["sha"], ("", "", ""))
                w.writerow([r["source"], r["name"], r["kind"], r["sha"][:12], q, t, o])
        for r in batches[date]:
            h = r["sha"]
            k, data, base = found[h]
            # no byte copies (disk budget): kmx texts are symlinked, npz bytes are referenced by location
            if k == "npz" and data is not None:
                npz_loc[h[:12]] = dict(path=data[0], member=data[1])
            elif h in kmx_for:
                stem = re.sub(r"\.kmb$", "", base)
                dst = os.path.join(d, "kmx", f"{'invsqrt' if k == 'invsqrt' else 'chem'}__{stem}__{h[:12]}.kmx")
                if not os.path.lexists(dst):
                    os.symlink(os.path.abspath(kmx_for[h]), dst)
        json.dump(npz_loc, open(os.path.join(d, "npz_locations.json"), "w"), indent=1, sort_keys=True)
        # scan date = download date (builder reads the scan.csv mtime)
        t = time.mktime(time.strptime(date + " 12:00", "%Y-%m-%d %H:%M")) - time.timezone
        os.utime(os.path.join(d, "scan.csv"), (t, t))
        summary[date] = len(batches[date])
    full = {h: dict(kind=v[0], name=v[2]) for h, v in found.items()}
    json.dump(dict(rows_per_date=summary, distinct=len(found), with_kmx=len(kmx_for), skipped=skipped, sha256=full),
              open(os.path.join(a.out, "scan_summary.json"), "w"), indent=1, sort_keys=True)
    print(json.dumps(dict(rows_per_date=summary, distinct=len(found), with_kmx=len(kmx_for), skipped=len(skipped)), indent=1))


if __name__ == "__main__":
    main()
