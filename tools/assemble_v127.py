#!/usr/bin/env python3
"""assemble_v127.py — build the v127 tree snapshot dataset + verify zip.

v127 = maoxin123's public "QCC 28.14" release (2026-11-17 02:16 UTC), taken as
published in his kernel's submission.zip, with our own invsqrt (identical bytes):

  invsqrt.kmb              0af21cb8  (unchanged vs v125/v126)   maoxin123, 44q
  dqi.kmb                  957d6733  <- 66b4f18b                manwithacat,
                           "Hedge Wizardry HW-29" on Atakan Aldemir's eea2d627
  dfthcsos/submission.npz  a73b25d2  <- 703843d3                maoxin123,
                           the public 906fa220-word table with a corank-2
                           reduced-gradient weight refit (lambda_eff 46.92171682)
  dfthcsos/angle_k_0..14.kmb   NEW set (15 files)             maoxin123,
                           4,022-Toffoli loaders (was 4,025), CNOT layers
                           compressed by ~64%

Measured receipts:
  invsqrt  local official verifier PASS 74,797.36535717871
  chem     local official verifier PASS 294,643,137.7335714
           (T 14,706, Q 427, lambda_eff 46.921716818, error 19.9999997 mHa,
            E_gap 3.9148980002646567)
  dqi      official in-kernel @102,400 shots -> see work/receipts/V127_RECEIPT.json
           (projected 346,654,664,786 on a clean draw -> projected GM 28.144301)

v126 (Grant Prater's 61c8348d DQI) was REJECTED by the gate: its official draw had
1 value error -> rep factor 1.19673 -> 348,004,440,260.46 (worse than v125).
"""
import hashlib
import json
import pathlib
import shutil
import zipfile

ROOT = pathlib.Path('/tmp/opencode/v127')
SRC125 = pathlib.Path('/tmp/opencode/adopt/v125')
SRC127 = pathlib.Path('/tmp/opencode/adopt/v127')
tree = ROOT / 'tree'
ds = ROOT / 'ds'
sub = ROOT / 'sub'
for d in (tree, ds, sub):
    d.mkdir(parents=True, exist_ok=True)

files = ['invsqrt.kmb', 'dqi.kmb'] + [f'dfthcsos/angle_k_{k}.kmb' for k in range(15)] + ['dfthcsos/submission.npz']

WANT = {
    'invsqrt.kmb': '0af21cb823328f6d91fbd62d6c09e48900cc5e36e343ed31681b5e87a8856b1b',
    'dqi.kmb': '957d673345413fb770f32d041174277a6f662ae0b24348a4fdcda79705bce9fb',
    'dfthcsos/submission.npz': 'a73b25d27caec65dba2b0ad6c49b34afbdb2343f4ef94f3b4ad0536dee0077f3',
}

# 1. stage the tree
for f in files:
    src = SRC125 / f if f == 'invsqrt.kmb' else SRC127 / f
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
tbl_path = pathlib.Path('/home/bandoc/Downloads/opencode/work/sha_tables/sha_table_v127.txt')
tbl_path.write_text(json.dumps(table, indent=1) + '\n')
print('sha table:', tbl_path, len(table), 'files')

# 3. dataset payload (flat names)
for f in files:
    (ds / f.replace('/', '__')).write_bytes((tree / f).read_bytes())

man = {'portfolio': 'v127_maoxin_28_14_mix', 'salt': 'moat-adoption', 'files': [
    {'file': f, 'sha256': table[f][0], 'bytes': table[f][1]} for f in files]}
(ds / 'QCC_RELEASE_MANIFEST.json').write_text(json.dumps(man, indent=1) + '\n')

