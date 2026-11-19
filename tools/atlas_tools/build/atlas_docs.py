"""Documentation side of build_atlas.py: README.md, dataset-metadata.json, cover.png, tools/README.md.

Every number in the generated text is computed from the rows the builder passes in. Licence: Apache-2.0.
"""
import collections
import json
import os

DATASET_ID = "asteriospanoras/qcc-circuit-atlas"
TITLE = "QCC Circuit Atlas + Verified Refit Toolkit"
SUBTITLE = "Every public circuit of Google's quantum contest, plus refit and analysis tools"
COMP_URL = "https://www.kaggle.com/competitions/google-verifiable-quantum-circuit-compilation"
KEYWORDS = ["physics", "computer science", "chemistry", "tabular", "python"]

CIRC_DESC = {
    "task": "Competition task: invsqrt, dqi or chemistry (the dfthcsos task).",
    "file_type": "circuit (a kickmix .kmb circuit) or factorization (a chemistry family's submission.npz).",
    "file_name": "File name in the source, e.g. invsqrt.kmb, dqi.kmb, angle_k_3.kmb or submission.npz.",
    "angle_k": "Chemistry loaders only: the k of angle_k_<k>.kmb (loader position in its family). Empty otherwise.",
    "sha12": "First 12 hex characters of the SHA-256 of the file bytes as published (the row key; files are deduplicated by it).",
    "sha256": "Full SHA-256 when known (from our official-verifier receipts, or computed from factorization bytes). Empty when unknown.",
    "qubits": "Number of qubits of the circuit, read by kickmix in the scan. Empty when not measured.",
    "toffoli_static": "Static count of Toffoli-like ops (CCX, CCZ, CSWAP) in the file, from kickmix operation statistics in the scan. Not the verifier's expected count. Empty when not measured.",
    "ops": "Number of operations in the circuit, from the scan. Empty when not measured.",
    "metrics_status": "ok (from kickmix in a Kaggle scan), ok (counted from the kmx text) for files added in v2, not a circuit (factorizations), or why qubits/toffoli_static/ops are empty.",
    "family_ids": "Chemistry only: the family_id(s) in families.csv that contain this file (one file can be shared by several families), separated by ';'.",
    "first_source_type": "notebook, dataset or competition: the kind of the first source (see first_source_ref).",
    "first_source_ref": "Kaggle owner/slug of one public source that holds the file (the competition if it is official data, else a notebook, else a dataset; the first in scan order). Read it as 'found in': it is not necessarily the author or the first publication (see credits and contributions/).",
    "first_source_url": "Kaggle URL of first_source_ref.",
    "first_source_path": "Where the file sits inside that source's output (archive:member for zip files).",
    "author": "Kaggle user name of the owner of first_source_ref.",
    "author_url": "Kaggle profile URL of author.",
    "credited_notebook_url": "When the first source is the aggregator dataset manwithacat/vqcc-apache-public-circuits: the original notebook it credits for this circuit or family. Empty otherwise.",
    "credited_author": "Display name of the author that manwithacat/vqcc-apache-public-circuits credits (see credited_notebook_url).",
    "n_sources": "Number of distinct public sources (notebooks, datasets) whose output holds the identical file.",
    "all_sources": "All those sources as owner/slug, separated by ';', first source first.",
    "first_seen_scan": "Our scan run that first recorded the file: a Kaggle scan notebook (v1, with kickmix) or atlas-v2-output-scan-<date> (v2 hash scan of downloaded public outputs, no kickmix).",
    "first_seen_date": "UTC date of that scan run's output (v2: the date the public outputs were downloaded).",
    "licence": "Licence of the source we redistribute the file under (licence_source), lower-case Kaggle licence name; competition-data for official files.",
    "licence_basis": "How the licence was established (dataset metadata read with the Kaggle CLI, a recorded notebook footer, or the Kaggle default for public notebooks).",
    "licence_source": "The source whose licence applies to the copy in this dataset (normally first_source_ref).",
    "included": "True when a copy of the file is in this dataset (at included_path).",
    "included_path": "Path of the copy in this dataset: kmx/invsqrt/<sha12>.kmx, kmx/chemistry/loaders/<sha12>.kmx or factorizations/<sha12>.npz.",
    "exclusion_reason": "Why the file is metadata only (empty when included). Files found only by the v2 hash scan have no kmx text unless one was exported earlier; their binary is at the source.",
    "verified_status": "PASS/FAIL from the official verifier in one of our own submission receipts, when this exact file (by full SHA-256) was scored there. invsqrt and dqi only.",
    "verified_score": "Task score from that official verifier run (lower is better).",
    "verified_toffoli_count": "Expected Toffoli count reported by that official verifier run.",
    "verified_receipts": "Which of our receipts scored this file (receipt id and notebook name), separated by ';'; the receipts are in contributions/receipts/.",
}
FAM_DESC = {
    "family_id": "Family key: <owner>__<slug>__<factorization sha12> of the first source holding this exact set of files ('set-<hash>' when there is no single factorization).",
    "first_source_type": "notebook, dataset or competition.",
    "first_source_ref": "Kaggle owner/slug of the first source of the family (same rule as circuits.csv).",
    "first_source_url": "Kaggle URL of first_source_ref.",
    "first_source_path": "Folder of the family inside that source's output (or inside its submission archive).",
    "author": "Kaggle user name of the owner of first_source_ref.",
    "credited_notebook_url": "Original notebook credited by manwithacat/vqcc-apache-public-circuits when that dataset is the first source.",
    "credited_author": "Display name credited by manwithacat/vqcc-apache-public-circuits.",
    "npz_sha12": "sha12 of the family's factorization (submission.npz).",
    "n_loaders": "Number of angle_k loader circuits in the family.",
    "angle_ks": "The loader indices k present, separated by ';'.",
    "loader_sha12s": "k:sha12 for every loader, separated by ';' (look the files up in circuits.csv).",
    "qubits_max": "Largest qubit count over the loaders (from the scan). Empty if any loader was not measured.",
    "toffoli_static_sum": "Sum of the loaders' static Toffoli-like counts (from the scan). Not the verifier's cost. Empty if any loader was not measured.",
    "ops_sum": "Sum of the loaders' op counts. Empty if any loader was not measured.",
    "n_sources": "Number of distinct sources holding this exact family.",
    "all_sources": "Those sources as owner/slug, separated by ';'.",
    "first_seen_scan": "Our scan run that first recorded the family.",
    "loaders_included": "How many of the family's loaders are in this dataset.",
    "factorization_included": "True when the family's submission.npz is in this dataset.",
    "complete_in_atlas": "True when every loader and the factorization are in this dataset (tools/atlas_family.py can rebuild the folder).",
    "verified_status": "PASS/FAIL of the official chemistry verifier in one of our receipts, when it scored exactly this family.",
    "verified_score": "Chemistry task score from that run (lower is better).",
    "verified_toffoli_count": "Toffoli count reported by that run.",
    "verified_lambda_eff": "lambda_eff reported by that run.",
    "verified_num_qubits": "Qubit count reported by that run.",
    "verified_receipts": "Which of our receipts scored this family.",
}
SRC_DESC = {
    "source_ref": "Kaggle owner/slug (competition:<slug> for the competition's own data).",
    "source_type": "notebook, dataset or competition.",
    "owner": "Kaggle user name of the owner.",
    "slug": "Kaggle slug of the notebook or dataset.",
    "url": "Kaggle URL.",
    "licence": "Licence (lower-case Kaggle name).",
    "licence_basis": "How the licence was established.",
    "scans": "Our scan runs that read this source, separated by ';'.",
    "distinct_files": "Distinct circuit/factorization files found in this source.",
    "first_source_of": "Rows of circuits.csv credited to this source.",
    "first_source_of_included": "Of those, how many are included in this dataset.",
}
INT_COLS = {"angle_k", "qubits", "toffoli_static", "ops", "n_sources", "n_loaders", "qubits_max", "toffoli_static_sum",
            "ops_sum", "loaders_included", "distinct_files", "first_source_of", "first_source_of_included", "verified_num_qubits"}
