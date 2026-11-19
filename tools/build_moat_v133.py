#!/usr/bin/env python3
"""build_moat_v133.py — rebuild the moat-lab in-kernel gate for the v133 tree.

v133 = the public mix published by `ghazarosbarseghyan91/vqcc-combo-candidates`
(2026-11-19), adopted through the two-receipt gate:

  invsqrt   ecf908fec987b61a  74,383.69875786705  (our own local official run,
                                                   200,540,928 shots, PASS)
  dqi       15a4b7403356092e  345,256,821,433.9815  (byte-identical to v132's
                                                   board-clean DQI: the verifier's
                                                   seed is the CIRCUIT's sha256, so
                                                   the same bytes => the same draw)
  dfthcsos  npz 6ef06081cb9c5752 + 15 loaders
            294,642,169.5116752 (official verifier PASS, lambda_eff
            46.92156262935824)

Projected GM 28.23441 (v132: 28.23163).

Differences from build_moat_v132.py:
  * 18-file SHA_TABLE   -> sha_table_v133.txt
  * discovery anchor    -> qcc-release-v133
  * snapshot dataset    -> badboyhalo1801/qcc-release-v133
  * labels              -> V133_RECEIPT / V133-RECEIPT-PASS
  * dfthcsos fallback ratio -> the v133 chemistry ratio
  * invsqrt anchor      -> ecf908fec987b61a / 74,383.69875786705

Pre-push gate: notebook JSON parses + every code cell passes ast.parse.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

SRC_DIR = Path('/tmp/opencode/kernel_moat_v132')   # the published v132 notebook
DST_DIR = Path('/tmp/opencode/kernel_moat_v133')
SHA_TABLE = {
    k: (v[0], v[1])
    for k, v in json.loads(Path('/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v133.txt').read_text())['files'].items()
}
assert len(SHA_TABLE) == 18, f'expected 18 files in the v133 sha table, got {len(SHA_TABLE)}'

ANCHOR = 'qcc-release-v133'
SNAPSHOT_DATASET = 'badboyhalo1801/qcc-release-v133'

# v133 chemistry ratio: REF / (local official-verifier cost 294,642,169.5116752)
DFT_RATIO = '11.388728267216'

INVSQLT_ANCHOR = '''# invsqrt is anchored, not re-probed in-kernel (the official verifier needs the
# 200M-shot scale: a 5400 s in-kernel run times out with no parseable verdict).
# Anchor = our own local run of the UNCHANGED official verifier on these exact
# bytes (sha ecf908fec987b61a9aee39ceba0d9082abf7236547997aebfde9018243773be5):
#   status PASS, score 74383.69875786705, 44 qubits, 1450.9367018237792 mean
#   Toffolis, 33 rotations, rotation_eps 2.0054235961209344e-13,
#   worst_error_over_tolerance 0.9994556024791729 at x = 231,
#   verified_shots 200540928.
INVSQLT_ANCHOR = {
    "status": "PASS", "score": 74383.69875786705, "num_qubits": 44,
    "toffoli_count": 1450.9367018237792, "rotation_count": 33.0,
    "rotation_eps": 2.0054235961209344e-13,
    "worst_error_over_tolerance": 0.9994556024791729, "worst_x": 231,
    "verified_shots": 200540928,
    "circuit_sha256": "ecf908fec987b61a9aee39ceba0d9082abf7236547997aebfde9018243773be5",
}
receipt["invsqrt_anchor"] = INVSQLT_ANCHOR
'''


def main() -> None:
    DST_DIR.mkdir(parents=True, exist_ok=True)
    nb_path = DST_DIR / 'moat-lab.ipynb'
    nb = json.loads((SRC_DIR / 'moat-lab.ipynb').read_text())
    cell = nb['cells'][0]
    src = ''.join(cell['source'])

    # 1. SHA_TABLE
    new_table = 'SHA_TABLE = {\n' + ''.join(
        f'    "{k}": ("{v[0]}", {v[1]}),\n' for k, v in sorted(SHA_TABLE.items())) + '}'
    src, n = re.subn(r'SHA_TABLE = \{.*?\n\}', lambda m: new_table, src, count=1, flags=re.S)
    assert n == 1, 'SHA_TABLE block not found'

    # 2. discovery anchor
    src, n = re.subn(r'if "qcc-release-v1[0-9a-z]+" in d\.as_posix\(\):', f'if "{ANCHOR}" in d.as_posix():', src)
    assert n == 1, 'anchor pattern not found'

    # 3. invsqrt anchor (replace the whole v132 anchor block, comments included)
    src, n = re.subn(
        r'# invsqrt is anchored, not re-probed in-kernel.*?receipt\["invsqrt_anchor"\] = INVSQLT_ANCHOR\n',
        lambda m: INVSQLT_ANCHOR, src, count=1, flags=re.S)
    assert n == 1, 'INVSQLT_ANCHOR block not found'

    # 4. dfthcsos fallback ratio -> the v133 chemistry ratio
    src, n = re.subn(r'rat\["dfthcsos"\] = [0-9.]+.*',
                     f'rat["dfthcsos"] = {DFT_RATIO}  # v133 local official-verifier receipt '
                     '(chem npz 6ef06081cb9c5752 + 15 loaders, cost 294,642,169.5116752)', src, count=1)
    assert n == 1, 'dfthcsos fallback ratio not found'

    # 5. labels
    src = re.sub(r'V1\d\d_RECEIPT\.json', 'V133_RECEIPT.json', src)
    src = re.sub(r'V1\d\d-RECEIPT-PASS', 'V133-RECEIPT-PASS', src)
    src = re.sub(r'"dqi-v1\d+"', '"dqi-v133"', src)
    src = re.sub(r'"dfth-v1\d+"', '"dfth-v133"', src)
    src = re.sub(r'moat-lab — v1\d\d RELEASE RECEIPT', 'moat-lab — v133 RELEASE RECEIPT', src)
    assert 'V133_RECEIPT.json' in src, 'receipt label replacement failed'
    assert 'V133-RECEIPT-PASS' in src, 'pass label replacement failed'
    for stale in ('V121', 'V122', 'V123', 'V124', 'V125', 'V126', 'V127', 'V128', 'V129', 'V130', 'V131', 'V132'):
        assert stale not in src, f'stale label {stale} left in notebook'

    cell['source'] = src.splitlines(keepends=True)

    # 6. kernel metadata: the v133 snapshot dataset replaces v132
    meta = json.loads((SRC_DIR / 'kernel-metadata.json').read_text())
    srcs = [s for s in meta.get('dataset_sources', []) if s != 'badboyhalo1801/qcc-release-v132']
    if SNAPSHOT_DATASET not in srcs:
        srcs.append(SNAPSHOT_DATASET)
    meta['dataset_sources'] = srcs
    meta['title'] = 'moat-lab'
    (DST_DIR / 'kernel-metadata.json').write_text(json.dumps(meta, indent=1) + '\n')

    nb_path.write_text(json.dumps(nb, indent=1) + '\n')

    # 7. pre-push gate
    nb2 = json.loads(nb_path.read_text())
    bad = []
    for i, c in enumerate(nb2['cells']):
        if c.get('cell_type') != 'code':
            continue
        try:
            ast.parse(''.join(c['source']))
        except SyntaxError as e:
            bad.append((i, e.msg))
    if bad:
        raise SystemExit(f'notebook syntax FAIL: {bad}')
    src2 = ''.join(nb2['cells'][0]['source'])
    checks = {
        'anchor v133': f'if "{ANCHOR}"' in src2,
        'sha table 18': src2.count('": ("') >= 18,
        'dft leg uses paths': 'paths[f"dfthcsos/angle_k_{k}.kmb"]' in src2,
        'shas_ok guard': 'dft_verify is not None and shas_ok' in src2,
        'labels v133': 'V133_RECEIPT.json' in src2 and 'V133-RECEIPT-PASS' in src2,
        'no stale labels': all(s not in src2 for s in ('V121', 'V130', 'V131', 'V132')),
        'dft ratio v133': f'rat["dfthcsos"] = {DFT_RATIO}' in src2,
        'invsqrt anchor': 'INVSQLT_ANCHOR' in src2 and 'ecf908fec987b61a' in src2,
        'invsqrt_ok driven': 'inv_ok = (INVSQLT_ANCHOR.get("status") == "PASS")' in src2,
        'invsqrt ratio used': 'rat["invsqrt"] = ratio("invsqrt", INVSQLT_ANCHOR["score"])' in src2,
        'dataset sources v133 only': meta['dataset_sources'] == [SNAPSHOT_DATASET],
    }
    print('moat-lab rebuilt for', ANCHOR, '- JSON + ast.parse gate PASS')
    for k, v in checks.items():
        print(f'  {k}: {v}')
    assert all(checks.values())
    print('dataset_sources:', srcs)
    print('notebook:', nb_path)


if __name__ == '__main__':
    main()
