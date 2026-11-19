"""Markdown report for one circuit (or a chemistry loader family)."""
from __future__ import annotations

import os
import time

import numpy as np

from . import cost as C
from . import kmx, liveness as L, motifs as M, structure as St, values as Vv


def _tab(rows: list[dict], cols: list[str], fmt: dict | None = None) -> str:
    fmt = fmt or {}
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        cells = []
        for c in cols:
            v = r.get(c, "")
            f = fmt.get(c)
            cells.append(f.format(v) if f and v != "" else str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def exchange_section() -> str:
    rows = C.exchange_table()
    g = C.target_gap()
    s = ["## Exchange rates (exact, from the verifier formulas)", "",
         _tab(rows, ["task", "cost", "score", "pts_per_toffoli", "pts_per_qubit", "toffoli_per_qubit"],
              {"cost": "{:.6g}", "score": "{:.4f}", "pts_per_toffoli": "{:.3g}", "pts_per_qubit": "{:.4f}",
               "toffoli_per_qubit": "{:.1f}"}),
         "", f"GM now {C.gm():.5f}; target {C.GM_TARGET} needs a total log-cost cut of {g['log_cost_cut']:.4f} "
             f"(= {g['pct_one_task']:.2f} % of one task's cost). Chem Toffoli = loader Toffoli per pass (counted twice).", ""]
    return "\n".join(s)


def _find_npz(path: str):
    import glob
    c = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(path)), "*.npz")))
    return c[0] if c else None


def analyse(path: str, task: str, lanes: int = 256, exhaustive: bool = False, values: bool = True,
            cache_dir: str | None = None, width_lanes: int = 0, npz: str | None = None) -> dict:
    t0 = time.time()
    circ = kmx.load(path, cache_dir=cache_dir)
    lv = L.compute(circ)
    S = St.scan(circ)
    V = None
    if values:
        if task == "invsqrt":
            inp = Vv.inputs_invsqrt(circ, lanes, exhaustive=exhaustive)
            lanes = inp.get("lanes", lanes)
        elif task == "dqi":
            inp = Vv.inputs_dqi(circ, lanes)
        else:
            npz = npz or _find_npz(path)
            words = np.load(npz)["angle_words"] if npz else None
            inp = Vv.inputs_chem(circ, words=words)
            lanes = inp["lanes"]
            exhaustive = words is not None   # only the family context (old words loaded) is the true input set
        V = Vv.run(circ, inp, S=lanes, min_gap=4 if circ.n_ops < 200_000 else 16)
    ep = L.episode_report(circ, lv)
    gad = St.gadget_census(circ, lv.width, block=512 if circ.n_ops < 200_000 else 4096)
    exhaustive = exhaustive and task in ("invsqrt", "chem")
    fnd = M.findings(task, circ, lv, S, V, exhaustive=exhaustive)
    if task == "invsqrt":
        fnd += M.invsqrt_extras(circ)
    wt = None
    if width_lanes and task != "chem":
        if task == "invsqrt":
            winp = Vv.inputs_invsqrt(circ, width_lanes)
        else:
            winp = Vv.inputs_dqi(circ, width_lanes)
        wt = Vv.episode_rebuild(circ, lv, winp, width_lanes)
        n_ok = sum(1 for x in wt if x["rebuildable"])
        fnd.append(M._f("E2", f"free CX rebuild of an idle dependent wire: {n_ok}/{len(wt)} peak episodes", n_ok, 0,
                        1 if n_ok == len(wt) else 0, task, "sampled",
                        f"{width_lanes} lanes; one qubit less only if every episode has one"))
    return dict(width_test=wt, path=path, task=task, circ=circ, lv=lv, S=S, V=V, ep=ep, gad=gad, findings=fnd,
                seconds=time.time() - t0, exhaustive=exhaustive)


