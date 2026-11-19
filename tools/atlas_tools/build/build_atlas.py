#!/usr/bin/env python3
"""Build the "QCC Circuit Atlas" Kaggle dataset folder from public-scan outputs.

Idempotent: re-run it whenever more scan folders (out*/) arrive. Every output is regenerated from the inputs in a
fixed order, compressed files are written with fixed gzip headers, files that already hold the right bytes are not
rewritten, and store files that are no longer referenced are removed.

Inputs (all paths are arguments; defaults match the original workstation layout next to this script):
  --scan-root      folder with out*/ subfolders, each holding scan.csv, kmx/ and a atlas-scan*.log
  --extra-scan-root  folder with appended scans (v2: scan_local.py hash scans of downloaded public outputs, no
                   kickmix). Their rows only ADD files and sources: a file already found by a --scan-root scan keeps
                   its v1 first source, family id and metrics.
  --push-root      folder with push25*/kernel-metadata.json of the scan kernels (maps "slug/..." paths to owners)
  --sources-list   all.txt, one owner/slug per line (fallback owner lookup)
  --receipts-glob  official-verifier receipts (receipt.json) of our own submissions
  --credits        manifest.csv of the dataset manwithacat/vqcc-apache-public-circuits (credit names/URLs only)
  --licence-cache  folder with dataset-metadata.json files from `kaggle datasets metadata OWNER/SLUG -p DIR`
  --out            dataset folder to (re)build

Never imports kickmix. No network access, except `--fetch-licences`, which runs the read-only
`kaggle datasets metadata` command for dataset sources missing from the licence cache.

Licence: Apache-2.0.
"""
import argparse
import collections
import csv
import glob
import gzip
import hashlib
import io
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KAGGLE = "https://www.kaggle.com"
COMPETITION = "google-verifiable-quantum-circuit-compilation"
REDISTRIBUTABLE = {"apache-2.0", "cc0-1.0", "cc-by-4.0", "cc-by-sa-4.0", "cc-by-3.0", "cc-by-sa-3.0", "mit",
                   "odc-by", "odbl", "pddl", "cc0", "other-permissive"}
NOTEBOOK_LICENCE = "apache-2.0"
NOTEBOOK_BASIS = ("Kaggle default licence of public notebooks and their outputs (Apache 2.0); "
                  "not checked notebook by notebook")
KIND_TASK = {"invsqrt": "invsqrt", "dqi": "dqi", "chem": "chemistry", "npz": "chemistry"}
SOURCE_RANK = {"competition": 0, "notebook": 1, "dataset": 2}


# ----------------------------------------------------------------------------------------------- small helpers
def write_if_changed(path, data):
    """Write bytes only when the file content differs (keeps mtimes stable across idempotent re-runs)."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    if os.path.exists(path):
        with open(path, "rb") as f:
            if f.read() == data:
                return False
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return True


def read_bytes(src):
    """Bytes of a store source: a path, or (zip path, member) / (path, "") from an appended scan's npz_locations."""
    if isinstance(src, tuple):
        path, member = src
        if member:
            import zipfile
            with zipfile.ZipFile(path) as z:
                return z.read(member)
        src = path
    with open(src, "rb") as f:
        return f.read()


