"""Unit tests on tiny hand-written kmx circuits (seconds).  Run: cd tools && python -m pytest -q qccscope/tests

Licence: Apache-2.0.
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.dont_write_bytecode = True

import numpy as np

from qccscope import cost as C
from qccscope import kmx, liveness as L, structure as St, values as Vv

HDR = "APPEND_TO_REGISTER q0 r0\nAPPEND_TO_REGISTER q1 r0\nREGISTER r0 \"x\"\n"


def circ(body: str) -> kmx.Circuit:
    return kmx.from_text(HDR + body)


def lanes2(a_vals, b_vals):
    """inputs for q0,q1 from per-lane bit lists"""
    qa = sum(1 << i for i, v in enumerate(a_vals) if v)
    qb = sum(1 << i for i, v in enumerate(b_vals) if v)
    return {"qubits": {0: qa, 1: qb}, "bits": {}}


ALL4 = lanes2([0, 1, 0, 1], [0, 0, 1, 1])


def test_parse_conditions_and_registers():
    c = circ("PUSH_CONDITION if b3\nCX q0 q2 if b1\nPOP_CONDITION\nZ_POW q1 0.125\nHMR q2 b4\n")
    assert c.n_ops == 5 and c.num_qubits == 3
    assert c.regs == {"r0": [0, 1]} and c.reg_names["r0"] == "x"
    assert c.op[1] == kmx.CX and c.cond[1] == 1 and c.depth[1] == 1
    assert c.op[0] == kmx.PUSH and c.bit[0] == 3
    assert c.angles[c.bit[3]] == "0.125" and c.bit[4] == 4
    assert c.conditional().tolist() == [False, True, False, False, False]


def test_liveness_open_close_and_noop_reset():
    c = circ("CCX q0 q1 q2\nCX q2 q3\nHMR q2 b0\nR q4\nCX q3 q0\nHMR q3 b1\n")
    lv = L.compute(c)
    # q4 reset while free is not an open; width: 2 regs + q2 (+ q3)
    assert lv.width.tolist() == [3, 4, 4, 3, 3, 3]
    assert lv.peak == 4
    assert sorted(lv.intervals) == [(2, 0, 2), (3, 1, 5)]
    rep = L.episode_report(c, lv)
    assert rep["n_episodes"] == 1


def test_scan_toffoli_uncompute_cancel_dead_const():
    c = circ("CCX q0 q1 q2\nCX q2 q3\nCCX q0 q1 q2\n"       # AND erased by a Toffoli (A1)
             "CCX q0 q1 q4\nCCX q0 q1 q4\n"                  # cancel pair (A2)
             "CCX q0 q1 q5\nHMR q5 b0\n"                     # dead write (A3)
             "CCX q6 q0 q7\n")                               # q6 never written: constant |0> control (A4)
    S = St.scan(c)
    assert S.toffoli_uncompute == [(0, 2)]
    assert S.cancel_pairs == [(3, 4)]
    assert S.dead_writes == [(5, 6)]
    assert S.const_control == [7]


def test_values_const_affine_repeat_and_count():
    c = circ("CCX q0 q1 q2\n"           # product a&b
             "CCX q0 q0 q3\n"           # equal controls: affine (= q0)
             "CCX q2 q4 q5\n"           # q4 = 0 -> product 0
             "CCX q0 q1 q6\n"           # repeat of op 0, first isolated
             "CCX q0 q1 q6\nCCX q0 q1 q2\nCX q0 q3\n"  # clean up
             "CCX q0 q1 q7 if b0\n")    # conditional: b0 = 0 -> no count
    V = Vv.run(c, ALL4, S=4, min_gap=1)
    assert V.affine == [1]
    assert V.const0[:1] == [2]
    assert (0, 3) in V.repeats
    assert V.toffoli_exec_mean == 6.0          # the conditional one never fires (b0 = 0)
    assert V.end_ok["inputs_restored"] and V.end_ok["dirty_ancillas"] == 0


def test_linear_products_and_drop_check():
    # q2 = q0 xor q1; then CCX q0 q2 -> q3 has product q0 & (q0^q1) = q0 & ~q1: not linear;
    # CCX q0 q5 with q5 = q0 copy: product q0 -> linear (one wire)
    c = circ("CX q0 q2\nCX q1 q2\nCCX q0 q2 q3\nCX q0 q5\nCCX q0 q5 q6\n")
    F = Vv.linear_products(c, ALL4, 4)
    assert [k for k, _, _ in F] == [4]
    assert F[0][1] == [0] or F[0][1] == [5]
    c2 = circ("CCX q0 q1 q2\nCCX q2 q4 q5\nCCX q0 q1 q2\n")
    V = Vv.run(c2, ALL4, S=4, track_gaps=False)
    assert V.const0 == [1]
    r = Vv.same_values(c2, Vv.drop_ops(c2, V.const0), ALL4, 4)
    assert r["equal"] and r["toffoli_before"] - r["toffoli_after"] == 1.0


def test_signature_equal_up_to_renaming():
    c = circ("CCX q0 q1 q2\nHMR q2 b0\nCCX q0 q1 q3\nHMR q3 b1\n")
    h1 = St.signature(c, 0, 2)[0]
    h2 = St.signature(c, 2, 4)[0]
    assert h1 == h2


def test_cost_models_reproduce_public_numbers():
    assert abs(C.MODELS["invsqrt"].cost() - 78765.51) < 1.0
    assert abs(C.MODELS["chem"].cost() - 295358662.46) < 1.0
    assert abs(C.gm() - 27.28998) < 2e-3
    assert C.saving_points("invsqrt", d_qubits=1) > 0.19
    # one qubit in DQI is worth about 860 Toffolis
    r = C.saving_points("dqi", d_qubits=1) / C.saving_points("dqi", d_toffoli=1)
    assert 840 < r < 880
    eps0 = C.dqi_eps_plus_zero_errors()
    assert abs(C.dqi_repetition(eps0) - 1.1913) < 1e-3
    g = C.gold_gap()
    assert 5.5 < g["pct_one_task"] < 6.0


def test_exhaustive_lane_builder_matches_small():
    vals = np.arange(5000, dtype=np.uint64)
    lanes = Vv.lanes_from_ints(vals, 13)
    for x in (0, 1, 777, 4999):
        assert sum(((lanes[j] >> x) & 1) << j for j in range(13)) == x


def test_episode_rebuild_finds_copy_wire():
    # q2 = copy of q0 (dependent), idle while q3, q4 are opened: width peak 5 -> q2 rebuildable by CX from q0
    c = circ("CX q0 q2\nCCX q0 q1 q3\nCCX q0 q1 q4\nCCX q0 q1 q4\nHMR q4 b0\nCCX q0 q1 q3\nHMR q3 b1\n"
             "CX q0 q2\nHMR q2 b2\n")
    lv = L.compute(c)
    assert lv.peak == 5
    r = Vv.episode_rebuild(c, lv, ALL4, 4)
    assert [(x["s"], x["e"]) for x in r] == [(2, 4)]
    assert 2 in r[0]["rebuildable"] and 3 not in r[0]["rebuildable"]