def timeline(circ: kmx.Circuit, lv, V, bins: int = 12) -> str:
    n = circ.n_ops
    edges = np.linspace(0, n, bins + 1).astype(np.int64)
    tops = np.flatnonzero(np.isin(circ.op, kmx.TOFFOLI_OPS))
    h_t = np.histogram(tops, edges)[0]
    rows = []
    rep2 = np.histogram([k for _, k in V.repeats], edges)[0] if V is not None and V.repeats else np.zeros(bins, int)
    zp = np.histogram(np.flatnonzero(circ.op == kmx.ZPOW), edges)[0]
    for i in range(bins):
        s, e = edges[i], edges[i + 1]
        rows.append(dict(ops=f"{s}-{e}", toffoli=int(h_t[i]), recomputed=int(rep2[i]), z_pow=int(zp[i]),
                         width_max=int(lv.width[s:e].max()) if e > s else 0,
                         width_mean=float(lv.width[s:e].mean()) if e > s else 0))
    return _tab(rows, ["ops", "toffoli", "recomputed", "z_pow", "width_max", "width_mean"], {"width_mean": "{:.1f}"})


def render(res: dict) -> str:
    circ, lv, S, V, ep, gad = res["circ"], res["lv"], res["S"], res["V"], res["ep"], res["gad"]
    task = res["task"]
    cen = S.census
    out = [f"# qccscope report: `{os.path.basename(res['path'])}` (task {task})", "",
           f"ops {circ.n_ops:,}; qubits {circ.num_qubits}; bits {circ.num_bits}; static Toffoli-like "
           f"{cen['_static_toffoli']:,} (conditional {cen['_conditional_toffoli']:,}); analysis {res['seconds']:.1f} s", ""]
    if V is not None:
        out += [f"Value scan: {V.lanes:,} {'inputs (EXHAUSTIVE)' if res['exhaustive'] else 'sampled inputs'}; "
                f"executed Toffoli mean {V.toffoli_exec_mean:,.2f}; end state {V.end_ok}", ""]
    out.append(exchange_section())
    out += ["## Census", "", _tab([dict(op=k, total=v["total"], conditional=v["conditional"]) for k, v in cen.items()
                                    if not k.startswith("_")], ["op", "total", "conditional"]), ""]
    out += ["## Toffoli kinds (static)", "",
            _tab([dict(kind=k, count=v) for k, v in S.toffoli_kinds.most_common()], ["kind", "count"]), "",
            f"MBU erasures (HMR of a wire last written by an AND): {S.mbu_erasures}; conditional Toffolis {S.cond_toffolis}", ""]
    out += ["## Timeline (cost attribution by position)", "", timeline(circ, lv, V), ""]
    out += ["## Gadget census (segments at width valleys; equal up to wire renaming)", "",
            f"{gad['n_segments']} segments, {gad['n_distinct']} distinct; share of Toffolis in repeated gadgets "
            f"{100 * gad['repeated_share']:.1f} %", "",
            _tab(gad["top"][:15], ["sig", "instances", "toffoli_each", "wires", "ops", "first", "peak"]), ""]
    out += ["## Width", "",
            f"static peak {lv.peak}; ops at peak {ep['ops_at_level']:,}; episodes {ep['n_episodes']}", "",
            f"episode openers: {ep.get('openers')}", "",
            f"greedy idle cover (wire, episodes covered, ops covered): {ep.get('greedy_cover')}; uncoverable "
            f"{ep.get('uncoverable_episodes')}", "",
            f"longest-lived non-register wires (wire, open, close, length): {L.long_lived(lv, 6)}", ""]
    wt = res.get("width_test")
    if wt is not None:
        bad = [x for x in wt if not x["rebuildable"]]
        out += [f"width test: {len(wt) - len(bad)} of {len(wt)} peak episodes have an idle wire that is an XOR of the "
                f"other live wires at both ends; blocking episodes (start, length, idle wires): "
                f"{[(x['s'], x['length'], x['idle']) for x in bad[:12]]}", ""]
    out += ["## Structure", "",
            f"carry-like ladders (start op, length) top 10: {S.ladders[:10]} (total {len(S.ladders)} ladders of length >= 4)", "",
            f"CX fanout runs (length: count), longest 6: {sorted(S.fanout_runs.items())[-6:]}", "",
            f"multiplicative depth: max {max(S.depth_hist) if S.depth_hist else 0}", ""]
    if V is not None:
        out += [f"value scan: const0 {len(V.const0)}, affine {len(V.affine)}, CSWAP no-op {len(V.swap_noop)}, "
                f"always-swap {len(V.swap_always)}, repeated products {len(V.repeats)} (distinct products "
                f"{V.repeat_groups}), zero gaps {len(V.zero_gaps)}", ""]
    out += ["## Findings (estimated saving and leaderboard points)", "",
            _tab(sorted(res["findings"], key=lambda r: -r["points"]),
                 ["id", "motif", "count", "d_toffoli", "d_qubits", "points", "confidence", "note"],
                 {"d_toffoli": "{:.1f}", "points": "{:+.4f}"}), "",
            "Confidence: exact = proven statically or on all inputs; sampled = seen on the samples only (verify before "
            "use); bound = ceiling / what-if, not a construction.", ""]
    out += ["## Earlier measured results for this task (not redone)", ""] + [f"* {h}" for h in M.HISTORY.get(task, [])]
    return "\n".join(out) + "\n"


