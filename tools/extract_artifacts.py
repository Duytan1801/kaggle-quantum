#!/usr/bin/env python3
"""extract_artifacts.py — pull every circuit artifact out of a pulled Kaggle notebook.

Public notebooks in this competition ship their circuits in three ways:
  * a base64 blob (often zlib- or lzma-compressed, sometimes a zip),
  * a dataset reference plus a sha256,
  * an attached dataset (not visible from the notebook source).

This script walks a directory of .ipynb files, decodes every base64 blob it can,
unpacks zips, and reports every kickmix `.kmb` (magic `d750c7d5c329d326e3cc9f6834f2b8bf`)
and every numpy `.npz` it finds, with sha256, size and the circuit's declared qubit count.
That is what lets us react to a public release within minutes instead of hours.

Usage: extract_artifacts.py <dir> [--out DIR] [--min-bytes 1000]
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import io
import json
import lzma
import pathlib
import re
import struct
import sys
import zipfile
import zlib

MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
B64 = re.compile(r"[A-Za-z0-9+/]{400,}={0,2}")


def kmb_info(data: bytes) -> dict:
    """num_qubits / num_bits / op count from the kickmix binary header."""
    if not data.startswith(MAGIC):
        return {}
    try:
        h = struct.unpack_from("<4I9Q", data, 16)
    except struct.error:
        return {}
    return {'qubits': h[1], 'num_bits': h[2], 'flags': h[3],
            'n_ops': h[4], 'n_static_toffoli': h[5]}


def try_decode(blob: str) -> list[bytes]:
    out = []
    try:
        raw = base64.b64decode(blob, validate=False)
    except (binascii.Error, ValueError):
        return out
    out.append(raw)
    for dec in (zlib.decompress, lzma.decompress):
        try:
            out.append(dec(raw))
        except Exception:
            pass
    return out


FOUND_BYTES: dict = {}


def scan_bytes(data: bytes, origin: str, found: dict, depth=0):
    if data.startswith(MAGIC):
        h = hashlib.sha256(data).hexdigest()
        found[h] = ('kmb', len(data), origin, kmb_info(data))
        FOUND_BYTES[h] = data
        return
    if data[:2] == b'PK' and depth < 3:
        try:
            z = zipfile.ZipFile(io.BytesIO(data))
        except Exception:
            return
        for n in z.namelist():
            try:
                scan_bytes(z.read(n), f'{origin}!{n}', found, depth + 1)
            except Exception:
                continue
        return
    if data[:6] == b'\x93NUMPY':
        h = hashlib.sha256(data).hexdigest()
        found[h] = ('npy', len(data), origin, {})
        FOUND_BYTES[h] = data
        return
    if data[:2] == b'\x78\x9c' or data[:2] == b'\x78\x01':
        try:
            scan_bytes(zlib.decompress(data), origin, found, depth + 1)
        except Exception:
            pass


def main():
    root = pathlib.Path(sys.argv[1])
    outdir = None
    if '--out' in sys.argv:
        outdir = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])
        outdir.mkdir(parents=True, exist_ok=True)
    min_bytes = 1000
    if '--min-bytes' in sys.argv:
        min_bytes = int(sys.argv[sys.argv.index('--min-bytes') + 1])
    found: dict = {}
    shas: set = set()
    for nb_path in sorted(root.rglob('*.ipynb')):
        try:
            nb = json.loads(nb_path.read_text())
        except Exception:
            continue
        text = nb_path.read_text()
        for s in re.findall(r'\b[0-9a-f]{64}\b', text):
            shas.add(s)
        for m in B64.finditer(text):
            blob = m.group(0)
            for cand in try_decode(blob):
                if len(cand) >= min_bytes:
                    scan_bytes(cand, f'{nb_path.name}:blob', found)
    for sha, (kind, size, origin, info) in sorted(found.items(), key=lambda kv: -kv[1][1]):
        line = f'{kind:4} {sha[:16]} {size:>12} {origin} {info}'
        print(line, flush=True)
        if outdir:
            (outdir / f'{sha}.{kind}').write_bytes(FOUND_BYTES[sha])
    print(f'--- saved {len(found)} artifacts to {outdir}' if outdir else f'--- {len(found)} artifacts')
    if shas:
        print(f'--- {len(shas)} sha256 strings mentioned in the notebooks')
        for s in sorted(shas)[:40]:
            print('   sha', s[:16])


if __name__ == '__main__':
    main()
