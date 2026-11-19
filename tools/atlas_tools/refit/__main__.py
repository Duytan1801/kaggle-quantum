"""Command line of the refit toolkit.

  python -m refit eval NPZ [NPZ ...]                 metrics of each file (verifier math)
  python -m refit run --start NPZ --minutes M --out DIR [--margin 1.5e-9] [--check-every 50]

Run from the folder that contains `refit/` (on Kaggle: /kaggle/input/qcc-circuit-atlas/tools), or put that folder
on sys.path. The competition verifier is read from /kaggle/input (attach the competition data), --verifiers or
QCC_VERIFIERS. `run` writes DIR/submission.npz (best exact point found; the start file if nothing better) and
DIR/refit_report.json. Confirm the result with the official dfthcsos/verify.py before you submit it.
Licence: Apache-2.0.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

from . import chemeval as ce

KEYS = ("lambda_eff", "error_1", "error_2", "E_gap", "Lambda", "gap_in_domain")
GATE = 0.02
FLOOR = 3.914898


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def valid(m: dict, margin: float = 1e-9) -> bool:
    """All verifier gates hold with at least `margin` (Ha) to spare (and Lambda is in its physical range)."""
    return (m["error_2"] < GATE - margin and m["error_1"] < GATE - margin and m["E_gap"] > FLOOR + margin
            and bool(m["gap_in_domain"]) and m["Lambda"] > 49.0)


def cmd_eval(a):
    for p in a.npz:
        m = ce.evaluate_npz(p)
        print(json.dumps({"file": os.path.basename(p), "sha256": _sha(p)[:12], **{k: m[k] for k in KEYS}}, default=float))


def cmd_run(a):
    from .model import Model, split, unsplit
    from .grg2 import GRG2
    t0 = time.time()

    def log(*x):
        print(f"[{(time.time() - t0) / 60:5.1f} min]", *x, flush=True)

    base = ce.load_npz(a.start)
    w0, wB0 = base["W"].astype(np.float64), base["H2_I"].astype(np.float64)

    def metrics(ww, bb):
        return ce.evaluate(base["angle_words"], ww, bb - ww.sum(1), base["tree_edges"])

    m0 = metrics(w0, wB0)
    log("start", {k: m0[k] for k in KEYS})
    best = {"leff": m0["lambda_eff"], "W": w0, "H2_I": wB0, "m": m0}
    deadline = t0 + 60 * a.minutes

    class Stop(Exception):
        pass

    def on_check(xe, okr):
        p, n, hp, hn = unsplit(xe, w0.shape)
        ww, bb = p - n, hp - hn
        m = metrics(ww, bb)
        if valid(m, a.accept_margin) and m["lambda_eff"] < best["leff"]:
            best.update(leff=m["lambda_eff"], W=ww.copy(), H2_I=bb.copy(), m=m)
            log("better", m["lambda_eff"])
        if time.time() > deadline:
            raise Stop()

    if a.minutes > 0:
        M = Model(base["angle_words"], base["tree_edges"], *w0.shape[:2], cache_key=a.cache_key)
        G = GRG2(M, w0.shape, log=(log if a.verbose else (lambda *x: None)), m2=a.margin, mg=a.margin, m1=max(a.margin, 2e-9))
        try:
            G.run(split(w0, wB0), a.max_iters, on_check=on_check, check_every=a.check_every)
        except Stop:
            pass
    os.makedirs(a.out, exist_ok=True)
    arrays = {k: np.array(base[k]) for k in base}
    arrays["W"], arrays["H2_I"] = best["W"], best["H2_I"]
    out = os.path.join(a.out, "submission.npz")
    with open(out, "wb") as f:
        np.savez(f, **arrays)
    rep = dict(start=os.path.basename(a.start), start_sha256=_sha(a.start), out_sha256=_sha(out), minutes=a.minutes,
               margin=a.margin, accept_margin=a.accept_margin, start_metrics={k: m0[k] for k in KEYS}, best_metrics={k: best["m"][k] for k in KEYS},
               improved=bool(best["leff"] < m0["lambda_eff"]), seconds=round(time.time() - t0, 1))
    json.dump(rep, open(os.path.join(a.out, "refit_report.json"), "w"), indent=1, default=float)
    log("lambda_eff", m0["lambda_eff"], "->", best["leff"], "written", out)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m refit", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verifiers", default=None, help="folder that contains dfthcsos/ (default: QCC_VERIFIERS or /kaggle/input search)")
    ap.add_argument("--fcidump", default=None, help="FCIDUMP file (default: the one packaged with the verifier)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval", help="print the verifier metrics of submission.npz files")
    e.add_argument("npz", nargs="+")
    r = sub.add_parser("run", help="refit W/H2_I of one submission.npz for a time budget")
    r.add_argument("--start", required=True, help="submission.npz to start from")
    r.add_argument("--minutes", type=float, required=True, help="wall-clock budget (0 = only evaluate and copy)")
    r.add_argument("--out", required=True, help="output folder")
    r.add_argument("--margin", type=float, default=1.5e-9, help="slack the refit targets on every gate (Ha)")
    r.add_argument("--accept-margin", type=float, default=1e-9, help="slack a saved point must have on every gate (Ha)")
    r.add_argument("--check-every", type=int, default=50, help="iterations between exact checks / saves")
    r.add_argument("--max-iters", type=int, default=100000)
    r.add_argument("--cache-key", default=None, help="cache the Qt matrices (~10 MB) in QCC_CACHE under this name")
    r.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    ce.setup(a.verifiers, a.fcidump)
    {"eval": cmd_eval, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    main()
