#!/usr/bin/env python3
"""loader_check: local emulation of the chemistry (dfthcsos) loader contract, simulated with kmsim.

It mirrors what the official chemistry scorer's word recovery (`recover_words_from_circuits`) needs from a family
of angle loaders, without kickmix:
  * every circuit keeps the selection register unchanged, leaves the workspace clean (no reset of a |1>, every
    qubit outside selection and word registers back to 0) and does not flip the phase;
  * repeated shots agree;
  * run forward from all-zero words, loader k turns block k-1 into block k; run in reverse order it restores
    block k-1 and finally clears the words;
  * the padding words after the angle words stay 0.
It prints the mean Toffoli count per circuit, (forward + reverse) / 2, and the qubit count of each loader.

    python loader_check.py DIR [--ref words.npy] [--save words.npy] [--shots 4]

DIR holds angle_k_<k>.kmx (or .kmx.gz), k = 0..K-1, for example a folder made by atlas_family.py. The defaults
(--num-vectors 1220 = 76 + 8 x 143, --num-angles 75) describe the common family layout (R = 8 rotations of
B = 143); pass the values of your family when it differs. A PASS here is a local check, not an official score.

Licence: Apache-2.0.
"""
import argparse
import glob
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kmsim  # noqa: E402


def load(d):
    """[(path, ops, regs, nq, nb)] for angle_k_*.kmx[.gz] in d, ordered by k."""
    fs = glob.glob(os.path.join(d, 'angle_k_*.kmx')) + glob.glob(os.path.join(d, 'angle_k_*.kmx.gz'))
    fs = sorted(fs, key=lambda f: int(re.findall(r'angle_k_(\d+)\.kmx', f)[0]))
    out = []
    for f in fs:
        ops, regs = kmsim.parse(f)
        nq, nb = kmsim.sizes(ops, regs)
        out.append((f, ops, regs, nq, nb))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a chemistry loader family (angle_k_*.kmx) locally with kmsim.")
    ap.add_argument('dir', help='folder with angle_k_<k>.kmx or .kmx.gz files')
    ap.add_argument('--ref', help='optional .npy word table to compare with')
    ap.add_argument('--shots', type=int, default=4, help='repetitions of every selection address (default 4)')
    ap.add_argument('--save', help='save the recovered word table (.npy)')
    ap.add_argument('--seed', type=int, default=0)
    ap.add_argument('--num-vectors', type=int, default=76 + 8 * 143, help='selection addresses N + R*B (default 1220)')
    ap.add_argument('--num-angles', type=int, default=75, help='angle words per address N - 1 (default 75)')
    a = ap.parse_args(argv)
    NUM_VECTORS, NUM_ANGLES = a.num_vectors, a.num_angles
    cs = load(a.dir)
    if not cs:
        sys.exit(f'no angle_k_*.kmx files in {a.dir}')
    R = a.shots
    B = NUM_VECTORS * R
    regs0 = cs[0][2]
    nm = kmsim.register_names(cs[0][0])
    sel = regs0[nm['selection']]
    J = sum(1 for k in nm if k.startswith('word_'))
    words = [regs0[nm[f'word_{j}']] for j in range(J)]
    brot = len(words[0])
    public = set(sel) | {q for w in words for q in w}
    addr = np.tile(np.arange(NUM_VECTORS), R)
    rng = np.random.default_rng(a.seed)

    def fresh(nq, nb, batch):
        s = kmsim.Sim(None, nq, nb, B, int(rng.integers(1 << 62)))
        for i, q in enumerate(sel):
            s.q[q] = (addr >> i) & 1 == 1
        if batch is not None:
            t = np.tile(batch, (R, 1))
            for j, w in enumerate(words):
                for i, q in enumerate(w):
                    s.q[q] = (t[:, j] >> i) & 1 == 1
        return s

    def run(c, batch, label):
        f, ops, regs, nq, nb = c
        assert regs[kmsim.register_names(f)['selection']] == sel, label
        s = fresh(nq, nb, batch)
        s.ops = ops
        s.run()
        A = sum((s.q[q].astype(np.int64) << i) for i, q in enumerate(sel))
        bad = []
        if not np.array_equal(A, addr):
            bad.append('selection changed')
        ws = [q for q in range(nq) if q not in public]
        if s.q[ws].any():
            bad.append(f'dirty workspace {int(s.q[ws].any(axis=1).sum())} qubits')
        if s.bad_reset.any():
            bad.append('R on |1>')
        if (s.ph != 0).any():
            bad.append(f'phase flipped on {int((s.ph != 0).sum())} shots')
        tab = np.stack([sum((s.q[q].astype(np.int64) << i) for i, q in enumerate(w)) for w in words], 1).reshape(R, NUM_VECTORS, J)
        if (tab != tab[0]).any():
            bad.append('shots disagree')
        if bad:
            print('FAIL', label, bad)
            sys.exit(1)
        return tab[0], float(s.toff.mean())

    batches, tf, tr = [], [], []
    prev = None
    for k, c in enumerate(cs):
        b, t = run(c, prev, f'ANGLE_{k}')
        batches.append(b)
        tf.append(t)
        prev = b
    W = np.concatenate(batches, 1)
    if W[:, NUM_ANGLES:].any():
        print('FAIL padding words not zero')
        sys.exit(1)
    cur = batches[-1]
    for k in reversed(range(len(cs))):
        b, t = run(cs[k], cur, f'reverse ANGLE_{k}')
        tr.append(t)
        want = batches[k - 1] if k > 0 else np.zeros_like(b)
        if not np.array_equal(b, want):
            print('FAIL reverse', k)
            sys.exit(1)
        cur = want
    tr = tr[::-1]
    W = W[:, :NUM_ANGLES]
    if a.ref:
        ref = np.load(a.ref)
        print('words match ref:', np.array_equal(ref, W), 'mismatched entries', int((ref != W).sum()))
    if a.save:
        np.save(a.save, W)
    per = [(x + y) / 2 for x, y in zip(tf, tr)]
    for k, c in enumerate(cs):
        print(f'k{k:2d} qubits {c[3]:3d} toffoli/pass fwd {tf[k]:.2f} rev {tr[k]:.2f}')
    print('PASS total toffoli per pass', round(sum(per), 3), 'max qubits', max(c[3] for c in cs), 'J', J, 'brot', brot)
    return W


if __name__ == '__main__':
    main()
