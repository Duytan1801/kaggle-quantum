#!/usr/bin/env python3
"""radar_check.py -- diff the live competition-kernel list against ADOPTED.

The public-release radar must see EVERY kernel on the competition board.
This tool lists the competition's kernels (all pages), compares them with
the refs already adjudicated in work/harvest/ADOPTED.tsv, and prints the
ones that are NOT adjudicated yet, so that they can be queued.

Usage: radar_check.py [--add]
    --add   queue the missing kernels through work/tools/harvest_queue.py
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KAGGLE = str(ROOT / 'qaenv/bin/kaggle')
COMP = 'google-verifiable-quantum-circuit-compilation'
ADOPTED = ROOT / 'work/harvest/ADOPTED.tsv'


def main() -> int:
    add = '--add' in sys.argv
    done = set()
    if ADOPTED.exists():
        for line in ADOPTED.read_text().splitlines():
            parts = line.split('\t')
            if len(parts) >= 2:
                done.add(parts[1].strip())
    print(f'adjudicated refs: {len(done)}')

    refs = []
    page = 1
    while True:
        cmd = [KAGGLE, 'kernels', 'list', '--competition', COMP,
               '--page', str(page), '--page-size', '100', '--csv']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            print('kaggle kernels list failed:', (r.stderr or r.stdout)[-300:])
            break
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        if not lines:
            break
        if page == 1:
            print('header:', lines[0][:200])
        for l in lines[1:]:
            parts = l.split(',')
            if len(parts) >= 2:
                ref = parts[0].strip()
                title = parts[1].strip().strip('"')
                refs.append((ref, title))
        if len(lines) <= 1:
            break
        page += 1
        if page > 40:
            break

    print(f'competition kernels listed: {len(refs)}')
    missing = [(r, t) for r, t in refs if r not in done]
    print(f'NOT adjudicated yet: {len(missing)}')
    for r, t in missing:
        print(f'  {r:60s} {t[:70]}')
    if add and missing:
        for r, t in missing:
            cmd = [str(ROOT / 'work/toolchain/venv/bin/python'),
                   str(ROOT / 'work/tools/harvest_queue.py'), 'add', r,
                   'kernel', t, 'radar-check']
            subprocess.run(cmd, capture_output=True, text=True)
        print(f'queued {len(missing)} kernels')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
