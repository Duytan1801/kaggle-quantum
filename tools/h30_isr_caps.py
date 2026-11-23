#!/usr/bin/env python3
"""H30 — run the q2026-v154 ISR generator at a chosen per-stage qubit cap.

The generator's runner (`r64_inv_stack_xcrun.py`) honours the env knob

    I39_CAPS="H1=39,DIV1=39,DIV2=39,END=39"

which plans the named circuit tags at their own cap; the final
`inv_i39_relabel.py` step relabels the emitted circuit so that its qubit
count equals its *peak live width* (it is NOT forced to 39).  This driver
replays `gen_m9.py` exactly (same HOME layout, same patches to
`f9_i1_stack.sh`) but with a caller-chosen cap and without the byte-exact
hash assertion, so that a narrower plan can be produced and measured.

Usage:
  h30_isr_caps.py --caps "H1=37,DIV1=37,DIV2=37,END=37" [--out DIR]
                  [--keep] [--source-root PATH]

Prints: the produced file, its SHA-256, qubit count, op census and the
relabel step's peak-live-width line.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
DEFAULT_SOURCE = ROOT / 'work/gens/q2026_v154/isr'


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def census(kmx: Path) -> dict:
    """Op census of a KMX text circuit (kickmix KMX format)."""
    toff = {'CCX', 'CCZ', 'CSWAP'}
    n = {'CCX': 0, 'CCZ': 0, 'CSWAP': 0, 'CX': 0, 'T': 0, 'Z_POW': 0,
         'HMR': 0, 'H': 0, 'X': 0, 'Z': 0, 'S': 0}
    wires = set()
    ops = 0
    for line in kmx.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('APPEND') \
                or line.startswith('REGISTER') or '=' in line.split(' ')[0]:
            continue
        tok = line.split()
        if not tok:
            continue
        name = tok[0]
        if name not in n and not name.startswith('Z_POW'):
            continue
        ops += 1
        if name in n:
            n[name] += 1
        for t in tok[1:]:
            if t.startswith('q'):
                wires.add(int(t[1:]))
    return {'ops': ops, 'wires': len(wires), 'max_wire': (max(wires) + 1) if wires else 0,
            'toffoli_like': n['CCX'] + n['CCZ'] + n['CSWAP'], 'counts': n}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--caps', default='', help='I39_CAPS value, e.g. "H1=37,DIV1=37"')
    ap.add_argument('--env', action='append', default=[],
                    help='extra env var for the pipeline, e.g. --env S5LEND=0')
    ap.add_argument('--out', default='/tmp/opencode/h30_run')
    ap.add_argument('--source-root', default=str(DEFAULT_SOURCE))
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--cores', default='0')
    a = ap.parse_args()

    src_root = Path(a.source_root)
    out_root = Path(a.out)
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True)
    work = out_root / 'work'
    work.mkdir()
    home = work / 'home'
    s18 = home / 'qcc/ws/invsqrt_fc/s18'
    G = src_root / 'repo/experiments/isr/iterations/758_isr_leader_public/public_generator/invsqrt'
    R = src_root / 'repo'
    for s, d in ((G / 'src_s18_srcM', s18 / 'srcM'), (G / 'cfg', s18 / 'cfg'),
                 (G / 'data/r59b0', home / 'qcc/ws/invsqrt_fc/best/r59b0'),
                 (G / 'tools', home / 'Quantum/tools'), (G / 'prog', home / 'prog')):
        shutil.copytree(s, d, ignore=shutil.ignore_patterns('__pycache__'))
    (home / 'qcc/data').mkdir(parents=True, exist_ok=True)
    (home / 'qcc/data/kickmix').symlink_to(R / 'host_provided/kickmix')
    (home / 'qcc/.venv/bin').mkdir(parents=True)
    wrapper = home / 'qcc/.venv/bin/python'
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    wrapper.chmod(0o755)
    for path in home.rglob('*'):
        if path.is_file() and not path.is_symlink():
            data = path.read_bytes()
            if b'<HOME>' in data:
                path.write_bytes(data.replace(b'<HOME>', str(home).encode()))

    cub = s18 / 'cub'
    cub.mkdir(parents=True, exist_ok=True)
    m9 = (src_root / 'repo/experiments/isr/iterations/769_isr_764_m9form/package/build/m9form.json')
    (cub / 'm9dev.json').write_bytes(m9.read_bytes())

    stack = home / 'Quantum/tools/f9_i1_stack.sh'
    text = stack.read_text()
    old = '  grep -q "CHECK PASS" $C/emit_chk.log\n'
    text = text.replace(old, '  grep -q "CHECK PASS" $C/emit_chk.log || echo "(emit check base not shipped: skipped)"\n')
    i, j = text.index('echo "== EXACT PROOF against the base'), text.index('echo "== PROVED')
    text = text[:i] + 'echo "== exact proof against the published circuit skipped in the package (no public circuit is read)"\n' + text[j:]
    text = re.sub(r"BASE=\$\(readlink -f \$\{BASE:-[^}]*\}\)", "BASE=", text)
    stack.write_text(text)

    env = dict(os.environ, HOME=str(home), S5LEND='1')
    for kv in a.env:
        k, _, v = kv.partition('=')
        env[k] = v
    if a.caps:
        env['I39_CAPS'] = a.caps
    log = work / 'stack.log'
    print(f'== running f9_i1_stack.sh with I39_CAPS={a.caps!r} env={a.env}', flush=True)
    with log.open('w') as fh:
        rc = subprocess.run(['bash', str(stack), 'q18', 'dq18c',
                             str(home / 'prog/dq18c.staged.json'), a.cores],
                            cwd=home, env=env, stdout=fh,
                            stderr=subprocess.STDOUT).returncode
    tail = log.read_text(errors='replace').splitlines()
    print(f'== rc={rc}; log {log}')
    for line in tail:
        if any(k in line for k in ('per-tag caps', 'peak live', 'relabel', 'post-chain final',
                                   'EMIT', 'FAILED', 'Traceback', 'Error', 'CHECK')):
            print('   ', line[:240])
    built = home / 'qcc/ws/f9_i1/best/dq18c/invsqrt.kmb'
    if not built.exists():
        print('== no circuit produced; last 40 log lines:')
        for line in tail[-40:]:
            print('   ', line[:240])
        return 1
    dst = out_root / 'invsqrt.kmb'
    shutil.copyfile(built, dst)
    print(f'== circuit: {dst}  sha256={sha256(dst)}  bytes={dst.stat().st_size}')
    kmx = None
    for cand in home.rglob('*.kmx'):
        if cand.stat().st_mtime >= built.stat().st_mtime - 60:
            kmx = cand
    if kmx is not None:
        try:
            print('== census of', kmx.name, census(kmx))
        except Exception as e:  # noqa: BLE001
            print('== census failed:', e)
    (out_root / 'stack.log').write_text(log.read_text(errors='replace'))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
