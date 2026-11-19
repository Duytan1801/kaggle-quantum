"""Fast tests for the atlas tools (seconds, no network, no kickmix).

    python tools/tests/test_tools.py      or      pytest tools/tests

Licence: Apache-2.0.
"""
import csv
import glob
import gzip
import json
import os
import sys
import tempfile

import numpy as np
sys.dont_write_bytecode = True

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)
import kmsim  # noqa: E402
import liveness  # noqa: E402
import build_splice  # noqa: E402

TOY = """APPEND_TO_REGISTER q0 r0
APPEND_TO_REGISTER q1 r0
REGISTER r0 "x"
CCX q0 q1 q2
CZ q2 q0
CCX q0 q1 q2
HMR q3 b0
R q3
"""


def toy(text=TOY, gz=False):
    fd, p = tempfile.mkstemp(suffix=".kmx.gz" if gz else ".kmx")
    os.close(fd)
    with (gzip.open(p, "wt") if gz else open(p, "w")) as f:
        f.write(text)
    return p


def test_parse_and_simulate_toy():
    for gz in (False, True):
        ops, regs = kmsim.parse(toy(gz=gz))
        assert regs == {"r0": [0, 1]}
        assert [o[0] for o in ops] == ["CCX", "CZ", "CCX", "HMR", "R"]
        s = kmsim.Sim(ops, 4, 1, 4, seed=1)
        for i, q in enumerate(regs["r0"]):
            s.q[q] = (np.arange(4) >> i) & 1 == 1
        s.run()
        assert not s.q[2].any() and not s.q[3].any()          # ancilla uncomputed, HMR/R reset
        assert list(s.toff) == [2, 2, 2, 2]
        # CZ q2 q0 fires only for x = 3 (q2 = q0 AND q1, q0 = 1): phase half a turn
        assert list(s.ph == np.uint64(1 << 63)) == [False, False, False, True]
        assert not s.bad_reset.any()


def test_reset_error_detected():
    ops, _ = kmsim.parse(toy("X q0\nR q0\n"))
    s = kmsim.Sim(ops, 1, 1, 2)
    s.run()
    assert s.bad_reset.all()


def test_liveness_toy():
    ops, regs = kmsim.parse(toy())
    iv = liveness.intervals(ops, 4, set(regs["r0"]))
    assert liveness.max_overlap(iv) == 3                    # x0, x1 and the ancilla q2


def test_build_splice_roundtrip():
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "aaaaaaaaaaaa.kmx"), "w") as f:
        f.write(TOY)
    out = os.path.join(d, "spliced.kmx")
    build_splice.build([["aaaaaaaaaaaa", 0, 3]], out, d)
    ops, regs = kmsim.parse(out)
    assert [o[0] for o in ops] == ["CCX", "CZ", "CCX"] and regs == {"r0": [0, 1]}


def test_real_invsqrt_if_present():
    rows = list(csv.DictReader(open(os.path.join(ROOT, "circuits.csv")))) if os.path.exists(os.path.join(ROOT, "circuits.csv")) else []
    rows = [r for r in rows if r["task"] == "invsqrt" and r["included"] == "True" and r["verified_status"] == "PASS"]
    if not rows:
        print("skip: no verified invsqrt circuit in this folder")
        return
    rep, _ = kmsim.check(os.path.join(ROOT, rows[0]["included_path"]), np.arange(1, 65, dtype=np.int64))
    assert rep["restored"] and rep["dirty"] == 0 and rep["bad_reset"] == 0 and rep["worst_ratio"] < 1
    assert rep["nq"] == int(rows[0]["qubits"])


def test_family_rebuild_if_present():
    p = os.path.join(ROOT, "families.csv")
    if not os.path.exists(p):
        print("skip: no families.csv")
        return
    fam = next((r for r in csv.DictReader(open(p)) if r["complete_in_atlas"] == "True"), None)
    if fam is None:
        print("skip: no complete family")
        return
    import atlas_family
    d = tempfile.mkdtemp()
    files = atlas_family.materialise(fam["family_id"], d, ROOT)
    assert len(glob.glob(os.path.join(d, "angle_k_*.kmx"))) == int(fam["n_loaders"])
    assert os.path.exists(os.path.join(d, "submission.npz")) and len(files) == int(fam["n_loaders"]) + 1


if __name__ == "__main__":
    n = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok", name)
    print(f"{n} tests passed")
