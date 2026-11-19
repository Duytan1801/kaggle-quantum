#!/usr/bin/env python3
"""Write contributions/ of the QCC Circuit Atlas (v2): our own public results, each with a README, a machine-readable
index (contributions/index.json) and the official-verifier receipts of our public notebook versions.

Only results that are already public on Kaggle are listed (the outputs of public versions of our notebooks). The
circuit and factorization files themselves live in the atlas store (kmx/invsqrt/, factorizations/); this script
only writes metadata, recipes and receipts, and the kmx text of the invsqrt dead-write fix (--derived-kmx-dir),
which build_atlas.py then stores like every other kmx text.

    python build_contrib.py --dataset DATASET --receipts-root DIR --chem-metrics chem_metrics.json \\
        --dcde-kmx invsqrt__dcde7078.kmx --derived-kmx-dir DIR

Run it before build_atlas.py (the atlas README reads contributions/index.json). Licence: Apache-2.0.
"""
import argparse
import csv
import hashlib
import json
import math
import os
import time

KAGGLE = "https://www.kaggle.com"
REF = {"invsqrt": 2076774.23, "dqi": 24439463583672.93, "dfthcsos": 3355599588.32}
NB = {
    "lb": ("asteriospanoras/lb-25-367-verified-portfolio-dqi-readout-fix", "LB 25.367 | Verified Portfolio + DQI Readout Fix"),
    "cz": ("asteriospanoras/qcc-27-30-public-frontier-free-cz-fix-in-invsq", "QCC 27.30 | Public Frontier + Free CZ Fix in invsq"),
    "ref": ("asteriospanoras/qcc-27-3122-frontier-finer-chemistry-refit", "QCC 27.3122 | Frontier + Finer Chemistry Refit"),
    "ana": ("asteriospanoras/qcc-27-30-what-works-what-fails-and-why", "QCC 27.30 | What Works, What Fails and Why"),
}
# receipt id (our run folder) -> notebook, version, submitted to the leaderboard by us
RECEIPTS = [
    ("out8", "lb", 1, "yes"), ("out21", "lb", 4, "unknown"), ("out23", "lb", 5, "yes"),
    ("out27", "cz", 1, "yes"), ("out29", "cz", 2, "no"), ("out33", "cz", 5, "yes"),
    ("out30", "cz", 3, "no"), ("out34", "cz", 6, "no"),
    ("out35", "ana", 7, "yes"), ("out36", "ana", 8, "no"), ("out38", "ana", "unknown", "unknown"),
    ("out37", "ref", 2, "yes"), ("out39", "ref", 4, "no"), ("out40", "ref", 5, "yes"),
]
SPLICE_SEGMENTS = [["034c7c2a54d5", 0, 69], ["13b5bf7a18bc", 81, 83], ["26ebf39df3b1", 71, 92], ["94b29cc52689", 118, 479],
                   ["034c7c2a54d5", 235, 421], ["5ec4f516164c", 515, 36611], ["034c7c2a54d5", 36245, 36409],
                   ["5ec4f516164c", 36867, 36869], ["6c6a734dbcb6", 36857, 36859], ["94b29cc52689", 36549, 36553],
                   ["13b5bf7a18bc", 53614, 53616], ["034c7c2a54d5", 36419, 36423], ["13b5bf7a18bc", 53620, 53622],
                   ["26ebf39df3b1", 36634, 36636], ["ac540b8eff24", 46889, 46897], ["034c7c2a54d5", 36437, 36477]]


def nb_url(k):
    return f"{KAGGLE}/code/{NB[k][0]}"


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = text.encode("utf-8") if isinstance(text, str) else text
    if os.path.exists(path) and open(path, "rb").read() == data:
        return
    with open(path, "wb") as f:
        f.write(data)


def jdump(obj):
    return json.dumps(obj, indent=1, sort_keys=False, ensure_ascii=False, default=float) + "\n"


