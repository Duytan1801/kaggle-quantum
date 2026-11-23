#!/usr/bin/env python3
"""evo_engine.py — durable evolutionary population store for the QCC campaign.

This is the AlphaEvolve-style "programs database" the campaign was missing.
It is deliberately small and mechanical:

  candidates   one row per distinct build recipe (config), deduped by SHA-256
  evaluations  one row per (candidate, cascade stage) with evidence + timing
  runs         one row per worker invocation (survives restarts)

Every candidate carries:
  * parent_id / mechanism / island  -> lineage, mutation family, MAP-Elites cell
  * status ladder                   -> PROPOSED -> BUILT -> SCORED ->
                                       SEMANTICS_OK -> PROOF_OK -> OFFICIAL_PASS
  * score_model / score_official    -> cheap proxy vs the unchanged verifier
  * features (JSON)                 -> Q, Toffoli, T, rotations, peak-live, sha

Why SQLite: parallel evaluators are a first-class requirement (AlphaEvolve runs
many programs in flight), and a single JSON file corrupts under concurrent
writers.  WAL mode lets a reader (`list`, `select`) run while a worker writes.

CLI
  init
  add --leg invsqrt --name X --config '<json>' [--parent ID] [--mechanism M] [--island I]
  record --id N --stage model --status PASS --score 60927.5 --features '<json>' --evidence '...'
  fail --id N --stage build --evidence '...'
  list [--leg L] [--status S] [--top N]
  show ID
  select --leg invsqrt --n 8
  islands
  import-population work/evo/population.json
  export PATH
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.environ.get("EVO_DB", ROOT / "work/evo/evo.sqlite3"))

LADDER = ["PROPOSED", "BUILT", "SCORED", "SEMANTICS_OK", "PROOF_OK", "OFFICIAL_PASS"]
RANK = {s: i for i, s in enumerate(LADDER)}
TERMINAL = {"FAILED", "REJECTED", "QUEUED_MOAT"}
# cascade stage -> the ladder rung it earns on PASS
STAGE_TO_STATUS = {
    "build": "BUILT",
    "static": "SCORED",
    "model": "SCORED",
    "semantics": "SEMANTICS_OK",
    "proof": "PROOF_OK",          # fast official verifier (screening, not the gate)
    "official": "OFFICIAL_PASS",  # full unchanged official verifier
}


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def canon(cfg) -> str:
    return json.dumps(cfg, sort_keys=True, separators=(",", ":"))


def cfg_hash(cfg) -> str:
    return hashlib.sha256(canon(cfg).encode()).hexdigest()[:16]


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH, timeout=60)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=60000")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


SCHEMA = """
CREATE TABLE IF NOT EXISTS candidates (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  leg           TEXT NOT NULL,
  name          TEXT NOT NULL UNIQUE,
  parent_id     INTEGER,
  config        TEXT NOT NULL,
  config_hash   TEXT NOT NULL UNIQUE,
  mechanism     TEXT NOT NULL DEFAULT '',
  island        TEXT NOT NULL DEFAULT '',
  status        TEXT NOT NULL DEFAULT 'PROPOSED',
  stage         TEXT NOT NULL DEFAULT '',
  score         REAL,
  score_model   REAL,
  score_official REAL,
  features      TEXT NOT NULL DEFAULT '{}',
  artifacts     TEXT NOT NULL DEFAULT '{}',
  note          TEXT NOT NULL DEFAULT '',
  created       TEXT NOT NULL,
  updated       TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS evaluations (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  candidate_id  INTEGER NOT NULL,
  stage         TEXT NOT NULL,
  status        TEXT NOT NULL,
  score         REAL,
  features      TEXT NOT NULL DEFAULT '{}',
  evidence      TEXT NOT NULL DEFAULT '',
  elapsed       REAL,
  ts            TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS runs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  kind          TEXT NOT NULL,
  summary       TEXT NOT NULL DEFAULT '',
  ts            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_cand_leg ON candidates(leg, status);
CREATE INDEX IF NOT EXISTS ix_eval_cand ON evaluations(candidate_id, stage);
"""


def init_db(con: sqlite3.Connection | None = None) -> None:
    c = con or connect()
    c.executescript(SCHEMA)
    c.commit()


def _json_or_empty(text) -> dict:
    if not text:
        return {}
    if isinstance(text, dict):
        return text
    try:
        v = json.loads(text)
        return v if isinstance(v, dict) else {}
    except Exception:
        return {}


def add(leg: str, name: str, config: dict, parent: int | None = None,
        mechanism: str = "", island: str = "", note: str = "",
        status: str = "PROPOSED", stage: str = "", score: float | None = None,
        score_model: float | None = None, score_official: float | None = None,
        features: dict | None = None, artifacts: dict | None = None,
        con: sqlite3.Connection | None = None) -> tuple[int, bool]:
    """Add a candidate. Returns (id, created). Duplicate configs are not re-run."""
    c = con or connect()
    init_db(c)
    h = cfg_hash(config)
    row = c.execute("SELECT id FROM candidates WHERE config_hash=?", (h,)).fetchone()
    if row:
        return int(row["id"]), False
    ts = now()
    island = island or f"{leg}:{mechanism or 'unassigned'}"
    cur = c.execute(
        """INSERT INTO candidates
           (leg,name,parent_id,config,config_hash,mechanism,island,status,stage,
            score,score_model,score_official,features,artifacts,note,created,updated)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (leg, name, parent, canon(config), h, mechanism, island, status, stage,
         score, score_model, score_official,
         json.dumps(features or {}, sort_keys=True),
         json.dumps(artifacts or {}, sort_keys=True), note, ts, ts))
    c.commit()
    return int(cur.lastrowid), True


def _merge_json(old: str, new: dict | None) -> str:
    if not new:
        return old or "{}"
    d = _json_or_empty(old)
    d.update(new)
    return json.dumps(d, sort_keys=True)


def record(candidate_id: int, stage: str, status: str, *,
           score: float | None = None, features: dict | None = None,
           evidence: str = "", elapsed: float | None = None,
           con: sqlite3.Connection | None = None) -> dict:
    """Append an evaluation and advance (never regress) the candidate status."""
    c = con or connect()
    init_db(c)
    row = c.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()
    if not row:
        raise SystemExit(f"no candidate {candidate_id}")
    ts = now()
    c.execute(
        """INSERT INTO evaluations(candidate_id,stage,status,score,features,evidence,elapsed,ts)
           VALUES (?,?,?,?,?,?,?,?)""",
        (candidate_id, stage, status, score,
         json.dumps(features or {}, sort_keys=True), evidence[:8000], elapsed, ts))

    cur_status = row["status"]
    new_status = cur_status
    new_stage = row["stage"] or stage
    if status in ("FAIL", "FAILED"):
        # A build/static/semantic failure is terminal for this candidate: a
        # later expensive stage never rescues bytes that already failed.  The
        # fast `proof` screen is the exception — one transcript per x can fail
        # by chance, so it only records the evidence and leaves the candidate
        # eligible for a full official run.
        if stage != "proof":
            new_status = "FAILED"
        new_stage = stage
    elif status in TERMINAL:
        new_status = status
        new_stage = stage
    elif status == "PASS":
        target = STAGE_TO_STATUS.get(stage, stage)
        if RANK.get(target, -1) >= RANK.get(cur_status, -1):
            new_status = target
            new_stage = stage
        else:
            new_stage = stage

    score_model = row["score_model"]
    score_official = row["score_official"]
    score_best = row["score"]
    if score is not None and status == "PASS":
        if stage == "official":
            score_official = score
            score_best = score
        else:
            score_model = score
            if score_official is None:
                score_best = score
    c.execute(
        """UPDATE candidates SET status=?, stage=?, score=?, score_model=?,
           score_official=?, features=?, artifacts=?, updated=? WHERE id=?""",
        (new_status, new_stage, score_best, score_model, score_official,
         _merge_json(row["features"], features),
         _merge_json(row["artifacts"], {"last_stage": stage, "last_evidence": evidence[:400]}),
         ts, candidate_id))
    c.commit()
    return {"id": candidate_id, "status": new_status, "stage": new_stage}


def fail(candidate_id: int, stage: str, evidence: str,
         con: sqlite3.Connection | None = None) -> dict:
    return record(candidate_id, stage, "FAIL", evidence=evidence, con=con)


def set_fields(candidate_id: int, **fields) -> None:
    if not fields:
        return
    c = connect()
    allowed = {"status", "stage", "score", "score_model", "score_official", "note",
               "mechanism", "island", "features", "artifacts"}
    sets, vals = [], []
    for k, v in fields.items():
        if k not in allowed:
            raise SystemExit(f"field not allowed: {k}")
        if k in ("features", "artifacts") and isinstance(v, dict):
            v = json.dumps(v, sort_keys=True)
        sets.append(f"{k}=?")
        vals.append(v)
    sets.append("updated=?")
    vals.append(now())
    vals.append(candidate_id)
    c.execute(f"UPDATE candidates SET {', '.join(sets)} WHERE id=?", vals)
    c.commit()


def rows(leg: str | None = None, status: str | None = None,
         top: int = 50) -> list[sqlite3.Row]:
    c = connect()
    init_db(c)
    q = "SELECT * FROM candidates WHERE 1=1"
    a = []
    if leg:
        q += " AND leg=?"
        a.append(leg)
    if status:
        q += " AND status=?"
        a.append(status)
    q += " ORDER BY (score IS NULL), score ASC, id ASC LIMIT ?"
    a.append(top)
    return list(c.execute(q, a))


def get(candidate_id: int) -> sqlite3.Row | None:
    c = connect()
    init_db(c)
    return c.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()


def evaluations(candidate_id: int) -> list[sqlite3.Row]:
    c = connect()
    init_db(c)
    return list(c.execute(
        "SELECT * FROM evaluations WHERE candidate_id=? ORDER BY id", (candidate_id,)))


def _q_of(row) -> int | None:
    f = _json_or_empty(row["features"])
    for k in ("Q", "qubits", "num_qubits"):
        if isinstance(f.get(k), (int, float)):
            return int(f[k])
    return None


def select_parents(leg: str, n: int = 8) -> list[sqlite3.Row]:
    """Union of three archives, so a stepping stone is never lost:

      1. performance: best score per mechanism island (top 2 each)
      2. width:       best score at each Q (a worse-cost narrower build is a parent)
      3. global:      the overall top candidates
    """
    c = connect()
    init_db(c)
    allrows = [r for r in c.execute(
        "SELECT * FROM candidates WHERE leg=? AND status NOT IN ('FAILED','REJECTED')", (leg,))]
    if not allrows:
        return []
    key = lambda r: (r["score"] is None, r["score"] if r["score"] is not None else 1e300, r["id"])

    by_island: dict[str, list] = {}
    by_q: dict[int, list] = {}
    for r in allrows:
        by_island.setdefault(r["island"] or r["mechanism"] or "none", []).append(r)
        q = _q_of(r)
        if q is not None:
            by_q.setdefault(q, []).append(r)

    picked: list = []
    for _, rs in sorted(by_island.items()):
        picked.extend(sorted(rs, key=key)[:2])
    for _, rs in sorted(by_q.items()):
        picked.append(sorted(rs, key=key)[0])
    picked.extend(sorted(allrows, key=key)[:max(3, n // 2)])

    seen, out = set(), []
    for r in picked:
        if r["id"] not in seen:
            seen.add(r["id"])
            out.append(r)
    out.sort(key=key)
    return out[:n]


def import_population(path: Path) -> tuple[int, int]:
    data = json.loads(path.read_text())
    created = dup = 0
    for v in data.get("variants", []):
        cfg = dict(v.get("config") or {})
        cfg.setdefault("builder", "syed")
        leg = cfg.get("leg", "invsqrt")
        status = "SCORED" if v.get("score") is not None else (
            "FAILED" if v.get("status") == "FAILED" else "PROPOSED")
        cid, new = add(
            leg=leg, name=f"pop_{v['id']}", config=cfg, parent=None,
            mechanism=(v.get("note") or "legacy")[:60],
            status=status, score=v.get("score"),
            score_model=v.get("score"), features=v.get("parts") or {},
            artifacts=v.get("artifacts") or {},
            note=v.get("note") or "")
        created += int(new)
        dup += int(not new)
    return created, dup


def export(path: Path) -> None:
    c = connect()
    init_db(c)
    out = {"exported": now(), "candidates": [], "evaluations": []}
    for r in c.execute("SELECT * FROM candidates ORDER BY id"):
        d = dict(r)
        d["config"] = json.loads(d["config"])
        d["features"] = _json_or_empty(d["features"])
        d["artifacts"] = _json_or_empty(d["artifacts"])
        out["candidates"].append(d)
    for r in c.execute("SELECT * FROM evaluations ORDER BY id"):
        d = dict(r)
        d["features"] = _json_or_empty(d["features"])
        out["evaluations"].append(d)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1) + "\n")


# ---------------------------------------------------------------- CLI
def cmd_list(a):
    for r in rows(a.leg, a.status, a.top):
        f = _json_or_empty(r["features"])
        q = f.get("Q") or f.get("qubits") or "?"
        print(f"{r['id']:>4} {r['leg']:<8} {r['status']:<13} Q={str(q):<4} "
              f"score={str(round(r['score'], 4) if r['score'] is not None else '—'):>12} "
              f"model={str(round(r['score_model'], 2) if r['score_model'] is not None else '—'):>10} "
              f"island={r['island'][:28]:<28} {r['name'][:34]}")
    print(f"({len(rows(a.leg, a.status, 100000))} candidates)")


def cmd_show(a):
    r = get(a.id)
    if not r:
        raise SystemExit(f"no candidate {a.id}")
    d = dict(r)
    for k in ("config", "features", "artifacts"):
        d[k] = json.loads(d[k])
    print(json.dumps(d, indent=2))
    for e in evaluations(a.id):
        print(f"  [{e['ts']}] {e['stage']:<10} {e['status']:<8} "
              f"score={e['score']} elapsed={e['elapsed']} {e['evidence'][:160]}")


def cmd_select(a):
    ps = select_parents(a.leg, a.n)
    if not ps:
        print("no parents")
        return
    for r in ps:
        print(f"{r['id']:>4} {r['status']:<13} score={r['score']} island={r['island']} "
              f"cfg={r['config'][:220]}")


def cmd_islands(a):
    c = connect()
    init_db(c)
    for r in c.execute(
            "SELECT island, leg, COUNT(*) n, MIN(COALESCE(score_official,score_model)) best "
            "FROM candidates GROUP BY island ORDER BY leg, best"):
        print(f"{r['leg']:<8} {r['island'][:44]:<44} n={r['n']:<4} best={r['best']}")


def main(argv=None):
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")

    q = sub.add_parser("add")
    q.add_argument("--leg", required=True)
    q.add_argument("--name", required=True)
    q.add_argument("--config", required=True)
    q.add_argument("--parent", type=int)
    q.add_argument("--mechanism", default="")
    q.add_argument("--island", default="")
    q.add_argument("--note", default="")
    q.add_argument("--status", default="PROPOSED")
    q.add_argument("--score", type=float)
    q.add_argument("--features", default="{}")

    q = sub.add_parser("record")
    q.add_argument("--id", type=int, required=True)
    q.add_argument("--stage", required=True)
    q.add_argument("--status", required=True)
    q.add_argument("--score", type=float)
    q.add_argument("--features", default="{}")
    q.add_argument("--evidence", default="")
    q.add_argument("--elapsed", type=float)

    q = sub.add_parser("fail")
    q.add_argument("--id", type=int, required=True)
    q.add_argument("--stage", required=True)
    q.add_argument("--evidence", default="")

    q = sub.add_parser("list")
    q.add_argument("--leg")
    q.add_argument("--status")
    q.add_argument("--top", type=int, default=40)

    q = sub.add_parser("show")
    q.add_argument("id", type=int)

    q = sub.add_parser("select")
    q.add_argument("--leg", required=True)
    q.add_argument("--n", type=int, default=8)

    sub.add_parser("islands")

    q = sub.add_parser("import-population")
    q.add_argument("path", type=Path)

    q = sub.add_parser("export")
    q.add_argument("path", type=Path)

    a = p.parse_args(argv)
    if a.cmd == "init":
        init_db()
        print(f"initialised {DB_PATH}")
    elif a.cmd == "add":
        cid, new = add(a.leg, a.name, json.loads(a.config), parent=a.parent,
                       mechanism=a.mechanism, island=a.island, note=a.note,
                       status=a.status, score=a.score,
                       features=json.loads(a.features))
        print(f"{'ADDED' if new else 'DUPLICATE'} id={cid} hash={cfg_hash(json.loads(a.config))}")
    elif a.cmd == "record":
        print(record(a.id, a.stage, a.status, score=a.score,
                     features=json.loads(a.features), evidence=a.evidence,
                     elapsed=a.elapsed))
    elif a.cmd == "fail":
        print(fail(a.id, a.stage, a.evidence))
    elif a.cmd == "list":
        cmd_list(a)
    elif a.cmd == "show":
        cmd_show(a)
    elif a.cmd == "select":
        cmd_select(a)
    elif a.cmd == "islands":
        cmd_islands(a)
    elif a.cmd == "import-population":
        print(import_population(a.path))
    elif a.cmd == "export":
        export(a.path)
        print(f"exported {a.path}")


if __name__ == "__main__":
    main()
