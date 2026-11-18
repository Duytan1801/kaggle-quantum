#!/usr/bin/env python3
"""peak_runs.py — list the peak-width runs of a workspace and dump their ops.

Usage: peak_runs.py <workspace_dir> [n_runs]
Prints, for each maximal run of ops at the maximum live width, the op list.
"""
from __future__ import annotations

import sys
import csv
import json
import pathlib

import numpy as np

ws = pathlib.Path(sys.argv[1])
n_show = int(sys.argv[2]) if len(sys.argv) > 2 else 5
prof = np.load(ws / 'profile.npy')
ops = []
with open(ws / 'ops.tsv') as f:
    for row in csv.DictReader(f, delimiter='\t'):
        ops.append(row)

w = int(prof.max())
print('peak width:', w, 'ops:', len(ops))
idx = np.flatnonzero(prof == w)
runs = []
if len(idx):
    start = idx[0]
    prev = idx[0]
    for i in idx[1:]:
        if i != prev + 1:
            runs.append((int(start), int(prev)))
            start = i
        prev = i
    runs.append((int(start), int(prev)))
print('peak runs:', len(runs), 'total peak ops:', int(len(idx)))
print('first runs:', runs[:8])
print('run lengths histogram:', sorted(set(r - s + 1 for s, r in runs)))
for (s, e) in runs[:n_show]:
    print(f'\n=== run {s}..{e} ({e-s+1} ops)')
    for row in ops[s:e + 1]:
        print('   ', row['index'], row['kind'], row['operands'], row['bit'], row['cond'], row['depth'], row['stage'])
