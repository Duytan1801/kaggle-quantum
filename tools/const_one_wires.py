#!/usr/bin/env python3
"""const_one_wires.py — find wires that hold a KNOWN |1> (constant control) in a circuit.

Two payoffs if such wires exist:
  1. a CCX with a constant-|1> control degenerates to a CX  -> the Toffoli count drops
     (invsqrt score = num_qubits * toffoli_equivalent, so every Toffoli saved is money)
  2. the wire itself may be removable -> num_qubits drops (invsqrt: +1/44 = +2.27% cost)

Usage: const_one_wires.py <circuit.kmx> [n_x_input_qubits]
"""
import sys
import numpy as np

sys.path.insert(0, '/tmp/opencode/recon/datasets/asteriospanoras_qcc-circuit-atlas/tools')
from qccscope import kmx  # noqa: E402

CX, CCX, CSWAP, CZ, CCZ, X, Z, SWAP, ZPOW, HMR, R, NEG, BINV, BST0, BST1, PUSH, POP, INFO, DBG = range(19)
S0, S1, SD = 0, 1, 2


def main():
    path = sys.argv[1]
    n_x = int(sys.argv[2]) if len(sys.argv) > 2 else 22
    c = kmx.load(path)
    nq = c.num_qubits
    st = np.zeros(nq, dtype=np.int8)
    st[:min(n_x, nq)] = SD
    OP = c.op; A = c.a; B = c.b; Cc = c.c
    # track, for every wire, the ops where it is in state S1 (known |1>) and SD (dirty)
    s1_ops = {q: [] for q in range(nq)}
    dirty_ops = {q: [] for q in range(nq)}
    ccx_const_ctrl = []      # (op, which control is const-1)
    ccx_const_tgt = []
    const_one_wire_ops = {q: 0 for q in range(nq)}
    for k in range(len(OP)):
        o = int(OP[k])
        if o == HMR or o == R:
            i = int(A[k]); st[i] = S0
        elif o == X:
            i = int(A[k]); v = int(st[i])
            st[i] = S0 if v == S1 else (S1 if v == S0 else SD)
        elif o == CX:
            a = int(A[k]); b = int(B[k]); va = int(st[a]); vb = int(st[b])
            if vb == S0:
                st[b] = va
            elif va == S1:
                st[b] = S0 if vb == S1 else (S1 if vb == S0 else SD)
            elif va == SD:
                st[b] = SD
        elif o == CCX:
            a = int(A[k]); b = int(B[k]); t = int(Cc[k])
            va, vb, vt = int(st[a]), int(st[b]), int(st[t])
            if va == SD or vb == SD:
                st[t] = SD
            elif va == S1 and vb == S1:
                st[t] = S0 if vt == S1 else (S1 if vt == S0 else SD)
            if va == S1:
                ccx_const_ctrl.append((k, 'a')); const_one_wire_ops[a] += 1
            if vb == S1:
                ccx_const_ctrl.append((k, 'b')); const_one_wire_ops[b] += 1
            if vt == S1:
                ccx_const_tgt.append(k)
        elif o == SWAP:
            a = int(A[k]); b = int(B[k]); st[a], st[b] = st[b], st[a]
        elif o == CSWAP:
            a = int(A[k]); b = int(B[k]); t = int(Cc[k]); va = int(st[a])
            if va == S1:
                st[b], st[t] = st[t], st[b]
            elif va == SD:
                st[b] = SD; st[t] = SD
        for q in range(nq):
            v = int(st[q])
            if v == S1:
                s1_ops[q].append(k)
            elif v == SD:
                dirty_ops[q].append(k)
    print(f'file: {path}  declared {nq}  ops {len(OP)}')
    print(f'  CCX ops with a constant-|1> control: {len(ccx_const_ctrl)}')
    print(f'  CCX ops with a constant-|1> TARGET : {len(ccx_const_tgt)}')
    if ccx_const_ctrl:
        cnt = {}
        for k, w in ccx_const_ctrl:
            cnt[w] = cnt.get(w, 0) + 1
        print('   by control side:', cnt)
        print('   first 12 ops:', [k for k, _ in ccx_const_ctrl[:12]])
    # wires that are S1 for a long contiguous stretch
    for q in range(nq):
        if s1_ops[q]:
            print(f'  wire {q:3d}: known-|1> at {len(s1_ops[q])} op positions, '
                  f'first {s1_ops[q][0]}, last {s1_ops[q][-1]}; '
                  f'used as const-1 control {const_one_wire_ops[q]} times')


if __name__ == '__main__':
    main()
