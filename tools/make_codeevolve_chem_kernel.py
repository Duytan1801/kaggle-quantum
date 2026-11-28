#!/usr/bin/env python3
"""make_codeevolve_chem_kernel.py — build the Kaggle kernel that runs the
CHEMISTRY CodeEvolve search.

WHAT IT RUNS
------------
The evolved program is a REWRITE RECIPE for one of the 15 chemistry loaders
(`batch` + an edit list).  The evaluator is EXACT: it symbolically simulates
the rewritten circuit against the original over all 1,219 valid addresses,
tracking every qubit's value AND phase, and rejects anything that changes the
circuit.  The objective is the loader's CCX count (fitness = -CCX, because
CodeEvolve maximises).

One candidate costs ~1 second, so the search runs hundreds of candidates per
hour on Kaggle (12 CPU cores) instead of the ~13 minutes per candidate that
the invsqrt generator lane needed.

The bundle (dataset `badboyhalo1801/qcc-chem-codeevolve`) carries:
  problem/input/evaluate.py, problem/input/src/init_program.py,
  problem/config_qcc.yaml, tree/dfthcsos/* (the v153 loader bytes),
  tools/{chem_extract,chem_plan}.py, kickmix/kickmix.so, codeevolve/.

The API key is injected at PUSH time only; the notebook in the repository
never contains a credential.  A Kaggle secret named NVIDIA_API_KEY takes
precedence.

Usage:
  make_codeevolve_chem_kernel.py --out /tmp/opencode/kernel_chem_ce
"""
from __future__ import annotations

import argparse
import ast
import json
import pathlib

KEY_PLACEHOLDER = "__NVIDIA_API_KEY_PLACEHOLDER__"
DATASET = "badboyhalo1801/qcc-chem-codeevolve"

MD = """\
# QCC — CodeEvolve evolutionary search for the CHEMISTRY loaders

This kernel runs **CodeEvolve** (`inter-co/science-codeevolve`, Apache-2.0,
vendored unchanged in the attached dataset) against the Kaggle
`google-verifiable-quantum-circuit-compilation` **chemistry (dfthcsos)** leg.

* the **evolved program** is a rewrite recipe for one loader: which loader
  (`batch`) and a list of edits (`drop` / `cx` / `insert_cx` / `insert_ccx` /
  `swap` / `move`);
* the **evaluator** is EXACT — it simulates the rewritten circuit symbolically
  against the original over all 1,219 valid addresses, tracking every qubit's
  value and phase, so a rewrite that changes the circuit is rejected;
* the **objective** is the loader's CCX count (one loader Toffoli is worth
  ~0.00169 leaderboard points; the five group-start loaders k = 0,1,5,7,11
  still cost 240-245 CCX each and are the target);
* the framework supplies islands, migration, MAP-Elites over (batch x CCX),
  crossover from inspirations, depth exploitation and checkpointing.

Why Kaggle: one candidate costs ~1 s, so a wide search is cheap, but this box
has 6 cores and 7 GB of RAM and the search should run unattended for hours.
"""

SETUP_CELL = '''\
# --- 1. rebuild the bundle from the flat dataset ----------------------------
import glob, hashlib, json, os, pathlib, shutil, sys, time

WORK = pathlib.Path("/kaggle/working")
WORK.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
print("python:", sys.version, flush=True)


def _find_bundle():
    for man in pathlib.Path("/kaggle/input").rglob("BUNDLE_MANIFEST.json"):
        return man.parent, man
    return None, None


src_dir, manifest_path = _find_bundle()
if src_dir is None:
    for _ in range(12):
        time.sleep(20)
        src_dir, manifest_path = _find_bundle()
        if src_dir is not None:
            print("bundle appeared after waiting", flush=True)
            break
if src_dir is None:
    print("inputs:", sorted(p.name for p in pathlib.Path("/kaggle/input").glob("*")))
    raise SystemExit("qcc-chem-codeevolve bundle not found under /kaggle/input")

BUNDLE = WORK / "bundle"
if BUNDLE.exists():
    shutil.rmtree(BUNDLE)
BUNDLE.mkdir(parents=True)

manifest = json.loads(manifest_path.read_text())
bad = 0
for item in manifest["files"]:
    flat = src_dir / item["flat"]
    if not flat.is_file():
        print("MISSING", item["flat"])
        bad += 1
        continue
    dst = BUNDLE / item["path"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(flat, dst)
    h = hashlib.sha256(dst.read_bytes()).hexdigest()
    if h != item["sha256"]:
        print("SHA MISMATCH", item["path"])
        bad += 1
print("bundle files:", len(manifest["files"]), "bad:", bad, flush=True)
if bad:
    raise SystemExit("bundle reconstruction failed")

DATA_ROOT = BUNDLE
os.environ["QCC_DATA_ROOT"] = str(DATA_ROOT)
os.environ["QCC_CACHE"] = str(WORK / "qcc_ce_cache")
print("DATA_ROOT:", DATA_ROOT, flush=True)
print("  problem :", (DATA_ROOT / "problem" / "input" / "evaluate.py").exists())
print("  tree    :", len(list((DATA_ROOT / "tree" / "dfthcsos").glob("angle_k_*.kmb"))))
print("  kickmix :", (DATA_ROOT / "kickmix" / "kickmix.so").exists())
'''

