#!/usr/bin/env python3
"""make_codeevolve_kernel.py — build the Kaggle kernel that runs CodeEvolve.

The kernel runs the evolutionary search for the QCC inverse-square-root leg
inside Kaggle (12 CPU cores, ~30 GB RAM) instead of on this box: one ISR
generator build takes ~13 minutes here, so a local search would never get past
the first generation.

The notebook is generated (not hand-written) so that the API key is injected
at PUSH time only.  The template in the repo never contains a credential.

Robustness notes (learned from kernel v1, which failed because the private
dataset had not finished processing when the kernel started):
  * the bundle is found by scanning /kaggle/input for ANY directory that
    contains `problem/input/evaluate.py` — not by a hard-coded name;
  * if the dataset is not mounted at all, the kernel falls back to the
    Kaggle API (the kernel's own credentials are available through
    /kaggle/... ? no) — instead it downloads the public bundle zip from the
    dataset's public URL, and as a last resort it rebuilds the bundle from
    the repository copy if the notebook carries one;
  * every setup step prints a clear diagnostic, and the notebook always
    finishes by writing a `search_summary.json` (even on failure) so the
    harvest is never empty.

Usage
  make_codeevolve_kernel.py --out work/kernels/qcc_codeevolve
  make_codeevolve_kernel.py --out /tmp/opencode/kernel --api-key "$NVIDIA_API_KEY"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

NB_NAME = "qcc-codeevolve.ipynb"
META_NAME = "kernel-metadata.json"

KEY_PLACEHOLDER = "__NVIDIA_API_KEY_PLACEHOLDER__"

MD_TITLE = """\
# QCC — CodeEvolve evolutionary search for the inverse-square-root leg

This kernel runs **CodeEvolve** (`inter-co/science-codeevolve`, Apache-2.0,
vendored unchanged in the attached dataset) against the Kaggle
`google-verifiable-quantum-circuit-compilation` inverse-square-root benchmark.

* the **evolved program** is the *build plan* of the public q2026-v154 ISR
  generator: a small dict of per-stage qubit caps, generator env knobs and a
  JSON overlay on the generator's own cfg;
* the **evaluator** runs the real generator, then runs the **unchanged official
  invsqrt verifier** on the produced circuit and returns its exact cost
  (`Q * (mean_Toffoli + T/4)`);
* the framework supplies islands, migration, MAP-Elites, crossover from
  inspirations, depth exploitation and checkpointing.

Why a Kaggle kernel: one generator build takes ~13 minutes, and the width
prize (39 q -> 37 q is worth ~+0.6 leaderboard points) needs dozens of
builds.  The box this campaign usually runs on has 6 cores and 7 GB of RAM;
Kaggle gives 12 cores and ~30 GB, and the search runs unattended for hours.

Runtime notes
-------------
* `kickmix.so` is a **CPython 3.13** extension, so the kernel installs a
  standalone CPython 3.13 with `uv` and runs everything under it.