def derive_dead_write_fix(src, out_dir):
    """dcde7078 kmx -> e46d90c3 kmx: op 3292 `CCX q16 q20 q21` -> `HMR q21 b61` + `CZ q16 q20 if b61`, op 3403 removed."""
    lines = open(src).read().splitlines()
    ol = [i for i, l in enumerate(lines) if l.split() and l.split()[0] not in ("APPEND_TO_REGISTER", "REGISTER", "INFO_TAG", "DEBUG_PRINT")]
    i1, i2 = ol[3292], ol[3403]
    assert lines[i1] == "CCX q16 q20 q21" and lines[i2] == "HMR q21 b61", (lines[i1], lines[i2])
    assert not any("b61" in l.split() for l in lines[:i2]), "b61 must be unused before the moved HMR"
    new = lines[:i1] + ["HMR q21 b61", "CZ q16 q20 if b61"] + lines[i1 + 1:i2] + lines[i2 + 1:]
    os.makedirs(out_dir, exist_ok=True)
    dst = os.path.join(out_dir, "invsqrt__e46d90c36d1b.kmx")
    write(dst, "\n".join(new) + "\n")
    return dict(base_kmx_sha256=hashlib.sha256(open(src, "rb").read()).hexdigest(),
                kmx_sha256=hashlib.sha256(open(dst, "rb").read()).hexdigest(),
                kmx_line_of_op_3292=i1 + 1, kmx_line_of_op_3403=i2 + 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--receipts-root", required=True, help="folder with our run folders (<id>/receipt.json)")
    ap.add_argument("--chem-metrics", required=True, help="json written by the chemeval check of the refits and their bases")
    ap.add_argument("--dcde-kmx", required=True, help="kmx text of dcde7078 (kickmix export)")
    ap.add_argument("--derived-kmx-dir", required=True)
    ap.add_argument("--kmsim-full", default="", help="kmsim output over every x for the dead-write fix (text)")
    a = ap.parse_args()
    C = os.path.join(a.dataset, "contributions")
    circ = {r["sha12"]: r for r in csv.DictReader(open(os.path.join(a.dataset, "circuits.csv")))} \
        if os.path.exists(os.path.join(a.dataset, "circuits.csv")) else {}

    def full(h12, fallback=""):
        return (circ.get(h12, {}).get("sha256") or fallback)

    def who(h12):
        r = circ.get(h12)
        return f"{r['first_source_ref']}" if r else "(not in circuits.csv)"

    # ---------------------------------------------------------------- receipts
    rec_rows, receipts = [], {}
    for rid, nb, ver, sub in RECEIPTS:
        p = os.path.join(a.receipts_root, rid, "receipt.json")
        r = json.load(open(p))
        date = time.strftime("%Y-%m-%d %H:%M", time.gmtime(os.path.getmtime(p)))
        v = r["verify"]
        gm = math.prod(REF[t] / v[t]["score"] for t in REF) ** (1 / 3)
        rel = f"contributions/receipts/{rid}__{NB[nb][0].split('/')[1]}__v{ver}.json"
        doc = dict(receipt_id=rid, notebook=NB[nb][0], notebook_title=NB[nb][1], notebook_url=nb_url(nb), version=ver,
                   output_downloaded_utc=date, submitted_by_us=sub, geometric_mean_score=gm, **r)
        write(os.path.join(a.dataset, rel), jdump(doc))
        receipts[rid] = dict(path=rel, notebook=nb, version=ver, date=date[:10], v=v, sha=r["sha256"], gm=gm)
        rec_rows.append(dict(receipt_id=rid, file=rel.split("/")[-1], notebook=NB[nb][0], version=ver,
                             output_downloaded_utc=date, submitted_by_us=sub,
                             invsqrt_sha12=r["sha256"]["invsqrt.kmb"][:12], dqi_sha12=r["sha256"]["dqi.kmb"][:12],
                             chem_npz_sha12=r["sha256"]["dfthcsos/submission.npz"][:12],
                             chem_loader_k0_sha12=r["sha256"].get("dfthcsos/angle_k_0.kmb", "")[:12],
                             invsqrt_score=v["invsqrt"]["score"], dqi_score=v["dqi"]["score"], chem_score=v["dfthcsos"]["score"],
                             chem_lambda_eff=v["dfthcsos"].get("lambda_eff"), dqi_value_errors=v["dqi"].get("value_errors"),
                             dqi_phase_errors=v["dqi"].get("phase_errors"), geometric_mean_score=round(gm, 6),
                             all_pass=all(v[t].get("status") == "PASS" for t in REF)))
    cols = list(rec_rows[0])
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, cols, lineterminator="\n")
    w.writeheader()
    w.writerows(rec_rows)
    write(os.path.join(C, "receipts", "receipts.csv"), buf.getvalue())

    def rlink(rid):
        r = receipts[rid]
        return f"[{NB[r['notebook']][1]}]({nb_url(r['notebook'])}) version {r['version']}"

    # ---------------------------------------------------------------- invsqrt
    dw = derive_dead_write_fix(a.dcde_kmx, a.derived_kmx_dir)
    kms = {}
    if a.kmsim_full and os.path.exists(a.kmsim_full):
        for line in open(a.kmsim_full):
            t = line.split()
            if len(t) == 2:
                kms[t[0]] = t[1]
    inv21, inv33 = receipts["out21"]["v"]["invsqrt"], receipts["out33"]["v"]["invsqrt"]
    BASE_DCDE = dict(score=78765.51312151134, toffoli_count=1480.7496921576028, num_qubits=46, rotation_count=33.0,
                     worst_error_over_tolerance=0.9986660009092673,
                     source="official verifier record in the public output of atakanaldemir/quantum-circuits-iso-gap-dqi-h5 (inverse_fresh_full64.json)")
    BASE_94B2 = dict(score=93739.35118674506, toffoli_count=1216.8341952521532, rotation_count=41.0,
                     worst_error_over_tolerance=0.9993237694056958, source="official verifier, our splice run (same run as the splice)")
    index = {}
    index["invsqrt_splice_62q"] = dict(
        task="invsqrt", sha12="9c708f7b9abc", sha256=full("9c708f7b9abc", inv21["circuit_sha256"]), path="kmx/invsqrt/9c708f7b9abc.kmx",
        what="Cheapest splice of public 62-qubit invsqrt circuits at clean cuts (identical qubit state and phase).",
        official=dict(score=inv21["score"], toffoli_count=inv21["toffoli_count"], num_qubits=inv21["num_qubits"],
                      worst_error_over_tolerance=inv21.get("worst_error_over_tolerance")),
        baseline=dict(sha12="94b29cc52689", **BASE_94B2),
        cost_change_percent=100 * (inv21["score"] / BASE_94B2["score"] - 1),
        first_public=dict(notebook=NB["lb"][0], url=nb_url("lb"), version=4, date_utc=receipts["out21"]["date"]),
        receipts=["out21", "out23", "out27"], segments=SPLICE_SEGMENTS)
    index["invsqrt_dead_write_fix"] = dict(
        task="invsqrt", sha12="e46d90c36d1b", sha256=inv33["circuit_sha256"], path="kmx/invsqrt/e46d90c36d1b.kmx",
        what="Dead-write fix on dcde7078: a CCX whose target is only X-measured afterwards becomes an HMR plus a classically controlled CZ.",
        base=dict(sha12="dcde70780434", sha256=full("dcde70780434", "dcde70780434501912c5cc032c6dfad25ac694d50da4e8e45cdb65115baa81b2"),
                  path="kmx/invsqrt/dcde70780434.kmx", **BASE_DCDE),
        recipe=dict(op_index_base=0, ops_counted="every kmx line except APPEND_TO_REGISTER, REGISTER, INFO_TAG, DEBUG_PRINT",
                    edit=["op 3292: `CCX q16 q20 q21` -> `HMR q21 b61` followed by `CZ q16 q20 if b61`",
                          "op 3403: the original `HMR q21 b61` is removed (b61 is not used before it)"],
                    then="kmx -> kmb with kickmix (Circuit.from_file(kmx, format='kmx').to_file(kmb, format='kmb')) gives sha256 e46d90c3...",
                    **dw),
        official=dict(score=inv33["score"], toffoli_count=inv33["toffoli_count"], num_qubits=inv33["num_qubits"],
                      rotation_count=inv33.get("rotation_count"), worst_error_over_tolerance=inv33.get("worst_error_over_tolerance")),
        kmsim_all_inputs={k: kms[k] for k in ("worst_ratio", "toff_mean", "restored", "dirty", "bad_reset") if k in kms},
        cost_change_percent=100 * (inv33["score"] / BASE_DCDE["score"] - 1),
        first_public=dict(notebook=NB["cz"][0], url=nb_url("cz"), version=5, date_utc=receipts["out33"]["date"],
                          note="also in version 4 of that notebook (pushed, not submitted; no receipt kept)"),
        receipts=["out33", "out35", "out37", "out39", "out40"])
    # ---------------------------------------------------------------- dqi
    d8 = receipts["out8"]["v"]["dqi"]
    index["dqi_readout_window_transplant"] = dict(
        task="dqi", sha12="245527f68413", sha256=d8["circuit_sha256"], path="",
        what="Two decoder regions of bb4287e7 replaced by their 9fcda0c1 versions: four controlled-swap readout windows "
             "(12 CSWAP each, both outputs X-measured right after) become CX + HMR + CZ + HMR + BIT_INVERT: 48 fewer Toffolis per shot.",
        base=dict(sha12="bb4287e7", first_source=who(next((h for h in circ if h.startswith("bb4287e7")), "")),
                  official_default_salt=dict(score=373606711683.7646, toffoli_count=394165.15760742186, num_qubits=892, value_errors=0)),
        donor=dict(sha12="9fcda0c1", note="Heliosli's file of the e9f54be3 line (Atakan Aldemir, QCC: Terminal Readout and Phase Folds)"),
        recipe=["export bb4287e7, cd71c482 and 9fcda0c1 to kmx with kickmix",
                "number the decoder regions by INFO_TAG order; map cd71c482 region i to bb4287e7 by difflib.SequenceMatcher over the INFO_TAG lines",
                "for regions i = 673 and 16783 of cd71c482: assert the bb4287e7 region equals the cd71c482 region and that the "
                "9fcda0c1 region introduces no new classical bits",
                "write bb4287e7 with those two regions replaced by the 9fcda0c1 regions; kmx -> kmb with kickmix"],
        official=dict(score=d8["score"], toffoli_count=d8["toffoli_count"], num_qubits=d8["num_qubits"],
                      value_errors=d8.get("value_errors"), phase_errors=d8.get("phase_errors"), repetition_factor=d8.get("repetition_factor"),
                      note="default salt; 1 value error inherited from the decoder line (about 6e-6 per shot), so the board price depends on the draw"),
        first_public=dict(notebook=NB["lb"][0], url=nb_url("lb"), version=1, date_utc=receipts["out8"]["date"]),
        receipts=["out8"], binary="metadata only (DQI files are too large); build it with the recipe, or take it from the notebook output")
    # ---------------------------------------------------------------- chemistry refits
    cm = json.load(open(a.chem_metrics))
    refits = [("2913ca130f71", "out37", "ref", 2, "maoxin123's v27 table and words (npz 3f864a7a); loaders 71735b23 (maoxin123)"),
              ("54bc3e71807e", "out39", "ref", 4, "Atakan Aldemir's weights e52b7cdd on maoxin123's v27 table and words"),
              ("5a75386681c8", "out40", "ref", 5, "Atakan Aldemir's weights f4f2db44 (QCC: Terminal Readout and Phase Folds) on maoxin123's v27 table and words; refit run inside the notebook (22 minutes)")]
    rrows = []
    for h, rid, nb, ver, base_note in refits:
        m, b = cm[h], cm[cm[h]["base"]]
        vc = receipts[rid]["v"]["dfthcsos"]
        fixed = [k for k, same in m["arrays_equal_to_base"].items() if same]
        changed = [k for k, same in m["arrays_equal_to_base"].items() if not same]
        name = f"chem_refit_{NB[nb][0].split('/')[1]}_v{ver}".replace("-", "_")
        index[name] = dict(
            task="chemistry", sha12=h, sha256=m["sha256"], path=f"factorizations/{h}.npz",
            what="W and H2_I refitted at fixed angle words (GRG, tools/refit); every other array identical to the base file.",
            base=dict(sha12=m["base"], sha256=b["sha256"], lambda_eff=b["lambda_eff"], note=base_note),
            metrics=dict((k, m[k]) for k in ("lambda_eff", "error_1", "error_2", "E_gap", "Lambda", "gap_in_domain")),
            arrays_changed=changed, arrays_identical_to_base=fixed, max_abs_change=m["max_abs_change"],
            official=dict(score=vc["score"], lambda_eff=vc.get("lambda_eff"), toffoli_count=vc.get("toffoli_count"), num_qubits=vc.get("num_qubits")),
            lambda_eff_change=m["lambda_eff"] - b["lambda_eff"],
            cost_change_percent=100 * (m["lambda_eff"] / b["lambda_eff"] - 1),
            first_public=dict(notebook=NB[nb][0], url=nb_url(nb), version=ver, date_utc=receipts[rid]["date"]),
            receipts=[rid])
        rrows.append(dict(sha12=h, path=f"factorizations/{h}.npz", base_sha12=m["base"], base_lambda_eff=b["lambda_eff"],
                          lambda_eff=m["lambda_eff"], lambda_eff_change=m["lambda_eff"] - b["lambda_eff"],
                          error_1=m["error_1"], error_2=m["error_2"], E_gap=m["E_gap"], Lambda=m["Lambda"],
                          official_chem_score=vc["score"], official_toffoli=vc.get("toffoli_count"), official_qubits=vc.get("num_qubits"),
                          notebook=NB[nb][0], version=ver, output_downloaded_utc=receipts[rid]["date"], receipt_id=rid))
    buf = io.StringIO()
    w = csv.DictWriter(buf, list(rrows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rrows)
    write(os.path.join(C, "chemistry_refits", "refits.csv"), buf.getvalue())
    write(os.path.join(C, "index.json"), jdump(index))
    write(os.path.join(C, "invsqrt", "9c708f7b9abc_splice.json"), jdump(index["invsqrt_splice_62q"]))
    write(os.path.join(C, "invsqrt", "e46d90c36d1b_dead_write_fix.json"), jdump(index["invsqrt_dead_write_fix"]))
    write(os.path.join(C, "dqi", "245527f68413_readout_windows.json"), jdump(index["dqi_readout_window_transplant"]))
    readmes(C, index, receipts, rrows, rec_rows, circ, rlink)
    print(json.dumps({k: v.get("cost_change_percent") for k, v in index.items()}, indent=1))


def fmt(x, n=2):
    return f"{x:,.{n}f}"


def readmes(C, I, R, rrows, rec_rows, circ, rlink):
    sp, dw, dq = I["invsqrt_splice_62q"], I["invsqrt_dead_write_fix"], I["dqi_readout_window_transplant"]
    chem = [v for k, v in I.items() if k.startswith("chem_refit")]

    def src(h):
        r = circ.get(h)
        return f"[{r['first_source_ref']}]({r['first_source_url']})" if r else "-"
    seg_md = "\n".join(f"| {i + 1} | `{s}` | {a} - {b} | {src(s)} |" for i, (s, a, b) in enumerate(sp["segments"]))
    write(os.path.join(C, "invsqrt", "README.md"), f"""# Our invsqrt contributions

## 1. Splice of public 62-qubit circuits: `9c708f7b9abc`

**What.** A shortest-path search over "clean cuts" of the public 62-qubit invsqrt circuits (a cut where the condition
stack is empty and no classical bit written before it is read after it; two circuits can be joined at cuts where
their qubit state and phase agree on every sampled input). The cheapest path joins 16 pieces of 7 public circuits.
Tools: `tools/splice_dp.py` (search) and `tools/build_splice.py` (writes the kmx).

**Gain (official verifier).** score {fmt(sp['official']['score'])} (Toffoli {sp['official']['toffoli_count']:.3f}, 62 qubits,
worst error/tolerance {sp['official']['worst_error_over_tolerance']}) against {fmt(sp['baseline']['score'])} for the best single
circuit `94b29cc52689` (Toffoli {sp['baseline']['toffoli_count']:.3f}): **{sp['cost_change_percent']:.3f} % cost**.

**Verified.** Official invsqrt verifier, PASS, in our receipts `{'`, `'.join(sp['receipts'])}` (`contributions/receipts/`).
**First public:** {rlink('out21')} (output of {sp['first_public']['date_utc']} UTC).
**File:** `{sp['path']}` (kmx text; sha256 `{sp['sha256']}`). Pieces and their sources: `9c708f7b9abc_splice.json`.

| # | Piece of | Body lines [start, end) | Found in (one public source) |
|---:|---|---|---|
{seg_md}

"Body lines" index the kmx text after its REGISTER / APPEND_TO_REGISTER header; classical bits are renumbered when
the pieces are joined. Credits: the authors of these circuits (see `circuits.csv`: WCao24's 44-CSWAP normaliser
`94b29cc5`, Thomas Gamet's early prefix `5ec4f516` and the public 62-qubit line they build on).

## 2. Dead-write fix: `e46d90c36d1b`

**What.** In Atakan Aldemir's `dcde70780434` (46 qubits) the Toffoli `CCX q16 q20 q21` (op 3292) writes a qubit that is
only X-measured afterwards (`HMR q21 b61`, op 3403). Measuring first and applying the phase classically,
`HMR q21 b61; CZ q16 q20 if b61`, is the same operation with one Toffoli fewer on every shot.

**Recipe** (ops numbered from 0 over every kmx line except APPEND_TO_REGISTER, REGISTER, INFO_TAG, DEBUG_PRINT):
take `kmx/invsqrt/dcde70780434.kmx`, replace op 3292 by `HMR q21 b61` + `CZ q16 q20 if b61`, delete op 3403, and convert
the text with kickmix (`Circuit.from_file(path, format="kmx").to_file(out, format="kmb")`): the .kmb has sha256
`{dw['sha256']}`. The resulting text is `{dw['path']}` (sha256 of the text `{dw['recipe']['kmx_sha256']}`).

**Gain (official verifier).** score {fmt(dw['official']['score'])} (Toffoli {dw['official']['toffoli_count']:.4f}, 46 qubits,
{dw['official']['rotation_count']:.0f} rotations, worst error/tolerance {dw['official']['worst_error_over_tolerance']}) against
{fmt(dw['base']['score'])} for `dcde7078` (Toffoli {dw['base']['toffoli_count']:.4f}; official record in Atakan Aldemir's public
output): **{dw['cost_change_percent']:.4f} % cost**, about +0.005 leaderboard points.

**Verified.** Official verifier PASS in receipts `{'`, `'.join(dw['receipts'])}`; `tools/kmsim.py` over all 3,133,452 inputs:
worst ratio {dw['kmsim_all_inputs'].get('worst_ratio', '')}, exact mean Toffoli {dw['kmsim_all_inputs'].get('toff_mean', '')}, inputs restored,
no dirty ancilla. Found with `tools/qccscope` (motif A3, dead write).
**First public:** {rlink('out33')} (output of {dw['first_public']['date_utc']} UTC); also in version 4 of that notebook (not submitted).
Base file credits: Atakan Aldemir (`dcde7078`, *quantum-circuits-iso-gap-dqi-h5*) on the public 46-qubit line of Syed Asad
Ali and Ali Haydar Özdağ and the authors they credit.
""")
    write(os.path.join(C, "dqi", "README.md"), f"""# Our DQI contribution: readout-window transplant `245527f68413`

**What.** Atakan Aldemir's DQI `bb4287e7` (*QCC: Shared Products and Controlled Refits*) sits on the `cd71c482` line of
the team *i want to run gemma 9b*. That line never received two decoder regions that the older `e9f54be3` line
(Atakan Aldemir, *QCC: Terminal Readout and Phase Folds*; kept in Heliosli's `9fcda0c1`) already had:
**controlled-swap readout windows**. A window is 12 `CSWAP c a b` whose two outputs are both X-measured right after;
each pair can be replaced by `CX a b; HMR a -> m1; CZ c b if m1; HMR b -> m2; BIT_INVERT m1 if m2` (same phase, same
classical record, no Toffoli). Four windows (two regions, each computed and uncomputed): **48 fewer Toffolis per shot**.

**Recipe.**
{chr(10).join(f'{i + 1}. {s}' for i, s in enumerate(dq['recipe']))}

The file is **metadata only** here (DQI circuits are hundreds of MB as text), like every DQI file of the atlas:
rebuild it with the recipe from the three public files, or take `dqi.kmb` from the output of version 1 of the
notebook below.

**Gain (official verifier, default salt, 102,400 shots).** mean Toffoli {dq['official']['toffoli_count']:,.2f} against
{dq['base']['official_default_salt']['toffoli_count']:,.2f} for `bb4287e7`, same 892 qubits. The decoder line keeps its inherited
rare failures (about 6e-6 per shot): this run drew {dq['official']['value_errors']} value error, so its score
{fmt(dq['official']['score'])} carries repetition factor {dq['official']['repetition_factor']:.4f}; at zero failed shots the cost is
about 0.012 % below `bb4287e7`.

**First public:** {rlink('out8')} (output of {dq['first_public']['date_utc']} UTC), leaderboard 25.36727. sha256 `{dq['sha256']}`.
Credits: Atakan Aldemir, the team *i want to run gemma 9b* (`b4dc000c`, `cd71c482`), Heliosli (`9fcda0c1`), and the decoder
line they credit (Syed Asad Ali, SomeJoint, jday96314, Kirill Tymchishin and others).
""")
    rows_md = "\n".join(
        f"| `{r['sha12']}` | `{r['base_sha12']}` | {r['base_lambda_eff']:.8f} | **{r['lambda_eff']:.8f}** | {r['lambda_eff_change']:+.2e} | "
        f"{r['error_1']:.12f} | {r['error_2']:.12f} | {r['E_gap']:.10f} | {fmt(r['official_chem_score'])} | v{r['version']} ({r['output_downloaded_utc']}) |"
        for r in rrows)
    write(os.path.join(C, "chemistry_refits", "README.md"), f"""# Our chemistry refits (W, H2_I at fixed angle words)

Three public outputs of [QCC 27.3122 | Frontier + Finer Chemistry Refit]({KAGGLE}/code/{NB['ref'][0]}). Each file is the
base file with **only `W` and `H2_I` changed** (U, H1_I, Hsym_lower, tree_edges and angle_words are byte-identical), so
the base file's 15 loader circuits stay valid. Made with `tools/refit` (GRG, our numpy port of prvsiyan's
`refit_grg.py`). The files are in the atlas store: `factorizations/<sha12>.npz`.

| File | Base | lambda_eff base | lambda_eff ours | change | error_1 | error_2 | E_gap | official chem score | notebook version (output UTC) |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
{rows_md}

Metrics: `python -m refit eval FILE` (the verifier's own math; equal to the official receipts to the last digit).
Gates: error_1 < 0.02, error_2 < 0.02, E_gap > 3.914898 (all with >= 1e-9 slack). The official chemistry score is
lambda_eff x Toffoli x qubits (14,728 x 427 with these loaders), so the cost falls in proportion to lambda_eff.
Machine-readable: `refits.csv`, `../index.json`. Receipts: `../receipts/`.

Credits: maoxin123 (v27 table, coded words and loaders), Atakan Aldemir (base weights `e52b7cdd`, `f4f2db44`),
Heliosli, prvsiyan (refit method, Apache-2.0), Lera (marculera) and the DF-THC authors they credit.
""")
    rec_md = "\n".join(f"| `{r['receipt_id']}` | [{r['notebook'].split('/')[1]}]({KAGGLE}/code/{r['notebook']}) | {r['version']} | {r['output_downloaded_utc']} | "
                       f"{r['submitted_by_us']} | `{r['invsqrt_sha12'][:8]}` `{r['dqi_sha12'][:8]}` `{r['chem_npz_sha12'][:8]}` | {r['geometric_mean_score']:.5f} |"
                       for r in rec_rows)
    write(os.path.join(C, "receipts", "README.md"), f"""# Official-verifier receipts of our public notebook versions

One JSON per public version that wrote a submission: the SHA-256 of every file of the submission and the full output
of the three unchanged official verifiers (`invsqrt/verify_submission_invsqrt.py`, `dqi/verify_submission_dqi.py`,
`dfthcsos/verify.py`), as written by the notebook (`receipt.json` in its output). The receipt id (our run label) is the
value used in the `verified_receipts` columns of `circuits.csv` and `families.csv`.

| Receipt | Notebook | Version | Output downloaded (UTC) | Submitted by us | invsqrt / DQI / chem npz | GM of the three scores |
|---|---|---:|---|---|---|---:|
{rec_md}

GM is the geometric mean of REF/score over the three tasks with the competition's reference costs; the leaderboard
uses its own salt and draw, so a board score can differ (DQI failures are random). "unknown": we did not record whether
that version was submitted. Version numbers are from our run log.
""")
    def tl(rid):
        return rlink(rid).replace(" | ", " \\| ")
    lines = [f"| invsqrt | [Splice of public 62-qubit circuits](invsqrt/README.md) | `{sp['sha12']}` | {sp['cost_change_percent']:.3f} % cost | {tl('out21')} |",
             f"| invsqrt | [Dead-write fix (CCX -> HMR + CZ)](invsqrt/README.md) | `{dw['sha12']}` | {dw['cost_change_percent']:.4f} % cost | {tl('out33')} |",
             f"| DQI | [Readout-window transplant](dqi/README.md) | `{dq['sha12']}` | -48 Toffolis per shot | {tl('out8')} |"]
    for v in chem:
        rid = v["receipts"][0]
        lines.append(f"| chemistry | [Refit of W, H2_I](chemistry_refits/README.md) | `{v['sha12']}` | lambda_eff {v['lambda_eff_change']:+.2e} ({v['cost_change_percent']:.5f} % cost) | {tl(rid)} |")
    write(os.path.join(C, "README.md"), """# Contributions: our own public results

Everything here was first published in a public version of one of our notebooks (linked). Each item has a README with
what it is, the exact gain, how it was verified, where it was first public and the credits of the file it builds on;
`index.json` has the same as data (paths relative to the dataset root), and `receipts/` holds the official-verifier
receipts. The circuit and factorization files are in the atlas store (`kmx/invsqrt/`, `factorizations/`), so they
are listed once in `circuits.csv` like every other public file.

| Task | Contribution | File | Gain | First public |
|---|---|---|---|---|
""" + "\n".join(lines) + """

```python
import sys; sys.path.insert(0, "/kaggle/input/qcc-circuit-atlas/tools")
import atlas_io as A
c = A.contribution("invsqrt_dead_write_fix"); print(c["official"], A.resolve(c["path"]))
```
""")


if __name__ == "__main__":
    main()
