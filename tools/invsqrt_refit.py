#!/usr/bin/env python3
"""invsqrt_refit.py — minimax refit of the invsqrt rotation angles.

MODEL
    The phase of the invsqrt circuit is, for every input x,

        theta_s(x) = sum_k u_k * v_k^s(x) + sign_s(x)      (mod 2^64 units)

    where u_k is the angle of Z_POW gate k (units of 2^-64 turns), v_k^s(x) is
    the indicator "gate k fires on input x in outcome stream s", and sign_s is
    the pi-phase bookkeeping.  v and sign do not depend on the angles, so the
    whole phase is LINEAR in u.  The current signed error of every x is known
    from invsqrt_sens.py, hence for an angle change du:

        err_new_s(x) = err_s(x) + sum_k v_k^s(x) * du_k

    (the official verifier computes the error mod 2^64; the simulator confirms
    the branch choice after the fit).

OBJECTIVE
    The score is  Q * (toffoli + t/4 + n_rot * (0.56*log2(1/eps)+5.3)/4)  with
    eps = pi * min_margin / 2^64 / n_rot, and min_margin is the SMALLEST
    (tol(x) - |err(x)|) over all x and all shots.  So the score-relevant
    objective is exactly

        maximise  m   subject to   |err_s(x)| <= tol(x) - m   for every x, s.

    That is a linear program.  It is solved with constraint generation: start
    from the few thousand most binding x, solve the LP, scan all x for
    violations, add them, repeat.

CEILING
    min_margin can never exceed min_x tol(x) = tol(max_x) = 2^-24/sqrt(max_x)
    turns, so the whole lane is bounded:  max min_margin = 6.21e8 units vs the
    current 3.66e7 units (factor 17), which is worth about +0.13 GM.

USAGE
    python invsqrt_refit.py analyze <sens.npz> [<sens2.npz> ...]
    python invsqrt_refit.py fit <out.json> <sens.npz> [<sens2.npz> ...] [--iters 12] [--active 4000]
    python invsqrt_refit.py apply <circuit.kmx> <units.json> <out.kmx>
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np
from scipy.optimize import linprog

MASK64 = (1 << 64) - 1


def load(streams):
    """-> list of dicts with V (n_rot, MAX_X) bool, err int64, tol uint64, units uint64, texts."""
    out = []
    for p in streams:
        d = np.load(p, allow_pickle=True)
        out.append(dict(path=str(p), V=d['V'], err=d['err'], tol=d['tol'], target=d['target'],
                        units=d['units'], texts=d['texts'], rot_idx=d['rot_idx']))
    return out


def zpow_class(units: int) -> str:
    """clifford / t / rotation, mirroring the official z_pow_class."""
    u = int(units) & MASK64
    if u % (1 << 62) == 0:
        return 'clifford'
    if u % (1 << 61) == 0:
        return 't'
    return 'rotation'


def analyze(streams):
    S = load(streams)
    tol = S[0]['tol'].astype(np.int64)
    print(f'{len(S)} outcome stream(s)')
    allm = []
    for s in S:
        err = s['err'].astype(np.int64)
        m = tol - np.abs(err)
        allm.append(m)
        r = np.abs(err).astype(np.float64) / tol.astype(np.float64)
        i = int(np.argmin(m))
        print(f'  {s["path"]}: min margin {int(m.min())} units at x={i + 1} '
              f'(tol {int(tol[i])}, |err| {int(abs(err[i]))}, ratio {r[i]:.9f}); '
              f'max ratio {r.max():.9f}')
    M = np.stack(allm)
    lo = M.min(axis=0)
    hi = M.max(axis=0)
    spread = hi - lo
    print(f'\nacross streams: worst-case margin {int(lo.min())}, max spread {int(spread.max())} units '
          f'(= {spread.max() / tol.min():.3e} of tol(max_x))')
    order = np.argsort(lo)[:20]
    print('\n20 most binding x (worst margin over streams):')
    for i in order:
        print(f'   x={int(i) + 1:>9}  margin {int(lo[i]):>14,}  tol {int(tol[i]):>14,}  '
              f'ratio {abs(S[0]["err"][i]) / tol[i]:.9f}  spread {int(spread[i]):,}')
    # theoretical ceiling
    ceil = int(tol.min())
    print(f'\nCEILING: min_margin <= min_x tol(x) = {ceil:,} units '
          f'(current {int(lo.min()):,}, factor {ceil / max(1, int(lo.min())):.2f})')
    # score impact
    import math
    nrot = sum(1 for u in S[0]['units'] if zpow_class(int(u)) == 'rotation')
    q = 37
    for name, mm in (('current', int(lo.min())), ('ceiling', ceil)):
        eps = math.pi * mm / 2 ** 64 / nrot
        rt = 0.56 * math.log2(1 / eps) + 5.3
        print(f'   {name}: min_margin {mm:,} -> eps {eps:.6e}, rot_t {rt:.4f}')
    return S


def fit(out_json, streams, iters=12, active=4000):
    from scipy.optimize import linprog
    S = load(streams)
    tol = S[0]['tol'].astype(np.int64)
    units0 = S[0]['units']
    nrot_total = len(units0)
    classes = [zpow_class(int(u)) for u in units0]
    var_idx = [k for k, c in enumerate(classes) if c == 'rotation']
    fixed_idx = [k for k, c in enumerate(classes) if c != 'rotation']
    print(f'{nrot_total} Z_POW: {len(var_idx)} priced (variables), {len(fixed_idx)} free (fixed)')

    # margin per stream / x
    margins = [tol - np.abs(s['err'].astype(np.int64)) for s in S]
    lo = np.stack(margins).min(axis=0)
    active_set = np.argsort(lo)[:active].copy()

    # column matrix for the variables, per stream: (n_var, MAX_X) kept as BOOL
    # (float64 for the whole matrix would be 826 MB per stream); the matvec is
    # done chunk by chunk.
    Vs = [s['V'][var_idx, :].astype(bool) for s in S]
    errs = [s['err'].astype(np.int64) for s in S]

    nvar = len(var_idx)
    c = np.zeros(nvar + 1)
    c[-1] = -1.0
    bounds = [(None, None)] * nvar + [(None, None)]

    best_du = np.zeros(nvar)
    best_m = -1e30
    for it in range(iters):
        rows = []
        rhs = []
        for x in active_set:
            for si in range(len(S)):
                v = Vs[si][:, x].astype(np.float64)
                # err + v.du <= tol - m   <=>   v.du + m <= tol - err
                rows.append(np.concatenate([v, [1.0]]))
                rhs.append(float(tol[x] - errs[si][x]))
                # -(err + v.du) <= tol - m  <=>  -v.du + m <= tol + err
                rows.append(np.concatenate([-v, [1.0]]))
                rhs.append(float(tol[x] + errs[si][x]))
        A = np.asarray(rows, dtype=np.float64)
        b = np.asarray(rhs, dtype=np.float64)
        res = linprog(c, A_ub=A, b_ub=b, bounds=bounds, method='highs')
        if not res.success:
            print(f'  iter {it}: LP failed: {res.message}')
            break
        du = np.asarray(res.x[:nvar])
        m_lp = float(res.x[-1])
        # scan every x, every stream
        viol = []
        minmargin = None
        chunk = 100000
        nX = S[0]['V'].shape[1]
        for x0 in range(0, nX, chunk):
            x1 = min(x0 + chunk, nX)
            chunk_min = None
            for si in range(len(S)):
                acc = errs[si][x0:x1].astype(np.float64)
                for j in range(nvar):
                    if du[j]:
                        acc += Vs[si][j, x0:x1] * du[j]
                mm = tol[x0:x1] - np.abs(acc)
                chunk_min = float(mm.min()) if chunk_min is None else min(chunk_min, float(mm.min()))
                if si == 0:
                    worst = mm
            if minmargin is None:
                minmargin = chunk_min
            else:
                minmargin = min(minmargin, chunk_min)
            bad = np.flatnonzero(worst < m_lp - 1.0)
            if len(bad):
                viol.extend((x0 + bad).tolist())
        if minmargin is not None and minmargin > best_m:
            best_m = minmargin
            best_du = du
        print(f'  iter {it}: LP m={m_lp:,.1f}  scanned min margin {minmargin:,.1f}  '
              f'violations {len(viol)}')
        if not viol:
            break
        # add the worst violators
        viol = np.array(sorted(set(viol)), dtype=np.int64)
        add = viol[np.argsort(tol[viol] - 0)][:20000]
        active_set = np.unique(np.concatenate([active_set, add]))
        if len(active_set) > 400000:
            active_set = active_set[-300000:]

    # integer rounding
    du_int = [int(round(float(x))) for x in best_du]
    new_units = [(int(units0[k]) + du_int[j]) & MASK64 for j, k in enumerate(var_idx)]
    out = {'var_idx': var_idx, 'units': [int(x) for x in new_units],
           'min_margin_scan': best_m, 'du': [float(x) for x in best_du]}
    pathlib.Path(out_json).write_text(json.dumps(out, indent=1))
    print(f'\nwrote {out_json}: scanned min margin {best_m:,.1f} units')
    print(f'   angle changes (units of 2^-64 turns):')
    for j, k in enumerate(var_idx):
        if du_int[j]:
            print(f'     rot {k:>2}: {int(units0[k]):>22} -> {int(new_units[j]):>22} '
                  f'(du {du_int[j]:>+14})  class {classes[k]} -> {zpow_class(int(new_units[j]))}')
    return out


def apply_angles(kmx_path, units_json, out_path):
    """Rewrite the Z_POW angles.  The KMX exponent is in HALF TURNS; the
    verifier's unit is 2^-64 turns, so the exponent text must be u/2^63.
    u/2^63 is exact in decimal with 63 fractional digits, and
    expo_to_units(u/2^63) == u (the verifier rounds to the nearest even unit).
    """
    data = json.loads(pathlib.Path(units_json).read_text())
    var_idx = data['var_idx']
    new_units = data['units']
    lines = pathlib.Path(kmx_path).read_text().splitlines()
    k = -1
    changed = 0
    for i, ln in enumerate(lines):
        t = ln.split()
        if not t or t[0] != 'Z_POW':
            continue
        k += 1
        if k not in var_idx:
            continue
        u = int(new_units[var_idx.index(k)]) & MASK64
        whole, frac = divmod(u * 5 ** 63, 10 ** 63)
        lines[i] = f'Z_POW {t[1]} {whole}.{frac:063d}'
        changed += 1
    pathlib.Path(out_path).write_text('\n'.join(lines) + '\n')
    print(f'wrote {out_path}: {changed} angles rewritten')


def main():
    mode = sys.argv[1]
    if mode == 'analyze':
        analyze(sys.argv[2:])
    elif mode == 'fit':
        out = sys.argv[2]
        args = sys.argv[3:]
        iters, active = 12, 4000
        if '--iters' in args:
            iters = int(args[args.index('--iters') + 1])
        if '--active' in args:
            active = int(args[args.index('--active') + 1])
        streams = [a for a in args if a.endswith('.npz')]
        fit(out, streams, iters, active)
    elif mode == 'apply':
        apply_angles(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
