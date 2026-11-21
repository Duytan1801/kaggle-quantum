#!/usr/bin/env python3
"""invsqrt_fit.py — refit the invsqrt rotation angles to enlarge the phase margin.

WHY
    The invsqrt cost is

        score = Q * (toffoli + t/4 + n_rot * (0.56*log2(1/eps) + 5.3)/4),
        eps   = pi * min_margin / 2^64 / n_rot,

    and `min_margin` is the smallest (tolerance - |phase error|) over all
    3,133,452 inputs x.  The phase error is DETERMINISTIC (measured: identical
    for forced-zero, forced-one and random measurement outcomes), so it comes
    from the FITTED ANGLES, not from measurement randomness.  A better fit
    -> bigger min_margin -> bigger eps -> cheaper rotations -> lower score.

    Every Z_POW contributes `units * [the wire's value at that moment]`, so the
    implemented phase is

        theta(x) = sum_k u_k * v_k(x)   (mod 2^64)

    with u_k the angle of rotation k (units of 2^-64 turns, even integers) and
    v_k(x) its 0/1 execution indicator.  This tool extracts the v_k once (a
    single simulation with u_k = 2^k), then refits the u_k numerically.

USAGE
  python invsqrt_fit.py profile <circuit.kmx>                 # error profile
  python invsqrt_fit.py sens    <circuit.kmx> <out.npz>       # extract v_k
  python invsqrt_fit.py fit     <circuit.kmx> <sens.npz> <out.kmx> [iters]
  python invsqrt_fit.py apply   <circuit.kmx> <units.json> <out.kmx>
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, '/tmp/opencode/gens/x/invsqrt/v50')
import kmxsim as K  # noqa: E402

MASK64 = (1 << 64) - 1


def rot_indices(ops):
    return [i for i, op in enumerate(ops) if op.name == 'Z_POW']


def simulate(ops, xreg, outcomes='rand', seed=1):
    nq = K.num_wires(ops)
    sim = K.Sim(nq, outcomes, seed)
    sim.load_x(xreg)
    sim.run(ops)
    return sim


def phase_and_sign(ops, xreg, outcomes='rand', seed=1):
    sim = simulate(ops, xreg, outcomes, seed)
    return sim.phase.copy(), (K.unpack(sim.sign).astype(np.uint64) << np.uint64(63))


def error_profile(ops, xreg, outcomes='rand', seed=1):
    """Phase error profile over the legal inputs x = 1..MAX_X.

    The simulator pads the input set to a multiple of 64 (NPAD >= MAX_X), and
    the pad repeats x = 1; everything here is sliced to MAX_X so the shapes
    match the official reference arrays.
    """
    target, tol = K.reference()
    phase, sign = phase_and_sign(ops, xreg, outcomes, seed)
    theta = (phase + sign)[:K.MAX_X]
    err = (theta - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    ratio = used.astype(np.float64) / tol.astype(np.float64)
    margin = tol.astype(np.int64) - err.astype(np.int64)
    return dict(theta=theta, err=err, used=used, tol=tol, ratio=ratio,
                phase=phase[:K.MAX_X], sign=sign[:K.MAX_X], margin=margin)


def main() -> None:
    mode = sys.argv[1]
    path = sys.argv[2]

    if mode == 'profile':
        ops, xreg = K.parse_kmx(path)
        for outcomes in ('zero', 'one', 'rand'):
            p = error_profile(ops, xreg, outcomes, 1)
            r = p['ratio'][:K.MAX_X]
            idx = np.argsort(-r)[:15]
            print(f'=== outcomes={outcomes}: max ratio {r.max():.9f} at x={int(np.argmax(r))+1} '
                  f'min_margin {int((p["tol"][:K.MAX_X].astype(np.int64)-p["used"][:K.MAX_X].view(np.int64)).min())}')
            print('   top 15:', [(int(i) + 1, round(float(r[i]), 6)) for i in idx])
            for thr in (0.5, 0.9, 0.99, 0.999, 1.0):
                print(f'   #x with ratio > {thr}: {int((r > thr).sum())}')
        return

    if mode == 'sens':
        out = pathlib.Path(sys.argv[3])
        ops, xreg = K.parse_kmx(path)
        ridx = rot_indices(ops)
        n = len(ridx)
        print(f'{n} Z_POW gates')
        # one simulation with u_k = 2^k recovers all indicator vectors v_k(x)
        base_units = [op.units for op in ops]
        for k, i in enumerate(ridx):
            ops[i].units = (1 << k) & MASK64
        sim = simulate(ops, xreg, 'rand', 1)
        phase = sim.phase.copy()
        # phase(x) = sum_k 2^k v_k(x)  -> decode bits
        V = np.zeros((n, K.NPAD), dtype=bool)
        for k in range(n):
            V[k] = ((phase >> np.uint64(k)) & np.uint64(1)).astype(bool)
        # sanity: rebuild the phase with the original units
        for k, i in enumerate(ridx):
            ops[i].units = base_units[i]
        p = error_profile(ops, xreg, 'rand', 1)
        recon = np.zeros(K.NPAD, dtype=np.uint64)
        for k, i in enumerate(ridx):
            recon += np.where(V[k], np.uint64(base_units[i]), np.uint64(0))
        err = (recon + p['sign'] - p['target'] if 'target' in p else 0)
        np.savez_compressed(out, V=V, units=np.array([base_units[i] for i in ridx], dtype=np.uint64),
                            rot_idx=np.array(ridx, dtype=np.int64))
        print(f'wrote {out}  V shape {V.shape}')

    if mode == 'apply':
        ops, xreg = K.parse_kmx(path)
        units = json.load(open(sys.argv[3]))
        ridx = rot_indices(ops)
        assert len(ridx) == len(units['units']), (len(ridx), len(units['units']))
        lines = open(path).read().splitlines()
        k = 0
        for i, ln in enumerate(lines):
            t = ln.split()
            if t and t[0] == 'Z_POW':
                u = int(units['units'][k]) & MASK64
                # angle in turns = u / 2^64, printed exactly as a decimal
                from fractions import Fraction
                fr = Fraction(u, 1 << 64)
                dec = float(fr)
                txt = format(fr, '.64f') if fr >= 0 else '-0'
                # use an exact decimal expansion with 64 fractional digits
                s = (u * 10 ** 64) // (1 << 64)
                rem = (u * 10 ** 64) % (1 << 64)
                txt = f'{s // 10 ** 64}.{s % 10 ** 64:064d}'
                lines[i] = f'Z_POW {t[1]} {txt}'
                k += 1
        pathlib.Path(sys.argv[4]).write_text('\n'.join(lines) + '\n')
        print(f'wrote {sys.argv[4]} with {k} rewritten angles')

    if mode == 'fit':
        ops, xreg = K.parse_kmx(path)
        data = np.load(sys.argv[3])
        V = data['V']
        units = data['units'].astype(object)
        ridx = data['rot_idx']
        target, tol = K.reference()
        # the sign part (outcome dependent) and the current phase
        p = error_profile(ops, xreg, 'rand', 1)
        sign = p['sign']
        Vm = V[:, :K.MAX_X].astype(np.float64)
        # current residual
        cur = np.zeros(K.MAX_X, dtype=np.uint64)
        for k in range(V.shape[0]):
            cur += np.where(Vm[k] > 0, np.uint64(int(units[k])), np.uint64(0)).astype(np.uint64)
        base = cur + sign[:K.MAX_X]
        err0 = (base - target).view(np.int64)
        used0 = np.abs(err0).view(np.uint64)
        r0 = used0.astype(np.float64) / tol.astype(np.float64)
        print(f'current: max ratio {r0.max():.9f} at x={int(np.argmax(r0))+1}, '
              f'min_margin {int((tol.astype(np.int64)-used0.view(np.int64)).min())}')

        # ---- coordinate descent on the u_k (even integers), minimising the max ratio
        iters = int(sys.argv[4]) if len(sys.argv) > 4 else 40
        u = [int(x) & MASK64 for x in units]
        # scale: the tolerance at the binding x is ~2^39/sqrt(x); a unit change of
        # u_k shifts the phase of the affected inputs by 2^-64 turn.
        def residual(uu):
            ph = np.zeros(K.MAX_X, dtype=np.uint64)
            for k in range(len(uu)):
                if uu[k]:
                    ph += np.where(Vm[k] > 0, np.uint64(uu[k]), np.uint64(0)).astype(np.uint64)
            e = (ph + sign[:K.MAX_X] - target).view(np.int64)
            uu_used = np.abs(e).view(np.uint64)
            return uu_used.astype(np.float64) / tol.astype(np.float64), e

        best, _ = residual(u)
        best_max = best.max()
        print(f'start max ratio {best_max:.9f}')
        # candidate steps: powers of two units (2^-64 turn granularity)
        steps = [2 << s for s in range(0, 44)]
        for it in range(iters):
            improved = False
            for k in range(len(u)):
                if not Vm[k].any():
                    continue
                for st in steps:
                    for sign_dir in (1, -1):
                        old = u[k]
                        u[k] = (old + sign_dir * st) & MASK64
                        r, _ = residual(u)
                        rm = r.max()
                        if rm < best_max - 1e-15:
                            best_max = rm
                            improved = True
                            break
                    else:
                        u[k] = old
                        continue
                    break
            print(f'  iter {it}: max ratio {best_max:.9f}')
            if not improved:
                break
        r, e = residual(u)
        margin = int((tol.astype(np.int64) - np.abs(e).view(np.int64)).min())
        print(f'fitted: max ratio {r.max():.9f} at x={int(np.argmax(r))+1}, min_margin {margin}')
        nrot = float(sum(1 for i in ridx if K.zpow_class(int(units[k])) == 'rotation'))
        out_units = {'units': [int(x) for x in u]}
        pathlib.Path(sys.argv[5] + '.units.json').write_text(json.dumps(out_units))
        # write the new kmx
        lines = open(path).read().splitlines()
        for k, i in enumerate(ridx):
            pass
        kk = 0
        for i, ln in enumerate(lines):
            t = ln.split()
            if t and t[0] == 'Z_POW':
                uu = u[kk] & MASK64
                s = (uu * 10 ** 64) // (1 << 64)
                txt = f'{s // 10 ** 64}.{s % 10 ** 64:064d}'
                lines[i] = f'Z_POW {t[1]} {txt}'
                kk += 1
        pathlib.Path(sys.argv[5]).write_text('\n'.join(lines) + '\n')
        print(f'wrote {sys.argv[5]} and {sys.argv[5]}.units.json')


if __name__ == '__main__':
    main()