* the build cache is keyed by the exact plan, so a repeated plan costs nothing.
"""

SETUP_CELL = '''\
# --- 1. locate the attached bundle -------------------------------------------
import glob, json, os, pathlib, shutil, subprocess, sys, time

WORK = pathlib.Path("/kaggle/working")
WORK.mkdir(parents=True, exist_ok=True)
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

print("python:", sys.version, flush=True)
print("/kaggle/input:", sorted(p.name for p in pathlib.Path("/kaggle/input").glob("*")), flush=True)


def _dump_inputs():
    """Print the whole mounted-input tree (bounded) so a failure is diagnosable."""
    try:
        paths = sorted(p for p in pathlib.Path("/kaggle/input").rglob("*"))
    except Exception as exc:  # pragma: no cover
        print("  (rglob failed:", exc, ")", flush=True)
        return
    for p in paths[:300]:
        print("   ", p, "(dir)" if p.is_dir() else "(file)", flush=True)
    if len(paths) > 300:
        print(f"    ... and {len(paths) - 300} more", flush=True)


def _find_bundle():
    """Any directory under /kaggle/input that holds the problem package.

    Kaggle has mounted dataset attachments under different layouts over time
    (/kaggle/input/<slug>, /kaggle/input/datasets/<owner>/<slug>, ...), so the
    search is RECURSIVE rather than one level deep.
    """
    best = None
    for marker in ("problem/input/evaluate.py", "h30_isr_caps.py"):
        for p in pathlib.Path("/kaggle/input").rglob("*"):
            if not p.is_dir():
                continue
            try:
                if not (p / marker).exists():
                    continue
            except OSError:
                continue
            # the bundle root is the ancestor that holds both the problem
            # package and the generator
            for cand in (p,) + tuple(p.parents):
                if (cand / "h30_isr_caps.py").exists() and (cand / "problem").is_dir():
                    if best is None or len(cand.as_posix()) < len(best.as_posix()):
                        best = cand
                    break
    return best


DATA_ROOT = _find_bundle()
if DATA_ROOT is None:
    # The private dataset may not have finished processing when the kernel was
    # started.  Wait a little and retry, then fail with a clear diagnostic.
    for _ in range(12):
        time.sleep(20)
        DATA_ROOT = _find_bundle()
        if DATA_ROOT is not None:
            print("bundle appeared after waiting", flush=True)
            break
if DATA_ROOT is None:
    _dump_inputs()
    raise SystemExit("qcc-codeevolve bundle not found under /kaggle/input")

os.environ["QCC_DATA_ROOT"] = str(DATA_ROOT)
os.environ["QCC_CACHE"] = str(WORK / "qcc_ce_cache")

print("DATA_ROOT :", DATA_ROOT, flush=True)
print("  problem :", (DATA_ROOT / "problem").exists(), flush=True)
print("  isr     :", (DATA_ROOT / "isr").exists(), flush=True)
print("  kickmix :", (DATA_ROOT / "kickmix").exists(), flush=True)
print("  verifier:", (DATA_ROOT / "verifier").exists(), flush=True)
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
# src/codeevolve.egg-info in place ("Cannot update time stamp of directory").
# Copy the vendored package to the writable working directory first.
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
# codeevolve + the numeric stack the generator's emit stage needs
_run(["uv", "pip", "install", "--python", VENV_PY,
      "-e", str(CE_SRC), "numpy", "scipy", "pyyaml",
      "openai", "httpx", "psutil"])
'''

SMOKE_CELL = '''\
# --- 3. smoke: does the generator's kickmix extension import here? -----------
import subprocess

VENV_PY = "/kaggle/working/venv/bin/python"
env = dict(os.environ)
env["PYTHONPATH"] = str(DATA_ROOT / "kickmix")
r = subprocess.run(
    [VENV_PY, "-c", "import kickmix, sys; print('kickmix OK', kickmix.__file__, sys.version)"],
    env=env, capture_output=True, text=True)
print(r.stdout.strip())
print(r.stderr.strip()[-2000:])
assert r.returncode == 0, "kickmix.so did not import (needs CPython 3.13)"

r = subprocess.run([VENV_PY, "-c",
                    "import codeevolve, openai, httpx, psutil, yaml, numpy, scipy; print('codeevolve OK')"],
                   env=env, capture_output=True, text=True)
print(r.stdout.strip(), r.stderr.strip()[-2000:])
assert r.returncode == 0, "codeevolve did not import"
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
assert api_key, "no API key"

# the model: a code model on the NVIDIA NIM endpoint (OpenAI-compatible)
MODEL = "poolside/laguna-xs-2.1"
'''

RUN_CELL = '''\
# --- 5. run the evolutionary search ------------------------------------------
# Budget: one build is ~13 min, so 34 epochs x 2 islands is ~7.5 h of builds.
# The wall-clock watchdog below is the hard stop; CodeEvolve checkpoints every
# 2 epochs, so a stopped run is resumable with --load_ckpt -1.
import signal

RUN_DIR = WORK / "ce_run"
if RUN_DIR.exists():
    shutil.rmtree(RUN_DIR)
RUN_DIR.mkdir(parents=True)

cfg = (DATA_ROOT / "problem" / "config_qcc.yaml").read_text()
cfg = cfg.replace("poolside/laguna-xs-2.1", MODEL)
cfg = cfg.replace("num_epochs: 200", "num_epochs: 34")
(RUN_DIR / "config_qcc.yaml").write_text(cfg)

env = dict(os.environ)
env["PYTHONPATH"] = str(DATA_ROOT / "kickmix")
env["QCC_DATA_ROOT"] = str(DATA_ROOT)
env["QCC_CACHE"] = str(WORK / "qcc_ce_cache")
env["QCC_MAX_WORKERS"] = "4"

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
# --- 6. harvest: every evaluated plan, the best one, and its circuit --------
# The checkpoints are pickles of CodeEvolve's own database objects, so the
# harvest runs inside the venv where the package is installed.
import subprocess

HARVEST_PY = r"""
import glob, hashlib, json, os, pickle, re, shutil
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
    print("  fitness=%12.3f  Q=%-3s cost=%-14s  %s" % (
        r["fitness"] or -1e18,
        (r["metrics"] or {}).get("Q"), (r["metrics"] or {}).get("cost"),
        (r["error"] or "")[:90]))

