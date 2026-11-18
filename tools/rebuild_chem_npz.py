#!/usr/bin/env python3
"""rebuild_chem_npz.py — reconstruct a chemistry weights npz published as parent XOR delta.

Atakan Aldemir's kernel embeds DELTA64 (lzma+base64); the published npz is
    bytes(parent) XOR delta
where parent is the 1,847,692-byte Lera npz (f6e12f02...).

Usage: rebuild_chem_npz.py <notebook.ipynb> <parent.npz> <out.npz> <expected_sha256>
"""
from __future__ import annotations

import sys
import base64
import hashlib
import json
import lzma
import pathlib
import re

nb_path, parent_path, out_path, want = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].lower()
nb = json.loads(pathlib.Path(nb_path).read_text())
blob = None
for cell in nb['cells']:
    src = ''.join(cell.get('source') or [])
    m = re.search(r"DELTA64\s*=\s*'([A-Za-z0-9+/=]+)'", src)
    if m:
        blob = m.group(1)
        break
if blob is None:
    raise SystemExit('DELTA64 not found')
delta = lzma.decompress(base64.b64decode(blob))
parent = pathlib.Path(parent_path).read_bytes()
print('parent', len(parent), hashlib.sha256(parent).hexdigest()[:12])
print('delta ', len(delta))
assert len(delta) == len(parent), (len(delta), len(parent))
out = bytes(a ^ b for a, b in zip(parent, delta))
h = hashlib.sha256(out).hexdigest()
print('result', len(out), h)
assert h == want, f'expected {want}'
pathlib.Path(out_path).write_bytes(out)
print('WROTE', out_path)
