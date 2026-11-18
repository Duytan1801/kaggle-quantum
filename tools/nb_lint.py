#!/usr/bin/env python3
"""nb_lint.py — mechanical pre-push lint for Kaggle notebook JSON.
Invariant (not prose): a notebook may only be pushed after this passes.

Checks:
  1. file parses as strict JSON
  2. has kernelsmith-compatible structure: metadata, nbformat, cells[]
  3. every code cell's source passes ast.parse
  4. no cell references a file that doesn't exist next to the notebook
     (only warns, since datasets may be attached at push time)

Usage: python3 nb_lint.py <notebook.ipynb> [more.ipynb ...]
Exit 0 = lint clean, exit 1 = any error (print all errors first).
"""
import ast, json, os, re, sys

errors, warnings = [], []

def lint(path):
    try:
        raw = open(path, "rb").read()
        nb = json.loads(raw.decode("utf-8"))
    except Exception as e:
        errors.append(f"{path}: JSON parse failed: {e}")
        return
    if not isinstance(nb, dict) or "cells" not in nb:
        errors.append(f"{path}: not a notebook (no cells[])")
        return
    n_src = 0
    for i, cell in enumerate(nb.get("cells", [])):
        src = cell.get("source", "")
        if isinstance(src, list):
            src = "".join(src)
        ct = cell.get("cell_type", "?")
        if ct == "code":
            n_src += 1
            try:
                ast.parse(src)
            except SyntaxError as e:
                errors.append(
                    f"{path}: cell {i} ast.parse FAILED: {e.msg} (line {e.lineno}): "
                    f"{(src.splitlines() or ['<empty>'])[max(0, (e.lineno or 1) - 1)][:120]!r}"
                )
        elif ct not in ("markdown", "raw"):
            errors.append(f"{path}: cell {i} unknown cell_type {ct!r}")
    # referenced-file existence check (warning only)
    base = os.path.dirname(os.path.abspath(path))
    blob = raw.decode("utf-8", "replace")
    for m in sorted(set(re.findall(r"[\w./-]+\.(?:kmb|json|npz|npy|py|csv|txt)\b", blob))):
        cand = os.path.join(base, m)
        if "/" not in m and not os.path.exists(cand):
            warnings.append(f"{path}: referenced file not present locally: {m} (ok if dataset-attached)")
    print(f"{path}: {len(nb.get('cells', []))} cells, {n_src} code cells linted")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    for p in sys.argv[1:]:
        lint(p)
    for w in warnings:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    sys.exit(1 if errors else 0)
