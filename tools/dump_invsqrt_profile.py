#!/usr/bin/env python3
"""dump_invsqrt_profile.py — per-x error profile of an invsqrt circuit.

Re-runs the *official* invsqrt verifier's simulation exactly (same seeds, same
batch size) but records, for every x, the worst |phase error| over its shots.
This tells us where the binding `min_margin = min_x (tol(x) - |error(x)|)` is and
what the functional shape of error(x) is.

Usage: dump_invsqrt_profile.py FILE.kmb [--shots-per-x N] [--out PROFILE.npz]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys

import numpy as np

VPATH = '/home/bandoc/Downloads/opencode/work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py'
_vspec = importlib.util.spec_from_file_location('vinv', VPATH)
vinv = importlib.util.module_from_spec(_vspec)
sys.modules['vinv'] = vinv
_vspec.loader.exec_module(vinv)


def build_profile(path, shots_per_x, batch_size=256, max_workers=None, quiet=False):
    circuit = vinv.km.Circuit.from_file(path, format='auto')
    spec = vinv.ProblemSpecInvSqrt.for_n_p(vinv.N_P, shots_per_x=shots_per_x)
    circuit_hash = vinv._circuit_sha256(circuit)
    x_reg, scratch = vinv.validate_registers(circuit, spec)
    target, tol = vinv.reference_values(spec, np.arange(1, spec.max_x + 1, dtype=np.uint64))
    base_seed = vinv._initial_seed(circuit_hash, '')

    num_shots = spec.num_shots
    chunk_shots = vinv.BATCHES_PER_CHUNK * batch_size
    starts = list(range(0, num_shots, chunk_shots))
    seeds = np.random.SeedSequence(base_seed, pool_size=8).generate_state(
        4 * len(starts), dtype=np.uint64).reshape(-1, 4)
    tasks = [(s, min(s + chunk_shots, num_shots), int.from_bytes(seeds[i], 'little'))
             for i, s in enumerate(starts)]

    cpus = getattr(os, 'process_cpu_count', os.cpu_count)() or 1
    nworkers = min(len(tasks), cpus if max_workers is None else max_workers)

    # split the task list into nworkers contiguous groups
    groups = []
    per = (len(tasks) + nworkers - 1) // nworkers
    for w in range(nworkers):
        g = tasks[w * per:(w + 1) * per]
        if g:
            groups.append(g)

    def run_group(group):
        used_max = np.zeros(spec.max_x, dtype=np.uint64)
        used_min = np.full(spec.max_x, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
        theta_a = np.full(spec.max_x, np.uint64(0xFFFFFFFFFFFFFFFF), dtype=np.uint64)
        theta_b = np.zeros(spec.max_x, dtype=np.uint64)
        for (chunk_start, chunk_stop, sim_seed) in group:
            sim = vinv.km.Simulator(batch_size=batch_size, debug_print=False,
                                    counting_operations=True, seed=sim_seed)
            for start in range(chunk_start, chunk_stop, batch_size):
                xs = vinv.sample_shots(spec, start, start + batch_size)
                sim.clear_for_shot()
                sim.write_across_shots(x_reg, vinv.to_bits(xs, spec.width))
                sim.do(circuit)
                theta = np.array([vinv.half_turns_to_units(sim.read_shot_phase(i))
                                  for i in range(batch_size)], dtype=np.uint64)
                t = target[xs - np.uint64(1)]
                err = (theta - t).view(np.int64)
                used = np.abs(err).view(np.uint64)
                idx = (xs - np.uint64(1)).astype(np.int64)
                np.maximum.at(used_max, idx, used)
                np.minimum.at(used_min, idx, used)
                np.minimum.at(theta_a, idx, theta)
                np.maximum.at(theta_b, idx, theta)
        return used_max, used_min, theta_a, theta_b

    if not quiet:
        print(f'profiling {path}: max_x={spec.max_x} shots/x={shots_per_x} '
              f'num_shots={num_shots} workers={len(groups)}', file=sys.stderr)
    results = vinv._run_parallel(run_group, groups, len(groups))
    used_max = results[0][0].copy()
    used_min = results[0][1].copy()
    theta_a = results[0][2].copy()
    theta_b = results[0][3].copy()
    for um, un, ta, tb in results[1:]:
        np.maximum(used_max, um, out=used_max)
        np.minimum(used_min, un, out=used_min)
        np.minimum(theta_a, ta, out=theta_a)
        np.maximum(theta_b, tb, out=theta_b)
    return {
        'used_max': used_max, 'used_min': used_min, 'tol': tol, 'target': target,
        'theta_a': theta_a, 'theta_b': theta_b,
        'spec': spec, 'circuit_hash': circuit_hash,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('circuit')
    ap.add_argument('--shots-per-x', type=int, default=2)
    ap.add_argument('--out', default='/tmp/opencode/inv44_profile.npz')
    args = ap.parse_args()
    prof = build_profile(args.circuit, args.shots_per_x)
    used_max, used_min, tol = prof['used_max'], prof['used_min'], prof['tol']
    np.savez_compressed(args.out, used_max=used_max, used_min=used_min, tol=tol,
                        theta_a=prof['theta_a'], theta_b=prof['theta_b'],
                        target=prof['target'])

    allowed = tol.astype(np.uint64)
    margin = allowed.astype(np.int64) - used_max.astype(np.int64)
    ratio = used_max.astype(np.float64) / allowed.astype(np.float64)
    print('\n=== summary ===')
    print(f'  max ratio            : {ratio.max():.9f} at x={int(ratio.argmax())+1}')
    print(f'  min margin (2^-64 tu): {int(margin.min())} at x={int(margin.argmin())+1}')
    print(f'  min margin (turns)   : {int(margin.min())/2**64:.6e}')
    print(f'  min tol at binding x : {int(allowed[margin.argmin()])/2**64:.6e}')
    print(f'  determinism (max==min): {int((used_max == used_min).sum())} of {len(used_max)} x identical')
    # ratio percentiles
    for p in (50, 90, 99, 99.9, 99.99):
        print(f'  ratio p{p:<6}: {np.percentile(ratio, p):.6f}')
    # top 40 by ratio
    order = np.argsort(-ratio)[:40]
    print('\n=== top 40 x by error/tolerance ===')
    for i in order:
        x = int(i) + 1
        print(f'  x={x:<9} bin={x:>22b} ratio={ratio[i]:.6f} err={int(used_max[i])/2**64:.4e} '
              f'tol={int(allowed[i])/2**64:.4e} margin={int(margin[i])}')
    # binding constraint: top 20 by smallest margin
    print('\n=== top 20 x by smallest margin ===')
    order2 = np.argsort(margin)[:20]
    for i in order2:
        x = int(i) + 1
        print(f'  x={x:<9} bin={x:>22b} margin={int(margin[i])} ratio={ratio[i]:.6f} '
              f'err={int(used_max[i])/2**64:.4e} tol={int(allowed[i])/2**64:.4e}')
    # error vs x structure: bucket by log2(x)
    print('\n=== error statistics by x decade ===')
    xs = np.arange(1, len(ratio) + 1)
    for e in range(0, 22, 2):
        sel = (xs >= 2 ** e) & (xs < 2 ** (e + 2))
        if not sel.any():
            continue
        print(f'  x in [2^{e},2^{e+2}): n={int(sel.sum())} '
              f'ratio: mean={ratio[sel].mean():.4f} max={ratio[sel].max():.4f} '
              f'min_margin={int(margin[sel].min())}')
    # relationship: error / target  (relative error)
    rel = used_max.astype(np.float64) / np.maximum(prof['target'].astype(np.float64), 1.0)
    print('\n=== relative error |err|/target (target = 1/sqrt(x) scaled) ===')
    for e in range(0, 22, 2):
        sel = (xs >= 2 ** e) & (xs < 2 ** (e + 2))
        if not sel.any():
            continue
        print(f'  x in [2^{e},2^{e+2}): rel mean={rel[sel].mean():.4e} max={rel[sel].max():.4e}')


if __name__ == '__main__':
    main()
