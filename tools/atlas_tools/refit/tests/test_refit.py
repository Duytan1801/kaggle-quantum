"""Fast tests for the refit toolkit (seconds; no network, no competition data needed).

    cd tools && python -m pytest -q refit/tests      or      python refit/tests/test_refit.py

With QCC_VERIFIERS (and QCC_FCIDUMP if the FCIDUMP is not next to the verifier) set, and QCC_TEST_NPZ pointing to a
submission.npz, test_verifier_metrics also compares the analytic model with the verifier's own math (about a minute).
Licence: Apache-2.0.
"""
import os
import sys

import numpy as np

TOOLS = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, TOOLS)
sys.dont_write_bytecode = True
from refit import chemeval as ce  # noqa: E402
from refit.model import SplitProblem, split, unsplit  # noqa: E402
from refit.__main__ import valid, main  # noqa: E402


class ToyModel:
    """Smooth stand-in for model.Model with the same evaluate() contract (metrics + gradients in w, wB)."""

    def __init__(self, shape, seed=0):
        rng = np.random.default_rng(seed)
        self.A = rng.normal(size=shape)
        self.B = rng.normal(size=shape[0::2])

    def evaluate(self, w, wB, need_grad=True, eps=0.0):
        e2 = float(np.sum((w - self.A) ** 2)); gap = 4.0 + float(np.sum(wB * self.B))
        e1 = float(np.sum(w * w) + np.sum(wB * wB)); lamh1 = float(np.sum(w * self.A))
        m = np.abs(w).sum(axis=1) + np.abs(wB)
        out = dict(error_1=e1, error_2=e2, E_gap=gap, Lambda=lamh1 + 0.25 * float(np.sum(m ** 2)), lambda_eff=1.0)
        if not need_grad:
            return out, None
        z = np.zeros_like(wB)
        g = {"e2": (2 * (w - self.A), z), "gap": (np.zeros_like(w), self.B.copy()), "e1": (2 * w, 2 * wB),
             "lamh1": (self.A.copy(), z), "m": m}
        return out, g


def test_split_roundtrip():
    rng = np.random.default_rng(1)
    w, wB = rng.normal(size=(2, 3, 4)), rng.normal(size=(2, 4))
    p, n, hp, hn = unsplit(split(w, wB), w.shape)
    assert np.allclose(p - n, w) and np.allclose(hp - hn, wB)
    assert (p >= 0).all() and (n >= 0).all() and (hp >= 0).all() and (hn >= 0).all()


def test_split_gradients_match_finite_differences():
    shape = (2, 3, 4)
    sp = SplitProblem(ToyModel(shape), shape)
    rng = np.random.default_rng(2)
    x = np.abs(rng.normal(size=2 * 24 + 2 * 8)) + 0.1
    o, g = sp.evaluate(x)
    h = 1e-6
    for key, metric in (("e2", "error_2"), ("gap", "E_gap"), ("e1", "error_1"), ("Lam", "Lambda_split")):
        for i in rng.choice(x.size, 6, replace=False):
            xp, xm = x.copy(), x.copy(); xp[i] += h; xm[i] -= h
            fd = (sp.evaluate(xp, False)[0][metric] - sp.evaluate(xm, False)[0][metric]) / (2 * h)
            assert abs(fd - g[key][i]) < 1e-5 * max(1.0, abs(fd)), (key, i, fd, g[key][i])


def test_valid_gates():
    m = dict(error_1=0.0199, error_2=0.0199, E_gap=3.92, gap_in_domain=True, Lambda=280.0)
    assert valid(m)
    assert not valid(dict(m, error_2=0.02))
    assert not valid(dict(m, E_gap=3.914898))
    assert not valid(dict(m, gap_in_domain=False))


def test_missing_verifier_message(tmp_path=None):
    import tempfile
    d = tempfile.mkdtemp()
    old = os.environ.pop("QCC_VERIFIERS", None)
    try:
        ce._STATE["verifiers"] = None
        try:
            ce.setup(os.path.join(d, "nothing"))
        except FileNotFoundError as e:
            assert "verifier" in str(e)
        else:
            raise AssertionError("setup should fail without a verifier")
    finally:
        if old is not None:
            os.environ["QCC_VERIFIERS"] = old


def test_cli_help():
    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0


def test_verifier_metrics():
    npz = os.environ.get("QCC_TEST_NPZ")
    if not (npz and os.environ.get("QCC_VERIFIERS")):
        print("skip test_verifier_metrics (set QCC_VERIFIERS and QCC_TEST_NPZ)")
        return
    from refit.model import Model
    ce._STATE["verifiers"] = None
    ce.setup()
    b = ce.load_npz(npz)
    w, wB = b["W"].astype(float), b["H2_I"].astype(float)
    ref = ce.evaluate(b["angle_words"], w, wB - w.sum(1), b["tree_edges"])
    M = Model(b["angle_words"], b["tree_edges"], *w.shape[:2])
    o, _ = M.evaluate(w, wB, need_grad=False)
    for k in ("error_1", "error_2", "E_gap", "Lambda", "lambda_eff"):
        assert abs(o[k] - ref[k]) < 1e-9 * max(1.0, abs(ref[k])), (k, o[k], ref[k])


if __name__ == "__main__":
    for name, f in sorted(globals().items()):
        if name.startswith("test_") and callable(f):
            f()
            print("ok", name)
