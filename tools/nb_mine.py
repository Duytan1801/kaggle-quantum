#!/usr/bin/env python3
"""nb_mine.py — mine a Kaggle notebook for embedded circuit artifacts.

Public QCC notebooks embed their circuit bytes as base64(+zlib) literals and
declare the member sha table and the per-leg verifier results in markdown.
This decodes every plausible blob, hashes it, reads its qubit count with
kickmix, and pulls the declared scores out of the notebook text — so a
candidate can be judged WITHOUT downloading a 500 MB dataset.

Usage: nb_mine.py <notebook.ipynb> [--json OUT]
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import pathlib
import re
import struct
import sys
import zlib

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KICK = ROOT / 'work/toolchain/kickmix'

BLOB = re.compile(r'"([A-Za-z0-9+/=]{2000,})"')
SHA12 = re.compile(r'\b([0-9a-f]{12})\b')
SCORE = re.compile(r'\b([0-9]{1,3}(?:,[0-9]{3})*(?:\.[0-9]+)?)\b')


def kmb_qubits(raw: bytes) -> int:
    try:
        h = struct.unpack_from('<4I9Q', raw[:128], 16)
        return int(h[1])
    except Exception:
        return -1


def decode_blob(b64: str) -> bytes | None:
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return None
    if raw[:2] == b'\x78':          # zlib
        try:
            return zlib.decompress(raw)
        except Exception:
            return None
    return raw


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('nb')
    ap.add_argument('--json')
    ap.add_argument('--min-bytes', type=int, default=1000)
    a = ap.parse_args()
    p = pathlib.Path(a.nb)
    nb = json.loads(p.read_text())
    full = "\n".join("".join(c.get('source', [])) for c in nb['cells'])

    out = {'notebook': str(p), 'blobs': [], 'declared_sha12': [], 'numbers': []}
    for m in SHA12.finditer(full):
        s = m.group(1)
        if s not in out['declared_sha12']:
            out['declared_sha12'].append(s)

    seen = set()
    for m in BLOB.finditer(full):
        b64 = m.group(1)
        data = decode_blob(b64)
        if not data or len(data) < a.min_bytes:
            continue
        sha = hashlib.sha256(data).hexdigest()
        if sha in seen:
            continue
        seen.add(sha)
        q = kmb_qubits(data)
        out['blobs'].append({'sha256': sha, 'sha12': sha[:12], 'bytes': len(data),
                             'qubits': q, 'b64_len': len(b64),
                             'is_kmb': data[:4] != b'PK\x03\x04'})
        # a .npz starts with PK
        if data[:2] == b'PK':
            out['blobs'][-1]['kind'] = 'npz/zip'
        else:
            out['blobs'][-1]['kind'] = 'kmb'

    # numbers that look like verifier scores (large decimals)
    for m in re.finditer(r'(?:score|cost|Score|Cost)[^0-9]{0,20}([0-9][0-9,]{5,}(?:\.[0-9]+)?)', full):
        out['numbers'].append(m.group(1))

    print(f'== {p.name} ==')
    print(f'  declared sha12 mentions: {len(out["declared_sha12"])}')
    print(f'  embedded blobs: {len(out["blobs"])}')
    for b in out['blobs']:
        print(f"    {b['kind']:8} {b['sha12']} {b['bytes']:>10}B q={b['qubits']:>4}")
    # narrow invsqrt?
    narrow = [b for b in out['blobs'] if b['kind'] == 'kmb' and 20 <= b['qubits'] <= 46]
    if narrow:
        print('  *** NARROW invsqrt-sized candidates: ***')
        for b in narrow:
            print(f"      {b['sha12']} q={b['qubits']} bytes={b['bytes']}")
    if out['numbers']:
        print('  score-like numbers:', sorted(set(out['numbers']))[:20])
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(out, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
