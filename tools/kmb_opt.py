#!/usr/bin/env python3
"""kmb_opt.py -- the EXACT peephole optimizer harvested from
bandlapallisudharani/qcc-target34-all-three-circuit-optimization.

WHAT IT IS
    A structural optimizer for kickmix `.kmb` circuits with three exact
    (symbolically verified) rewrite rules:

      1. pair_pass   -- commuting Toffoli/CCZ identities:
             * two identical Toffolis cancel;
             * two Toffolis with the SAME target and ONE shared control
               become  CX(a,b) . Toffoli(c,b,t) . CX(a,b)      (2 -> 1 magic);
             * two Toffolis with the SAME controls and DIFFERENT targets
               become  CX(t,s) . Toffoli(A,t) . CX(t,s)        (2 -> 1 magic);
             * the same for CCZ (0x30).
      2. measure_pass -- the "measure-first" rewrite: a target-only X/CX/CCX
               immediately before a measurement on that wire is moved AFTER
               the measurement and becomes a phase correction, which is exact
               because the outcome is classical.
      3. anf_pass    -- exact affine-frame ANF reconstruction: a short block
               of gates is synthesised symbolically and replaced by a shorter
               equivalent block.

WHY IT MATTERS HERE
    The official chemistry scorer counts ONLY the Toffoli-like operations
    (`circuit.operation_statistics().num_toffoli_like`).  CNOTs are free.
    So every Toffoli -> CNOT conversion is a direct score win, and the
    chemistry prize is
        d(score)/d(T) = lambda_eff * Q_total = 46.914 * 405 = 18990
    per Toffoli of the total T (13,166 over both passes), i.e. about
    +0.00084 GM per Toffoli.

    The rewrite is EXACT (symbolic), so the official verifier accepts it if
    the simulation matches -- no re-tuning of angles is involved.

USAGE
    kmb_opt.py <file.kmb> [--out FILE] [--passes N] [--report]
    kmb_opt.py --tree DIR        # every angle_k_*.kmb in DIR
"""
from __future__ import annotations

import argparse
import pathlib
import struct
import sys
from collections import Counter

import numpy as np

MAGIC = bytes.fromhex("d750c7d5c329d326e3cc9f6834f2b8bf")

PURE = {0x00, 0x01, 0x06, 0x10, 0x11, 0x12, 0x13, 0x20, 0x21, 0x22,
        0x30, 0x31, 0x32}
MAGIC_OPS = (0x30, 0x31, 0x32)


# ---------------------------------------------------------------- kmb codec
def parse_raw_kmb(path_or_bytes):
    data = (path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray))
            else pathlib.Path(path_or_bytes).read_bytes())
    magic = data[:16]
    ver, n_qubits, n_cbits, n_regs = struct.unpack_from("<4I", data, 16)
    counts = list(struct.unpack_from("<9Q", data, 32))
    pos = 104
    regs = {}
    for _ in range(n_regs):
        rtype, elen = struct.unpack_from("<2Q", data, pos)
        nl, nw = struct.unpack_from("<2I", data, pos + 16)
        name = data[pos + 24: pos + 24 + nl].decode()
        wires = list(struct.unpack_from(f"<{nw}I", data, pos + 24 + nl))
        regs[name] = wires
        pos += 16 + elen
    reg_bytes = data[104:pos]
    secs = {}
    for _ in range(11):
        sid, slen = struct.unpack_from("<2Q", data, pos)
        pos += 16
        secs[sid] = data[pos: pos + slen]
        pos += slen
    assert pos == len(data), f"Trailing bytes: {pos} != {len(data)}"
    return dict(magic=magic, header_ints=(ver, n_qubits, n_cbits, n_regs),
                counts=counts, regs=regs, reg_bytes=reg_bytes, secs=secs)


def serialize_raw_kmb(kmb_dict) -> bytes:
    head = struct.pack("<4I", *kmb_dict["header_ints"])
    head += struct.pack("<9Q", *kmb_dict["counts"])
    body = kmb_dict["reg_bytes"]
    for sid in sorted(kmb_dict["secs"]):
        sec = kmb_dict["secs"][sid]
        body += struct.pack("<2Q", sid, len(sec)) + sec
    return kmb_dict["magic"] + head + body


