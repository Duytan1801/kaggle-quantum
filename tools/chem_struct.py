#!/usr/bin/env python3
"""chem_struct.py — structural analysis of the chemistry loader plans.

WHAT THIS IS
    The chemistry leg is 15 loader circuits.  Batch k's loader must XOR the
    delta  D_k(a) = words_k(a) ^ words_{k-1}(a)  into the word registers for
    each of the 1,219 addresses a.

    `goodpjw2008/qcc-shorter-chemistry-loaders-lb-33-21179` published a plan
    for ten of the fifteen batches.  A plan is:

        99 (or 100) *features*  f_j(a)  -- pure functions of the 11 address
            bits: the constant, the 11 address bits, 5 products of low bits
            that the incoming words already contain, 68 cached bank ANDs,
            6 low ANDs and 8 mixed (low==7 / low==14) AND bank features;
        nP *products*  g_p(a) = f_{u_p}(a) AND f_{v_p}(a), each XORed into a
            30-bit output mask M_p;
        a *linear rest*  R_i, so that

            D_k[i](a) = XOR_{p : i in M_p} g_p(a) XOR (linear form of features)

    The cost is  82 + nP  Toffolis (83 + nP in the "swap" layout).

    This tool (1) verifies that model against the ten public plans, (2)
    reports the structure of those plans, and (3) computes the same structural
    diagnostics for the five batches that have no public plan (k = 0,1,5,7,11)
    so we can tell whether they are intrinsically harder or merely unsearched.

Usage:
    chem_struct.py <submission.npz> [--public DIR]
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
sys.path.insert(0, str(ROOT / 'work/tools'))
import chem_plan as CP                                        # noqa: E402

NV = CP.NV
ADDR = CP.ADDR
BANK, LOW = CP.BANK, CP.LOW
OUTS = CP.OUTS
NBANK = 77
NLOW = 16
CELLS = NBANK * NLOW
LOW16 = np.arange(NLOW)
VALID = np.zeros(CELLS, bool)
VALID[BANK * NLOW + LOW] = True


def cellvec(f):
    """a 1219-address function -> a 77x16 grid vector (unused cells = 0)"""
    v = np.zeros(CELLS, bool)
    v[BANK * NLOW + LOW] = f
    return v


def gens77():
    """indicator of bank bit i being 1, on the 77 valid banks"""
    out = []
    for i in range(7):
        g = np.zeros(NBANK, bool)
        g[(np.arange(NBANK) >> i) & 1 == 1] = True
        out.append(g)
    return out


GENS = gens77()


def pair77(row, gens):
    """the emitter's pair(): XOR of gens[row[i]] over the row's slots.

    IMPORTANT: the emitter's `gens` list GROWS -- it starts as the seven
    bank-bit generators and every cached AND appends its own `u & v` mask.
    So a row entry >= 7 refers to an EARLIER cached feature, not to a bank
    bit.  Entry 255 means "zero".
    """
    u = np.zeros(NBANK, bool)
    v = np.zeros(NBANK, bool)
    for i in row[:3]:
        if i < 255:
            u ^= gens[i]
    for i in row[3:]:
        if i < 255:
            v ^= gens[i]
    return u, v


def grid_of_bank77(b):
    """77-vector -> 77x16 grid"""
    return np.repeat(b[:, None], NLOW, axis=1).reshape(CELLS)


def build_features(P):
    """-> (features, names) where features is a list of CELLS-bool vectors."""
    swap = P['early'] > 0
    nb, nmix = (66, 9) if swap else (68, 8)
    f = []
    f.append(np.ones(CELLS, bool))                                    # 0 const
    for i in range(11):                                               # 1..11
        f.append(cellvec(((ADDR >> i) & 1).astype(bool)))
    for (x, y) in CP.QUADS:                                           # 12..16
        # NOTE: the emitter writes fun((LOW >> x) & 1 & (LOW >> y)); that is an
        # INTEGER and, fun() casts to bool, so the feature is
        # (low_x == 1) AND (LOW >> y != 0), i.e. low_x AND (LOW >= y).
        # It is NOT low_x AND low_y.
        f.append(cellvec((((LOW >> x) & 1) & (LOW >> y)).astype(bool)))
    # the emitter's growing `gens` list: bank-bit generators, then one entry
    # per cached AND (its own u & v mask)
    gens = [g.copy() for g in GENS]
    for row in P['ands'][:nb]:                                        # cached bank ANDs
        u, v = pair77(row, gens)
        gens.append(u & v)
        f.append(grid_of_bank77(u & v))
    if swap:
        u1, v1 = pair77(P['ands'][66], gens)
        f.append(grid_of_bank77(u1 & v1))                             # i1 = len(f)-1
        u3, v3 = pair77(P['ands'][67], gens)
        f.append(grid_of_bank77(u3 & v3))                             # i3 = len(f)-1
    for s, t in CP.LOW_ANDS:                                          # 6 low ANDs
        u = np.ones(NLOW, bool)
        for x in s:
            u &= ((LOW16 >> x) & 1).astype(bool)
        v = ((LOW16 >> t) & 1).astype(bool)
        f.append(cellvec((u & v)[LOW]))
    for g in range(nmix):                                             # mixed
        loweq = np.zeros(NLOW, bool)
        loweq[7 if g < nmix - 4 else 14] = True
        bmask = P['B'][g]
        b = np.zeros(NBANK, bool)
        for b_ in range(NBANK):
            b[b_] = bool(bmask[b_])
        f.append(grid_of_bank77(b) & cellvec(loweq[LOW]))
    return f


def main():
    path = pathlib.Path(sys.argv[1]).resolve()
    z = np.load(path)
    W = z['angle_words']
    plans = CP.decode_plans()

    # target deltas
    tgt = {}
    for k in range(15):
        wk = CP.word_bits(W, k)
        wp = CP.word_bits(W, k - 1)
        d = (wk ^ wp)[OUTS]                      # (30, 1219)
        tgt[k] = np.stack([cellvec(d[i]) for i in range(30)])

    print(f'{path}   angle_words {W.shape}')
    print()
    hdr = (f'{"k":>3s} {"nP":>4s} {"early":>5s} {"tof":>4s} {"ok":>3s} '
           f'{"prod/out":>8s} {"maskSz":>8s} {"|U|":>5s} {"|V|":>5s} '
           f'{"bankOnly":>9s} {"lowOnly":>8s} {"mixed":>6s}')
    print(hdr)
    for k in sorted(plans):
        P = plans[k]
        f = build_features(P)
        nf = len(f)
        A = tgt[k]
        # reconstruct
        out = np.zeros((30, CELLS), bool)
        for i in range(30):
            lin = np.zeros(CELLS, bool)
            for j in range(nf):
                if P['R'][i][j]:
                    lin ^= f[j]
            out[i] = lin
        nprod = len(P['U'])
        sizes = []
        bankonly = lowonly = mixed = 0
        szU = []
        szV = []
        for p in range(nprod):
            u, v = P['U'][p], P['V'][p]
            gu = np.zeros(CELLS, bool)
            for j in np.nonzero(u)[0]:
                gu ^= f[j]
            gv = np.zeros(CELLS, bool)
            for j in np.nonzero(v)[0]:
                gv ^= f[j]
            g = gu & gv
            m = P['M'][p]
            idx = np.nonzero(m)[0]
            sizes.append(len(idx))
            szU.append(len(np.nonzero(u)[0]))
            szV.append(len(np.nonzero(v)[0]))
            for i in idx:
                out[i] ^= g
            # classify by low-profile: is g independent of low?
            g2 = g.reshape(NBANK, NLOW)
            if (g2 == g2[:, :1]).all():
                bankonly += 1
            elif (g2 == g2[0, :][None, :]).all():
                lowonly += 1
            else:
                mixed += 1
        ok = bool(np.array_equal(out & VALID[None, :], A & VALID[None, :]))
        perout = np.zeros(30, int)
        for p in range(nprod):
            for i in np.nonzero(P['M'][p])[0]:
                perout[i] += 1
        nb, nmix = (66, 9) if P['early'] > 0 else (68, 8)
        tof = nb + 6 + nmix + (2 if P['early'] > 0 else 0) + nprod
        print(f'{k:3d} {nprod:4d} {P["early"]:5d} {tof:4d} {"OK" if ok else "BAD":>3s} '
              f'{perout.mean():8.2f} {np.mean(sizes):8.2f} {np.mean(szU):5.2f} {np.mean(szV):5.2f} '
              f'{bankonly:9d} {lowonly:8d} {mixed:6d}')

    # ---- diagnostics for the five batches without a public plan
    print()
    print('five batches with no public plan: structural diagnostics')
    print(f'{"k":>3s} {"rankEachOut":>12s} {"maxRank":>8s} {"colsCommon":>11s} '
          f'{"distinctCols":>13s} {"liveWt":>7s}')
    for k in (0, 1, 5, 7, 11):
        A = tgt[k]
        ranks = []
        for i in range(30):
            M = A[i].reshape(NBANK, NLOW).astype(np.uint8)
            r = gf2_rank(M)
            ranks.append(r)
        # how many of the 16 low-columns are identical across all outputs?
        cols = [A[i].reshape(NBANK, NLOW)[:, l] for l in range(NLOW)]
        common = np.zeros(NBANK, bool)
        for l in range(1, NLOW):
            common &= cols[0] ^ cols[l]
        print(f'{k:3d} {np.mean(ranks):12.2f} {max(ranks):8d} '
              f'{int((common == (A[0].reshape(NBANK,NLOW)[:,0])).all()):11d} '
              f'{len({c.tobytes() for c in cols}):13d} {int(A[:, VALID].sum()):7d}')


def gf2_rank(M):
    """rank over GF(2) of a uint8 0/1 matrix"""
    A = M.copy() % 2
    m, n = A.shape
    r = 0
    for c in range(n):
        piv = None
        for i in range(r, m):
            if A[i, c]:
                piv = i
                break
        if piv is None:
            continue
        A[[r, piv]] = A[[piv, r]]
        for i in range(m):
            if i != r and A[i, c]:
                A[i] ^= A[r]
        r += 1
        if r == m:
            break
    return r


if __name__ == '__main__':
    raise SystemExit(main())