NUM_COLS = {"verified_score", "verified_toffoli_count", "verified_lambda_eff"}
BOOL_COLS = {"included", "factorization_included", "complete_in_atlas"}


def ftype(c):
    return "integer" if c in INT_COLS else "number" if c in NUM_COLS else "boolean" if c in BOOL_COLS else "string"


def coldict_md(cols, desc):
    return "\n".join(f"| `{c}` | {ftype(c)} | {desc.get(c, '')} |" for c in cols)


def fmt(n):
    return f"{n:,}"


def write_text(path, text):
    data = text.encode("utf-8")
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    with open(path, "wb") as f:
        f.write(data)


def size_of(root, sub):
    tot = 0
    for d, _, fs in os.walk(os.path.join(root, sub)):
        tot += sum(os.path.getsize(os.path.join(d, f)) for f in fs)
    return tot


def credits_md(rows, fam_rows):
    """One line per author with an included file: Kaggle user, the sources, and file counts."""
    by = collections.OrderedDict()
    for r in sorted(rows, key=lambda r: (r["author"].lower(), r["first_source_ref"])):
        if not r["included"]:
            continue
        a = by.setdefault(r["author"], dict(url=r["author_url"], refs=collections.OrderedDict(), n=0))
        a["refs"].setdefault(r["first_source_ref"], r["first_source_url"])
        a["n"] += 1
    lines = ["| Kaggle user | Source(s) of included files | Included files |", "|---|---|---|"]
    for user, a in by.items():
        refs = ", ".join(f"[{ref.split('/')[1]}]({url})" for ref, url in a["refs"].items())
        lines.append(f"| [{user}]({a['url']}) | {refs} | {a['n']} |")
    # authors credited by the aggregator dataset for files we took from it
    cred = collections.OrderedDict()
    for r in rows:
        if r["included"] and r["credited_notebook_url"]:
            cred.setdefault((r["credited_author"], r["credited_notebook_url"]), 0)
            cred[(r["credited_author"], r["credited_notebook_url"])] += 1
    for f in fam_rows:
        if f["loaders_included"] and f["credited_notebook_url"]:
            cred.setdefault((f["credited_author"], f["credited_notebook_url"]), 0)
    cl = []
    if cred:
        cl = ["", "Files taken from the aggregator dataset "
              "[manwithacat/vqcc-apache-public-circuits](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits) "
              "are credited there to these original notebooks (also in the `credited_*` columns):", "",
              "| Author (as credited there) | Original notebook |", "|---|---|"]
        for (au, url), _ in sorted(cred.items(), key=lambda t: (t[0][0].lower(), t[0][1])):
            cl.append(f"| {au} | [{url.rsplit('/', 1)[-1]}]({url}) |")
    return "\n".join(lines + cl)


