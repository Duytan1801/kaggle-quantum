#!/usr/bin/env python3
"""assemble_v129.py — build the v129 tree snapshot dataset + verify zip.

v129 = the best measured public file of each task (2026-11-17 05:10 UTC):

  invsqrt.kmb            0af21cb8   maoxin123, 44q   cost 74,797.36535717871
                         (local official verifier PASS; the two fresh 44q
                          candidates a0015c5b / 8b410e77 measured 75,038.57 and
                          75,038.13 -> both worse, 0af21cb8 stays)
  dqi.kmb                575b043f   Grant Prater, "the later file": dqi 61c8348d
                         with four more products held on idle wires, each proven
                         before it was taken
                         890q, 367,989 static Toffoli-likes, T_mean 367,116.0572
                         official @102,400: 346,409,762,292.7187, 0 value errors,
                         0 phase errors, repetition factor 1.1912604648115832
  dfthcsos/submission.npz  a73b25d2  maoxin123, the public 906fa220-word table
                         with a corank-2 reduced-gradient weight refit
                         cost 294,643,137.7335714 (lambda_eff 46.92171681802858,
                         T 14,706, Q 427; local official verifier PASS)
  dfthcsos/angle_k_0..14.kmb  NEW 4,022-Toffoli set (maoxin123)

Projected: r_inv 27.765339 x r_dqi 70.542599 x r_dft 11.388690788 -> GM 28.150932

A sweep of 57 public chemistry sets (work/tools/sweep_chem_sets.py) and every
public 44q invsqrt in the harvested portfolios confirms these three files are the
best available; the DQI is the best of the 890-qubit line by mean Toffolis.
"""
import hashlib
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path('/tmp/opencode/v129')
SRC125 = pathlib.Path('/tmp/opencode/adopt/v125')
SRC127 = pathlib.Path('/tmp/opencode/adopt/v127')
SRC129 = pathlib.Path('/tmp/opencode/adopt/v129')
tree = ROOT / 'tree'
ds = ROOT / 'ds'
sub = ROOT / 'sub'
for d in (tree, ds, sub):
    d.mkdir(parents=True, exist_ok=True)

files = ['invsqrt.kmb', 'dqi.kmb'] + [f'dfthcsos/angle_k_{k}.kmb' for k in range(15)] + ['dfthcsos/submission.npz']

WANT = {
    'invsqrt.kmb': '0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b',
    'dqi.kmb': '575b043f4fee91a0fc3a9fd6fc1e9290e7b2a0669cae79886be2bf999f7ec155',
    'dfthcsos/submission.npz': 'a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3',
}

# 1. stage the tree
for f in files:
    if f == 'invsqrt.kmb':
        src = SRC125 / f
    elif f == 'dqi.kmb':
        src = SRC129 / f
    else:
        src = SRC127 / f
    assert src.exists(), src
    b = src.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    if f in WANT:
        assert h == WANT[f], f'{f}: {h} != published {WANT[f]}'
    dst = tree / f
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)
    (sub / f).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, sub / f)

# 2. sha table (the static receipt the in-kernel gate is built from)
table = {}
for f in files:
    b = (tree / f).read_bytes()
    table[f] = [hashlib.sha256(b).hexdigest(), len(b)]
tbl_path = pathlib.Path('/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v129.txt')
tbl_path.write_text(json.dumps(table, indent=1) + '\n')
print('sha table:', tbl_path, len(table), 'files')

# 3. dataset payload (flat names)
for f in files:
    (ds / f.replace('/', '__')).write_bytes((tree / f).read_bytes())

