#!/usr/bin/env python3
"""Rebuild this archive's package members (generic entry point of the Packager release tool; shipped as build.py).

Usage:  python -B build.py OUTDIR        (the archive folder must be writable; the build writes under repo/)

BUILD.json (next to this file) names the task, the release, the handoff package (a folder under repo/), how to run its
build (cwd, argv, env with {repo} = this archive's repo/ folder and {name} = the release name), the files the build writes
(member name -> path under the package) and the licence members (member name -> path under repo/). The build runs once
with Q2026_ROOT and every other path pointing inside this archive; then the outputs and licence files are copied to
OUTDIR and every SHA256SUMS entry is checked. Writes OUTDIR/<task>_build_log.json. Exit 0 only if every entry matches.
Nothing outside OUTDIR and this archive folder is written.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE / 'repo'


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def numpy_dispatch_pin():
    """Defensive, as in the v145-v148 ISR archives: turn off numpy's AVX-512 dispatch (no-op without AVX-512)."""
    import numpy as np
    core = getattr(getattr(np, '_core', None), '_multiarray_umath', None) or np.core._multiarray_umath
    names = [f for f in getattr(core, '__cpu_dispatch__', []) if f.startswith('AVX512')]
    return {'NPY_DISABLE_CPU_FEATURES': ' '.join(names)} if names else {}


def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    spec = json.loads((HERE / 'BUILD.json').read_text())
    run, name = spec['run'], spec['release']
    pkg = REPO / spec['package']

    def fill(text):
        return text.replace('{repo}', str(REPO)).replace('{name}', name).replace('{package}', str(pkg))

    t0 = time.time()
    for rel in run.get('generated', []):
        p = pkg / fill(rel).rstrip('/')
        if p.exists() or p.is_symlink():
            sys.exit(f'refusing: {p} exists (use a freshly unpacked archive)')
    pin = numpy_dispatch_pin()
    print(f'NPY_DISABLE_CPU_FEATURES={pin.get("NPY_DISABLE_CPU_FEATURES", "")!r}', flush=True)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **{k: fill(v) for k, v in run.get('env', {}).items()}, **pin)
    argv = [sys.executable, '-B', *[fill(a) for a in run['argv']]]
    print(' '.join(argv), flush=True)
    r = subprocess.run(argv, cwd=pkg / run['cwd'], env=env, capture_output=True, text=True)
    print((r.stdout + r.stderr).strip()[-3000:], flush=True)
    for member, rel in run['outputs'].items():
        src = pkg / fill(rel)
        if r.returncode == 0 and src.is_file():
            (out / member).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, out / member)
    for member, rel in spec.get('licenses', {}).items():
        (out / member).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / rel, out / member)
    sums = {}
    for line in (HERE / 'SHA256SUMS').read_text().splitlines():
        digest, member = line.split(None, 1)
        p = out / member
        got = sha(p) if p.is_file() else None
        sums[member] = dict(sha256=got, expected=digest, match=got == digest)
        print(('MATCH ' if got == digest else 'MISMATCH ') + f'{member} {got}', flush=True)
    record = dict(task=spec['task'], release=name, candidate=spec['candidate'], package=f'repo/{spec["package"]}',
                  seconds=round(time.time() - t0, 2), command=argv[2:], returncode=r.returncode,
                  python=sys.version.split()[0], numpy=__import__('numpy').__version__,
                  NPY_DISABLE_CPU_FEATURES=pin.get('NPY_DISABLE_CPU_FEATURES', ''), members=sums,
                  all_match=r.returncode == 0 and bool(sums) and all(m['match'] for m in sums.values()))
    (out / f'{spec["task"]}_build_log.json').write_text(json.dumps(record, indent=1) + '\n')
    if not record['all_match']:
        sys.exit(f'{spec["task"]}: the build failed or some hashes differ')
    print(f'{spec["task"]} build complete; every hash matches.', flush=True)


if __name__ == '__main__':
    main()
