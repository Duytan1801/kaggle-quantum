"""atlas_io: find and read the files of the QCC Circuit Atlas from a notebook (no kickmix needed, except to_kmb).

    import sys; sys.path.insert(0, "/kaggle/input/qcc-circuit-atlas/tools")
    import atlas_io as A
    A.root()                                   # the dataset folder (works whatever the mount path is)
    A.circuit("e46d90c36d1b")                  # the circuits.csv row of a file (dict)
    A.local_path("e46d90c36d1b")               # kmx/invsqrt/e46d90c36d1b.kmx (or the .npz of a factorization)
    A.contribution("invsqrt_dead_write_fix")   # one entry of contributions/index.json
    A.to_kmb(A.local_path("e46d90c36d1b"), "/kaggle/working/invsqrt.kmb")   # kmx -> kmb with the competition's kickmix

Kaggle serves the uploaded .gz files decompressed, so on Kaggle every path is the plain .kmx / .npz; in a local
copy of the dataset the same files are .kmx.gz / .npz.gz and every function here accepts both.
Licence: Apache-2.0.
"""
import csv
import functools
import glob
import gzip
import hashlib
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))


@functools.lru_cache(1)
def root():
    """Dataset root: $QCC_ATLAS, else the folder above tools/, else a search of /kaggle/input."""
    cands = [os.environ.get("QCC_ATLAS", ""), os.path.dirname(HERE)]
    cands += sorted(os.path.dirname(p) for p in glob.glob("/kaggle/input/**/circuits.csv", recursive=True))
    for c in cands:
        if c and os.path.exists(os.path.join(c, "circuits.csv")) and os.path.isdir(os.path.join(c, "tools")):
            return c
    raise FileNotFoundError("QCC Circuit Atlas not found: attach the dataset or set QCC_ATLAS")


def resolve(rel):
    """Absolute path of a dataset file given its published path (tries the .gz store name too)."""
    p = os.path.join(root(), rel)
    for c in (p, p + ".gz"):
        if os.path.exists(c):
            return c
    raise FileNotFoundError(rel)


def read_bytes(rel_or_abs):
    """Bytes of a dataset file (decompressed if stored as .gz)."""
    p = rel_or_abs if os.path.isabs(rel_or_abs) and os.path.exists(rel_or_abs) else resolve(rel_or_abs)
    with (gzip.open(p, "rb") if p.endswith(".gz") else open(p, "rb")) as f:
        return f.read()


def materialize(rel, dst):
    """Write the (decompressed) file to dst and return dst."""
    os.makedirs(os.path.dirname(os.path.abspath(dst)) or ".", exist_ok=True)
    with open(dst, "wb") as f:
        f.write(read_bytes(rel))
    return dst


@functools.lru_cache(1)
def circuits():
    with open(os.path.join(root(), "circuits.csv")) as f:
        return {r["sha12"]: r for r in csv.DictReader(f)}


def circuit(sha):
    """circuits.csv row for a SHA-256 prefix (12 hex characters, or longer)."""
    return circuits()[sha[:12]]


def local_path(sha):
    """Absolute path of the copy of this file in the dataset (raises if the file is metadata only)."""
    r = circuit(sha)
    if r["included"] != "True":
        raise FileNotFoundError(f"{sha[:12]} is metadata only here: {r['exclusion_reason']} ({r['first_source_url']})")
    return resolve(r["included_path"])


@functools.lru_cache(1)
def contributions():
    with open(os.path.join(root(), "contributions", "index.json")) as f:
        return json.load(f)


def contribution(name):
    """One entry of contributions/index.json (paths are relative to the dataset root)."""
    return contributions()[name]


def find_kickmix(base="/kaggle/input"):
    """The competition's kickmix folder (needs the competition data attached)."""
    for p in sorted(glob.glob(os.path.join(base, "**", "kickmix"), recursive=True)):
        if os.path.isdir(p) and os.path.isdir(os.path.join(os.path.dirname(p), "verifiers")):
            return p
    raise FileNotFoundError("kickmix not found: attach the competition data")


def to_kmb(kmx, out, kickmix_dir=None):
    """Convert a kmx text (path, .gz allowed) to a .kmb with the competition's kickmix; returns the SHA-256."""
    import sys
    km_dir = kickmix_dir or find_kickmix()
    if km_dir not in sys.path:
        sys.path.insert(0, km_dir)
    import kickmix as km
    src = kmx
    if kmx.endswith(".gz"):
        src = out + ".kmx"
        with gzip.open(kmx, "rb") as fi, open(src, "wb") as fo:
            shutil.copyfileobj(fi, fo)
    km.Circuit.from_file(src, format="kmx").to_file(out, format="kmb")
    if src != kmx:
        os.remove(src)
    return hashlib.sha256(open(out, "rb").read()).hexdigest()
