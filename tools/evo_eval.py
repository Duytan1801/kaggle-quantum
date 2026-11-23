#!/usr/bin/env python3
"""evo_eval.py — the cheap-to-expensive evaluation cascade for evo_engine.

One candidate goes through the stages in cost order; a candidate never pays for
an expensive stage until the cheap one passed:

  build      emit the circuit (ISR generator / Syed patch tree / DQI gate edit)
  static     Q, ops, Toffoli-like, T, generic rotations, peak-live  (seconds)
  model      modelled official cost from the static ledger              (instant)
  semantics  the builder's own all-input CHECK PASS lines               (seconds)
  proof      official invsqrt verifier at --shots-per-x 1               (minutes)
  official   the UNCHANGED official verifier at full shots              (finalists only)

DQI / chemistry cannot be fully verified under the local 3 GB cap; for those
legs the `official` stage writes a durable moat-lab request instead of pretending
to pass.

Usage
  evo_eval.py --id 12 [--official auto|none|fast|full] [--full]
  evo_eval.py --list-stages
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "work/tools"))
import evo_engine as E  # noqa: E402

PY = ROOT / "work/toolchain/venv/bin/python"
KICK = ROOT / "work/toolchain/kickmix"
VER = ROOT / "work/toolchain/verifiers"
RUN_CAPPED = ROOT / "harness/run_capped.sh"
BUILD_ROOT = Path("/tmp/opencode/evo_eval")
ART = ROOT / "work/evo/artifacts"
MOAT = ROOT / "work/evo/moat_queue"
CAP = os.environ.get("EVO_CAP", "3G")

sys.path.insert(0, str(KICK))
try:
    import kickmix as km  # noqa: E402
except Exception as exc:  # pragma: no cover
    km = None
    KM_ERR = str(exc)
else:
    KM_ERR = ""


# ------------------------------------------------------------------ helpers
def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def slug(s: str, n: int = 40) -> str:
    s = re.sub(r"[^A-Za-z0-9_.-]+", "_", s).strip("_")
    return s[:n] or "cand"


def run(cmd: list[str], *, timeout: int, env: dict | None = None,
        cwd: Path | None = None, capped: bool = True) -> subprocess.CompletedProcess:
    if capped and RUN_CAPPED.exists() and not os.environ.get("EVO_NO_CAP"):
        cmd = [str(RUN_CAPPED), CAP, *cmd]
    e = os.environ.copy()
    if env:
        e.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                          env=e, cwd=str(cwd) if cwd else None)


def kmb_stats(path: Path) -> dict:
    """Fast static ledger straight from the binary (no KMX materialisation)."""
    if km is None:
        raise RuntimeError(f"kickmix unavailable: {KM_ERR}")
    c = km.Circuit.from_file(str(path), "kmb")
    st = c.operation_statistics()
    tof = int(getattr(st, "num_toffoli_like", 0))
    tlike = int(getattr(st, "num_t_like", 0))
    noncliff = int(getattr(st, "num_non_clifford", 0))
    rot = max(0, noncliff - tof - tlike)
    return {"Q": int(c.num_qubits), "ops": int(getattr(st, "num_instructions", 0)),
            "toffoli_like": tof, "t_like": tlike, "generic_rotations": rot,
            "non_clifford": noncliff}


def kmb_liveness(path: Path) -> dict:
    """Peak-live width from the KMX op stream (small circuits only)."""
    if km is None:
        return {}
    c = km.Circuit.from_file(str(path), "kmb")
    buf = io.BytesIO()
    c.to_file(buf, format="kmx")
    first, last = {}, {}
    i = 0
    for line in buf.getvalue().decode(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        toks = line.split()
        name = toks[0]
        if name in ("APPEND", "REGISTER") or "=" in name:
            continue
        wires = []
        for t in toks[1:]:
            if t == "if":
                break
            if t.startswith("q") and t[1:].isdigit():
                wires.append(int(t[1:]))
        if not wires:
            continue
        for w in wires:
            first.setdefault(w, i)
            last[w] = i
        i += 1
    if not first:
        return {}
    # peak over ops of the number of wires whose span covers the op
    peak, at = 0, -1
    for j in range(i):
        n = sum(1 for w in first if first[w] <= j <= last[w])
        if n > peak:
            peak, at = n, j
    return {"peak_live": peak, "peak_at_op": at, "span_wires": len(first)}


def parse_stack_log(path: Path) -> dict:
    if not path.exists():
        return {}
    text = path.read_text(errors="replace")
    means = [float(m) for m in re.findall(
        r"Toffoli-like a shot with random outcomes = ([\d.]+)", text)]
    return {
        "mean_toffoli_sampled": means[-1] if means else None,
        "check_pass": text.count("CHECK PASS"),
        "has_error": bool(re.search(r"Traceback|AssertionError|no schedule|FAILED", text)),
        "tail": "\n".join(text.splitlines()[-12:]),
    }


def model_invsqrt(f: dict, mean_toffoli: float | None, rot_price: float = 7.1) -> float:
    q = f["Q"]
    tof = mean_toffoli if mean_toffoli is not None else 0.924 * f["toffoli_like"]
    return q * (tof + f["t_like"] / 4.0 + f["generic_rotations"] * rot_price)


# ------------------------------------------------------------------ builders
def build_isr(cfg: dict, work: Path) -> dict:
    cmd = [str(PY), str(ROOT / "work/tools/h30_isr_caps.py"), "--out", str(work)]
    if cfg.get("caps"):
        cmd += ["--caps", str(cfg["caps"])]
    for k, v in (cfg.get("env") or {}).items():
        cmd += ["--env", f"{k}={v}"]
    for k, v in (cfg.get("stack_env") or {}).items():
        cmd += ["--stack-env", f"{k}={v}"]
    if cfg.get("keep_r56"):
        cmd += ["--keep-r56"]
    began = time.monotonic()
    p = run(cmd, timeout=int(cfg.get("timeout", 2400)))
    elapsed = time.monotonic() - began
    kmb = work / "invsqrt.kmb"
    log = work / "stack.log"
    out = {"rc": p.returncode, "elapsed": elapsed, "kmb": str(kmb),
           "stdout_tail": p.stdout[-3000:], "stderr_tail": p.stderr[-3000:],
           "stack_log": str(log)}
    if p.returncode != 0 or not kmb.exists():
        out["error"] = (p.stderr or p.stdout)[-2000:]
        return out
    out["sha256"] = sha256(kmb)
    out["stack"] = parse_stack_log(log)
    return out


def build_syed(cfg: dict, work: Path) -> dict:
    work.mkdir(parents=True, exist_ok=True)
    cfg_path = work / "config.json"
    cfg_path.write_text(json.dumps(cfg, indent=1))
    began = time.monotonic()
    p = run([str(PY), str(ROOT / "work/tools/evo_build.py"),
             "--config", str(cfg_path), "--work", str(work / "build"),
             "--out", str(work / "result.json")], timeout=int(cfg.get("timeout", 1800)))
    elapsed = time.monotonic() - began
    res = {}
    if (work / "result.json").exists():
        res = json.loads((work / "result.json").read_text())
    out = {"rc": p.returncode, "elapsed": elapsed, "result": res,
           "stderr_tail": p.stderr[-3000:]}
    score = res.get("score") or {}
    if p.returncode != 0 or res.get("status") != "EMITTED":
        out["error"] = (res.get("stderr") or p.stderr or "")[-2000:]
        return out
    out["sha256"] = score.get("kmb_sha256")
    out["model"] = score.get("score_model")
    out["features"] = {"Q": score.get("Q"), "toffoli_like": score.get("toffoli_like"),
                       "t_like": score.get("T"), "generic_rotations": score.get("generic_rotations")}
    return out


def _kmx_bytes(kmb: Path) -> bytes:
    c = km.Circuit.from_file(str(kmb), "kmb")
    buf = io.BytesIO()
    c.to_file(buf, format="kmx")
    del c
    return buf.getvalue()


def build_dqi_edit(cfg: dict, work: Path) -> dict:
    """Apply exact KMX text rewrites to a DQI binary and re-pin the SHA."""
    src = Path(cfg["source"])
    if not src.is_absolute():
        src = ROOT / src
    began = time.monotonic()
    txt = _kmx_bytes(src)
    applied = []
    for label, old, new in cfg.get("edits", []):
        o = ("\n" + old + "\n").encode()
        n = ("\n" + new + "\n").encode()
        cnt = txt.count(o)
        if cnt != 1:
            return {"rc": 1, "elapsed": time.monotonic() - began,
                    "error": f"edit {label!r} matched {cnt} times (need exactly 1)"}
        txt = txt.replace(o, n, 1)
        applied.append(label)
    kmx = work / "dqi_edited.kmx"
    kmx.write_bytes(txt)
    c = km.Circuit.from_file(str(kmx), "kmx")
    out_kmb = work / "dqi.kmb"
    c.to_file(str(out_kmb), format="kmb")
    del c
    os.remove(kmx)
    return {"rc": 0, "elapsed": time.monotonic() - began, "kmb": str(out_kmb),
            "sha256": sha256(out_kmb), "applied": applied,
            "expected_sha": cfg.get("expected_sha")}


def build_artifact(cfg: dict, work: Path) -> dict:
    """Evaluate an already-built circuit (retro-scoring, cascade self-test)."""
    src = Path(cfg["kmb"])
    if not src.is_absolute():
        src = ROOT / src
    if not src.exists():
        return {"rc": 1, "error": f"missing artifact {src}"}
    dst = work / src.name
    shutil.copyfile(src, dst)
    return {"rc": 0, "elapsed": 0.0, "kmb": str(dst), "sha256": sha256(dst)}


def build(cfg: dict, work: Path) -> dict:
    b = cfg.get("builder")
    if b == "artifact":
        return build_artifact(cfg, work)
    if b == "isr":
        return build_isr(cfg, work)
    if b == "syed":
        return build_syed(cfg, work)
    if b == "dqi_edit":
        return build_dqi_edit(cfg, work)
    return {"rc": 1, "error": f"unknown builder {b!r}"}


# ------------------------------------------------------------------ official
def best_for_leg(leg: str, exclude: int) -> tuple[float | None, int | None]:
    c = E.connect()
    E.init_db(c)
    rows = [r for r in c.execute(
        "SELECT id,score,score_model,features FROM candidates WHERE leg=? AND id<>?",
        (leg, exclude))]
    best = None
    bestq = None
    for r in rows:
        s = r["score_official"] if r["score_official"] is not None else r["score_model"]
        if s is not None and (best is None or s < best):
            best = s
        f = E._json_or_empty(r["features"])
        q = f.get("Q")
        if isinstance(q, int) and (bestq is None or q < bestq):
            bestq = q
    return best, bestq


def run_official_invsqrt(kmb: Path, shots_per_x: int, timeout: int = 3600) -> dict:
    cmd = [str(PY), str(VER / "invsqrt/verify_submission_invsqrt.py"), str(kmb),
           "--shots-per-x", str(shots_per_x)]
    p = run(cmd, timeout=timeout, env={"PYTHONPATH": str(KICK)})
    text = (p.stdout or "") + (p.stderr or "")
    payload = None
    dec = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = dec.raw_decode(text[i:])
                if isinstance(obj, dict) and "status" in obj:
                    payload = obj
            except json.JSONDecodeError:
                continue
    if payload is None:
        payload = {"status": "NO_JSON", "rc": p.returncode, "tail": text[-1500:]}
    payload["rc"] = p.returncode
    return payload


def queue_moat(cid: int, row, kmb: Path, evidence: str) -> Path:
    MOAT.mkdir(parents=True, exist_ok=True)
    req = {"candidate_id": cid, "leg": row["leg"], "name": row["name"],
           "kmb": str(kmb), "sha256": sha256(kmb) if kmb.exists() else None,
           "config": json.loads(row["config"]),
           "evidence": evidence,
           "instruction": "run the UNCHANGED official verifier at full shots; "
                          "append the JSON receipt to work/evo/moat_queue/RESULTS.jsonl",
           "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
    p = MOAT / f"c{cid:04d}_{slug(row['name'])}.json"
    p.write_text(json.dumps(req, indent=2) + "\n")
    return p


# ------------------------------------------------------------------ cascade
def evaluate(cid: int, official: str = "auto", full: bool = False) -> dict:
    row = E.get(cid)
    if not row:
        raise SystemExit(f"no candidate {cid}")
    cfg = json.loads(row["config"])
    work = BUILD_ROOT / f"c{cid:04d}_{slug(row['name'])}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    summary = {"id": cid, "name": row["name"], "leg": row["leg"], "stages": {}}

    # ---- build
    b = build(cfg, work)
    summary["stages"]["build"] = {k: b.get(k) for k in
                                  ("rc", "elapsed", "sha256", "error") if k in b}
    if b.get("rc") != 0:
        E.record(cid, "build", "FAIL", evidence=json.dumps(b)[-7000:], elapsed=b.get("elapsed"))
        return summary
    kmb = Path(b.get("kmb") or (work / "invsqrt.kmb"))
    E.record(cid, "build", "PASS", features={"kmb": str(kmb), "sha256": b.get("sha256")},
             evidence=f"built {kmb.name} sha={b.get('sha256')}", elapsed=b.get("elapsed"))

    # ---- static ledger
    if row["leg"] == "invsqrt":
        f = kmb_stats(kmb)
        if cfg.get("builder") in ("isr", "artifact"):
            f.update(kmb_liveness(kmb))
        if cfg.get("builder") == "isr":
            st = b.get("stack") or {}
            f["mean_toffoli_sampled"] = st.get("mean_toffoli_sampled")
            f["check_pass"] = st.get("check_pass")
        E.record(cid, "static", "PASS", features=f,
                 evidence=f"Q={f['Q']} ops={f['ops']} tof={f['toffoli_like']} "
                          f"rot={f['generic_rotations']} peak={f.get('peak_live')}")
        summary["stages"]["static"] = f

        # ---- model
        model = b.get("model") or model_invsqrt(f, f.get("mean_toffoli_sampled"))
        E.record(cid, "model", "PASS", score=float(model),
                 features={"score_model": float(model),
                           "rotation_price": 7.1 if not b.get("model") else "build_report"},
                 evidence=f"modelled cost {model:.6f}")
        summary["stages"]["model"] = {"score_model": model}

        # ---- semantics
        if cfg.get("builder") == "isr":
            st = b.get("stack") or {}
            ok = bool(st.get("check_pass")) and not st.get("has_error")
            E.record(cid, "semantics", "PASS" if ok else "FAIL",
                     evidence=json.dumps(st)[-7000:])
            summary["stages"]["semantics"] = {"pass": ok}
            if not ok:
                return summary
        else:
            E.record(cid, "semantics", "PASS", evidence="builder reported EMITTED")

        # ---- official cascade
        best, bestq = best_for_leg("invsqrt", cid)
        finalist = (best is None or model <= best * 1.02 or
                    (bestq is not None and f["Q"] < bestq))
        mode = official
        if mode == "auto":
            mode = "fast" if finalist else "none"
        summary["finalist"] = finalist
        if mode in ("fast", "full"):
            fp = run_official_invsqrt(kmb, 1, timeout=1800)
            ok = fp.get("status") == "PASS"
            E.record(cid, "proof", "PASS" if ok else "FAIL", score=fp.get("score"),
                     features={k: fp.get(k) for k in
                               ("score", "num_qubits", "toffoli_count", "rotation_count",
                                "worst_error_over_tolerance", "verified_shots") if k in fp},
                     evidence=json.dumps(fp)[-7000:], elapsed=fp.get("elapsed"))
            summary["stages"]["proof"] = {k: fp.get(k) for k in
                                          ("status", "score", "num_qubits",
                                           "worst_error_over_tolerance")}
            if ok and (full or mode == "full"):
                fp2 = run_official_invsqrt(kmb, 64, timeout=5400)
                ok2 = fp2.get("status") == "PASS"
                E.record(cid, "official", "PASS" if ok2 else "FAIL", score=fp2.get("score"),
                         features={k: fp2.get(k) for k in
                                   ("score", "num_qubits", "toffoli_count", "rotation_count",
                                    "worst_error_over_tolerance", "verified_shots") if k in fp2},
                         evidence=json.dumps(fp2)[-7000:], elapsed=fp2.get("elapsed"))
                summary["stages"]["official"] = {k: fp2.get(k) for k in
                                                 ("status", "score", "num_qubits",
                                                  "worst_error_over_tolerance")}
    else:
        # DQI / chemistry: static ledger only; the gate is moat-lab.
        f = kmb_stats(kmb)
        E.record(cid, "static", "PASS", features=f,
                 evidence=f"Q={f['Q']} ops={f['ops']} tof={f['toffoli_like']}")
        model = float(f["Q"]) ** 2 * f["toffoli_like"]
        E.record(cid, "model", "PASS", score=model,
                 features={"score_model": model},
                 evidence=f"modelled DQI cost Q^2*T={model:.3f}")
        summary["stages"]["static"] = f
        summary["stages"]["model"] = {"score_model": model}
        if official in ("auto", "fast", "full"):
            p = queue_moat(cid, row, kmb, f"model={model}")
            E.record(cid, "official", "QUEUED_MOAT",
                     evidence=f"moat request {p}")
            summary["stages"]["official"] = {"queued_moat": str(p)}

    # copy the artifact durably
    ad = ART / f"c{cid:04d}_{slug(row['name'])}"
    ad.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copyfile(kmb, ad / kmb.name)
        (ad / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    except OSError as exc:
        summary["artifact_copy_error"] = str(exc)
    E.set_fields(cid, artifacts={"artifact_dir": str(ad)})
    return summary


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--id", type=int)
    ap.add_argument("--official", default="auto", choices=["auto", "none", "fast", "full"])
    ap.add_argument("--full", action="store_true", help="run the full-shot verifier too")
    ap.add_argument("--list-stages", action="store_true")
    a = ap.parse_args()
    if a.list_stages:
        print("build -> static -> model -> semantics -> proof -> official")
        return
    if not a.id:
        raise SystemExit("--id required")
    out = evaluate(a.id, a.official, a.full)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
