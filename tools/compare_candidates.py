#!/usr/bin/env python3
"""Compare every adjudicated candidate tree against v144/v145 member by member.

Prints, for each pending ref with a complete 18-file tree: the DQI member
SHA + header op count, the chemistry table SHA, and the number of members
shared with v145.  This turns "candidate" into a measured comparison.
"""
from __future__ import annotations

import hashlib
import pathlib
import struct
import sys

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
WORK = pathlib.Path('/tmp/opencode/adjudicate')
V145 = ROOT / 'work/trees/v145_ozertuu_33170350'
V144 = ROOT / 'work/trees/v144_leotang_chem_refit'


def sha(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def kmb_ops(p: pathlib.Path) -> int | None:
    """Header op count of a .kmb (little-endian u64 at offset 40)."""
    b = p.read_bytes()[:64]
    if len(b) < 48:
        return None
    return struct.unpack_from('<Q', b, 40)[0]


def main() -> int:
    v145 = {p.relative_to(V145).as_posix(): sha(p) for p in V145.rglob('*') if p.is_file()}
    v144 = {p.relative_to(V144).as_posix(): sha(p) for p in V144.rglob('*') if p.is_file()}
    print(f'{"ref":70} {"dqi_ops":>8} {"dqi_sha":>10} {"chem_npz_sha":>12} {"same145":>7} {"same144":>7}')
    rows = []
    for d in sorted(WORK.iterdir()):
        trees = []
        for cand in (d / 'submission__extracted', d):
            if (cand / 'dqi.kmb').is_file() and (cand / 'invsqrt.kmb').is_file():
                trees.append(cand)
        for t in trees:
            files = {p.relative_to(t).as_posix(): sha(p) for p in t.rglob('*') if p.is_file()}
            if 'dqi.kmb' not in files:
                continue
            ops = kmb_ops(t / 'dqi.kmb')
            n145 = sum(1 for k, v in files.items() if v145.get(k) == v)
            n144 = sum(1 for k, v in files.items() if v144.get(k) == v)
            rows.append((d.name, ops, files['dqi.kmb'][:10],
                         files.get('dfthcsos/submission.npz', '?')[:12], n145, n144,
                         t.as_posix()))
    for r in sorted(rows):
        print(f'{r[0]:70} {str(r[1]):>8} {r[2]:>10} {r[3]:>12} {r[4]:>7} {r[5]:>7}  {r[6]}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