def decode_instructions(kmb_dict):
    secs = kmb_dict["secs"]
    ops = np.frombuffer(secs[1], dtype=np.uint8)
    s2 = np.frombuffer(secs[2], dtype=np.uint32)
    s3 = np.frombuffer(secs[3], dtype=np.uint32)
    s4 = np.frombuffer(secs[4], dtype=np.uint32)
    s5 = np.frombuffer(secs[5], dtype=np.uint32)
    s6 = np.frombuffer(secs[6], dtype=np.uint32)
    s7 = np.frombuffer(secs[7], dtype=np.uint32)
    s8 = np.frombuffer(secs[8], dtype=np.uint32)
    s9 = np.frombuffer(secs[9], dtype=np.uint32)
    s10_bytes = secs[10]
    assert len(s10_bytes) % 16 == 0

    i3 = i2 = i1 = ic_out = ic_cond = i_rot = 0
    ins = []
    for op_raw in ops:
        op = int(op_raw)
        base = op & 0x7F
        cond = int(s9[ic_cond]) if (op & 0x80) else None
        if op & 0x80:
            ic_cond += 1
        if base in (0x00, 0x01, 0x06):
            ins.append((op, cond, (), None))
        elif base in (0x10, 0x11, 0x12):
            ins.append((op, cond, (int(s7[i1]),), None))
            i1 += 1
        elif base == 0x13:
            rot_chunk = s10_bytes[i_rot * 16: (i_rot + 1) * 16]
            ins.append((op, cond, (int(s7[i1]),), rot_chunk))
            i1 += 1
            i_rot += 1
        elif base in (0x20, 0x21, 0x22):
            ins.append((op, cond, (int(s5[i2]), int(s6[i2])), None))
            i2 += 1
        elif base in (0x30, 0x31, 0x32):
            ins.append((op, cond, (int(s2[i3]), int(s3[i3]), int(s4[i3])), None))
            i3 += 1
        elif base in (0x40, 0x41, 0x42):
            ins.append((op, cond, (int(s8[ic_out]),), None))
            ic_out += 1
        elif base == 0x50:
            ins.append((op, cond, (int(s7[i1]), int(s8[ic_out])), None))
            i1 += 1
            ic_out += 1
        else:
            raise ValueError(f"Unknown opcode {hex(op)}")
    assert i3 == len(s2) == len(s3) == len(s4)
    assert i2 == len(s5) == len(s6)
    assert i1 == len(s7)
    assert ic_out == len(s8)
    assert ic_cond == len(s9)
    assert i_rot == len(s10_bytes) // 16
    return ins


def encode_instructions(kmb_dict, ins):
    ops_l, s2_l, s3_l, s4_l, s5_l, s6_l = [], [], [], [], [], []
    s7_l, s8_l, s9_l, s10_l = [], [], [], []
    for op, cond, args, rot in ins:
        ops_l.append(op)
        base = op & 0x7F
        if op & 0x80:
            assert cond is not None and 0 <= cond < 0x80000000
            s9_l.append(cond)
        if base in (0x00, 0x01, 0x06):
            pass
        elif base in (0x10, 0x11, 0x12):
            s7_l.append(args[0])
        elif base == 0x13:
            s7_l.append(args[0])
            assert isinstance(rot, (bytes, bytearray)) and len(rot) == 16
            s10_l.append(bytes(rot))
        elif base in (0x20, 0x21, 0x22):
            s5_l.append(args[0])
            s6_l.append(args[1])
        elif base in (0x30, 0x31, 0x32):
            s2_l.append(args[0])
            s3_l.append(args[1])
            s4_l.append(args[2])
        elif base in (0x40, 0x41, 0x42):
            s8_l.append(args[0])
        elif base == 0x50:
            s7_l.append(args[0])
            s8_l.append(args[1])
        else:
            raise ValueError(f"Unknown opcode {hex(op)}")
    secs = dict(kmb_dict["secs"])
    secs[1] = bytes(np.array(ops_l, dtype=np.uint8).tobytes())
    secs[2] = np.array(s2_l, dtype=np.uint32).tobytes()
    secs[3] = np.array(s3_l, dtype=np.uint32).tobytes()
    secs[4] = np.array(s4_l, dtype=np.uint32).tobytes()
    secs[5] = np.array(s5_l, dtype=np.uint32).tobytes()
    secs[6] = np.array(s6_l, dtype=np.uint32).tobytes()
    secs[7] = np.array(s7_l, dtype=np.uint32).tobytes()
    secs[8] = np.array(s8_l, dtype=np.uint32).tobytes()
    secs[9] = np.array(s9_l, dtype=np.uint32).tobytes()
    secs[10] = b''.join(s10_l)
    out = dict(kmb_dict)
    out["secs"] = secs
    return out


