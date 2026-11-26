#!/usr/bin/env python3
"""radar_repair.py -- repair rows mis-queued by a broken harvest_queue.py call.

BUG (2026-11-25):  radar_queue.py called
        harvest_queue.py add <ref> 'kernel' <title> 'radar-title-triage'
but the tool's signature is
        harvest_queue.py add <ref> <note> <kind>
so the TITLE landed in the note column, the kind became the title (and was
rejected -> 'manual'), and every row was written as

        manual <ref> <ts> kernel '' manual manual

with the title LOST.  auto_adjudicate.py reads column 0 as the kind and
defaults anything unknown to 'dataset', so those 243 KERNEL rows would have
been handed to `kaggle datasets download` and closed wrongly.

This tool re-lists the competition kernels (to recover the titles) and
rewrites every such row to the correct shape:

        kernel <ref> <ts> <title> <author> <source> <version>

Usage:  radar_repair.py [--dry]
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KAGGLE = str(ROOT / 'qaenv/bin/kaggle')
COMP = 'google-verifiable-quantum-circuit-compilation'
PENDING = ROOT / 'work/harvest/PENDING.tsv'


def list_kernels():
    """-> {ref: title}"""
    out = {}
    page = 1
    while True:
        cmd = [KAGGLE, 'kernels', 'list', '--competition', COMP,
               '--page', str(page), '--page-size', '100', '--csv']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
        if r.returncode != 0:
            break
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        if len(lines) <= 1:
            break
        for l in lines[1:]:
            parts = l.split(',')
            if len(parts) >= 2:
                out[parts[0].strip()] = parts[1].strip().strip('"')
        page += 1
        if page > 40:
            break
    return out


def main() -> int:
    dry = '--dry' in sys.argv
    titles = list_kernels()
    print(f'competition kernels listed: {len(titles)}')

    rows = []
    for line in PENDING.read_text().splitlines():
        if line.strip():
            rows.append(line.split('\t'))

    fixed = 0
    still_missing = []
    for r in rows:
        if r and r[0] == 'manual' and len(r) >= 4 and r[3] == 'kernel':
            ref = r[1]
            title = titles.get(ref, '')
            if not title:
                still_missing.append(ref)
                continue
            r[0] = 'kernel'
            r[3] = title
            r[4] = ref.split('/')[0]
            r[5] = 'comp-kernels'
            r[6] = 'radar-title-triage'
            fixed += 1
    print(f'fixed rows: {fixed}')
    if still_missing:
        print(f'title not found for {len(still_missing)} refs: '
              f'{still_missing[:5]}')
    if dry:
        print('dry run -- not written')
        return 0
    PENDING.write_text('\n'.join('\t'.join(r) for r in rows) + '\n')
    print(f'PENDING.tsv rewritten: {len(rows)} rows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
