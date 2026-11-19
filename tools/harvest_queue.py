#!/usr/bin/env python3
"""harvest_queue.py — adjudicate the public-release queue.

The radar (`harness/watch_public.py`) writes every new/updated public release
to `work/harvest/PENDING.tsv`.  This tool is how the campaign closes the loop:

  list      show the queue, newest first
  take REF  mark a ref as being worked on (removes it from the queue, logs it)
  done REF VERDICT [NOTE]
            record the verdict for a ref in work/harvest/ADOPTED.tsv
  add REF NOTE
            re-queue a ref manually (e.g. a release we want to re-examine)

The point of `take`/`done` is that a release must never be rediscovered
forever: the radar is version-aware, so an un-adjudicated ref keeps its key in
SEEN.tsv and will NOT re-enter the queue on its own — which is why `done`
matters.  A release that is genuinely not worth taking can be closed with
`done <ref> rejected <reason>`.

Usage:
  harvest_queue.py list
  harvest_queue.py take  <ref>
  harvest_queue.py done  <ref> <verdict> [note]
  harvest_queue.py add   <ref> [note]
"""
from __future__ import annotations

import pathlib
import sys
import time

H = pathlib.Path('/home/bandoc/Downloads/opencode/work/harvest')
PENDING = H / 'PENDING.tsv'
ADOPTED = H / 'ADOPTED.tsv'


def read_pending() -> list[list[str]]:
    if not PENDING.exists():
        return []
    rows = []
    for line in PENDING.read_text().splitlines():
        if line.strip():
            rows.append(line.split('\t'))
    return rows


def write_pending(rows: list[list[str]]) -> None:
    PENDING.write_text('\n'.join('\t'.join(r) for r in rows) + ('\n' if rows else ''))


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    rows = read_pending()

    if cmd == 'list':
        if not rows:
            print('PENDING queue is EMPTY')
            return 0
        print(f'{len(rows)} pending release(s):')
        # newest first
        for r in sorted(rows, key=lambda r: r[2] if len(r) > 2 else ''):
            print('  ' + '\t'.join(r[:6]))
        return 0

    if cmd == 'take':
        ref = argv[2]
        keep = [r for r in rows if len(r) < 2 or r[1] != ref]
        if len(keep) == len(rows):
            print(f'ref not in queue: {ref}')
            return 1
        write_pending(keep)
        print(f'taken: {ref}  (queue now {len(keep)})')
        return 0

    if cmd == 'done':
        ref, verdict = argv[2], argv[3]
        note = argv[4] if len(argv) > 4 else ''
        ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        with open(ADOPTED, 'a') as f:
            f.write(f'{ts}\t{ref}\t{verdict}\t{note}\n')
        keep = [r for r in rows if len(r) < 2 or r[1] != ref]
        write_pending(keep)
        print(f'done: {ref} -> {verdict}  (logged in {ADOPTED.name})')
        return 0

    if cmd == 'add':
        ref = argv[2]
        note = argv[3] if len(argv) > 3 else ''
        if any(len(r) > 1 and r[1] == ref for r in rows):
            print(f'already queued: {ref}')
            return 1
        ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
        rows.append(['manual', ref, ts, note, '', 'manual', 'manual'])
        write_pending(rows)
        print(f'queued: {ref}')
        return 0

    print(__doc__)
    return 2


if __name__ == '__main__':
    raise SystemExit(main(sys.argv))
