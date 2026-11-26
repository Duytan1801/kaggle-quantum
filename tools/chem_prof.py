#!/usr/bin/env python3
"""chem_prof.py -- the PROFILES and DIRECTIONS of a public plan's products.

For each product g = u.v of a public plan:
  * u = alpha_u + x(low), v = alpha_v + y(low) are XORs of the plan's
    features; split the feature set into bank-only / low-only / mixed and
    read off
      - the low profile of each factor (which columns it varies over),
      - the bank direction pair (alpha_u, alpha_v) as 77-bit vectors,
  * the column-difference contribution of the product is
        d_y(j).alpha_u + d_x(j).alpha_v ,
    so the profile difference vectors (d_x, d_y) in F_2^15 say at which
    columns each direction is active.

This is the structural signature of the construction, and it is what a
better plan has to beat.

Usage: chem_prof.py <batch> [--dump]
"""
from __future__ import annotations

import pathlib
import sys
from collections import Counter

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402
import chem_prune as CPR                                     # noqa: E402

NBANK, NLOW = 77, 16


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    k = int(args[0]) if args else 14
    dump = '--dump' in sys.argv

    P = CP.decode_plans()[k]
    f = CPR.plan_features(P)
    nf = len(f)
    G = CPR.product_functions(P, f)

    # feature classes
    swap = P['early'] > 0
    nb = 66 if swap else 68
    nmix = 9 if swap else 8
    bank_idx = set(range(5, 12)) | set(range(17, 17 + nb))
    if swap:
        bank_idx |= {17 + nb, 17 + nb + 1}
    mixed_idx = set(range(nf - nmix, nf))
    low_idx = set(range(nf)) - bank_idx - mixed_idx

    # the feature layout is fixed by the emitter (chem_plan.build_loader):
    #   0            constant (acts as a NOT on a control)
    #   1..11        address bits (1..4 low, 5..11 bank)
    #   12..16       QUADS features (low-only, from the incoming words)
    #   17..17+nb-1  cached bank ANDs (bank-only)
    #   (swap) +2    two more bank ANDs
    #   next 6       low ANDs (low-only)
    #   last 8/9     mixed (bank function AND low==7 / low==14)
    lo = {0} | set(range(1, 5)) | set(range(12, 17))
    bo = set(range(5, 12)) | set(range(17, 17 + nb))
    if swap:
        bo |= {17 + nb, 17 + nb + 1}
    low_and_start = (17 + nb + 2) if swap else (17 + nb)
    lo |= set(range(low_and_start, low_and_start + 6))
    mx = set(range(nf)) - bo - lo
    bo, lo, mx = sorted(bo), sorted(lo), sorted(mx)
    print(f'batch {k}: nf={nf}  bank-only {len(bo)}  low-only {len(lo)}  mixed {len(mx)}')

    def split(mask):
        """-> (bank-only part, low-only part, mixed part) as feature index sets"""
        idx = [j for j in np.nonzero(mask)[0].tolist()]
        return ([j for j in idx if j in bo], [j for j in idx if j in lo],
                [j for j in idx if j in mx])

    def bankvec(idx):
        """the 77-bit bank vector of a XOR of bank-only features"""
        v = 0
        for j in idx:
            v ^= f[j]
        out = 0
        for b in range(NBANK):
            if (v >> (b * NLOW)) & 1:
                out |= 1 << b
        return out

    def lowprofile(idx):
        """the 16-bit column profile of a XOR of low-only features"""
        v = 0
        for j in idx:
            v ^= f[j]
        out = 0
        for l in range(NLOW):
            if (v >> l) & 1:
                out |= 1 << l
        return out

    rows = []
    for p, (U, V) in enumerate(zip(P['U'], P['V'])):
        ub, ul, um = split(U)
        vb, vl, vm = split(V)
        au = bankvec(ub) if ub else 0
        av = bankvec(vb) if vb else 0
        xu = lowprofile(ul) if ul else 0
        xv = lowprofile(vl) if vl else 0
        # the column-difference profile vectors (15 bits, columns 1..15)
        dx = xu ^ (xu & 1)
        dy = xv ^ (xv & 1)
        # the difference of the LOW profile of the product is not simply the
        # difference of the factors: record the raw profiles too
        rows.append(dict(p=p, ub=ub, ul=ul, um=um, vb=vb, vl=vl, vm=vm,
                         au=au, av=av, xu=xu, xv=xv,
                         nact=sum((dx >> j) & 1 for j in range(1, NLOW))
                         + sum((dy >> j) & 1 for j in range(1, NLOW))))

    print()
    print('  factor mixes (bank/low/mixed feature counts):')
    mix = Counter((len(r['ub']), len(r['ul']), len(r['um']),
                   len(r['vb']), len(r['vl']), len(r['vm'])) for r in rows)
    for key, n in mix.most_common(8):
        print(f'    u:(b{key[0]},l{key[1]},m{key[2]}) v:(b{key[3]},l{key[4]},m{key[5]})'
              f'  x {n}')

    print()
    aus = Counter(r['au'] for r in rows)
    avs = Counter(r['av'] for r in rows)
    print(f'  distinct alpha_u: {len(aus)}   distinct alpha_v: {len(avs)}'
          f'   (of {len(rows)} products)')
    allv = set(aus) | set(avs)
    print(f'  distinct directions overall: {len(allv)}')
    B = CPR.Basis((i, v) for i, v in enumerate(allv) if v)
    print(f'  their rank: {B.rank()} of {NBANK}')

    print()
    print('  low profiles (16-bit column patterns) of the factors:')
    xu = Counter(r['xu'] for r in rows)
    xv = Counter(r['xv'] for r in rows)
    print(f'    distinct x_u patterns: {len(xu)}; distinct x_v patterns: {len(xv)}')
    for pat, n in xu.most_common(6):
        print(f'      x_u = {pat:016b}  x {n}')
    for pat, n in xv.most_common(6):
        print(f'      x_v = {pat:016b}  x {n}')

    print()
    print('  active difference columns per product (both directions):')
    print(f'    {dict(sorted(Counter(r["nact"] for r in rows).items()))}')

    if dump:
        print()
        for r in rows[:20]:
            print(f'    p{r["p"]:3d} au={bin(r["au"]).count("1"):2d} '
                  f'av={bin(r["av"]).count("1"):2d} xu={r["xu"]:016b} '
                  f'xv={r["xv"]:016b} mix u=({len(r["ub"])},{len(r["ul"])},'
                  f'{len(r["um"])}) v=({len(r["vb"])},{len(r["vl"])},'
                  f'{len(r["vm"])})')


if __name__ == '__main__':
    raise SystemExit(main())
