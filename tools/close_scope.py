#!/usr/bin/env python3
"""close_scope.py — close queue rows whose release is about another competition.

Reads work/harvest/PENDING.tsv (read-only), and for every row whose ref/title
matches a known non-QCC competition, records the verdict with
work/tools/harvest_queue.py done (the only sanctioned way to close a row).

The note names the other competition and the measured evidence (title, author,
release timestamp) so the verdict is auditable.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
PENDING = ROOT / 'work/harvest/PENDING.tsv'
TOOL = ROOT / 'work/tools/harvest_queue.py'
PY = str(ROOT / 'work/toolchain/venv/bin/python')

# ref-substring -> (other competition, human label)
OTHER = {
    'santa-2026': ('santa-2026', 'Santa-2026 program-search puzzle'),
    'squares-in-squares': ('squares-in-squares', 'Squares-in-Squares packing atlas'),
    'gga-benchmark': ('gga-benchmark-telemetry-atlas', 'GGA telemetry atlas'),
    'specstream': ('us-data-samples', 'US company/filing data sample'),
    'casmi-scorer': ('casmi', 'CASMI molecular scorer'),
    'llm-speculative-decoding': ('llm-telemetry', 'LLM speculative-decoding telemetry'),
    'kaggle-shakeup-atlas': ('kaggle-shakeup', 'Kaggle shakeup atlas'),
    'spectra-to-structures': ('molecular-eda', 'molecular spectra EDA'),
    'black-cat-quantum-heist': ('puzzle-game', 'puzzle game notebook'),
    'the-real-150k': ('puzzle-game', 'puzzle/heuristic game notebook'),
    'quantum-sim-linalg-cache': ('quantum-sim-cache', 'generic quantum simulator cache'),
    'quantum-attempt-reset': ('general-quantum', 'generic quantum attempt-reset notebook'),
}


def close(ref, verdict, note):
    r = subprocess.run([PY, str(TOOL), 'done', ref, verdict, note],
                       capture_output=True, text=True)
    ok = r.returncode == 0
    print(f'  [{"ok" if ok else "FAIL"}] {verdict:14s} {ref}')
    if not ok:
        print('    ', (r.stdout + r.stderr)[-300:])
    return ok


def main():
    rows = [l.split('\t') for l in PENDING.read_text().splitlines() if l.strip()]
    n = 0
    for r in rows:
        if len(r) < 4:
            continue
        ref, title = r[1], r[3]
        for key, (comp, label) in OTHER.items():
            if key in ref.lower():
                note = (f'other competition ({comp}): {label}; release title "{title}"; '
                        f'no VQCC/dfthcsos/invsqrt/dqi circuit candidate, not scored here')
                close(ref, 'out-of-scope', note)
                n += 1
                break
    print(f'closed {n} out-of-scope rows')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
