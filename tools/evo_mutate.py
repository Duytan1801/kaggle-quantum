#!/usr/bin/env python3
"""evo_mutate.py — propose the next generation of generator variants.

This is the AlphaEvolve "prompt sampler + mutation" half of the loop.  It reads
the durable population (evo_engine), samples parents from three archives
(performance / width / mechanism), and writes NEW candidate configs as one-knob
diffs.  The evaluator, not the proposer, decides whether a diff is good.

Two plans:
  first   a pre-registered, priority-ordered sweep of the H1 live-count levers,
          including the width-cap x live-lever combinations that the serial
          campaign never tried as a matrix
  random  sample a knob delta per selected parent (exploration)

Usage
  evo_mutate.py --generation gen001 --plan first
  evo_mutate.py --generation gen002 --plan random --n 6
  evo_mutate.py --seed-known          # register the already-measured facts
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "work/tools"))
import evo_engine as E  # noqa: E402

REG = ROOT / "work/evo/knobs/isr.json"
GEN = ROOT / "work/evo/generations"

BASELINE = {
    "leg": "invsqrt",
    "builder": "isr",
    "source": "work/gens/q2026_v154/isr",
    "caps": "",
    "env": {"S5LEND": "1"},
    "stack_env": {},
}


def merge(base: dict, delta: dict) -> dict:
    cfg = copy.deepcopy(base)
    for k in ("caps", "keep_r56", "timeout"):
        if k in delta:
            cfg[k] = delta[k]
    for field in ("env", "stack_env"):
        if delta.get(field):
            cfg.setdefault(field, {})
            cfg[field].update(delta[field])
    return cfg


def add_delta(name: str, mechanism: str, delta: dict, parent: int | None,
              base: dict, note: str = "") -> int | None:
    cfg = merge(base, delta)
    cid, new = E.add(leg="invsqrt", name=name, config=cfg, parent=parent,
                     mechanism=mechanism, island=f"invsqrt:{mechanism}",
                     note=note or json.dumps(delta, sort_keys=True))
    if new:
        print(f"  + c{cid:04d} {mechanism:<12} {name}")
        return cid
    print(f"  = c{cid:04d} {mechanism:<12} {name} (already in population)")
    return None


def seed_known() -> None:
    """Register facts already measured before the engine existed.

    Without this the first worker generation re-runs experiments the campaign
    has already paid for — the exact amnesia the population store exists to stop.
    """
    base = copy.deepcopy(BASELINE)
    E.add("invsqrt", "known_default_39q", base, mechanism="baseline",
          status="SCORED", score=62993.5511616945,
          score_model=62993.5511616945,
          features={"Q": 39, "toffoli_like": 1493, "t_like": 3,
                    "generic_rotations": 33, "ops": 24387},
          artifacts={"sha256": "68eb8c13ebc75", "note": "byte-exact default build"},
          note="known: q2026-v154 ISR default, official PASS 62,993.5511616945 @39q")
    E.add("invsqrt", "known_S5LEND0", merge(base, {"env": {"S5LEND": "0"}}),
          mechanism="endpoint", status="SCORED", score=63098.90656123393,
          score_model=63098.90656123393,
          features={"Q": 39, "toffoli_like": 1493, "t_like": 3, "generic_rotations": 33},
          artifacts={"sha256": "864dbb1f5decd7b3",
                     "receipt": "work/receipts/H30_S5LEND0_LOCAL_INVSQRT_VERIFY.log"},
          note="known: official PASS 63,098.90656123393 @39q (dominated)")
    E.add("invsqrt", "known_FXACCCAP29", merge(base, {"stack_env": {"FXACCCAP": "29"}}),
          mechanism="h1_acc", status="SCORED", score_model=62962.6,
          features={"Q": 39, "toffoli_like": 1493, "t_like": 3, "generic_rotations": 33,
                    "ops": 22820},
          artifacts={"sha256": "709c9452ae261096"},
          note="known: 39q, 22,820 ops; no width win")
    E.add("invsqrt", "known_R56J", merge(base, {"env": {"R56_LEV": "J"},
                                                "keep_r56": True}),
          mechanism="divider", status="SCORED", score_model=62962.6,
          features={"Q": 39, "toffoli_like": 1493, "t_like": 3, "generic_rotations": 33,
                    "ops": 22820},
          artifacts={"sha256": "709c9452ae261096"},
          note="known: R56_LEV=J, 39q, 22,820 ops; no width win")
    E.add("invsqrt", "known_caps38_H1", merge(base, {"caps": "H1=38,DIV1=38,DIV2=38,END=38"}),
          mechanism="width", status="FAILED", stage="build",
          note="known KILLED: no schedule within 1 temporaries at H1 (live=37+2 clean)")


# Pre-registered first generation.  Ordered by expected width signal per
# build-minute: a live-count lever first, then the cap-38 matrix that only
# becomes feasible if that lever actually removes a live wire.
FIRST = [
    ("FC_XFREE", "wire_free", {"stack_env": {"FC_XFREE": "1"}}),
    ("FC_RELAX_ALL0", "wire_free", {"stack_env": {"FC_RELAX_ALL": "0"}}),
    ("C1WIDE", "h1_add", {"stack_env": {"C1WIDE": "1"}}),
    ("C1INIT", "h1_add", {"stack_env": {"C1INIT": "1"}}),
    ("CHIACC0", "h1_acc", {"stack_env": {"CHIACC": "0"}}),
    ("CHIMODE_plain", "h1_acc", {"stack_env": {"CHIMODE": "plain"}}),
    ("CHIPROG8", "h1_acc", {"stack_env": {"CHIPROG8": "1"}}),
    ("FC2_S_5_7", "h1_split", {"stack_env": {"FC2_S": "5,7"}}),
    ("C1MIX0", "h1_add", {"stack_env": {"C1MIX": "0"}}),
    ("C1MIXBEST0", "h1_add", {"stack_env": {"C1MIXBEST": "0"}}),
]
CAPS38 = "H1=38,DIV1=38,DIV2=38,END=38"
COMBOS = [
    ("caps38_FC_XFREE", "width_x_wire_free",
     {"caps": CAPS38, "stack_env": {"FC_XFREE": "1"}}),
    ("caps38_C1WIDE", "width_x_h1_add",
     {"caps": CAPS38, "stack_env": {"C1WIDE": "1"}}),
    ("caps38_CHIACC0", "width_x_h1_acc",
     {"caps": CAPS38, "stack_env": {"CHIACC": "0"}}),
    ("caps38_C1MIX0", "width_x_h1_add",
     {"caps": CAPS38, "stack_env": {"C1MIX": "0"}}),
    ("caps38_FC_RELAX0", "width_x_wire_free",
     {"caps": CAPS38, "stack_env": {"FC_RELAX_ALL": "0"}}),
    ("caps38_FC2_S_5_7", "width_x_h1_split",
     {"caps": CAPS38, "stack_env": {"FC2_S": "5,7"}}),
]


def plan_first(generation: str) -> list[int]:
    base = copy.deepcopy(BASELINE)
    made = []
    for name, mech, delta in FIRST:
        cid = add_delta(name, mech, delta, None, base)
        if cid:
            made.append(cid)
    for name, mech, delta in COMBOS:
        cid = add_delta(name, mech, delta, None, base)
        if cid:
            made.append(cid)
    return made


def plan_random(generation: str, n: int, seed: int) -> list[int]:
    reg = json.loads(REG.read_text())
    knobs = reg["knobs"]
    parents = E.select_parents("invsqrt", max(2, n))
    if not parents:
        print("no parents; seeding baseline")
        cid, _ = E.add("invsqrt", "random_baseline", copy.deepcopy(BASELINE),
                       mechanism="baseline")
        parents = [E.get(cid)]
    rng = random.Random(seed)
    made = []
    for i in range(n):
        parent = parents[i % len(parents)]
        cfg = json.loads(parent["config"])
        knob = rng.choice(knobs)
        val = rng.choice(knob["domain"])
        delta = {}
        if knob["where"] == "caps":
            delta["caps"] = val
        elif knob["where"] == "env":
            delta["env"] = {knob["name"]: val}
            if knob["name"] == "R56_LEV":
                delta["keep_r56"] = True
        else:
            delta["stack_env"] = {knob["name"]: val}
        name = f"r{seed}_{i:02d}_{knob['name']}_{str(val).replace(',', '-').replace(';', '_') or 'empty'}"
        cid = add_delta(name, knob["mechanism"], delta, parent["id"], cfg,
                        note=f"random mutation of c{parent['id']:04d}: {knob['name']}={val}")
        if cid:
            made.append(cid)
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generation", default="gen001")
    ap.add_argument("--plan", choices=["first", "random"], default="first")
    ap.add_argument("--n", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--seed-known", action="store_true")
    a = ap.parse_args()
    E.init_db()
    if a.seed_known:
        seed_known()
        return
    GEN.mkdir(parents=True, exist_ok=True)
    made = plan_first(a.generation) if a.plan == "first" else plan_random(
        a.generation, a.n, a.seed)
    manifest = {"generation": a.generation, "plan": a.plan,
                "created": E.now(), "candidate_ids": made}
    p = GEN / f"{a.generation}.json"
    p.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(made)} new candidates -> {p}")


if __name__ == "__main__":
    main()
