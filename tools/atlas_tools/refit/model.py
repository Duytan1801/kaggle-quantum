"""Exact DF-THC metrics of (W, H2_I) at FIXED angle words, with analytic gradients (numpy, float64).

The formulas are the verifier's (dfthcsos.scoreinfra.dfthc_math). The error_2 expansion through the Gram matrix
G_bb' = (u_b . u_b')^2 and Qt = P T P^T follows the public refit codes of Lera (marculera, refit_weights.py,
Apache-2.0) and prvsiyan (chemlib.py, Apache-2.0); the split of the weights into non-negative parts (L1 terms
linear) follows prvsiyan's refit_grg.py (Apache-2.0).

Variables: w (R, B, C) = file 'W', wB (R, C) = file 'H2_I'. Native offsets Wc = wB - sum_b w.
    g_rb    = sum_c Wc_rc w_rbc
    h1'     = A0 - sum_rb g_rb u_rb u_rb^T
    E_gap   = c0 + sum|lam| - sum lam + 0.5 sum Wc^2
    Lambda  = sum|lam| + 1/4 sum_rc (sum_b |w_rbc| + |wB_rc|)^2
    error_2 = sqrt(sum_rs ||w_r^T G_rs w_s||^2 - 2 sum_r tr(w_r^T Qt_rr w_r) + ||T||^2)
    error_1 = || sum_j lam_pi(j) v_j v_j^T - h1' ||_F   (v_j = the fixed one-body rows)

The (R*B, R*B) matrices Qt/T2 take about a minute to build; pass cache_key to keep them in QCC_CACHE
(default: <temp dir>/qcc_refit_cache). Licence: Apache-2.0.
"""
from __future__ import annotations

import os
import tempfile

import numpy as np
from scipy.optimize import linear_sum_assignment

from . import chemeval as ce

CACHE = os.environ.get("QCC_CACHE", os.path.join(tempfile.gettempdir(), "qcc_refit_cache"))


class Model:
    def __init__(self, words, edges, R, B, brot=8, cache_key=None, rows=None):
        """words: full (N + R*B, N-1) table; rows (optional): two-body row indices (into the R0*B0 rows
        of words[N:]) to use, in (rho, b) order, for reduced shapes."""
        dm = ce.dm()
        ref = ce.reference()
        S, beta = ce.shifts()
        N = 76
        self.N, self.R, self.B = N, R, B
        u_all = dm.reconstruct_u_vectors(np.asarray(words) / (1 << (brot - 1)), np.asarray(edges))
        u_all = u_all / np.linalg.norm(u_all, axis=1, keepdims=True)
        self.v1 = u_all[:N]
        u2 = u_all[N:]
        if rows is not None:
            u2 = u2[np.asarray(rows)]
        self.u = u2.reshape(R, B, N)
        self.c0 = float(ce.refmod().UPPER_ENERGY - ref['ecore'] + ref['electrons'] * beta)
        oei = np.asarray(ref['oei'], np.float64)
        flat = self.u.reshape(R * B, N)
        tei = np.asarray(ref['tei'], np.float64)
        self.A0 = oei - 0.5 * np.einsum('prrq->pq', tei) - 0.5 * ref['electrons'] * S + beta * np.eye(N)
        self.G = (flat @ flat.T) ** 2
        path = None
        if cache_key:
            os.makedirs(CACHE, exist_ok=True)
            path = f'{CACHE}/qt_{cache_key}.npz'
        if path and os.path.exists(path):
            z = np.load(path)
            self.Qt, self.T2 = z['Qt'], float(z['T2'])
        else:
            T = tei.reshape(N * N, N * N)
            eye = np.eye(N).ravel()
            T = T + 0.5 * (np.outer(S.ravel(), eye) + np.outer(eye, S.ravel()))
            P = np.einsum('mp,mq->mpq', flat, flat).reshape(R * B, N * N)
            TP = T @ P.T
            Qt = P @ TP
            self.Qt = 0.5 * (Qt + Qt.T)
            self.T2 = float(np.sum(T * T))
            del T, TP
            if path:
                np.savez(path, Qt=self.Qt, T2=self.T2)
        self.Qd = np.stack([self.Qt[r * B:(r + 1) * B, r * B:(r + 1) * B] for r in range(R)])
        self.Gb = self.G.reshape(R, B, R, B)

    # ------------------------------------------------------------------
    def error2(self, w):
        R, B, C = w.shape
        Wbd = np.zeros((R * B, R * C))
        for r in range(R):
            Wbd[r * B:(r + 1) * B, r * C:(r + 1) * C] = w[r]
        GW = self.G @ Wbd                       # (RB, RC)
        Amat = Wbd.T @ GW                        # (RC, RC)
        F = float(np.sum(Amat * Amat))
        L = float(np.einsum('rbc,rbd,rdc->', w, self.Qd, w, optimize=True))
        e2sq = F - 2 * L + self.T2
        e2 = float(np.sqrt(max(e2sq, 0.0)))
        dF = 4 * GW @ Amat                       # (RB, RC), only diagonal blocks used
        de2sq = np.stack([dF[r * B:(r + 1) * B, r * C:(r + 1) * C] for r in range(R)])
        de2sq -= 4 * np.einsum('rbd,rdc->rbc', self.Qd, w)
        return e2, de2sq / (2 * max(e2, 1e-300))

    def evaluate(self, w, wB, need_grad=True, eps=0.0):
        """Returns dict of metrics and (if need_grad) gradients {name: (dw, dwB)} for
        e2, e1, gap, Lam (Lam with the L1 terms as functions of |w|, see split_grad)."""
        R, B, C = w.shape
        N = self.N
        Wc = wB - w.sum(axis=1)
        g = np.einsum('rc,rbc->rb', Wc, w)
        h1 = self.A0 - np.einsum('rb,rbp,rbq->pq', g, self.u, self.u, optimize=True)
        h1 = 0.5 * (h1 + h1.T)
        lam, V = np.linalg.eigh(h1)
        ov = np.abs(self.v1 @ V)
        qi, ii = linear_sum_assignment(-ov)
        perm = np.empty(N, dtype=np.int64)
        perm[qi] = ii
        lam_m = lam[perm]
        rec = np.einsum('j,jp,jq->pq', lam_m, self.v1, self.v1)
        Rres = rec - h1
        e1 = float(np.linalg.norm(Rres))
        alam = np.sqrt(lam * lam + eps * eps) if eps > 0 else np.abs(lam)
        sabs = float(alam.sum())
        gap = self.c0 + sabs - float(lam.sum()) + 0.5 * float(np.sum(Wc ** 2))
        m = np.abs(w).sum(axis=1) + np.abs(wB)
        Lam = sabs + 0.25 * float(np.sum(m ** 2))
        e2, de2 = self.error2(w)
        out = dict(error_1=e1, error_2=e2, E_gap=gap, Lambda=Lam)
        rad = gap * (2 * Lam - gap)
        out['lambda_eff'] = float(np.sqrt(rad)) if rad > 0 else float('nan')
        if not need_grad:
            return out, None
        # gradients w.r.t. h1'
        M_abs = (V * (lam / alam if eps > 0 else np.sign(lam))) @ V.T
        M_sum = np.eye(N)
        vRv = np.einsum('jp,pq,jq->j', self.v1, Rres, self.v1)
        Vp = V[:, perm]                              # eigenvector matched to row j
        M_e1 = ((Vp * vRv) @ Vp.T - Rres) / max(e1, 1e-300)

        def via_h1(Mh, dWc_direct):
            gam = -np.einsum('rbp,pq,rbq->rb', self.u, Mh, self.u, optimize=True)   # dF/dg
            eta = dWc_direct + np.einsum('rb,rbc->rc', gam, w)                   # dF/dWc total
            dw = gam[:, :, None] * Wc[:, None, :] - eta[:, None, :]
            return dw, eta.copy()

        zR = np.zeros((R, C))
        d_gap = via_h1(M_abs - M_sum, Wc)
        d_e1 = via_h1(M_e1, zR)
        d_lam_h1 = via_h1(M_abs, zR)
        out_g = {'e2': (de2, np.zeros_like(wB)), 'gap': d_gap, 'e1': d_e1, 'lamh1': d_lam_h1, 'm': m}
        return out, out_g