man = {'portfolio': 'v129_best_measured_public_mix_dqi575b', 'salt': 'moat-adoption', 'files': [
    {'file': f, 'sha256': table[f][0], 'bytes': table[f][1]} for f in files]}
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v129',
    'id': 'badboyhalo1801/qcc-release-v129',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v129 tree snapshot for the moat-lab gate',
    'description': (
        'Our assembled tree = the best MEASURED public file of each task: invsqrt 0af21cb8 '
        '(maoxin123, 44q, cost 74,797.37); DQI 575b043f (Grant Prater, dataset '
        'vqcc-dqi-61c8348d-merged-closings: his later file, dqi 61c8348d with four more products '
        'held on idle wires, each proven before it was taken; 890q, 367,989 static Toffoli-likes, '
        'mean 367,116.06; official verifier @102,400 shots 346,409,762,292.72 with 0 value and 0 '
        'phase errors); chemistry weights a73b25d2 (maoxin123, public 906fa220-word table with a '
        'corank-2 reduced-gradient weight refit, lambda_eff 46.92171682, cost 294,643,137.73) on his '
        '15 loaders at 4,022 Toffolis per pass. NOTICE chain: see CREDITS.md (Apache-2.0 Section 4d) '
        '- Syed Asad Ali, Lera (marculera), Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, '
        'Areeb Ali, Hayato Hikawa, Ali Haydar Ozdag, maoxin123, boristown, James Barlow, drpatrickchan, '
        'Balram Srinivasan, Grant Prater, Atakan Aldemir, Akmal Xodarev (busyaprime), prvsiyan.'),
}, indent=1) + '\n')

(ds / 'CREDITS.md').write_text("""
---

# v129 addendum (assembled by badboyhalo1801)

v129 is the **best measured public file of each task** (17 November 2026), each one pinned by
SHA-256 and verified with the competition's own verifiers.

| file | sha12 | author | measured cost |
|------|-------|--------|---------------|
| `invsqrt.kmb` | `0af21cb8` | maoxin123, `qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` | 74,797.36535717871 (44q, official local verifier PASS) |
| `dqi.kmb` | `575b043f` | Grant Prater, dataset `grantprater/vqcc-dqi-61c8348d-merged-closings`: his later file, `dqi 61c8348d` with **four more products held on idle wires**, each proven before it was taken | 346,409,762,292.7187 (890q, 367,989 static Toffoli-likes, mean 367,116.06; official verifier @102,400 shots, 0 value / 0 phase errors, repetition factor 1.1912604648115832) |
| `dfthcsos/submission.npz` | `a73b25d2` | maoxin123, `qcc-28-14-4-022-toffoli-chemistry-loaders`: the public `906fa220`-word table with a corank-2 reduced-gradient weight refit | 294,643,137.7335714 (lambda_eff 46.92171681802858, T 14,706, Q 427, official local verifier PASS) |
| `dfthcsos/angle_k_0..14.kmb` | 15 new files | maoxin123: 4,022-Toffoli loaders (was 4,025), CNOT layers compressed by ~64% | -6 Toffolis per pass |

A sweep of every public chemistry set we could harvest (57 sets, `work/tools/sweep_chem_sets.py`)
and every public 44-qubit invsqrt confirms these are the best of the public pool; the DQI is the
best of the 890-qubit line by mean Toffolis.

Provenance of every byte (all public, all SHA-256 pinned):

* `dqi.kmb` `575b043f` - Grant Prater, dataset `grantprater/vqcc-dqi-61c8348d-merged-closings`,
  file `dqi_575b043f.kmb.xz` (decompressed).
* `dfthcsos/submission.npz` `a73b25d2` and the 15 loaders - maoxin123, kernel output
  `submission.zip` of `qcc-28-14-4-022-toffoli-chemistry-loaders`.
* `invsqrt.kmb` `0af21cb8` - maoxin123, embedded in that release and in the verified portfolios.

Credit: maoxin123, Grant Prater, boristown, Balram Srinivasan, manwithacat (James Barlow),
Atakan Aldemir, drpatrickchan, prvsiyan, Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang,
Areeb Ali, Hayato Hikawa, Ali Haydar Ozdag, Lera (marculera), Syed Asad Ali, busyaprime (Akmal
Xodarev).  The NOTICE chain of v123-v128 travels with this dataset (Apache-2.0 Section 4d).
""")

# 4. zip — Kaggle requires the uploaded file to be named submission.zip
out = ROOT / 'submission.zip'
if out.exists():
    out.unlink()
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(sub / f, f)
h = hashlib.sha256(out.read_bytes()).hexdigest()
print('zip:', out, out.stat().st_size, 'sha256', h)

z = zipfile.ZipFile(out)
ok = all(hashlib.sha256(z.read(f)).hexdigest() == table[f][0] for f in files)
print('zip entries:', len(z.namelist()), 'all match:', ok)
print('ds files:', len(list(ds.iterdir())))
assert ok
