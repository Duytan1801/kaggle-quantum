#!/usr/bin/env python3
"""dirty_width.py — symbolic dirty-state width analysis for a kickmix .kmx circuit (memory-lean).

Tracks, per qubit, one of:
  '0'  : known |0>
  '1'  : known |1>
  'D'  : dirty (input-dependent superposition)
and reports the maximum number of simultaneously dirty qubits.

If max_dirty < declared_num_qubits, the physical qubit count could in principle be
reduced (reusing a physical qubit for two non-overlapping dirty lifetimes), which
lowers the score directly:
    invsqrt: score = num_qubits * toffoli_equivalent   (-1 qubit = +1/44 = +2.27% cost)
    dqi:     score = rep * num_qubits**2 * toffolis     (-1 qubit = +0.225% cost)

Memory-lean: no .tolist() on the big op arrays; numpy scalar indexing only.
Usage: dirty_width.py <circuit.kmx> [n_x_input_qubits]
"""
import sys
import numpy as np

sys.path.insert(0, '/tmp/opencode/recon/datasets/asteriospanoras_qcc-circuit-atlas/tools')
from qccscope import kmx  # noqa: E402

CX, CCX, CSWAP, CZ, CCZ, X, Z, SWAP, ZPOW, HMR, R, NEG, BINV, BST0, BST1, PUSH, POP, INFO, DBG = range(19)

# state codes: 0 = const0, 1 = const1, 2 = dirty
S0, S1, SD = 0, 1, 2


def analyse(path, n_x=22):
    c = kmx.load(path)
    nq = c.num_qubits
    st = np.zeros(nq, dtype=np.int8)
    if n_x:
        st[:min(n_x, nq)] = SD
    OP = c.op; A = c.a; B = c.b; Cc = c.c
    n = len(OP)
    dirty = int((st == SD).sum())
    nonzero = int((st != S0).sum())
    peak = dirty
    peak_nz = nonzero
    peak_at = []
    hist = np.zeros(nq + 1, dtype=np.int64)
    hist_nz = np.zeros(nq + 1, dtype=np.int64)
    for k in range(n):
        o = int(OP[k])
        if o == HMR or o == R:
            i = int(A[k])
            if st[i] == SD:
                dirty -= 1
            st[i] = S0
        elif o == X:
            i = int(A[k])
            v = st[i]
            st[i] = S0 if v == S1 else (S1 if v == S0 else SD)
        elif o == CX:
            a = int(A[k]); b = int(B[k])
            va = st[a]; vb = st[b]
            if vb == S0:
                st[b] = va
                if va == SD and vb != SD:
                    dirty += 1
            elif va == S1:
                st[b] = S0 if vb == S1 else (S1 if vb == S0 else SD)
                if vb == SD:
                    dirty -= 1
            elif va == SD:
                if vb == S0:
                    st[b] = SD
                    dirty += 1
                elif vb == S1:
                    st[b] = SD
                # vb == SD: stays dirty
        elif o == CCX:
            a = int(A[k]); b = int(B[k]); t = int(Cc[k])
            va, vb, vt = st[a], st[b], st[t]
            if va == SD or vb == SD:
                if vt != SD:
                    st[t] = SD
                    dirty += 1
            elif va == S1 and vb == S1:
                if vt == S0:
                    st[t] = S1
                elif vt == S1:
                    st[t] = S0
                elif vt == SD:
                    pass
            # else: product is 0 -> target unchanged
        elif o == SWAP:
            a = int(A[k]); b = int(B[k])
            st[a], st[b] = st[b], st[a]
        elif o == CSWAP:
            a = int(A[k]); b = int(B[k]); t = int(Cc[k])
            va = st[a]
            if va == S1:
                st[b], st[t] = st[t], st[b]
            elif va == SD:
                if st[b] != SD:
                    st[b] = SD; dirty += 1
                if st[t] != SD:
                    st[t] = SD; dirty += 1
        # Z / CZ / CCZ / ZPOW / NEG / bits / PUSH / POP: no change to dirty-ness
        # (ZPOW on a dirty qubit keeps it dirty; on |0> it stays |0>)
        if dirty > peak:
            peak = dirty
            peak_at = [k]
        elif dirty == peak:
            peak_at.append(k)
        hist[dirty] += 1
        # non-zero state count: a wire that is exactly |0> can share a physical wire
        nz = int(np.count_nonzero(st))
        if nz > peak_nz:
            peak_nz = nz
        hist_nz[nz] += 1
    print(f'file: {path}')
    print(f'  declared num_qubits: {nq}   ops: {n}')
    print(f'  max simultaneously DIRTY qubits: {peak}')
    print(f'  max simultaneously NON-ZERO qubits: {peak_nz}   <-- minimum physical width')
    print(f'  peak at {len(peak_at)} op positions (first {peak_at[:5]}, last {peak_at[-3:]})')
    nz = [(i, int(v)) for i, v in enumerate(hist) if v]
    print('  dirty-count histogram:', nz[-12:])
    print('  final dirty qubits:', [i for i in range(nq) if st[i] == SD][:40])
    return peak, nq


if __name__ == '__main__':
    nx = int(sys.argv[2]) if len(sys.argv) > 2 else 22
    analyse(sys.argv[1], nx)