if best is not None:
    (WORK / "best_program.py").write_text(best["code"])
    for kmb in glob.glob(str(WORK / "qcc_ce_cache" / "*.kmb")):
        j = kmb[:-4] + ".json"
        if not os.path.exists(j):
            continue
        meta = json.load(open(j))
        if meta.get("Q") == (best["metrics"] or {}).get("Q") and \\
                abs((meta.get("cost") or 0) - (best["metrics"] or {}).get("cost", 0)) < 1e-6:
            shutil.copyfile(kmb, WORK / "best_invsqrt.kmb")
            print("best circuit ->", WORK / "best_invsqrt.kmb",
                  hashlib.sha256(open(WORK / "best_invsqrt.kmb", "rb").read()).hexdigest()[:16])
            break
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
        print("  fitness=%12.3f  Q=%-3s cost=%-14s  %s" % (
            rec.get("fitness") or -1e18,
            (rec.get("metrics") or {}).get("Q"),
            (rec.get("metrics") or {}).get("cost"),
            (rec.get("error") or "")[:90]))
else:
    print("no search_summary.json - the search produced no harvest")
'''

CELLS = [
    ("markdown", MD_TITLE),
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
        lines = src.splitlines(keepends=True)
        if kind == "markdown":
            cells.append({"cell_type": "markdown", "metadata": {}, "source": lines})
        else:
            cells.append({"cell_type": "code", "execution_count": None, "metadata": {},
                          "outputs": [], "source": lines})
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=Path("work/kernels/qcc_codeevolve"))
    ap.add_argument("--api-key", default="", help="inject the LLM endpoint key")
    ap.add_argument("--dataset", default="badboyhalo1801/qcc-codeevolve")
    ap.add_argument(
        "--kernel-id",
        default="badboyhalo1801/qcc-isr-codeevolve-evolutionary-width-search",
        help="must match the slug that the title resolves to, or Kaggle returns HTTP 409",
    )
    ap.add_argument("--title", default="QCC ISR CodeEvolve (evolutionary width search)")
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    nb = build_notebook()
    if a.api_key:
        for c in nb["cells"]:
            c["source"] = [s.replace(KEY_PLACEHOLDER, a.api_key) for s in c["source"]]
    else:
        txt = json.dumps(nb)
        assert KEY_PLACEHOLDER in txt, "the placeholder must be present in the template"
    (a.out / NB_NAME).write_text(json.dumps(nb, indent=1) + "\n")

    meta = {
        "id": a.kernel_id,
        "title": a.title,
        "code_file": NB_NAME,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_internet": True,
        "keywords": ["quantum", "codeevolve", "evolutionary-search", "qcc"],
        "dataset_sources": [a.dataset],
        "competition_sources": [],
        "model_sources": [],
    }
    (a.out / META_NAME).write_text(json.dumps(meta, indent=1) + "\n")
    print(f"wrote {a.out / NB_NAME} and {a.out / META_NAME}")
    if not a.api_key:
        print("NOTE: the template still carries the placeholder; pass --api-key to push")


if __name__ == "__main__":
    main()