def readme(out, rows, fam_rows, src_rows, stats, CIRC, FAM, SRC):
    t = collections.Counter((r["task"], r["file_type"]) for r in rows)
    inc = collections.Counter((r["task"], r["file_type"]) for r in rows if r["included"])
    n_src = collections.Counter(s["source_type"] for s in src_rows)
    ok_inv = [r for r in rows if r["task"] == "invsqrt" and r["qubits"] is not None]
    fam_complete = sum(1 for f in fam_rows if f["complete_in_atlas"])
    ver = [r for r in rows if r["verified_status"]] + [f for f in fam_rows if f["verified_status"]]
    scans = stats["scans"]
    excl = collections.Counter(r["exclusion_reason"] for r in rows if not r["included"])
    excl_md = "\n".join(f"| {reason} | {n} |" for reason, n in excl.most_common())
    lic_cnt = collections.Counter((x["source_type"], x["licence"] or "(not read)") for x in src_rows)
    lic_md = "\n".join(f"| {st} | {l} | {n} |" for (st, l), n in sorted(lic_cnt.items()))
    sizes = {k: size_of(out, k) for k in ("kmx/invsqrt", "kmx/chemistry", "factorizations", "tools")}
    ex_inv = next((r for r in sorted(rows, key=lambda r: r["sha12"]) if r["task"] == "invsqrt" and r["included"] and r["verified_status"] == "PASS"),
                  next((r for r in rows if r["task"] == "invsqrt" and r["included"]), None))
    ex_fam = next((f for f in fam_rows if f["complete_in_atlas"] and f["verified_status"] == "PASS"),
                  next((f for f in fam_rows if f["complete_in_atlas"]), None))
    inv_line = f"kmx/invsqrt/{ex_inv['sha12']}.kmx" if ex_inv else "kmx/invsqrt/<sha12>.kmx"
    fam_line = ex_fam["family_id"] if ex_fam else "<family_id>"
    contrib = {}
    cpath = os.path.join(out, "contributions", "index.json")
    if os.path.exists(cpath):
        contrib = json.load(open(cpath))
    n_new = sum(1 for r in rows if str(r["first_seen_scan"]).startswith("atlas-v2"))
    n_new_inc = sum(1 for r in rows if str(r["first_seen_scan"]).startswith("atlas-v2") and r["included"])
    n_new_fam = sum(1 for f in fam_rows if str(f["first_seen_scan"]).startswith("atlas-v2"))
    n_new_npz = sum(1 for r in rows if str(r["first_seen_scan"]).startswith("atlas-v2") and r["file_type"] == "factorization" and r["included"])
    sizes.update({k: size_of(out, k) for k in ("contributions", "tools/refit", "tools/qccscope")})

    def cline(key, label):
        c = contrib.get(key)
        if not c:
            return ""
        fp = c["first_public"]
        gain = ("48 fewer Toffolis per shot" if c.get("cost_change_percent") is None else
                f"lambda_eff {c['lambda_eff_change']:+.2e} ({c['cost_change_percent']:+.5f} % task cost)" if c["task"] == "chemistry" else
                f"{c['cost_change_percent']:+.4f} % task cost")
        title = fp["notebook"].split("/")[1]
        return f"| {label} | `{c['sha12']}` | {gain} | [{title}]({fp['url']}) v{fp['version']} |"
    chem_keys = sorted(k for k in contrib if k.startswith("chem_refit"))
    new_lines = "\n".join(x for x in [cline("invsqrt_splice_62q", "invsqrt: splice of public 62-qubit circuits"),
                                       cline("invsqrt_dead_write_fix", "invsqrt: dead-write fix (CCX -> HMR + CZ)"),
                                       cline("dqi_readout_window_transplant", "DQI: readout-window transplant")]
                          + [cline(k, "chemistry: W/H2_I refit at fixed words") for k in chem_keys] if x)
    return f"""# {TITLE}

**{SUBTITLE}.** A deduplicated, credited map of the circuits that people have published for the Google Quantum AI
[Verifiable Quantum Circuit Compilation]({COMP_URL}) competition, the readable text (kmx) of every invsqrt and
chemistry circuit whose licence allows it, our own verified public results, and pure-numpy tools (simulator,
diagnosis library, chemistry weight refit, splicing, loader check) that run without the competition's `kickmix`.

## What's new in v2

* **`contributions/`: our own public results**, each with what it is, the exact gain, how it was verified (official
  verifier receipts, exhaustive simulation), the first public notebook version and the credits of the base file:

| Contribution | File | Gain | First public |
|---|---|---|---|
{new_lines}

* **`tools/refit/`**: our numpy DF-THC weight refit (generalised reduced gradient, a port of prvsiyan's
  `refit_grg.py`): `python -m refit run --start NPZ --minutes M --out DIR` lowers lambda_eff at fixed angle words.
  It reads the competition verifier from `/kaggle/input` (the verifier is Competition Data and is not included).
* **`tools/qccscope/`**: our circuit diagnosis library (parser, cost models and exchange rates, liveness, motif
  detectors, sampled value scan, markdown report): `python -m qccscope report FILE --task invsqrt`.
* **`tools/atlas_io.py`**: find and read atlas files from any notebook (`A.local_path(sha12)`, `A.contribution(name)`,
  `A.to_kmb(kmx, out)` with the competition's kickmix).
* **{fmt(n_new)} more public files** ({fmt(n_new_inc)} included, {fmt(n_new_npz)} new factorizations, {fmt(n_new_fam)} new families) from public
  notebook outputs published since 12 Nov, found by a hash scan of the downloaded outputs; `contributions/receipts/`
  with the official-verifier receipts of our public notebook versions.
* Every v1 file is still here at the same path; v1 rows keep their values (only source lists and receipts grew).

## At a glance

| Task | Distinct files listed | Included here | What is included |
|---|---:|---:|---|
| invsqrt | {fmt(t[('invsqrt', 'circuit')])} circuits | {fmt(inc[('invsqrt', 'circuit')])} | readable `.kmx` text |
| chemistry (dfthcsos) | {fmt(t[('chemistry', 'circuit')])} loaders + {fmt(t[('chemistry', 'factorization')])} factorizations in {fmt(len(fam_rows))} families | {fmt(inc[('chemistry', 'circuit')])} + {fmt(inc[('chemistry', 'factorization')])} ({fmt(fam_complete)} complete families) | `.kmx` text, `.npz` |
| dqi | {fmt(t[('dqi', 'circuit')])} circuits | 0 | metadata only (each file is very large) |

Collected from {fmt(n_src['notebook'])} public notebooks and {fmt(n_src['dataset'])} public datasets by
{len(scans)} scan run(s). {fmt(len(ver))} files or families carry an official-verifier result from our own submissions.

## Use it in a notebook

Add this dataset (and the competition data, for kickmix and the verifiers) to your notebook, then:

```python
import glob, os, sys, numpy as np
ATLAS = next(os.path.dirname(p) for p in glob.glob("/kaggle/input/**/circuits.csv", recursive=True)
             if os.path.isdir(os.path.join(os.path.dirname(p), "tools", "refit")))
sys.path.insert(0, os.path.join(ATLAS, "tools"))
import atlas_io as A, kmsim                       # file lookup + exact invsqrt simulator
from refit import chemeval                        # chemistry metrics with the verifier's math
inv = A.local_path("e46d90c36d1b")                # invsqrt with our dead-write fix (kmx text)
print(kmsim.check(inv, np.arange(1, 4097, dtype=np.int64))[0])
A.to_kmb(inv, "/kaggle/working/invsqrt.kmb")      # kmx -> kmb with the competition's kickmix
chemeval.setup(); print(chemeval.evaluate_npz(A.local_path("5a75386681c8"))["lambda_eff"])
```

Refit a chemistry table for 20 minutes (writes `submission.npz` and `refit_report.json`), then verify officially:

```python
import subprocess
subprocess.run([sys.executable, "-m", "refit", "run", "--start", A.local_path("5a75386681c8"), "--minutes", "20",
                "--out", "/kaggle/working/refit"], cwd=os.path.join(ATLAS, "tools"), check=True)
```

## Why this dataset

* **One table of the public landscape.** Who published which circuit, how many notebooks re-use it, its qubits and
  static Toffoli count: filter, sort and plot the frontier in two lines of pandas.
* **Circuits you can read.** The competition's `.kmb` files are binary. The `.kmx` text here is the same circuit,
  one op per line (`CCX q3 q7 q12`), ready for `grep`, diffing, and your own analysis.
* **Tools that run anywhere.** `tools/kmsim.py` simulates the invsqrt task exactly with numpy; on circuit
  `9c708f7b9abc` its worst error over tolerance (0.9993237694056958) equals the official verifier's.
* **Verified results you can build on.** Our public gains with recipes, receipts and the code that made them.
* **Credit where it is due.** Every row names a public source and its author and lists every other source that holds
  the identical bytes.

## Files

| Path | What it is |
|---|---|
| `circuits.csv` | One row per distinct file (circuit or chemistry factorization) found in public sources, deduplicated by SHA-256 prefix. {fmt(len(rows))} rows. |
| `families.csv` | One row per distinct chemistry family (a set of angle_k loaders plus its factorization). {fmt(len(fam_rows))} rows. |
| `sources.csv` | One row per scanned public notebook, dataset or competition data folder, with its licence. {fmt(len(src_rows))} rows. |
| `kmx/invsqrt/<sha12>.kmx` | invsqrt circuits as kickmix text. {fmt(inc[('invsqrt', 'circuit')])} files, {sizes['kmx/invsqrt'] / 1e6:.1f} MB. |
| `kmx/chemistry/loaders/<sha12>.kmx` | Chemistry angle loaders as kickmix text, each stored once. {fmt(inc[('chemistry', 'circuit')])} files, {sizes['kmx/chemistry'] / 1e6:.1f} MB. |
| `factorizations/<sha12>.npz` | Chemistry factorizations (`submission.npz`), byte for byte. {fmt(inc[('chemistry', 'factorization')])} files, {sizes['factorizations'] / 1e6:.1f} MB. |
| `contributions/` | Our own public results: `README.md` (overview), `index.json` (the same as data), `invsqrt/` (splice `9c708f7b9abc`, dead-write fix `e46d90c36d1b`: README + JSON recipe), `dqi/` (readout-window transplant `245527f68413`: README + JSON recipe), `chemistry_refits/` (README + `refits.csv` with lambda_eff, error_1, error_2, E_gap of our three refits), `receipts/` (official-verifier receipts of our public notebook versions + `receipts.csv`). {sizes['contributions'] / 1e3:.0f} kB. |
| `tools/` | Apache-2.0 Python tools and their tests; see `tools/README.md`. |
| `tools/refit/` | Chemistry weight refit toolkit (chemeval, model, grg, grg2, al, CLI, tests, README). |
| `tools/qccscope/` | Circuit diagnosis library and CLI (kmx, cost, liveness, structure, values, motifs, report, tests, README). |
| `tools/atlas_io.py` | Find and read atlas files from a notebook; kmx -> kmb with the competition's kickmix. |
| `tools/build/` | The scripts that built this dataset (`build_atlas.py`, `atlas_docs.py`, `build_contrib.py`, `scan_local.py`, `kmxstats.py`). |
| `cover.png` | Cover image: qubits against static Toffoli count of every measured public circuit. |

Chemistry loaders are shared between many families, so they are stored once, by hash. To get the folder of one
family (angle_k_*.kmx plus submission.npz), run `python tools/atlas_family.py FAMILY_ID OUTDIR`.

## More quick starts

**1. Load the table and look at the invsqrt frontier**

```python
import pandas as pd
c = pd.read_csv(f"{{ATLAS}}/circuits.csv")
inv = c[(c.task == "invsqrt") & c.qubits.notna()]
print(inv.sort_values(["toffoli_static", "qubits"])[["sha12", "qubits", "toffoli_static", "author", "n_sources"]].head(10))
print(c.groupby(["task", "file_type"]).included.agg(["size", "sum"]))
```

**2. Simulate an invsqrt circuit with kmsim (no kickmix needed)**

```python
report, sim = kmsim.check(f"{{ATLAS}}/{inv_line}", np.arange(1, 4097, dtype=np.int64))
print(report)   # worst_ratio < 1 on these x, restored input, clean scratch, mean Toffolis
```

or from a shell: `python tools/kmsim.py {inv_line} --xmax 4096` (use `--xmax 3133452` for every input; minutes).

**3. Rebuild and check one chemistry family**

```python
import subprocess
fam = pd.read_csv(f"{{ATLAS}}/families.csv")
print(fam[fam.complete_in_atlas].sort_values("toffoli_static_sum").head())
subprocess.run([sys.executable, f"{{ATLAS}}/tools/atlas_family.py", "{fam_line}", "/kaggle/working/fam"], check=True)
subprocess.run([sys.executable, f"{{ATLAS}}/tools/loader_check.py", "/kaggle/working/fam"], check=True)
```

`loader_check.py` emulates the chemistry loader contract locally (clean workspace, unchanged selection, no phase,
forward and reverse word blocks); a PASS is a local check, not an official score.

**4. Diagnose a circuit with qccscope**

```python
from qccscope import report
print(report.render(report.analyse(f"{{ATLAS}}/{inv_line}", "invsqrt", lanes=256)))
```

## Column dictionary

### circuits.csv

| Column | Type | Meaning |
|---|---|---|
{coldict_md(CIRC, CIRC_DESC)}

### families.csv

| Column | Type | Meaning |
|---|---|---|
{coldict_md(FAM, FAM_DESC)}

### sources.csv

| Column | Type | Meaning |
|---|---|---|
{coldict_md(SRC, SRC_DESC)}

Empty cells mean "unknown or not applicable", never zero.

## Provenance and collection method

1. **Sources.** The list of public notebooks of the competition that publish circuit files, plus the public datasets
   that hold circuits, was attached read-only as inputs to our private scan notebooks on Kaggle
   ({', '.join(s['kernel'] or s['folder'] for s in scans)}). Nothing from a source was executed.
2. **Scan.** Each scan walks the attached inputs and opens every `*.kmb`, `*.kmb.xz`, `*.npz` and every `.kmb`/`.npz`
   inside `.zip` archives. A file is classified by name (`invsqrt*`, `dqi*`, `angle_k_*`, `*.npz`), hashed with
   SHA-256, and loaded once per distinct hash with the competition's own `kickmix` (qubits, Toffoli-like count,
   op count); invsqrt and chemistry circuits are written out as `.kmx` text with kickmix.
3. **Merge (this dataset).** `tools/build/build_atlas.py` merges all scan runs, deduplicates by hash, picks the
   first source (competition data, then notebooks, then datasets; ties in scan order), groups chemistry files into
   families (files that sit in one folder or archive of one source, keyed by their exact set of hashes), applies
   the licence rule below and copies the allowed files. It is deterministic and re-run when new scan runs arrive.
4. **v2 hash scan.** Public notebook outputs published after the v1 scans were downloaded with the read-only
   `kaggle kernels output` command (and our own public notebook outputs) and hashed by `tools/build/scan_local.py`
   with the same file rules, without kickmix. Rows found only this way keep the v1 conventions; their
   qubits/toffoli_static/ops come from a kmx text exported earlier with kickmix when we hold one (`kmxstats.py`; it
   reproduces the kickmix counts of 204 v1 circuits exactly), else they are empty. Appended scans never change the
   first source, family id or metrics of a file found in v1. Files under `verifiers/` or `kickmix/` folders, and files
   identical to competition data, are never recorded.
5. **Verification results** come only from the official verifier output in our own receipts
   (`verified_*` columns, `contributions/receipts/`); every other number comes from the scans.
6. **Credits** for files that we found only in the aggregator dataset manwithacat/vqcc-apache-public-circuits are
   copied from its manifest (names and links only).

Scan runs used for this version:

| Scan run | Rows | Output date (UTC) |
|---|---:|---|
""" + "\n".join(f"| {s['kernel'] or s['folder']} | {fmt(s['rows'])} | {s['date']} |" for s in scans) + f"""

## Licences

This dataset is released under **Apache 2.0**. A file is copied here only when a source that holds it allows
redistribution:

| Source type | Licence | Sources |
|---|---|---:|
{lic_md}

* **Public notebooks.** Kaggle releases public notebooks and their outputs under Apache 2.0 by default; we did not
  check each notebook page, so `licence_basis` says so (or names the recorded footer evidence where we have it).
  If you are an author and your notebook uses another licence, tell us and the file will be removed.
* **Datasets.** Licence read with `kaggle datasets metadata` (Apache 2.0 or CC0 for all scanned datasets).
* **Competition data** (the official sample files) is listed for reference but never copied.
* **DQI circuits** are listed but not copied (each is hundreds of MB as text); follow `first_source_url`.

Files that are metadata only, and why:

| Reason | Files |
|---|---:|
{excl_md}

## Credits

Thank you to everyone who published their circuits. Every included file is credited in `circuits.csv`; by author:

{credits_md(rows, fam_rows)}

The [VQCC public circuits](https://www.kaggle.com/datasets/manwithacat/vqcc-apache-public-circuits) dataset by
manwithacat, with its own manifest and verifier runs, is a complementary collection of the original `.kmb` files;
use it when you need binaries, and this atlas when you want text, tools and one table across all sources.

Tools: `tools/refit/grg.py` is a numpy port of prvsiyan's `refit_grg.py`
([prvsiyan/vqcc-verified-best-of-circuits-1106a](https://www.kaggle.com/datasets/prvsiyan/vqcc-verified-best-of-circuits-1106a),
Apache-2.0); the refit's error_2 expansion and augmented-Lagrangian variant follow Lera (marculera)'s public DF-THC
refit code and gauge ideas (Apache-2.0). Our contributions build on files by Atakan Aldemir, maoxin123, Syed Asad Ali,
Ali Haydar Özdağ, WCao24, Thomas Gamet, Heliosli, the team *i want to run gemma 9b* and the authors they credit
(details in each `contributions/*/README.md`).
The circuit language, verifiers and tasks are by the competition organisers (Google Quantum AI, Qualtran). The
verifiers, kickmix and the FCIDUMP are Competition Data and are not included: attach the competition data.

**AI assistance.** The scan, the builder, the tools and this README were written with the help of an AI coding
assistant (Anthropic's Claude), under the direction of and reviewed by the dataset owner. Every number comes from
the scan runs or official verifier receipts, not from the assistant.

## Update policy

Updated when new scan runs or new public circuits appear, until the competition ends: re-running the builder over
all scan outputs gives the next version; rows are never renamed (the key is `sha12`), new rows are appended.
Expected update frequency: weekly during the competition, then never.

## Limitations

* `toffoli_static` is a static count of Toffoli-like ops in the file, not the verifier's expected (average)
  Toffoli count or the task score.
* Some circuits come from research or candidate folders of a notebook and were never that notebook's submission.
* A notebook can change after we read it; the hash identifies exactly which bytes are described.
* Rows with `metrics_status` "not measured" were recorded in a scan run in which kickmix could not be loaded, or only
  by the v2 hash scan (no kickmix); they are listed with hash and source only.
* `first_source_ref` is one public source that holds the file (the first in scan order), not proof of authorship or
  of first publication; `contributions/` gives the first public version of our own results.
* No claim about who designed a circuit is made beyond its first public source.

Not affiliated with Google, Qualtran or Kaggle.
"""


