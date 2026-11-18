#!/usr/bin/env python3
"""assemble_v123.py — build the v123 tree snapshot dataset + verify zip.

v123 = maoxin123's rescheduled 44q invsqrt (f2cdab0b, cost 75,006.37)
       + the v122 dqi (ccc2ab84, "C-merge + HW-27") and chemistry (f6e12f02 npz, marculera loaders).
Predicted GM = (27.68797 x 70.35460 x 11.38407)^(1/3) = 28.09487.
NOTICE chain (Apache-2.0 §4d) travels in the snapshot dataset (CREDITS.md + licenses/).
"""
import hashlib, json, pathlib, zipfile

ROOT = pathlib.Path('/tmp/opencode/v123')
ds = ROOT / 'ds'
ds.mkdir(parents=True, exist_ok=True)
files = ['invsqrt.kmb', 'dqi.kmb'] + [f'dfthcsos/angle_k_{k}.kmb' for k in range(15)] + ['dfthcsos/submission.npz']

# 1. dataset payload: 18 files with `dfthcsos__` flat names (snapshot convention)
for f in files:
    src = ROOT / 'tree' / f
    dst = ds / f.replace('/', '__')
    if not dst.exists():
        dst.write_bytes(src.read_bytes())

# 2. manifest
man = {'portfolio': 'v123_rescheduled_invsqrt_best_of_each', 'salt': 'moat-adoption', 'files': []}
for f in files:
    b = (ROOT / 'tree' / f).read_bytes()
    man['files'].append({'file': f, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)})
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

# 3. dataset metadata
(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v123',
    'id': 'badboyhalo1801/qcc-release-v123',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v123 tree snapshot for the moat-lab gate',
    'description': ('Our assembled tree: invsqrt f2cdab0b (44q, 75,006.37 - maoxin123 rescheduled '
                    '46q generator line, 1,464.13 mean Toffoli, 33 refit rotations), '
                    '890q DQI decoder ccc2ab84 (347,375,470,571.73; syed3000 line + product retention + '
                    'HW-27/C-merge patches), marculera (8,143,44) chemistry loaders with the f6e12f02 '
                    'Stage A/B refit npz (294,762,732.98). '
                    'NOTICE chain: see CREDITS.md and licenses/ (Apache-2.0 Section 4d) - Syed Asad Ali, '
                    'Lera (marculera), Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, '
                    'Areeb Ali, Hayato Hikawa, Ali Haydar Ozdag, maoxin123, boristown, James Barlow.'),
}, indent=1) + '\n')

# 4. zip (18 entries, exact names)
out = ROOT / 'submission.zip'
with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
    for f in files:
        z.write(ROOT / 'sub' / f, f)
h = hashlib.sha256(out.read_bytes()).hexdigest()
print('zip:', out, out.stat().st_size, 'sha256', h)

# 5. verify zip contents vs the sha table
z = zipfile.ZipFile(out)
ok = all(hashlib.sha256(z.read(f)).hexdigest() == hashlib.sha256((ROOT / 'tree' / f).read_bytes()).hexdigest()
         for f in files)
print('zip entries:', len(z.namelist()), 'all match:', ok)