def split(w, wB):
    return np.concatenate([np.maximum(w, 0).ravel(), np.maximum(-w, 0).ravel(),
                           np.maximum(wB, 0).ravel(), np.maximum(-wB, 0).ravel()])


def unsplit(x, shape):
    R, B, C = shape
    nW, nH = R * B * C, R * C
    p, n = x[:nW].reshape(R, B, C), x[nW:2 * nW].reshape(R, B, C)
    hp, hn = x[2 * nW:2 * nW + nH].reshape(R, C), x[2 * nW + nH:].reshape(R, C)
    return p, n, hp, hn


class SplitProblem:
    """Metrics as functions of x = (p, n, hp, hn) >= 0 with w = p - n, wB = hp - hn and the L1 parts of
    Lambda written as p + n (linear)."""

    def __init__(self, model, shape):
        self.M, self.shape = model, shape

    def evaluate(self, x, need_grad=True, eps=0.0):
        p, n, hp, hn = unsplit(x, self.shape)
        w, wB = p - n, hp - hn
        out, g = self.M.evaluate(w, wB, need_grad, eps)
        # Lambda in split form
        mS = (p + n).sum(axis=1) + hp + hn
        m = np.abs(w).sum(axis=1) + np.abs(wB)
        out['Lambda_split'] = out['Lambda'] - 0.25 * float(np.sum(m ** 2)) + 0.25 * float(np.sum(mS ** 2))
        if not need_grad:
            return out, None
        grads = {}
        for k in ('e2', 'gap', 'e1', 'lamh1'):
            dw, dB = g[k]
            grads[k] = np.concatenate([dw.ravel(), -dw.ravel(), dB.ravel(), -dB.ravel()])
        dl1w = np.broadcast_to(0.5 * mS[:, None, :], p.shape)
        dl1 = np.concatenate([dl1w.ravel(), dl1w.ravel(), (0.5 * mS).ravel(), (0.5 * mS).ravel()])
        grads['Lam'] = grads['lamh1'] + dl1
        return out, grads
