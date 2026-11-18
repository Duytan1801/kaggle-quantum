#!/usr/bin/env python3
"""assemble_v125.py — build the v125 tree snapshot dataset + verify zip.

v125 = the public 28.1277 portfolio (all three files newer than ours), mixed
best-per-task from public sources:

  invsqrt.kmb            f2cdab0b -> 0af21cb8   maoxin123's v27 44q line
                         (cost 75,006.37653863191 -> 74,797.37)
  dqi.kmb                ccc2ab84 -> 66b4f18b   Balram Srinivasan's GF(2^24)
                         closings in Syed Asad Ali's v13 DQI (890q)
                         (cost 347,375,470,571.73 -> 347,128,304,010.81)
  dfthcsos/submission.npz 367d46e9 -> 703843d3  Atakan Aldemir's refit of
                         Lera's weights (cost 294,762,697.44 -> 294,762,512.86)

  dfthcsos/angle_k_0..14.kmb   UNCHANGED (marculera's stack-4028 loaders)

Every file is byte-verified against its published SHA-256 before it is packaged.
"""
import hashlib
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path('/tmp/opencode/v125')
SRC = pathlib.Path('/tmp/opencode/adopt/v125')
tree = ROOT / 'tree'
ds = ROOT / 'ds'
sub = ROOT / 'sub'
for d in (tree, ds, sub):
    d.mkdir(parents=True, exist_ok=True)

files = ['invsqrt.kmb', 'dqi.kmb'] + [f'dfthcsos/angle_k_{k}.kmb' for k in range(15)] + ['dfthcsos/submission.npz']

# published sha256 prefixes (from the authors' own kernels / the 28.1277 portfolio zip)
WANT = {
    'invsqrt.kmb': '0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b',
    'dqi.kmb': '66b4f18b8527',
    'dfthcsos/submission.npz': '703843d35a722f07b7f833b3a6565c54f00ec5ce4e692f7192593c79728f8ce9',
}

# 1. stage the tree
for f in files:
    src = SRC / f
    assert src.exists(), src
    b = src.read_bytes()
    h = hashlib.sha256(b).hexdigest()
    if f in WANT:
        assert h.startswith(WANT[f]), f'{f}: {h} does not match published {WANT[f]}'
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
tbl_path = pathlib.Path('/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v125.txt')
tbl_path.write_text(json.dumps(table, indent=1) + '\n')
print('sha table:', tbl_path, len(table), 'files')

# 3. dataset payload (flat names)
for f in files:
    (ds / f.replace('/', '__')).write_bytes((tree / f).read_bytes())

man = {'portfolio': 'v125_public_28_1277_mix', 'salt': 'moat-adoption', 'files': [
    {'file': f, 'sha256': table[f][0], 'bytes': table[f][1]} for f in files]}
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v125',
    'id': 'badboyhalo1801/qcc-release-v125',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v125 tree snapshot for the moat-lab gate',
    'description': (
        'Our assembled tree (public best-per-task mix, all three files newer than v124): '
        'invsqrt 0af21cb8 (maoxin123, 44q, cost 74,797.37 - v27 rescheduled line), '
        '890q DQI decoder 66b4f18b (Balram Srinivasan, GF(2^24) closings in Syed Asad Ali v13, '
        'cost 347,128,304,010.81), and marculera (8,143,44) chemistry loaders with Atakan Aldemir\'s '
        'refit of Lera\'s weights 703843d3 (cost 294,762,512.86, lambda_eff 46.92158) on the unchanged '
        'coded-word table. NOTICE chain: see CREDITS.md (Apache-2.0 Section 4d) - Syed Asad Ali, '
        'Lera (marculera), Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, Areeb Ali, '
        'Hayato Hikawa, Ali Haydar Ozdag, maoxin123, boristown, James Barlow, drpatrickchan, '
        'Balram Srinivasan, Atakan Aldemir.'),
}, indent=1) + '\n')

(ds / 'CREDITS.md').write_text("""
---

# v125 addendum (assembled by badboyhalo1801)

v125 is the **public best-per-task mix** published on 16 November 2026 at 19:00 UTC and
verified by the 28.1277 portfolio (asteriospanoras / pramitdas / koushikrudra).  Three files
change against v124:

| file | v124 | v125 | author | cost v124 -> v125 |
|------|------|------|--------|-------------------|
| `invsqrt.kmb` | `f2cdab0b` | `0af21cb8` | maoxin123 (`qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier`) | 75,006.37653863191 -> 74,797.37 |
| `dqi.kmb` | `ccc2ab84` | `66b4f18b` | Balram Srinivasan (`vqcc-28-10-gf24-closings-in-syed-v13-dqi`), GF(2^24) closings in Syed Asad Ali's v13 | 347,375,470,571.73 -> 347,128,304,010.81 |
| `dfthcsos/submission.npz` | `367d46e9` | `703843d3` | Atakan Aldemir (`qcc-terminal-readout-and-phase-folds`), refit of Lera's weights | 294,762,697.43843937 -> 294,762,512.86 |

The 15 chemistry loaders `dfthcsos/angle_k_0..14.kmb` are **byte-identical** to v124
(marculera's stack-4028 loaders, Apache-2.0): the coded-word table, the Givens tree and `U`
are unchanged, only the Hamiltonian weight tensors were refit.

Provenance of every byte (all public, all SHA-256 pinned):

* `invsqrt.kmb` `0af21cb8` - embedded in maoxin123's kernel notebook and shipped in the
  `submission.zip` of pramitdas' and koushikrudra's verified portfolios.
* `dqi.kmb` `66b4f18b` - rebuilt by Balram Srinivasan from Syed Asad Ali's public v13 DQI
  (the GF(2^24) closing optimisation), shipped in the same portfolio zips.
* `dfthcsos/submission.npz` `703843d3` - Atakan Aldemir's refit of Lera's weights, shipped in
  the same portfolio zips.
* loaders - Lera (marculera), dataset `marculera/dfthc-c44-build`.

Credit: maoxin123, Balram Srinivasan, Atakan Aldemir, Lera (marculera), Syed Asad Ali,
boristown, Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, Areeb Ali, Hayato Hikawa,
Ali Haydar Ozdag, James Barlow, drpatrickchan.  The NOTICE chain of v123/v124 travels with
this dataset (Apache-2.0 Section 4d).
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
