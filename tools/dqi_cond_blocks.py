#!/usr/bin/env python3
"""dqi_cond_blocks.py — where do the DQI's Toffolis live, and what does the
conditional (zero-test-cut) machinery actually skip?

BACKGROUND.  The DQI score is

    score = rep_factor(eps) * Q^2 * mean_Toffoli

where `mean_Toffoli` is the AVERAGE number of Toffoli-like ops EXECUTED per
shot (the verifier counts executed ops over its 102,400 shots), NOT the static
count.  Our file has:

    static Toffoli-like = 318,962
    mean   Toffoli      = 316,122.9567      (0.89 % below static)

so the existing conditional machinery ("zero-test cuts", goodpjw2008) only
saves 2,839 Toffolis on the average shot.  The question this tool answers is:
how much headroom is left in that lane?

ENCODING (kickmix v2 binary format; see work/run_moat/decode_it15/kmbparse.py):
    NEG=0x00  NEG_IF=0x80
    POP=0x01  PUSH=0x81        <-- RAW bytes, not the base opcode
    Z=0x10 X=0x11 R=0x12 ZAPOW=0x13 HMR=0x50
    CZ=0x20 CX=0x21 SWAP=0x22
    CCZ=0x30 CCX=0x31 CSWAP=0x32
    BS0=0x40 BS1=0x41 BINVR=0x42
  The 0x80 bit marks a CONDITIONAL op.  NOTE: PUSH is *always* 0x81 (the
  conditional form of the base opcode 0x01), so the region nesting must be
  computed from the RAW byte, not from `op & 0x7f`.

Usage:
  dqi_cond_blocks.py <dqi.kmb> [--json OUT.json]
"""
from __future__ import annotations

import collections
import json
import pathlib
import sys

import numpy as np

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
from kmb_cols import Kmb

PUSH = 0x81
POP = 0x01
TOF = (0x30, 0x31, 0x32)


def main() -> int:
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                        '/home/bandoc/Downloads/opencode/work/trees/v147/dqi.kmb')
    k = Kmb(path)
    ops = np.frombuffer(k.read_col(1), dtype=np.uint8)
    n = len(ops)
    base = ops & 127
    flagged = ops & 0x80

    # ---- conditional-region nesting depth (RAW bytes) --------------------
    depth = np.zeros(n, dtype=np.int32)
    d = 0
    # vectorised-ish scan: the stack is shallow, so a plain loop over the
    # PUSH/POP positions is enough.
    pp = np.flatnonzero((ops == PUSH) | (ops == POP))
    # fill depth by segments
    prev = 0
    cur = 0
    for p in pp:
        if p > prev:
            depth[prev:p] = cur
        if ops[p] == PUSH:
            depth[p] = cur
            cur += 1
        else:
            cur -= 1
            depth[p] = cur
            if cur < 0:
                cur = 0
        prev = p + 1
    if prev < n:
        depth[prev:] = cur
    inside = depth > 0
    print(f'{path}: {n} ops')
    print(f'PUSH={int((ops == PUSH).sum())} POP={int((ops == POP).sum())} '
          f'final depth={int(depth[-1])} max depth={int(depth.max())}')
    print(f'ops inside a conditional region: {int(inside.sum())} '
          f'({100*inside.mean():.3f} %)')

    # ---- Toffoli census --------------------------------------------------
    is3 = np.isin(base, TOF)
    tof_all = is3
    tof_in = is3 & inside
    tof_flagged = is3 & (flagged != 0)
    tof_static_out = is3 & (~inside) & (flagged == 0)
    print(f'Toffoli-like ops: {int(tof_all.sum())}')
    print(f'  inside a conditional region : {int(tof_in.sum())}')
    print(f'  flagged conditional (0x80)  : {int(tof_flagged.sum())}')
    print(f'  static and OUTSIDE any region: {int(tof_static_out.sum())} '
          f'(always executed -> hard floor for mean_Toffoli)')

    # ---- region size histogram -------------------------------------------
    sizes = []
    tofs = []
    i = 0
    while i < n:
        if ops[i] == PUSH:
            j = i + 1
            d2 = 1
            while j < n and d2 > 0:
                if ops[j] == PUSH:
                    d2 += 1
                elif ops[j] == POP:
                    d2 -= 1
                j += 1
            sizes.append(j - i - 2)
            tofs.append(int(tof_in[i:j].sum()))
            i = j
        else:
            i += 1
    sz = np.array(sizes)
    tf = np.array(tofs)
    print(f'conditional regions: {len(sz)}')
    if len(sz):
        print(f'  region length: median {int(np.median(sz))} '
              f'p90 {int(np.percentile(sz,90))} p99 {int(np.percentile(sz,99))} '
              f'max {int(sz.max())} total {int(sz.sum())}')
        print(f'  Toffolis/region: median {int(np.median(tf))} '
              f'p90 {int(np.percentile(tf,90))} max {int(tf.max())} '
              f'total {int(tf.sum())}')
        print(f'  regions with >=1 Toffoli: {int((tf > 0).sum())} '
              f'({100*(tf > 0).mean():.2f} %)')
        print(f'  regions with >=10 Toffolis: {int((tf >= 10).sum())} '
              f'({100*(tf >= 10).mean():.2f} %)')
        print(f'  regions with >=100 Toffolis: {int((tf >= 100).sum())} '
              f'({100*(tf >= 100).mean():.2f} %)')
        big = np.argsort(-tf)[:10]
        print('  top-10 regions by Toffoli count (size, toffolis):')
        for b in big:
            print(f'    {int(sz[b]):10d} ops  {int(tf[b]):8d} Toffolis')
        # ---- how the observed mean saving can be explained ----------------
        mean = 316122.9567
        static = 318962.0
        obs = static - mean
        print(f'\n  observed mean saving = {obs:.4f} Toffolis/shot')
        print(f'  Toffolis inside conditional regions = {int(tf.sum()):,}')
        if tf.sum():
            implied_skip = obs / tf.sum()
            print(f'  => implied average skip rate of the conditional '
                  f'regions = {implied_skip:.6f}')
        out = {
            'ops': int(n),
            'push': int((ops == PUSH).sum()),
            'pop': int((ops == POP).sum()),
            'max_depth': int(depth.max()),
            'ops_inside': int(inside.sum()),
            'toffoli_all': int(tof_all.sum()),
            'toffoli_inside': int(tof_in.sum()),
            'toffoli_flagged': int(tof_flagged.sum()),
            'toffoli_static_outside': int(tof_static_out.sum()),
            'regions': int(len(sz)),
            'regions_with_toffoli': int((tf > 0).sum()),
            'regions_ge10_toffoli': int((tf >= 10).sum()),
            'regions_ge100_toffoli': int((tf >= 100).sum()),
            'observed_mean_saving': obs,
            'implied_skip_rate': (obs / tf.sum()) if tf.sum() else None,
        }
        if '--json' in sys.argv:
            p = sys.argv[sys.argv.index('--json') + 1]
            pathlib.Path(p).write_text(json.dumps(out, indent=1))
            print('wrote', p)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
