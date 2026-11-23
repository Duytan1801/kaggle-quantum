#!/usr/bin/env python3
"""qcc_cfg_patch.py — deep-merge a JSON overlay into a generator cfg file.

Called by f9_i1_stack.sh right after `mkcfg` writes the cfg, so the overlay
reaches the generator's emit stage (the stage that decides the H1 schedule
and the peak live width).

Usage:  qcc_cfg_patch.py <cfg.json> <overlay.json>

Merge rules
  * dict   -> recursive merge (the overlay wins on scalars)
  * list   -> REPLACED wholesale (a list in the cfg encodes a schedule or a
    table; merging element-wise would be meaningless)
  * scalar -> replaced

The string "<HOME>" in any overlay value is replaced by the home directory
that the driver created, so paths such as `h1c.cubprog` can be pointed at
the bundle's own files.
"""
from __future__ import annotations

import json
import os
import sys


def merge(base, over):
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = merge(out[k], v) if k in out else v
        return out
    return over


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: qcc_cfg_patch.py <cfg.json> <overlay.json>", file=sys.stderr)
        return 2
    cfg_path, overlay_path = sys.argv[1], sys.argv[2]
    with open(cfg_path) as fh:
        cfg = json.load(fh)
    with open(overlay_path) as fh:
        overlay = json.load(fh)

    home = os.environ.get("QCC_HOME", "")
    if home:
        def sub(v):
            if isinstance(v, str):
                return v.replace("<HOME>", home)
            if isinstance(v, list):
                return [sub(x) for x in v]
            if isinstance(v, dict):
                return {k: sub(x) for k, x in v.items()}
            return v
        overlay = sub(overlay)

    merged = merge(cfg, overlay)
    with open(cfg_path, "w") as fh:
        json.dump(merged, fh, indent=1)
    changed = sorted(k for k in overlay if cfg.get(k) != merged.get(k))
    print(f"qcc_cfg_patch: applied {len(overlay)} top-level key(s), changed {changed}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
