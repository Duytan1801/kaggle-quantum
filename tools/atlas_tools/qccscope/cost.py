"""Task cost models (copied from the official verifiers) and exchange rates in leaderboard points.

Leaderboard: GM = (prod_i REF_i / cost_i)^(1/3).  A change of task i's cost from c to c' moves the score by
GM * ((c / c')^(1/3) - 1)  (exact; about -GM/3 * dc/c for small changes).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

REF = {"invsqrt": 2076774.23, "dqi": 24439463583672.93, "chem": 3355599588.32}
# Reference point for the exchange rates (pass your own gm= to the functions): the public leaderboard score of the
# files in atakanaldemir/quantum-circuits-iso-gap-dqi-h5 on 2026-11-14 (invsqrt dcde7078, DQI 821bf8d1, chemistry
# loaders 6de2263f + table 56913801); the MODELS below hold the official verifier numbers of those files.
GM_PUBLIC_BEST = 27.28998
GM_TARGET = 27.83                   # an example target score (pass your own to gold_gap / target_gap)


def rotation_t_count(eps: float) -> float:
    return 0.56 * math.log2(1 / eps) + 5.3


def dqi_repetition(eps: float) -> float:
    return 1.0 if eps == 0 else math.log(2.0) / -math.log(0.5 + 2.0 * math.sqrt(eps))


def dqi_eps_plus_zero_errors(shots: int = 102_400, log2_delta: float = -128.0) -> float:
    return -math.expm1(log2_delta * math.log(2.0) / shots)


@dataclass(frozen=True)
class InvSqrt:
    Q: int = 46
    toffoli: float = 1480.7497          # mean executed Toffoli-like gates (official 200,540,928 shots)
    t_base: float = 1.0                 # exact T gates
    n_rot: int = 33
    eps: float = 6.003064377662461e-13  # = pi * min_margin / 2^64 / n_rot

    @property
    def min_margin_units(self) -> float:
        return self.eps * self.n_rot * 2 ** 64 / math.pi

    def toffoli_equivalent(self) -> float:
        return self.toffoli + (self.t_base + self.n_rot * rotation_t_count(self.eps)) / 4

    def cost(self) -> float:
        return self.Q * self.toffoli_equivalent()

    def with_margin(self, margin_units: float, n_rot: int | None = None) -> "InvSqrt":
        n = self.n_rot if n_rot is None else n_rot
        return replace(self, n_rot=n, eps=math.pi * margin_units / 2 ** 64 / n)


@dataclass(frozen=True)
class DQI:
    Q: int = 889
    toffoli: float = 382_600.0          # mean executed Toffolis (official draw)
    rep: float = dqi_repetition(dqi_eps_plus_zero_errors())   # 1.1914 floor at 0 observed errors

    def cost(self) -> float:
        return self.rep * self.Q ** 2 * self.toffoli


@dataclass(frozen=True)
class Chem:
    lambda_eff: float = 46.89535386215613
    loader_toffoli_per_pass: float = 4044.0     # sum over the 15 ANGLE_k circuits; counted twice (U_T and U_T^dagger)
    heuristic_toffoli: float = 6662.0           # outer 317 + inner 4095 + Givens 2250 (cost model of R,B,C,brot)
    Q: int = 427                                # 124 persistent + max(303 heuristic temp, 77 loader temp)

    def toffoli(self) -> float:
        return 2 * self.loader_toffoli_per_pass + self.heuristic_toffoli

    def cost(self) -> float:
        return self.lambda_eff * self.toffoli() * self.Q


MODELS = {"invsqrt": InvSqrt(), "dqi": DQI(), "chem": Chem()}


def points(task: str, new_cost: float, old_cost: float | None = None, gm: float = GM_PUBLIC_BEST) -> float:
    """Exact leaderboard change when `task` goes from old_cost to new_cost (others fixed)."""
    old = MODELS[task].cost() if old_cost is None else old_cost
    return gm * ((old / new_cost) ** (1 / 3) - 1)


def saving_points(task: str, d_toffoli: float = 0.0, d_qubits: int = 0, model=None, gm: float = GM_PUBLIC_BEST) -> float:
    """Points for removing d_toffoli Toffolis (per shot / per pass for chem loaders) and d_qubits qubits."""
    m = MODELS[task] if model is None else model
    old = m.cost()
    if task == "invsqrt":
        new = replace(m, Q=m.Q - d_qubits, toffoli=m.toffoli - d_toffoli).cost()
    elif task == "dqi":
        new = replace(m, Q=m.Q - d_qubits, toffoli=m.toffoli - d_toffoli).cost()
    elif task == "chem":
        new = replace(m, Q=m.Q - d_qubits, loader_toffoli_per_pass=m.loader_toffoli_per_pass - d_toffoli).cost()
    else:
        raise KeyError(task)
    return points(task, new, old, gm)


def exchange_table(gm: float = GM_PUBLIC_BEST) -> list[dict]:
    rows = []
    for t, m in MODELS.items():
        p_t = saving_points(t, d_toffoli=1, gm=gm)
        p_q = saving_points(t, d_qubits=1, gm=gm)
        rows.append(dict(task=t, cost=m.cost(), score=REF[t] / m.cost(), pts_per_toffoli=p_t, pts_per_qubit=p_q,
                         toffoli_per_qubit=p_q / p_t))
    return rows


def gm(costs: dict | None = None) -> float:
    c = {t: MODELS[t].cost() for t in MODELS}
    if costs:
        c.update(costs)
    return math.prod(REF[t] / c[t] for t in c) ** (1 / 3)


def target_gap(gm_now: float = GM_PUBLIC_BEST, gold: float = GM_TARGET) -> dict:
    """Total log-cost cut needed to go from gm_now to the target score (and the same as % of one task's cost)."""
    need = 3 * math.log(gold / gm_now)
    return dict(log_cost_cut=need, pct_one_task=100 * (1 - math.exp(-need)))


def invsqrt_margin_points(d_margin_units: float, m: InvSqrt | None = None, gm_now: float = GM_PUBLIC_BEST) -> float:
    m = MODELS["invsqrt"] if m is None else m
    return points("invsqrt", m.with_margin(m.min_margin_units + d_margin_units).cost(), m.cost(), gm_now)


gold_gap = target_gap   # backwards-compatible name
GM_GOLD = GM_TARGET
