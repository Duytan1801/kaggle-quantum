#!/usr/bin/env python3
"""assemble_v124.py — build the v124 tree snapshot dataset + verify zip.

v124 = v123 tree with ONE changed file: the chemistry weight table
        dfthcsos/submission.npz  f6e12f02  ->  367d46e9  (drpatrickchan's `sub1` refit)
Everything else is byte-identical to v123:
        invsqrt.kmb  f2cdab0b (44q, 75,006.37)
        dqi.kmb      ccc2ab84 (890q, 347,375,470,571.73)
        dfthcsos/angle_k_0..14.kmb  (marculera's stack-4028 loaders, unchanged)

The `sub1` refit changes ONLY the Hamiltonian weight tensors (W, H2_I); the coded
angle-word table, the tree edges and U are bit-identical to v123's, so the same 15
loaders remain valid.  Local official dfthcsos verifier:
        v123  294,762,732.97757906   lambda_eff 46.921618411
        v124  294,762,697.43843937   lambda_eff 46.921612754   (-35.539 cost units)
NOTICE chain (Apache-2.0 §4d) travels in the snapshot dataset (CREDITS.md + licenses/).
"""
import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path('/tmp/opencode/v124')
ds = ROOT / 'ds'
ds.mkdir(parents=True, exist_ok=True)
files = ['invsqrt.kmb', 'dqi.kmb'] + [f'dfthcsos/angle_k_{k}.kmb' for k in range(15)] + ['dfthcsos/submission.npz']

# 0. carry the v123 legal side-car files (NOTICE chain) over unchanged
old_ds = pathlib.Path('/tmp/opencode/v123/ds')
for name in ('licenses',):
    if (old_ds / name).exists() and not (ds / name).exists():
        shutil.copytree(old_ds / name, ds / name)

# 1. dataset payload: 18 files with `dfthcsos__` flat names (snapshot convention)
for f in files:
    src = ROOT / 'tree' / f
    dst = ds / f.replace('/', '__')
    dst.write_bytes(src.read_bytes())

# 2. manifest
man = {'portfolio': 'v124_sub1_chem_refit', 'salt': 'moat-adoption', 'files': []}
for f in files:
    b = (ROOT / 'tree' / f).read_bytes()
    man['files'].append({'file': f, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)})
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

# 3. dataset metadata
(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v124',
    'id': 'badboyhalo1801/qcc-release-v124',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v124 tree snapshot for the moat-lab gate',
    'description': ('Our assembled tree: invsqrt f2cdab0b (44q, 75,006.37 - maoxin123 rescheduled '
                    '46q generator line, 1,464.13 mean Toffoli, 33 refit rotations), '
                    '890q DQI decoder ccc2ab84 (347,375,470,571.73; syed3000 line + product retention + '
                    'HW-27/C-merge patches), marculera (8,143,44) chemistry loaders with drpatrickchan\'s '
                    '`sub1` weight refit npz (294,762,697.44, lambda_eff 46.921612754) on the unchanged '
                    'coded-word table. '
                    'NOTICE chain: see CREDITS.md and licenses/ (Apache-2.0 Section 4d) - Syed Asad Ali, '
                    'Lera (marculera), Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, '
                    'Areeb Ali, Hayato Hikawa, Ali Haydar Ozdag, maoxin123, boristown, James Barlow, '
                    'drpatrickchan.'),
}, indent=1) + '\n')

# 4. credits: carry v123's chain and append the v124 addendum
credits = (old_ds / 'CREDITS.md').read_text() if (old_ds / 'CREDITS.md').exists() else ''
addendum = """
---

# v124 addendum (assembled by badboyhalo1801)

v124 replaces **only** the chemistry weight table `dfthcsos/submission.npz`
(`f6e12f02`, 294,762,732.97757906) with **drpatrickchan's `sub1` weight refit**
(`367d46e9`, 294,762,697.43843937, lambda_eff 46.921612754), published in their Kaggle dataset
`drpatrickchan/qcc-chem-sub1-weights` (CC0) and notebook
`drpatrickchan/qcc-chem-refit-sub1-on-the-28-09-frontier`.

* The refit changes **only** the Hamiltonian weight tensors (`W`, `H2_I`).  The coded
  angle-word table (`angle_words`), the Givens tree (`tree_edges`) and `U` are bit-identical
  to the v123 package, so the 15 chemistry loaders are unchanged and remain valid.
* Verified with the competition's unmodified `verifiers/dfthcsos/verify.py`:
  PASS, error_1 = error_2 = 19.9999985 mHa, E_gap = 3.9148980015 Ha (above the 3.914898 floor),
  T = 14,712 Toffolis, Q = 427 qubits, lambda_eff = 46.921612754.
* All invsqrt and dqi files are byte-identical to v123.

Credit: drpatrickchan (chem `sub1` refit, CC0).  The rest of the NOTICE chain is unchanged and
travels with this dataset.
"""
if 'v124 addendum' not in credits:
    credits += addendum
(ds / 'CREDITS.md').write_text(credits)
if not (ds / 'README.md').exists() and (old_ds / 'README.md').exists():
    shutil.copyfile(old_ds / 'README.md', ds / 'README.md')

# 5. zip (18 entries, exact names) — Kaggle requires the uploaded file to be submission.zip
out = ROOT / 'submission.zip'
import zipfile
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(ROOT / 'sub' / f, f)
h = hashlib.sha256(out.read_bytes()).hexdigest()
print('zip:', out, out.stat().st_size, 'sha256', h)

# 6. verify zip contents vs the sha table
z = zipfile.ZipFile(out)
ok = all(hashlib.sha256(z.read(f)).hexdigest() == hashlib.sha256((ROOT / 'tree' / f).read_bytes()).hexdigest()
         for f in files)
print('zip entries:', len(z.namelist()), 'all match:', ok)
print('ds files:', len(list(ds.iterdir())))