(ds / 'dataset-metadata.json').write_text(json.dumps({
    'title': 'qcc-release-v127',
    'id': 'badboyhalo1801/qcc-release-v127',
    'licenses': [{'name': 'CC0-1.0'}],
    'keywords': [],
    'subtitle': 'Frozen v127 tree snapshot for the moat-lab gate',
    'description': (
        'Our assembled tree = maoxin123\'s public "QCC 28.14" release (17 Nov 2026 02:16 UTC), '
        'taken from the bytes in his kernel submission.zip. invsqrt 0af21cb8 (maoxin123, 44q, '
        'cost 74,797.37); DQI 957d6733 (manwithacat, Hedge Wizardry HW-29, 890q, on Atakan '
        'Aldemir\'s eea2d627); chemistry weights a73b25d2 (maoxin123, public 906fa220-word table '
        'with a corank-2 reduced-gradient weight refit, lambda_eff 46.92171682, cost '
        '294,643,137.73) on his new 15 loaders at 4,022 Toffolis per pass. NOTICE chain: see '
        'CREDITS.md (Apache-2.0 Section 4d) - Syed Asad Ali, Lera (marculera), Asterios Panoras, '
        'Ertugrul Ozer, Jeff Emerson, Leo Tang, Areeb Ali, Hayato Hikawa, Ali Haydar Ozdag, '
        'maoxin123, boristown, James Barlow, drpatrickchan, Balram Srinivasan, Grant Prater, '
        'Atakan Aldemir, Akmal Xodarev (busyaprime), prvsiyan.'),
}, indent=1) + '\n')

(ds / 'CREDITS.md').write_text("""
---

# v127 addendum (assembled by badboyhalo1801)

v127 is **maoxin123's public "QCC 28.14 | 4,022-Toffoli chemistry loaders" release**
(17 November 2026 02:16 UTC), taken from the exact bytes in his kernel's `submission.zip`.

| file | v125/v126 | v127 | author | cost v125 -> v127 |
|------|-----------|------|--------|-------------------|
| `invsqrt.kmb` | `0af21cb8` | `0af21cb8` (unchanged) | maoxin123 | 74,797.36535717871 (unchanged) |
| `dqi.kmb` | `66b4f18b` | `957d6733` | manwithacat, *Hedge Wizardry HW-29*, on Atakan Aldemir's `eea2d627` | 347,128,304,010.81 -> 346,654,664,786 on a clean draw |
| `dfthcsos/submission.npz` | `703843d3` | `a73b25d2` | maoxin123, the public `906fa220`-word table with a corank-2 reduced-gradient weight refit | 294,762,512.8596263 -> 294,643,137.7335714 |
| `dfthcsos/angle_k_0..14.kmb` | marculera stack-4028 | **new 4,022-Toffoli set** | maoxin123 | T 14,712 -> 14,706 |

Measured with the competition's own verifiers: invsqrt PASS 74,797.36535717871;
dfthcsos PASS 294,643,137.7335714 (lambda_eff 46.92171681802858, error_1 = error_2 =
19.9999997 mHa, E_gap 3.9148980002646567); DQI verified in-kernel at 102,400 shots
(see `V127_RECEIPT.json` in the receipt folder).

Provenance of every byte (all public, all SHA-256 pinned):

* `dqi.kmb` `957d6733` - manwithacat, `vqcc-hedge-wizardry-notebook` / Hedge Wizardry HW-29.
* `dfthcsos/submission.npz` `a73b25d2` and the 15 loaders - maoxin123, kernel output
  `submission.zip` of `qcc-28-14-4-022-toffoli-chemistry-loaders`.
* `invsqrt.kmb` `0af21cb8` - maoxin123, embedded in the same release and in the verified
  public portfolios.

Credit: maoxin123, manwithacat (James Barlow), Atakan Aldemir, boristown, Balram Srinivasan,
Grant Prater, prvsiyan, Asterios Panoras, Ertugrul Ozer, Jeff Emerson, Leo Tang, Areeb Ali,
Hayato Hikawa, Ali Haydar Ozdag, Lera (marculera), Syed Asad Ali, busyaprime (Akmal Xodarev),
James Barlow, drpatrickchan.  The NOTICE chain of v123-v126 travels with this dataset
(Apache-2.0 Section 4d).
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
