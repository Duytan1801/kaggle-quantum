import numpy as np
from .grg import GRG
class GRG2(GRG):
    """GRG with a full Newton restoration (Jacobian recomputed each iteration; the chord version oscillates here)."""
    def restore(self, x, eps, J, free, tol=2e-10, maxit=8):
        maxit = max(maxit, 12)
        for _ in range(maxit):
            f, c, e1, g, JJ = self.fgc(x, eps)
            r = c - self.TGT
            if not np.all(np.isfinite(r)):
                return x, f, c, e1, False
            if np.max(np.abs(r)) < tol:
                return x, f, c, e1, True
            act = x > 0
            mu = np.linalg.lstsq((JJ * act).T, g * act, rcond=None)[0]
            fr = self.free_mask(x, g - mu @ JJ)
            Jf = JJ * fr
            x = np.maximum(0.0, x - Jf.T @ np.linalg.solve(Jf @ Jf.T, r))
        f, c, e1 = self.fgc(x, eps, grads=False)
        return x, f, c, e1, bool(np.max(np.abs(c - self.TGT)) < 50 * tol)
