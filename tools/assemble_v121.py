#!/usr/bin/env python3
"""assemble_v121.py — build the v121 best-of-each tree snapshot dataset + verify zip.

v121 = C8 milestone portfolio (hayatohikawa) 18 files:
  invsqrt.kmb  = syed3000 v13 44q + asteriospanoras LP-resolved angles (75,170.10)
  dqi.kmb      = syed3000 v13 890q decoder + Areeb Ali retention (est. 3.4776e11)
  dfthcsos/*   = marculera (8,143,44) table + loaders + C8 continued refit npz (294,763,813.63)
NOTICE chain (Apache-2.0 §4d) travels in the snapshot dataset (CREDITS.md + licenses/).
"""
import hashlib, json, pathlib, zipfile

ROOT = pathlib.Path('/tmp/opencode/v121')
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
man = {'portfolio': 'v121_c8_best_of_each', 'salt': 'moat-adoption', 'files': []}
for f in files:
    b = (ROOT / 'tree' / f).read_bytes()
    man['files'].append({'file': f, 'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)})
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

# 3. dataset metadata
(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v121',
    'id': 'badboyhalo1801/qcc-release-v121',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v121 best-of-each tree snapshot for the moat-lab gate',
    'description': ('Our assembled tree: syed3000 v13 44q invsqrt (LP-resolved angles by asteriospanoras), '
                    'syed3000 v13 890q DQI decoder (Areeb Ali retention), marculera (8,143,44) chemistry '
                    'table/loaders with the C8 continued refit npz (hayatohikawa packaging). '
                    'NOTICE chain: see CREDITS.md and licenses/ (Apache-2.0 Section 4d) - Syed Asad Ali, '
                    'Lera (marculera), Asterios Panoras, Ertugrul Ozer, Areeb Ali, Hayato Hikawa.'),
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
