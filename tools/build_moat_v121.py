#!/usr/bin/env python3
"""build_moat_v121.py — rebuild the moat-lab in-kernel gate for the v121 tree.

From the v120 gate cell:
  * 18-file SHA_TABLE  -> v121 (C8 best-of-each tree)
  * discovery anchor    -> qcc-release-v121
  * local_path fix      -> flat-name fallback `dfthcsos/angle_k_0.kmb` → `dfthcsos__angle_k_0.kmb`
                           (the snapshot dataset convention that killed the v120 dfthcsos leg)
  * dfthcsos in-kernel leg uses the already-resolved paths[] instead of local_path
  * labels              -> V121_RECEIPT / V121-RECEIPT-PASS

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

SHA_TABLE = {
    "dfthcsos/angle_k_0.kmb": ("aed6aa7cde8cefae06376546c276208a667a1a402ebfe9e57cb33881868ab089", 415169),
    "dfthcsos/angle_k_1.kmb": ("72b79b56514e657650ed3258d90e7a533568ade86db407990a34bfb4380b6e60", 421737),
    "dfthcsos/angle_k_10.kmb": ("2926a709c9d0ed2824073bef29347d2beee6282e1e08aff5b982512e345f6220", 357811),
    "dfthcsos/angle_k_11.kmb": ("7aed38f94ef86b504f985dcee98ed33dd6b341114147c55d0407b88495a1015d", 354943),
    "dfthcsos/angle_k_12.kmb": ("d73ee72ed6661082acd273d3bbf4d3511330d688bec8e64e6a8d647a975b9655", 353554),
    "dfthcsos/angle_k_13.kmb": ("38b56f2fc07b7bd5a378c7d25650f62a430fe42d5595d6184d5ae930b258bec3", 353477),
    "dfthcsos/angle_k_14.kmb": ("ab06b98fc22fce8a33b591db9caf73e93d407342a6c0f3d2e2e1416dffffdfd7", 362314),
    "dfthcsos/angle_k_2.kmb": ("42ea507daa22d0464e16d8f8d8f091e684d025998a32b574fee34672414b18ad", 371346),
    "dfthcsos/angle_k_3.kmb": ("423968d4ab8219b164a27284c4b889b67a864ead9322b7703599fc839d7d8035", 368418),
    "dfthcsos/angle_k_4.kmb": ("cf7c413468b0fe51cfb7ff457b1f9ab76dc80df01dbfba87cd190c9686078d68", 356845),
    "dfthcsos/angle_k_5.kmb": ("8c8a6281407052dbc2bfaa2a90d7cc34f936b406ad83b11a3a0586f2d32f1896", 354694),
    "dfthcsos/angle_k_6.kmb": ("0ebb575aef372a33941a1a9b8e317351dda7746389ec31c1b52f40f2280ad329", 350614),
    "dfthcsos/angle_k_7.kmb": ("77c35bb2ee9c699693ee581a510b53f0c9cf4a3c3a58b02882913ca048fd09ab", 352233),
    "dfthcsos/angle_k_8.kmb": ("9c5ced81d9a7378b763603f0bdd61322369e1bc3c72628a224b0445486e48663", 357510),
    "dfthcsos/angle_k_9.kmb": ("611fe155e4e060d0cca795236b0f1abd6e41225b7bbca135cfaec8da5a4334f9", 354915),
    "dfthcsos/submission.npz": ("7e6e65d79f3528d7ec64bb22e5498edac4979dd0164b3a3cb4c67f05035133a1", 1847692),
    "dqi.kmb": ("4b350932b03931af6040c871209da62aa0ebc74cfac3e77efcb6384e027285cc", 486993377),
    "invsqrt.kmb": ("090009609ee68ca309b28950c06adb7c0640ed784f8dfbc78f1319088e8322bf", 200369),
}

ANCHOR = "qcc-release-v121"
SNAPSHOT_DATASET = "badboyhalo1801/qcc-release-v121"

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
    src2, n = re.subn(r"SHA_TABLE = \{.*?\n\}", new_table, src, count=1, flags=re.S)
    assert n == 1, "SHA_TABLE block not found"
    src = src2

    # 2. discovery anchor
    src = re.sub(r'if "qcc-release-v1[0-9a-z]+" in d\.as_posix\(\):', f'if "{ANCHOR}" in d.as_posix():', src)

    # 3. local_path flat fallback
    src3, n = re.subn(r"def local_path\(rel, stored_as=None\):.*?raise FileNotFoundError\(rel \+ \" in \" \+ ds\.as_posix\(\)\)",
                      lambda m: FLAT_FALLBACK.strip(), src, count=1, flags=re.S)
    assert n == 1, "local_path block not found"
    src = src3

    # 4. dfthcsos leg: replace the old one (its marker comment) with the fixed version
    src4, n = re.subn(r"# --- 4b\. dfthcsos official verifier.*?(?=\n# --- 5\.)",
                      lambda m: DFT_LEG.strip() + "\n", src, count=1, flags=re.S)
    assert n == 1, "old dfthcsos leg not found"
    src = src4

    # 5. labels
    src = src.replace("V120_RECEIPT.json", "V121_RECEIPT.json")
    src = src.replace("V120-RECEIPT-PASS", "V121-RECEIPT-PASS")
    src = src.replace('"dqi-v120"', '"dqi-v121"')
    src = src.replace('"dfth-v120"', '"dfth-v121"')
    src = src.replace("# 🧱 moat-lab — v120 RELEASE RECEIPT", "# 🧱 moat-lab — v121 RELEASE RECEIPT")

    cell["source"] = src.splitlines(keepends=True)

    # 6. kernel metadata: add the v121 snapshot dataset
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
        "anchor v121": 'if "qcc-release-v121"' in src2,
        "sha table 18": src2.count('": ("') >= 18,
        "flat fallback": 'rel.replace("/", "__")' in src2,
        "dft leg uses paths": 'paths[f"dfthcsos/angle_k_{k}.kmb"]' in src2,
        "shas_ok guard": "dft_verify is not None and shas_ok" in src2,
    }
    print("moat-lab rebuilt for", ANCHOR, "- JSON + ast.parse gate PASS")
    for k, v in checks.items():
        print(f"  {k}: {v}")
    assert all(checks.values())
    print("dataset_sources tail:", srcs[-3:])


if __name__ == "__main__":
    main()