def gzip_file(src, dst):
    """Deterministic gzip (mtime 0, no file name). Skips work when dst already exists and decompresses to src."""
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return False
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    with open(tmp, "wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as fo:
            fo.write(read_bytes(src))
    os.replace(tmp, dst)
    return True


def sha256_file(path):
    if isinstance(path, tuple):
        return hashlib.sha256(read_bytes(path)).hexdigest()
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_text(header, rows):
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    for r in rows:
        w.writerow(["" if r.get(k) is None else r.get(k) for k in header])
    return buf.getvalue()


def to_int(v):
    v = (v or "").strip()
    return int(v) if re.fullmatch(r"-?\d+", v) else None


def angle_k(name):
    m = re.search(r"angle_k_(\d+)\.kmb$", name)
    return int(m.group(1)) if m else None


# ----------------------------------------------------------------------------------------------- source mapping
def scan_kernels(push_root):
    """kernel id slug -> {"datasets": [...], "kernels": [...]} from push*/kernel-metadata.json."""
    out = {}
    for p in sorted(glob.glob(os.path.join(push_root, "push*", "kernel-metadata.json"))):
        try:
            m = json.load(open(p))
        except (OSError, ValueError):
            continue
        out[m["id"].split("/")[-1]] = {"datasets": m.get("dataset_sources", []), "kernels": m.get("kernel_sources", [])}
    return out


def scan_kernel_of(folder):
    logs = sorted(glob.glob(os.path.join(folder, "*.log")))
    return os.path.basename(logs[0])[:-4] if logs else ""


def resolve_source(path, kernel_meta, fallback):
    """Return (type, owner, slug, inner_path) for one scan.csv source path."""
    parts = path.split("/")
    if parts[0] in ("notebooks", "datasets") and len(parts) >= 3:
        return ("notebook" if parts[0] == "notebooks" else "dataset"), parts[1], parts[2], "/".join(parts[3:])
    if parts[0] == "competitions" and len(parts) >= 2:
        return "competition", "", parts[1], "/".join(parts[2:])
    slug, inner = parts[0], "/".join(parts[1:])
    if slug == COMPETITION:
        return "competition", "", slug, inner
    hits = [("notebook", r) for r in kernel_meta.get("kernels", []) if r.split("/")[1] == slug]
    hits += [("dataset", r) for r in kernel_meta.get("datasets", []) if r.split("/")[1] == slug]
    if len(hits) != 1:
        cands = fallback.get(slug, [])
        if len(cands) == 1:
            hits = [("notebook", cands[0])]
    if len(hits) == 1:
        t, ref = hits[0]
        return t, ref.split("/")[0], slug, inner
    return "unknown", "", slug, inner


def source_url(t, owner, slug):
    if t == "notebook":
        return f"{KAGGLE}/code/{owner}/{slug}"
    if t == "dataset":
        return f"{KAGGLE}/datasets/{owner}/{slug}"
    if t == "competition":
        return f"{KAGGLE}/competitions/{slug}"
    return ""


def source_ref(t, owner, slug):
    return f"competition:{slug}" if t == "competition" else (f"{owner}/{slug}" if owner else f"?/{slug}")


# ----------------------------------------------------------------------------------------------- licences
def dataset_licence(ref, cache, fetch, kaggle_cli):
    owner, slug = ref.split("/")
    p = os.path.join(cache, owner, slug, "dataset-metadata.json")
    if not os.path.exists(p) and fetch and kaggle_cli:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        subprocess.run([kaggle_cli, "datasets", "metadata", ref, "-p", os.path.dirname(p)],
                       check=False, capture_output=True, timeout=120)
    if not os.path.exists(p):
        return "", "licence not read (no cached `kaggle datasets metadata` output)"
    info = json.load(open(p))
    info = info.get("info", info)
    names = [l.get("name", "") for l in info.get("licenses", [])]
    return ";".join(n.lower() for n in names), f"`kaggle datasets metadata {ref}` (read {time.strftime('%Y-%m-%d', time.gmtime(os.path.getmtime(p)))})"


# ----------------------------------------------------------------------------------------------- main build
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--scan-root", default=os.path.join(HERE, "..", "scan25"))
    ap.add_argument("--extra-scan-root", default=os.path.join(HERE, "scan_v2"))
    ap.add_argument("--push-root", default=os.path.join(HERE, ".."))
    ap.add_argument("--sources-list", default=os.path.join(HERE, "..", "scan25", "all.txt"))
    ap.add_argument("--receipts-glob", default=os.path.join(HERE, "..", "out*", "receipt.json"))
    ap.add_argument("--credits", default=os.path.join(HERE, "..", "pub", "manifest.csv"))
    ap.add_argument("--licence-cache", default=os.path.join(HERE, "cache", "licences"))
    ap.add_argument("--fetch-licences", action="store_true")
    ap.add_argument("--kaggle-cli", default=shutil.which("kaggle") or "")
    ap.add_argument("--out", default=os.path.join(HERE, "dataset"))
    ap.add_argument("--no-cover", action="store_true")
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)

    fallback = collections.defaultdict(list)
    if os.path.exists(a.sources_list):
        for line in open(a.sources_list):
            line = line.strip()
            if "/" in line:
                fallback[line.split("/")[1]].append(line)
    kernels = scan_kernels(a.push_root)

    # ---- 1. read every scan folder in a fixed order (out, out-2, out-3, ... numeric)
    def scan_order(p):
        m = re.search(r"out-?(\d*)$", p.rstrip("/"))
        return int(m.group(1) or 1) if m else 10 ** 6
    scans = sorted([p for p in glob.glob(os.path.join(a.scan_root, "out*")) if os.path.isfile(os.path.join(p, "scan.csv"))],
                   key=scan_order)
    n_base_scans = len(scans)
    extra = sorted(p for p in glob.glob(os.path.join(a.extra_scan_root, "out*")) if os.path.isfile(os.path.join(p, "scan.csv"))) \
        if a.extra_scan_root and os.path.isdir(a.extra_scan_root) else []
    scans += extra
    occ = []            # one entry per (scan row)
    kmx_files = {}      # sha12 -> path of kmx/npz bytes in some scan folder
    scan_info = []
    for si, folder in enumerate(scans):
        kid = scan_kernel_of(folder)
        meta = kernels.get(kid, {})
        date = time.strftime("%Y-%m-%d", time.gmtime(os.path.getmtime(os.path.join(folder, "scan.csv"))))
        n = 0
        for ri, r in enumerate(csv.DictReader(open(os.path.join(folder, "scan.csv")))):
            if r["kind"] not in KIND_TASK:
                continue
            t, owner, slug, inner = resolve_source(r["source"], meta, fallback)
            name = r["name"]
            if r["source"].endswith(".zip"):
                inner_path = f"{inner}:{name}" if inner else name
                container, fam_dir = r["source"], posixpath.dirname(name)
            else:
                inner_path = inner
                container, fam_dir = posixpath.dirname(r["source"]), ""
            err = r["qubits"] == "ERR"
            occ.append(dict(scan=si, scan_name=kid or os.path.basename(folder), scan_date=date, row=ri,
                            kind=r["kind"], sha12=r["sha12"], name=posixpath.basename(name), src_type=t, owner=owner,
                            slug=slug, inner_path=inner_path, group=(si, container, fam_dir),
                            qubits=None if err else to_int(r["qubits"]),
                            toffoli=None if err else to_int(r["toffoli_static"]),
                            ops=None if err else to_int(r["ops"]), err=r["toffoli_static"] if err else ""))
            n += 1
        for f in sorted(glob.glob(os.path.join(folder, "kmx", "*"))):
            b = os.path.basename(f)
            m = re.search(r"__([0-9a-f]{12})\.(kmx|npz)$", b)
            if m and m.group(1) not in kmx_files:
                kmx_files[m.group(1)] = f
        locp = os.path.join(folder, "npz_locations.json")
        if os.path.exists(locp):
            for h12, loc in sorted(json.load(open(locp)).items()):
                kmx_files.setdefault(h12, (loc["path"], loc["member"]))
        scan_info.append(dict(folder=os.path.basename(folder), kernel=kid, rows=n, date=date))

    # ---- 2. receipts (full SHA-256 and official verifier results of our own submissions)
    full_sha = {}
    receipts_circuit = {}   # full sha -> (receipt label, verify dict)
    receipts_chem = []      # (label, {k:sha}, npz sha, verify dict)
    for p in sorted(glob.glob(a.receipts_glob)):
        rc = json.load(open(p))
        d = os.path.dirname(p)
        logs = sorted(glob.glob(os.path.join(d, "*.log")))
        label = os.path.basename(d) + (f" ({os.path.basename(logs[0])[:-4]})" if logs else "")
        shas = rc.get("sha256", {})
        for fn, h in shas.items():
            full_sha[h[:12]] = h
        for task, v in rc.get("verify", {}).items():
            if task in ("invsqrt", "dqi") and v.get("circuit_sha256"):
                receipts_circuit.setdefault(v["circuit_sha256"], []).append((label, v))
            elif task == "dfthcsos":
                loaders = {angle_k(fn): h[:12] for fn, h in shas.items() if fn.startswith("dfthcsos/") and angle_k(fn) is not None}
                npz = next((h[:12] for fn, h in shas.items() if fn.endswith(".npz")), "")
                receipts_chem.append((label, loaders, npz, v))

    if extra and os.path.exists(os.path.join(a.extra_scan_root, "scan_summary.json")):
        for h in json.load(open(os.path.join(a.extra_scan_root, "scan_summary.json")))["sha256"]:
            full_sha.setdefault(h[:12], h)

    # ---- 3. credits from the manwithacat manifest (names and URLs only)
    credits = {}
    if os.path.exists(a.credits):
        for r in csv.DictReader(open(a.credits)):
            credits[r["sha12"]] = (r.get("source_notebook_url", ""), r.get("author", ""), r.get("licence_evidence", ""))
    confirmed_nb = {c[0] for c in credits.values() if "Apache 2.0" in c[2]}

    def credit_for(o):
        if o["src_type"] != "dataset" or o["owner"] != "manwithacat":
            return None
        m = re.search(r"(?:chemistry/|factorizations/|dqi/|invsqrt/)([0-9a-f]{12})", o["inner_path"])
        return credits.get(m.group(1)) if m else None

    # ---- 4. licences per source
    lic = {}
    for o in occ:
        ref = source_ref(o["src_type"], o["owner"], o["slug"])
        if ref in lic:
            continue
        if o["src_type"] == "dataset":
            l, basis = dataset_licence(ref, a.licence_cache, a.fetch_licences, a.kaggle_cli)
        elif o["src_type"] == "notebook":
            url = source_url("notebook", o["owner"], o["slug"])
            l = NOTEBOOK_LICENCE
            basis = ("Apache 2.0 page footer recorded per notebook in the manwithacat/vqcc-apache-public-circuits manifest"
                     if url in confirmed_nb else NOTEBOOK_BASIS)
        elif o["src_type"] == "competition":
            l, basis = "competition-data", "competition data: governed by the competition rules, not redistributed"
        else:
            l, basis = "", "source owner could not be resolved"
        lic[ref] = (l, basis)

    def redistributable(ref):
        return any(x in REDISTRIBUTABLE for x in lic[ref][0].split(";") if x)

    # ---- 5. per-file aggregation (dedup by sha12 within the scan namespace)
    by_sha = collections.OrderedDict()
    for o in occ:
        by_sha.setdefault(o["sha12"], []).append(o)

    def occ_key(o):
        # base (v1) scans first, so appended scans never change an existing file's first source or family id
        return (o["scan"] >= n_base_scans, SOURCE_RANK.get(o["src_type"], 9), o["scan"], o["row"])

    files = {}
    for sha, os_ in by_sha.items():
        os_ = sorted(os_, key=occ_key)
        first = os_[0]
        good = next((o for o in sorted(os_, key=lambda o: (o["scan"], o["row"])) if o["qubits"] is not None), None)
        refs = []
        for o in os_:
            r = source_ref(o["src_type"], o["owner"], o["slug"])
            if r not in refs:
                refs.append(r)
        files[sha] = dict(first=first, occ=os_, good=good, refs=refs)

    # ---- 6. chemistry families: files that share one container/dir in one scan, keyed by their member set
    groups = collections.OrderedDict()
    for o in occ:
        if o["kind"] in ("chem", "npz"):
            if o["src_type"] == "dataset" and o["owner"] == "manwithacat" and "factorizations" in o["group"][1]:
                continue  # standalone copies of family factorizations, not a family
            groups.setdefault(o["group"], []).append(o)
    fam_members = collections.OrderedDict()
    for g, os_ in groups.items():
        loaders = tuple(sorted({(angle_k(o["name"]), o["sha12"]) for o in os_ if o["kind"] == "chem"}, key=lambda t: (t[0] is None, t[0] or 0, t[1])))
        npzs = tuple(sorted({o["sha12"] for o in os_ if o["kind"] == "npz"}))
        key = (loaders, npzs)
        fam_members.setdefault(key, []).extend(os_)
    families = []
    for key, os_ in fam_members.items():
        loaders, npzs = key
        os_ = sorted(os_, key=occ_key)
        families.append(dict(loaders=loaders, npzs=npzs, occ=os_, first=os_[0],
                             member_hash=hashlib.sha256(repr(key).encode()).hexdigest()[:12]))
    # stable ids: sort by first occurrence then member hash; assign ids in that order
    families.sort(key=lambda f: (occ_key(f["first"]), f["member_hash"]))
    used_ids = set()
    for f in families:
        f0 = f["first"]
        base = f"{f0['owner'] or 'competition'}__{f0['slug']}__{(f['npzs'][0] if len(f['npzs']) == 1 else 'set-' + f['member_hash'])}"
        fid, i = base, 2
        while fid in used_ids:
            fid, i = f"{base}-{i}", i + 1
        used_ids.add(fid)
        f["id"] = fid
    file_family = {}
    for f in families:
        for k, s in f["loaders"]:
            file_family.setdefault(s, []).append(f["id"])
        for s in f["npzs"]:
            file_family.setdefault(s, []).append(f["id"])

    # ---- 7. decide inclusion and write the store
    competition_shas = {s for s, d in files.items() if any(o["src_type"] == "competition" for o in d["occ"])}
    referenced = set()
    rows = []
    for sha, d in files.items():
        f0, good = d["first"], d["good"]
        task = KIND_TASK[f0["kind"]]
        ref0 = source_ref(f0["src_type"], f0["owner"], f0["slug"])
        lic_ref = ref0 if redistributable(ref0) else next((r for r in d["refs"] if redistributable(r)), "")
        reason, path = "", ""
        if sha in competition_shas:
            reason = "competition data (official sample/reference file): not redistributed"
            lic_ref = ""
        elif not lic_ref:
            reason = "no source with a licence that allows redistribution"
        elif f0["kind"] == "dqi":
            reason = "DQI circuits are too large for this dataset: metadata only, binary at the source"
        elif sha not in kmx_files:
            if all(o["scan"] >= n_base_scans for o in d["occ"]):
                reason = ("no kmx text: found only by a v2 hash scan (no kickmix); the binary is at the source"
                          if f0["kind"] != "npz" else "factorization bytes not kept by the scan")
            else:
                reason = ("the scan could not convert this file (kickmix failed to load in that scan run)"
                          if f0["kind"] != "npz" else "factorization bytes not kept by the scan")
        else:
            if f0["kind"] == "invsqrt":
                path = f"kmx/invsqrt/{sha}.kmx"
                src = kmx_files[sha]
                dst = os.path.join(out, path)
                if not (os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src)):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copyfile(src, dst)
            elif f0["kind"] == "chem":
                path = f"kmx/chemistry/loaders/{sha}.kmx"
                # stored gzip-compressed (.gz); Kaggle serves it decompressed under `path`
                gzip_file(kmx_files[sha], os.path.join(out, path + ".gz"))
            else:
                h = sha256_file(kmx_files[sha])
                if h[:12] != sha:
                    reason = "factorization bytes in the scan do not match the recorded hash"
                else:
                    full_sha.setdefault(sha, h)
                    path = f"factorizations/{sha}.npz"
                    gzip_file(kmx_files[sha], os.path.join(out, path + ".gz"))
            if path:
                referenced.add(path + ".gz" if f0["kind"] in ("chem", "npz") else path)
        credit = next((c for c in (credit_for(o) for o in d["occ"]) if c), None) if f0["src_type"] == "dataset" else None
        ver = receipts_circuit.get(full_sha.get(sha, ""), [])
        lic_l, lic_b = lic.get(lic_ref, ("", ""))
        if not lic_ref:
            lic_l, lic_b = lic[ref0]
        rows.append(dict(
            task=task, file_type="factorization" if f0["kind"] == "npz" else "circuit", file_name=f0["name"],
            angle_k=angle_k(f0["name"]) if f0["kind"] == "chem" else None, sha12=sha, sha256=full_sha.get(sha, ""),
            qubits=good and good["qubits"], toffoli_static=good and good["toffoli"], ops=good and good["ops"],
            metrics_status=("not a circuit" if f0["kind"] == "npz" else
                            ("ok" if good["scan"] < n_base_scans else "ok (counted from the kmx text)") if good else
                            "not measured: found only by a v2 hash scan (no kickmix)" if all(o["scan"] >= n_base_scans for o in d["occ"])
                            else "not measured: kickmix failed to load in the scan run"),
            family_ids=";".join(file_family.get(sha, [])) if task == "chemistry" else "",
            first_source_type=f0["src_type"], first_source_ref=ref0, first_source_url=source_url(f0["src_type"], f0["owner"], f0["slug"]),
            first_source_path=f0["inner_path"], author=f0["owner"], author_url=f"{KAGGLE}/{f0['owner']}" if f0["owner"] else "",
            credited_notebook_url=credit[0] if credit else "", credited_author=credit[1] if credit else "",
            n_sources=len(d["refs"]), all_sources=";".join(d["refs"]), first_seen_scan=f0["scan_name"], first_seen_date=f0["scan_date"],
            licence=lic_l, licence_basis=lic_b, licence_source=lic_ref or ref0,
            included=bool(path), included_path=path, exclusion_reason=reason,
            verified_status=ver[-1][1].get("status", "") if ver else "", verified_score=ver[-1][1].get("score") if ver else None,
            verified_toffoli_count=ver[-1][1].get("toffoli_count") if ver else None,
            verified_receipts=";".join(v[0] for v in ver)))
    rows.sort(key=lambda r: (["invsqrt", "dqi", "chemistry"].index(r["task"]), r["file_type"], r["sha12"]))
    row_by = {r["sha12"]: r for r in rows}

    # ---- 8. family table
    fam_rows = []
    for f in families:
        f0 = f["first"]
        lrows = [row_by[s] for k, s in f["loaders"]]
        nrow = [row_by[s] for s in f["npzs"]]
        complete_metrics = all(r["qubits"] is not None for r in lrows) and bool(lrows)
        ks = [k for k, s in f["loaders"]]
        ver = [rc for rc in receipts_chem if rc[2] in f["npzs"] and sorted(rc[1].items()) == sorted((k, s) for k, s in f["loaders"])]
        refs = []
        for o in f["occ"]:
            r = source_ref(o["src_type"], o["owner"], o["slug"])
            if r not in refs:
                refs.append(r)
        credit = next((c for c in (credit_for(o) for o in f["occ"]) if c), None) if f0["src_type"] == "dataset" else None
        fam_rows.append(dict(
            family_id=f["id"], first_source_type=f0["src_type"], first_source_ref=source_ref(f0["src_type"], f0["owner"], f0["slug"]),
            first_source_url=source_url(f0["src_type"], f0["owner"], f0["slug"]),
            first_source_path=(f0["group"][2] if f0["group"][1].endswith(".zip") else f0["inner_path"].rsplit("/", 1)[0] if "/" in f0["inner_path"] else ""),
            author=f0["owner"], credited_notebook_url=credit[0] if credit else "", credited_author=credit[1] if credit else "",
            npz_sha12=";".join(f["npzs"]), n_loaders=len(lrows),
            angle_ks=";".join("" if k is None else str(k) for k in ks),
            loader_sha12s=";".join(f"{k}:{s}" for k, s in f["loaders"]),
            qubits_max=max(r["qubits"] for r in lrows) if complete_metrics else None,
            toffoli_static_sum=sum(r["toffoli_static"] for r in lrows) if complete_metrics else None,
            ops_sum=sum(r["ops"] for r in lrows) if complete_metrics else None,
            n_sources=len(refs), all_sources=";".join(refs), first_seen_scan=f0["scan_name"],
            loaders_included=sum(1 for r in lrows if r["included"]),
            factorization_included=bool(nrow) and all(r["included"] for r in nrow),
            complete_in_atlas=bool(lrows) and all(r["included"] for r in lrows) and bool(nrow) and all(r["included"] for r in nrow),
            verified_status=ver[-1][3].get("status", "") if ver else "", verified_score=ver[-1][3].get("score") if ver else None,
            verified_toffoli_count=ver[-1][3].get("toffoli_count") if ver else None,
            verified_lambda_eff=ver[-1][3].get("lambda_eff") if ver else None,
            verified_num_qubits=ver[-1][3].get("num_qubits") if ver else None,
            verified_receipts=";".join(v[0] for v in ver)))

    # ---- 9. sources table
    src_rows = []
    seen = collections.OrderedDict()
    for o in sorted(occ, key=lambda o: (o["src_type"], o["owner"], o["slug"])):
        ref = source_ref(o["src_type"], o["owner"], o["slug"])
        s = seen.setdefault(ref, dict(source_ref=ref, source_type=o["src_type"], owner=o["owner"], slug=o["slug"],
                                      url=source_url(o["src_type"], o["owner"], o["slug"]), licence=lic[ref][0],
                                      licence_basis=lic[ref][1], scans=[], files=set(), first=set()))
        if o["scan_name"] not in s["scans"]:
            s["scans"].append(o["scan_name"])
        s["files"].add(o["sha12"])
    for r in rows:
        seen[r["first_source_ref"]]["first"].add(r["sha12"])
    for s in seen.values():
        inc = sum(1 for h in s["first"] if row_by[h]["included"])
        src_rows.append(dict(source_ref=s["source_ref"], source_type=s["source_type"], owner=s["owner"], slug=s["slug"], url=s["url"],
                             licence=s["licence"], licence_basis=s["licence_basis"], scans=";".join(s["scans"]),
                             distinct_files=len(s["files"]), first_source_of=len(s["first"]), first_source_of_included=inc))

    # ---- 10. write tables, prune stale store files
    CIRC_COLS = ["task", "file_type", "file_name", "angle_k", "sha12", "sha256", "qubits", "toffoli_static", "ops", "metrics_status",
                 "family_ids", "first_source_type", "first_source_ref", "first_source_url", "first_source_path", "author", "author_url",
                 "credited_notebook_url", "credited_author", "n_sources", "all_sources", "first_seen_scan", "first_seen_date",
                 "licence", "licence_basis", "licence_source", "included", "included_path", "exclusion_reason",
                 "verified_status", "verified_score", "verified_toffoli_count", "verified_receipts"]
    FAM_COLS = list(fam_rows[0].keys()) if fam_rows else []
    SRC_COLS = list(src_rows[0].keys()) if src_rows else []
    write_if_changed(os.path.join(out, "circuits.csv"), csv_text(CIRC_COLS, rows))
    write_if_changed(os.path.join(out, "families.csv"), csv_text(FAM_COLS, fam_rows))
    write_if_changed(os.path.join(out, "sources.csv"), csv_text(SRC_COLS, src_rows))
    for sub in ("kmx", "factorizations"):
        for f in glob.glob(os.path.join(out, sub, "**", "*"), recursive=True):
            rel = os.path.relpath(f, out).replace(os.sep, "/")
            if os.path.isfile(f) and rel not in referenced:
                os.remove(f)

    stats = dict(scans=scan_info, rows=len(rows), families=len(fam_rows), sources=len(src_rows),
                 by_task={t: collections.Counter() for t in ("invsqrt", "dqi", "chemistry")})
    for r in rows:
        c = stats["by_task"][r["task"]]
        c[r["file_type"]] += 1
        c[r["file_type"] + "_included"] += int(r["included"])
    stats["by_task"] = {t: dict(c) for t, c in stats["by_task"].items()}
    stats["exclusions"] = dict(collections.Counter(r["exclusion_reason"] for r in rows if not r["included"]))
    stats["families_complete_in_atlas"] = sum(1 for f in fam_rows if f["complete_in_atlas"])
    write_if_changed(os.path.join(HERE, "build_stats.json"), json.dumps(stats, indent=1, sort_keys=True) + "\n")

    sys.path.insert(0, HERE)
    sys.dont_write_bytecode = True
    import atlas_docs  # README, metadata, cover, credits (kept separate so the text is easy to edit)
    atlas_docs.write_all(out, rows, fam_rows, src_rows, stats, CIRC_COLS, FAM_COLS, SRC_COLS, cover=not a.no_cover)
    # keep a copy of the builder next to the data so the table can be reproduced
    for fn in ("build_atlas.py", "atlas_docs.py", "scan_local.py", "kmxstats.py", "build_contrib.py"):
        if not os.path.exists(os.path.join(HERE, fn)):
            continue
        write_if_changed(os.path.join(out, "tools", "build", fn), open(os.path.join(HERE, fn), "rb").read())
    print(json.dumps(stats, indent=1, sort_keys=True))


if __name__ == "__main__":
    main()
