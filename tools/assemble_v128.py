#!/usr/bin/env python3
"""assemble_v128.py — build the v128 tree snapshot dataset + verify zip.

v128 = the best measured public file of each task (2026-11-17):

  invsqrt.kmb            0af21cb8   maoxin123, 44q   cost 74,797.36535717871
                         (local official verifier PASS)
  dqi.kmb                b0983d55   manwithacat "Hedge Wizardry HW-28": Balram
                         Srinivasan's 66b4f18b with 88 Toffolis measured away in
                         the 890-qubit decoder
                         official @102,400: 347,045,216,047.3212, 0 value errors,
                         0 phase errors, repetition factor 1.1912604648115832,
                         mean Toffoli 367,789.4946
  dfthcsos/submission.npz  a73b25d2  maoxin123, the public 906fa220-word table
                         with a corank-2 reduced-gradient weight refit
                         cost 294,643,137.7335714 (lambda_eff 46.92171681802858,
                         T 14,706, Q 427; local official verifier PASS)
  dfthcsos/angle_k_0..14.kmb  NEW 4,022-Toffoli set (maoxin123)

Projected: r_inv 27.765339 x r_dqi 70.421554 x r_dft 11.388690788 -> GM 28.133740
(v125 = 28.127697).

Rejected in this cycle by the two-receipt gate (NOT submitted):
  v126  dqi 61c8348d (Grant Prater)  official 348,004,440,260.46 (1 value error)
  v127  dqi 957d6733 (manwithacat HW-29) official 348,246,849,661.48 (1 value error)
"""
import hashlib
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path('/tmp/opencode/v128')
SRC125 = pathlib.Path('/tmp/opencode/adopt/v125')
SRC127 = pathlib.Path('/tmp/opencode/adopt/v127')
SRC128 = pathlib.Path('/tmp/opencode/adopt/v128')
tree = ROOT / 'tree'
ds = ROOT / 'ds'
sub = ROOT / 'sub'
for d in (tree, ds, sub):
    d.mkdir(parents=True, exist_ok=True)

files = ['invsqrt.kmb', 'dqi.kmb'] + [f'dfthcsos/angle_k_{k}.kmb' for k in range(15)] + ['dfthcsos/submission.npz']

WANT = {
    'invsqrt.kmb': '0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b',
    'dqi.kmb': 'b0983d55f58db5b743702bf269683e30a7fe9eacccafa9607c8d930d0327eb27',
    'dfthcsos/submission.npz': 'a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3',
}

# 1. stage the tree
for f in files:
    if f == 'invsqrt.kmb':
        src = SRC125 / f
    elif f == 'dqi.kmb':
        src = SRC128 / f
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
tbl_path = pathlib.Path('/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v128.txt')
tbl_path.write_text(json.dumps(table, indent=1) + '\n')
print('sha table:', tbl_path, len(table), 'files')

# 3. dataset payload (flat names)
for f in files:
    (ds / f.replace('/', '__')).write_bytes((tree / f).read_bytes())

man = {'portfolio': 'v128_best_measured_public_mix', 'salt': 'moat-adoption', 'files': [
    {'file': f, 'sha256': table[f][0], 'bytes': table[f][1]} for f in files]}
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v128',
    'id': 'badboyhalo1801/qcc-release-v128',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v128 tree snapshot for the moat-lab gate',
    'description': (
        'Our assembled tree = the best MEASURED public file of each task: invsqrt 0af21cb8 '
        '(maoxin123, 44q, cost 74,797.37); DQI b0983d55 (manwithacat, Hedge Wizardry HW-28, '
        'Balram Srinivasan\'s 66b4f18b with 88 Toffolis measured away, official @102,400 shots '
        '347,045,216,047.32 with 0 value and 0 phase errors); chemistry weights a73b25d2 '
        '(maoxin123, public 906fa220-word table with a corank-2 reduced-gradient weight refit, '
        'lambda_eff 46.92171682, cost 294,643,137.73) on his new 15 loaders at 4,022 Toffolis '
        'per pass. NOTICE chain: see CREDITS.md (Apache-2.0 Section 4d) - Syed Asad Ali, '
        'Lera (marculera), Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, Areeb Ali, '
        'Hayato Hikawa, Ali Haydar Ozdag, maoxin123, boristown, James Barlow, drpatrickchan, '
        'Balram Srinivasan, Grant Prater, Atakan Aldemir, Akmal Xodarev (busyaprime), prvsiyan.'),
}, indent=1) + '\n')

(ds / 'CREDITS.md').write_text("""
---

# v128 addendum (assembled by badboyhalo1801)

v128 is the **best measured public file of each task** (17 November 2026), each one pinned by
SHA-256 and verified with the competition's own verifiers.

| file | sha12 | author | measured cost |
|------|-------|--------|---------------|
| `invsqrt.kmb` | `0af21cb8` | maoxin123, `qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier` | 74,797.36535717871 (44q, official local verifier PASS) |
| `dqi.kmb` | `b0983d55` | manwithacat, *VQCC Hedge Wizardry* HW-28: Balram Srinivasan's `66b4f18b` with 88 Toffolis measured away in the 890-qubit decoder | 347,045,216,047.3212 (official @102,400 shots, 0 value / 0 phase errors, rep factor 1.1912604648115832) |
| `dfthcsos/submission.npz` | `a73b25d2` | maoxin123, `qcc-28-14-4-022-toffoli-chemistry-loaders`: the public `906fa220`-word table with a corank-2 reduced-gradient weight refit | 294,643,137.7335714 (lambda_eff 46.92171681802858, T 14,706, Q 427, official local verifier PASS) |
| `dfthcsos/angle_k_0..14.kmb` | 15 new files | maoxin123: 4,022-Toffoli loaders (was 4,025), CNOT layers compressed by ~64% | -6 Toffolis per pass |

Rejected in the same cycle by the two-receipt gate (not submitted): Grant Prater's DQI
`61c8348d` (official 348,004,440,260.46, 1 value error) and manwithacat's HW-29 `957d6733`
(official 348,246,849,661.48, 1 value error).

Provenance of every byte (all public, all SHA-256 pinned):

* `dqi.kmb` `b0983d55` - manwithacat, dataset `manwithacat/vqcc-hedge-wizardry`,
  file `circuits/dqi/b0983d55f58d.kmb`.
* `dfthcsos/submission.npz` `a73b25d2` and the 15 loaders - maoxin123, kernel output
  `submission.zip` of `qcc-28-14-4-022-toffoli-chemistry-loaders`.
* `invsqrt.kmb` `0af21cb8` - maoxin123, embedded in that release and in the verified portfolios.

Credit: maoxin123, manwithacat (James Barlow), Balram Srinivasan, Atakan Aldemir, boristown,
Grant Prater, prvsiyan, Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, Areeb Ali,
Hayato Hikawa, Ali Haydar Ozdag, Lera (marculera), Syed Asad Ali, busyaprime (Akmal Xodarev),
drpatrickchan.  The NOTICE chain of v123-v127 travels with this dataset (Apache-2.0 Section 4d).
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
