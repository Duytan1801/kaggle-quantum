#!/usr/bin/env python3
"""assemble_v126.py — build the v126 tree snapshot dataset + verify zip.

v126 = v125 with ONE changed file: the DQI decoder

  dqi.kmb   66b4f18b -> 61c8348d   Grant Prater's "merged patches + closings at all 49"
                                  (boristown d54d3387 patches spliced into Balram
                                  Srinivasan's GF(2^24) closings 66b4f18b, plus 49
                                  measured uncomputations and the 8 closings an exact
                                  matcher does not match)

  890 qubits | 367,993 static Toffoli-likes (was 368,750) | 57,520,809 ops (was 57,666,786)
  author's claimed cost on a draw with no failed shot: ~346,413,400,000
  (x0.99794 of the public 66b4f18b) -> projected GM 28.147 (v125: 28.127697)

Unchanged from v125:
  invsqrt.kmb            0af21cb8  (maoxin123, 44q, cost 74,797.36535717871)
  dfthcsos/submission.npz 703843d3 (Atakan Aldemir, cost 294,762,512.8596263)
  dfthcsos/angle_k_0..14.kmb   (marculera's stack-4028 loaders)
"""
import hashlib
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path('/tmp/opencode/v126')
SRC125 = pathlib.Path('/tmp/opencode/adopt/v125')
SRC126 = pathlib.Path('/tmp/opencode/adopt/v126')
tree = ROOT / 'tree'
ds = ROOT / 'ds'
sub = ROOT / 'sub'
for d in (tree, ds, sub):
    d.mkdir(parents=True, exist_ok=True)

files = ['invsqrt.kmb', 'dqi.kmb'] + [f'dfthcsos/angle_k_{k}.kmb' for k in range(15)] + ['dfthcsos/submission.npz']

WANT = {
    'invsqrt.kmb': '0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b',
    'dqi.kmb': '61c8348d6e85bb0259c4b89f14be9a2834c77bf8a680cf79959bf5e1089cf5de',
    'dfthcsos/submission.npz': '703843d35a722f07b7f833b3a6565c54f00ec5ce4e692f7192593c79728f8ce9',
}

# 1. stage the tree
for f in files:
    src = (SRC126 / f) if f == 'dqi.kmb' else (SRC125 / f)
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
tbl_path = pathlib.Path('/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v126.txt')
tbl_path.write_text(json.dumps(table, indent=1) + '\n')
print('sha table:', tbl_path, len(table), 'files')

# 3. dataset payload (flat names)
for f in files:
    (ds / f.replace('/', '__')).write_bytes((tree / f).read_bytes())

man = {'portfolio': 'v126_public_frontier_plus_grantprater_dqi', 'salt': 'moat-adoption', 'files': [
    {'file': f, 'sha256': table[f][0], 'bytes': table[f][1]} for f in files]}
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v126',
    'id': 'badboyhalo1801/qcc-release-v126',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v126 tree snapshot for the moat-lab gate',
    'description': (
        'Our assembled tree: the public 28.1277 best-per-task portfolio with the DQI replaced by '
        'Grant Prater\'s merged-patch decoder 61c8348d (890q, 367,993 static Toffoli-likes vs 368,750; '
        'the two public patch sets d54d3387 and 66b4f18b spliced, the cheaper closing carried to all 49 '
        'sites, 49 measured uncomputations). invsqrt 0af21cb8 (maoxin123, 44q, cost 74,797.37) and '
        'chemistry weights 703843d3 (Atakan Aldemir, cost 294,762,512.86) on Lera\'s (marculera) '
        'coded-word table and 15 unchanged loaders. NOTICE chain: see CREDITS.md '
        '(Apache-2.0 Section 4d) - Syed Asad Ali, Lera (marculera), Asterios Panoras, Ertugrul Ozer, '
        'Jeff Emerson, Leo Tang, Areeb Ali, Hayato Hikawa, Ali Haydar Ozdag, maoxin123, boristown, '
        'James Barlow, drpatrickchan, Balram Srinivasan, Grant Prater, Atakan Aldemir, '
        'Akmal Xodarev (busyaprime).'),
}, indent=1) + '\n')

(ds / 'CREDITS.md').write_text("""
---

# v126 addendum (assembled by badboyhalo1801)

v126 is the **public best-per-task portfolio of 16 November 2026 19:00 UTC** with **one** file
changed against v125: the DQI decoder.

| file | v125 | v126 | author | note |
|------|------|------|--------|------|
| `dqi.kmb` | `66b4f18b` | `61c8348d` | Grant Prater (`vqcc-dqi-merged-patches-closings-at-all-49`) | boristown `d54d3387` patches spliced into Balram Srinivasan's GF(2^24) closings; the cheaper closing carried to all 49 sites; 49 measured uncomputations; 890 qubits, 367,993 static Toffoli-likes (was 368,750) |

Unchanged from v125:

* `invsqrt.kmb` `0af21cb8` - maoxin123 (`qcc-v27-a-44-qubit-invsqrt-on-the-28-09-frontier`), 44 qubits.
* `dfthcsos/submission.npz` `703843d3` - Atakan Aldemir (`qcc-terminal-readout-and-phase-folds`).
* `dfthcsos/angle_k_0..14.kmb` - Lera (marculera), dataset `marculera/dfthc-c44-build`, Apache-2.0.

Provenance of every byte (all public, all SHA-256 pinned):

* `dqi.kmb` `61c8348d` - Grant Prater, from his public kernel output; rebuilt there from the two
  public parents (boristown `d54d3387`, Balram Srinivasan `66b4f18b`) and checked with the
  competition's own verifier.
* `invsqrt.kmb` `0af21cb8` - embedded in maoxin123's kernel notebook and shipped in the
  `submission.zip` of the verified public portfolios.
* `dfthcsos/submission.npz` `703843d3` - Atakan Aldemir's refit of Lera's weights.

Credit: Grant Prater, boristown, Balram Srinivasan, maoxin123, Atakan Aldemir, Lera (marculera),
Syed Asad Ali, hayatohikawa, busyaprime (Akmal Xodarev), Asterios Panoras, Ertugrul Ozer,
Jeff Emerson, Leo Tang, Areeb Ali, Hayato Hikawa, Ali Haydar Ozdag, James Barlow, drpatrickchan.
The NOTICE chain of v123-v125 travels with this dataset (Apache-2.0 Section 4d).
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
