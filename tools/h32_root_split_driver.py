#!/usr/bin/env python3
"""h32_root_split_driver.py — spawn-safe driver for the family-C root-split screen.

The bundled `r37_inv_40_model.py` uses `multiprocessing.Pool`, which DEADLOCKS
here: the parent imports numpy/scipy (which start OpenBLAS threads) BEFORE
forking, and the forked children inherit a locked allocator mutex.  Observed
directly: 6 workers sitting in `futex_do_wait` with <20 s of CPU each after
2 h of wall clock (2026-11-23 09:2x UTC).

This driver runs ONE spec per fresh process (`subprocess`, no fork of a
threaded parent), with the BLAS thread pools pinned to 1, and appends each
result to the same JSONL.  Specs are ordered cheapest-first so the kill/success
criteria are answered as early as possible.

Usage: h32_root_split_driver.py [--m 6] [--only NAME ...] [--jobs N]
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
TOOLS = (ROOT / 'work/gens/q2026_v154/isr/repo/experiments/isr/iterations'
         / '758_isr_leader_public/public_generator/invsqrt/tools')
WORK = pathlib.Path('/tmp/opencode/h32_screen')
MODEL = TOOLS / 'r37_inv_40_model.py'


def specs_for(m: int):
    """the m-ladder specs, ordered cheapest-first (ideal HO converges fastest)."""
    out = [
        dict(name=f'm{m}_ideal', m=m, ho='ideal', off=-1, bt=6,
             F1=5, ring=27, blast=1, slot='std'),
        dict(name=f'm{m}_r37_off-1', m=m, ho='r37', st={}, s=9,
             off=-1, bt=6, F1=5, ring=27, blast=1, slot='std'),
        dict(name=f'm{m}_r37_off0', m=m, ho='r37', st={}, s=9,
             off=0, bt=6, F1=5, ring=27, blast=1, slot='std'),
    ]
    for nb in (11, 12, 13):
        out.append(dict(name=f'm{m}_r37_nb{nb}', m=m, ho='r37',
                        st=dict(nb=nb), s=9, off=0, bt=6, F1=5,
                        ring=27, blast=1, slot='std'))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--m', nargs='+', type=int, default=[6])
    ap.add_argument('--only', nargs='*', default=None)
    ap.add_argument('--specs', default=None,
                    help='JSON file with an explicit list of spec dicts')
    ap.add_argument('--jobs', type=int, default=1)
    a = ap.parse_args()
    WORK.mkdir(parents=True, exist_ok=True)
    chain = WORK / 'chain.npz'
    if not chain.exists():
        raise SystemExit('chain.npz missing — run h32_root_split_screen.py first')

    env = dict(os.environ)
    env['PYTHONPATH'] = str(TOOLS)
    env['OMP_NUM_THREADS'] = '1'
    env['OPENBLAS_NUM_THREADS'] = '1'
    env['MKL_NUM_THREADS'] = '1'
    env['NUMEXPR_NUM_THREADS'] = '1'

    jobs = []
    if a.specs:
        jobs.extend(json.loads(pathlib.Path(a.specs).read_text()))
    else:
        for m in a.m:
            jobs.extend(specs_for(m))
    if a.only:
        jobs = [j for j in jobs if j['name'] in set(a.only)]

    outp = WORK / 'out.jsonl'
    done = set()
    if outp.exists():
        for line in outp.read_text().splitlines():
            try:
                done.add(json.loads(line).get('name'))
            except Exception:
                pass
    jobs = [j for j in jobs if j['name'] not in done]
    print(f'{len(jobs)} specs to run: {[j["name"] for j in jobs]}', flush=True)

    running = []
    while jobs or running:
        while jobs and len(running) < a.jobs:
            j = jobs.pop(0)
            sp = WORK / f'spec_{j["name"]}.json'
            sp.write_text(json.dumps([j], indent=1))
            cmd = [str(ROOT / 'harness/run_capped.sh'), '3G',
                   str(ROOT / 'work/toolchain/venv/bin/python'), str(MODEL),
                   str(TOOLS), str(WORK), str(outp), '1', str(sp)]
            print('START', j['name'], flush=True)
            p = subprocess.Popen(cmd, env=env)
            running.append((j['name'], p))
        time_sleep = 5
        import time
        time.sleep(time_sleep)
        for item in list(running):
            name, p = item
            if p.poll() is not None:
                print('DONE ', name, 'rc=', p.returncode, flush=True)
                running.remove(item)
    print('all specs done', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
