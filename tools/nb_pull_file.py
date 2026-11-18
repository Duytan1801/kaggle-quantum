#!/usr/bin/env python3
"""nb_pull_file.py — extract an embedded artifact from a notebook by sha256 prefix.

Walks every code/output cell, collects base64 blobs (possibly wrapped across lines),
decodes (raw / zlib / lzma / zip-in-base64), recursively unpacks zips, and writes the
first blob whose sha256 starts with the wanted prefix into OUTDIR.

Usage: nb_pull_file.py <notebook.ipynb> <sha256-prefix> <outdir> [--name NAME]
"""
from __future__ import annotations

import sys
import base64
import hashlib
import io
import json
import lzma
import pathlib
import re
import zipfile
import zlib

B64 = re.compile(r"[A-Za-z0-9+/=]{200,}")


def try_decode(blob: str):
    raw = base64.b64decode(re.sub(r'\s+', '', blob), validate=False)
    yield raw
    for dec in (zlib.decompress, lzma.decompress):
        try:
            yield dec(raw)
        except Exception:
            pass
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        for n in z.namelist():
            try:
                yield z.read(n)
            except Exception:
                pass
    except Exception:
        pass


def main() -> None:
    nb_path, want, outdir = pathlib.Path(sys.argv[1]), sys.argv[2].lower(), pathlib.Path(sys.argv[3])
    name = None
    if '--name' in sys.argv:
        name = sys.argv[sys.argv.index('--name') + 1]
    outdir.mkdir(parents=True, exist_ok=True)
    nb = json.loads(nb_path.read_text())
    seen = 0
    for ci, cell in enumerate(nb['cells']):
        sources = [''.join(cell.get('source') or [])]
        for o in cell.get('outputs') or []:
            d = o.get('data') or {}
            for k, v in d.items():
                if isinstance(v, list):
                    sources.append(''.join(v))
                elif isinstance(v, str):
                    sources.append(v)
            txt = o.get('text')
            if isinstance(txt, list):
                sources.append(''.join(txt))
            elif isinstance(txt, str):
                sources.append(txt)
        for src in sources:
            for m in B64.finditer(src):
                blob = m.group(0)
                for cand in try_decode(blob):
                    seen += 1
                    h = hashlib.sha256(cand).hexdigest()
                    if h.startswith(want):
                        out = outdir / (name or h[:16])
                        out.write_bytes(cand)
                        print(f'FOUND cell {ci}: sha {h} ({len(cand)} bytes) -> {out}')
                        if name is None or out.name == name:
                            return
    print(f'no blob matched {want} ({seen} candidates decoded)')


if __name__ == '__main__':
    main()
