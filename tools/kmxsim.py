#!/usr/bin/env python3
"""kmxsim.py -- bit-sliced simulator of kickmix text circuits (.kmx) for the invsqrt benchmark.

All 3,133,452 legal inputs x = 1..MAX_X are simulated at once: every wire is a packed uint64 bit-plane with one
bit per input. Measurement outcomes (HMR) are drawn independently per input, so one pass is one "shot of every x".

What it gives (same quantities as the official verifier, computed independently):
  * x restored / scratch clean checks
  * the tracked phase in units of 2^-64 turn, the error against round(2^64/sqrt(x)) and the margin tol - |err|
  * the mean number of executed Toffoli-like gates, T gates and rotations per shot
  * optional per-op traces: executed fraction, and which wires are identically zero (free) after each op

This is an analysis/screening tool. Validity is only ever claimed from the unchanged official verifier.
"""
from __future__ import annotations

import math
import sys
from fractions import Fraction

import numpy as np

MAX_X = 3133452
WIDTH = 22
NW = (MAX_X + 63) // 64            # 64-bit words per bit-plane
NPAD = NW * 64                     # padded number of inputs (the pad repeats x = 1)
ALL = np.uint64(0xFFFFFFFFFFFFFFFF)
TOFFOLI_LIKE = ("CCX", "CCZ", "CSWAP")


# ----------------------------------------------------------------------------------------------- parsing
class Op:
    __slots__ = ("name", "q", "b", "cond", "units", "expo", "line")

    def __init__(self, name, q=(), b=None, cond=None, units=0, expo=None, line=0):
        self.name, self.q, self.b, self.cond, self.units, self.expo, self.line = name, tuple(q), b, cond, units, expo, line

    def text(self):
        parts = [self.name] + [f"q{i}" for i in self.q]
        if self.name == "Z_POW":
            parts.append(self.expo)
        if self.b is not None:
            parts.append(f"b{self.b}")
        if self.cond is not None:
            parts += ["if", f"b{self.cond}"]
        return " ".join(parts)


