#!/usr/bin/env python3
"""build_moat_v127.py — rebuild the moat-lab in-kernel gate for the v125 tree.

From the v124 builder:
  * 18-file SHA_TABLE   -> v125 (public best-per-task mix of 16 Nov 19:00 UTC)
  * discovery anchor    -> qcc-release-v127
  * labels              -> V127_RECEIPT / V127-RECEIPT-PASS  (asserted, no silent no-op)
  * dfthcsos fallback ratio -> the v125 chemistry ratio (the in-kernel chem verifier leg
    normally supplies it; the fallback is the local official-verifier number so a
    leg timeout can never silently report an older cost).

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

SHA_TABLE = {
    k: (v[0], v[1])
    for k, v in json.loads(Path("/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v127.txt").read_text()).items()
}
assert len(SHA_TABLE) == 18, f"expected 18 files in the v125 sha table, got {len(SHA_TABLE)}"

ANCHOR = "qcc-release-v127"
SNAPSHOT_DATASET = "badboyhalo1801/qcc-release-v127"

# v127 chemistry ratio: REF / (maoxin123 a73b25d2 local official-verifier cost 294,643,137.7335714)
DFT_RATIO = "11.38869078753095"

FLAT_FALLBACK = '''def local_path(rel, stored_as=None):
    if rel == "dqi.kmb":
        for p in (ds / "dqi.kmb",):
            if p.exists():
                return p
        xz = ds / "dqi.kmb.xz"
        if xz.exists():
            raw = OUT / "dqi.kmb"
            if not raw.exists():
                import lzma
                raw.write_bytes(lzma.decompress(xz.read_bytes()))
            return raw
        raise FileNotFoundError("dqi.kmb/.xz in " + ds.as_posix())
    cands = [ds / rel,
             ds / (stored_as or "") if stored_as else None,
             ds / rel.replace("/", "__")]          # flat-name snapshot convention
    for p in cands:
        if p is not None and p.exists():
            return p
    raise FileNotFoundError(rel + " in " + ds.as_posix())
'''

DFT_LEG = '''
# --- 4b. dfthcsos official verifier (in-kernel, tree dir) --------------------
dft_verify = None
for r, dirs, fs in os.walk(ROOT):
    if os.path.basename(r) == "dfthcsos" and "verify.py" in fs:
        dft_verify = Path(r) / "verify.py"
if dft_verify is not None and shas_ok:
    try:
        dft_dir = OUT / "dfthcsos_tree"
        dft_dir.mkdir(parents=True, exist_ok=True)
        for k in range(15):
            shutil.copyfile(paths[f"dfthcsos/angle_k_{k}.kmb"], dft_dir / f"angle_k_{k}.kmb")
        shutil.copyfile(paths["dfthcsos/submission.npz"], dft_dir / "submission.npz")
        env = {**os.environ, "PYTHONPATH": PY}
        cmd = [sys.executable, str(dft_verify), str(dft_dir), "--shots-per-address", "1"]
        t = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=7200)
        out = (r.stdout or "") + "\\n" + (r.stderr or "")
        i, j = out.find("{"), out.rfind("}")
        res = {}
        if 0 <= i < j:
            try:
                p = json.loads(out[i:j + 1]); res = p if isinstance(p, dict) else {}
            except Exception:
                pass
        receipt["dfthcsos_in_kernel"] = {"status": res.get("status"), "score": res.get("score"),
                                         "lambda_eff": res.get("lambda_eff"),
                                         "toffoli_count": res.get("toffoli_count"),
                                         "num_qubits": res.get("num_qubits"),
                                         "dt": round(time.time() - t, 1),
                                         "raw_tail": out[-900:]}
        print("[dfthcsos-in-kernel]", receipt["dfthcsos_in_kernel"])
    except Exception as e:
        receipt["dfthcsos_in_kernel"] = {"error": repr(e)[:300]}
else:
    receipt["dfthcsos_in_kernel"] = {"error": "verifiers/dfthcsos/verify.py not mounted or shas not ok"}
'''


def main() -> None:
    d = Path("/tmp/opencode/kernel_moat")
    nb_path = d / "moat-lab.ipynb"
    nb = json.loads(nb_path.read_text())
    cell = nb["cells"][0]
    src = "".join(cell["source"])

    # 1. SHA_TABLE
    new_table = "SHA_TABLE = {\n" + "".join(
        f'    "{k}": ("{v[0]}", {v[1]}),\n' for k, v in sorted(SHA_TABLE.items())) + "}"
    src2, n = re.subn(r"SHA_TABLE = \{.*?\n\}", lambda m: new_table, src, count=1, flags=re.S)
    assert n == 1, "SHA_TABLE block not found"
    src = src2

    # 2. discovery anchor
    src, n = re.subn(r'if "qcc-release-v1[0-9a-z]+" in d\.as_posix\(\):', f'if "{ANCHOR}" in d.as_posix():', src)
    assert n == 1, "anchor pattern not found"

    # 3. local_path flat fallback
    src, n = re.subn(r"def local_path\(rel, stored_as=None\):.*?raise FileNotFoundError\(rel \+ \" in \" \+ ds\.as_posix\(\)\)",
                     lambda m: FLAT_FALLBACK.strip(), src, count=1, flags=re.S)
    assert n == 1, "local_path block not found"

    # 4. dfthcsos leg
    src, n = re.subn(r"# --- 4b\. dfthcsos official verifier.*?(?=\n# --- 5\.)",
                     lambda m: DFT_LEG.strip() + "\n", src, count=1, flags=re.S)
    assert n == 1, "old dfthcsos leg not found"

    # 4c. dfthcsos fallback ratio -> the v125 chemistry ratio
    src, n = re.subn(r'rat\["dfthcsos"\] = [0-9.]+.*', f'rat["dfthcsos"] = {DFT_RATIO}  # v127 local official-verifier receipt '
                     '(maoxin123 a73b25d2 refit on the 906fa220-word table, cost 294,643,137.7335714)', src, count=1)
    assert n == 1, "dfthcsos fallback ratio not found"

    # 5. labels — replace ANY previous V1xx label, assert the new one is present
    src = re.sub(r"V1\d\d_RECEIPT\.json", "V127_RECEIPT.json", src)
    src = re.sub(r"V1\d\d-RECEIPT-PASS", "V127-RECEIPT-PASS", src)
    src = re.sub(r'"dqi-v1\d+"', '"dqi-v127"', src)
    src = re.sub(r'"dfth-v1\d+"', '"dfth-v127"', src)
    src = re.sub(r"moat-lab — v1\d\d RELEASE RECEIPT", "moat-lab — v127 RELEASE RECEIPT", src)
    assert "V127_RECEIPT.json" in src, "receipt label replacement failed"
    assert "V127-RECEIPT-PASS" in src, "pass label replacement failed"
    for stale in ("V121", "V122", "V123", "V124", "V125", "V126"):
        assert stale not in src, f"stale label {stale} left in notebook"

    cell["source"] = src.splitlines(keepends=True)

    # 6. kernel metadata: add the v125 snapshot dataset
    meta_path = d / "kernel-metadata.json"
    meta = json.loads(meta_path.read_text())
    srcs = meta.get("dataset_sources", [])
    if SNAPSHOT_DATASET not in srcs:
        srcs.append(SNAPSHOT_DATASET)
    meta["dataset_sources"] = srcs
    meta_path.write_text(json.dumps(meta, indent=1) + "\n")

    nb_path.write_text(json.dumps(nb, indent=1) + "\n")

    # 7. pre-push gate
    nb2 = json.loads(nb_path.read_text())
    bad = []
    for i, c in enumerate(nb2["cells"]):
        if c.get("cell_type") != "code":
            continue
        try:
            ast.parse("".join(c["source"]))
        except SyntaxError as e:
            bad.append((i, e.msg))
    if bad:
        raise SystemExit(f"notebook syntax FAIL: {bad}")
    src2 = "".join(nb2["cells"][0]["source"])
    checks = {
        "anchor v125": 'if "qcc-release-v127"' in src2,
        "sha table 18": src2.count('": ("') >= 18,
        "flat fallback": 'rel.replace("/", "__")' in src2,
        "dft leg uses paths": 'paths[f"dfthcsos/angle_k_{k}.kmb"]' in src2,
        "shas_ok guard": "dft_verify is not None and shas_ok" in src2,
        "labels v125": "V127_RECEIPT.json" in src2 and "V127-RECEIPT-PASS" in src2,
        "no stale labels": all(s not in src2 for s in ("V121", "V122", "V123", "V124", "V125", "V126")),
        "dft ratio v125": f'rat["dfthcsos"] = {DFT_RATIO}' in src2,
    }
    print("moat-lab rebuilt for", ANCHOR, "- JSON + ast.parse gate PASS")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    assert all(checks.values())
    print("dataset_sources tail:", srcs[-3:])


if __name__ == "__main__":
    main()
