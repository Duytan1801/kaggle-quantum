"""Turn detector output into findings: motif, instances, estimated saving in task units and leaderboard points.

Each finding: dict(id, motif, count, d_toffoli, d_qubits, points, confidence, note).
confidence: 'exact' (static proof or exhaustive simulation), 'sampled' (value property seen on S samples only:
must be verified on all inputs before use), 'bound' (an upper bound / ceiling, not a construction), 'info'.
"""
from __future__ import annotations

import numpy as np

from . import cost as C
from . import kmx
from . import values as Vv

# Best known bilinear ranks over GF(2) (Ballet et al. survey; Montgomery; Barbulescu et al.)
MU2 = {2: 3, 3: 6, 4: 9, 5: 13, 6: 15, 7: 22, 8: 24, 12: 42}

# Prior measured results per task, printed as context in reports. Empty here: add your own notes, e.g.
# HISTORY["invsqrt"].append("rotation angles already LP-optimal").
HISTORY = {"invsqrt": [], "dqi": [], "chem": []}


def _f(id_, motif, count, d_toffoli, d_qubits, task, confidence, note="", model=None):
    pts = C.saving_points(task, d_toffoli=d_toffoli, d_qubits=d_qubits, model=model) if (d_toffoli or d_qubits) else 0.0
    return dict(id=id_, motif=motif, count=int(count), d_toffoli=float(d_toffoli), d_qubits=int(d_qubits),
                points=pts, confidence=confidence, note=note)


def findings(task: str, circ: kmx.Circuit, lv, S, V=None, exhaustive: bool = False, loaders: int = 1) -> list[dict]:
    """task in invsqrt|dqi|chem. For chem the saving is per loader file (Toffolis per pass)."""
    out = []
    conf_v = "exact" if exhaustive else "sampled"
    out.append(_f("A1", "Toffoli-erased AND (MBU would erase for free)", len(S.toffoli_uncompute),
                  len(S.toffoli_uncompute), 0, task, "exact", "replace 2nd CCX by HMR + if m: CZ a b"))
    out.append(_f("A2", "cancelling identical Toffoli pair", len(S.cancel_pairs), 2 * len(S.cancel_pairs), 0, task,
                  "exact"))
    out.append(_f("A3", "dead write (CCX target only written, then HMR)", len(S.dead_writes), len(S.dead_writes), 0,
                  task, "exact", "drop the CCX; its phase is an if m: CZ on the controls"))
    out.append(_f("A4s", "Toffoli with a statically |0> control", len(S.const_control), len(S.const_control), 0, task,
                  "exact"))
    if V is not None:
        n0 = len(V.const0); na = len(V.affine); ns = len(V.swap_noop) + len(V.swap_always)
        out.append(_f("A4v", "Toffoli product 0 on all " + ("inputs" if exhaustive else f"{V.lanes} samples"), n0,
                      n0 if exhaustive else 0, 0, task, conf_v,
                      "" if exhaustive else "rare-active Toffolis: not removable without proof on all inputs"))
        out.append(_f("A5", "affine Toffoli (product equals a control)", na, na if exhaustive else 0, 0, task, conf_v))
        out.append(_f("A6", "CSWAP no-op / always-swap", ns, ns if exhaustive else 0, 0, task, conf_v))
        if task != "chem":
            q = {"invsqrt": C.MODELS["invsqrt"].Q, "dqi": C.MODELS["dqi"].Q}[task]
            red = Vv.gap_width_reduction(circ.n_ops, V.zero_gaps, lv.width)
            w2 = lv.width.astype(np.int64) - red
            best = None
            for k in range(0, 4):
                rp = Vv.retention_plan(V.repeats, w2, q + k, block=1 if circ.n_ops < 200_000 else 256)
                pts = C.saving_points(task, d_toffoli=rp["free"], d_qubits=-k)
                out.append(_f(f"A7+{k}", f"retain repeated products with {k} extra qubit(s)", rp["candidates"],
                              rp["free"], -k, task, conf_v if k == 0 else "bound",
                              f"{rp['free']} of {rp['candidates']} repeats fit (earliest-end greedy)"))
                if best is None or pts > best[1]:
                    best = (k, pts)
            semi = int(w2.max())
            if semi < lv.peak:
                out.append(_f("E3", "value-level width below static width (zero gaps)", lv.peak - semi, 0,
                              lv.peak - semi, task, conf_v, f"semistatic peak {semi} vs {lv.peak}"))
    # width: what a single qubit is worth and what blocks it
    if task != "chem":
        ep = lv.episodes()
        out.append(_f("E1", f"peak width {lv.peak}: {len(ep)} episodes, {int((lv.width >= lv.peak).sum())} ops", len(ep),
                      0, 1, task, "bound", "value of removing one qubit (Amdahl ceiling of the width lever)"))
    return out


def invsqrt_extras(circ: kmx.Circuit) -> list[dict]:
    """Rotation budget and margin sensitivity (invsqrt only)."""
    m = C.MODELS["invsqrt"]
    rot_eq = (m.t_base + m.n_rot * C.rotation_t_count(m.eps)) / 4
    angles = [circ.angles[b] for b in circ.bit[circ.op == kmx.ZPOW].tolist()]
    from collections import Counter
    cnt = Counter(angles)
    dup = sum(v for v in cnt.values() if v > 1)
    rows = [
        dict(id="R1", motif="rotation synthesis budget", count=m.n_rot, d_toffoli=rot_eq, d_qubits=0,
             points=C.saving_points("invsqrt", d_toffoli=rot_eq), confidence="bound",
             note=f"{rot_eq:.1f} Toffoli-eq of {m.toffoli_equivalent():.1f} ({100 * rot_eq / m.toffoli_equivalent():.1f} %): ceiling if all rotations were free"),
        dict(id="R2", motif="margin x2 (better approximation)", count=1, d_toffoli=m.n_rot * 0.56 / 4, d_qubits=0,
             points=C.invsqrt_margin_points(m.min_margin_units), confidence="bound",
             note="each doubling of the min phase margin saves n_rot*0.56/4 = 4.6 Toffoli-eq"),
        dict(id="R3", motif="one rotation fewer at the same margin", count=1,
             d_toffoli=C.rotation_t_count(m.eps) / 4, d_qubits=0,
             points=C.points("invsqrt", C.InvSqrt(n_rot=m.n_rot - 1).with_margin(m.min_margin_units, m.n_rot - 1).cost()),
             confidence="bound", note="ceiling: needs the remaining rotations to keep the phase margin"),
        dict(id="R4", motif="Z_POW with an angle used more than once (Hamming-weight phasing candidates)", count=dup,
             d_toffoli=0, d_qubits=0, points=0.0, confidence="info", note=f"{len(cnt)} distinct angles in {len(angles)} Z_POW"),
    ]
    return rows
