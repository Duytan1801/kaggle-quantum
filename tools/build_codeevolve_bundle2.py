#!/usr/bin/env python3
"""build_codeevolve_bundle2.py — assemble the SECOND CodeEvolve+QCC bundle.

WHY A SECOND BUNDLE (the 2026-11-26 pipeline diagnosis)
----------------------------------------------------------
The first bundle (`build_codeevolve_bundle.py`, used for the v5 run) searched
the WRONG BASELINE and had a search space that could not reach the prize:

1. **Wrong incumbent.**  The v5 run searched the q2026-v154 ISR generator at
   its DEFAULT 39 q build (cost 62,993.55).  The tree we actually ship is
   37 q / cost 60,927.55 — the incumbent was WORSE than the best known
   solution, so the search was optimising from a point behind the frontier
   and every "improvement" was measured against the wrong reference.
   The Apache catalogue (765 scored circuits) confirms the public floor is
   37 q; the v155 ISR generator is the same lineage one generation newer.
2. **Width floor at 36 q.**  `NWCAP`, `cap` and `R63_CAP` allow-lists bottom
   out at 36, so no candidate could even be *proposed* below 36 q — but the
   gap arithmetic says 33 q is what the leaderboard needs.
3. **The incumbent's OWN generator was missing.**  The shipped 37 q circuit
   descends from prvsiyan's `6b592145` / varianceofx's `bb676b95` / Rithvik's
   `d2148a7c`, all on the **Syed Asad Ali generator line**, whose source we
   hold at `work/gens/vqcc_generator_line_2026-11-23/invsqrt_source` (Q = 46
   base, 561 files).  That source is the ONLY substrate that can *reproduce*
   the incumbent, and it was never in the bundle.

This bundle therefore ships THREE substrates, and the evaluator picks per
candidate:

    `isr`      the q2026-v154 ISR generator (13 min build, wide knob space)
    `v155`     the v155 ISR generator from dziyanavalenta (NEWER lineage)
    `gline`    the Syed Asad Ali generator line (the incumbent's own lineage,
               80 s build — the only substrate fast enough for a wide search)

and the evaluator adds a **cheap static pre-screen** so a candidate that
cannot possibly win never pays the 13-minute official-verifier cost.

Usage:
  build_codeevolve_bundle2.py --root /tmp/opencode/ce2_root
  build_codeevolve_bundle2.py --root ... --zip /tmp/opencode/qcc_codeevolve2.zip
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ISR_SRC = ROOT / "work/gens/q2026_v154/isr"
GLINE_SRC = ROOT / "work/gens/vqcc_generator_line_2026-11-23/invsqrt_source"
V155_TGZ = ROOT / "work/gens/v155_isr/isr_source_targz.bin"
KICKMIX = ROOT / "work/toolchain/kickmix/kickmix.so"
VERIFIER = ROOT / "work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py"
DRIVER = ROOT / "work/tools/h30_isr_caps.py"
CODEEVOLVE = ROOT / "work/vendor/science-codeevolve"
PROBLEM = ROOT / "work/evo/qcc_codeevolve2"

README = """# QCC CodeEvolve bundle v2 — incumbent-seeded, three-substrate, pre-screened

Everything needed to run the CodeEvolve evolutionary search for the Kaggle
`google-verifiable-quantum-circuit-compilation` inverse-square-root leg on a
Kaggle kernel.

* `codeevolve/` — vendored `inter-co/science-codeevolve` (Apache-2.0), unmodified.
* `problem/`    — the CodeEvolve problem package (evolved program + evaluator
                  + config).  The evaluator pre-screens statically and picks
                  the substrate per candidate.
* `isr/`        — the q2026-v154 ISR generator source (byte-identical to the
                  public release preserved under `work/gens/q2026_v154/isr`).
* `v155/`       — the v155 ISR generator source (dziyanavalenta's
                  `q2026-v155-isr-generator`, Apache-2.0).  One generation
                  newer than `isr/`; it is the lineage that produced the
                  39 q `b4ba2126` circuit.
* `gline/`      — the Syed Asad Ali generator line source (Apache-2.0) — the
                  ANCESTOR of the shipped 37 q incumbent (`bb676b95` /
                  `6b592145`).  It rebuilds `invsqrt.kmb` in ~80 s, which is
                  what makes a wide search affordable.
* `kickmix/`    — the CPython **3.13** extension the generators import.
* `verifier/`   — the UNCHANGED official invsqrt verifier.
* `h30_isr_caps.py` — build driver for the `isr` substrate.

Runtime layout on a Kaggle kernel:

    /kaggle/input/<slug>                <- QCC_DATA_ROOT
    /kaggle/working/qcc_ce2_cache       <- QCC_CACHE (build cache)
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
    if GLINE_SRC.exists():
        copytree(GLINE_SRC, root / "gline")
    if V155_TGZ.exists():
        (root / "v155").mkdir()
        shutil.copyfile(V155_TGZ, root / "v155/isr_source_targz.bin")
    (root / "kickmix").mkdir()
    shutil.copyfile(KICKMIX, root / "kickmix/kickmix.so")
    (root / "verifier").mkdir()
    shutil.copyfile(VERIFIER, root / "verifier/verify_submission_invsqrt.py")
    shutil.copyfile(DRIVER, root / "h30_isr_caps.py")
    if (ROOT / "work/tools/qcc_cfg_patch.py").exists():
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
    ap.add_argument("--root", type=Path, default=Path("/tmp/opencode/ce2_root"))
    ap.add_argument("--zip", type=Path, default=Path("/tmp/opencode/qcc_codeevolve2.zip"))
    a = ap.parse_args()
    root = assemble(a.root)
    print(f"assembled {root}")
    if a.zip:
        z = make_zip(root, a.zip)
        print(f"zip {z} bytes={z.stat().st_size} sha256={sha256(z)[:16]}")


if __name__ == "__main__":
    main()