# ---------------------------------------------------------------- rewrites
def rw(g):
    op, c, a, r = g
    b = op & 127
    if b not in PURE:
        return None
    if b in (0x00,):
        return set(), set()
    if b in (0x10, 0x13, 0x20, 0x30):
        return set(a), set()
    if b == 0x11:
        return set(), set(a)
    if b in (0x21, 0x31):
        return set(a[:-1]), {a[-1]}
    return set(a), set(a)


def commute(x, y):
    rx = rw(x)
    ry = rw(y)
    if rx is None or ry is None:
        return False
    r, w = rx
    s, v = ry
    return not (w & s or v & r)


def gate(op, a, c=None):
    return (op | (128 if c is not None else 0), c, tuple(a), None)


def pair(a, b):
    op, c, u, _ = a
    oq, d, v, _ = b
    if op != oq or c != d:
        return None
    base = op & 127
    if base == 0x31:
        A = set(u[:2])
        B = set(v[:2])
        t = u[2]
        s = v[2]
        if len(set(u)) != 3 or len(set(v)) != 3:
            return None
        if A == B and t == s:
            return []
        if t == s and len(A & B) == 1:
            common = next(iter(A & B))
            x = next(iter(A - B))
            y = next(iter(B - A))
            return [gate(0x21, (x, y)), gate(0x31, (common, y, t), c),
                    gate(0x21, (x, y))]
        if A == B and t != s and not ({t, s} & A):
            return [gate(0x21, (t, s)), gate(0x31, (*sorted(A), t), c),
                    gate(0x21, (t, s))]
    if base == 0x30:
        A = set(u)
        B = set(v)
        if len(A) != 3 or len(B) != 3:
            return None
        if A == B:
            return []
        if len(A & B) == 2:
            x = next(iter(A - B))
            y = next(iter(B - A))
            return [gate(0x21, (x, y)), gate(0x30, (*sorted(A & B), y), c),
                    gate(0x21, (x, y))]
    return None


def pair_pass(g, look=48):
    g = list(g)
    dead = set()
    stats = Counter()
    for i in range(len(g)):
        if i in dead or (g[i][0] & 127) not in (0x30, 0x31):
            continue
        a = g[i]
        mid = []
        for j in range(i + 1, min(len(g), i + look + 1)):
            if j in dead:
                continue
            b = g[j]
            if rw(b) is None:
                break
            p = pair(a, b)
            if p is not None and all(commute(b, h) for h in mid):
                stats['pair_cancel' if not p else 'pair_factor'] += 1
                g[i] = p
                dead.add(j)
                break
            mid.append(b)
    out = []
    for i, a in enumerate(g):
        if i not in dead:
            out.extend(a if isinstance(a, list) else [a])
    return out, stats


def measure_pass(g, look=4096):
    g = list(g)
    inserts = {}
    deleted = set()
    stats = Counter()
    for j in range(len(g)):
        if g[j][0] != 0x50:
            continue
        q, c = g[j][2]
        eligible = []
        for i in range(j - 1, max(-1, j - look - 1), -1):
            h = g[i]
            if i in deleted or i in inserts or h[1] == c:
                break
            op, cond, a, r = h
            base = op & 127
            if base in (0x40, 0x41, 0x42):
                if a[0] == c:
                    break
                continue
            if base == 0x50:
                if a[0] == q or a[1] == c:
                    break
                continue
            if base == 0x12:
                if a[0] == q:
                    break
                continue
            if rw(h) is None:
                break
            if q not in a:
                continue
            if (cond is not None or op not in (0x11, 0x21, 0x31)
                    or a[-1] != q or q in a[:-1]):
                break
            eligible.append(i)
        if not any(g[i][0] == 0x31 for i in eligible):
            continue
        lo = min(eligible)
        inserts[lo] = g[j]
        deleted.add(j)
        for i in eligible:
            op, cond, a, r = g[i]
            g[i] = gate({0x11: 0, 0x21: 0x10, 0x31: 0x20}[op], a[:-1], c)
            stats['measure_x' if op == 0x11 else
                  'measure_cx' if op == 0x21 else 'measure_ccx'] += 1
    out = []
    for i, h in enumerate(g):
        if i in inserts:
            out.append(inserts[i])
        if i not in deleted:
            out.append(h)
    return out, stats


