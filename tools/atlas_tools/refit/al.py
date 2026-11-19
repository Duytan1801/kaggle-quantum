"""Augmented-Lagrangian refit of (w, H2_I) at fixed words: minimise lambda_eff subject to
error_2 <= T2, error_1 <= T1, E_gap >= floor (own code; the AL formulation follows Lera's refit_al.py,
Apache-2.0, and the non-negative split + Newton restoration onto the active constraints follow prvsiyan's
refit_grg.py, Apache-2.0)."""
from __future__ import annotations
import time
import numpy as np
from scipy.optimize import minimize
from .model import SplitProblem, split, unsplit

FLOOR = 3.914898
GATE = 0.02


class Refit:
    def __init__(self, model, shape, m1=2e-9, m2=2e-9, mg=3e-9, eps=1e-6, log=print):
        self.SP = SplitProblem(model, shape)
        self.shape = shape
        self.t1, self.t2, self.fl = GATE - m1, GATE - m2, FLOOR + mg
        self.eps = eps
        self.log = log

    def parts(self, x, eps):
        o, g = self.SP.evaluate(x, True, eps)
        Lam, gap = o['Lambda_split'], o['E_gap']
        rad = gap * (2 * Lam - gap)
        if not (rad > 0):
            return None
        f = 500.0 * np.log(rad)
        df = 1e3 * ((Lam - gap) * g['gap'] + gap * g['Lam']) / rad
        cons = np.array([1e3 * (o['error_2'] - self.t2), 1e3 * (o['error_1'] - self.t1), 1e3 * (self.fl - gap)])
        dcons = np.stack([1e3 * g['e2'], 1e3 * g['e1'], -1e3 * g['gap']])
        return o, f, df, cons, dcons

    def al_solve(self, x0, outer=30, inner=400, rho=1.0, y=None, active=(True, True, True)):
        y = np.zeros(3) if y is None else np.asarray(y, float)
        act = np.array(active)
        x = x0.copy()
        t0 = time.time()
        prev_viol = np.inf
        for k in range(outer):
            def fun(z):
                r = self.parts(z, self.eps)
                if r is None:
                    return 1e12, np.zeros_like(z)
                o, f, df, c, dc = r
                pen = np.maximum(0.0, y + rho * c) * act
                val = f + float(np.sum((pen ** 2 - (y * act) ** 2) / (2 * rho)))
                return val, df + pen @ dc
            res = minimize(fun, x, jac=True, method='L-BFGS-B', bounds=[(0, None)] * x.size,
                           options={'maxiter': inner, 'maxcor': 30, 'ftol': 1e-14, 'gtol': 1e-9, 'maxls': 50})
            x = res.x
            o, f, df, c, dc = self.parts(x, 0.0)
            viol = float(np.max(np.maximum(c * act, 0)))
            y = np.maximum(0.0, y + rho * c) * act
            if viol > 0.25 * prev_viol and viol > 1e-6:
                rho = min(rho * 4, 1e4)
            prev_viol = viol
            self.log(f'AL {k}: it {res.nit} e2 {1e3*o["error_2"]:.6f} e1 {1e3*o["error_1"]:.6f} gap {o["E_gap"]:.7f} '
                     f'Lam {o["Lambda"]:.4f} leff {o["lambda_eff"]:.6f} y {np.round(y,3)} rho {rho:g} ({time.time()-t0:.0f}s)')
            if viol < 1e-5 and k >= 3 and res.nit < 5:
                break
        return x, y, rho

    def restore(self, x, maxit=30, tol=1e-12):
        """Newton steps (exact metrics) on violated / active constraints, free variables only, until all
        constraints hold with their margins."""
        for it in range(maxit):
            o, g = self.SP.evaluate(x, True, 0.0)
            c = np.array([o['error_2'] - self.t2, o['error_1'] - self.t1, self.fl - o['E_gap']])
            if np.all(c <= tol):
                return x, o, True
            J = np.stack([g['e2'], g['e1'], -g['gap']])
            sel = c > -1e-7                     # near-active constraints are held at their target
            free = (x > 0).astype(float)
            Jf = J[sel] * free
            r = np.minimum(c[sel], 0) * 0 + c[sel] + 1e-11
            step = Jf.T @ np.linalg.lstsq(Jf @ Jf.T, r, rcond=None)[0]
            x = np.maximum(0.0, x - step)
        o, _ = self.SP.evaluate(x, False, 0.0)
        c = np.array([o['error_2'] - self.t2, o['error_1'] - self.t1, self.fl - o['E_gap']])
        return x, o, bool(np.all(c <= tol))


def save_npz(path, base, w, wB):
    d = dict(base)
    R, B, C = w.shape
    d['W'] = w
    d['H2_I'] = wB
    if d['U'].shape[:2] != (R, B):
        raise ValueError('U shape mismatch')
    np.savez(path, **d)
