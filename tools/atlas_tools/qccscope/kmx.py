"""Streaming kmx parser -> compact numpy op table (no kickmix).

Each operation becomes one row:
  op    uint8   opcode (see OPS)
  a,b,c int16/int32 qubit operands in kmx order (-1 = unused)
               CX a->b ; CCX a,b->c ; CSWAP ctrl a, swap b,c ; CZ a,b ; CCZ a,b,c ; SWAP a,b ; X/Z/Z_POW/HMR/R a
  bit   int32   HMR output bit / BIT_* target bit / PUSH_CONDITION bit / Z_POW angle index (-1 = unused)
  cond  int32   own `if bK` condition bit (-1 = none)
  depth uint8   number of PUSH_CONDITION blocks open at this op (the op is conditional if depth>0 or cond>=0)
Registers (REGISTER / APPEND_TO_REGISTER) are kept in `regs` {name: [qubits]}; they are not ops.
"""
from __future__ import annotations

import hashlib
import io
import lzma
import os
import subprocess
from array import array
from dataclasses import dataclass, field
from fractions import Fraction

import numpy as np

OPS = ["CX", "CCX", "CSWAP", "CZ", "CCZ", "X", "Z", "SWAP", "Z_POW", "HMR", "R", "NEG",
       "BIT_INVERT", "BIT_STORE0", "BIT_STORE1", "PUSH_CONDITION", "POP_CONDITION", "INFO_TAG", "DEBUG_PRINT"]
OPC = {n: i for i, n in enumerate(OPS)}
CX, CCX, CSWAP, CZ, CCZ, X, Z, SWAP, ZPOW, HMR, R, NEG, BINV, BST0, BST1, PUSH, POP, INFO, DBG = range(len(OPS))
TOFFOLI_OPS = (CCX, CCZ, CSWAP)
DIAGONAL_OPS = (CZ, CCZ, Z, ZPOW)


@dataclass
class Circuit:
    op: np.ndarray
    a: np.ndarray
    b: np.ndarray
    c: np.ndarray
    bit: np.ndarray
    cond: np.ndarray
    depth: np.ndarray
    regs: dict = field(default_factory=dict)
    bit_regs: dict = field(default_factory=dict)
    reg_names: dict = field(default_factory=dict)
    angles: list = field(default_factory=list)      # Z_POW angle strings, indexed by `bit`
    tags: list = field(default_factory=list)        # (op index, text) of INFO_TAG lines
    path: str = ""

    @property
    def n_ops(self) -> int:
        return len(self.op)

    @property
    def num_qubits(self) -> int:
        m = -1
        for arr in (self.a, self.b, self.c):
            if len(arr):
                m = max(m, int(arr.max()))
        return m + 1

    @property
    def num_bits(self) -> int:
        return int(max(self.bit.max(initial=-1), self.cond.max(initial=-1))) + 1

    def conditional(self) -> np.ndarray:
        return (self.cond >= 0) | (self.depth > 0)

    def input_qubits(self) -> np.ndarray:
        qs = sorted({q for v in self.regs.values() for q in v})
        return np.array(qs, dtype=np.int64)

    def angle_half_turns(self, k: int) -> Fraction:
        return Fraction(self.angles[k])


def _open_text(path: str):
    if path.endswith(".xz"):
        try:
            p = subprocess.Popen(["xz", "-T4", "-dc", path], stdout=subprocess.PIPE, bufsize=1 << 22)
            return io.TextIOWrapper(p.stdout, encoding="ascii"), p
        except FileNotFoundError:
            return io.TextIOWrapper(lzma.open(path, "rb"), encoding="ascii"), None
    return open(path, "r", encoding="ascii", buffering=1 << 22), None


