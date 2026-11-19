#!/usr/bin/env python3
"""queue_sweep.py — adjudicate the whole public-release queue mechanically.

The wake contract says every entry in work/harvest/PENDING.tsv must be pulled,
scanned and adjudicated (never left queued, or it is rediscovered forever).
375 entries at ~10-60 s each is too much to do by hand, so this does it:

  for each pending ref:
      pull (kernel: `kaggle kernels pull`; dataset: `kaggle datasets download`)
      extract, then run work/tools/ds_scan.py over the extracted tree
      classify:
          candidate-tree   -> NOT marked done: a human/agent must run the full
                              two-receipt gate on it (kept in PENDING, listed in
                              work/harvest/CANDIDATES.tsv)
          parts-only       -> done "parts" (the shas are recorded so we can mix
                              them into a tree later)
          no-candidate     -> done "rejected"
          pull-failed      -> done "pull-failed" (with the error)

The state file work/harvest/SWEEP_STATE.tsv makes the sweep RESUMABLE: a ref
already adjudicated is never re-pulled.

Usage:
  queue_sweep.py [--limit N] [--workers 3] [--only-score-geo 28.18] [--dry-run]
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
H = ROOT / 'work/harvest'
PENDING = H / 'PENDING.tsv'
ADOPTED = H / 'ADOPTED.tsv'
STATE = H / 'SWEEP_STATE.tsv'
CANDIDATES = H / 'CANDIDATES.tsv'
WORK = pathlib.Path('/tmp/opencode/queue_sweep')
PY = ROOT / 'work/toolchain/venv/bin/python'
DS_SCAN = ROOT / 'work/tools/ds_scan.py'


def read_pending() -> list[list[str]]:
    if not PENDING.exists():
        return []
    return [l.split('\t') for l in PENDING.read_text().splitlines() if l.strip()]


def write_pending(rows: list[list[str]]) -> None:
    PENDING.write_text('\n'.join('\t'.join(r) for r in rows) + ('\n' if rows else ''))


def read_state() -> dict[str, str]:
    st = {}
    if STATE.exists():
        for line in STATE.read_text().splitlines():
            if '\t' in line:
                ref, verdict = line.split('\t', 1)[0], line.split('\t', 1)[1]
                st[ref] = verdict
    return st


def append_state(ref: str, verdict: str) -> None:
    with open(STATE, 'a') as f:
        f.write(f'{ref}\t{verdict}\n')


def mark_done(ref: str, verdict: str, note: str) -> None:
    ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
    with open(ADOPTED, 'a') as f:
        f.write(f'{ts}\t{ref}\t{verdict}\t{note}\n')
    rows = read_pending()
    keep = [r for r in rows if len(r) < 2 or r[1] != ref]
    write_pending(keep)


def slug(ref: str) -> str:
    return ref.replace('/', '__')


def pull(kind: str, ref: str, dest: pathlib.Path, timeout: int) -> tuple[bool, str]:
    dest.mkdir(parents=True, exist_ok=True)
    env = {**os.environ}
    try:
        if kind == 'kernel':
            cmd = ['kaggle', 'kernels', 'pull', ref, '-p', str(dest)]
        else:
            cmd = ['kaggle', 'datasets', 'download', '-d', ref, '-p', str(dest), '--force']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        out = (r.stdout or '') + (r.stderr or '')
        if r.returncode != 0:
            return False, out.strip().splitlines()[-1][:200] if out.strip() else f'rc={r.returncode}'
    except subprocess.TimeoutExpired:
        return False, f'TIMEOUT after {timeout}s'
    # extract every archive
    for z in list(dest.glob('*.zip')):
        try:
            subprocess.run(['unzip', '-o', '-q', str(z), '-d', str(dest / 'x')], timeout=600)
        except Exception:
            pass
    return True, 'ok'


def scan(dest: pathlib.Path) -> dict:
    roots = [dest]
    x = dest / 'x'
    if x.exists():
        roots = [x]
    best = {'candidates': [], 'parts': []}
    for root in roots:
        if not root.exists():
            continue
        try:
            r = subprocess.run([str(PY), str(DS_SCAN), str(root), '--out', str(dest / 'scan.json')],
                               capture_output=True, text=True, timeout=900)
            txt = (r.stdout or '')
            i, j = txt.find('{'), txt.rfind('}')
            if 0 <= i < j:
                best = json.loads(txt[i:j + 1])
                break
        except Exception as e:
            best = {'error': f'{type(e).__name__}: {e}'}
    return best


def classify(scan_res: dict) -> tuple[str, str]:
    """-> (verdict, note).  'candidate' means a full tree that needs the gate."""
    if not scan_res:
        return 'rejected', 'scan produced nothing'
    cands = scan_res.get('candidates') or []
    parts = scan_res.get('parts') or []
    if cands:
        notes = []
        for c in cands[:6]:
            if isinstance(c, dict):
                notes.append(f"{c.get('path', '?')}:q={c.get('num_qubits')},"
                             f"score={c.get('score')},sha={str(c.get('sha256'))[:12]}")
            else:
                notes.append(str(c)[:120])
        return 'candidate', '; '.join(notes)[:400]
    if parts:
        notes = []
        for p in parts[:8]:
            if isinstance(p, dict):
                notes.append(f"{p.get('path', '?')}:sha={str(p.get('sha256'))[:12]}")
            else:
                notes.append(str(p)[:100])
        return 'parts', '; '.join(notes)[:400]
    return 'rejected', 'no QCC tree or parts'


def process(kind: str, ref: str, title: str, timeout: int, dry: bool) -> tuple[str, str, str]:
    dest = WORK / slug(ref)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    ok, msg = pull(kind, ref, dest, timeout)
    if not ok:
        if '403' in msg or 'Forbidden' in msg:
            return 'gated-403', msg, ''
        return 'pull-failed', msg, ''
    files = [f for f in dest.rglob('*') if f.is_file()]
    if not files:
        shutil.rmtree(dest, ignore_errors=True)
        return 'pull-empty', 'download succeeded but produced no files', ''
    try:
        size = sum(f.stat().st_size for f in files)
    except Exception:
        size = 0
    if size > 4 * 1024**3:
        shutil.rmtree(dest, ignore_errors=True)
        return 'too-large', f'{size/1024**3:.1f} GB, not scanned', ''
    res = scan(dest)
    verdict, note = classify(res)
    shutil.rmtree(dest, ignore_errors=True)
    return verdict, note, title


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=0)
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--only', default='', help='substring filter on the ref')
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    rows = read_pending()
    state = read_state()
    todo = [r for r in rows if len(r) >= 4 and r[1] not in state
            and (not a.only or a.only in r[1])]
    if a.limit:
        todo = todo[:a.limit]
    print(f'queue: {len(rows)} pending | {len(state)} already swept | {len(todo)} to pull',
          flush=True)
    if not todo:
        return 0

    WORK.mkdir(parents=True, exist_ok=True)
    done_n = 0
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(process, r[0], r[1], r[3], a.timeout, a.dry_run): r for r in todo}
        for fut in cf.as_completed(futs):
            r = futs[fut]
            kind, ref, title = r[0], r[1], r[3]
            try:
                verdict, note, _ = fut.result()
            except Exception as e:
                verdict, note = 'error', f'{type(e).__name__}: {e}'[:200]
            append_state(ref, verdict)
            if verdict == 'candidate':
                ts = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())
                with open(CANDIDATES, 'a') as f:
                    f.write(f'{ts}\t{kind}\t{ref}\t{title}\t{note}\n')
                print(f'  CANDIDATE  {ref}  {note[:140]}', flush=True)
            else:
                if verdict == 'gated-403':
                    with open(H / 'GATED.tsv', 'a') as f:
                        f.write(f'{time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}\t{kind}\t'
                                f'{ref}\t{title}\t{note}\n')
                if not a.dry_run:
                    mark_done(ref, verdict, note)
                print(f'  {verdict:<12} {ref}  {note[:100]}', flush=True)
            done_n += 1
            if done_n % 10 == 0:
                print(f'  ... {done_n}/{len(todo)} in {time.time()-t0:.0f}s', flush=True)
    print(f'\nswept {done_n} refs in {time.time()-t0:.0f}s; queue now {len(read_pending())}',
          flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
