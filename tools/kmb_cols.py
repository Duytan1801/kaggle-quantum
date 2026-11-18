#!/usr/bin/env python3
"""kmb_cols.py — read/write the DQI `.kmb` column-stream format.

Layout (little-endian):
  header 104 bytes
    [0:16]  magic
    [28:32] uint32 num_registers
    [32:104] 9 x uint64 counts
  then `num_registers` register records: uint64 kind(=0), uint64 nbytes, nbytes payload
  then 11 column records: uint64 kind(1..11), uint64 nbytes, nbytes payload

  col 1 : 1 byte per op        -> op type code
  col 2 : uint32 per type-49 op -> operand 1
  col 3 : uint32 per type-49 op -> operand 2
  col 4 : uint32 per type-49 op -> operand 3 (target)
  col 5 : uint32 per type-33 op -> operand 1
  col 6 : uint32 per type-33 op -> operand 2

Only the columns a rewrite touches are materialised in RAM.
"""
import struct
from pathlib import Path

import numpy as np

MAGIC_LEN = 16
HEADER_LEN = 104
N_COLS = 11


class Kmb:
    def __init__(self, path):
        self.path = Path(path)
        with self.path.open('rb') as f:
            head = f.read(HEADER_LEN)
            self.magic = head[:MAGIC_LEN]
            self.counts = list(struct.unpack_from('<9Q', head, 32))
            nregs = struct.unpack_from('<I', head, 28)[0]
            self.regs = []
            for _ in range(nregs):
                k, n = struct.unpack('<QQ', f.read(16))
                self.regs.append((k, n, f.tell()))
                f.seek(n, 1)
            self.prefix_end = f.tell()
            self.cols = []
            for _ in range(N_COLS):
                k, n = struct.unpack('<QQ', f.read(16))
                self.cols.append((k, n, f.tell()))
                f.seek(n, 1)
            self.data_end = f.tell()
        self.size = self.path.stat().st_size

    def read_col(self, idx, dtype=None):
        """idx is the column *kind* (1..11), matching the on-disk record."""
        k, n, off = self.cols[idx - 1]
        with self.path.open('rb') as f:
            f.seek(off)
            raw = f.read(n)
        if dtype is None:
            return raw
        return np.frombuffer(raw, dtype=dtype)

    def col_bytes(self, idx):
        return self.read_col(idx)

    def summary(self):
        return {
            'counts': self.counts,
            'nregs': len(self.regs),
            'prefix_end': self.prefix_end,
            'cols': [(k, n) for k, n, _ in self.cols],
            'size': self.size,
        }


def write_patched(src: Path, dst: Path, col_updates, counts=None):
    """col_updates: {col_index: bytes}.  Rewrites the column payloads in place
    (same order, new lengths) and optionally patches the header counts."""
    k = Kmb(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + '.tmp')
    with src.open('rb') as fin, tmp.open('wb') as fout:
        head = bytearray(fin.read(HEADER_LEN))
        if counts is not None:
            struct.pack_into('<9Q', head, 32, *counts)
        fout.write(head)
        fin.seek(HEADER_LEN)
        fout.write(fin.read(k.prefix_end - HEADER_LEN))
        for idx, (kk, n, off) in enumerate(k.cols):
            kind = idx + 1
            if kind in col_updates:
                payload = col_updates[kind]
                fout.write(struct.pack('<QQ', kk, len(payload)))
                fout.write(payload)
            else:
                fin.seek(off)
                fout.write(fin.read(n))
    tmp.replace(dst)
    return dst
