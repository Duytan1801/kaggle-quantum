#!/usr/bin/env python3
"""evo_worker.py — resource-aware parallel evaluator loop.

Claims PROPOSED candidates from evo_engine, runs each through evo_eval.py, and
keeps the population store current.  It is restart-safe: a claimed candidate is
marked RUNNING; `--reclaim` puts stale RUNNING rows back in the queue.

The worker is deliberately conservative with memory.  The box has ~7 GB and the
ISR generator peaks near 2-3 GB, so `--parallel 1` is forced for ISR builds
unless explicitly overridden.  Cheap Syed builds can run 2-3 wide.

Usage
  evo_worker.py --leg invsqrt --max 3 --official auto
  evo_worker.py --leg invsqrt --minutes 90 --parallel 1
  evo_worker.py --reclaim 180
  evo_worker.py --status
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "work/tools"))
import evo_engine as E  # noqa: E402

PY = ROOT / "work/toolchain/venv/bin/python"
RUN_CAPPED = ROOT / "harness/run_capped.sh"
LOGDIR = ROOT / "work/evo/runs"
CAP = os.environ.get("EVO_CAP", "3G")


def log(msg: str, fh=None) -> None:
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    if fh:
        fh.write(line + "\n")
        fh.flush()


def claim(leg: str, con, stale_minutes: int = 240) -> int | None:
    con.execute("BEGIN IMMEDIATE")
    try:
        cutoff = time.strftime("%Y-%m-%d %H:%M:%S",
                               time.localtime(time.time() - stale_minutes * 60))
        con.execute("UPDATE candidates SET status='PROPOSED' WHERE status='RUNNING' AND updated<?",
                    (cutoff,))
        row = con.execute(
            "SELECT id,name FROM candidates WHERE leg=? AND status='PROPOSED' ORDER BY id LIMIT 1",
            (leg,)).fetchone()
        if not row:
            con.commit()
            return None
        con.execute("UPDATE candidates SET status='RUNNING', updated=? WHERE id=?",
                    (E.now(), row["id"]))
        con.commit()
        return int(row["id"])
    except Exception:
        con.rollback()
        raise


def reclaim(minutes: int) -> int:
    con = E.connect()
    E.init_db(con)
    cutoff = time.strftime("%Y-%m-%d %H:%M:%S",
                           time.localtime(time.time() - minutes * 60))
    cur = con.execute("UPDATE candidates SET status='PROPOSED', updated=? "
                      "WHERE status='RUNNING' AND updated<?", (E.now(), cutoff))
    con.commit()
    return cur.rowcount


def run_one(cid: int, official: str, full: bool) -> dict:
    cmd = [str(PY), str(ROOT / "work/tools/evo_eval.py"), "--id", str(cid),
           "--official", official]
    if full:
        cmd.append("--full")
    env = os.environ.copy()
    env["EVO_NO_CAP"] = "1"          # the worker already owns the cgroup
    if RUN_CAPPED.exists():
        cmd = [str(RUN_CAPPED), CAP, *cmd]
    began = time.monotonic()
    p = subprocess.run(cmd, capture_output=True, text=True, env=env)
    elapsed = time.monotonic() - began
    out = {}
    try:
        out = json.loads(p.stdout)
    except Exception:
        out = {"raw_tail": (p.stdout or p.stderr)[-1500:]}
    out["rc"] = p.returncode
    out["elapsed"] = round(elapsed, 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--leg", default="invsqrt")
    ap.add_argument("--max", type=int, default=0, help="0 = until the queue is empty")
    ap.add_argument("--minutes", type=float, default=0, help="0 = no wall-clock cap")
    ap.add_argument("--parallel", type=int, default=1)
    ap.add_argument("--official", default="auto", choices=["auto", "none", "fast", "full"])
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--reclaim", type=int, metavar="MINUTES")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    if a.status:
        for r in E.rows(a.leg, None, 1000):
            print(f"{r['id']:>4} {r['status']:<13} {r['name'][:50]}")
        return
    if a.reclaim is not None:
        print(f"reclaimed {reclaim(a.reclaim)} stale RUNNING candidates")
        return

    E.init_db()
    LOGDIR.mkdir(parents=True, exist_ok=True)
    logpath = LOGDIR / f"worker_{time.strftime('%Y%m%d_%H%M%S')}.log"
    deadline = time.time() + a.minutes * 60 if a.minutes else None
    con = E.connect()
    done = 0
    parallel = a.parallel
    if a.leg == "invsqrt" and parallel > 1 and not os.environ.get("EVO_ALLOW_PARALLEL_ISR"):
        parallel = 1

    with logpath.open("w") as fh:
        log(f"worker start leg={a.leg} parallel={parallel} official={a.official} "
            f"max={a.max or 'queue'} minutes={a.minutes or 'none'}", fh)
        while True:
            if deadline and time.time() >= deadline:
                log("wall-clock budget reached", fh)
                break
            if a.max and done >= a.max:
                log("max reached", fh)
                break
            batch = []
            for _ in range(parallel):
                cid = claim(a.leg, con)
                if cid is None:
                    break
                batch.append(cid)
            if not batch:
                log("queue empty", fh)
                break
            log(f"claimed {batch}", fh)
            if parallel == 1:
                out = run_one(batch[0], a.official, a.full)
                done += 1
                log(f"c{batch[0]:04d} rc={out.get('rc')} elapsed={out.get('elapsed')}s "
                    f"{json.dumps({k: out.get(k) for k in ('finalist', 'stages')})[:700]}", fh)
            else:
                with ThreadPoolExecutor(max_workers=parallel) as ex:
                    futs = {ex.submit(run_one, c, a.official, a.full): c for c in batch}
                    for f in as_completed(futs):
                        c = futs[f]
                        out = f.result()
                        done += 1
                        log(f"c{c:04d} rc={out.get('rc')} elapsed={out.get('elapsed')}s "
                            f"{json.dumps({k: out.get(k) for k in ('finalist', 'stages')})[:700]}", fh)
        log(f"worker done: {done} evaluated; log {logpath}", fh)
        con.execute("INSERT INTO runs(kind,summary,ts) VALUES (?,?,?)",
                    ("worker", f"leg={a.leg} evaluated={done} log={logpath}", E.now()))
        con.commit()


if __name__ == "__main__":
    main()
