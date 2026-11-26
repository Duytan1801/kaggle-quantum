#!/usr/bin/env python3
"""dqi_static_scan.py — cheap static census of many DQI candidates.

For each .kmb: read the header (qubit count) and the op column, count
Toffoli-like ops (0x30/0x31/0x32) and how many sit inside a conditional
region (the 0x80 flag bit on PUSH/POP-nested ops).

The OFFICIAL DQI score is

    score = R(eps_plus) * Q^2 * T_mean

so a candidate only needs a smaller ``Q^2 * T_mean`` to beat us.  The mean
is static minus the conditional skip; we use the SAME skip factor measured on
our own tree (0.057793 of conditional Toffolis) as a proxy, so the comparison
is apples-to-apples and conservative for trees with fewer conditionals.

Usage: dqi_static_scan.py FILE [FILE ...]
"""
from __future__ import annotations

import pathlib
import struct
import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb

TOF3 = (0x30, 0x31, 0x32)
OUR_Q = 900
OUR_T_STATIC = 318_962
OUR_T_MEAN = 316_122.95665039064
SKIP = 1.0 - OUR_T_MEAN / OUR_T_STATIC   # 0.008899 of static is skipped
# implied factor between mean and static for any tree with the same mix:
# mean = static - skipped, skipped = conditional * (OUR mean skip rate)
COND_SKIP = 0.057793


def scan(path: pathlib.Path) -> dict:
    with path.open('rb') as f:
        head = f.read(32)
    nq = struct.unpack_from('<I', head, 20)[0]
    k = Kmb(path)
    ops = np.frombuffer(k.read_col(1), dtype=np.uint8)
    base = ops & 127
    flagged = ops & 0x80
    tof = (base == 0x30) | (base == 0x31) | (base == 0x32)
    n_tof = int(tof.sum())
    # conditional depth: track raw PUSH/POP nesting (PUSH is always 0x81),
    # chunked so a 100 M-op file stays inside a 2.5 GB address space.
    is_push = ops == 0x81
    is_pop = ops == 0x01
    cond_tof = 0
    d = 0
    CH = 1 << 22
    for s in range(0, len(ops), CH):
        e = min(s + CH, len(ops))
        delta = is_push[s:e].astype(np.int8) - is_pop[s:e].astype(np.int8)
        dep = np.cumsum(delta, dtype=np.int16)
        if s:
            dep += d
        d = int(dep[-1]) if len(dep) else d
        cond_tof += int((tof[s:e] & (dep > 0)).sum())
    q = nq
    mean_est = n_tof - cond_tof * COND_SKIP
    return {
        'file': str(path), 'Q': q, 'static_T': n_tof, 'cond_T': cond_tof,
        'mean_est': mean_est, 'Q2T_est': q * q * mean_est,
        'ratio_to_ours': (q * q * mean_est) / (OUR_Q * OUR_Q * OUR_T_MEAN),
    }


def main() -> int:
    files = [pathlib.Path(a) for a in sys.argv[1:]]
    if not files:
        print(__doc__)
        return 2
    rows = []
    for f in files:
        try:
            rows.append(scan(f))
        except Exception as e:  # noqa: BLE001
            print(f'  !! {f}: {e}', file=sys.stderr)
    rows.sort(key=lambda r: r['Q2T_est'])
    print(f'{"file":72s} {"Q":>4s} {"static_T":>10s} {"cond_T":>8s} '
          f'{"mean_est":>10s} {"Q2T_est":>16s} {"vs ours":>9s}')
    for r in rows:
        print(f"{r['file'][-72:]:72s} {r['Q']:4d} {r['static_T']:10d} "
              f"{r['cond_T']:8d} {r['mean_est']:10.1f} {r['Q2T_est']:16.4g} "
              f"{r['ratio_to_ours']:9.5f}")
    print(f'\nours: Q={OUR_Q} static_T={OUR_T_STATIC} mean={OUR_T_MEAN} '
          f'Q2T={OUR_Q**2 * OUR_T_MEAN:.6g}')
    print('ratio < 1 means the candidate beats us on the static proxy')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