def poly_mul(a, b):
    r = set()
    for x in a:
        for y in b:
            z = x | y
            if z in r:
                r.remove(z)
            else:
                r.add(z)
    return r


def mat_inv(rows):
    n = len(rows)
    a = list(rows)
    v = [1 << i for i in range(n)]
    for j in range(n):
        p = next((i for i in range(j, n) if a[i] >> j & 1), None)
        if p is None:
            return None
        a[j], a[p] = a[p], a[j]
        v[j], v[p] = v[p], v[j]
        for i in range(n):
            if i != j and a[i] >> j & 1:
                a[i] ^= a[j]
                v[i] ^= v[j]
    return v


def lin_circuit(rows, wires):
    n = len(rows)
    a = list(rows)
    g = []
    for j in range(n):
        p = next((i for i in range(j, n) if a[i] >> j & 1), None)
        if p is None:
            return None
        if p != j:
            a[j], a[p] = a[p], a[j]
            g.extend([gate(0x21, (wires[j], wires[p])),
                      gate(0x21, (wires[p], wires[j])),
                      gate(0x21, (wires[j], wires[p]))])
        for i in range(n):
            if i != j and a[i] >> j & 1:
                a[i] ^= a[j]
                g.append(gate(0x21, (wires[j], wires[i])))
    return list(reversed(g))


def dot(a, b):
    return (a & b).bit_count() & 1


def image(rows, v):
    return sum(dot(r, v) << i for i, r in enumerate(rows))


def rowtimes(row, mat):
    v = 0
    for i, r in enumerate(mat):
        if row >> i & 1:
            v ^= r
    return v


def add_basis(piv, row):
    r = row
    while r:
        j = r.bit_length() - 1
        if j in piv:
            r ^= piv[j]
        else:
            piv[j] = r
            return True
    return False


def anf_state(block, wires):
    """the ANF of every output wire as a set of monomials"""
    idx = {q: i for i, q in enumerate(wires)}
    f = [{1 << i} for i in range(len(wires))]
    for op, c, args, r in block:
        a = [idx[q] for q in args]
        if op == 0x11:
            f[a[0]] ^= {0}
        elif op == 0x21:
            f[a[1]] ^= f[a[0]]
        elif op == 0x22:
            f[a[0]], f[a[1]] = f[a[1]], f[a[0]]
        elif op == 0x31:
            f[a[2]] ^= poly_mul(f[a[0]], f[a[1]])
        else:
            raise ValueError(op)
        if sum(map(len, f)) > 4096:
            return None
    return f


