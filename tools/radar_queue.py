#!/usr/bin/env python3
"""radar_queue.py -- queue the not-yet-adjudicated competition kernels that
are worth adjudicating, using a TITLE TRIAGE (the queue is finite).

Rules (pre-registered):
  * a title that mentions a score of >= 25 (e.g. "33.21179", "lb-28-5"),
    or one of the strong words (frontier, sota, milestone, loader, chem,
    invsqrt, dqi, portfolio, verified, refit, splice, peephole, xor, search,
    rewrite, hybrid), is QUEUED;
  * obvious noise (santa-2026, casmi, ibm-quantum, starter-notebook,
    explained, tutorial, "how wrong") is SKIPPED;
  * everything else is left unqueued and reported as a count.

Usage: radar_queue.py [--apply]
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KAGGLE = str(ROOT / 'qaenv/bin/kaggle')
COMP = 'google-verifiable-quantum-circuit-compilation'
ADOPTED = ROOT / 'work/harvest/ADOPTED.tsv'
QPY = str(ROOT / 'work/toolchain/venv/bin/python')
HQ = str(ROOT / 'work/tools/harvest_queue.py')

STRONG = ('frontier', 'sota', 'milestone', 'loader', 'chem', 'invsqrt', 'dqi',
          'portfolio', 'verified', 'refit', 'splice', 'peephole', 'xor',
          'search', 'rewrite', 'hybrid', 'factor', 'optimizer', 'circuit')
NOISE = ('santa-2026', 'casmi', 'ibm-quantum', 'starter-notebook', 'explained',
         'tutorial', 'how wrong', 'about ', 'guide', 'learn', 'intro')
SCORE = re.compile(r'\b(?:lb[-_ ]?)?(\d{2})\.(\d{3,5})\b')


def main() -> int:
    apply = '--apply' in sys.argv
    done = set()
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
            break
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        if len(lines) <= 1:
            break
        for l in lines[1:]:
            parts = l.split(',')
            if len(parts) >= 2:
                refs.append((parts[0].strip(), parts[1].strip().strip('"')))
        page += 1
        if page > 40:
            break

    queued, skipped = [], 0
    for ref, title in refs:
        if ref in done:
            continue
        low = title.lower()
        if any(n in low for n in NOISE):
            skipped += 1
            continue
        m = SCORE.search(title)
        score = float(f'{m.group(1)}.{m.group(2)}') if m else 0.0
        if score >= 25.0 or any(s in low for s in STRONG):
            queued.append((ref, title))
        else:
            skipped += 1
    print(f'competition kernels: {len(refs)}; to queue: {len(queued)}; '
          f'skipped: {skipped}')
    for ref, title in queued:
        print(f'  {ref:62s} {title[:64]}')
    if apply:
        # harvest_queue.py's signature is:  add <ref> <note> <kind>
        for ref, title in queued:
            subprocess.run([QPY, HQ, 'add', ref, title, 'kernel'],
                           capture_output=True, text=True)
        print(f'queued {len(queued)} kernels through harvest_queue.py')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
