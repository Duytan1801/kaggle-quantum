#!/usr/bin/env python3
"""h32_m6_stage_screen2.py — control (m=7 shipped config) + richer m=6 stages.

Findings from screen 1 (2026-11-23 09:5x UTC), all measured with the
UNCHANGED bundle model on all 3,133,452 inputs:

  m7 (shipped config)      -> CONTROL, margin = ?
  m6 ideal                 -> +131,552,726   (exact series: viable)
  m6 trunc s=7             ->  +94,568,973   (exact table of T, 128-wide cells)
  m6 trunc s=8             ->  +13,768,299   (exact table of T, 256-wide cells)
  m6 trunc s=9             -> -810,700,180   (exact table of T, 512-wide cells)
  m6 quad + exact cubic    -> -516,135,809
  m6 r37 nb=11 exact cubic  -> -1,575,853,774
  m6 r37 nb=11 DEF7 pieces -> -5,939,779,480,920

So the m=6 chain closes ONLY if the higher-order stage's table is accurate to
~1e-8 relative.  Two knobs can still buy that inside the stage's own
parameterisation:
  * `cub`     - more cubic pieces (the list may hold many [weight, bits]);
  * `cubtab`  - the cubic as a table of the top k folded bits (2^k entries).
Screen 2 measures whether either closes the gap, with m=7 as the control.
"""
from __future__ import annotations

import json
import pathlib

OUT = pathlib.Path('/tmp/opencode/h32_screen/m6_specs2.json')


def base(name, m=6, **kw):
    s = dict(name=name, m=m, ho='r37', st={}, s=9, off=0, bt=6,
             F1=5, ring=27, blast=1, slot='std')
    s.update(kw)
    return s


def cub_shift(nb, weights=(4, 8, 2, 1)):
    top = nb - 1
    return [[weights[0], [top]],
            [weights[1], [top, top - 1]],
            [weights[2], [top, top - 2]],
            [weights[3], [top, top - 3]]]


def main() -> int:
    specs = []
    # --- CONTROL: the shipped m=7 configuration ---------------------------
    specs.append(base('m7_shipped_control', m=7, st={}, off=0))
    specs.append(base('m7_ideal_control', m=7, ho='ideal', off=-1))
    specs.append(base('m7_trunc_s8_control', m=7, ho='trunc', off=-1, s=8))
    # --- m=6 with a bigger cubic table over the top k folded bits ---------
    for k in (9, 10, 11, 12):
        specs.append(base(f'm6_nb11_cubtab{k}_exact',
                          st=dict(nb=11, cub='exact', cubtab=[k, [0] * (1 << k)])))
    # --- m=6 with more cubic pieces (quartic terms) ----------------------
    nb = 11
    top = nb - 1
    cub = cub_shift(nb) + [[1, [top, top - 1, top - 2]],
                           [1, [top, top - 1, top - 2, top - 3]]]
    specs.append(base('m6_nb11_exactcub_plusquartic', st=dict(nb=11, cub='exact')))
    specs.append(base('m6_nb11_quarticpieces', st=dict(nb=11, cub=cub)))
    # --- m=6 trunc at s=8 with the offset variants ------------------------
    for off in (0, 1, -2):
        specs.append(base(f'm6_trunc_s8_off{off}', ho='trunc', off=off, s=8))
    # --- m=6 ideal (upper bound, re-checked) ------------------------------
    specs.append(base('m6_ideal_recheck', ho='ideal', off=-1))
    # --- m=6 with a finer cell in the r37 stage: the model's stage_ref
    #     hardcodes y >> 9, so a finer cell needs a new stage; the closest
    #     in-model proxy is the trunc family at s=7/s=8 (above).
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(specs, indent=1))
    print(f'{len(specs)} specs -> {OUT}')
    for s in specs:
        print(' ', s['name'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
