#!/usr/bin/env python3
"""build_dqi_build_kernel.py — build the `dqi-build` kernel: search for more removable Toffolis.

Grant Prater's public tools (vqcc_ir.py, vqcc_measure_out.py, vqcc_pair_window.py,
vqcc_bitsim.py, vqcc_stream_diff.py) implement a *measured uncomputation* pass:
when a product is computed twice and a wire is clean over the span, one Toffoli
can be held on that wire instead of being computed twice.  His README leaves
open: "14 more Toffoli-likes in each closing (686 in all) wait for a second
helper wire that is idle between the two computations".

This kernel runs that pass on the best public DQI (575b043f) with every flag
combination the tools offer, rewrites what the pass can prove, and measures each
candidate with the competition's own verifier (official grade, 102,400 shots).
Kernel pushes cost no submission slot, so this is a free search.
"""
import ast
import json
import pathlib

ROOT = pathlib.Path('/tmp/opencode/kernel_build')
ROOT.mkdir(parents=True, exist_ok=True)

CELL = r'''# dqi-build — search the public DQI line for more removable Toffolis (free kernel).
#
# Measured uncomputation: a product computed twice, with a wire clean over the span,
# can be held on that wire: one Toffoli fewer.  Grant Prater's tools are public
# (dataset grantprater/vqcc-dqi-61c8348d-merged-closings).  His README leaves open
# "14 more Toffoli-likes in each closing (686 in all) wait for a second helper wire
# that is idle between the two computations".
#
# This kernel: lays the tools out as their package, runs the finder with every flag
# combination, applies what the pass proves exactly, and measures each candidate
# with the competition's own verifier at official-grade shots.

import io, json, os, shutil, subprocess, sys, time, lzma, hashlib
from pathlib import Path

T0 = time.time()
OUT = Path("/kaggle/working"); OUT.mkdir(parents=True, exist_ok=True)
INPUT = Path("/kaggle/input")

DATA = next(INPUT.rglob('vqcc_measure_out.py')).parent
COMP = next(INPUT.rglob('verify_submission_dqi.py')).parents[2]
KICKMIX, VERIFIERS = COMP / 'kickmix', COMP / 'verifiers'
print("DATA:", DATA, "| COMP:", COMP, flush=True)

# --- the tools, laid out as the package they were written in --------------------
TOOLS = OUT / 'tools'
for sub in ('qc/passes', 'analysis/ir', 'analysis/dqi'):
    (TOOLS / sub).mkdir(parents=True, exist_ok=True)
for p in ('qc/__init__.py', 'qc/passes/__init__.py', 'analysis/__init__.py',
          'analysis/ir/__init__.py', 'analysis/dqi/__init__.py'):
    (TOOLS / p).write_text('')
shutil.copy(DATA / 'vqcc_ir.py', TOOLS / 'qc/ir.py')
shutil.copy(DATA / 'vqcc_bitsim.py', TOOLS / 'qc/bitsim.py')
shutil.copy(DATA / 'vqcc_measure_out.py', TOOLS / 'qc/passes/measure_out.py')
shutil.copy(DATA / 'vqcc_stream_diff.py', TOOLS / 'analysis/ir/stream_diff.py')
shutil.copy(DATA / 'vqcc_pair_window.py', TOOLS / 'analysis/dqi/pair_window.py')
print("tools laid out", flush=True)

# --- the base file: Grant Prater's later file (best public DQI by mean Toffolis)
src = next((p for p in DATA.glob('dqi_575b043f.kmb.xz')), None)
if src is None:
    src = next((p for p in INPUT.rglob('dqi_575b043f.kmb.xz')), None)
BASE = OUT / 'base_575b043f.kmb'
if src.name.endswith('.xz'):
    BASE.write_bytes(lzma.decompress(src.read_bytes()))
else:
    BASE.write_bytes(src.read_bytes())
print("base:", BASE, BASE.stat().st_size, "B", flush=True)

PY = sys.executable
ENV = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(TOOLS), str(KICKMIX)])}


def run(cmd, tail=4000, timeout=5400):
    t = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, env=ENV, timeout=timeout)
        out = (r.stdout or '') + '\n' + (r.stderr or '')
    except subprocess.TimeoutExpired:
        out = 'TIMEOUT'
    print(f"$ {' '.join(str(c) for c in cmd)}\n{out[-tail:]}\n[dt {time.time()-t:.0f}s]", flush=True)
    return out


MO = [PY, '-m', 'qc.passes.measure_out']

# --- 1. the finder, with every flag combination ------------------------------
report = {"base": str(BASE), "base_bytes": BASE.stat().st_size, "counts": {}, "candidates": []}
combos = [
    ("retain", ["--retain"]),
    ("symclean", ["--retain", "--symclean"]),
    ("condsym", ["--retain", "--symclean", "--condsym"]),
    ("lin", ["--retain", "--symclean", "--condsym", "--lin"]),
    ("extra1", ["--retain", "--symclean", "--condsym", "--lin", "--extra", "1"]),
]
for name, flags in combos:
    out = run(MO + ['count', str(BASE)] + flags, tail=2500)
    report["counts"][name] = out[-2500:]
    (OUT / 'DQI_BUILD.json').write_text(json.dumps(report, indent=1))

# --- 2. apply what the pass proves, and measure it ---------------------------
VERIFY = VERIFIERS / 'dqi' / 'verify_submission_dqi.py'


def verify(path, shots=102400):
    env = {**ENV, 'PYTHONPATH': os.pathsep.join([str(TOOLS), str(KICKMIX), str(VERIFIERS),
                                                 str(VERIFIERS / 'dqi')])}
    t = time.time()
    try:
        r = subprocess.run([PY, str(VERIFY), str(path), '--num-shots', str(shots)],
                           capture_output=True, text=True, env=env, timeout=7200)
        out = (r.stdout or '') + '\n' + (r.stderr or '')
    except subprocess.TimeoutExpired:
        out = 'TIMEOUT'
    i, j = out.find('{'), out.rfind('}')
    res = {}
    if 0 <= i < j:
        try:
            res = json.loads(out[i:j + 1])
        except Exception:
            pass
    rec = {"status": res.get("status"), "score": res.get("score"),
           "value_errors": res.get("value_errors"), "phase_errors": res.get("phase_errors"),
           "verified_shots": res.get("verified_shots"), "num_ops": res.get("num_ops"),
           "max_toffoli_count": res.get("max_toffoli_count"),
           "toffoli_count": res.get("toffoli_count"),
           "repetition_factor": res.get("repetition_factor"),
           "num_qubits": res.get("num_qubits"), "dt": round(time.time() - t, 1),
           "tail": out[-600:]}
    print(f"[verify {Path(path).name}] status={rec['status']} score={rec['score']} "
          f"verr={rec['value_errors']} perr={rec['phase_errors']} "
          f"toffoli_mean={rec['toffoli_count']} rep={rec['repetition_factor']}", flush=True)
    return rec


apply_combos = [
    ("cand_retain", ["--retain"]),
    ("cand_symclean", ["--retain", "--symclean"]),
    ("cand_condsym", ["--retain", "--symclean", "--condsym"]),
    ("cand_lin", ["--retain", "--symclean", "--condsym", "--lin"]),
]
for name, flags in apply_combos:
    dst = OUT / f'{name}.kmb'
    out = run(MO + [str(BASE), str(dst)] + flags, tail=2500)
    if not dst.exists():
        print(f"{name}: no output file", flush=True)
        continue
    sha = hashlib.sha256(dst.read_bytes()).hexdigest()
    rec = {"name": name, "sha256": sha, "bytes": dst.stat().st_size, "flags": flags,
           "build_tail": out[-1200:]}
    rec.update(verify(dst))
    report["candidates"].append(rec)
    (OUT / 'DQI_BUILD.json').write_text(json.dumps(report, indent=1))

# --- 3. summary ---------------------------------------------------------------
REF_DQI = 24439463583672.93
REF_INV = 2076774.233715282
REF_DFT = 3355599588.3155375
print("\n=== DQI BUILD SUMMARY ===", flush=True)
for c in report["candidates"]:
    sc = c.get("score")
    gm = ((REF_INV / 74797.36535717871) * (REF_DQI / sc) *
          (REF_DFT / 294643137.7335714)) ** (1 / 3) if sc else None
    print(f"  {c['name']:<16} sha={c['sha256'][:12]} status={c['status']} score={sc} "
          f"verr={c.get('value_errors')} T_mean={c.get('toffoli_count')} GM={gm}", flush=True)
report["done"] = True
(OUT / 'DQI_BUILD.json').write_text(json.dumps(report, indent=1))
print("=== done (elapsed %.0fs) ===" % (time.time() - T0), flush=True)
'''

nb = {
    "cells": [{
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": CELL.splitlines(keepends=True),
    }],
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12.0"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

json.dumps(nb)
ast.parse(CELL)
print("dqi-build notebook: JSON OK, ast.parse OK, cell chars", len(CELL))
(ROOT / 'dqi-build.ipynb').write_text(json.dumps(nb, indent=1) + "\n")

meta = {
    "id": "badboyhalo1801/dqi-build",
    "title": "dqi-build",
    "code_file": "dqi-build.ipynb",
    "language": "python",
    "kernel_type": "notebook",
    "is_private": True,
    "enable_gpu": False,
    "enable_tpu": False,
    "enable_internet": True,
    "keywords": [],
    "dataset_sources": ["grantprater/vqcc-dqi-61c8348d-merged-closings"],
    "kernel_sources": [],
    "competition_sources": ["google-verifiable-quantum-circuit-compilation"],
    "model_sources": [],
}
(ROOT / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + "\n")
print("wrote", ROOT)