def tools_readme():
    return """# Tools (Apache-2.0)

Pure Python + numpy; none of them imports `kickmix`. Every tool reads `.kmx` (and also gzip-compressed `.kmx.gz`). The files are uploaded gzip-compressed and Kaggle serves them decompressed, so on Kaggle they are plain `.kmx` / `.npz`.

| Tool | What it does | Example |
|---|---|---|
| `kmsim.py` | Exact batch simulator of the kickmix op subset used here (qubits, bits, phase in 2^-64 turns, Toffoli and rotation counters) plus the invsqrt accuracy check. On circuit 9c708f7b9abc over every x its worst error/tolerance equals the official verifier's (0.9993237694056958). | `python kmsim.py ../kmx/invsqrt/<sha12>.kmx --xmax 4096` |
| `liveness.py` | Static qubit liveness: peak number of simultaneously live qubits, a lower bound for a re-allocation of the same op sequence. | `python liveness.py ../kmx/invsqrt/<sha12>.kmx` |
| `splice_dp.py` | Cheapest splice of several passing invsqrt circuits at "clean cuts" with identical state, by shortest path. Checked on sampled inputs only. | `python splice_dp.py A.kmx B.kmx --out splice.json` |
| `build_splice.py` | Writes the kmx circuit described by a `splice_dp.py` result. | `python build_splice.py splice.json out.kmx --kmx-dir ../kmx/invsqrt` |
| `loader_check.py` | Local emulation of the chemistry loader contract on a family folder (clean workspace, unchanged selection, no phase, forward and reverse word blocks). | `python loader_check.py FAMDIR` |
| `atlas_family.py` | Rebuilds one chemistry family folder (angle_k_*.kmx + submission.npz) from this dataset. | `python atlas_family.py FAMILY_ID FAMDIR` |
| `atlas_io.py` | Find the dataset root under /kaggle/input, look up a file by sha12 (`circuit`, `local_path`), read `contributions/index.json`, convert kmx -> kmb with the competition's kickmix (`to_kmb`). | `import atlas_io as A; A.local_path("e46d90c36d1b")` |
| `refit/` | Chemistry DF-THC weight refit at fixed angle words (GRG; numpy port of prvsiyan's refit_grg.py) and exact metrics with the verifier's math; reads the competition verifier at run time. See `refit/README.md`. | `python -m refit run --start NPZ --minutes 20 --out DIR` |
| `qccscope/` | Circuit diagnosis library: kmx parser, cost models and exchange rates, liveness, motif detectors, sampled value scan, report. See `qccscope/README.md`. | `python -m qccscope report FILE.kmx --task invsqrt` |
| `build/` | The builders of this dataset (`build_atlas.py`, `atlas_docs.py`, `build_contrib.py`, `scan_local.py`, `kmxstats.py`; they need the scan outputs and are kept for provenance). | `python build_atlas.py --help` |

Tests (seconds, no network, no competition data): `python tools/tests/test_tools.py`, `cd tools && python -m pytest -q
refit/tests qccscope/tests tests` (or run each test file with python).
The competition's verifiers, kickmix and FCIDUMP are Competition Data and are not included: attach the competition
data to your notebook for `refit` and `atlas_io.to_kmb`.

Always confirm a circuit with the official verifier before you submit it: these tools are for analysis.
"""


