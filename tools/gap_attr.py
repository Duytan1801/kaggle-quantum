#!/usr/bin/env python3
"""gap_attr.py — per-wake GAP ATTRIBUTION across the three benchmark legs.

WHY THIS TOOL EXISTS (the 2026-11-26 pipeline diagnosis)
----------------------------------------------------------
The campaign's evolutionary search produced 7,205 s of compute for a
0.00017 % fitness improvement, because no step ever asked the question
"which leg, and which construction, can close the gap to the leaderboard?"

This tool answers that question *exactly* every wake, from the measured cost
model:

    GM = (REF_invsqrt/cost_inv * REF_dqi/cost_dqi * REF_chem/cost_chem)^(1/3)

so a target leaderboard score T implies a total cost multiplier
f = (T / GM_now)^3.  Each leg then answers "what does f demand of ME?":

    invsqrt   cost ~ Q * (T_mean + T/4)   ->  Q_target = Q_now / f
    DQI       cost ~ Q^2 * T_mean          ->  Q_target = Q_now * sqrt(f)
    chemistry cost ~ lambda * T * Q        ->  T_target = T_now / f

and the tool also reports the *marginal* value of one unit in each leg
(1 qubit, 1 Toffoli), so the hypothesis queue can be re-ranked by what it is
actually worth.

Usage:
  gap_attr.py --board 34.50408 --out work/recon/gap_attr_<date>.md
  gap_attr.py --json          # machine-readable
"""
from __future__ import annotations

import argparse
import json
import pathlib

REF_INV = 2076774.233715282
REF_DQI = 24439463583672.93
REF_CH = 3355599588.3155375

# --- the measured v150/v151 state (2026-11-26) --------------------------------
# board DQI cost is the BOARD draw, not the local default-salt draw: the board
# uses a hidden salt, and the measured v150 score of 33.25564 pins it.
STATE = {
    "invsqrt": {"cost": 60927.54794503887, "Q": 37, "T_mean": 1406.3115550407745,
                "label": "6b592145 (prvsiyan), 37 q"},
    "dqi": {"cost": 305032258732.73, "Q": 900, "T_mean": 316122.95665039064,
            "label": "6f78ecdd (board draw)"},
    "chemistry": {"cost": 249131841.8273937, "Q": 405, "T": 13112,
                  "lambda": 46.91430370584927,
                  "label": "25ac10da + 5 re-solved loaders, T 13112"},
}