PY313_CELL = '''\
# --- 2. a CPython 3.13 (required by BOTH codeevolve and kickmix.so) ---------
import subprocess as _sp

VENV = "/kaggle/working/venv"
VENV_PY = VENV + "/bin/python"


def _run(cmd, **kw):
    print("+", " ".join(cmd), flush=True)
    p = _sp.run(cmd, capture_output=True, text=True, **kw)
    print(p.stdout[-3000:])
    if p.returncode != 0:
        print(p.stderr[-4000:])
        raise SystemExit("command failed: %s" % cmd[:3])
    return p


if _sp.run(["which", "uv"], capture_output=True).returncode != 0:
    _run([sys.executable, "-m", "pip", "install", "-q", "uv"])
_run(["uv", "python", "install", "3.13"])
if os.path.exists(VENV):
    shutil.rmtree(VENV)
_run(["uv", "venv", "--python", "3.13", VENV])
# The dataset mount is READ-ONLY, so setuptools cannot refresh
# src/codeevolve.egg-info in place; copy the vendored package out first.
CE_SRC = WORK / "codeevolve_src"
if CE_SRC.exists():
    shutil.rmtree(CE_SRC)
shutil.copytree(DATA_ROOT / "codeevolve", CE_SRC)
os.chmod(CE_SRC, 0o755)
for p in CE_SRC.rglob("*"):
    try:
        os.chmod(p, 0o755 if p.is_dir() else 0o644)
    except OSError:
        pass
_run(["uv", "pip", "install", "--python", VENV_PY,
      "-e", str(CE_SRC), "numpy", "scipy", "pyyaml",
      "openai", "httpx", "psutil"])
'''

SMOKE_CELL = '''\
# --- 3. smoke: kickmix + the exact evaluator on the seed program ------------
import subprocess

VENV_PY = "/kaggle/working/venv/bin/python"
env = dict(os.environ)
env["PYTHONPATH"] = str(DATA_ROOT / "kickmix")
r = subprocess.run(
    [VENV_PY, "-c", "import kickmix, sys; print('kickmix OK', sys.version)"],
    env=env, capture_output=True, text=True)
print(r.stdout.strip())
print(r.stderr.strip()[-2000:])
assert r.returncode == 0, "kickmix.so did not import (needs CPython 3.13)"

r = subprocess.run([VENV_PY, "-c",
                    "import codeevolve, openai, httpx, psutil, yaml, numpy, scipy; print('codeevolve OK')"],
                   env=env, capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip()[-2000:])
assert r.returncode == 0, "codeevolve did not import"

# the baseline: the seed program must reproduce the shipped loader exactly
seed = WORK / "seed_program.py"
seed.write_text((DATA_ROOT / "problem" / "input" / "src" / "init_program.py").read_text())
r = subprocess.run([VENV_PY, str(DATA_ROOT / "problem" / "input" / "evaluate.py"),
                    str(seed), str(WORK / "seed_metrics.json")],
                   env=env, capture_output=True, text=True, timeout=1800)
print(r.stdout[-2000:])
print(r.stderr[-2000:])
assert (WORK / "seed_metrics.json").exists(), "the evaluator produced no metrics"
m = json.loads((WORK / "seed_metrics.json").read_text())
print("seed metrics:", {k: m.get(k) for k in ("fitness", "ccx", "ccx_baseline", "exact_ok", "batch")})
assert m.get("exact_ok") == 1, "the baseline loader does not reproduce exactly"
'''

