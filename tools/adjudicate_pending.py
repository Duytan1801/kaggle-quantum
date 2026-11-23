#!/usr/bin/env python3
"""Pull every PENDING release and compare any 18-file tree to v144/v145.

This is the audit half of queue adjudication: queue_sweep.py already classifies
refs mechanically, but the wake contract requires a measured verdict for every
row.  This tool downloads each pending kernel OUTPUT / dataset, finds candidate
trees, and prints an exact member-level comparison against the current best
trees so a row can be closed with evidence.

It never edits PENDING/ADOPTED; it emits a review TSV on stdout.
"""
from __future__ import annotations

import concurrent.futures as cf
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
H = ROOT / 'work/harvest'
WORK = pathlib.Path('/tmp/opencode/adjudicate')
V145 = ROOT / 'work/trees/v145_ozertuu_33170350'
V144 = ROOT / 'work/trees/v144_leotang_chem_refit'
NEEDED = ['invsqrt.kmb', 'dqi.kmb', 'dfthcsos/submission.npz']
V145_H = json.loads((ROOT / 'work/sha_tables/sha_table_v145.txt').read_text())['files']
V144_H = json.loads((ROOT / 'work/sha_tables/sha_table_v144.txt').read_text())['files']


def digest(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree_hash(root: pathlib.Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): digest(p)
            for p in root.rglob('*') if p.is_file()}


def find_trees(root: pathlib.Path) -> list[pathlib.Path]:
    hits = []
    # canonical layout: <root>/dfthcsos/{submission.npz,angle_k_*.kmb}
    for p in root.rglob('dfthcsos/submission.npz'):
        hits.append(p.parent.parent)
    for p in root.rglob('submission.npz'):
        parent = p.parent
        if parent.name == 'dfthcsos':
            hits.append(parent.parent)
        elif (parent / 'angle_k_0.kmb').is_file():
            hits.append(parent)
    # flat dataset layouts (dfthcsos__submission.npz)
    for p in root.rglob('dfthcsos__submission.npz'):
        hits.append(p.parent)
    return sorted(set(hits))


def norm(paths: dict[str, str]) -> dict[str, str]:
    out = {}
    for k, v in paths.items():
        if k.endswith('dfthcsos__submission.npz'):
            k = 'dfthcsos/submission.npz'
        elif k.startswith('dfthcsos__'):
            k = 'dfthcsos/' + k[len('dfthcsos__'):]
        out[k] = v
    return out


def pull(kind: str, ref: str) -> str | None:
    d = WORK / ref.replace('/', '__')
    cached = d.exists() and any(p.is_file() for p in d.rglob('*'))
    if not cached:
        if d.exists():
            shutil.rmtree(d)
        d.mkdir(parents=True)
        if kind == 'kernel':
            cmd = ['kaggle', 'kernels', 'output', ref, '-p', str(d), '--force']
        else:
            cmd = ['kaggle', 'datasets', 'download', '-d', ref, '-p', str(d),
                   '--force', '--unzip']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        if r.returncode != 0:
            return 'pull-failed: ' + (r.stderr or r.stdout).strip().splitlines()[-1][:160]
    # Candidate trees are published inside submission.zip; extract every archive.
    import zipfile
    for z in list(d.glob('*.zip')):
        out = d / (z.stem + '__extracted')
        if out.exists():
            continue
        try:
            with zipfile.ZipFile(z) as zf:
                zf.extractall(out)
        except zipfile.BadZipFile:
            continue
    return None


def audit(kind: str, ref: str) -> tuple[str, str]:
    err = pull(kind, ref)
    d = WORK / ref.replace('/', '__')
    if err:
        return ref, err
    files = [p for p in d.rglob('*') if p.is_file()]
    if not files:
        return ref, 'empty download'
    trees = find_trees(d)
    if not trees:
        return ref, f'no tree (files={len(files)})'
    best = None
    notes = []
    for t in trees:
        h = norm(tree_hash(t))
        if not set(NEEDED) <= set(h):
            notes.append(f'{t.name}: partial ({len(h)} files)')
            continue
        n145 = sum(1 for k, v in h.items() if V145_H.get(k, ('',))[0] == v)
        n144 = sum(1 for k, v in h.items() if V144_H.get(k, ('',))[0] == v)
        rec = (n145, n144, len(h), t.as_posix(), h)
        if best is None or rec[:4] > best[:4]:
            best = rec
    if best is None:
        return ref, '; '.join(notes)[:180] or 'no complete 18-file tree'
    n145, n144, n, where, h = best
    if n145 == 18:
        verdict = 'duplicate-of-v145'
    elif n144 == 18:
        verdict = 'duplicate-of-v144'
    else:
        changed = [k for k in sorted(h) if V145_H.get(k, ('',))[0] != h[k]]
        verdict = (f'candidate dir={where[len(str(d))+1:] or "."} '
                   f'files={n} same_v145={n145} same_v144={n144} '
                   f'changed={changed}')
    return ref, verdict


def main() -> int:
    rows = [l.split('\t') for l in (H / 'PENDING.tsv').read_text().splitlines() if l.strip()]
    WORK.mkdir(parents=True, exist_ok=True)
    out = []
    with cf.ThreadPoolExecutor(max_workers=2) as ex:
        futs = {ex.submit(audit, r[0], r[1]): r for r in rows}
        for f in cf.as_completed(futs):
            r = futs[f]
            try:
                ref, verdict = f.result()
            except Exception as e:  # noqa: BLE001
                ref, verdict = f'{r[0]}\t{r[1]}', f'error: {type(e).__name__}: {e}'
            out.append(f'{r[0]}\t{ref}\t{verdict}')
            print(f'{r[0]}\t{ref}\t{verdict}', flush=True)
    (H / 'ADJUDICATION_REVIEW.tsv').write_text('\n'.join(sorted(out)) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
