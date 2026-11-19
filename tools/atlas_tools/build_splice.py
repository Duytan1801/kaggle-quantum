#!/usr/bin/env python3
"""build_splice: write the kmx circuit described by a splice_dp.py result.

Each segment [name, start, stop] copies body ops start..stop-1 (register lines excluded) of the circuit whose file
name starts with `name`. Classical bits are renumbered per segment so segments never share a bit. The register
header is taken from the first segment's circuit.

    python build_splice.py splice.json spliced.kmx --kmx-dir DIR

Licence: Apache-2.0.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kmsim  # noqa: E402


def load_lines(name, kmx_dir):
    """(header lines, body lines) of the circuit DIR/name*.kmx[.gz]."""
    hits = sorted(glob.glob(os.path.join(kmx_dir, name + "*.kmx")) + glob.glob(os.path.join(kmx_dir, name + "*.kmx.gz")))
    if not hits:
        raise FileNotFoundError(f"no {name}*.kmx in {kmx_dir}")
    head, body = [], []
    with kmsim.open_text(hits[0]) as fh:
        for line in fh:
            t = line.split()
            if not t:
                continue
            (head if t[0] in ("APPEND_TO_REGISTER", "REGISTER") else body).append(line.rstrip("\n"))
    return head, body


def remap_bits(line, table, counter):
    out = []
    for tok in line.split():
        if tok.startswith("b") and tok[1:].isdigit():
            if tok not in table:
                table[tok] = "b" + str(counter[0])
                counter[0] += 1
            tok = table[tok]
        out.append(tok)
    return " ".join(out)


def build(segs, out, kmx_dir):
    head = None
    lines = []
    counter = [0]
    for name, a, b in segs:
        h, body = load_lines(name, kmx_dir)
        head = head or h
        table = {}
        lines += [remap_bits(l, table, counter) for l in body[a:b]]
    with open(out, "w") as f:
        f.write("\n".join(head + lines) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Build a kmx circuit from a splice_dp.py segment list.")
    ap.add_argument("splice_json", help="output of splice_dp.py")
    ap.add_argument("out_kmx", help="kmx file to write")
    ap.add_argument("--kmx-dir", default=".", help="folder that holds the source circuits (default: current folder)")
    a = ap.parse_args(argv)
    build(json.load(open(a.splice_json))["segments"], a.out_kmx, a.kmx_dir)
    print("wrote", a.out_kmx)


if __name__ == "__main__":
    main()
