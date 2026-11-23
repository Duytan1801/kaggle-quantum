#!/usr/bin/env python3
"""Poll the competition board for a submission reference until it is scored.

Usage:
  score_poll.py --ref 58749949 [--poll 60] [--timeout 7200] [--label v146]

Writes the observed row to work/receipts/<LABEL>_BOARD_SCORE.tsv and prints it.
Exit codes: 0 = scored, 2 = timeout, 3 = error.
"""
from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import time

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
COMP = 'google-verifiable-quantum-circuit-compilation'
ROW = re.compile(
    r'^(?P<ref>\d+)\s+submission\.zip\s+(?P<date>\S+)\s+(?P<desc>.*?)\s+'
    r'SubmissionStatus\.(?P<status>\w+)\s*(?P<public>\S*)\s*(?P<private>\S*)\s*$')


def rows() -> list[dict]:
    r = subprocess.run(['kaggle', 'competitions', 'submissions', '-c', COMP],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout)[-300:])
    out = []
    for line in (r.stdout or '').splitlines():
        m = ROW.match(line)
        if m:
            d = m.groupdict()
            out.append({'ref': d['ref'], 'date': d['date'], 'status': d['status'],
                        'publicScore': d['public'] or '', 'privateScore': d['private'] or '',
                        'description': d['desc']})
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--ref', required=True)
    ap.add_argument('--poll', type=int, default=60)
    ap.add_argument('--timeout', type=int, default=7200)
    ap.add_argument('--label', default='v146')
    a = ap.parse_args()
    t0 = time.time()
    while True:
        try:
            found = [r for r in rows() if r['ref'] == a.ref]
        except Exception as e:  # noqa: BLE001
            print(f'poll error: {e}', flush=True)
            found = []
        if found:
            r = found[0]
            print(f"{time.strftime('%H:%M:%S')} ref={r['ref']} status={r['status']} "
                  f"publicScore={r['publicScore']!r} privateScore={r['privateScore']!r}",
                  flush=True)
            if r['status'] == 'COMPLETE' or r['publicScore']:
                dest = ROOT / 'work/receipts' / f'{a.label.upper()}_BOARD_SCORE.tsv'
                dest.write_text('\t'.join([r['ref'], r['date'], r['status'],
                                           r['publicScore'], r['privateScore'],
                                           r['description']]) + '\n')
                print(f'wrote {dest}', flush=True)
                return 0
        else:
            print(f'[{time.strftime("%H:%M:%S")}] ref {a.ref} not in the board yet',
                  flush=True)
        if time.time() - t0 > a.timeout:
            print('TIMEOUT waiting for the board score', flush=True)
            return 2
        time.sleep(a.poll)


if __name__ == '__main__':
    raise SystemExit(main())
