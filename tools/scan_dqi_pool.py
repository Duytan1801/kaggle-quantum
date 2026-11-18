#!/usr/bin/env python3
"""scan_dqi_pool.py — index every DQI candidate inside the harvested public portfolios.

Streams each candidate (decompressing .xz on the fly), reads the .kmb header for
qubits / ops / static-Toffoli, and computes the SHA-256 of the *decompressed*
bytes (i.e. of the bytes that would actually be submitted).
"""
import glob
import hashlib
import io
import json
import lzma
import os
import pathlib
import struct
import zipfile

POOL = pathlib.Path('/tmp/opencode/pool')
OUT = pathlib.Path('/tmp/opencode/pool_index.json')


def kmb_header(head: bytes):
    # 16-byte magic + <4I9Q> payload
    try:
        h = struct.unpack_from('<4I9Q', head, 16)
    except struct.error:
        return None
    # h = (magic0..3, qubits, num_bits, ?, n_ops, static_toffoli, ...)
    return {"qubits": h[1], "num_bits": h[2], "n_ops": h[4], "static_toffoli": h[5]}


def scan_stream(fh, label, source):
    h = hashlib.sha256()
    size = 0
    header = b""
    while True:
        chunk = fh.read(1 << 22)
        if not chunk:
            break
        if len(header) < 128:
            header += chunk[:128]
        h.update(chunk)
        size += len(chunk)
    hdr = kmb_header(header)
    if hdr is None:
        return None
    return {"sha256": h.hexdigest(), "bytes": size, "label": label,
            "source": source, **hdr}


index = {}
for zpath in sorted(POOL.rglob('*.zip')):
    source = zpath.parent.name
    try:
        z = zipfile.ZipFile(zpath)
    except Exception as e:
        print("BAD ZIP", zpath, e)
        continue
    for info in z.infolist():
        if info.is_dir():
            continue
        name = info.filename
        low = name.lower()
        if not (low.endswith('.kmb') or low.endswith('.kmb.xz')):
            continue
        # keep only dqi-looking circuits (name mentions dqi, or it is the top-level dqi.kmb)
        base = os.path.basename(low)
        if 'dqi' not in low and base != 'dqi.kmb' and base != 'dqi.kmb.xz':
            continue
        try:
            raw = z.open(info)
            if low.endswith('.xz'):
                fh = lzma.LZMAFile(io.BytesIO(raw.read()))
                rec = scan_stream(fh, name, source)
            else:
                rec = scan_stream(raw, name, source)
        except Exception as e:
            print("ERR", source, name, repr(e)[:100])
            continue
        if not rec:
            continue
        sha = rec["sha256"]
        if sha in index:
            index[sha]["also_in"].append(f"{source}:{name}")
        else:
            rec["also_in"] = []
            index[sha] = rec

OUT.write_text(json.dumps(index, indent=1))
rows = sorted(index.values(), key=lambda r: r["static_toffoli"])
print(f"distinct DQI candidates: {len(rows)}")
print(f"{'sha12':<14}{'q':>5}{'static':>9}{'ops':>11}{'bytes':>11}  source")
for r in rows:
    print(f"{r['sha256'][:12]:<14}{r['qubits']:>5}{r['static_toffoli']:>9}{r['n_ops']:>11}{r['bytes']:>11}  {r['source']} :: {r['label']}")
print("\nwritten:", OUT)