def parse(path: str, verbose: bool = False) -> Circuit:
    """Parse a .kmx (or .kmx.xz) file. Linear time, about 1-2 M lines/s."""
    op = array("B"); A = array("i"); B = array("i"); C = array("i")
    BIT = array("i"); COND = array("i"); DEP = array("B")
    regs: dict = {}
    bit_regs: dict = {}
    reg_names: dict = {}
    angles: list = []
    ang_idx: dict = {}
    tags: list = []
    depth = 0
    opc = OPC
    f, proc = _open_text(path)
    n = 0
    for line in f:
        t = line.split()
        if not t:
            continue
        name = t[0]
        if name == "APPEND_TO_REGISTER":
            if t[1][0] == "q":
                regs.setdefault(t[2], []).append(int(t[1][1:]))
            else:
                bit_regs.setdefault(t[2], []).append(int(t[1][1:]))
            continue
        if name == "REGISTER":
            reg_names[t[1]] = t[2].strip('"') if len(t) > 2 else t[1]
            continue
        if name == "INFO_TAG" or name == "DEBUG_PRINT":
            tags.append((len(op), line.rstrip("\n")))
            continue
        k = opc[name]
        cond = -1
        if len(t) >= 3 and t[-2] == "if":
            cond = int(t[-1][1:])
            t = t[:-2]
        qa = qb = qc = bt = -1
        if k == PUSH:
            op.append(k); A.append(-1); B.append(-1); C.append(-1); BIT.append(cond); COND.append(-1)
            DEP.append(min(depth, 255)); depth += 1
            continue
        if k == POP:
            depth -= 1
            op.append(k); A.append(-1); B.append(-1); C.append(-1); BIT.append(-1); COND.append(-1)
            DEP.append(min(depth, 255))
            continue
        nt = len(t)
        if k == ZPOW:
            qa = int(t[1][1:])
            s = t[2]
            bt = ang_idx.get(s)
            if bt is None:
                bt = ang_idx[s] = len(angles); angles.append(s)
        elif k == HMR:
            qa = int(t[1][1:]); bt = int(t[2][1:])
        elif k >= BINV:  # BIT_* ops
            bt = int(t[1][1:])
        else:
            if nt > 1: qa = int(t[1][1:])
            if nt > 2: qb = int(t[2][1:])
            if nt > 3: qc = int(t[3][1:])
        op.append(k); A.append(qa); B.append(qb); C.append(qc); BIT.append(bt); COND.append(cond)
        DEP.append(min(depth, 255))
        n += 1
        if verbose and n % 5_000_000 == 0:
            print(f"  parsed {n:,} ops", flush=True)
    f.close()
    if proc is not None:
        proc.wait()
    nq = max(max(A, default=-1), max(B, default=-1), max(C, default=-1)) + 1
    wdt = np.int16 if nq < 32000 else np.int32
    return Circuit(op=np.frombuffer(op, dtype=np.uint8).copy(),
                   a=np.frombuffer(A, dtype=np.int32).astype(wdt), b=np.frombuffer(B, dtype=np.int32).astype(wdt),
                   c=np.frombuffer(C, dtype=np.int32).astype(wdt), bit=np.frombuffer(BIT, dtype=np.int32).copy(),
                   cond=np.frombuffer(COND, dtype=np.int32).copy(), depth=np.frombuffer(DEP, dtype=np.uint8).copy(),
                   regs=regs, bit_regs=bit_regs, reg_names=reg_names, angles=angles, tags=tags, path=path)


def load(path: str, cache_dir: str | None = None, verbose: bool = False) -> Circuit:
    """parse() with an on-disk .npz cache keyed by file size+mtime (big DQI files parse once)."""
    if cache_dir is None:
        return parse(path, verbose)
    st = os.stat(path)
    key = hashlib.sha1(f"{os.path.abspath(path)}|{st.st_size}|{st.st_mtime_ns}".encode()).hexdigest()[:16]
    cp = os.path.join(cache_dir, f"{os.path.basename(path)}.{key}.v2.npz")
    if os.path.exists(cp):
        z = np.load(cp, allow_pickle=True)
        meta = z["meta"].item()
        return Circuit(op=z["op"], a=z["a"], b=z["b"], c=z["c"], bit=z["bit"], cond=z["cond"], depth=z["depth"],
                       regs=meta["regs"], bit_regs=meta.get("bit_regs", {}), reg_names=meta["reg_names"], angles=meta["angles"], tags=meta["tags"],
                       path=path)
    circ = parse(path, verbose)
    os.makedirs(cache_dir, exist_ok=True)
    meta = dict(regs=circ.regs, bit_regs=circ.bit_regs, reg_names=circ.reg_names, angles=circ.angles, tags=circ.tags)
    np.savez(cp, op=circ.op, a=circ.a, b=circ.b, c=circ.c, bit=circ.bit, cond=circ.cond, depth=circ.depth,
             meta=np.array(meta, dtype=object))
    return circ


def from_text(text: str) -> Circuit:
    """Parse kmx text (used by the unit tests)."""
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".kmx", delete=False) as fh:
        fh.write(text)
        p = fh.name
    try:
        return parse(p)
    finally:
        os.unlink(p)
