#!/usr/bin/env python3
"""Apply a verdicts TSV to the harvest queue.

For every ref in the verdicts file: remove the row from work/harvest/PENDING.tsv
and append `timestamp<TAB>ref<TAB>verdict<TAB>note` to
work/harvest/ADOPTED.tsv.  Fails closed if a ref is not queued (so a verdict
can never silently disappear) and is idempotent (a ref already in ADOPTED is
not appended twice).
"""
from __future__ import annotations

import pathlib
import sys
import time

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
H = ROOT / 'work/harvest'
PENDING = H / 'PENDING.tsv'
ADOPTED = H / 'ADOPTED.tsv'
VERDICTS = H / 'VERDICTS_2026-11-23.tsv'


def main() -> int:
    if len(sys.argv) > 1:
        verdicts_path = pathlib.Path(sys.argv[1])
    else:
        verdicts_path = VERDICTS
    rows = [l.split('\t') for l in verdicts_path.read_text().splitlines()
            if l.strip() and not l.startswith('ref\t')]
    pending = [l.split('\t') for l in PENDING.read_text().splitlines() if l.strip()]
    pending_refs = {r[1] for r in pending}
    todo = [r for r in rows if r[0] in pending_refs]
    missing = [r[0] for r in rows if r[0] not in pending_refs]
    if missing:
        print(f'NOTE: not queued (already adjudicated): {missing}')

    todo_refs = {r[0] for r in todo}
    keep = [r for r in pending if r[1] not in todo_refs]
    PENDING.write_text('\n'.join('\t'.join(r) for r in keep) + ('\n' if keep else ''))

    existing = ADOPTED.read_text() if ADOPTED.exists() else ''
    stamp = time.strftime('%Y-%m-%d %H:%M:%S')
    out = []
    for ref, verdict, note in todo:
        if f'\t{ref}\t' in existing:
            print(f'skip (already in ADOPTED): {ref}')
            continue
        out.append(f'{stamp}\t{ref}\t{verdict}\t{note}')
    if out:
        with ADOPTED.open('a') as fh:
            fh.write('\n'.join(out) + '\n')
    print(f'adjudicated {len(out)} refs; PENDING now has {len(keep)} rows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
