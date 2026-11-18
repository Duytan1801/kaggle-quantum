#!/usr/bin/env python3
"""assemble_v122.py — build the v122 super-SOTA tree snapshot dataset + verify zip.

v122 = ozertuu's newest verified portfolio (kernel output 2026-11-16 01:44 UTC, GM 28.09091):
  invsqrt.kmb  = 8b410e77 (44q, 1,455.25 Toff, cost 75,038.03 — jeffemerson AND-merge lineage, further cut)
  dqi.kmb      = ccc2ab84 (890q, cost 347,375,470,571.73 — "C-merge + HW-27" over syed v13 4b350932)
  dfthcsos/*   = marculera (8,143,44) loaders + f6e12f02 npz (Stage A/B round 3, cost 294,762,732.98)
NOTICE chain (Apache-2.0 §4d) travels in the snapshot dataset (CREDITS.md + licenses/).
"""
import hashlib, json, pathlib, zipfile

ROOT = pathlib.Path('/tmp/opencode/v122')
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
man = {'portfolio': 'v122_supersota_best_of_each', 'salt': 'moat-adoption', 'files': []}
for f in files:
    b = (ROOT / 'tree' / f).read_bytes()
    man['files'].append({'file': f, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)})
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

# 3. dataset metadata
(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v122',
    'id': 'badboyhalo1801/qcc-release-v122',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v122 super-SOTA tree snapshot for the moat-lab gate',
    'description': ('Our assembled tree: 44q invsqrt 8b410e77 (75,038.03; syed3000 v13 base 47b31838 + '
                    'jeffemerson AND-merge lineage cut 9339eecc, further cut to 1,455.25 Toffoli), '
                    '890q DQI decoder ccc2ab84 (347,375,470,571.73; syed3000 v13 4b350932 with C-merge + HW-27), '
                    'marculera (8,143,44) chemistry loaders with the f6e12f02 Stage A/B round-3 refit npz '
                    '(294,762,732.98). Direct public source: ozertuu kernel '
                    'vqcc-verified-portfolio-28-082-sota (output zip, 2026-11-16 01:44 UTC run, their GM 28.09091). '
                    'NOTICE chain: see CREDITS.md and licenses/ (Apache-2.0 Section 4d) - Syed Asad Ali, '
                    'Lera (marculera), Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Areeb Ali, Hayato Hikawa.'),
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
