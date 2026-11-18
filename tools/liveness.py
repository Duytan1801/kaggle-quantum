#!/usr/bin/env python3
"""liveness.py — backward liveness (dead-code) analysis for a kickmix .kmx circuit.

Finds Toffoli-like ops whose effect is never observed: the write to the target is
overwritten before anything reads it, the target is never measured into a used
bit, and the op contributes nothing to the tracked phase.

Method (standard backward liveness over value versions):
  * forward pass assigns a version id to every value of every wire/bit,
  * each op records the versions it *reads* (its inputs) and the versions it
    *produces* (its outputs),
  * backward pass: an op is live iff one of its outputs is needed downstream
    (or it contributes to the phase); a live op makes its inputs needed.
  * a Toffoli with a dead output version is removable.

Conservative choices (may keep ops alive that could be dropped, never drops a
live one):
  * Z / Z_POW / CZ / CCZ are treated as phase-affecting,
  * every op inside a conditional scope depends on all scope bits,
  * NEG is treated as reading and writing its bit,
  * HMR's pre-measurement value is needed only if the measured bit is used.

Usage: liveness.py FILE.kmx [--show N] [--verbose]
"""
import sys
from collections import defaultdict

PHASE_OPS = {'Z', 'Z_POW', 'CZ', 'CCZ'}
TOF_OPS = {'CCX', 'CSWAP'}


class Op:
    __slots__ = ('idx', 'line', 'name', 'rd_w', 'wr_w', 'rd_b', 'wr_b', 'phase',
                 'tof', 'cond', 'raw', 'rd_w_v', 'wr_w_v', 'rd_b_v', 'wr_b_v', 'live')

    def __init__(self, idx, line, name, raw):
        self.idx = idx
        self.line = line
        self.name = name
        self.raw = raw
        self.rd_w = []      # (wire, version) consumed
        self.wr_w = []      # (wire, new version) produced
        self.rd_b = []      # (bit, version) consumed
        self.wr_b = []      # (bit, new version) produced
        self.phase = False
        self.tof = None     # (c1, c2, target) for CCX
        self.cond = False
        self.live = False


def parse(path):
    ops = []
    for ln, line in enumerate(open(path).read().splitlines()):
        t = line.split()
        if not t:
            continue
        name = t[0]
        if name in ('APPEND_TO_REGISTER', 'REGISTER', 'INFO_TAG', 'DEBUG_PRINT_EMPTY',
                    'DEBUG_PRINT_C', 'DEBUG_PRINT_Q'):
            continue
        op = Op(len(ops), ln, name, line)
        args = t[1:]
        cond_bit = None
        if len(args) >= 2 and args[-2] == 'if':
            cond_bit = args[-1]
            args = args[:-2]
        op.cond = cond_bit is not None
        if name == 'CCX':
            op.tof = (args[0], args[1], args[2])
            op.rd_w = [args[0], args[1], args[2]]   # new value depends on old target too
            op.wr_w = [args[2]]
        elif name == 'CCZ':
            op.rd_w = list(args[:3])
            op.phase = True
        elif name == 'CSWAP':
            op.tof = (args[0], args[1], args[2])
            op.rd_w = list(args[:3])
            op.wr_w = list(args[:3])
        elif name == 'CX':
            op.rd_w = [args[0], args[1]]            # target's old value matters
            op.wr_w = [args[1]]
        elif name == 'CZ':
            op.rd_w = list(args[:2])
            op.phase = True
        elif name == 'SWAP':
            op.rd_w = list(args[:2])
            op.wr_w = list(args[:2])
        elif name == 'X':
            op.rd_w = [args[0]]          # X is invertible: output depends on old value
            op.wr_w = [args[0]]
        elif name == 'Z':
            op.rd_w = [args[0]]
            op.phase = True
        elif name == 'Z_POW':
            op.rd_w = [args[0]]
            op.phase = True
        elif name == 'HMR':
            op.rd_w = [args[0]]          # pre-measurement value (conditional)
            op.wr_w = [args[0]]          # reset
            op.wr_b = [args[1]]
        elif name == 'R':
            op.rd_w = [args[0]]
            op.wr_w = [args[0]]
            op.phase = True
        elif name == 'PUSH_CONDITION':
            op.rd_b = [cond_bit if cond_bit is not None else args[0]]
        elif name == 'POP_CONDITION':
            pass
        elif name == 'NEG':
            if args:
                op.rd_b = [args[0]]
                op.wr_b = [args[0]]
        elif name in ('BIT_STORE0', 'BIT_STORE1'):
            op.wr_b = [args[0]]
        elif name == 'BIT_INVERT':
            op.rd_b = [args[0]]
            op.wr_b = [args[0]]
        elif cond_bit is not None:
            op.rd_b = [cond_bit]
        if cond_bit is not None and name not in ('NEG', 'BIT_INVERT'):
            op.rd_b = list(op.rd_b) + [cond_bit]
        ops.append(op)
    return ops