def gm_now(state: dict) -> float:
    return (REF_INV / state["invsqrt"]["cost"] *
            REF_DQI / state["dqi"]["cost"] *
            REF_CH / state["chemistry"]["cost"]) ** (1 / 3)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", type=float, default=34.50408,
                    help="the leaderboard score we are trying to reach")
    ap.add_argument("--out", type=pathlib.Path)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    st = STATE
    cur = gm_now(st)
    f = (a.board / cur) ** 3
    inv, dqi, ch = st["invsqrt"], st["dqi"], st["chemistry"]
    # The invsqrt cost per qubit is the verifier's toffoli_equivalent:
    #     eq = mean_toffoli + T/4
    # and the leg cost is Q * eq.  Removing one Toffoli lowers eq by 1, so the
    # leg cost falls by a factor (eq-1)/eq and the GM rises by the cube root.
    inv_eq = inv["T_mean"] + 1 / 4

    rows = {
        "current_gm": cur,
        "target": a.board,
        "cost_multiplier_needed": f,
        "cost_reduction_pct": 100 * (1 - 1 / f),
        "legs": {
            "invsqrt": {
                "cost": inv["cost"], "Q": inv["Q"],
                "Q_target_single_leg": inv["Q"] / f,
                "Q_target_rounded": round(inv["Q"] / f),
                # one FEWER qubit: cost scales linearly in Q, so cost' = cost*(Q-1)/Q
                "value_per_qubit": cur * (inv["Q"] / (inv["Q"] - 1)) ** (1 / 3) - cur,
                # one fewer Toffoli: cost' = cost * (eq-1)/eq, where eq is the
                # verifier's toffoli_equivalent (mean_toffoli + T/4).
                # one fewer Toffoli: cost' = cost * (eq-1)/eq, so the GM is
                # multiplied by (eq/(eq-1))^(1/3).
                "value_per_toffoli": cur * (inv_eq / (inv_eq - 1)) ** (1 / 3) - cur,
            },
            "dqi": {
                "cost": dqi["cost"], "Q": dqi["Q"],
                "Q_target_single_leg": dqi["Q"] * f ** 0.5,
                "Q_target_rounded": round(dqi["Q"] * f ** 0.5),
                # one fewer qubit: DQI cost ~ Q^2, so cost' = cost*((Q-1)/Q)^2
                "value_per_qubit": cur * ((dqi["Q"] / (dqi["Q"] - 1)) ** 2) ** (1 / 3) - cur,
                "value_per_toffoli": cur * (dqi["T_mean"] / (dqi["T_mean"] - 1)) ** (1 / 3) - cur,
            },
            "chemistry": {
                "cost": ch["cost"], "Q": ch["Q"], "T": ch["T"],
                "T_target_single_leg": ch["T"] / f,
                "T_target_rounded": round(ch["T"] / f),
                "value_per_toffoli": cur * (ch["T"] / (ch["T"] - 1)) ** (1 / 3) - cur,
            },
        },
    }
    # the ladder: what each width step is worth
    ladder = []
    for q in range(36, 28, -1):
        c = inv["cost"] * q / inv["Q"]
        g = (REF_INV / c * REF_DQI / dqi["cost"] * REF_CH / ch["cost"]) ** (1 / 3)
        ladder.append({"invsqrt_Q": q, "gm": g, "gain": g - cur})
    rows["invsqrt_width_ladder"] = ladder
    for q in (890, 880, 870, 860, 852, 840):
        c = dqi["cost"] * (q / dqi["Q"]) ** 2
        g = (REF_INV / inv["cost"] * REF_DQI / c * REF_CH / ch["cost"]) ** (1 / 3)
        rows.setdefault("dqi_width_ladder", []).append(
            {"dqi_Q": q, "gm": g, "gain": g - cur})
    for t in (13000, 12500, 12000, 11741):
        c = ch["cost"] * t / ch["T"]
        g = (REF_INV / inv["cost"] * REF_DQI / dqi["cost"] * REF_CH / c) ** (1 / 3)
        rows.setdefault("chemistry_T_ladder", []).append(
            {"T": t, "gm": g, "gain": g - cur})

    if a.json:
        print(json.dumps(rows, indent=2))
        return
    L = []
    L.append(f"# Gap attribution — target {a.board}  ({a.out and a.out.name or 'stdout'})\n")
    L.append(f"Current GM (measured v150 board draw): **{cur:.5f}**")
    L.append(f"Target: **{a.board}**")
    L.append(f"Total cost multiplier needed: **x{f:.5f}** "
             f"(a {rows['cost_reduction_pct']:.2f} % cost cut)\n")
    L.append("## Which leg can close it (single-leg, everything else fixed)\n")
    L.append("| leg | now | single-leg target to hit the target | verdict |")
    L.append("|---|---:|---:|---|")
    L.append(f"| invsqrt | {inv['Q']} q / {inv['cost']:,.2f} | "
             f"**{rows['legs']['invsqrt']['Q_target_rounded']} q** | "
             f"the only lane with the needed headroom |")
    L.append(f"| DQI | {dqi['Q']} q / {dqi['cost']:,.0f} | "
             f"**{rows['legs']['dqi']['Q_target_rounded']} q** | "
             f"H22 closed; Entangled Team's own decoder is also 900 q |")
    L.append(f"| chemistry | T {ch['T']} / {ch['cost']:,.2f} | "
             f"**T {rows['legs']['chemistry']['T_target_rounded']}** | "
             f"H48 killed; at most +0.24 GM from loader work |")
    L.append("\n## Marginal value of one unit\n")
    L.append(f"- 1 invsqrt qubit: **+{rows['legs']['invsqrt']['value_per_qubit']:.4f} GM**")
    L.append(f"- 1 invsqrt Toffoli: **+{rows['legs']['invsqrt']['value_per_toffoli']:.5f} GM**")
    L.append(f"- 1 DQI qubit: **+{rows['legs']['dqi']['value_per_qubit']:.4f} GM**")
    L.append(f"- 1 DQI Toffoli: **+{rows['legs']['dqi']['value_per_toffoli']:.6f} GM**")
    L.append(f"- 1 chemistry Toffoli: **+{rows['legs']['chemistry']['value_per_toffoli']:.5f} GM**")
    L.append("\n## invsqrt width ladder (the decisive lane)\n")
    L.append("| Q | GM | gain vs now |")
    L.append("|---:|---:|---:|")
    for r in ladder:
        L.append(f"| {r['invsqrt_Q']} | {r['gm']:.5f} | {r['gain']:+.5f} |")
    L.append("\n## DQI width ladder\n")
    L.append("| Q | GM | gain vs now |")
    L.append("|---:|---:|---:|")
    for r in rows.get("dqi_width_ladder", []):
        L.append(f"| {r['dqi_Q']} | {r['gm']:.5f} | {r['gain']:+.5f} |")
    L.append("\n## chemistry T ladder\n")
    L.append("| T | GM | gain vs now |")
    L.append("|---:|---:|---:|")
    for r in rows.get("chemistry_T_ladder", []):
        L.append(f"| {r['T']} | {r['gm']:.5f} | {r['gain']:+.5f} |")
    L.append("\n## Reading\n")
    L.append("The public frontier (34.50408) needs the WHOLE cost cut from ONE leg.")
    L.append("invsqrt at 33 q reaches 34.548 (> target); DQI at 852 q reaches")
    L.append("34.493; chemistry at T 11741 reaches 34.504. All three are single-leg")
    L.append("paths, so the search must know which ONE it is attacking — that is what")
    L.append("this table is for. A hypothesis that cannot name its leg and its")
    L.append("required width is not a hypothesis, it is a wish.")
    text = "\n".join(L) + "\n"
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text)
        print(f"wrote {a.out}")
        print(text[:1200])
    else:
        print(text)


if __name__ == "__main__":
    main()
