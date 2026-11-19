#!/usr/bin/env python3
"""Build one or more invsqrt generator variants and score their emitted reports.

This is the H6 evaluator's reproducible runner.  It copies Syed's pinned source
into a disposable tree, applies a declarative patch chain, emits with
`tools/build_variant.py`, and computes the objective from the emitted exact
native expectation.  It intentionally stops at EMITTED status: a variant is
only VERIFIED after the native exact proof and official verifier pass.

Config JSON fields:
  name          unique variant name
  Q             builder maximum width
  patches       ordered [{"src": "...", "dst": "patch_name.py"}] or {"dst": ...}
  env           environment overrides for the build
  post          optional list of postpass relative files (not yet supported)

Example:
  work/tools/evo_build.py --config work/evo/configs/v001.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "work/invsqrt/syed_src"
ENGINE = ROOT / "work/toolchain/kickmix"
VERIFIERS = ROOT / "work/toolchain/verifiers"
PY = ROOT / "work/toolchain/venv/bin/python"


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cfg(path: pathlib.Path) -> dict:
    cfg = json.loads(path.read_text())
    for key in ("name", "Q", "patches"):
        if key not in cfg:
            raise ValueError(f"missing config field: {key}")
    return cfg


def prepare_tree(cfg: dict, work: pathlib.Path) -> pathlib.Path:
    tree = work / "tree"
    shutil.copytree(SOURCE / "src", tree)
    for item in tree.rglob("*"):
        if item.is_file():
            item.chmod(0o664)
    # Relocate the same @FG_ROOT@ token used by Syed's build.sh.  The token is
    # valid in Python/shell sources; reject it in data files.  Patches are
    # copied after this pass, so relocate them too.
    def relocate(path: pathlib.Path) -> None:
        if not path.is_file() or path.suffix not in (".py", ".sh"):
            return
        data = path.read_bytes()
        if b"@FG_ROOT@" in data:
            path.write_bytes(data.replace(b"@FG_ROOT@", str(tree).encode()))

    for path in tree.rglob("*"):
        relocate(path)
    patch_dir = tree / "patches"
    patch_dir.mkdir(exist_ok=True)
    args = []
    for i, p in enumerate(cfg["patches"]):
        dst = p.get("dst", f"variant_{i:02d}.py")
        src = pathlib.Path(p["src"])
        if not src.is_absolute():
            src = ROOT / src
        target = patch_dir / dst
        shutil.copyfile(src, target)
        relocate(target)          # patch modules carry @FG_ROOT@ too
        args.extend(["--patch", str(target)])
    order = patch_dir / "EVO_PATCH_ORDER.txt"
    order.write_text("\n".join(str(x) for x in args[1::2]) + "\n")
    # Non-patch support files a variant needs next to its patch module
    # (certificates, plans, helper modules).  They are inert data: they are
    # copied into the tree, never passed to build_variant as a patch.
    for f in cfg.get("extra_files", []):
        src = pathlib.Path(f["src"])
        if not src.is_absolute():
            src = ROOT / src
        sub = f.get("dir", "patches")
        dest_dir = tree / sub
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest_dir / f.get("dst", src.name))
    # Host files the pinned sources expect inside the tree (Syed's build.sh
    # copies them from ENGINE_DIR / VERIFIERS_DIR into work/c10/narrow/base/
    # official): the kickmix engine extension and the official invsqrt verifier.
    off = tree / "work/c10/narrow/base/official"
    (off / "kickmix").mkdir(parents=True, exist_ok=True)
    (off / "verifier_invsqrt").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ENGINE / "kickmix.so", off / "kickmix/kickmix.so")
    ver_dir = VERIFIERS / "invsqrt"
    if ver_dir.is_dir():
        for f in ("__init__.py", "nr_reference_circuit.py", "verify_submission_invsqrt.py"):
            if (ver_dir / f).exists():
                shutil.copyfile(ver_dir / f, off / "verifier_invsqrt" / f)
    return tree


def run_build(cfg: dict, work: pathlib.Path) -> dict:
    tree = prepare_tree(cfg, work)
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in cfg.get("env", {}).items()})
    env["PY"] = str(PY)
    out = work / "build"
    cmd = [
        str(PY), str(tree / "tools/macrun.py"), str(tree / "tools/build_variant.py"),
        "--out", str(out), "--name", cfg["name"], "--Q", str(cfg["Q"]),
    ]
    for p in cfg["patches"]:
        # Files are copied into the disposable tree by prepare_tree.
        dst = p.get("dst", f"variant_{cfg['patches'].index(p):02d}.py")
        cmd.extend(["--patch", str(tree / "patches" / dst)])
    began = time.monotonic()
    proc = subprocess.run(cmd, cwd=tree, env=env, text=True, capture_output=True, timeout=1800)
    (work / "build.log").write_text(proc.stdout + "\n--- STDERR ---\n" + proc.stderr)
    result = {
        "name": cfg["name"],
        "status": "BUILD_FAILED" if proc.returncode else "EMITTED",
        "returncode": proc.returncode,
        "elapsed_seconds": time.monotonic() - began,
        "work": str(work),
        "tree": str(tree),
        "stdout": proc.stdout[-4000:],
        "stderr": proc.stderr[-4000:],
        "config": cfg,
    }
    reports = sorted(out.glob("*.build.json")) if out.exists() else []
    if reports:
        report_path = reports[0]
        report = json.loads(report_path.read_text())
        sys.path.insert(0, str(ROOT / "work/tools"))
        from evo_invsqrt import score_report
        result["score"] = score_report(report)
        result["build_report"] = str(report_path)
        result["build_report_sha256"] = sha256(report_path)
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", type=pathlib.Path, required=True)
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--work", type=pathlib.Path)
    args = ap.parse_args()
    cfg = load_cfg(args.config)
    if args.work:
        work = args.work
        work.mkdir(parents=True, exist_ok=True)
        result = run_build(cfg, work)
    else:
        with tempfile.TemporaryDirectory(prefix="evo-invsqrt-", dir="/tmp/opencode") as td:
            result = run_build(cfg, pathlib.Path(td))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if result["returncode"]:
        sys.exit(result["returncode"])


if __name__ == "__main__":
    main()