def expo_to_units(text: str) -> int:
    """Z_POW exponent (half turns, exact decimal string) -> integer multiple of 2^-64 turn (mod 2^64), rounded to
    nearest exactly as the verifier's half_turns_to_units."""
    fr = Fraction(text)
    n, d = fr.numerator, fr.denominator
    return (((n << 64) // d + 1) >> 1) & ((1 << 64) - 1)


def parse_kmx(path):
    """Returns (ops, xreg) where xreg lists the x-register wires (LSB first)."""
    ops, xreg = [], []
    with open(path) as f:
        for ln, raw in enumerate(f, 1):
            s = raw.strip()
            if not s or s.startswith("#"):
                continue
            tok = s.split()
            name = tok[0]
            if name == "APPEND_TO_REGISTER":
                assert tok[2] == "r0" and tok[1][0] == "q", s
                xreg.append(int(tok[1][1:]))
                continue
            if name in ("REGISTER", "INFO_TAG", "DEBUG_PRINT"):
                continue
            cond = None
            if "if" in tok:
                i = tok.index("if")
                cond = int(tok[i + 1][1:])
                tok = tok[:i]
            qs = [int(t[1:]) for t in tok[1:] if t[0] == "q"]
            bs = [int(t[1:]) for t in tok[1:] if t[0] == "b"]
            units, expo = 0, None
            if name == "Z_POW":
                expo = tok[2]
                units = expo_to_units(expo)
            ops.append(Op(name, qs, bs[0] if bs else None, cond, units, expo, ln))
    return ops, xreg


def write_kmx(path, ops, xreg):
    with open(path, "w") as f:
        for q in xreg:
            f.write(f"APPEND_TO_REGISTER q{q} r0\n")
        f.write('REGISTER r0 "x"\n')
        for op in ops:
            f.write(op.text() + "\n")


def zpow_class(units: int) -> str:
    """clifford / t / rotation, as the verifier's z_pow_class (units of 2^-64 turn; half turn = 2^63)."""
    if units % (1 << 62) == 0:
        return "clifford"
    if units % (1 << 61) == 0:
        return "t"
    return "rotation"


# ----------------------------------------------------------------------------------------------- reference


def reference():
    """(target, tol) uint64 arrays indexed by x - 1, exactly as the official verifier's reference_values."""
    num = 1 << 130
    mask = (1 << 64) - 1
    tg = np.empty(MAX_X, dtype=np.uint64)
    tl = np.empty(MAX_X, dtype=np.uint64)
    for x in range(1, MAX_X + 1):
        r = math.isqrt(num // x)
        tg[x - 1] = ((r + 1) >> 1) & mask
        tl[x - 1] = min(r >> 25, 1 << 63)
    return tg, tl


# ----------------------------------------------------------------------------------------------- bit planes
def pack(bits_bool: np.ndarray) -> np.ndarray:
    """bool array of length NPAD -> uint64 plane of NW words (bit i of word w = input 64 w + i)."""
    return np.packbits(bits_bool, bitorder="little").view(np.uint64)


def unpack(plane: np.ndarray) -> np.ndarray:
    return np.unpackbits(plane.view(np.uint8), bitorder="little").astype(bool)


def popcount(plane: np.ndarray) -> int:
    return int(np.bitwise_count(plane).sum())


def input_values() -> np.ndarray:
    """x per simulated input: 1..MAX_X then pad copies of x = 1."""
    xs = np.ones(NPAD, dtype=np.int64)
    xs[:MAX_X] = np.arange(1, MAX_X + 1)
    return xs


# ----------------------------------------------------------------------------------------------- simulator
class Sim:
    def __init__(self, nq: int, outcomes="rand", seed: int = 1, xs: np.ndarray | None = None):
        """outcomes: 'rand' (independent fair coins per input), 'zero' or 'one' (all HMR outcomes forced)."""
        self.nq = nq
        self.xs = input_values() if xs is None else xs
        self.n = len(self.xs)
        assert self.n % 64 == 0
        self.nw = self.n // 64
        self.Q = np.zeros((nq, self.nw), dtype=np.uint64)
        self.bits = {}
        self.sign = np.zeros(self.nw, dtype=np.uint64)          # pi phases (Z, CZ, CCZ, NEG, HMR kickback)
        self.phase = np.zeros(self.n, dtype=np.uint64)          # Z_POW phases, units 2^-64 turn
        self.stack = []
        self.outcomes = outcomes
        self.rng = np.random.default_rng(seed)
        self.count = {"toffoli": 0, "t": 0, "rot": 0}
        self.reset_dirty = 0

    def load_x(self, xreg):
        for i, w in enumerate(xreg):
            self.Q[w] = pack(((self.xs >> i) & 1).astype(bool))

    def bit(self, b):
        v = self.bits.get(b)
        if v is None:
            v = self.bits[b] = np.zeros(self.nw, dtype=np.uint64)
        return v

    def mask(self, cond):
        """effective execution mask: None = every input."""
        m = None
        for s in self.stack:
            m = s if m is None else (m & s)
        if cond is not None:
            c = self.bit(cond)
            m = c if m is None else (m & c)
        return m

    def nexec(self, m):
        return self.n if m is None else popcount(m)

    def apply(self, op: Op):
        """Applies one op; returns the number of inputs on which it was executed."""
        name, Q = op.name, self.Q
        if name == "POP_CONDITION":
            if self.stack:
                self.stack.pop()
            return self.n
        if name == "PUSH_CONDITION":
            self.stack.append(self.bit(op.cond).copy())
            return self.n
        m = self.mask(op.cond)
        ne = self.nexec(m)
        if name == "CX":
            a, b = op.q
            Q[b] ^= Q[a] if m is None else (Q[a] & m)
        elif name == "X":
            Q[op.q[0]] ^= ALL if m is None else m
        elif name == "CCX":
            a, b, c = op.q
            t = Q[a] & Q[b]
            Q[c] ^= t if m is None else (t & m)
            self.count["toffoli"] += ne
        elif name == "CSWAP":
            c, a, b = op.q
            t = (Q[a] ^ Q[b]) & Q[c]
            if m is not None:
                t &= m
            Q[a] ^= t
            Q[b] ^= t
            self.count["toffoli"] += ne
        elif name == "SWAP":
            a, b = op.q
            t = Q[a] ^ Q[b]
            if m is not None:
                t &= m
            Q[a] ^= t
            Q[b] ^= t
        elif name == "Z":
            t = Q[op.q[0]]
            self.sign ^= t if m is None else (t & m)
        elif name == "CZ":
            a, b = op.q
            t = Q[a] & Q[b]
            self.sign ^= t if m is None else (t & m)
        elif name == "CCZ":
            a, b, c = op.q
            t = Q[a] & Q[b] & Q[c]
            self.sign ^= t if m is None else (t & m)
            self.count["toffoli"] += ne
        elif name == "NEG":
            self.sign ^= ALL if m is None else m
        elif name == "Z_POW":
            t = Q[op.q[0]] if m is None else (Q[op.q[0]] & m)
            self.phase[unpack(t)] += np.uint64(op.units)
            cls = zpow_class(op.units)
            if cls == "t":
                self.count["t"] += ne
            elif cls == "rotation":
                self.count["rot"] += ne
        elif name == "HMR":
            q = op.q[0]
            if self.outcomes == "rand":
                r = self.rng.integers(0, 1 << 64, self.nw, dtype=np.uint64)
            elif self.outcomes == "one":
                r = np.full(self.nw, ALL, dtype=np.uint64)
            else:
                r = np.zeros(self.nw, dtype=np.uint64)
            if m is None:
                self.sign ^= r & Q[q]
                self.bits[op.b] = r
                Q[q] = 0
            else:
                self.sign ^= r & Q[q] & m
                self.bits[op.b] = (self.bit(op.b) & ~m) | (r & m)
                Q[q] &= ~m
        elif name == "R":
            q = op.q[0]
            t = Q[q] if m is None else (Q[q] & m)
            self.reset_dirty += popcount(t)
            Q[q] &= ~(ALL if m is None else m)
        elif name == "BIT_INVERT":
            self.bits[op.b] = self.bit(op.b) ^ (ALL if m is None else m)
        elif name == "BIT_STORE0":
            self.bits[op.b] = self.bit(op.b) & ~(ALL if m is None else m)
        elif name == "BIT_STORE1":
            self.bits[op.b] = self.bit(op.b) | (ALL if m is None else m)
        else:
            raise ValueError(f"unknown op {name}")
        return ne

    def run(self, ops, trace=None):
        """trace: optional callable(i, op, n_executed) called after each op."""
        for i, op in enumerate(ops):
            ne = self.apply(op)
            if trace is not None:
                trace(i, op, ne)

    def theta(self):
        """total tracked phase per input, units 2^-64 turn."""
        return self.phase + (unpack(self.sign).astype(np.uint64) << np.uint64(63))

    def word(self, wires):
        """integer held on the given wires (LSB first) per input."""
        v = np.zeros(self.n, dtype=np.int64)
        for i, w in enumerate(wires):
            v |= unpack(self.Q[w]).astype(np.int64) << i
        return v


def num_wires(ops):
    return 1 + max(q for op in ops for q in op.q)


def check(ops, xreg, outcomes="rand", seed=1, verbose=True):
    """Full all-input check of a circuit. Returns a dict in the verifier's vocabulary (one shot per x)."""
    nq = num_wires(ops)
    sim = Sim(nq, outcomes, seed)
    sim.load_x(xreg)
    sim.run(ops)
    xs = sim.xs
    x_ok = bool(np.array_equal(sim.word(xreg), xs))
    scratch = [w for w in range(nq) if w not in set(xreg)]
    dirty = [w for w in scratch if sim.Q[w].any()]
    target, tol = reference()
    th = sim.theta()[:MAX_X]
    err = (th - target).view(np.int64)
    used = np.abs(err).view(np.uint64)
    bad = int((used > tol).sum())
    margin = (tol.astype(np.int64) - used.astype(np.int64))
    ratio = used / tol
    npad = sim.n - MAX_X
    scale = sim.n                                  # pad inputs execute the same gates as x = 1
    tof = sim.count["toffoli"] / scale
    tb = sim.count["t"] / scale
    nrot = sim.count["rot"] / scale
    mm = int(margin.min())
    out = dict(x_ok=x_ok, dirty=dirty, reset_dirty=sim.reset_dirty, bad=bad, min_margin=mm,
               worst_ratio=float(ratio.max()), worst_x=int(np.argmax(ratio)) + 1,
               toffoli=tof, t=tb, nrot=nrot, num_qubits=nq, num_ops=len(ops), npad=npad)
    if mm > 0 and nrot:
        eps = math.pi * mm / 2 ** 64 / nrot
        tcount = tb + nrot * (0.56 * math.log2(1 / eps) + 5.3)
        out["rotation_eps"] = eps
        out["toffoli_equivalent"] = tof + tcount / 4
        out["score"] = nq * out["toffoli_equivalent"]
        out["multiplier"] = 2076774.233715282 / out["score"]
    out["status"] = "PASS" if (x_ok and not dirty and bad == 0 and sim.reset_dirty == 0 and mm > 0) else "FAIL"
    if verbose:
        print({k: v for k, v in out.items()})
    return out


if __name__ == "__main__":
    path = sys.argv[1]
    outcomes = sys.argv[2] if len(sys.argv) > 2 else "rand"
    seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    ops, xreg = parse_kmx(path)
    check(ops, xreg, outcomes, seed)
