#!/usr/bin/env python3
"""build_moat_v120.py — rebuild the moat-lab in-kernel gate for the v120 tree.

Takes the pulled `moat-lab.ipynb` (the it18-era gate cell) and rewrites it for
the CURRENT live tree:

  * the hardcoded 18-file SHA_TABLE (tree identity, immune to label drift),
  * the discovery anchor (our frozen snapshot dataset `qcc-release-v120`),
  * an extra in-kernel dfthcsos leg (the official `verifiers/dfthcsos/verify.py`
    run on the mounted loaders — it is cheap and gives the chem cost in-kernel),
  * the receipt/verdict labels.

Then it writes `moat-lab.ipynb` + `kernel-metadata.json` and applies the
pre-push gate: the notebook JSON must parse and every code cell must pass
`ast.parse`.

    python3 build_moat_v120.py [--dir /tmp/opencode/kernel_moat]
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path

SHA_TABLE = {
    "dfthcsos/angle_k_0.kmb": ("71735b23037e8a64d16e39b3347d440b36bdf8813613ec70c36a85bfd362d7c2", 410442),
    "dfthcsos/angle_k_1.kmb": ("7032e8c6430ba22acc3a127397b637746df3129e19ebd49693f07059f0557bcc", 413301),
    "dfthcsos/angle_k_10.kmb": ("8c68db4e05a99107d4ebe432a2faed82ea63c40ed85c65e410298a6e926d908b", 339213),
    "dfthcsos/angle_k_11.kmb": ("34109c735ed8591fb0c5c2e737bb0287770183b04b3729c63377098dba0c5284", 354075),
    "dfthcsos/angle_k_12.kmb": ("473493c3c9f20c718a77252ef4d2d424715ed64cf97da5eed0340c180263c9b2", 341601),
    "dfthcsos/angle_k_13.kmb": ("ca8550e4646a8bb83f6068437a5de072b0ae707c7f5ea561e088a82b5351000c", 338131),
    "dfthcsos/angle_k_14.kmb": ("ff16054ac59be803b0c02738cfab47513136196bee9adcb2fea04ff20ef466cb", 345289),
    "dfthcsos/angle_k_2.kmb": ("ab9c6386e1987dcb5b04e6814edaab30c0434c608b30bb83bc88caa4bc0ef64c", 417879),
    "dfthcsos/angle_k_3.kmb": ("bf8fb9f7dbcbc682ad9e86e9eb91ca2d44f552da59fae18228af7c0be33d19e0", 414029),
    "dfthcsos/angle_k_4.kmb": ("2ba4e3506d6c4e94db557d0a2b2e195c3da013fc4d1fbd61fcf7ca17fa911d82", 350845),
    "dfthcsos/angle_k_5.kmb": ("67863645d9fb73ccd1a33483eb3492338881a7e9d9f86715bf02c51237bf97be", 354181),
    "dfthcsos/angle_k_6.kmb": ("2d8bfdbbf9093109542626812754e76c6b275e4bd521542876089acf2f8171e2", 347998),
    "dfthcsos/angle_k_7.kmb": ("231b5b87c73900bd3f04c133d5e5747ad47a2355178ac59056eb0fec6c5b1ba7", 350619),
    "dfthcsos/angle_k_8.kmb": ("6a5bb3ec2b567f918362cad7b0978fba6668e0da4a107910ad89538ab3683040", 338480),
    "dfthcsos/angle_k_9.kmb": ("73c23cdca9cab4447d8a8bbfc1e31254c06f6f7510a3b0fcf0d69c624b48b75a", 351945),
    "dfthcsos/submission.npz": ("b3c7c5166857fb886fe4b725b5aaf572cc7842792cb2af7c38ba76fb2064b78f", 1847940),
    "dqi.kmb": ("821bf8d157c03c3e868a0099b0ab1438cfba664ab1bc6fec3210654099b672a3", 455584321),
    "invsqrt.kmb": ("a4d46b173ade79975f04bb33dbb93816df7559be0f9b5cfe9ea4a9b44aa09469", 198617),
}

ANCHOR = "qcc-release-v120"
SNAPSHOT_DATASET = "badboyhalo1801/qcc-release-v120"

DFT_LEG = '''
# --- 4b. dfthcsos official verifier (in-kernel, tree dir) --------------------
dft_verify = None
for r, dirs, fs in os.walk(ROOT):
    if os.path.basename(r) == "dfthcsos" and "verify.py" in fs:
        dft_verify = Path(r) / "verify.py"
if dft_verify is not None:
    try:
        dft_dir = OUT / "dfthcsos_tree"
        dft_dir.mkdir(parents=True, exist_ok=True)
        for k in range(15):
            shutil.copyfile(local_path(f"dfthcsos/angle_k_{k}.kmb"), dft_dir / f"angle_k_{k}.kmb")
        shutil.copyfile(local_path("dfthcsos/submission.npz"), dft_dir / "submission.npz")
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
    receipt["dfthcsos_in_kernel"] = {"error": "verifiers/dfthcsos/verify.py not mounted"}
'''


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="/tmp/opencode/kernel_moat")
    a = ap.parse_args()
    d = Path(a.dir)
    nb_path = d / "moat-lab.ipynb"
    nb = json.loads(nb_path.read_text())
    cell = nb["cells"][0]
    src = "".join(cell["source"])

    # 1. replace the SHA_TABLE
    new_table = "SHA_TABLE = {\n" + "".join(
        f'    "{k}": ("{v[0]}", {v[1]}),\n' for k, v in sorted(SHA_TABLE.items())) + "}"
    src2, n = re.subn(r"SHA_TABLE = \{.*?\n\}", new_table, src, count=1, flags=re.S)
    assert n == 1, "SHA_TABLE block not found"
    src = src2

    # 2. discovery anchor
    src = src.replace('if "qcc-release-v119g" in d.as_posix():', f'if "{ANCHOR}" in d.as_posix():')

    # 3. imports for the dfthcsos leg
    src = src.replace("import io, os, sys, json, time, hashlib, subprocess, glob",
                      "import io, os, sys, json, time, hashlib, subprocess, glob, shutil")

    # 4. insert the dfthcsos in-kernel leg before the GM math section
    marker = "# --- 5. GM math"
    assert marker in src
    src = src.replace(marker, DFT_LEG.strip() + "\n\n" + marker)

    # 5. labels
    src = src.replace("V107_RECEIPT.json", "V120_RECEIPT.json")
    src = src.replace("V107-RECEIPT-PASS", "V120-RECEIPT-PASS")
    src = src.replace('"dqi-v107"', '"dqi-v120"')
    src = src.replace('"dfth-v107"', '"dfth-v120"')
    src = src.replace("# 🧱 moat-lab — it18: V107 RELEASE RECEIPT (adoption gate)",
                      "# 🧱 moat-lab — v120 RELEASE RECEIPT (adoption gate, tree identity + official-grade dqi)")
    src = src.replace("rat[\"dfthcsos\"] = 11.39179  # owner-anchor: heliosli 25.29380 @16:52 w/ these files",
                      "rat[\"dfthcsos\"] = 11.379646  # local official-verifier receipt for the v120 tree")

    cell["source"] = src.splitlines(keepends=True)

    # 6. kernel metadata: add the snapshot dataset
    meta_path = d / "kernel-metadata.json"
    meta = json.loads(meta_path.read_text())
    srcs = meta.get("dataset_sources", [])
    if SNAPSHOT_DATASET not in srcs:
        srcs.append(SNAPSHOT_DATASET)
    meta["dataset_sources"] = srcs
    meta_path.write_text(json.dumps(meta, indent=1) + "\n")

    nb_path.write_text(json.dumps(nb, indent=1) + "\n")

    # 7. pre-push gate: JSON parses and every code cell passes ast.parse
    nb2 = json.loads(nb_path.read_text())
    bad = []
    for i, c in enumerate(nb2["cells"]):
        if c.get("cell_type") != "code":
            continue
        try:
            ast.parse("".join(c["source"]))
        except SyntaxError as e:
            bad.append((i, e.msg, str(e)))
    if bad:
        raise SystemExit(f"notebook syntax FAIL: {bad}")
    print("moat-lab notebook rebuilt for", ANCHOR, "- JSON + ast.parse gate PASS")
    print("dataset_sources:", meta["dataset_sources"])


if __name__ == "__main__":
    main()
