#!/usr/bin/env python3
"""evo_pop.py — H6 population store for evolutionary generator search.

AlphaEvolve's "programs database": every variant tried, its canonical config,
its verified score, score parts, and durable artifact pointers.  The store is
append/update oriented, atomically persisted, and deduplicates by canonical
configuration hash so a wake never repeats a known experiment.

Usage:
  python3 evo_pop.py add   --config '{"leg":"invsqrt","Q":46}' [--parent v0] [--note "..."]
  python3 evo_pop.py set   --id v3 --score 74560.91 --parts '{"Q":44}' --artifacts '{"tree":"/tmp/x"}'
  python3 evo_pop.py fail  --id v3 --note "carry alloc 46>45"
  python3 evo_pop.py list  [--top 10]
  python3 evo_pop.py prompt [--top 5]
"""
import argparse
import hashlib
import json
import os
import sys
import time

DB = os.environ.get("EVO_DB", "/home/bandoc/Downloads/opencode/work/evo/population.json")


def parse_config(text):
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("--config must be a JSON object")
    return value


def canon(cfg):
    return json.dumps(cfg, sort_keys=True, separators=(",", ":"))


def load():
    if not os.path.exists(DB):
        return {"variants": [], "created": time.time()}
    with open(DB) as f:
        db = json.load(f)
    if not isinstance(db, dict) or not isinstance(db.get("variants"), list):
        raise ValueError(f"invalid population database: {DB}")
    return db


def save(db):
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    tmp = DB + ".tmp"
    with open(tmp, "w") as f:
        json.dump(db, f, indent=1, sort_keys=False)
        f.write("\n")
    os.replace(tmp, DB)


def find(db, vid):
    for v in db["variants"]:
        if v["id"] == vid:
            return v
    return None


def cmd_add(a):
    db = load()
    cfg = parse_config(a.config)
    h = hashlib.sha256(canon(cfg).encode()).hexdigest()[:12]
    for v in db["variants"]:
        if v.get("hash") == h:
            print(f"DUPLICATE {v['id']} (hash {h}) — not re-running (rule 3)")
            return v["id"]
    n = len(db["variants"]) + 1
    vid = f"v{n:03d}"
    rec = {
        "id": vid,
        "hash": h,
        "parent": a.parent,
        "config": cfg,
        "score": None,
        "parts": None,
        "status": "NEW",
        "artifacts": {},
        "note": a.note or "",
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    db["variants"].append(rec)
    save(db)
    print(f"ADDED {vid} hash={h} config={canon(cfg)}")
    return vid


def _as_json(value):
    """Accept a JSON string or an already-decoded dict/list (never both)."""
    if value is None or isinstance(value, (dict, list)):
        return value
    return json.loads(value)


def cmd_set(a):
    db = load()
    v = find(db, a.id)
    if not v:
        print(f"NO SUCH VARIANT {a.id}")
        sys.exit(1)
    v["score"] = a.score
    v["parts"] = _as_json(a.parts)
    v["artifacts"] = _as_json(a.artifacts) or {}
    # SCORED = emitted and modelled-scored (not yet proved/verified);
    # VERIFIED = passed the exact proof + official verifier.
    v["status"] = getattr(a, "status", None) or "VERIFIED"
    if a.note:
        v["note"] = a.note
    save(db)
    print(f"SET {a.id} score={a.score} status={v['status']}")


def cmd_fail(a):
    db = load()
    v = find(db, a.id)
    if not v:
        print(f"NO SUCH VARIANT {a.id}")
        sys.exit(1)
    v["status"] = "FAILED"
    v["note"] = a.note or ""
    save(db)
    print(f"FAILED {a.id}: {v['note']}")


def cmd_list(a):
    db = load()
    vs = sorted([v for v in db["variants"] if v.get("score") is not None], key=lambda v: -v["score"])
    vs += [v for v in db["variants"] if v.get("score") is None]
    for v in vs[: a.top]:
        print(f"{v['id']:>5}  score={str(v.get('score')):>12}  status={v['status']:<8} "
              f"parent={str(v.get('parent')):<5} {v['note'][:70]}")
    print(f"({len(db['variants'])} variants, {sum(1 for v in db['variants'] if v.get('score') is not None)} verified)")


def cmd_prompt(a):
    db = load()
    vs = sorted([v for v in db["variants"] if v.get("score") is not None], key=lambda v: -v["score"])[: a.top]
    if not vs:
        print("population is empty — no verified variant to sample from")
        return
    print("TOP VARIANTS (generate a mutation of the best; return a NEW config, not prose):")
    for v in vs:
        print(f"  {v['id']} score={v['score']} parts={json.dumps(v.get('parts'))} cfg={canon(v['config'])}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    q = sub.add_parser("add")
    q.add_argument("--config", required=True)
    q.add_argument("--parent")
    q.add_argument("--note")
    q.set_defaults(fn=cmd_add)
    q = sub.add_parser("set")
    q.add_argument("--id", required=True)
    q.add_argument("--score", type=float, required=True)
    q.add_argument("--parts")
    q.add_argument("--artifacts")
    q.add_argument("--note")
    q.set_defaults(fn=cmd_set)
    q = sub.add_parser("fail")
    q.add_argument("--id", required=True)
    q.add_argument("--note")
    q.set_defaults(fn=cmd_fail)
    q = sub.add_parser("list")
    q.add_argument("--top", type=int, default=20)
    q.set_defaults(fn=cmd_list)
    q = sub.add_parser("prompt")
    q.add_argument("--top", type=int, default=5)
    q.set_defaults(fn=cmd_prompt)
    a = p.parse_args()
    a.fn(a)
