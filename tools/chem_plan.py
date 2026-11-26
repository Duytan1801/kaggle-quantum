#!/usr/bin/env python3
"""chem_plan.py — decode and re-emit the public chemistry loader plans.

WHAT THIS IS
    The chemistry leg of the competition is 15 "ANGLE_k" loader circuits.  A
    loader XORs the batch delta D(a) = words_k(a) ^ words_{k-1}(a) (35 bits,
    of which 30 are live) into the word registers, for 1,219 addresses.

    A loader can be built from a *plan* P:

      P['ands'] (68,6) uint8   68 cached AND features, each the product of
                                two linear forms over the 7 bank bits
      P['B']    (nm,77) bits   nm mixed features: a bank set AND (LOW==7 or 14)
      P['U']    (nP,nf) bits   for each product: the first factor's feature set
      P['V']    (nP,nf) bits   for each product: the second factor's feature set
      P['M']    (nP,30) bits   for each product: which live outputs it feeds
      P['R']    (30,nf) bits   the linear rest of each output
      P['early']               >0 => the "swap" layout (66 cached ANDs, 9 mixed,
                                one shared ancilla for two features)

    Toffolis per loader = (68 or 66) + 6 + (8 or 9) + (2 if swap) + nP.

    The plan blob for the ten loaders that
    `goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-21179` shipped lives in
    that public notebook (cell 5, `PACK`).  This tool decodes it, re-emits the
    circuits, and checks them byte for byte against a tree.

    The five batches goodpjw did NOT re-solve (k = 0,1,5,7,11, the ones at
    240-245 Toffolis) have no public plan.  This tool is the half of the
    problem that is solved; the other half is the plan search.

USAGE
    chem_plan.py --plans                      list the decoded plans
    chem_plan.py --verify PUBLIC_DIR OUR_DIR  rebuild and compare byte for byte
    chem_plan.py --emit PUBLIC_DIR OUT_DIR    write the rebuilt loaders
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/toolchain/kickmix'))

# ---------------------------------------------------------------- plan blob
# The blob is embedded in the public notebook cell; keep a durable copy.
PACK_FILE = ROOT / 'work/gens/goodpjw2008_chem_2026-11-25/loader_generator_cell5.py'
PACK_SHA = '74bd542689ad57340215541a021c741c2dda09f316a684811b71ff17bd126399'

# k, number of products, early (>0 => swap layout)
KS = [[2, 132, 16], [3, 132, 17], [4, 132, 17], [6, 132, 17], [8, 127, 0],
      [9, 132, 17], [10, 132, 17], [12, 132, 17], [13, 127, 0], [14, 123, 0]]

NV, OUTS = 1219, [o for o in range(35) if o % 7 != 6]
ADDR = np.arange(NV)
BANK, LOW = ADDR >> 4, ADDR & 15
LOW_ANDS = [((2,), 3), ((0, 1), 2), ((0, 1), 3), ((0, 2), 3), ((1, 2), 3), ((0, 1, 2), 3)]
QUADS = [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3)]

# Ground-truth record of the emitter's tracked feature functions, filled in by
# build_loader():  RECORD['fn'][qubit] = the boolean function (as an int
# bitmask over the 1,219 addresses) that the emitter believes that qubit
# carries;  RECORD['names'] = the emitter's feature-name list.
RECORD: dict = {'fn': {}, 'names': []}


def _pack_blob() -> bytes:
    src = PACK_FILE.read_text()
    m = re.search(r"PACK = r'''(.*?)'''", src, re.S)
    if not m:
        raise SystemExit(f'PACK not found in {PACK_FILE}')
    blob = base64.b85decode(m.group(1).replace('\n', ''))
    got = hashlib.sha256(blob).hexdigest()
    if got != PACK_SHA:
        raise SystemExit(f'embedded loaders corrupted: {got}')
    return blob


def decode_plans() -> dict:
    """-> {batch k: plan dict}"""
    blob = _pack_blob()
    pos = 0
    plans: dict = {}

    def take(shape):
        nonlocal pos
        n = int(np.prod(shape))
        a = np.frombuffer(blob[pos:pos + n], np.uint8).reshape(shape)
        pos += n
        return a

    for k, nP, early in KS:
        nf, nm = (100, 9) if early else (99, 8)
        plans[k] = dict(
            early=early,
            ands=take((68, 6)),
            B=np.unpackbits(take((nm, 10)), axis=1)[:, :77],
            U=np.unpackbits(take((nP, 13)), axis=1)[:, :nf],
            V=np.unpackbits(take((nP, 13)), axis=1)[:, :nf],
            M=np.unpackbits(take((nP, 4)), axis=1)[:, :30],
            R=np.unpackbits(take((30, 13)), axis=1)[:, :nf],
        )
    assert pos == len(blob), (pos, len(blob))
    return plans


# ------------------------------------------------------------------ emitter
def fun(f):
    return int.from_bytes(np.packbits(np.asarray(f, bool), bitorder='little').tobytes(), 'little')


class Lin:
    """write a function of the address as an XOR of tracked qubits"""

    def __init__(self):
        self.b = {}
        self.add(fun(np.ones(NV, bool)), frozenset(['1']))

    def red(self, v, c):
        while v:
            t = v.bit_length() - 1
            if t not in self.b:
                return v, c
            pv, pc = self.b[t]
            v ^= pv
            c = c ^ pc
        return 0, c

    def add(self, v, c):
        v, c = self.red(v, c)
        if v:
            self.b[v.bit_length() - 1] = (v, c)

    def expr(self, v):
        r, c = self.red(v, frozenset())
        assert r == 0
        return c - {'1'}, '1' in c


def controls(su, cu, sv, cv):
    """CNOTs that put u and v on two qubits"""
    for qa in sorted(su):
        inA = qa in sv
        s2 = (sv ^ su) if inA else sv
        cand = [q for q in s2 if q != qa]
        if cand:
            break
    qb = min(cand)
    pre = [('CX', q, qa) for q in sorted(su) if q != qa] + ([('X', qa)] if cu else [])
    pre += [('CX', q, qb) for q in sorted(s2) if q not in (qb, qa)] + ([('CX', qa, qb)] if inA else [])
    return pre + ([('X', qb)] if cv ^ (cu if inA else False) else []), qa, qb


def build_loader(P, sel, wq, anc0=46):
    inv = lambda s: s[::-1]
    swap = P['early'] > 0
    nb, nmix = (66, 9) if swap else (68, 8)
    ops, names, recs, L = [], ['1'], [], Lin()
    free = iter(range(anc0, 128))
    RECORD['fn'].clear()
    RECORD['names'] = names

    def track(q, f):
        names.append(q)
        L.add(f, frozenset([q]))
        RECORD['fn'][q] = f

    for i, q in enumerate(sel):
        track(q, fun((ADDR >> i) & 1))
    for j, (x, y) in enumerate(QUADS):
        ops.append(('CX', wq[7 * j + 5], wq[7 * j + 6]))
        track(wq[7 * j + 6], fun((LOW >> x) & 1 & (LOW >> y)))

    def compute(u, v, q=None):
        pre, qa, qb = controls(*L.expr(u), *L.expr(v))
        q = next(free) if q is None else q
        ops.extend(pre + [('CCX', qa, qb, q)] + inv(pre))
        RECORD['fn'][q] = u & v
        return q, pre, qa, qb

    def uncompute(q, pre, qa, qb):
        ops.extend(pre + [('HMR', q), ('CZ', qa, qb)] + inv(pre))

    def cache(u, v):
        recs.append(compute(u, v))
        track(recs[-1][0], u & v)

    gens = [sum(((x >> i) & 1) << x for x in range(77)) for i in range(7)]
    up = lambda b: fun(np.array([(b >> i) & 1 for i in range(77)], bool)[BANK])

    def pair(row):
        u = v = 0
        for i in row[:3]:
            u ^= gens[i] if i < 255 else 0
        for i in row[3:]:
            v ^= gens[i] if i < 255 else 0
        return u, v

    for row in P['ands'][:nb]:
        u, v = pair(row)
        gens.append(u & v)
        cache(up(u), up(v))
    if swap:
        (u1, v1), (u3, v3) = pair(P['ands'][66]), pair(P['ands'][67])
        e1 = compute(up(u1), up(v1))
        names += [e1[0], e1[0]]
        i1, i3 = len(names) - 2, len(names) - 1
    lb = [fun((LOW >> i) & 1) for i in range(4)]
    for s, t in LOW_ANDS:
        u = fun(np.ones(NV, bool))
        for x in s:
            u &= lb[x]
        cache(u, lb[t])
    for g in range(nmix):
        recs.append(compute(fun(LOW == (7 if g < nmix - 4 else 14)), fun(P['B'][g][BANK])))
        names.append(recs[-1][0])

    sup = lambda bits, skip=(): (frozenset(names[i] for i in np.nonzero(bits)[0] if i and i not in skip),
                                  bool(bits[0]))

    def product(u, v, m):
        pre, qa, qb = controls(*sup(u), *sup(v))
        tg = [wq[OUTS[i]] for i in np.nonzero(m)[0]]
        fan = [('CX', tg[0], q) for q in tg[1:]]
        ops.extend(pre + fan + [('CCX', qa, qb, tg[0])] + inv(fan) + inv(pre))

    prods = list(zip(P['U'], P['V'], P['M']))
    for p in prods[:P['early']]:
        product(*p)
    if swap:
        assert not any(p[0][i3] or p[1][i3] for p in prods[:P['early']])
        assert not any(p[0][i1] or p[1][i1] for p in prods[P['early']:])
        ops.extend([('CX', e1[0], wq[o]) for i, o in enumerate(OUTS) if P['R'][i][i1]])
        uncompute(*e1)
        e3 = compute(up(u3), up(v3), e1[0])
    for p in prods[P['early']:]:
        product(*p)
    for i, o in enumerate(OUTS):
        s, c = sup(P['R'][i], (i1,) if swap else ())
        ops += [('CX', q, wq[o]) for q in sorted(s)] + ([('X', wq[o])] if c else [])
    for n, r in enumerate(reversed(recs)):
        if swap and n == nmix + 6:
            uncompute(*e3)
        uncompute(*r)
    ops += [('CX', wq[7 * j + 5], wq[7 * j + 6]) for j in reversed(range(5))]
    out = []
    for t in ops:
        if out and out[-1] == t and t[0] in ('CX', 'X'):
            out.pop()
        else:
            out.append(t)
    return out


# ------------------------------------------------------------------- reader
def read_loader(path):
    """header lines, operations and registers of a loader file"""
    import kickmix as km
    c = km.Circuit.from_file(path, 'kmb')
    b = io.BytesIO()
    c.to_file(b, format='kmx')
    hdr, regs, items, ops = [], {}, {}, []
    for line in b.getvalue().decode().splitlines():
        t = line.split()
        if not t:
            continue
        if t[0] == 'REGISTER':
            regs[t[1]] = t[2].strip('"')
            hdr.append(line)
        elif t[0] == 'APPEND_TO_REGISTER':
            items.setdefault(t[2], []).append(int(t[1][1:]))
            hdr.append(line)
        else:
            ops.append((t[0],) + tuple(int(x[1:]) for x in t[1:] if x[0] == 'q'))
    by = {regs[r]: items[r] for r in regs}
    return hdr, ops, by['selection'], [q for j in range(5) for q in by[f'word_{j}']]


def run_loader(ops, sel, wq, zin):
    """values of the word bits after the loader, for all 1,219 addresses"""
    S = np.zeros((1 + max(max(t[1:]) for t in ops), NV), bool)
    S[wq] = zin
    for i, q in enumerate(sel):
        S[q] = (ADDR >> i) & 1
    for t in ops:
        if t[0] == 'CX':
            S[t[2]] ^= S[t[1]]
        elif t[0] == 'X':
            S[t[1]] ^= True
        elif t[0] == 'CCX':
            S[t[3]] ^= S[t[1]] & S[t[2]]
        elif t[0] == 'HMR':
            S[t[1]] = False
        elif t[0] == 'Z':
            S[t[1]] = False
        else:
            assert t[0] == 'CZ', t
    return S[wq].copy()


def word_bits(W, k):
    if k < 0:
        return np.zeros((35, NV), bool)
    return np.stack([((W[:, 5 * k + j] >> i) & 1).astype(bool) for j in range(5) for i in range(7)])


FMT = {'CX': 'CX q%d q%d', 'X': 'X q%d', 'CCX': 'CCX q%d q%d q%d',
       'HMR': 'HMR q%d b0', 'CZ': 'CZ q%d q%d if b0'}


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--plans', action='store_true')
    ap.add_argument('--verify')
    ap.add_argument('--emit')
    ap.add_argument('--public', default=str(ROOT / 'work/trees/v147/dfthcsos'))
    args = ap.parse_args()
    plans = decode_plans()

    if args.plans or not (args.verify or args.emit):
        print(f'{"k":>4s} {"nP":>5s} {"early":>6s} {"Toffoli":>8s}')
        for k, P in sorted(plans.items()):
            nb, nmix = (66, 9) if P['early'] > 0 else (68, 8)
            tof = nb + 6 + nmix + (2 if P['early'] > 0 else 0) + len(P['U'])
            print(f'{k:4d} {len(P["U"]):5d} {P["early"]:6d} {tof:8d}')
        print('\nmissing plans (no public blob): k = 0, 1, 5, 7, 11')
        print('our tree costs for those: k0=245 k1=240 k5=240 k7=240 k11=240')
        return 0

    import kickmix as km
    public = pathlib.Path(args.public)
    ok = True
    for k, P in sorted(plans.items()):
        hdr, _, sel, wq = read_loader(str(public / f'angle_k_{k}.kmb'))
        ops = build_loader(P, sel, wq)
        tof = sum(t[0] == 'CCX' for t in ops)
        text = ('\n'.join(hdr + [FMT[t[0]] % t[1:] for t in ops]) + '\n').encode()
        if args.emit:
            out = pathlib.Path(args.emit)
            out.mkdir(parents=True, exist_ok=True)
            path = out / f'angle_k_{k}.kmb'
            km.Circuit.from_file(io.BytesIO(text), format='kmx').to_file(str(path), format='kmb')
            print(f'k={k:2d} toffoli={tof:4d} wrote {path}')
        if args.verify:
            ours = pathlib.Path(args.verify) / f'angle_k_{k}.kmb'
            if not ours.exists():
                print(f'k={k:2d} MISSING {ours}')
                ok = False
                continue
            tmp = pathlib.Path('/tmp/opencode/chem_plan_check')
            tmp.mkdir(parents=True, exist_ok=True)
            p = tmp / f'angle_k_{k}.kmb'
            km.Circuit.from_file(io.BytesIO(text), format='kmx').to_file(str(p), format='kmb')
            same = sha(p) == sha(ours)
            ok &= same
            print(f'k={k:2d} toffoli={tof:4d} rebuilt_sha={sha(p)[:16]} ours={sha(ours)[:16]} '
                  f'{"SAME" if same else "DIFFER"}')
    if args.verify:
        print('\nRESULT:', 'ALL BYTE-IDENTICAL' if ok else 'MISMATCH')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
