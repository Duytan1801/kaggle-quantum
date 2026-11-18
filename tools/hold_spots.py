#!/usr/bin/env python3
"""hold_spots.py — can each repair-block hold be hosted in an EXISTING wire at no width cost?

A hold keeps a product alive across [hm, i-1].  The toolkit's width model charges +1
because the original wire was zeroed by the HMR.  Physically we only need +1 width if
no wire is spare.  A wire is spare if it is PROVABLY |0> and untouched over the
blocking ops (it can host the copy and be cleared afterwards).

Inputs: workspace dir (ops.tsv, intervals.tsv, profile.npy) + repairs.json + the
tracker's zero-site table (wire becomes provably |0> at op Z).
Output: per-hold report of feasible free-window hosts.
"""
from __future__ import annotations

import sys
import csv
import json
import pathlib

import numpy as np

sys.path.insert(0, '/tmp/opencode/recon/datasets/vqcc-tools-0.1.0/scripts')
import qhdl_schedule as S


def load(ws):
    ws = pathlib.Path(ws)
    kinds, wires, bit, cond = [], [], [], []
    with open(ws / 'ops.tsv', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            kinds.append(r['kind'])
            wires.append([int(x[1:]) for x in r['operands'].split(',')] if r['operands'] else [])
            bit.append(int(r['bit'][1:]) if r['bit'] else -1)
            cond.append(int(r['cond'][1:]) if r['cond'] else -1)
    iv = []
    with open(ws / 'intervals.tsv', newline='') as f:
        for r in csv.DictReader(f, delimiter='\t'):
            iv.append((int(r['wire']), int(r['start']), int(r['end'])))
    prof = np.load(ws / 'profile.npy')
    return S.Table(kinds, wires, bit, cond, prof, iv)


def main() -> None:
    ws, rep_path = sys.argv[1], sys.argv[2]
    t = load(ws)
    q = int(t.prof.max())
    print('peak width', q, 'ops', t.n)

    # next touch of each wire after an op
    nxt = {}
    for w in range(q + 2):
        nxt[w] = [t.n] * (t.n + 2)
    touches = {w: [] for w in nxt}
    for i in range(t.n):
        for w in set(t.wires[i]):
            touches[w].append(i)
    import bisect
    for w, idxs in touches.items():
        arr = nxt[w]
        for i in range(t.n):
            j = bisect.bisect_right(idxs, i)
            arr[i] = idxs[j] if j < len(idxs) else t.n

    # zero sites from the tracker: (op, wire) -> wire provably |0> AFTER op, until next touch
    zeros_path = pathlib.Path(ws) / 'track' / 'track_0_20735_idle_zeros.tsv'
    free = []   # (wire, start_inclusive, end_exclusive)
    with open(zeros_path) as f:
        for r in csv.DictReader(f, delimiter='\t'):
            w = int(r['wire'][1:])
            op = int(r['op'])
            free.append((w, op + 1, nxt[w][op]))
    print('provably-zero windows (wire, from, to):', [(w, s, e) for (w, s, e) in free if e > s])

    rep = json.loads(pathlib.Path(rep_path).read_text())
    holds = []
    for row in rep['rows']:
        for h in row.get('recompute_holds') or []:
            if h.get('ccx') is None or h.get('hmr') is None:
                continue
            holds.append((row, h))
    print('holds with span info:', len(holds))

    # executable counters: mean executed probability per op
    ex = json.loads((pathlib.Path(ws) / 'exec' / 'exec_seed1.json').read_text())
    rows_n = ex['rows']
    sampled = {int(k): v for k, v in ex['sampled'].items()}

    feasible = []
    for row, h in holds:
        hm, i = h['hmr'], row['start']
        hd = S.hold(t, [h['wire']], hm, i - 1, q)
        blocks = hd['blocking_runs']
        if not blocks:
            feasible.append((row, h, hd, None))
            continue
        # find a provably-zero host window covering every blocking op, and also covering
        # the copy point (we must copy the value in BEFORE the HMR at hm)
        host = None
        for (w, s, e) in free:
            ok = all(s <= b['start'] and b['end'] <= e - 1 for b in blocks)
            ok = ok and s <= h['earlier'] + 1 and hm <= e - 1
            if ok:
                host = (w, s, e)
                break
        if host:
            feasible.append((row, h, hd, host))

    print(f'\n=== holds: {len(holds)}  feasible-at-no-extra-width (provably-zero host): {len(feasible)}')
    # diagnostics: where do the blocking ops live?
    spans = []
    for row, h in holds:
        hm, i = h['hmr'], row['start']
        hd = S.hold(t, [h['wire']], hm, i - 1, q)
        blocks = hd['blocking_runs']
        spans.append((h['ccx'], h['earlier'], hm, row['start'], row['end'], hd['max_width_needed'],
                      hd['blocking_ops'], [(b['start'], b['end']) for b in blocks]))
    spans.sort(key=lambda z: z[1] or 0)
    print('first 8 holds (ccx, earlier, hmr, block_start, block_end, need, nblock, blocks):')
    for s in spans[:8]:
        print('   ', s)
    print('holds whose blocking ops fall inside a provably-zero window (ignoring the copy-point rule):')
    for s in spans:
        ccx, earlier, hm, bs, be, need, nb, blocks = s
        for (w, fs, fe) in free:
            if blocks and all(fs <= b[0] and b[1] <= fe - 1 for b in blocks):
                print(f'    cxx={ccx} hmr={hm} span=[{hm},{bs-1}] blocks={blocks} host=q{w}[{fs},{fe}) earlier={earlier}')
                break
    tot_mean = 0.0
    for (row, h, hd, host) in feasible:
        ccx = h['ccx']
        prob = sampled.get(ccx, 0.0) / rows_n
        tot_mean += prob
        if len(feasible) < 12 or host is None:
            print(f'  cxx={ccx} hmr={h["hmr"]} span=[{h["hold_span"]}] blocks={len(hd["blocking_runs"])} '
                  f'need={hd["max_width_needed"]} host={host} mean_saving={prob:.4f}')
    print('total mean Toffoli saving if all feasible holds applied:', round(tot_mean, 3))
    # what if we allow Q+1?
    print('\n=== economics')
    C = 1704.6903758779981
    base = 44 * C
    for k in (1,):
        for N in (len(holds), len(feasible), 141):
            print(f'  Q={44+k}, holds={N}, mean saving {tot_mean if N==len(feasible) else 0.5*N:.1f}: '
                  f'score={(44+k)*(C-(tot_mean if N==len(feasible) else 0.5*N)):.1f} vs base {base:.1f}')
    if feasible:
        print(f'  Q=44 with {len(feasible)} holds: score={44*(C-tot_mean):.1f} vs base {base:.1f} '
              f'=> r_inv x{(C-tot_mean)/C:.5f}')


if __name__ == '__main__':
    main()
