#!/usr/bin/env python3
"""loader_compat.py — which public chemistry loader is compatible with which npz?

The chemistry task ships 15 "angle loaders" (one per block of 5 columns of the
angle-word table) plus a `submission.npz` that holds the table itself.  A loader
may only be swapped for another loader if it computes the SAME function of the
11-bit address: the npz's `angle_words` table fixes the truth table, and a
loader that encodes a different table silently corrupts the chemistry (we saw
error_1 = 9232 mHa for an incompatible k=14 swap).

This script, for every candidate loader file, simulates the loader on all 2048
addresses with the UNCHANGED kickmix Simulator and matches its 35 output bits
against the npz's angle-word columns.  A loader is COMPATIBLE with an npz iff
all 35 bits match for every valid address (< len(angle_words)).

Usage:
  PYTHONPATH=<kickmix> python loader_compat.py <npz> <loader_dir> [label]
"""
from __future__ import annotations

import collections
import io
import pathlib
import re
import sys

import numpy as np

import kickmix as km

REG_RE = re.compile(r'^REGISTER\s+(\S+)\s+"(.*)"$')
APP_RE = re.compile(r'^APPEND_TO_REGISTER\s+q(\d+)\s+(\S+)$')


def parse_layout(path: pathlib.Path):
    lines = path.read_text().splitlines()
    regs = []
    cur_name = None
    pending = []
    for l in lines:
        if l.startswith('APPEND_TO_REGISTER'):
            m = APP_RE.match(l)
            pending.append((int(m.group(1)), m.group(2)))
            continue
        if l.startswith('REGISTER'):
            m = REG_RE.match(l)
            cur_name = m.group(1)
            regs.append((m.group(2), [q for q, r in pending if r == cur_name]))
            pending = []
            continue
        if l.strip():
            break
    addr = regs[0][1]
    words = [(lab, qs) for lab, qs in regs if lab.startswith('word_')]
    words.sort(key=lambda t: int(t[0].split('_')[1]))
    wq = [q for _, qs in words for q in qs]
    return addr, wq


def truth_table(path: pathlib.Path, addr, outs):
    circuit = km.Circuit.from_file(str(path), format='kmb')
    n_addr = len(addr)
    total = 1 << n_addr
    batch = 512
    addrs = np.arange(total, dtype=np.int64)
    sim = km.Simulator(batch_size=batch, debug_print=False, counting_operations=False)
    vals = np.zeros((total, len(outs)), dtype=np.uint8)
    for start in range(0, total, batch):
        stop = min(start + batch, total)
        xs = addrs[start:stop]
        sim.clear_for_shot()
        bits = ((xs[:, None] >> np.arange(n_addr, dtype=np.int64)[None, :]) & 1).astype(bool).T
        sim.write_across_shots(km.array([km.q(q) for q in addr]), bits)
        sim.do(circuit)
        got = sim.read_across_shots(km.array([km.q(q) for q in outs]))
        for j in range(len(outs)):
            vals[start:stop, j] = got[j].astype(np.uint8)
    return vals


def col_bits(words: np.ndarray) -> np.ndarray:
    """(rows, 75) of 7-bit values -> (rows, 75, 7) bit vectors (LSB first)."""
    b = np.zeros(words.shape + (7,), dtype=np.uint8)
    for i in range(7):
        b[..., i] = (words >> i) & 1
    return b


def main() -> None:
    npz_path = pathlib.Path(sys.argv[1])
    loader_dir = pathlib.Path(sys.argv[2])
    label = sys.argv[3] if len(sys.argv) > 3 else loader_dir.name
    z = np.lib.npyio.NpzFile(npz_path) if False else None
    import zipfile
    zz = zipfile.ZipFile(npz_path)
    aw = np.load(io.BytesIO(zz.read('angle_words.npy')))
    rows = aw.shape[0]
    cb = col_bits(aw)                     # (rows, 75, 7)
    cbr = cb[..., ::-1]                    # MSB-first variant

    files = sorted(loader_dir.glob('angle_k_*.kmb'),
                   key=lambda p: int(re.search(r'angle_k_(\d+)', p.name).group(1)))
    print(f'== {label}: npz {npz_path.name} (angle_words {aw.shape}) ==')
    for p in files:
        k = int(re.search(r'angle_k_(\d+)', p.name).group(1))
        addr, wq = parse_layout(p) if p.suffix == '.kmx' else (None, None)
        if addr is None:
            circuit = km.Circuit.from_file(str(p), format='kmb')
            s = io.BytesIO()
            circuit.to_file(s, format='kmx')
            tmp = pathlib.Path('/tmp/opencode/_compat_tmp.kmx')
            tmp.write_bytes(s.getvalue())
            addr, wq = parse_layout(tmp)
        tt = truth_table(p, addr, wq)[:rows]        # (rows, 35)
        nwords = len(wq) // 7
        mapping, ok = [], True
        used = set()
        for j in range(nwords):
            blk = tt[:, 7 * j:7 * j + 7]
            hit = None
            for c in range(cb.shape[1]):
                if c in used:
                    continue
                if np.array_equal(blk, cb[:, c, :]):
                    hit = (c, 'lsb')
                    break
                if np.array_equal(blk, cbr[:, c, :]):
                    hit = (c, 'msb')
                    break
            if hit is None:
                ok = False
                mapping.append(None)
            else:
                used.add(hit[0])
                mapping.append(hit)
        print(f'  k={k:<3} compatible={ok}  mapping={mapping}')


if __name__ == '__main__':
    main()
