#!/usr/bin/env python3
"""invsqrt_shrink.py — delete priced invsqrt rotations, re-fit the rest, verify.

WHY
    eps = pi*min_margin/2^64/n_rot, and the score contains n_rot*rot_t(eps)/4,
    so every priced rotation that can be deleted without losing margin is worth
    ~275 cost units (~+0.05 GM).  The minimax LP says dropping ONE priced
    rotation keeps min_margin at 36,584,658 units (the full set's optimum), so
    the basis is effectively redundant for the minimax objective.

    This tool does the whole pipeline for a given set of dropped rotations:
      1. LP over the surviving indicator vectors (constraint generation),
      2. rewrite the KMX: delete the dropped Z_POW gates, rewrite the angles
         of the survivors with the fitted values (exact 63-digit decimals),
      3. run the exact simulator (kmxsim) on the rewritten circuit: it
         reproduces the official verifier's phase, margin and score.

Usage:
    python invsqrt_shrink.py greedy <sens.npz> <out_prefix> [max_drops]
    python invsqrt_shrink.py apply  <sens.npz> <out_prefix> <k> [seed]
    python invsqrt_shrink.py list   <sens.npz>
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kmxsim as K  # noqa: E402
from invsqrt_lab import solve_lp, score_for, zpow_class  # noqa: E402

MASK64 = (1 << 64) - 1
KMX = '/tmp/opencode/ours37.kmx'


def angle_text(u: int) -> str:
    """KMX Z_POW exponent (HALF TURNS) for a phase of u units of 2^-64 turns."""
    u = int(u) & MASK64
    whole, frac = divmod(u * 5 ** 63, 10 ** 63)
    return f'{whole}.{frac:063d}'


def write_kmx(ops, xreg, out_path, keep_idx, new_units_by_rot):
    """Write the circuit with only `keep_idx` rotations, with new angles."""
    body = []
    k = -1
    for op in ops:
        if op.name == 'Z_POW':
            k += 1
            if k not in keep_idx:
                continue
            if k in new_units_by_rot:
                op.units = int(new_units_by_rot[k]) & MASK64
                op.expo = angle_text(op.units)
            # free rotations keep their original angle
        body.append(op.text())
    with open(out_path, 'w') as f:
        for q in xreg:
            f.write(f'APPEND_TO_REGISTER q{q} r0\n')
        f.write('REGISTER r0 "x"\n')
        f.write('\n'.join(body) + '\n')


def lp_fit(V, err, tol, cols):
    m, du, na = solve_lp(V[cols, :], err, tol, iters=10, active=5000)
    return m, du


def err_after_drops(V, err, target, units, drop):
    """Signed error of the circuit AFTER the dropped Z_POW gates are deleted.

    Deleting a gate removes its phase contribution u_k * v_k(x), so the error
    is recomputed in exact uint64 (mod 2^64) arithmetic from the current one.
    """
    n = err.shape[0]
    theta = (err.astype(np.uint64) + target.astype(np.uint64))
    contrib = np.zeros(n, dtype=np.uint64)
    for k in drop:
        contrib = (contrib + np.where(V[k], np.uint64(int(units[k])), np.uint64(0)))
    with np.errstate(over='ignore'):
        theta2 = (theta - contrib).astype(np.uint64)
        e = (theta2 - target.astype(np.uint64)).view(np.int64)
    return e


def main():
    mode = sys.argv[1]
    sens = sys.argv[2]
    d = np.load(sens, allow_pickle=True)
    V = d['V']
    err = d['err'].astype(np.int64)
    tol = d['tol'].astype(np.int64)
    units = d['units']
    classes = [zpow_class(u) for u in units]
    priced = [k for k, c in enumerate(classes) if c == 'rotation']
    ops, xreg = K.parse_kmx(KMX)
    npriced = len(priced)

    def finish(drop, out_prefix, tag):
        cols = [k for k in priced if k not in drop]
        print(f'  [{tag}] computing the error after drops {sorted(drop)}', flush=True)
        err_base = err_after_drops(V, err, d['target'], units, drop)
        print(f'  [{tag}] LP over {len(cols)} columns', flush=True)
        m, du = lp_fit(V, err_base, tol, cols)
        print(f'  [{tag}] LP done: margin {m}', flush=True)
        if m is None:
            print(f'  LP failed for drops {drop}')
            return None
        # new units for the surviving priced rotations
        newu = {}
        for j, k in enumerate(cols):
            du_int = int(round(float(du[j])))
            newu[k] = (int(units[k]) + du_int) & MASK64
        # class check
        nnew = sum(1 for k in cols if zpow_class(newu[k]) == 'rotation')
        # free rotations keep their angles
        out_kmx = f'{out_prefix}_{tag}.kmx'
        print(f'  [{tag}] writing {out_kmx}', flush=True)
        keep_idx = set(cols) | {k for k, c in enumerate(classes) if c != 'rotation'}
        write_kmx(ops, xreg, out_kmx, keep_idx, newu)
        # exact simulation
        print(f'  [{tag}] simulating', flush=True)
        r = subprocess.run([sys.executable, '/tmp/opencode/gens/x/invsqrt/v50/kmxsim.py',
                            out_kmx, 'rand', '1'], capture_output=True, text=True)
        tail = [l for l in r.stdout.strip().splitlines() if l.startswith('{')]
        if not tail:
            print(f'  simulator failed: {r.stderr[-500:]}')
            return None
        res = eval(tail[-1])
        sc = res['score']
        print(f'  drops={sorted(drop)} n_rot={nnew} LP margin {m:,.0f} | '
              f'SIM margin {res["min_margin"]:,} score {sc:,.2f} status {res["status"]} '
              f'worst_ratio {res["worst_ratio"]:.9f} @x={res["worst_x"]}')
        return dict(drop=sorted(drop), kmx=out_kmx, margin=res['min_margin'], score=sc,
                    nrot=nnew, status=res['status'])

    if mode == 'list':
        print('priced rotations (index, text, units):')
        for k in priced:
            print(f'  {k:>2} {d["texts"][k][:40]:<40} {int(units[k]):>22}')

    elif mode == 'apply':
        out_prefix = sys.argv[3]
        k = int(sys.argv[4])
        seed = int(sys.argv[5]) if len(sys.argv) > 5 else 0
        rng = np.random.default_rng(seed)
        drop = set(rng.choice(priced, size=k, replace=False).tolist()) if k else set()
        finish(drop, out_prefix, f'drop{k}s{seed}')

    elif mode == 'greedy':
        out_prefix = sys.argv[3]
        max_drops = int(sys.argv[4]) if len(sys.argv) > 4 else 6
        drop = set()
        for step in range(max_drops + 1):
            cols = [k for k in priced if k not in drop]
            err_base = err_after_drops(V, err, d['target'], units, drop)
            m, du = lp_fit(V, err_base, tol, cols)
            sc, eps, _ = score_for(m, len(cols))
            print(f'step {step}: drops={sorted(drop)} n={len(cols)} LP margin {m:,.0f} '
                  f'LP score {sc:,.2f}', flush=True)
            if step == max_drops:
                break
            # try dropping each remaining rotation; keep the one with the best margin
            cands = []
            for kk in cols:
                c2 = [k for k in priced if k not in drop and k != kk]
                eb = err_after_drops(V, err, d['target'], units, drop | {kk})
                m2, _ = lp_fit(V, eb, tol, c2)
                if m2 is None:
                    continue
                cands.append((m2, kk))
            cands.sort(reverse=True)
            if not cands:
                break
            m_best, k_best = cands[0]
            print(f'   best next drop: rot {k_best} -> margin {m_best:,.0f}', flush=True)
            drop.add(k_best)
        finish(drop, out_prefix, 'greedy')
    else:
        raise SystemExit(__doc__)


if __name__ == '__main__':
    main()
