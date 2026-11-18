#!/usr/bin/env python3
"""list_ds_files.py — page through `kaggle datasets files` and print all paths.

The Kaggle CLI paginates the file list with an opaque page token, so a complete
inventory of a large dataset (e.g. manwithacat/vqcc-apache-public-circuits, 5.4 GB,
every public circuit of this competition) takes several calls.  We print one path per
line so the caller can filter and fetch single files with `kaggle datasets download -f`.

Usage: list_ds_files.py <owner/dataset> [--max-pages 40] [--out FILE]
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

KG = '/home/bandoc/Downloads/opencode/qaenv/bin/kaggle'


def main():
    ds = sys.argv[1]
    max_pages = 40
    out = None
    if '--max-pages' in sys.argv:
        max_pages = int(sys.argv[sys.argv.index('--max-pages') + 1])
    if '--out' in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])
    token = None
    lines = []
    for page in range(max_pages):
        cmd = [KG, 'datasets', 'files', ds, '--page-size', '200']
        if token:
            cmd += ['--page-token', token]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        txt = r.stdout
        if not txt:
            print('no output:', r.stderr[:200], file=sys.stderr)
            break
        tok = None
        for ln in txt.splitlines():
            if ln.startswith('Next Page Token = '):
                tok = ln.split('=', 1)[1].strip()
                continue
            parts = ln.split()
            if len(parts) >= 2 and parts[1].isdigit():
                lines.append(parts[0])
        print(f'page {page}: +{len(lines)} paths, next_token={"yes" if tok else "no"}', file=sys.stderr)
        if not tok:
            break
        token = tok
    if out:
        out.write_text('\n'.join(lines) + '\n')
        print('wrote', out, len(lines), 'paths', file=sys.stderr)
    else:
        print('\n'.join(lines))


if __name__ == '__main__':
    main()
