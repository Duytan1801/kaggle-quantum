#!/usr/bin/env python3
"""build_moat_v123.py — rebuild the moat-lab in-kernel gate for the v123 tree.

From the v121 builder:
  * 18-file SHA_TABLE   -> v123 (rescheduled invsqrt f2cdab0b + dqi ccc2ab84 + chem f6e12f02)
  * discovery anchor    -> qcc-release-v123
  * labels              -> V123_RECEIPT / V123-RECEIPT-PASS  (asserted, no silent no-op)

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

# SHA_TABLE is loaded from the static receipt file (work/sha_tables/sha_table_v123.txt)
# so the in-kernel gate can never drift from the locally-verified tree identity.
SHA_TABLE = {
    k: (v[0], v[1])
    for k, v in json.loads(Path("/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v123.txt").read_text()).items()
}
assert len(SHA_TABLE) == 18, f"expected 18 files in the v123 sha table, got {len(SHA_TABLE)}"

ANCHOR = "qcc-release-v123"
SNAPSHOT_DATASET = "badboyhalo1801/qcc-release-v123"

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

    # 5. labels — replace ANY previous V1xx label, assert the new one is present
    src = re.sub(r"V1\d\d_RECEIPT\.json", "V123_RECEIPT.json", src)
    src = re.sub(r"V1\d\d-RECEIPT-PASS", "V123-RECEIPT-PASS", src)
    src = re.sub(r'"dqi-v1\d+"', '"dqi-v123"', src)
    src = re.sub(r'"dfth-v1\d+"', '"dfth-v123"', src)
    src = re.sub(r"moat-lab — v1\d\d RELEASE RECEIPT", "moat-lab — v123 RELEASE RECEIPT", src)
    assert "V123_RECEIPT.json" in src, "receipt label replacement failed"
    assert "V123-RECEIPT-PASS" in src, "pass label replacement failed"
    for stale in ("V121", "V122"):
        assert stale not in src, f"stale label {stale} left in notebook"

    cell["source"] = src.splitlines(keepends=True)

    # 6. kernel metadata: add the v123 snapshot dataset
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
        "anchor v123": 'if "qcc-release-v123"' in src2,
        "sha table 18": src2.count('": ("') >= 18,
        "flat fallback": 'rel.replace("/", "__")' in src2,
        "dft leg uses paths": 'paths[f"dfthcsos/angle_k_{k}.kmb"]' in src2,
        "shas_ok guard": "dft_verify is not None and shas_ok" in src2,
        "labels v123": "V123_RECEIPT.json" in src2 and "V123-RECEIPT-PASS" in src2,
        "no stale labels": "V121" not in src2 and "V122" not in src2,
    }
    print("moat-lab rebuilt for", ANCHOR, "- JSON + ast.parse gate PASS")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    assert all(checks.values())
    print("dataset_sources tail:", srcs[-3:])


if __name__ == "__main__":
    main()
