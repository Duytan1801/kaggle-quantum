#!/usr/bin/env python3
"""recalc_frontier.py — exact inverse-sqrt targets and GM operating points.

This is the mechanical companion to
``work/recon/frontier_recalc_2026-11-22.md``.  It prevents the v138/v139
mixed-leg arithmetic error that appeared in the 2026-11-22 00:44 state files.

With DQI and chemistry held at measured v139 costs, a target board GM G maps
to an inverse-sqrt cost C by

    C = REF_invsqrt / (G^3 / (REF_dqi/cost_dqi * REF_chem/cost_chem)).

Conversely, an inverse-sqrt cost maps to the composite GM directly.
"""
from __future__ import annotations

import argparse
from decimal import Decimal, getcontext

REF = {
    'invsqrt': Decimal('2076774.233715282'),
    'dqi': Decimal('24439463583672.93'),
    'dfthcsos': Decimal('3355599588.3155375'),
}
V139_COST = {
    'invsqrt': Decimal('60955.32670759028'),
    'dqi': Decimal('305041647011.3978'),
    'dfthcsos': Decimal('251692077.714951'),
}


def gm(inv_cost: Decimal, dqi_cost: Decimal = V139_COST['dqi'],
       chem_cost: Decimal = V139_COST['dfthcsos']) -> Decimal:
    product = (REF['invsqrt'] / inv_cost
               * REF['dqi'] / dqi_cost
               * REF['dfthcsos'] / chem_cost)
    return product ** (Decimal(1) / Decimal(3))


def inv_cost_for_gm(target: Decimal, dqi_cost: Decimal = V139_COST['dqi'],
                    chem_cost: Decimal = V139_COST['dfthcsos']) -> Decimal:
    other = REF['dqi'] / dqi_cost * REF['dfthcsos'] / chem_cost
    return REF['invsqrt'] / (target ** 3 / other)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', action='append', default=[],
                    help='target board GM (repeatable)')
    ap.add_argument('--inv-cost', action='append', default=[], type=Decimal,
                    help='inverse-sqrt cost (repeatable)')
    a = ap.parse_args()
    getcontext().prec = 50

    baseline = gm(V139_COST['invsqrt'])
    print(f'v139 baseline GM: {baseline}')
    for raw in a.target:
        target = Decimal(raw)
        cost = inv_cost_for_gm(target)
        print(f'target GM {target}: implied invsqrt cost {cost}')
    for cost in a.inv_cost:
        value = gm(cost)
        print(f'invsqrt cost {cost}: GM {value}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
