"""Reduced-gradient refit on the surface error_2 = TAU, E_gap = EFL (and error_1 = E1T once it binds).

A numpy port of prvsiyan's refit_grg.py (Copyright 2026 prvsiyan, Apache-2.0; dataset
prvsiyan/vqcc-verified-best-of-circuits-1106a, code/refit_grg.py): non-negative split of the weights,
L-BFGS direction of the Lagrangian projected on the tangent space of the active constraints, Newton
restoration back onto the surface for every trial point, exact (unsmoothed) restoration + official check
for saved points. Changes here: numpy gradients from model.SplitProblem instead of torch autograd, a
generic shape (any R, B, C), and a callback for saving.
"""
from __future__ import annotations
import time
import numpy as np
from .model import SplitProblem

E_GAP_FLOOR = 3.914898


class GRG:
    def __init__(self, model, shape, m2=3e-9, mg=3e-9, m1=2e-8, eps=1e-6, mem=20, log=print):
        self.SP = SplitProblem(model, shape)
        self.TAU = 0.02 - m2
        self.EFL = E_GAP_FLOOR + mg
        self.E1T = 0.02 - m1
        self.EPS = eps
        self.MEM = mem
        self.log = log
        self.TGT3 = np.array([self.TAU * 1e3, self.EFL * 1e3, self.E1T * 1e3])
        self.NC = 2
        self.LEFF0 = None

    def fgc(self, x, eps, grads=True):
        o, g = self.SP.evaluate(x, grads, eps)
        Lam, gap = o['Lambda_split'], o['E_gap']
        L0 = self.LEFF0
        f = gap * (2 * Lam - gap) / (2 * L0) - 0.5 * L0
        cc = np.array([1e3 * o['error_2'], 1e3 * gap, 1e3 * o['error_1']])[:self.NC]
        if not grads:
            return f, cc, o['error_1']
        df = ((2 * Lam - 2 * gap) * g['gap'] + 2 * gap * g['Lam']) / (2 * L0)
        J = np.stack([1e3 * g['e2'], 1e3 * g['gap'], 1e3 * g['e1']])[:self.NC]
        return f, cc, o['error_1'], df, J

    @property
    def TGT(self):
        return self.TGT3[:self.NC]

    def restore(self, x, eps, J, free, tol=2e-10, maxit=8):
        Jf = J * free
        Mm = Jf @ Jf.T
        for _ in range(maxit):
            f, c, e1 = self.fgc(x, eps, grads=False)
            r = c - self.TGT
            if not np.all(np.isfinite(r)):
                return x, f, c, e1, False
            if np.max(np.abs(r)) < tol:
                return x, f, c, e1, True
            x = np.maximum(0.0, x - Jf.T @ np.linalg.solve(Mm, r))
        f, c, e1 = self.fgc(x, eps, grads=False)
        return x, f, c, e1, bool(np.max(np.abs(c - self.TGT)) < 50 * tol)

    @staticmethod
    def free_mask(x, g):
        return (x > 0) | (g < 0)

    def exact_point(self, x, free):
        fe, ce, e1e, ge, Je = self.fgc(x, 0.0)
        xe, fe, ce, e1e, okr = self.restore(x.copy(), 0.0, Je, free, tol=5e-10, maxit=12)
        return xe, okr

    def feasible(self, x, maxit=200, frac=0.3):
        """Damped min-norm steps (free variables) that move the three constraints toward their targets by at
        most `frac` of the residual per step: a robust way onto the surface from a far start."""
        NC0 = self.NC; self.NC = 3
        for it in range(maxit):
            f, c, e1, g, J = self.fgc(x, self.EPS)
            r = c - self.TGT3
            r[0] = max(r[0], -0.0); r[2] = max(r[2], 0.0)   # e2, e1 one-sided; gap held at the floor
            if np.max(np.abs(r)) < 1e-3:
                break
            mu = np.linalg.lstsq((J * (x > 0)).T, g * (x > 0), rcond=None)[0]
            free = self.free_mask(x, g - mu @ J)
            Jf = J * free
            step = Jf.T @ np.linalg.solve(Jf @ Jf.T + 1e-12 * np.eye(3), frac * r)
            x = np.maximum(0.0, x - step)
            if it % 10 == 0:
                o, _ = self.SP.evaluate(x, False, 0.0)
                self.log(f'feas {it} r {np.round(r, 4)} leff {o["lambda_eff"]:.6f} Lam {o["Lambda"]:.4f}')
        self.NC = NC0
        return x

    def run(self, x, iters, on_check=None, check_every=50, e1switch=0.0199, feas=True):
        o, _ = self.SP.evaluate(x, False, 0.0)
        if self.LEFF0 is None:
            self.LEFF0 = o['lambda_eff']
        if feas:
            x = self.feasible(x)
            o, _ = self.SP.evaluate(x, False, 0.0)
        if o['error_1'] > e1switch:
            self.NC = 3
        f, c, e1, g, J = self.fgc(x, self.EPS)
        self.log('GRG smoothed start f', f, 'c', c, 'target', self.TGT, 'e1', e1)
        mu = np.linalg.lstsq((J * (x > 0)).T, g * (x > 0), rcond=None)[0]
        free = self.free_mask(x, g - mu @ J)
        x, f, c, e1, okr = self.restore(x, self.EPS, J, free, maxit=40)
        self.log('restored', f, c, e1, okr)
        f, c, e1, g, J = self.fgc(x, self.EPS)
        S_, Y_ = [], []
        t0 = time.time(); alpha = 1.0; nfail = 0
        for it in range(iters):
            act = x > 0
            mu = np.linalg.lstsq((J * act).T, g * act, rcond=None)[0]
            gL = g - mu @ J
            free = self.free_mask(x, gL)
            gF = gL * free
            Jf = J * free
            JJ = Jf @ Jf.T

            def proj(v):
                return v - Jf.T @ np.linalg.solve(JJ, Jf @ v)
            pg = proj(gF)
            q = pg.copy(); al_ = []
            for s, y in reversed(list(zip(S_, Y_))):
                a = (s @ q) / (y @ s); al_.append(a); q -= a * y
            if S_:
                q *= (S_[-1] @ Y_[-1]) / (Y_[-1] @ Y_[-1])
            for (s, y), a in zip(zip(S_, Y_), reversed(al_)):
                b = (y @ q) / (y @ s); q += (a - b) * s
            d = -proj(q * free)
            slope = pg @ d
            if slope >= 0:
                d = -pg; slope = -(pg @ pg); S_, Y_ = [], []
            if not S_:
                alpha = min(alpha, 1e-3 / max(np.abs(d).max(), 1e-30))
            else:
                alpha = 1.0
            ok = False; hit1 = False
            for ls in range(25):
                xt = np.maximum(0.0, x + alpha * d)
                xt, ft, ct, e1t, okr = self.restore(xt, self.EPS, J, free)
                if okr and np.isfinite(ft) and ft < f + 1e-4 * alpha * slope and (self.NC == 3 or e1t < self.E1T):
                    ok = True; break
                if self.NC == 2 and okr and np.isfinite(ft) and e1t >= self.E1T:
                    hit1 = True
                alpha *= 0.4
            if not ok and hit1:
                self.NC = 3; S_, Y_ = [], []
                f, c, e1, g, J = self.fgc(x, self.EPS)
                act = x > 0; mu = np.linalg.lstsq((J * act).T, g * act, rcond=None)[0]
                x, f, c, e1, okr = self.restore(x, self.EPS, J, self.free_mask(x, g - mu @ J), maxit=20)
                f, c, e1, g, J = self.fgc(x, self.EPS)
                self.log(f'it {it} error_1 constraint switched on; restored {okr} c {c}')
                continue
            if not ok:
                nfail += 1
                self.log(f'it {it} line search failed; reset memory (fail {nfail})')
                if not S_ and nfail > 3:
                    break
                S_, Y_ = [], []; alpha = 1.0
                continue
            nfail = 0
            go, Jo, muo = g, J, mu
            xo = x; x = xt
            f, c, e1, g, J = self.fgc(x, self.EPS)
            s = x - xo; y = proj(((g - muo @ J) - (go - muo @ Jo)) * free)
            if s @ y > 1e-12 * np.linalg.norm(s) * np.linalg.norm(y):
                S_.append(s); Y_.append(y); S_, Y_ = S_[-self.MEM:], Y_[-self.MEM:]
            if it % 10 == 0 or it == iters - 1:
                o, _ = self.SP.evaluate(x, False, 0.0)
                self.log(f'it {it} {time.time()-t0:.0f}s f {f:.4e} |pg| {np.linalg.norm(pg):.2e} alpha {alpha:.1e} '
                         f'nfree {int(free.sum())} NC {self.NC} | leff {o["lambda_eff"]:.8f} e2 {o["error_2"]:.10f} '
                         f'Eg {o["E_gap"]:.9f} e1 {o["error_1"]:.8f} Lam {o["Lambda"]:.4f}')
                if on_check and it % check_every == 0:
                    xe, okr = self.exact_point(x, free)
                    on_check(xe, okr)
        xe, okr = self.exact_point(x, self.free_mask(x, g - mu @ J))
        if on_check:
            on_check(xe, okr)
        return x, xe, okr
