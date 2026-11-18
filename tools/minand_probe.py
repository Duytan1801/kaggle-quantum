#!/usr/bin/env python3
"""minand_probe.py — H2 probe: decode Syed's minand_sat form schema and recover
the target function + care-row set directly from a shipped form file.

Form schema (confirmed against v9_form_e2.json and the consumer
w2core_e2.py::_emit_form):
  inputs  : list of input wire names (n of them)
  gates[i]: {'left': [idx...], 'right': [idx...]} — gate i computes
            AND( XOR(left), XOR(right) ); indices < n are inputs,
            indices >= n refer to earlier gates (index n+i == gate i)
  output  : {'constant': 0/1, 'terms': [idx...]} — final value is
            constant XOR (XOR of the referenced inputs/gates)

Usage:
  python3 minand_probe.py <form.json> [more.json ...]
"""
import json, sys


def eval_form(form):
    """Return (table, n) where table[x] is the form's value on input vector x."""
    n = len(form["inputs"])
    gates = form["gates"]
    table = []
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)]
        vals = list(bits)                      # vals[j] for j<n = inputs
        for gi, g in enumerate(gates):
            def parity(idxs):
                p = 0
                for j in idxs:
                    p ^= vals[j]
                return p
            vals.append(parity(g["left"]) & parity(g["right"]))
        out = form["output"]["constant"] & 1
        for t in form["output"]["terms"]:
            out ^= vals[t]
        table.append(out)
    return table, n


def gate_values(form, gi):
    """Truth table of gate gi alone (1 if the AND-gate is 1)."""
    n = len(form["inputs"])
    gates = form["gates"]
    tab = []
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)]
        vals = list(bits)
        for k, g in enumerate(gates):
            def parity(idxs, vals=vals):
                p = 0
                for j in idxs:
                    p ^= vals[j]
                return p
            vals.append(parity(g["left"]) & parity(g["right"]))
        tab.append(vals[n + gi])
    return tab


def describe(path):
    form = json.load(open(path))
    table, n = eval_form(form)
    gates = form["gates"]
    names = form["inputs"]
    print(f"\n=== {path}")
    print(f"inputs({n}) = {names}   gates = {len(gates)}   output terms = {form['output']['terms']} const={form['output']['constant']}")
    print(f"table = {''.join(str(v) for v in table)}")
    ones = [i for i, v in enumerate(table) if v]
    print(f"table ones: {len(ones)}/{1 << n}")

    # candidate target = AND of the two parities of gate 0 (the literal 'exact AND')
    g0 = gates[0]
    tgt = []
    for x in range(1 << n):
        bits = [(x >> i) & 1 for i in range(n)]
        a = 0
        for j in g0["left"]:
            a ^= bits[j]
        b = 0
        for j in g0["right"]:
            b ^= bits[j]
        tgt.append(a & b)
    agree = [i for i in range(1 << n) if table[i] == tgt[i]]
    disagree = [i for i in range(1 << n) if table[i] != tgt[i]]
    print(f"form == AND(parity(g0.left), parity(g0.right)) on {len(agree)} rows; differs on {len(disagree)}: {disagree}")
    if disagree:
        # candidate care set = rows where form still equals g0's AND (the don't-care filler differs)
        gt = gate_values(form, 0)
        alt_agree = [i for i in range(1 << n) if gt[i] == tgt[i]]
        print(f"g0 alone == AND on {len(alt_agree)} rows (trivially 64 if g0 is that AND)")
    return {"n": n, "table": table, "target": tgt, "agree": agree, "disagree": disagree,
            "form": form, "care_rows_field": form.get("care_rows")}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(2)
    for p in sys.argv[1:]:
        describe(p)
