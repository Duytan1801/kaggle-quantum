#!/usr/bin/env python3
"""List every file of a Kaggle dataset (all pages) via the CLI.

Usage: ds_files.py <owner/slug> [--csv out.csv]

The CLI `kaggle datasets files` prints one page plus a "Next Page Token = ..."
line; the dataset manifest API paginates with that token.  Public-release
harvesting needs the COMPLETE manifest (competitors ship their circuits as
`circuits/<task>/<hash>/...`, and the archive download is often still 404).
"""
from __future__ import annotations

import csv
import pathlib
import re
import subprocess
import sys

TOKEN = re.compile(r'^Next Page Token = (\S+)\s*$')


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ref = sys.argv[1].strip('/')
    rows: list[tuple[str, int]] = []
    token = None
    while True:
        cmd = ['kaggle', 'datasets', 'files', ref, '--format', 'csv', '--page-size', '200']
        if token:
            cmd += ['--page-token', token]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        out = p.stdout or ''
        nxt = None
        data: list[tuple[str, int]] = []
        for line in out.splitlines():
            m = TOKEN.match(line)
            if m:
                nxt = m.group(1)
                continue
            if not line.strip() or line.startswith('name,size'):
                continue
            parts = line.split(',')
            if len(parts) < 2:
                continue
            data.append((parts[0], int(parts[1])))
        rows.extend(data)
        if not nxt or not data:
            break
        token = nxt
    print(f'{ref}: {len(rows)} files')
    if '--csv' in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index('--csv') + 1])
        with out.open('w', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['name', 'bytes'])
            w.writerows(rows)
        print(f'wrote {out}')
    else:
        for n, b in rows:
            print(f'{b}\t{n}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