KEY_CELL = '''\
# --- 4. the OpenAI-compatible endpoint for the mutation LLM ------------------
# The key is injected when the kernel is pushed; it is never stored in the
# repository.  A Kaggle secret named NVIDIA_API_KEY takes precedence.
api_key = ""
try:
    from kaggle_secrets import UserSecretClient
    api_key = UserSecretClient().get_secret("NVIDIA_API_KEY")
    print("using the Kaggle secret")
except Exception as exc:
    print("no Kaggle secret (%s)" % exc)
if not api_key:
    api_key = "__NVIDIA_API_KEY_PLACEHOLDER__"
    print("using the key embedded at push time")

os.environ["API_BASE"] = "https://integrate.api.nvidia.com/v1"
os.environ["API_KEY"] = api_key
assert api_key and "PLACEHOLDER" not in api_key, "no API key"

MODEL = "poolside/laguna-xs-2.1"
'''

RUN_CELL = '''\
# --- 5. run the evolutionary search ------------------------------------------
# Budget: a candidate costs ~1 s, so the wall-clock budget (not the epoch
# count) is the binding constraint.  CodeEvolve checkpoints every 5 epochs,
# so a stopped run is resumable with --load_ckpt -1.
import signal

RUN_DIR = WORK / "ce_run"
if RUN_DIR.exists():
    shutil.rmtree(RUN_DIR)
RUN_DIR.mkdir(parents=True)

cfg = (DATA_ROOT / "problem" / "config_qcc.yaml").read_text()
cfg = cfg.replace("poolside/laguna-xs-2.1", MODEL)
(RUN_DIR / "config_qcc.yaml").write_text(cfg)

env = dict(os.environ)
env["PYTHONPATH"] = str(DATA_ROOT / "kickmix")
env["QCC_DATA_ROOT"] = str(DATA_ROOT)
env["QCC_CACHE"] = str(WORK / "qcc_ce_cache")

cmd = [VENV_PY, "-m", "codeevolve.cli",
       "--inpt_dir", str(DATA_ROOT / "problem" / "input"),
       "--cfg_path", str(RUN_DIR / "config_qcc.yaml"),
       "--out_dir", str(RUN_DIR),
       "--load_ckpt", "0", "--y"]
print(" ".join(cmd), flush=True)

BUDGET_S = 8 * 3600
t0 = time.time()
proc = subprocess.Popen(cmd, env=env, cwd=str(WORK),
                        stdout=open(WORK / "codeevolve.log", "w"),
                        stderr=subprocess.STDOUT, start_new_session=True)
try:
    rc = proc.wait(timeout=BUDGET_S)
except subprocess.TimeoutExpired:
    print("wall-clock budget reached; stopping the islands", flush=True)
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except Exception:
        proc.terminate()
    try:
        rc = proc.wait(timeout=600)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        rc = proc.wait()
print("codeevolve exited rc=%s after %.1f min" % (rc, (time.time() - t0) / 60), flush=True)
print(open(WORK / "codeevolve.log").read()[-6000:])
'''

