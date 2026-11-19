#!/usr/bin/env python3
"""watch_public.py — the campaign's public-release radar.

WHY THIS EXISTS (the 2026-11-19 bug)
------------------------------------
`harness/watch_public.sh` (bash, v1) polled `kaggle datasets list` with
`--sort-by dateCreated` and `--sort-by dateUpdated`.  Both are INVALID for the
Kaggle CLI: the accepted values are

    hottest | votes | updated | active | published

so **every dataset poll failed on every cycle**, and because `poll()` sent
stderr to /dev/null the failure was completely silent.  The dataset channel
had never once produced a detection.  Competitors release their circuit trees
as DATASETS, so the campaign was structurally blind to them: the
`asteriospanoras/qcc-circuit-atlas` release (28.23162) and three more releases
from 2026-11-19 were sitting in plain sight while the radar reported nothing.

Second defect: the bash version wrote its findings to
`/tmp/opencode/watch/new_releases.log` and NOTHING EVER READ THAT FILE.  The
wake prompt asked "Public tree changed?" with no sensor wired to the answer.
The bash watcher did detect `ozertuu/28-23163` at 23:49 UTC on 2026-11-18 and
`manvenderraparia/vqcc-28-23163` at 01:45 UTC on 2026-11-19 — both better than
the tree we eventually adopted — and both sat unread.

WHAT THIS FIXES
---------------
1. Every poll command is validated: a non-JSON or empty answer is a LOUD
   failure in the log, never a silent no-op.
2. State is DURABLE and lives in the repo (`work/harvest/`), so a reboot does
   not wipe the ledger.
3. Keys are VERSION-AWARE (`kind|ref|version-timestamp`), so a dataset that is
   updated after we already saw it re-enters the queue.
4. The publisher watch-list is SELF-GROWING: every author ever seen is watched
   from then on, so new publishers cannot hide.
5. The output is a FILE THE WAKE MUST READ: `work/harvest/PENDING.tsv`.
   That is the sensor that answers "Public tree changed?".
6. Both channels are covered: kernels (notebooks) AND datasets.

Usage:
    watch_public.py --once        # single pass (what campaign_wake.sh calls)
    watch_public.py --loop        # forever (what the systemd service calls)
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KG = 'kaggle'
COMP = 'google-verifiable-quantum-circuit-compilation'
H = ROOT / 'work/harvest'
SEEN = H / 'SEEN.tsv'
PENDING = H / 'PENDING.tsv'
AUTHORS = H / 'AUTHORS.txt'
LOG = H / 'watch.log'

# Seeds: publishers we already know about, plus the competition's own kernels.
SEED_AUTHORS = [
    'ozertuu', 'boristown', 'jeffemerson', 'leotang09', 'hayatohikawa',
    'marculera', 'syed3000', 'manwithacat', 'atakanaldemir', 'asteriospanoras',
    'ahoirg', 'maoxin123', 'hosen42', 'mrmeows', 'busyaprime', 'yoyobar',
    'heliosli', 'kirilltym', 'michaelrustad', 'vumaniacom', 'pramitdas',
    'junmiaotiao', 'arizalfirdaus123', 'ghazarosbarseghyan91', 'alexahern',
    'varianceofx', 'balramsrinivasan', 'srinath2495', 'jezzlin', 'henritonnang',
    'manvenderraparia', 'codeatlantis', 'ratnachand', 'aiokajima',
    'thomasgamet', 'apogean', 'rishabhbafnaiiitd', 'prami', 'auriclee',
    'nursrijan', 'c6519219f598', 'ozertuu',
]

# Search terms for the global dataset sweep.  The `-s qcc --sort-by updated`
# sweep is what actually surfaced `qcc-circuit-atlas`; the plain "newest
# created" head does not, because a dataset published earlier and updated
# later stays buried.
DATASET_SEARCHES = ['qcc', 'vqcc', 'quantum circuit', 'invsqrt', 'dqi',
                    'verifiable quantum', 'circuit compilation', 'dfthc']

# Valid Kaggle sort keys (verified 2026-11-19 against the installed CLI):
#   datasets: hottest | votes | updated | active | published
#   kernels:  dateRun | ... (the competition list accepts dateRun)
VALID_DATASET_SORTS = {'hottest', 'votes', 'updated', 'active', 'published'}

# The global dataset sweep sees ALL of Kaggle, not just the competition.  Only
# QCC-looking releases may enter the queue or the author watch-list — otherwise
# the queue fills with unrelated datasets and the author list explodes.
QCC_RE = re.compile(
    r'qcc|vqcc|quantum|circuit|invsqrt|inverse.?sqrt|dqi|dfthc|reversib|'
    r'compil|toffoli|qubit|chemistr|atlas|frontier|portfolio|syndrome|'
    r'decoder|mbuc|pec|amplitude|rotation|shor|qaoa|ising', re.I)

# The agent reads this file, so it must stay readable.
MAX_QUEUE = 400


def log(msg: str) -> None:
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())} {msg}"
    print(line, flush=True)
    try:
        with open(LOG, 'a') as f:
            f.write(line + '\n')
    except OSError:
        pass


def run_json(args: list[str]) -> list[dict]:
    """Run a kaggle list command and parse it as JSON.

    A failure returns [] AND is logged loudly — never silently.
    """
    cmd = [KG] + args + ['--format', 'json']
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired:
        log(f'POLL-FAILED (timeout): {" ".join(cmd)}')
        return []
    out = (r.stdout or '').strip()
    if r.returncode != 0:
        log(f'POLL-FAILED (rc={r.returncode}): {" ".join(cmd)} :: '
            f'{(r.stderr or "").strip()[:200]}')
        return []
    if not out:
        log(f'POLL-EMPTY: {" ".join(cmd)}')
        return []
    # Kaggle answers "this author has nothing" with a plain-text sentence, not
    # JSON.  That is NOT a failure — logging it as one would fill the log with
    # fake failures and train us to ignore real ones (the 2026-11-19 bug).
    if not out.startswith('['):
        low = out.lower()
        if any(s in low for s in ('no datasets found', 'not found', 'no kernels found',
                                  'no results')):
            return []
        log(f'POLL-FAILED (not json): {" ".join(cmd)} :: {out[:200]}')
        return []
    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        log(f'POLL-FAILED (not json): {" ".join(cmd)} :: {out[:200]}')
        return []
    if not isinstance(data, list):
        log(f'POLL-FAILED (shape): {" ".join(cmd)}')
        return []
    return data


class Ledger:
    def __init__(self):
        self.seen: set[str] = set()
        self.pending: list[dict] = []
        self.fresh: list[dict] = []      # rows detected during THIS run only
        if SEEN.exists():
            for line in SEEN.read_text().splitlines():
                if line.strip():
                    self.seen.add(line.split('\t', 1)[0])
        if PENDING.exists():
            for line in PENDING.read_text().splitlines():
                if line.strip():
                    f = line.split('\t')
                    self.pending.append({'kind': f[0], 'ref': f[1], 'when': f[2],
                                         'title': f[3] if len(f) > 3 else '',
                                         'author': f[4] if len(f) > 4 else '',
                                         'version': f[5] if len(f) > 5 else '',
                                         'source': f[6] if len(f) > 6 else ''})

    def add(self, kind: str, ref: str, version: str, title: str, author: str,
            source: str) -> None:
        # --- relevance gate -------------------------------------------------
        # A competition KERNEL is always ours, even when its title is garbage
        # ("notebook0a72b91d14") — it may embed a tree, so it always enters the
        # queue.  A DATASET needs a QCC-looking ref or title: the per-author
        # channel returns whatever that publisher last uploaded, and many of
        # them also publish unrelated Kaggle datasets (Mars maps, LoRA
        # adapters).  Without this gate the queue flooded to 1200 rows of which
        # only 340 were ours.
        if not (kind == 'kernel' and source.startswith('comp-kernels')):
            if not (QCC_RE.search(ref) or QCC_RE.search(title or '')):
                return
        key = f'{kind}|{ref}|{version}'
        if key in self.seen:
            return
        self.seen.add(key)
        row = {'kind': kind, 'ref': ref,
               'when': time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
               'title': title, 'author': author,
               'version': version, 'source': source}
        self.pending.append(row)
        self.fresh.append(row)

    def flush(self) -> None:
        H.mkdir(parents=True, exist_ok=True)
        SEEN.write_text('\n'.join(sorted(self.seen)) + '\n')
        # MERGE, DO NOT OVERWRITE.  The adjudicator (work/tools/harvest_queue.py
        # done / work/tools/queue_sweep.py) removes rows from PENDING.tsv when
        # it closes them.  This process used to write back its own in-memory
        # snapshot, which RESURRECTED every closed row on the next poll (378 of
        # 379 queued refs were already adjudicated).  So: re-read the file from
        # disk and merge only the rows detected during THIS run.
        disk: list[dict] = []
        if PENDING.exists():
            for line in PENDING.read_text().splitlines():
                if line.strip():
                    f = line.split('\t')
                    disk.append({'kind': f[0], 'ref': f[1], 'when': f[2],
                                 'title': f[3] if len(f) > 3 else '',
                                 'author': f[4] if len(f) > 4 else '',
                                 'version': f[5] if len(f) > 5 else '',
                                 'source': f[6] if len(f) > 6 else ''})
        merged = disk + [r for r in self.fresh if r not in disk]
        # One row per (kind, ref): if a release was updated and re-queued, only
        # the NEWEST version stays visible, so the agent never adjudicates the
        # same release three times.
        latest: dict[tuple[str, str], dict] = {}
        for p in merged:
            k = (p['kind'], p['ref'])
            if k not in latest or p['version'] >= latest[k]['version']:
                latest[k] = p
        # Order by the release's OWN timestamp (most recently updated first):
        # that is the actionable order, and it is stable across rebuilds.
        rows = sorted(latest.values(),
                      key=lambda p: (p['version'] or '', p['when']), reverse=True)
        # Cap the queue: the agent reads this file, so it must stay readable.
        # The newest rows are the actionable ones.
        rows = rows[:MAX_QUEUE]
        lines = []
        for p in rows:
            lines.append('\t'.join([p['kind'], p['ref'], p['when'],
                                    (p['title'] or '').replace('\t', ' ')[:120],
                                    (p['author'] or '').replace('\t', ' ')[:80],
                                    p['version'], p['source']]))
        PENDING.write_text('\n'.join(lines) + ('\n' if lines else ''))
        # The loop mode calls flush() every cycle; only the rows detected in
        # THIS cycle may be re-added, otherwise the loop would resurrect every
        # row it ever saw (and every row the adjudicator closed).
        self.fresh.clear()
        self.pending = merged


def read_authors() -> list[str]:
    seen: list[str] = []
    if AUTHORS.exists():
        seen = [l.strip() for l in AUTHORS.read_text().splitlines() if l.strip()]
    for a in SEED_AUTHORS:
        if a not in seen:
            seen.append(a)
    return seen


def write_authors(authors: list[str]) -> None:
    AUTHORS.write_text('\n'.join(sorted(set(authors))) + '\n')


def poll_once(led: Ledger, fast: bool = False) -> int:
    authors = set(read_authors())
    new_pending = 0

    # ---- channel 1: competition kernels (notebooks) --------------------------
    for row in run_json(['kernels', 'list', '--competition', COMP,
                         '--sort-by', 'dateRun', '--page-size', '40']):
        ref = row.get('ref')
        if not ref:
            continue
        ver = row.get('lastRunTime') or ''
        au = row.get('author') or ref.split('/')[0]
        authors.add(ref.split('/')[0])
        before = len(led.pending)
        led.add('kernel', ref, ver, row.get('title', ''), au, 'comp-kernels')
        new_pending += len(led.pending) - before

    # ---- channel 2: global dataset sweep, by update time --------------------
    #   (the "newest created" head hides datasets that were updated later)
    #   The global head is ALL of Kaggle, so only QCC-looking entries are kept.
    for srt in ('updated', 'published'):
        assert srt in VALID_DATASET_SORTS
        for row in run_json(['datasets', 'list', '--sort-by', srt,
                             '--page-size', '40']):
            ref = row.get('ref')
            if not ref:
                continue
            title = row.get('title', '') or ''
            if not QCC_RE.search(ref) and not QCC_RE.search(title):
                continue          # not ours — never pollute the queue or authors
            ver = row.get('lastUpdated') or ''
            au = ref.split('/')[0]
            authors.add(au)
            before = len(led.pending)
            led.add('dataset', ref, ver, title, au, f'global-{srt}')
            new_pending += len(led.pending) - before

    # ---- channel 3: global dataset sweep, by SEARCH -------------------------
    for term in DATASET_SEARCHES:
        for row in run_json(['datasets', 'list', '-s', term, '--sort-by', 'updated',
                             '--page-size', '40']):
            ref = row.get('ref')
            if not ref:
                continue
            title = row.get('title', '') or ''
            if not QCC_RE.search(ref) and not QCC_RE.search(title):
                continue
            ver = row.get('lastUpdated') or ''
            au = ref.split('/')[0]
            authors.add(au)
            before = len(led.pending)
            led.add('dataset', ref, ver, title, au, f'search:{term}')
            new_pending += len(led.pending) - before

    # ---- channel 4: per-publisher datasets AND kernels ----------------------
    #   the publisher list is self-growing: every author seen above is watched
    #   from now on, so a NEW publisher cannot hide after its first sighting.
    #   This channel costs ~2 API calls per author, so it runs on the SLOW cycle
    #   only; the global + search channels (channels 2 and 3) already surface
    #   anything recent, and the search sweeps are what caught the atlas.
    if not fast:
        for au in sorted(authors):
            for row in run_json(['datasets', 'list', '--user', au, '--sort-by', 'updated',
                                 '--page-size', '10']):
                ref = row.get('ref')
                if not ref:
                    continue
                ver = row.get('lastUpdated') or ''
                before = len(led.pending)
                led.add('dataset', ref, ver, row.get('title', ''), au, f'user:{au}')
                new_pending += len(led.pending) - before
            for row in run_json(['kernels', 'list', '--user', au, '--sort-by', 'dateRun',
                                 '--page-size', '10']):
                ref = row.get('ref')
                if not ref:
                    continue
                ver = row.get('lastRunTime') or ''
                before = len(led.pending)
                led.add('kernel', ref, ver, row.get('title', ''), au, f'user:{au}')
                new_pending += len(led.pending) - before
    else:
        # fast cycle still learns authors from the cheap channels
        authors |= set(read_authors())

    write_authors(authors)
    led.flush()
    log(f'pass done: pending={len(led.pending)} (new {new_pending}) '
        f'authors={len(authors)}')
    return new_pending


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--once', action='store_true')
    ap.add_argument('--loop', action='store_true',
                    help='run forever (default; the systemd service uses this)')
    ap.add_argument('--fast', action='store_true',
                    help='skip the expensive per-author channel (fast path for a wake)')
    ap.add_argument('--interval', type=int, default=600)
    a = ap.parse_args()
    H.mkdir(parents=True, exist_ok=True)
    led = Ledger()
    if a.once:
        poll_once(led, fast=a.fast)
        return 0
    cycle = 0
    while True:
        try:
            # the per-author channel runs every 6th cycle (~1 h); the cheap
            # global + search channels run every cycle.
            poll_once(led, fast=(cycle % 6 != 0))
            cycle += 1
        except Exception as e:  # a crash must never kill the radar
            log(f'EXCEPTION: {e!r}')
        time.sleep(a.interval)


if __name__ == '__main__':
    raise SystemExit(main())
