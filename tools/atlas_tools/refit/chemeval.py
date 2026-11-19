"""Exact DF-THC metrics of a chemistry submission.npz with the official verifier's own math (no kickmix).

The competition's chemistry verifier (`dfthcsos/scoreinfra`, Competition Data: NOT included in this dataset) is
found at run time, in this order:
  1. `setup(verifiers=..., fcidump=...)` called by your code (the CLI passes --verifiers / --fcidump),
  2. the environment variables QCC_VERIFIERS (folder that contains `dfthcsos/`) and QCC_FCIDUMP,
  3. a search of /kaggle/input for a `verifiers` folder with `dfthcsos/scoreinfra` (attach the competition data).
The FCIDUMP defaults to the one packaged with the verifier (its SHA-256 is checked by the verifier's own code).

Licence: Apache-2.0 (this file). The verifier code and data belong to the competition organisers.
"""
from __future__ import annotations

import functools
import glob
import os
import sys

import numpy as np

N_ORB = 76
_STATE = {"verifiers": None, "fcidump": None}


def find_verifiers(root: str = "/kaggle/input") -> str | None:
    """Return a folder that contains dfthcsos/scoreinfra/dfthc_math.py below `root`, or None."""
    for p in sorted(glob.glob(os.path.join(root, "**", "dfthcsos", "scoreinfra", "dfthc_math.py"), recursive=True)):
        return os.path.dirname(os.path.dirname(os.path.dirname(p)))
    return None


def setup(verifiers: str | None = None, fcidump: str | None = None) -> str:
    """Make the competition verifier importable. Returns the verifier folder."""
    v = verifiers or _STATE["verifiers"] or os.environ.get("QCC_VERIFIERS") or find_verifiers()
    if not v or not os.path.isdir(os.path.join(v, "dfthcsos", "scoreinfra")):
        raise FileNotFoundError(
            "competition verifier not found: attach the competition data on Kaggle, or pass --verifiers DIR "
            "(the folder that contains dfthcsos/) or set QCC_VERIFIERS")
    if v not in sys.path:
        sys.path.insert(0, v)
    _STATE["verifiers"] = v
    if fcidump or os.environ.get("QCC_FCIDUMP"):
        _STATE["fcidump"] = fcidump or os.environ.get("QCC_FCIDUMP")
    return v


def _ref():
    setup()
    from dfthcsos.scoreinfra import reference as refmod
    return refmod


def dm():
    """The verifier's dfthc_math module."""
    setup()
    from dfthcsos.scoreinfra import dfthc_math
    return dfthc_math


def refmod():
    return _ref()


@functools.lru_cache(1)
def reference():
    r = _ref()
    path = _STATE["fcidump"] or str(r.PACKAGED_FCIDUMP)
    r.check_fcidump(path)
    return r.load_reference(path)


@functools.lru_cache(1)
def shifts():
    r = _ref()
    sh = r.load_fixed_shifts()
    S = np.asarray(dm().symmetric_from_lower(sh["Hsym_lower"], N_ORB), dtype=np.float64)
    beta_1 = float(sh["H1_I"]) - 0.5 * float(np.trace(S))
    return S, beta_1


def load_npz(path: str) -> dict:
    """All arrays of a submission.npz (also .npz.gz) as a dict (W, H2_I, U, angle_words, tree_edges, ...)."""
    if path.endswith(".gz"):
        import gzip
        import io
        with gzip.open(path, "rb") as f:
            path = io.BytesIO(f.read())
    with np.load(path) as d:
        return {k: np.array(d[k]) for k in d.files}


def native(params: dict):
    """(w, Wc): the weights W and the native offsets Wc = H2_I - sum_b W."""
    w = np.asarray(params["W"], np.float64)
    Wc = np.asarray(params["H2_I"], np.float64) - w.sum(axis=1)
    return w, Wc


def evaluate(words, w, Wc, tree_edges, brot: int = 8) -> dict:
    """Verifier metrics (error_1, error_2, E_gap, Lambda, lambda_eff, gap_in_domain, ...) at these words/weights."""
    S, beta_1 = shifts()
    return dm().evaluate_dfthc_angle_words(words, w, Wc, S, beta_1, reference(), brot=brot,
                                           tree_edges=tree_edges, energy_upper=_ref().UPPER_ENERGY)


def evaluate_npz(path: str) -> dict:
    """Metrics of one submission.npz file."""
    b = load_npz(path)
    w, Wc = native(b)
    return evaluate(b["angle_words"], w, Wc, b["tree_edges"])
