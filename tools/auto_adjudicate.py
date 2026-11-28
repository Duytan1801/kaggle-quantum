#!/usr/bin/env python3
"""auto_adjudicate.py — adjudicate public-release queue rows BY MEASUREMENT.

For each ref in the queue (or a given list), it:
  * pulls the kernel / downloads the dataset,
  * finds any complete 18-file submission tree inside,
  * compares it member-by-member against our current SHA table,
  * measures any candidate leg it can (official verifier where affordable,
    static proxies otherwise),
  * writes a verdict into work/harvest/ADOPTED.tsv and removes the row from
    work/harvest/PENDING.tsv — ALWAYS through work/tools/harvest_queue.py.

The verdict is chosen from the measurements, never from the title:
  adopted            a leg beats ours and the tree is complete (18 files)
  dominated          measured, and no leg beats ours
  research-ledger    no circuit candidate, but the release carries usable
                     public research (methods, negative results, generators)
  out-of-scope       the release is about a different competition
  no-candidate       about this competition, ships no circuit candidate
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import zipfile

import numpy as np

ROOT = pathlib.Path('/home/bandoc/Downloads/opencode')
KAGGLE = str(ROOT / 'qaenv/bin/kaggle')
WORK = pathlib.Path('/tmp/opencode/autoadj')
PENDING = ROOT / 'work/harvest/PENDING.tsv'
ADOPTED = ROOT / 'work/harvest/ADOPTED.tsv'
TABLE = json.loads((ROOT / 'work/sha_tables/sha_table_v149.txt').read_text())['files']

# our current per-leg scores (the bar a candidate must beat)
OUR = {'invsqrt': 60927.57739905387, 'dqi': 309694874626.0435, 'dfthcsos': 250157973.2614051}
GM0 = 33.21179
# A leg improvement is only worth a submission slot if it moves the geometric
# mean by more than the public salt noise band (|residual| <= 5e-5 GM).  We
# demand 20x that: a tree that beats us by 5e-6 GM is a tie, and spending
# one of the 5 daily submissions on it would be strictly worse than keeping
# the slot for a real gain.
MIN_GM_GAIN = 1.0e-3


def leg_gain(new_cost, old_cost):
    """dGM of replacing one leg's cost by new_cost (lower is better)."""
    if not (new_cost > 0 and old_cost > 0):
        return 0.0
    return GM0 * (1.0 - (new_cost / old_cost) ** (1.0 / 3.0))
OUR_Q = {'invsqrt': 37, 'dqi': 900, 'dfthcsos': 405}
OUR_T = {'invsqrt': 1406.311400272666, 'dqi': 318962.0, 'dfthcsos': 13166.0}

# QCC-relevant tokens: a release whose text mentions any of these is about us
QCC_TOKENS = ['verifiable-quantum-circuit', 'vqcc', 'qcc-', 'qcc_', 'dfthcsos', 'angle_k',
              'google-quantum-ai-verifiable', 'kickmix', 'qcc']


def run(cmd, timeout=3600):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, '', 'timeout'


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_pending():
    rows = []
    for line in PENDING.read_text().splitlines():
        if line.strip():
            rows.append(line.split('\t'))
    return rows


def pending_refs():
    """-> [(kind, bare_ref)] for every queued release.

    The queue's first column says whether the release is a kernel or a
    dataset.  Getting this wrong makes `kaggle datasets download` fail on a
    kernel slug, so the kind must be carried through.

    The rows are ordered by the score advertised in the title (highest
    first), so the queue's most valuable candidates are adjudicated before
    the generic ones.
    """
    out = []
    for r in read_pending():
        if len(r) < 2:
            continue
        kind = r[0] if r[0] in ('kernel', 'dataset') else 'dataset'
        title = r[3] if len(r) > 3 else ''
        out.append((kind, r[1], title))
    scored = []
    for kind, ref, title in out:
        m = re.search(r'\b(\d{2})\.(\d{3,5})\b', title or '')
        s = float(f'{m.group(1)}.{m.group(2)}') if m else 0.0
        scored.append((-s, kind, ref))
    scored.sort()
    return [(k, r) for _, k, r in scored]


def harvest_done(ref, verdict, note):
    """the ONLY way a row leaves the queue"""
    cmd = [str(ROOT / 'work/toolchain/venv/bin/python'), str(ROOT / 'work/tools/harvest_queue.py'),
           'done', ref, verdict, note]
    rc, out, err = run(' '.join(f'"{c}"' for c in cmd))
    print(f'  [{verdict}] {ref}: {note[:150]}')
    if rc != 0:
        print('    harvest_queue FAILED:', out[-200:], err[-200:])
    return rc == 0


