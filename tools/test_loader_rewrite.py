#!/usr/bin/env python3
"""test_loader_rewrite.py — validate the Toffoli removals found by
`scan_loader_toffoli.py` (data model) by exact simulation.

For every loader with candidates we build the rewritten circuit (the flagged CCX
becomes CNOTs from the GF(2) span solution) and compare the full 2^11-address
simulation against the original: every qubit's value and every shot's phase, with
zero word registers and with random word registers.  A removal is accepted only if
both comparisons match exactly.

Usage: test_loader_rewrite.py <loader-dir> [--rewrite OUTDIR] [--json OUT.json]
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/tools')
import kickmix as km  # noqa: E402
import numpy as np  # noqa: E402
from scan_loader_toffoli import scan, rewrite, to_kmx  # noqa: E402


def simulate(lines, word_values, seed=7):
    c = km.Circuit('\n'.join(lines) + '\n')
    regs: dict[str, list[int]] = {}
    for l in lines:
        t = l.split()
        if t[0] == 'APPEND_TO_REGISTER':
            regs.setdefault(t[2], []).append(int(t[1][1:]))
    sel = km.array([km.q(q) for q in regs['r0']])
    words = km.array([km.q(q) for r, qs in sorted(regs.items()) if r != 'r0' for q in qs])
    N = 2048
    s = km.Simulator(batch_size=N, seed=seed, debug_print=False)
    s.clear_for_shot()
    addr = np.arange(N, dtype=np.uint64)
    s.write_across_shots(sel, ((addr[None, :] >> np.arange(11, dtype=np.uint64)[:, None]) & 1).astype(bool))
    s.write_across_shots(words, word_values)
    s.do(c)
    state = s.read_across_shots(km.array([km.q(q) for q in range(c.num_qubits)]))
    phase = np.array([s.read_shot_phase(j) for j in range(N)])
    return state, phase


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    loader_dir = pathlib.Path(args[0])
    outdir = pathlib.Path(sys.argv[sys.argv.index('--rewrite') + 1]) if '--rewrite' in sys.argv else None
    outjson = pathlib.Path(sys.argv[sys.argv.index('--json') + 1]) if '--json' in sys.argv else None

    rng = np.random.default_rng(2026)
    ZERO = np.zeros((40, 2048), dtype=bool)
    RAND = rng.integers(0, 2, (40, 2048)).astype(bool)
    report = {'loaders': {}, 'summary': {}}
    total_removed = 0
    total_safe = 0
    for k in range(15):
        src = loader_dir / f'angle_k_{k}.kmb'
        if not src.exists():
            continue
        lines = to_kmx(src, pathlib.Path(f'/tmp/opencode/_test_k{k}.kmx'))
        d = scan(lines, words_are_data=True)
        if not d['hits']:
            continue
        new = rewrite(lines, d['hits'])
        base_zero = simulate(lines, ZERO)
        base_rand = simulate(lines, RAND)
        mod_zero = simulate(new, ZERO)
        mod_rand = simulate(new, RAND)
        ok_zero = bool((mod_zero[0] == base_zero[0]).all() and np.array_equal(mod_zero[1], base_zero[1]))
        ok_rand = bool((mod_rand[0] == base_rand[0]).all() and np.array_equal(mod_rand[1], base_rand[1]))
        safe = ok_zero and ok_rand
        removed = len(d['hits'])
        total_removed += removed
        if safe:
            total_safe += removed
        report['loaders'][k] = {'removed': removed, 'same_zero': ok_zero, 'same_random': ok_rand,
                                'safe': safe, 'gates': [h['gate'] for h in d['hits']]}
        print(f'loader {k}: removed {removed} CCX -> same_zero={ok_zero} same_random={ok_rand} '
              f'{"SAFE" if safe else "UNSAFE"}', flush=True)
        if safe and outdir is not None:
            outdir.mkdir(parents=True, exist_ok=True)
            km.Circuit('\n'.join(new) + '\n').to_file(str(outdir / f'angle_k_{k}.kmb'), format='kmb')
    report['summary'] = {'total_removed': total_removed, 'total_safe': total_safe}
    print(f'TOTAL: removed {total_removed}, safe {total_safe}')
    if outjson:
        outjson.write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
