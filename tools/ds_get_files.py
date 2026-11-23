#!/usr/bin/env python3
"""Download selected files of a Kaggle dataset by name (per-file API).

Usage: ds_get_files.py <owner/slug> <file> [file...]

The dataset ARCHIVE download often 404s while the individual files are already
published (Kaggle creates the archive asynchronously).  `kaggle datasets
download -f FILE` works for those, so public-release harvesting must be able
to fetch a manifest file-by-file.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    ref = sys.argv[1].strip('/')
    files = sys.argv[2:]
    out = pathlib.Path('/tmp/opencode/ds_get') / ref.replace('/', '_')
    out.mkdir(parents=True, exist_ok=True)
    rc = 0
    for f in files:
        cmd = ['kaggle', 'datasets', 'download', ref, '-f', f, '-p', str(out), '--force']
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        target = out / f
        ok = target.exists() and target.stat().st_size > 0
        print(f'{"OK " if ok else "FAIL"} {f} ({(target.stat().st_size if ok else 0)} B)'
              + ('' if ok else ' :: ' + ((p.stderr or p.stdout) or '')[-160:].replace('\n', ' ')))
        if not ok:
            rc = 1
    print(f'root: {out}')
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
