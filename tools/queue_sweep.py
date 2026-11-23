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


def read_state() -> dict[tuple[str, str], str]:
    """State is keyed by (ref, version): the radar is VERSION-AWARE, so a
    re-uploaded dataset/kernels is a NEW release and must be swept again.

    Legacy 2-column rows (`ref\\tverdict`, no version) are read as
    (ref, '') and therefore do NOT block a row that carries a version stamp.
    """
    st: dict[tuple[str, str], str] = {}
    if STATE.exists():
        for line in STATE.read_text().splitlines():
            if '\t' not in line:
                continue
            parts = line.split('\t')
            if len(parts) >= 3:
                ref, version, verdict = parts[0], parts[1], parts[2]
            else:
                ref, version, verdict = parts[0], '', parts[1]
            # A transient error is NOT an adjudication: keep the row eligible
            # for retry instead of letting it block the queue forever.
            if verdict == 'error':
                continue
            st[(ref, version)] = verdict
    return st


def append_state(ref: str, verdict: str, version: str = '') -> None:
    with open(STATE, 'a') as f:
        f.write(f'{ref}\t{version}\t{verdict}\n')


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
    # A KERNEL publishes its tree in the kernel OUTPUT (submission.zip), not in
    # the notebook source: `kaggle kernels pull` never fetches it.  That blind
    # spot hid the best public DQI circuit (4471b493) inside
    # leotang09/vqcc-t7421-submission's output.  So fetch the output too.
    if kind == 'kernel':
        outdir = dest / 'kernel_output'
        try:
            r2 = subprocess.run(['kaggle', 'kernels', 'output', ref, '-p', str(outdir)],
                                capture_output=True, text=True, timeout=timeout, env=env)
            if r2.returncode != 0:
                print(f'  (kernel output unavailable for {ref}: '
                      f'{(r2.stderr or "").strip().splitlines()[-1][:120] if (r2.stderr or "").strip() else "rc=" + str(r2.returncode)})',
                      flush=True)
        except subprocess.TimeoutExpired:
            print(f'  (kernel output TIMEOUT for {ref})', flush=True)
    # extract every archive
    for z in list(dest.rglob('*.zip')):
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
            # --skip-score: the official invsqrt verifier needs the full
            # 200,540,928-shot run and times out under sweep load.  Triage only
            # needs the shas + qubit counts; a candidate tree is scored through
            # the full gate afterwards.
            r = subprocess.run([str(PY), str(DS_SCAN), str(root), '--out', str(dest / 'scan.json'),
                                '--skip-score'],
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
    """-> (verdict, note).  'candidate' means a full tree that needs the gate.

    ds_scan reports three collections: ``trees`` (directories containing an
    invsqrt+dqi pair), ``artifacts`` (loose circuit files) and ``subzips``.
    The old classifier looked for non-existent ``candidates``/``parts`` keys,
    so every successful scan was mislabeled 'rejected'.
    """
    if not scan_res:
        return 'error', 'scan produced nothing (retry)'
    if scan_res.get('error'):
        # ds_scan failed (usually the invsqrt verifier timed out under load).
        # This is NOT a verdict about the release: keep it queued for a retry.
        return 'error', f"scan error (retry): {scan_res['error']}"[:300]

    trees = scan_res.get('trees') or []
    cands = [t for t in trees if t.get('is_full_18')]
    parts = [t for t in trees if not t.get('is_full_18')]
    parts += scan_res.get('artifacts') or []
    parts += scan_res.get('subzips') or []

    if cands:
        notes = []
        for c in cands[:6]:
            inv = ((c.get('files') or {}).get('invsqrt.kmb') or {})
            dqi = ((c.get('files') or {}).get('dqi.kmb') or {})
            notes.append(f"dir={c.get('dir', '?')}:files={c.get('n_files')},"
                         f"invq={inv.get('qubits')},dqiq={dqi.get('qubits')},"
                         f"invsha={str(inv.get('sha256'))[:12]}")
        return 'candidate', '; '.join(notes)[:400]
    if parts:
        notes = []
        for p in parts[:8]:
            if isinstance(p, dict):
                if p.get('path'):
                    notes.append(f"{p.get('path')}:q={p.get('qubits')},"
                                 f"sha={str(p.get('sha256'))[:12]}")
                else:
                    notes.append(f"dir={p.get('dir', '?')}:files={p.get('n_files')},"
                                 f"missing={len(p.get('missing') or [])}")
            else:
                notes.append(str(p)[:100])
        return 'parts', '; '.join(notes)[:400]
    return 'rejected', 'no QCC tree or parts'


def process(kind: str, ref: str, title: str, timeout: int, dry: bool,
            size_cap_gb: float = 4.0) -> tuple[str, str, str]:
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
    if size > size_cap_gb * 1024**3:
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
    ap.add_argument('--size-cap-gb', type=float, default=4.0,
                    help='skip datasets larger than this (default 4)')
    a = ap.parse_args()

    rows = read_pending()
    state = read_state()
    todo = [r for r in rows if len(r) >= 4 and (r[1], r[5] if len(r) > 5 else '') not in state
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
        futs = {ex.submit(process, r[0], r[1], r[3], a.timeout, a.dry_run,
                                  a.size_cap_gb): r for r in todo}
        for fut in cf.as_completed(futs):
            r = futs[fut]
            kind, ref, title = r[0], r[1], r[3]
            try:
                verdict, note, _ = fut.result()
            except Exception as e:
                verdict, note = 'error', f'{type(e).__name__}: {e}'[:200]
            append_state(ref, verdict, r[5] if len(r) > 5 else '')
            if verdict == 'error':
                # transient (verifier timeout / download hiccup): do not close it
                print(f'  error        {ref}  {note[:120]}', flush=True)
            elif verdict == 'candidate':
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