# ------------------------------------------------------------------ metrics
def kmb_toffoli(path):
    """static Toffoli-like count of a .kmb, via the local parser"""
    sys.path.insert(0, str(ROOT / 'work/run_moat/decode_it15'))
    import kmbparse as K
    d = K.parse_full(str(path))
    ops = np.array(d['ops'], dtype=np.uint8)
    base = ops & 127
    tof = int(((base == 0x30) | (base == 0x31) | (base == 0x32)).sum())
    q = int.from_bytes(d['head'][:4][20:24], 'little') if 'head' in d else None
    return tof, q


def dqi_static(path):
    """Q, static Toffolis, conditional Toffolis of a DQI .kmb"""
    with open(path, 'rb') as fh:
        head = fh.read(32)
    nq = int.from_bytes(head[20:24], 'little')
    rc, out, err = run(f'"{ROOT}/work/toolchain/venv/bin/python" "{ROOT}/work/tools/dqi_static_scan.py" '
                       f'"{path}"', timeout=1800)
    tof = cond = None
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 5 and p[1].isdigit():
            tof, cond = int(p[2]), int(p[3])
    return nq, tof, cond


def verify_dfthcsos(d):
    rc, out, err = run(
        f'cd "{ROOT}" && export PYTHONPATH=$PWD/work/toolchain/kickmix && '
        f'bash harness/run_capped.sh 3G work/toolchain/venv/bin/python '
        f'work/toolchain/verifiers/dfthcsos/verify.py "{d}" --shots-per-address 1', timeout=2400)
    txt = out + err
    i, j = txt.find('{'), txt.rfind('}')
    if i < 0 or j < 0:
        return None
    try:
        v = json.loads(txt[i:j + 1])
    except Exception:
        return None
    return v if v.get('status') == 'PASS' else None


def verify_invsqrt(path):
    rc, out, err = run(
        f'cd "{ROOT}" && export PYTHONPATH=$PWD/work/toolchain/kickmix && '
        f'bash harness/run_capped.sh 3G work/toolchain/venv/bin/python '
        # 1 shot per x: the SCORE (Q x T_eq) is exact and shot-independent;
        # the 200M-shot default costs ~14 min per candidate and the queue has
        # ~250 rows.  A candidate that matters is re-verified in full at the
        # adoption gate.
        f'work/toolchain/verifiers/invsqrt/verify_submission_invsqrt.py "{path}" '
        f'--shots-per-x 1', timeout=3600)
    txt = out + err
    i, j = txt.find('{'), txt.rfind('}')
    if i < 0 or j < 0:
        return None
    try:
        v = json.loads(txt[i:j + 1])
    except Exception:
        return None
    return v if v.get('status') == 'PASS' else None


# -------------------------------------------------------------------- trees
def find_trees(root):
    """find submission trees: a dir or zip with invsqrt.kmb + dqi.kmb + dfthcsos/"""
    out = []
    for zp in root.rglob('*.zip'):
        try:
            with zipfile.ZipFile(zp) as z:
                names = z.namelist()
        except Exception:
            continue
        if any(n.endswith('invsqrt.kmb') for n in names) and any(n.endswith('dqi.kmb') for n in names):
            out.append(('zip', zp))
    for d in root.rglob('*'):
        if d.is_dir() and (d / 'invsqrt.kmb').exists() and (d / 'dqi.kmb').exists():
            out.append(('dir', d))
    return out


def tree_members(kind, path):
    """-> {member name: sha256 hex}  (STREAMED -- a DQI member is 700 MB)"""
    out = {}
    if kind == 'zip':
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith('/')]
            # strip a single common top-level directory ("submission/..." ->
            # "...") so the members line up with our 18-file table
            tops = {n.split('/', 1)[0] for n in names if '/' in n}
            prefix = ''
            if len(tops) == 1 and all(n.startswith(next(iter(tops)) + '/') for n in names):
                prefix = next(iter(tops)) + '/'
            for n in names:
                h = hashlib.sha256()
                with z.open(n) as fh:
                    for b in iter(lambda: fh.read(1 << 20), b''):
                        h.update(b)
                out[n[len(prefix):]] = h.hexdigest()
        return out
    for p in path.rglob('*'):
        if p.is_file():
            out[str(p.relative_to(path))] = sha256(p)
    return out


