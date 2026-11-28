#!/usr/bin/env python3
"""build_codeevolve_chem_bundle.py — assemble the CHEMISTRY CodeEvolve bundle.

WHAT THIS IS
------------
The chemistry lane's evolutionary search needs FOUR things on the Kaggle
kernel, and the bundle ships all four:

  problem/input/evaluate.py   the exact evaluator (symbolic simulation of a
                               rewritten loader over all 1,219 addresses)
  problem/input/src/init_program.py
                               the seed program (baseline recipe)
  problem/config_qcc.yaml     the search configuration (MAP-Elites over
                               CCX x batch, 4 islands, 300 epochs)
  tree/dfthcsos/*             the 15 loaders + submission.npz (the exact
                               bytes of the v153 tree)
  tools/chem_extract.py       the plan recovery helpers the evaluator imports
  tools/chem_plan.py
  kickmix/kickmix.so          the competition's own circuit extension
                               (CPython 3.13 only)
  codeevolve/                 the vendored, unmodified science-codeevolve
                               package (Apache-2.0)

WHY THE BUNDLE CARRIES THE TREE, NOT A LINK
--------------------------------------------
The evaluator is EXACT: a rewrite is accepted only if it reproduces the
original circuit's values AND phases on all 1,219 valid addresses.  That
means the evaluator must see the very bytes the submission ships; a
re-generated loader would be a different circuit.

Usage:
  build_codeevolve_chem_bundle.py --root /tmp/opencode/chem_ce_root
  build_codeevolve_chem_bundle.py --root ... --zip /tmp/opencode/chem_ce.zip
"""
from __future__ import annotations

import argparse
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path("/home/bandoc/Downloads/opencode")
TREE = ROOT / "work/trees/v153/dfthcsos"
EVO = ROOT / "work/evo/qcc_chem_codeevolve"
VENDOR = ROOT / "work/vendor/science-codeevolve"
KICKMIX = ROOT / "work/toolchain/kickmix/kickmix.so"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=pathlib.Path, required=True)
    ap.add_argument("--zip", type=pathlib.Path)
    a = ap.parse_args()
    root = a.root
    if root.exists():
        shutil.rmtree(root)
    (root / "problem" / "input" / "src").mkdir(parents=True)
    (root / "tree" / "dfthcsos").mkdir(parents=True)
    (root / "tools").mkdir(parents=True)
    (root / "kickmix").mkdir(parents=True)

    # problem package
    shutil.copyfile(EVO / "input" / "evaluate.py", root / "problem" / "input" / "evaluate.py")
    shutil.copyfile(EVO / "input" / "src" / "init_program.py",
                    root / "problem" / "input" / "src" / "init_program.py")
    shutil.copyfile(EVO / "config_qcc.yaml", root / "problem" / "config_qcc.yaml")

    # the tree bytes
    for p in sorted(TREE.iterdir()):
        if p.is_file():
            shutil.copyfile(p, root / "tree" / "dfthcsos" / p.name)

    # tools + kickmix
    for name in ("chem_extract.py", "chem_plan.py"):
        shutil.copyfile(ROOT / "work" / "tools" / name, root / "tools" / name)
    shutil.copyfile(KICKMIX, root / "kickmix" / "kickmix.so")

    # The vendored search framework (unmodified).  The upstream EXAMPLE
    # problems are dropped: they are not needed to run the search, and Kaggle
    # datasets are flat, so keeping them would push the file count past the
    # 200-file listing page and make the upload unverifiable.
    shutil.copytree(VENDOR, root / "codeevolve",
                    ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "problems"))

    files = [p for p in root.rglob("*") if p.is_file()]
    print(f"bundle at {root}: {len(files)} files, "
          f"{sum(p.stat().st_size for p in files) / 2**20:.1f} MiB")
    assert (root / "problem" / "input" / "evaluate.py").is_file()
    assert (root / "problem" / "input" / "src" / "init_program.py").is_file()
    assert (root / "problem" / "config_qcc.yaml").is_file()
    assert len(list((root / "tree" / "dfthcsos").glob("angle_k_*.kmb"))) == 15
    assert (root / "tree" / "dfthcsos" / "submission.npz").is_file()
    assert (root / "codeevolve" / "pyproject.toml").is_file()

    if a.zip:
        with zipfile.ZipFile(a.zip, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(files):
                z.write(p, p.relative_to(root).as_posix())
        print("zip:", a.zip, a.zip.stat().st_size / 2**20, "MiB")


if __name__ == "__main__":
    main()
