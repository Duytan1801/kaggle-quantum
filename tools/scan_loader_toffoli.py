#!/usr/bin/env python3
"""scan_loader_toffoli.py — exact GF(2) redundancy scan of the chemistry ANGLE loaders.

Port of mizeroluckygall's "Exact Toffoli Scan of the Loaders" notebook
(Apache-2.0, https://www.kaggle.com/code/mizeroluckygall/quantum-circuits-exact-toffoli-scan-of-loaders)
to run *locally* against our own tree.

A loader reads an 11-bit selection address and XORs five 8-bit angle words into its
word registers, building the word values with Toffolis on the way.  This scan tracks
every qubit's value as a full truth table over all 2^11 addresses and asks, for every
Toffoli, whether its product (the AND of its two control truth tables) is already a
XOR of *other live, data-free* qubits.  If it is, the Toffoli can be replaced by a few
CNOTs and the chemistry cost drops (T = 2 * L_angles + 6662; 100 Toffolis/pass is worth
about +0.13 GM).

Two models are computed:
  data    word registers carry arbitrary data (the correct model: a Toffoli whose
          controls carry word data is untracked, and the span may only use
          data-free qubits);
  zero    word registers are treated as known-zero (the near-miss model that finds
          Toffolis which only exist to handle the borrowed scratch bit).

Usage:
  scan_loader_toffoli.py <loader-dir> [--rewrite OUTDIR] [--json OUT.json]
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, '/home/bandoc/Downloads/opencode/work/toolchain/kickmix')
import kickmix as km  # noqa: E402

N = 2048                      # 2^11 addresses
ONES = (1 << N) - 1
VARS = [sum(1 << x for x in range(N) if (x >> i) & 1) for i in range(11)]


def to_kmx(path: pathlib.Path, tmp: pathlib.Path) -> list[str]:
    tmp.parent.mkdir(parents=True, exist_ok=True)
    km.Circuit.from_file(str(path), format='kmb').to_file(str(tmp), format='kmx')
    return [l for l in tmp.read_text().splitlines() if l.strip()]


def in_span(target: int, basis) -> list[int] | None:
    """GF(2) elimination: express `target` as a XOR of basis vectors; return their
    qubit ids, or None if it is not in the span."""
    piv: dict[int, tuple[int, int]] = {}
    for name, v in basis:
        tag = 1 << name
        while v:
            h = v.bit_length() - 1
            if h in piv:
                pv, pt = piv[h]
                v ^= pv
                tag ^= pt
            else:
                piv[h] = (v, tag)
                break
    v, tag = target, 0
    while v:
        h = v.bit_length() - 1
        if h not in piv:
            return None
        pv, pt = piv[h]
        v ^= pv
        tag ^= pt
    return [q for q in range(tag.bit_length()) if tag >> q & 1]


def scan(lines: list[str], words_are_data: bool):
    regs: dict[int, str] = {}
    for l in lines:
        t = l.split()
        if t[0] == 'APPEND_TO_REGISTER':
            regs[int(t[1][1:])] = t[2]
    sel = sorted(q for q, r in regs.items() if r == 'r0')
    f: dict[int, int] = {}
    dep: dict[int, int] = {}
    for j, q in enumerate(sel):
        f[q], dep[q] = VARS[j], 0
    for q, r in regs.items():
        if r != 'r0':
            f[q], dep[q] = 0, ((1 << q) if words_are_data else 0)

    def kill(q):
        f.pop(q, None)
        dep.pop(q, None)

    hits, toffolis, untracked = [], 0, 0
    for i, l in enumerate(lines):
        t = l.split()
        op = t[0]
        if op in ('APPEND_TO_REGISTER', 'REGISTER', 'CZ', 'Z', 'CCZ'):
            continue
        a = [int(x[1:]) for x in t[1:] if x.startswith('q')]
        if 'if' in t:
            kill(a[-1])
            continue
        if op in ('R', 'HMR'):
            for q in a:
                f[q], dep[q] = 0, 0
        elif op == 'X':
            for q in a:
                if q in f:
                    f[q] ^= ONES
        elif op == 'CX':
            c, x = a
            if c in f and x in f:
                f[x] ^= f[c]
                dep[x] ^= dep[c]
            else:
                kill(x)
        elif op == 'SWAP':
            p, q = a
            vp, dp, vq, dq = f.get(p), dep.get(p), f.get(q), dep.get(q)
            for z, v, d in ((p, vq, dq), (q, vp, dp)):
                if v is None:
                    kill(z)
                else:
                    f[z], d2 = v, d
                    dep[z] = d2
        elif op == 'CCX':
            toffolis += 1
            c1, c2, x = a
            if c1 in f and c2 in f and x in f and dep[c1] == 0 and dep[c2] == 0:
                prod = f[c1] & f[c2]
                sol = in_span(prod, [(q, v) for q, v in f.items() if q != x and dep[q] == 0 and v])
                if sol is not None:
                    hits.append({'line': i, 'gate': l, 'xor_of': sol})
                f[x] ^= prod
            else:
                # The target now holds a data-dependent value: it is no longer a
                # known function of the address and must leave the tracked map.
                # (Leaving it in place with a stale truth table is what makes
                # false-positive "removable" Toffolis appear.)
                kill(x)
                untracked += 1
    return {'hits': hits, 'toffolis': toffolis, 'untracked': untracked}


def rewrite(lines: list[str], hits) -> list[str]:
    """Replace every flagged CCX by CNOTs from the span solution."""
    byline = {h['line']: h for h in hits}
    out = []
    for i, l in enumerate(lines):
        h = byline.get(i)
        if h is None:
            out.append(l)
            continue
        t = l.split()
        x = int(t[3][1:])
        for q in h['xor_of']:
            out.append(f'CX q{q} q{x}')
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    loader_dir = pathlib.Path(args[0])
    outdir = None
    outjson = None
    if '--rewrite' in sys.argv:
        outdir = pathlib.Path(sys.argv[sys.argv.index('--rewrite') + 1])
    if '--json' in sys.argv:
        outjson = pathlib.Path(sys.argv[sys.argv.index('--json') + 1])

    report = {'loaders': {}, 'summary': {}}
    tot_data = tot_zero = tot_ccx = 0
    for k in range(15):
        src = loader_dir / f'angle_k_{k}.kmb'
        if not src.exists():
            print(f'loader {k}: missing', flush=True)
            continue
        lines = to_kmx(src, pathlib.Path(f'/tmp/opencode/_scan_k{k}.kmx'))
        d = scan(lines, words_are_data=True)
        z = scan(lines, words_are_data=False)
        ccx = sum(1 for l in lines if l.startswith('CCX'))
        tot_data += len(d['hits'])
        tot_zero += len(z['hits'])
        tot_ccx += ccx
        report['loaders'][k] = {'ccx': ccx, 'data_hits': d['hits'],
                                'zero_hits': z['hits'], 'untracked_data': d['untracked']}
        print(f'loader {k}: CCX={ccx} data-model hits={len(d["hits"])} '
              f'zero-model hits={len(z["hits"])} untracked={d["untracked"]}', flush=True)
        if outdir is not None and d['hits']:
            outdir.mkdir(parents=True, exist_ok=True)
            new = rewrite(lines, d['hits'])
            km.Circuit('\n'.join(new) + '\n').to_file(str(outdir / f'angle_k_{k}.kmb'), format='kmb')
    report['summary'] = {'total_ccx': tot_ccx, 'data_hits': tot_data, 'zero_hits': tot_zero}
    print(f'TOTAL: CCX={tot_ccx} data-model removable={tot_data} zero-model candidates={tot_zero}')
    if outjson:
        outjson.write_text(json.dumps(report, indent=1))


if __name__ == '__main__':
    main()