def extract_members(kind, path, dest, wanted):
    """extract only the members we actually verify (never the 700 MB DQI)"""
    got = []
    dest.mkdir(parents=True, exist_ok=True)
    if kind == 'zip':
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if not n.endswith('/')]
            tops = {n.split('/', 1)[0] for n in names if '/' in n}
            prefix = ''
            if len(tops) == 1 and all(n.startswith(next(iter(tops)) + '/') for n in names):
                prefix = next(iter(tops)) + '/'
            for n in names:
                rel = n[len(prefix):]
                if rel not in wanted:
                    continue
                d = dest / rel
                d.parent.mkdir(parents=True, exist_ok=True)
                with z.open(n) as fh, open(d, 'wb') as out:
                    for b in iter(lambda: fh.read(1 << 20), b''):
                        out.write(b)
                got.append(rel)
        return got
    for rel in wanted:
        p = path / rel
        if p.is_file():
            d = dest / rel
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, d)
            got.append(rel)
    return got


def compare(theirs):
    """-> (n_ours, n_theirs, changed, extra) against our 18-file table"""
    ours = {k: v[0] for k, v in TABLE.items()}
    common = set(ours) & set(theirs)
    changed = sorted(k for k in common if ours[k] != theirs[k])
    extra = sorted(set(theirs) - set(ours))
    return len(common), len(theirs), changed, extra


def dqi_receipt(target):
    """Look for a DQI score in the release's OWN receipt / log files.

    The DQI leg cannot be verified locally (it exceeds the 3 GB cage), so a
    release's own official receipt is the only evidence.  A release whose
    receipt says a better DQI than ours is a candidate even when its
    chemistry and invsqrt are worse -- the three legs are independent.
    """
    best = None
    for p in list(target.rglob('*.json')) + list(target.rglob('*.txt')) + list(target.rglob('*.log')):
        try:
            if p.stat().st_size > 40_000_000:
                continue
            blob = p.read_text(errors='ignore')
        except Exception:
            continue
        if 'dqi' not in blob.lower():
            continue
        try:
            d = json.loads(blob)
        except Exception:
            d = None
        cands = []

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(k, str) and 'dqi' in k.lower() and isinstance(v, (int, float)):
                        cands.append(float(v))
                    if isinstance(v, dict) and 'score' in v and 'dqi' in k.lower():
                        pass
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        if d is not None:
            try:
                walk(d)
            except Exception:
                pass
        # plain text: "dqi ... 305033672024.33" style
        for m in re.finditer(r'dqi[^0-9\n]{0,40}([0-9]{7,}(?:\.[0-9]+)?)', blob, re.I):
            try:
                cands.append(float(m.group(1)))
            except Exception:
                pass
        for c in cands:
            if c > 1e6 and (best is None or c < best):
                best = c
    return best