def rank1_synth(block):
    """synthesise an affine(+one quadratic) circuit equal to `block`"""
    wires = sorted({q for _, _, a, _ in block for q in a})
    n = len(wires)
    if n > 16:
        return None
    f = anf_state(block, wires)
    if f is None:
        return None
    linear = [sum(x for x in r if x.bit_count() == 1) for r in f]
    const = [i for i, r in enumerate(f) if 0 in r]
    nonlinear = [frozenset(x for x in r if x.bit_count() >= 2) for r in f]
    kinds = set(nonlinear) - {frozenset()}
    if len(kinds) > 1:
        return None
    if not kinds:
        g = lin_circuit(linear, wires)
        if g is None:
            return None
    else:
        q = next(iter(kinds))
        if any(x.bit_count() != 2 for x in q):
            return None
        m = [0] * n
        for x in q:
            a = x & -x
            b = x ^ a
            i = a.bit_length() - 1
            j = b.bit_length() - 1
            m[i] ^= b
            m[j] ^= a
        i = next(i for i, r in enumerate(m) if r)
        j = (m[i] & -m[i]).bit_length() - 1
        alpha, beta = m[i], m[j]
        if any(m[k] != (beta if alpha >> k & 1 else 0) ^
               (alpha if beta >> k & 1 else 0) for k in range(n)):
            return None
        v = sum((r == q) << k for k, r in enumerate(nonlinear))
        diag = alpha & beta
        A = [row ^ (diag if v >> k & 1 else 0) for k, row in enumerate(linear)]
        inv = mat_inv(A)
        if inv is None:
            return None
        w = image(inv, v)
        if not w or dot(alpha, w) or dot(beta, w):
            return None
        pivot = (w & -w).bit_length() - 1
        B = [alpha, beta]
        piv = {}
        assert add_basis(piv, alpha) and add_basis(piv, beta)
        for k in range(n):
            if k == pivot:
                continue
            row = (1 << k) ^ ((1 << pivot) if w >> k & 1 else 0)
            if add_basis(piv, row):
                B.append(row)
        if len(B) != n - 1:
            return None
        B.append(1 << pivot)
        Binv = mat_inv(B)
        if Binv is None:
            return None
        post = [rowtimes(row, Binv) for row in A]
        pre = lin_circuit(B, wires)
        tail = lin_circuit(post, wires)
        if pre is None or tail is None:
            return None
        g = pre + [gate(0x31, (wires[0], wires[1], wires[-1]))] + tail
    g += [gate(0x11, (wires[i],)) for i in const]
    if len(g) > max(128, 3 * len(block)):
        return None
    # Independent complete symbolic equality before accepting.
    if anf_state(g, wires) != f:
        return None
    return g


def anf_pass(gs, look=60):
    out = []
    i = 0
    stats = Counter()
    allowed = {0x11, 0x21, 0x22, 0x31}
    while i < len(gs):
        if gs[i][0] != 0x31:
            out.append(gs[i])
            i += 1
            continue
        ends = []
        ncc = 1
        for j in range(i + 1, min(i + look, len(gs))):
            if gs[j][0] not in allowed:
                break
            if gs[j][0] == 0x31:
                ncc += 1
                ends.append((j + 1, ncc))
                if ncc == 5:
                    break
        for end, ncc in reversed(ends):
            cand = rank1_synth(gs[i:end])
            if cand is not None:
                save = ncc - sum(h[0] == 0x31 for h in cand)
                if save > 0:
                    out.extend(cand)
                    stats['anf_ccx_saved'] += save
                    stats['anf_windows'] += 1
                    i = end
                    break
        else:
            out.append(gs[i])
            i += 1
    return out, stats


def optimize(raw, passes=4):
    k = parse_raw_kmb(raw)
    g = decode_instructions(k)
    assert serialize_raw_kmb(encode_instructions(k, g)) == raw
    orig = Counter(h[0] & 127 for h in g)
    stats = Counter()
    for _ in range(passes):
        g, s = pair_pass(g)
        stats.update(s)
        g, t = measure_pass(g)
        stats.update(t)
        g, u = anf_pass(g)
        stats.update(u)
        if not (s or t or u):
            break
    final = Counter(h[0] & 127 for h in g)
    n0 = sum(orig[o] for o in MAGIC_OPS)
    n1 = sum(final[o] for o in MAGIC_OPS)
    if n1 >= n0:
        return raw, dict(rules=dict(stats), accepted=False,
                         before=dict(orig), after=dict(final),
                         magic_before=n0, magic_after=n1)
    b = serialize_raw_kmb(encode_instructions(k, g))
    assert decode_instructions(parse_raw_kmb(b)) == g
    return b, dict(rules=dict(stats), accepted=True, before=dict(orig),
                   after=dict(final), magic_before=n0, magic_after=n1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--out')
    ap.add_argument('--passes', type=int, default=4)
    ap.add_argument('--report', action='store_true')
    args = ap.parse_args()
    p = pathlib.Path(args.path)
    raw = p.read_bytes()
    out, info = optimize(raw, args.passes)
    if args.report:
        print(json.dumps(info, indent=2, default=str))
    else:
        print(f'{p.name}: magic {info["magic_before"]} -> {info["magic_after"]}  '
              f'accepted={info["accepted"]}  rules={info["rules"]}')
    if args.out:
        pathlib.Path(args.out).write_bytes(out)
        print(f'wrote {args.out} ({len(out)} bytes)')
    return 0


if __name__ == '__main__':
    import json
    raise SystemExit(main())