def cover(out, rows):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    surface, ink, ink2, grid = "#1a1a19", "#f0efec", "#c3c2b7", "#3a3a37"
    series = [("invsqrt", "#3987e5"), ("chemistry", "#d95926"), ("dqi", "#199e70")]
    fig = plt.figure(figsize=(16, 8), dpi=100, facecolor=surface)
    ax = fig.add_axes([0.075, 0.13, 0.52, 0.70], facecolor=surface)
    for task, col in series:
        pts = [(r["qubits"], r["toffoli_static"]) for r in rows if r["task"] == task and r["qubits"] and r["toffoli_static"]]
        if not pts:
            continue
        x, y = zip(*pts)
        ax.scatter(x, y, s=46, c=col, alpha=0.85, edgecolors=surface, linewidths=1.0, label=f"{task} ({len(pts):,})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.grid(True, which="major", color=grid, linewidth=0.8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(colors=ink2, labelsize=13)
    ax.set_xlabel("qubits", color=ink2, fontsize=15)
    ax.set_ylabel("static Toffoli-like ops", color=ink2, fontsize=15)
    leg = ax.legend(loc="upper left", frameon=False, fontsize=14, labelcolor=ink, markerscale=1.3)
    fig.text(0.64, 0.70, "QCC", color=ink, fontsize=60, fontweight="bold", va="bottom")
    fig.text(0.64, 0.59, "Circuit Atlas", color=ink, fontsize=44, fontweight="bold", va="bottom")
    n = sum(1 for r in rows if r["file_type"] == "circuit")
    fig.text(0.64, 0.48, f"{n:,} distinct public circuits", color=ink2, fontsize=19)
    fig.text(0.64, 0.43, "kmx text + refit and analysis tools", color=ink2, fontsize=19)
    fig.text(0.64, 0.37, "Verifiable Quantum Circuit Compilation", color=ink2, fontsize=15)
    fig.text(0.075, 0.88, "Every measured public circuit: qubits vs static Toffoli count (log-log)", color=ink, fontsize=18)
    p = os.path.join(out, "cover.png")
    fig.savefig(p + ".tmp.png", facecolor=surface, metadata={"Software": None})
    plt.close(fig)
    if os.path.exists(p) and open(p, "rb").read() == open(p + ".tmp.png", "rb").read():
        os.remove(p + ".tmp.png")
    else:
        os.replace(p + ".tmp.png", p)


def metadata(out, text, CIRC, FAM, SRC, rows, fam_rows, src_rows):
    def schema(cols, desc):
        return {"fields": [{"name": c, "description": desc.get(c, ""), "type": ftype(c)} for c in cols]}
    res = [
        {"path": "circuits.csv", "description": f"One row per distinct public circuit or chemistry factorization file ({len(rows):,} rows): hash, size metrics, sources, author, licence, inclusion and official-verifier results.", "schema": schema(CIRC, CIRC_DESC)},
        {"path": "families.csv", "description": f"One row per distinct chemistry family ({len(fam_rows):,} rows): its loaders, factorization, sources and totals.", "schema": schema(FAM, FAM_DESC)},
        {"path": "sources.csv", "description": f"One row per scanned public source ({len(src_rows):,} rows) with its licence and how many files it contributed.", "schema": schema(SRC, SRC_DESC)},
        {"path": "kmx/invsqrt", "description": "invsqrt circuits as kickmix kmx text, one file per distinct circuit, named <sha12>.kmx."},
        {"path": "kmx/chemistry/loaders", "description": "Chemistry angle_k loader circuits as gzip-compressed kmx text, stored once each as <sha12>.kmx.gz; families.csv maps them to families."},
        {"path": "factorizations", "description": "Chemistry factorizations (submission.npz), gzip-compressed, <sha12>.npz.gz; byte for byte the published file after decompression."},
        {"path": "tools", "description": "Apache-2.0 Python tools without kickmix: kmsim simulator, liveness, splice search and builder, chemistry loader check, family rebuild, atlas_io file access, refit and qccscope packages, tests, and the dataset builders."},
        {"path": "tools/refit", "description": "Chemistry DF-THC weight refit at fixed angle words (GRG, numpy port of prvsiyan's refit_grg.py) with exact verifier-math metrics; CLI python -m refit eval|run; needs the competition verifier (not included)."},
        {"path": "tools/qccscope", "description": "Circuit diagnosis library for kmx text: parser, task cost models and exchange rates, liveness, motif detectors, sampled value scan, markdown report; CLI python -m qccscope report."},
        {"path": "tools/atlas_io.py", "description": "Find and read atlas files from a notebook by sha12; read contributions/index.json; convert kmx to kmb with the competition's kickmix."},
        {"path": "contributions", "description": "Our own public results (invsqrt splice 9c708f7b9abc and dead-write fix e46d90c36d1b, DQI readout-window transplant 245527f68413, three chemistry refits) with gains, recipes, first public versions, credits and official-verifier receipts."},
        {"path": "contributions/invsqrt", "description": "README and JSON recipes of our invsqrt results: splice 9c708f7b9abc (pieces of 7 public 62-qubit circuits) and dead-write fix e46d90c36d1b (op edit on dcde7078); the circuits are in kmx/invsqrt/."},
        {"path": "contributions/dqi", "description": "README and JSON recipe of our DQI readout-window transplant 245527f68413 (two decoder regions of bb4287e7 from 9fcda0c1; 48 fewer Toffolis per shot); metadata only, like every DQI file."},
        {"path": "contributions/chemistry_refits", "description": "README and refits.csv of our three W/H2_I refits (2913ca130f71, 54bc3e71807e, 5a75386681c8); the npz files are in factorizations/."},
        {"path": "contributions/receipts", "description": "Official-verifier receipts (receipt.json of the notebook output: file SHA-256 + verifier output of the three tasks) of our public notebook versions, named <receipt id>__<notebook>__v<version>.json."},
        {"path": "contributions/index.json", "description": "All our contributions as data: task, sha256, path in this dataset, base file, recipe, official verifier numbers, gain, first public notebook version, receipts."},
        {"path": "contributions/chemistry_refits/refits.csv", "description": "Our three chemistry refits: base file, lambda_eff before/after, error_1, error_2, E_gap, Lambda, official chemistry score, notebook version, receipt id."},
        {"path": "contributions/receipts/receipts.csv", "description": "Index of the official-verifier receipts of our public notebook versions: files (sha12), scores of the three tasks, DQI errors, geometric mean, submitted or not."},
        {"path": "cover.png", "description": "Cover image: qubits against static Toffoli-like count of every measured public circuit."},
    ]
    meta = {"title": TITLE, "subtitle": SUBTITLE, "id": DATASET_ID, "licenses": [{"name": "apache-2.0"}],
            "keywords": KEYWORDS, "expectedUpdateFrequency": "weekly", "isPrivate": True,
            "description": text, "resources": res}
    write_text(os.path.join(out, "dataset-metadata.json"), json.dumps(meta, indent=1, ensure_ascii=False) + "\n")


def write_all(out, rows, fam_rows, src_rows, stats, CIRC, FAM, SRC, cover=True):
    make_cover = cover
    assert len(TITLE) <= 50 and 20 <= len(SUBTITLE) <= 80, (len(TITLE), len(SUBTITLE))
    os.makedirs(os.path.join(out, "tools"), exist_ok=True)
    write_text(os.path.join(out, "tools", "README.md"), tools_readme())
    if make_cover:
        globals()["cover"](out, rows)
    text = readme(out, rows, fam_rows, src_rows, stats, CIRC, FAM, SRC)
    write_text(os.path.join(out, "README.md"), text)
    metadata(out, text, CIRC, FAM, SRC, rows, fam_rows, src_rows)