def main():
    args = sys.argv[1:]
    slice_spec = None
    if '--slice' in args:
        i = args.index('--slice')
        slice_spec = args[i + 1]
        del args[i:i + 2]
    if args:
        # CLI refs may be bare "owner/slug" (kind inferred from the queue if
        # known, else dataset) or explicit "kernel/owner/slug".
        pairs = []
        for a in args:
            if a.startswith('kernel/') or a.startswith('dataset/'):
                kind, ref = a.split('/', 1)
            else:
                kind, ref = None, a
            if kind is None:
                kind = 'dataset'
                for k, r in pending_refs():
                    if r == ref:
                        kind = k
                        break
            pairs.append((kind, ref))
    else:
        pairs = pending_refs()
    if slice_spec:
        idx, tot = (int(x) for x in slice_spec.split('/'))
        pairs = pairs[idx::tot]
        print(f'### slice {idx}/{tot}: {len(pairs)} refs')
    WORK.mkdir(parents=True, exist_ok=True)
    for kind, ref in pairs:
        name = ref.split('/')[-1]
        target = WORK / name
        print(f'=== {kind}/{ref}')
        if target.exists():
            subprocess.run(['rm', '-rf', str(target)])
        target.mkdir(parents=True, exist_ok=True)
        if kind == 'kernel':
            rc, out, err = run(f'"{KAGGLE}" kernels pull {ref} -p "{target}"', timeout=1800)
            if rc != 0:
                rc2, out2, err2 = run(f'"{KAGGLE}" kernels output {ref} -p "{target}/out" --force', timeout=3600)
                if rc2 != 0:
                    harvest_done(ref, 'no-candidate', 'kaggle pull and output both failed')
                    continue
            run(f'"{KAGGLE}" kernels output {ref} -p "{target}/out" --force', timeout=3600)
        else:
            rc, out, err = run(f'"{KAGGLE}" datasets download -d {ref} -p "{target}" --force --unzip', timeout=5400)
            if rc != 0 and not any(target.iterdir()):
                harvest_done(ref, 'no-candidate', f'dataset download failed: {(err or out)[-160:]}')
                continue

        trees = find_trees(target)
        notes = []
        best = None
        for tkind, tpath in trees:
            members = tree_members(tkind, tpath)
            n_ours, n_theirs, changed, extra = compare(members)
            notes.append(f'{tkind} {tpath.name}: {n_theirs} files, {n_ours}/18 of ours present, '
                         f'{len(changed)} changed, {len(extra)} extra')
            if n_ours == 18 and n_theirs == 18:
                # same shape: measure the legs that differ
                meas = []
                tmp = target / ('_x_' + tpath.name)
                # extract ONLY what we verify -- dqi.kmb is 700 MB and the
                # disk is finite (a full queue once filled /tmp entirely)
                wanted = {k for k in members
                          if k == 'invsqrt.kmb' or k.startswith('dfthcsos/')}
                extract_members(tkind, tpath, tmp, wanted)
                chem = tmp / 'dfthcsos'
                if chem.is_dir():
                    r = verify_dfthcsos(chem)
                    if r:
                        meas.append(f"chem PASS {r['score']:.2f} (ours {OUR['dfthcsos']:.2f})")
                        g = leg_gain(r['score'], OUR['dfthcsos'])
                        if g >= MIN_GM_GAIN:
                            best = ('adopted', f'complete tree beats chemistry by {g:+.5f} GM '
                                                f'(>= {MIN_GM_GAIN}): {r["score"]:.2f} < {OUR["dfthcsos"]:.2f}')
                    else:
                        meas.append('chem FAIL')
                iv = tmp / 'invsqrt.kmb'
                if iv.exists():
                    r = verify_invsqrt(iv)
                    if r:
                        meas.append(f"invsqrt PASS {r['score']:.4f} (ours {OUR['invsqrt']:.4f})")
                        g = leg_gain(r['score'], OUR['invsqrt'])
                        if g >= MIN_GM_GAIN:
                            best = ('adopted', f'complete tree beats invsqrt by {g:+.5f} GM '
                                                f'(>= {MIN_GM_GAIN}): {r["score"]:.4f} < {OUR["invsqrt"]:.4f}')
                    else:
                        meas.append('invsqrt FAIL')
                shutil.rmtree(tmp, ignore_errors=True)
                notes.append('  ' + '; '.join(meas))
                if best is None and meas:
                    best = ('dominated', 'complete 18-file tree, measured legs: ' + '; '.join(meas))
                # the DQI leg cannot be verified locally: use the release's
                # OWN official receipt as the only admissible evidence
                dq = dqi_receipt(target)
                if dq is not None:
                    meas.append(f"dqi (their receipt) {dq:,.2f} (ours {OUR['dqi']:,.2f})")
                    if dq < OUR['dqi']:
                        g = leg_gain(dq, OUR['dqi'])
                        if g < MIN_GM_GAIN:
                            meas.append(f'(DQI gain {g:+.6f} GM < {MIN_GM_GAIN}: tie within noise)')
                        else:
                            # second-hand evidence: the DQI leg cannot be verified
                            # locally (it exceeds the 3 GB cage), so this is a
                            # CANDIDATE for the full two-receipt gate, not an
                            # adoption.
                            best = ('dqi-candidate', f'complete tree beats DQI by {g:+.5f} GM per its own '
                                                    f'receipt: {dq:,.2f} < {OUR["dqi"]:,.2f} -- needs the full '
                                                    f'two-receipt gate (DQI cannot be verified locally)')
                    elif best is None:
                        best = ('dominated', 'complete 18-file tree, measured legs: ' + '; '.join(meas))

        # textual evidence: is it about our competition at all?
        text = ''
        for p in list(target.rglob('*.ipynb')) + list(target.rglob('*.md')) + list(target.rglob('*.txt')):
            try:
                text += p.read_text(errors='ignore')[:400000]
            except Exception:
                pass
        low = text.lower()
        about_qcc = any(t in low for t in QCC_TOKENS)

        if best is None:
            if not about_qcc:
                verdict, note = 'out-of-scope', 'no QCC circuit candidate; release text has no VQCC/dfthcsos/kickmix content'
            else:
                verdict, note = 'research-ledger', 'about VQCC but ships no complete 18-file tree; public research/notes harvested'
            if notes:
                note += ' | ' + ' | '.join(notes[:4])
            best = (verdict, note)
        harvest_done(ref, best[0], best[1])
        # free the disk: one DQI tree is 700 MB and the queue has ~230 rows
        shutil.rmtree(target, ignore_errors=True)


if __name__ == '__main__':
    main()
