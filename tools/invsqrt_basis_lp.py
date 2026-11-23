#!/usr/bin/env python3
"""invsqrt_basis_lp.py — rank extra scratch-wire indicators for H25.

This consumes the salt-invariant catalogue produced by invsqrt_basis_probe.py
and the exact phase model produced by invsqrt_sens.py.  For each candidate
indicator f, it solves the same Chebyshev minimax LP as invsqrt_refit.py, but
with one additional column and one additional angle variable:

    maximise m
    subject to |err(x) + sum_j V[j,x] du_j + f[x] z| <= tol(x) - m.

Constraint generation starts from the most binding inputs and adds every
violation found by an exact scan of all 3,133,452 inputs.

Usage:
    python invsqrt_basis_lp.py <sens.npz> <basis.npz> <out.json> \
        [--candidates 1,2,3] [--all] [--iters 10] [--active 4000]
"""
from __future__ import annotations

import argparse
import json
import pathlib

import numpy as np
from scipy.optimize import linprog

MASK64 = (1 << 64) - 1


def zpow_class(units: int) -> str:
    u = int(units) & MASK64
    if u % (1 << 62) == 0:
        return "clifford"
    if u % (1 << 61) == 0:
        return "t"
    return "rotation"


def unpack_candidate(row: np.ndarray, n: int) -> np.ndarray:
    bits = np.unpackbits(row.view(np.uint8), bitorder="little")
    return bits[:n].astype(bool)


def fit_candidate(V: np.ndarray, err: np.ndarray, tol: np.ndarray,
                  f: np.ndarray, iters: int, active: int) -> dict:
    nvar = V.shape[0]
    nX = V.shape[1]
    margins0 = tol - np.abs(err)
    active_set = np.argsort(margins0)[:active].copy()

    # Variables: nvar existing-angle deltas, one new angle z, then m.
    c = np.zeros(nvar + 2)
    c[-1] = -1.0
    bounds = [(None, None)] * (nvar + 1) + [(None, None)]

    best_du = np.zeros(nvar)
    best_z = 0.0
    best_m = -1e30
    history = []
    for it in range(iters):
        rows = []
        rhs = []
        for x in active_set:
            v = V[:, x].astype(np.float64)
            z = float(f[x])
            # e + v.du + z*zvar <= tol - m
            rows.append(np.concatenate([v, [z, 1.0]]))
            rhs.append(float(tol[x] - err[x]))
            # -(e + v.du + z*zvar) <= tol - m
            rows.append(np.concatenate([-v, [-z, 1.0]]))
            rhs.append(float(tol[x] + err[x]))
        A = np.asarray(rows, dtype=np.float64)
        b = np.asarray(rhs, dtype=np.float64)
        res = linprog(c, A_ub=A, b_ub=b, bounds=bounds, method="highs")
        if not res.success:
            history.append({"iter": it, "error": res.message})
            break
        du = np.asarray(res.x[:nvar])
        z = float(res.x[nvar])
        m_lp = float(res.x[-1])

        acc = err.astype(np.float64)
        for j in range(nvar):
            if du[j]:
                acc += V[j].astype(np.float64) * du[j]
        if z:
            acc += f.astype(np.float64) * z
        mm = tol - np.abs(acc)
        minmargin = float(mm.min())
        bad = np.flatnonzero(mm < m_lp - 1.0)
        if minmargin > best_m:
            best_m = minmargin
            best_du = du.copy()
            best_z = z
        history.append({"iter": it, "lp_m": m_lp, "scan_m": minmargin,
                        "violations": int(len(bad))})
        if len(bad) == 0:
            break
        # Add the worst violations; cap the active set to keep HiGHS bounded.
        bad = bad[np.argsort(mm[bad])][:20000]
        active_set = np.unique(np.concatenate([active_set, bad]))
        if len(active_set) > 400000:
            active_set = active_set[-300000:]

    return {"min_margin": best_m, "du": best_du.tolist(), "z": best_z,
            "history": history}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("sens")
    ap.add_argument("basis")
    ap.add_argument("out")
    ap.add_argument("--candidates", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--iters", type=int, default=10)
    ap.add_argument("--active", type=int, default=4000)
    args = ap.parse_args()

    sens = np.load(args.sens, allow_pickle=True)
    basis = np.load(args.basis, allow_pickle=True)
    units = sens["units"]
    priced_idx = [i for i, u in enumerate(units) if zpow_class(int(u)) == "rotation"]
    V = sens["V"][priced_idx]
    err = sens["err"].astype(np.int64)
    tol = sens["tol"].astype(np.int64)
    nX = V.shape[1]
    base_margin = int(np.min(tol - np.abs(err)))

    if args.all:
        candidates = list(range(len(basis["bits"])))
    else:
        candidates = [int(x) for x in args.candidates.split(",") if x.strip()]
    results = []
    for cid in candidates:
        f = unpack_candidate(basis["bits"][cid], nX)
        fit = fit_candidate(V, err, tol, f, args.iters, args.active)
        occ = basis["occurrences"][basis["occurrences"][:, 2] == cid]
        result = {
            "candidate": cid,
            "frequency": int(basis["frequencies"][cid]),
            "occurrences": occ.tolist(),
            "base_margin": base_margin,
            "margin_ratio": fit["min_margin"] / max(1, base_margin),
            **fit,
        }
        results.append(result)
        print(f"candidate {cid:>3}: margin {fit['min_margin']:>18,.1f} "
              f"(x{fit['min_margin'] / max(1, base_margin):.6f}), z={fit['z']:+.6g}, "
              f"freq={result['frequency']}", flush=True)

    results.sort(key=lambda r: r["min_margin"], reverse=True)
    payload = {
        "base_margin": base_margin,
        "break_even_ratio": 2.96,
        "candidates": results,
    }
    pathlib.Path(args.out).write_text(json.dumps(payload, indent=1))
    print(f"wrote {args.out}; best x{results[0]['margin_ratio']:.6f}")


if __name__ == "__main__":
    main()
