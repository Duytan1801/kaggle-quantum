#!/usr/bin/env python3
"""atlas_family: rebuild one chemistry family folder from this dataset.

Loaders are stored once each (content-addressed by SHA-256 prefix) in kmx/chemistry/loaders/, factorizations in
factorizations/, and families.csv says which loaders and which factorization make up each family. This writes

    OUTDIR/angle_k_<k>.kmx      (decompressed text)
    OUTDIR/submission.npz       (the family's factorization, byte for byte as published)

    python atlas_family.py FAMILY_ID OUTDIR [--atlas DATASET_ROOT]
    python atlas_family.py --list [--atlas DATASET_ROOT]   # families whose files are all in the dataset

Licence: Apache-2.0.
"""
import argparse
import csv
import gzip
import os
import shutil
import sys

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def families(root):
    with open(os.path.join(root, "families.csv")) as f:
        return {r["family_id"]: r for r in csv.DictReader(f)}


def _find(path):
    """The file at PATH, or PATH + '.gz' (Kaggle serves the uploaded .gz files decompressed)."""
    for p in (path, path + ".gz"):
        if os.path.exists(p):
            return p
    return None


def _copy(src, dst):
    opener = gzip.open if src.endswith(".gz") else open
    with opener(src, "rb") as fi, open(dst, "wb") as fo:
        shutil.copyfileobj(fi, fo)


def materialise(family_id, outdir, root=DEFAULT_ROOT):
    fam = families(root)[family_id]
    os.makedirs(outdir, exist_ok=True)
    written = []
    for item in fam["loader_sha12s"].split(";"):
        k, sha = item.split(":")
        src = _find(os.path.join(root, "kmx", "chemistry", "loaders", sha + ".kmx"))
        if src is None:
            raise FileNotFoundError(f"loader {sha} (angle_k_{k}) is not included in this dataset")
        dst = os.path.join(outdir, f"angle_k_{k}.kmx")
        _copy(src, dst)
        written.append(dst)
    for sha in filter(None, fam["npz_sha12"].split(";")):
        src = _find(os.path.join(root, "factorizations", sha + ".npz"))
        if src is not None:
            dst = os.path.join(outdir, "submission.npz")
            _copy(src, dst)
            written.append(dst)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(description="Write the files of one chemistry family to a folder.")
    ap.add_argument("family_id", nargs="?", help="a family_id from families.csv")
    ap.add_argument("outdir", nargs="?", help="folder to write")
    ap.add_argument("--atlas", default=DEFAULT_ROOT, help="dataset root (default: the folder above tools/)")
    ap.add_argument("--list", action="store_true", help="list families that are complete in the dataset")
    a = ap.parse_args(argv)
    if a.list:
        for fid, r in families(a.atlas).items():
            if r["complete_in_atlas"] == "True":
                print(fid, r["n_loaders"], r["toffoli_static_sum"])
        return
    if not (a.family_id and a.outdir):
        ap.error("give FAMILY_ID and OUTDIR, or --list")
    for p in materialise(a.family_id, a.outdir, a.atlas):
        print(p)


if __name__ == "__main__":
    sys.exit(main())
