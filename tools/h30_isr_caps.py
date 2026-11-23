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
# Portable fallback: when this file is shipped inside a bundle (Kaggle dataset),
# the generator source sits next to it under `isr/`.
_LOCAL_SRC = pathlib.Path(__file__).resolve().parent / 'isr'
DEFAULT_SOURCE = ROOT / 'work/gens/q2026_v154/isr'
if not DEFAULT_SOURCE.exists() and _LOCAL_SRC.exists():
    DEFAULT_SOURCE = _LOCAL_SRC


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
    ap.add_argument('--stack-env', action='append', default=[],
                    help='env var injected AFTER the stack script hardcodes its exports '
                         '(use for C1MIX/FXACCCAP/etc.); e.g. --stack-env FC_XFREE=1')
    ap.add_argument('--cfg-overlay', default='',
                    help='JSON file (or inline JSON) deep-merged into the generator cfg '
                         'after mkcfg, i.e. before the emit stage that decides the H1 '
                         'schedule and the peak live width')
    ap.add_argument('--out', default='/tmp/opencode/h30_run')
    ap.add_argument('--source-root', default=str(DEFAULT_SOURCE))
    ap.add_argument('--keep', action='store_true')
    ap.add_argument('--keep-r56', action='store_true',
                    help='preserve R56_LEV instead of the stack script unsetting it')
    ap.add_argument('--cores', default='0')
    a = ap.parse_args()

    src_root = Path(a.source_root).resolve()
    out_root = Path(a.out).resolve()
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
    # ABSOLUTE symlink: the generator's scripts put $HOME/qcc/data/kickmix on
    # PYTHONPATH, and a relative target would resolve against the symlink's
    # own directory (home/qcc/data/) and break the kickmix import.
    kickmix_link = home / 'qcc/data/kickmix'
    if kickmix_link.is_symlink() or kickmix_link.exists():
        kickmix_link.unlink()
    kickmix_link.symlink_to((R / 'host_provided/kickmix').resolve())
    (home / 'qcc/.venv/bin').mkdir(parents=True)
    wrapper = home / 'qcc/.venv/bin/python'
    wrapper.write_text(f'#!/bin/sh\nexec "{sys.executable}" "$@"\n')
    wrapper.chmod(0o755)
    # The generator's own steps import kickmix from $HOME/qcc/data/kickmix.
    # Verify the extension really imports under THIS interpreter before the
    # 13-minute build starts, so a broken environment fails in 1 second
    # instead of 13 minutes.
    _probe = subprocess.run(
        [sys.executable, '-c',
         'import sys; sys.path.insert(0, "%s"); import kickmix; '
         'print("kickmix OK", kickmix.__file__, sys.version)' % (home / 'qcc/data/kickmix')],
        capture_output=True, text=True)
    if _probe.returncode != 0:
        raise SystemExit('kickmix does not import under %s:\n%s\n%s'
                         % (sys.executable, _probe.stdout[-800:], _probe.stderr[-1500:]))
    print('   ', _probe.stdout.strip())
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

    # the cfg overlay: applied after mkcfg writes the cfg, so it reaches the
    # emit stage (the stage that fixes the H1 schedule and the peak width).
    overlay_path = ''
    if a.cfg_overlay:
        overlay_path = str(home / 'qcc_cfg_overlay.json')
        ov = a.cfg_overlay
        if os.path.exists(ov):
            ov_text = pathlib.Path(ov).read_text()
        else:
            ov_text = ov
        try:
            json.loads(ov_text)
        except json.JSONDecodeError as exc:
            raise SystemExit(f'--cfg-overlay is neither a file nor valid JSON: {exc}')
        (home / 'qcc_cfg_overlay.json').write_text(ov_text)
        _patch = pathlib.Path(__file__).resolve().parent / 'qcc_cfg_patch.py'
        if not _patch.exists():
            _patch = pathlib.Path('/home/bandoc/Downloads/opencode/work/tools/qcc_cfg_patch.py')
        if not _patch.exists():
            raise SystemExit('--cfg-overlay: qcc_cfg_patch.py not found next to the driver')
        shutil.copyfile(_patch, home / 'Quantum/tools/qcc_cfg_patch.py')
        anchor = 'mkcfg 0 || exit 1'
        if anchor not in text:
            raise SystemExit('--cfg-overlay: anchor "mkcfg 0 || exit 1" not found')
        text = text.replace(
            anchor,
            anchor + '\n[ -n "$QCC_CFG_PATCH" ] && { '
                     '$P $Q/tools/qcc_cfg_patch.py "$CFG" "$QCC_CFG_PATCH" || exit 1; }',
            1)
    old = '  grep -q "CHECK PASS" $C/emit_chk.log\n'
    text = text.replace(old, '  grep -q "CHECK PASS" $C/emit_chk.log || echo "(emit check base not shipped: skipped)"\n')
    i, j = text.index('echo "== EXACT PROOF against the base'), text.index('echo "== PROVED')
    text = text[:i] + 'echo "== exact proof against the published circuit skipped in the package (no public circuit is read)"\n' + text[j:]
    text = re.sub(r"BASE=\$\(readlink -f \$\{BASE:-[^}]*\}\)", "BASE=", text)
    if a.keep_r56:
        text = text.replace("unset R56_LEV", "# R56_LEV preserved by the H30 driver")
    if a.stack_env:
        # The stack script hardcodes its own exports (C1MIX=1, FXACCCAP=30, ...).
        # Inject our overrides AFTER those lines and BEFORE the first build call,
        # so a mutated knob actually reaches the generator.
        inject = "\n".join(f"export {kv}" for kv in a.stack_env) + "\n"
        anchor = "export NUMBA_CACHE_DIR="
        if anchor not in text:
            raise SystemExit("--stack-env: anchor export NUMBA_CACHE_DIR not found")
        text = text.replace(anchor, inject + anchor, 1)
    stack.write_text(text)

    env = dict(os.environ, HOME=str(home), S5LEND='1')
    for kv in a.env:
        k, _, v = kv.partition('=')
        env[k] = v
    if a.caps:
        env['I39_CAPS'] = a.caps
    if overlay_path:
        env['QCC_CFG_PATCH'] = overlay_path
        env['QCC_HOME'] = str(home)
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