def analyse(path, show=20, verbose=False):
    ops = parse(path)
    # ---- forward pass: version ids -------------------------------------
    nxt = [0]          # version counter
    wver = {}          # wire -> current version
    bver = {}          # bit  -> current version
    scope = []         # stack of (bit, version)

    def newver():
        nxt[0] += 1
        return nxt[0]

    for op in ops:
        op.rd_w_v = []
        op.wr_w_v = []
        op.rd_b_v = []
        op.wr_b_v = []
        # scope dependencies
        for (b, v) in scope:
            op.rd_b_v.append((b, v))
        if op.name == 'PUSH_CONDITION':
            b = op.rd_b[0]
            v = bver.get(b)
            if v is None:
                v = newver()
                bver[b] = v
            op.rd_b_v.append((b, v))
            scope.append((b, v))
            continue
        if op.name == 'POP_CONDITION':
            if scope:
                scope.pop()
            continue
        # wires
        for w in op.rd_w:
            op.rd_w_v.append((w, wver.get(w)))
        for w in op.wr_w:
            v = newver()
            op.wr_w_v.append((w, v))
            wver[w] = v
        # bits
        for b in op.rd_b:
            op.rd_b_v.append((b, bver.get(b)))
        for b in op.wr_b:
            v = newver()
            op.wr_b_v.append((b, v))
            bver[b] = v

    # ---- backward pass -------------------------------------------------
    live = set()
    for w, v in wver.items():          # final value of every wire is constrained
        live.add(v)
    removable = []
    for op in reversed(ops):
        out_live = any(v in live for (_, v) in op.wr_w_v + op.wr_b_v)
        op_live = out_live or op.phase
        if op_live:
            for (_, v) in op.rd_w_v + op.rd_b_v:
                if v is not None:
                    live.add(v)
        op.live = op_live
        if op.tof and op.name == 'CCX' and not out_live and not op.phase:
            # dead write: the target value is never observed
            removable.append(op)

    print(f'file: {path}   ops: {len(ops)}')
    ntof = sum(1 for o in ops if o.name in ('CCX', 'CSWAP', 'CCZ'))
    print(f'  Toffoli-like ops: {ntof}   removable (dead-write CCX): {len(removable)}'
          f'   (~{len(removable)*0.00552:.3f} GM)')
    if removable:
        print('\n=== removable CCX ===')
        for op in sorted(removable, key=lambda o: o.idx)[:show]:
            print(f'  op {op.idx} (line {op.line}): {op.raw}')
            if verbose:
                for k in range(max(0, op.idx - 4), min(len(ops), op.idx + 8)):
                    print(f'      {k}: {ops[k].raw}')
    return ops, removable


if __name__ == '__main__':
    p = sys.argv[1]
    sh = int(sys.argv[sys.argv.index('--show') + 1]) if '--show' in sys.argv else 20
    analyse(p, sh, '--verbose' in sys.argv)
