#!/usr/bin/env python3
"""ds_headers.py — fetch only the *header* of every file of a Kaggle dataset.

A dqi .kmb is ~490 MB and there are 99 of them in the public mirror (48 GB).  We do
not need the whole file to rank them: the kickmix header carries the qubit count,
the bit count, the op count and the static Toffoli count, and the dqi cost is

    score = rep(eps_plus) * Q^2 * T_mean

with `rep` at its floor (1.19126) for any file with zero verification errors.  So
(Q, static Toffoli) ranks the candidates; the winners are then downloaded whole and
verified with the official verifier.

The Kaggle download endpoint honours HTTP Range requests, so a 256-byte read per
file is enough.

Usage: ds_headers.py <owner/dataset> <paths.txt> <out.csv>
"""
from __future__ import annotations

import base64
import csv
import json
import pathlib
import struct
import sys
import urllib.request

MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")
CREDS = pathlib.Path.home() / '.kaggle' / 'kaggle.json'


def auth_header() -> str:
    d = json.loads(CREDS.read_text())
    return 'Basic ' + base64.b64encode(f"{d['username']}:{d['key']}".encode()).decode()


def header_of(ds: str, path: str, auth: str, retries: int = 3) -> dict:
    url = f"https://www.kaggle.com/api/v1/datasets/download/{ds}?filename={path}"
    last = None
    for _ in range(retries):
        try:
            req = urllib.request.Request(url, headers={'Authorization': auth,
                                                       'Range': 'bytes=0-255'})
            with urllib.request.urlopen(req, timeout=180) as r:
                data = r.read()
                cr = r.headers.get('Content-Range', '')
                total = int(cr.split('/')[-1]) if '/' in cr else 0
                if not data.startswith(MAGIC):
                    return {'error': 'not a kmb', 'bytes': len(data)}
                h = struct.unpack_from('<4I9Q', data, 16)
                return {'qubits': h[1], 'num_bits': h[2], 'flags': h[3],
                        'n_ops': h[4], 'static_toffoli': h[5],
                        'file_bytes': total, 'header_bytes': len(data)}
        except Exception as e:      # transient Kaggle errors are common
            last = repr(e)[:120]
    return {'error': last}


def main():
    ds = sys.argv[1]
    paths = pathlib.Path(sys.argv[2]).read_text().split()
    out = pathlib.Path(sys.argv[3])
    auth = auth_header()
    rows = list(csv.DictReader(out.open())) if out.exists() else []
    done = {r['path'] for r in rows}
    for i, p in enumerate(paths):
        if p in done:
            continue
        rec = {'path': p}
        rec.update(header_of(ds, p, auth))
        rows.append(rec)
        print(f'[{i+1}/{len(paths)}] {p} q={rec.get("qubits")} ops={rec.get("n_ops")} '
              f'toff={rec.get("static_toffoli")} bytes={rec.get("file_bytes")} '
              f'{rec.get("error","")}', flush=True)
        with out.open('w', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=sorted({k for r in rows for k in r}))
            w.writeheader()
            w.writerows(rows)


if __name__ == '__main__':
    main()
