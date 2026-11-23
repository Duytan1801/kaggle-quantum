#!/usr/bin/env python3
"""ds_scan.py — scan a downloaded Kaggle dataset for candidate QCC submission trees.

Competitors release their circuit trees as KAGGLE DATASETS, not as notebooks.
This scans an extracted dataset for:
  * a `submission.zip` (the competition's own zip)            -> unpack + score
  * a `QCC_RELEASE_MANIFEST.json`                             -> read the manifest
  * any 18-file tree (dfthcsos/angle_k_*.kmb + submission.npz + dqi.kmb + invsqrt.kmb)
  * loose `invsqrt*.kmb` / `dqi.kmb` / `submission.npz` artifacts

and reports, for each, the cheap facts that decide whether it is worth a full
adoption gate: qubit count, official-verifier score (invsqrt only -- dqi needs
102,400 shots and is only logged), and the exact sha256.

Usage: ds_scan.py <extracted_dir> [--out JSON]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
PY = ROOT / 'work/toolchain/venv/bin/python'
KICK = ROOT / 'work/toolchain/kickmix'
VER = ROOT / 'work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py'

NEEDED = {'dfthcsos/angle_k_%d.kmb' % k for k in range(15)} | {
    'dfthcsos/submission.npz', 'dqi.kmb', 'invsqrt.kmb'}


def sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 22), b''):
            h.update(c)
    return h.hexdigest()


def kmb_qubits(p: pathlib.Path) -> int:
    import struct
    raw = p.read_bytes()[:128]
    try:
        h = struct.unpack_from('<4I9Q', raw, 16)
        return int(h[1])
    except Exception:
        return -1


def score_invsqrt(p: pathlib.Path, timeout: int = 900):
    env = {**os.environ, 'PYTHONPATH': str(KICK)}
    try:
        r = subprocess.run(
            [str(PY), str(VER), str(p), '--shots-per-x', '1', '--batch-size', '32',
             '--max-workers', '4'],
            capture_output=True, text=True, env=env, timeout=timeout)
        out = (r.stdout or '') + '\n' + (r.stderr or '')
    except subprocess.TimeoutExpired:
        return {'status': 'TIMEOUT'}
    i, j = out.find('{'), out.rfind('}')
    try:
        d = json.loads(out[i:j + 1])
    except Exception:
        return {'status': 'UNPARSED', 'tail': out[-400:]}
    return {k: d.get(k) for k in ('status', 'score', 'num_qubits', 'toffoli_count',
                                  'rotation_count', 'rotation_eps',
                                  'worst_error_over_tolerance', 'verified_shots')}


def find_trees(root: pathlib.Path):
    """Yield (rel_dir, {relpath: Path}) for every directory that holds a full tree."""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        names = set(filenames)
        if 'invsqrt.kmb' in names and 'dqi.kmb' in names:
            base = pathlib.Path(dirpath)
            files = {}
            for r, _, fs in os.walk(base):
                for n in fs:
                    p = pathlib.Path(r) / n
                    files[str(p.relative_to(base)).replace(os.sep, '/')] = p
            out.append((str(base.relative_to(root)), files))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--out')
    ap.add_argument('--skip-score', action='store_true')
    a = ap.parse_args()
    root = pathlib.Path(a.dir)
    report = {'root': str(root), 'trees': [], 'artifacts': [], 'subzips': []}

    # 1. nested submission.zip files
    for p in root.rglob('submission.zip'):
        report['subzips'].append({'path': str(p.relative_to(root)),
                                  'bytes': p.stat().st_size,
                                  'sha256': sha256(p)})

    # 2. full trees
    for rel, files in find_trees(root):
        have = set(files)
        entry = {'dir': rel, 'n_files': len(files),
                 'is_full_18': NEEDED.issubset(have),
                 'missing': sorted(NEEDED - have)[:20],
                 'files': {}}
        for name, p in sorted(files.items()):
            e = {'bytes': p.stat().st_size, 'sha256': sha256(p)}
            if name.endswith('.kmb'):
                e['qubits'] = kmb_qubits(p)
                if name == 'invsqrt.kmb' and not a.skip_score:
                    e['official_verifier'] = score_invsqrt(p)
            entry['files'][name] = e
        report['trees'].append(entry)

    # 3. loose invsqrt-looking artifacts not inside a tree
    tree_files = {p for _, fs in find_trees(root) for p in fs.values()}
    for p in root.rglob('*.kmb'):
        if p in tree_files:
            continue
        q = kmb_qubits(p)
        e = {'path': str(p.relative_to(root)), 'bytes': p.stat().st_size,
             'sha256': sha256(p), 'qubits': q}
        if 20 <= q <= 80 and not a.skip_score:
            e['official_verifier'] = score_invsqrt(p)
        report['artifacts'].append(e)

    text = json.dumps(report, indent=1)
    if a.out:
        pathlib.Path(a.out).write_text(text + '\n')
    # Print the COMPLETE JSON document.  The old 6,000-character truncation
    # made stdout impossible to parse and silently turned every dataset scan
    # into a queue error.
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
