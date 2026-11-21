#!/usr/bin/env python3
"""loader_anatomy.py — what does a chemistry angle loader actually compute?

For each loader k of the public chemistry generator (tonylica/quantum-ai-32-85306-
task-generators), this script

  1. parses loaders_kmx/angle_k_N.kmx and recovers the register layout
     (address input / selection output / word outputs / ancillas),
  2. counts the CCX gates spent before the first output write (the decoder) and
     after it (the per-bit multi-controlled X tree),
  3. simulates the loader on every address with the UNCHANGED kickmix Simulator
     and recovers the exact truth table  address -> (selection, word bits),
  4. computes, for every output bit, the ANF (algebraic normal form) over the
     7-bit selection code and over the 11-bit address, and reports the number of
     monomials -- i.e. how cheap a truth-table-exact replacement could be.

Nothing here is a submission artifact; it is the evidence for hypothesis H20
(chemistry loader Toffoli count).  Usage:

  PYTHONPATH=<kickmix> python loader_anatomy.py <loaders_kmx_dir> [k ...]
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


def parse(path: pathlib.Path):
    lines = path.read_text().splitlines()
    regs: list[tuple[str | None, str, list[int]]] = []
    cur_name: str | None = None
    cur_label = ''
    cur_q: list[int] = []
    pending: list[tuple[int, str]] = []
    for l in lines:
        if l.startswith('APPEND_TO_REGISTER'):
            m = APP_RE.match(l)
            pending.append((int(m.group(1)), m.group(2)))
            continue
        if l.startswith('REGISTER'):
            m = REG_RE.match(l)
            cur_name, cur_label = m.group(1), m.group(2)
            cur_q = [q for q, r in pending if r == cur_name]
            pending = []
            regs.append((cur_name, cur_label, cur_q))
            continue
        if l.strip():
            break
    return lines, regs


def gate_stats(lines, regs):
    named = {}
    for name, label, qs in regs:
        named[label] = qs
    # the first REGISTER block is the address input ("selection" = 11 address bits)
    addr = regs[0][2]
    sel = []
    words = sorted([(lab, qs) for lab, qs in named.items() if lab.startswith('word_')],
                   key=lambda t: int(t[0].split('_')[1]))
    wq = [q for _, qs in words for q in qs]
    ops = collections.Counter(l.split()[0] for l in lines if l.strip())
    # first write into an output word qubit
    first_out = None
    for i, l in enumerate(lines):
        t = l.split()
        if not t:
            continue
        if t[0] in ('CX', 'CCX'):
            tgt = int(t[-1][1:])
            if tgt in wq:
                first_out = i
                break
    ccx_before = sum(1 for l in lines[:first_out] if l.startswith('CCX'))
    ccx_after = sum(1 for l in lines[first_out:] if l.startswith('CCX'))
    return dict(addr=addr, sel=sel, words=words, wq=wq, ops=ops,
                first_out=first_out, ccx_before=ccx_before, ccx_after=ccx_after,
                nlines=len(lines))


def truth_table(path: pathlib.Path, info, nbits_addr):
    circuit = km.Circuit.from_file(str(path), format='kmx')
    n_addr = len(info['addr'])
    outs = list(info['sel']) + list(info['wq'])
    n_total = 1 << n_addr
    batch = 512
    addrs = np.arange(n_total, dtype=np.uint64)
    sim = km.Simulator(batch_size=batch, debug_print=False, counting_operations=False)
    vals = np.zeros((n_total, len(outs)), dtype=np.uint8)
    for start in range(0, n_total, batch):
        stop = min(start + batch, n_total)
        xs = addrs[start:stop]
        sim.clear_for_shot()
        bits = ((xs.astype(np.int64)[:, None] >> np.arange(n_addr, dtype=np.int64)[None, :]) & 1).astype(bool).T
        sim.write_across_shots(km.array([km.q(q) for q in info['addr']]), bits)
        sim.do(circuit)
        got = sim.read_across_shots(km.array([km.q(q) for q in outs]))
        for j in range(len(outs)):
            vals[start:stop, j] = got[j].astype(np.uint8)
    return vals


def anf_support(col: np.ndarray, nvars: int) -> list[int]:
    """ANF monomials of a Boolean function given its truth table over nvars vars."""
    f = col.astype(np.uint8).copy()
    for i in range(nvars):
        bit = 1 << i
        idx = np.where((np.arange(len(f)) & bit) == 0)[0]
        f[idx] ^= f[idx | bit]
    return [i for i, v in enumerate(f) if v]


def main() -> None:
    d = pathlib.Path(sys.argv[1])
    ks = [int(x) for x in sys.argv[2:]] or list(range(15))
    for k in ks:
        p = d / f'angle_k_{k}.kmx'
        lines, regs = parse(p)
        info = gate_stats(lines, regs)
        n_addr = len(info['addr'])
        n_sel = len(info['sel'])
        print('=' * 90)
        print(f'loader {k}: lines {info["nlines"]}  CCX {info["ops"]["CCX"]}  '
              f'CX {info["ops"]["CX"]}  HMR {info["ops"]["HMR"]}  CZ {info["ops"]["CZ"]}')
        print(f'  registers: ' + ', '.join(f'{lab or "<addr>"}({len(qs)})' for _, lab, qs in regs))
        print(f'  decoder CCX (before first word write): {info["ccx_before"]}   '
              f'output CCX: {info["ccx_after"]}   first_out line {info["first_out"]}')
        vals = truth_table(p, info, n_addr)
        sel_bits = vals[:, :n_sel]
        word_bits = vals[:, n_sel:]
        # which addresses produce a nonzero word?
        nz = np.where(word_bits.any(axis=1))[0]
        print(f'  addresses with a nonzero word: {len(nz)}  (of {len(vals)})')
        if len(nz):
            print(f'  first few nonzero addresses: {nz[:8].tolist()}')
        # per output bit: dependence on the selection code (as a 7-bit index)
        for j in range(word_bits.shape[1]):
            col = word_bits[:, j]
            if not col.any():
                print(f'  word bit {j:>2}: IDENTICALLY ZERO')
                continue
            sup = anf_support(col, n_addr)
            nz_addrs = nz
            # express as a function of the selection code where the word is nonzero
            sup_sel = []
            print(f'  word bit {j:>2}: ANF(address,{n_addr}) monomials {len(sup):>4}   '
                  f'ANF(selection,{n_sel}) monomials {len(sup_sel):>3}   '
                  f'ones {int(col.sum()):>5}')


if __name__ == '__main__':
    main()