HARVEST_CELL = '''\
# --- 6. harvest: every evaluated recipe, the best one ------------------------
import subprocess

HARVEST_PY = r"""
import glob, json, os, pickle, re, shutil
from pathlib import Path

WORK = Path("/kaggle/working")
RUN_DIR = WORK / "ce_run"
summary = {"programs": [], "best": None}

ckpts = sorted(glob.glob(str(RUN_DIR / "island_*" / "ckpt" / "ckpt_*.pkl")),
               key=lambda p: int(re.findall(r"ckpt_(\\d+)\\.pkl", p)[-1]))
print("checkpoints:", [c.split("/")[-1] for c in ckpts])

best = None
for c in ckpts:
    try:
        with open(c, "rb") as fh:
            data = pickle.load(fh)
    except Exception as exc:
        print("skip", c, exc)
        continue
    sol_db = data.get("sol_db")
    if sol_db is None:
        continue
    for pid, prog in sol_db.programs.items():
        rec = {"id": pid, "island": c.split("/")[-3], "fitness": prog.fitness,
               "metrics": prog.eval_metrics, "error": (prog.error or "")[-400:],
               "code": prog.code}
        summary["programs"].append(rec)
        if best is None or (prog.fitness or -1e18) > (best["fitness"] or -1e18):
            best = rec
summary["best"] = best
summary["programs"].sort(key=lambda r: -(r["fitness"] or -1e18))
(WORK / "search_summary.json").write_text(json.dumps(summary, indent=1))
print("evaluated programs:", len(summary["programs"]))
for r in summary["programs"][:10]:
    print("  fitness=%12.3f  batch=%-3s ccx=%-4s saved=%-3s  %s" % (
        r["fitness"] or -1e18,
        (r["metrics"] or {}).get("batch"), (r["metrics"] or {}).get("ccx"),
        (r["metrics"] or {}).get("saved"), (r["error"] or "")[:90]))

if best is not None:
    (WORK / "best_program.py").write_text(best["code"])
    m = best.get("metrics") or {}
    (WORK / "best_recipe.json").write_text(json.dumps(
        {"fitness": best.get("fitness"), "metrics": m, "code": best.get("code")}, indent=1))
    print("best ->", WORK / "best_program.py")
print("summary ->", WORK / "search_summary.json")
"""

(WORK / "harvest.py").write_text(HARVEST_PY)
r = subprocess.run([VENV_PY, str(WORK / "harvest.py")],
                   capture_output=True, text=True, timeout=1800)
print(r.stdout[-8000:])
print(r.stderr[-4000:])
print("harvest rc =", r.returncode)
if (WORK / "search_summary.json").exists():
    summary = json.loads((WORK / "search_summary.json").read_text())
    print("evaluated programs:", len(summary.get("programs", [])))
    for rec in summary.get("programs", [])[:10]:
        print("  fitness=%12.3f  batch=%-3s ccx=%-4s saved=%-3s  %s" % (
            rec.get("fitness") or -1e18,
            (rec.get("metrics") or {}).get("batch"),
            (rec.get("metrics") or {}).get("ccx"),
            (rec.get("metrics") or {}).get("saved"),
            (rec.get("error") or "")[:90]))
else:
    print("no search_summary.json - the search produced no harvest")
'''

CELLS = [
    ("markdown", MD),
    ("code", SETUP_CELL),
    ("code", PY313_CELL),
    ("code", SMOKE_CELL),
    ("code", KEY_CELL),
    ("code", RUN_CELL),
    ("code", HARVEST_CELL),
]


def build_notebook() -> dict:
    cells = []
    for kind, src in CELLS:
        if kind == "code":
            ast.parse(src)          # pre-push gate: every code cell must parse
        cells.append({"cell_type": kind, "metadata": {},
                      "outputs": [], "execution_count": None,
                      "source": src.splitlines(keepends=True)})
    return {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python",
                                    "name": "python3"},
                     "language_info": {"name": "python", "version": "3.13.0"}},
        "nbformat": 4, "nbformat_minor": 5,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--api-key", default="")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    nb = build_notebook()
    (a.out / "qcc-chem-codeevolve.ipynb").write_text(json.dumps(nb, indent=1))
    meta = {
        "id": "badboyhalo1801/qcc-chem-codeevolve",
        "title": "QCC Chemistry CodeEvolve (exact loader rewrite search)",
        "code_file": "qcc-chem-codeevolve.ipynb",
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": True,
        "keywords": [],
        "dataset_sources": [DATASET],
        "competition_sources": ["google-verifiable-quantum-circuit-compilation"],
        "kernel_sources": [],
    }
    (a.out / "kernel-metadata.json").write_text(json.dumps(meta, indent=1))
    if a.api_key:
        text = (a.out / "qcc-chem-codeevolve.ipynb").read_text()
        (a.out / "qcc-chem-codeevolve.ipynb").write_text(
            text.replace(KEY_PLACEHOLDER, a.api_key))
        print("API key injected at push time (not stored in the repo)")
    else:
        text = (a.out / "qcc-chem-codeevolve.ipynb").read_text()
        if KEY_PLACEHOLDER not in text:
            raise SystemExit("the key placeholder is missing")
        print("no --api-key given: the kernel expects the Kaggle secret "
              "NVIDIA_API_KEY (the placeholder will abort the run)")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
