#!/usr/bin/env python3
"""build_codeevolve_bundle.py — assemble the CodeEvolve+QCC bundle.

The bundle is the unit that ships to Kaggle as a dataset:

    <root>/
      isr/                 the q2026-v154 ISR generator source (unchanged)
      kickmix/kickmix.so   the CPython 3.13 extension the generator imports
      verifier/            the UNCHANGED official invsqrt verifier
      h30_isr_caps.py      the build driver (caps / env / stack-env knobs)
      codeevolve/          the vendored inter-co/science-codeevolve framework
      problem/             the CodeEvolve problem package
                             input/src/init_program.py   (the evolved program)
                             input/evaluate.py           (the evaluator)
                             config_qcc.yaml             (the run config)
      README.md

Usage
  build_codeevolve_bundle.py --root /tmp/opencode/ce_root
  build_codeevolve_bundle.py --zip  /tmp/opencode/qcc_codeevolve.zip
  build_codeevolve_bundle.py --root /tmp/opencode/ce_root --zip both.zip
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ISR_SRC = ROOT / "work/gens/q2026_v154/isr"
KICKMIX = ROOT / "work/toolchain/kickmix/kickmix.so"
VERIFIER = ROOT / "work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py"
DRIVER = ROOT / "work/tools/h30_isr_caps.py"
CODEEVOLVE = ROOT / "work/vendor/science-codeevolve"
PROBLEM = ROOT / "work/evo/qcc_codeevolve"

README = """# QCC CodeEvolve bundle

Everything needed to run the CodeEvolve evolutionary search for the Kaggle
`google-verifiable-quantum-circuit-compilation` inverse-square-root leg on a
Kaggle kernel.

* `codeevolve/` — vendored `inter-co/science-codeevolve` (Apache-2.0), unmodified.
* `problem/`    — the CodeEvolve problem package (evolved program + evaluator + config).
* `isr/`        — the q2026-v154 ISR generator source, byte-identical to the
                  public release preserved under `work/gens/q2026_v154/isr`.
* `kickmix/`    — the CPython **3.13** extension the generator imports.  It is
                  ABI-specific: Python 3.11/3.12 fail with
                  `undefined symbol: PyObject_ClearManagedDict`.
* `verifier/`   — the UNCHANGED official invsqrt verifier.
* `h30_isr_caps.py` — build driver; `--caps`, `--env`, `--stack-env`,
                  `--cfg-overlay`.

Runtime layout on a Kaggle kernel:

    /kaggle/input/<slug>                <- QCC_DATA_ROOT
    /kaggle/working/qcc_ce_cache        <- QCC_CACHE (build cache)
"""


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copytree(src: Path, dst: Path, skip: tuple[str, ...] = ()) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", *skip))


def assemble(root: Path) -> Path:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)

    copytree(ISR_SRC, root / "isr")
    (root / "kickmix").mkdir()
    shutil.copyfile(KICKMIX, root / "kickmix/kickmix.so")
    (root / "verifier").mkdir()
    shutil.copyfile(VERIFIER, root / "verifier/verify_submission_invsqrt.py")
    shutil.copyfile(DRIVER, root / "h30_isr_caps.py")
    shutil.copyfile(ROOT / "work/tools/qcc_cfg_patch.py", root / "qcc_cfg_patch.py")

    # the framework: source + packaging only (no tests / assets / benchmarks)
    copytree(CODEEVOLVE / "src", root / "codeevolve/src")
    copytree(CODEEVOLVE / "configs", root / "codeevolve/configs")
    for f in ("pyproject.toml", "LICENSE", "README.md"):
        if (CODEEVOLVE / f).exists():
            shutil.copyfile(CODEEVOLVE / f, root / "codeevolve" / f)

    copytree(PROBLEM / "input", root / "problem/input")
    shutil.copyfile(PROBLEM / "config_qcc.yaml", root / "problem/config_qcc.yaml")
    (root / "README.md").write_text(README)
    return root


def make_zip(root: Path, zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if p.is_dir() or "__pycache__" in p.parts:
                continue
            zf.write(p, p.relative_to(root.parent))
    return zip_path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path("/tmp/opencode/ce_root"))
    ap.add_argument("--zip", type=Path, default=Path("/tmp/opencode/qcc_codeevolve.zip"))
    a = ap.parse_args()
    root = assemble(a.root)
    print(f"assembled {root}")
    if a.zip:
        z = make_zip(root, a.zip)
        print(f"zip {z} bytes={z.stat().st_size} sha256={sha256(z)[:16]}")


if __name__ == "__main__":
    main()
