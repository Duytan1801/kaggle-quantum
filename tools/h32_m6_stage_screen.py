#!/usr/bin/env python3
"""h32_m6_stage_screen.py — is the family-C m=6 (38-wire) invsqrt buildable?

MEASURED 2026-11-23 09:2x UTC (H32 screen, spawn-safe driver):
  * `m6_ideal`  margin = +131,552,726  (POSITIVE, converged) -> m=6 is
    MATHEMATICALLY VIABLE: a perfect higher-order stage closes the chain at
    the m=6 root split (model layout 39 wires -> build 38 wires).
  * `m6_r37` with the SHIPPED stage parameters (DEF7: nb=10, cub weights
    4/8/2/1 on bits 9,9+8,9+7,9+6) fails: the m=6 word is twice as wide
    (y in [-1044418, 1036414] vs m=7's half-width), so the folded top bits
    need nb=11 and every stage constant (lin = 3*2^(nb-9), the w_ij pairwise
    corrections and the cubic pieces) is tuned for the m=7 range.

This screen re-tunes the stage for the m=6 range and asks the unchanged model
for the all-input angle margin.  Knobs (all from the bundle's own
`r37_inv_40_ref.py`):
  nb         folded top bits (11 for m=6, 12 for m=5)
  cub        list of [weight, bits] cubic pieces
  cub='exact' the EXACT rounded cubic 5*yt^3/2^55 (model-only exactness)
  cubtab     [k, values] cubic as a table of the top k folded bits
  K2         constant half-unit offset
  cin_bits / cin_pairs / drop8   borrow-in knobs

KILL criterion: no spec reaches margin > 0 with a stage that is cheap in the
circuit (cub pieces only, or cubtab with k <= 8) -> the m=6 lane is closed
and the root-split ladder ends at m=7.
SUCCESS criterion: a spec reaches margin > 0 with cub-piece / small-cubtab
stage -> build it (m=6 -> 38 wires -> cost ~60,114 -> GM ~33.3196).
"""
from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path('/tmp/opencode/h32_screen/m6_specs.json')


def base(name, **kw):
    s = dict(name=name, m=6, ho='r37', st={}, s=9, off=0, bt=6,
             F1=5, ring=27, blast=1, slot='std')
    s.update(kw)
    return s


def cub_shift(nb, shift=None, weights=(4, 8, 2, 1)):
    """DEF7's cubic pieces re-anchored on the new top bit."""
    if shift is None:
        shift = nb - 10
    top = nb - 1
    return [[weights[0], [top]],
            [weights[1], [top, top - 1]],
            [weights[2], [top, top - 2]],
            [weights[3], [top, top - 3]]]


def main() -> int:
    specs = []
    # --- the exact cubic is the best possible stage at a given nb ----------
    for nb in (10, 11, 12):
        specs.append(base(f'm6_nb{nb}_exactcub', st=dict(nb=nb, cub='exact')))
    # --- the cubic pieces re-anchored on the new top bit ------------------
    for nb in (11, 12):
        specs.append(base(f'm6_nb{nb}_cubshift', st=dict(nb=nb, cub=cub_shift(nb))))
    # --- the pieces unshifted (control: should be as bad as DEF7) ----------
    specs.append(base('m6_nb11_cubDEF7', st=dict(nb=11, cub=cub_shift(10))))
    # --- off = -1 (the shipped cfg uses off 0 for m=7? try both) -----------
    specs.append(base('m6_nb11_exactcub_off-1', off=-1,
                      st=dict(nb=11, cub='exact')))
    specs.append(base('m6_nb12_exactcub_off-1', off=-1,
                      st=dict(nb=12, cub='exact')))
    # --- K2 constant offsets around the exact cubic -----------------------
    for k2 in (-64, -16, 16, 64):
        specs.append(base(f'm6_nb11_exactcub_K2{k2}',
                          st=dict(nb=11, cub='exact', K2=k2)))
    # --- a small cubic table over the top k folded bits -------------------
    for k in (4, 6, 8):
        vals = [0] * (1 << k)
        specs.append(base(f'm6_nb11_cubtab{k}',
                          st=dict(nb=11, cubtab=[k, vals])))
    # --- the other HO kinds the model supports (analytic, for reference) ---
    for kind in ('pade', 'trunc', 'quad'):
        specs.append(base(f'm6_{kind}', ho=kind, off=-1))
    specs.append(base('m6_quad_c3', ho='quad', off=-1, cub='c3'))
    specs.append(base('m6_trunc_s8', ho='trunc', off=-1, s=8))
    specs.append(base('m6_trunc_s7', ho='trunc', off=-1, s=7))
    # --- F1 variants (F1 < 5 shortens U by g bits) ------------------------
    for f1 in (3, 4):
        specs.append(base(f'm6_nb11_exactcub_F1{f1}', F1=f1,
                          st=dict(nb=11, cub='exact')))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(specs, indent=1))
    print(f'{len(specs)} specs -> {OUT}')
    for s in specs:
        print(' ', s['name'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