def render_family(results: list[dict]) -> str:
    """Chemistry: the 15 loaders together (Toffolis per pass add up; qubits = max)."""
    rows = []
    for r in results:
        S, V = r["S"], r["V"]
        rows.append(dict(file=os.path.basename(r["path"]), qubits=r["circ"].num_qubits,
                         toffoli=S.census["_static_toffoli"],
                         cache_ands=S.toffoli_kinds.get("CCX->fresh (AND compute)", 0),
                         products=S.toffoli_kinds.get("CCX->busy (accumulate)", 0),
                         mbu=S.mbu_erasures, peak=r["lv"].peak,
                         exec_mean=V.toffoli_exec_mean if V else "",
                         findings_pts=sum(f["points"] for f in r["findings"] if f["confidence"] == "exact")))
    tot = sum(r["toffoli"] for r in rows)
    m = C.MODELS["chem"]
    out = ["# qccscope report: chemistry loader family", "", exchange_section(),
           "## Loaders", "", _tab(rows, ["file", "qubits", "toffoli", "cache_ands", "products", "mbu", "peak",
                                         "exec_mean", "findings_pts"], {"findings_pts": "{:+.4f}"}), "",
           f"total loader Toffolis per pass {tot} (verifier counts {m.loader_toffoli_per_pass:.0f} per pass, x2 passes); "
           f"products {sum(r['products'] for r in rows)}, cache ANDs {sum(r['cache_ands'] for r in rows)}", "",
           f"value of 1 loader Toffoli per pass: {C.saving_points('chem', d_toffoli=1):.5f} pts; of 25 per loader x 15: "
           f"{C.saving_points('chem', d_toffoli=375):.4f} pts", ""]
    allf = {}
    for r in results:
        for f in r["findings"]:
            a = allf.setdefault(f["id"], dict(f, count=0, d_toffoli=0.0))
            a["count"] += f["count"]; a["d_toffoli"] += f["d_toffoli"]
    for a in allf.values():
        a["points"] = C.saving_points("chem", d_toffoli=a["d_toffoli"]) if a["d_toffoli"] else 0.0
    out += ["## Findings summed over the family", "",
            _tab(sorted(allf.values(), key=lambda r: -r["points"]), ["id", "motif", "count", "d_toffoli", "points",
                                                                      "confidence", "note"],
                 {"d_toffoli": "{:.1f}", "points": "{:+.4f}"}), ""]
    out += ["## Earlier measured results (not redone)", ""] + [f"* {h}" for h in M.HISTORY["chem"]]
    return "\n".join(out) + "\n"
