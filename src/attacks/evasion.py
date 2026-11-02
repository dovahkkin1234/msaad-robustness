"""Feature-space evasion attacks (FGSM, BIM, PGD, C&W-L2), as in the base paper's MSAPG.

All attacks work on the min-max-scaled feature matrix X (n, d) that MABTSE sees, using the
surrogate's gradients, and respect three rules:
  * only rows in ``rows`` are perturbed (e.g. only DDoS flows under the realistic threat model);
  * missing features (NaN) stay missing and are never perturbed;
  * values stay in the scaled domain box [min(0, x), max(1, x)] per element, so a value the
    scaler legitimately put outside [0, 1] is not pulled back in.
L-inf attacks also stay inside the epsilon ball around the original vector.

Parameter choices (the paper only says "default parameters, epsilon 0.1" for IBM ART):
  FGSM one step of size eps; BIM eps_step=eps/4 x 20 steps; PGD the same plus one random start;
  C&W-L2 (binary form, projected Adam) with a 6-step binary search on the constant c.
"""
from __future__ import annotations

from typing import Optional, Tuple

import numpy as np

from .surrogate import Surrogate


def _prep(X: np.ndarray, rows: np.ndarray):
    X = np.asarray(X, dtype=float)
    nan = np.isnan(X)
    Xf = np.where(nan, 0.0, X)
    lo, hi = np.minimum(0.0, Xf), np.maximum(1.0, Xf)
    fixed = nan | ~np.asarray(rows, dtype=bool)[:, None]  # positions that must not move
    return Xf, nan, lo, hi, fixed


def _finish(Xf: np.ndarray, Xa: np.ndarray, nan: np.ndarray, fixed: np.ndarray) -> np.ndarray:
    out = np.where(fixed, Xf, Xa)
    out[nan] = np.nan
    return out


def fgsm(sur: Surrogate, X: np.ndarray, y: np.ndarray, eps: float, rows: np.ndarray) -> np.ndarray:
    """Fast Gradient Sign Method: one step of size eps along sign(grad of the loss)."""
    Xf, nan, lo, hi, fixed = _prep(X, rows)
    Xa = np.clip(Xf + eps * np.sign(sur.loss_grad(Xf, y)), lo, hi)
    return _finish(Xf, Xa, nan, fixed)


def _iterative(sur, Xf, y, eps, step, iters, lo, hi, fixed, start):
    Xa = np.where(fixed, Xf, start)
    for _ in range(iters):
        Xa = Xa + step * np.sign(sur.loss_grad(Xa, y))
        Xa = np.clip(np.clip(Xa, Xf - eps, Xf + eps), lo, hi)
        Xa = np.where(fixed, Xf, Xa)
    return Xa


def bim(sur: Surrogate, X: np.ndarray, y: np.ndarray, eps: float, rows: np.ndarray,
        step: float = 0.025, iters: int = 20) -> np.ndarray:
    """Basic Iterative Method (iterated FGSM, projected to the eps ball)."""
    Xf, nan, lo, hi, fixed = _prep(X, rows)
    Xa = _iterative(sur, Xf, y, eps, step, iters, lo, hi, fixed, Xf)
    return _finish(Xf, Xa, nan, fixed)


def pgd(sur: Surrogate, X: np.ndarray, y: np.ndarray, eps: float, rows: np.ndarray,
        step: float = 0.025, iters: int = 20, random_start: bool = True,
        seed: int = 0) -> np.ndarray:
    """Projected Gradient Descent (Madry et al.): BIM from a random point in the eps ball."""
    Xf, nan, lo, hi, fixed = _prep(X, rows)
    start = Xf
    if random_start:
        rng = np.random.default_rng(seed)
        start = np.clip(Xf + rng.uniform(-eps, eps, size=Xf.shape), lo, hi)
    Xa = _iterative(sur, Xf, y, eps, step, iters, lo, hi, fixed, start)
    return _finish(Xf, Xa, nan, fixed)


def cw_l2(sur: Surrogate, X: np.ndarray, y: np.ndarray, rows: np.ndarray,
          confidence: float = 0.0, lr: float = 0.01, iters: int = 100,
          search_steps: int = 6, c_init: float = 1.0) -> Tuple[np.ndarray, np.ndarray]:
    """Carlini-Wagner L2, binary form.

    For each row, minimise ||x' - x||^2 + c * max(s * z(x') + confidence, 0), where z is the
    surrogate's logit and s = +1 for attack rows (push to benign) or -1 for benign rows.
    Projected Adam keeps x' in the domain box; a binary search tunes c per row. Rows with
    no adversarial point found are returned unchanged (as IBM ART does).
    Returns (X_adv, found) where ``found`` marks rows that fooled the surrogate.
    """
    Xf, nan, lo, hi, fixed = _prep(X, rows)
    rows = np.asarray(rows, dtype=bool)
    y = np.asarray(y).astype(int)
    s = np.where(y == 1, 1.0, -1.0)
    n = len(Xf)
    c = np.full(n, float(c_init))
    c_lo, c_hi = np.zeros(n), np.full(n, np.inf)
    best, best_l2 = Xf.copy(), np.full(n, np.inf)
    found = np.zeros(n, dtype=bool)
    b1, b2, tiny = 0.9, 0.999, 1e-8
    for _ in range(search_steps):
        Xa = Xf.copy()
        m, v = np.zeros_like(Xf), np.zeros_like(Xf)
        hit = np.zeros(n, dtype=bool)
        for t in range(1, iters + 1):
            z = sur.logit(Xa)
            active = (s * z + confidence) > 0
            grad = 2.0 * (Xa - Xf) + (c * active * s)[:, None] * sur.grad_logit(Xa)
            m = b1 * m + (1 - b1) * grad
            v = b2 * v + (1 - b2) * grad * grad
            Xa = Xa - lr * (m / (1 - b1 ** t)) / (np.sqrt(v / (1 - b2 ** t)) + tiny)
            Xa = np.where(fixed, Xf, np.clip(Xa, lo, hi))
            adv = rows & ((s * sur.logit(Xa) + confidence) < 0)
            l2 = np.sum((Xa - Xf) ** 2, axis=1)
            better = adv & (l2 < best_l2)
            best[better], best_l2[better] = Xa[better], l2[better]
            hit |= adv
        found |= hit
        # Binary search on c: success -> try a smaller c; failure -> a larger one.
        c_hi = np.where(hit, np.minimum(c_hi, c), c_hi)
        c_lo = np.where(hit, c_lo, np.maximum(c_lo, c))
        c = np.where(np.isinf(c_hi), c * 10.0, (c_lo + c_hi) / 2.0)
    return _finish(Xf, best, nan, fixed), found


def run_attack(name: str, sur: Surrogate, X: np.ndarray, y: np.ndarray, rows: np.ndarray,
               eps: float, params: Optional[dict] = None, seed: int = 0) -> np.ndarray:
    """Dispatch by name: fgsm, bim, pgd, cw."""
    p = dict(params or {})
    if name == "fgsm":
        return fgsm(sur, X, y, eps, rows)
    if name == "bim":
        return bim(sur, X, y, eps, rows, step=p.get("step", eps / 4), iters=p.get("iters", 20))
    if name == "pgd":
        return pgd(sur, X, y, eps, rows, step=p.get("step", eps / 4), iters=p.get("iters", 20),
                   random_start=p.get("random_start", True), seed=seed)
    if name == "cw":
        return cw_l2(sur, X, y, rows, confidence=p.get("confidence", 0.0), lr=p.get("lr", 0.01),
                     iters=p.get("iters", 100), search_steps=p.get("search_steps", 6),
                     c_init=p.get("c_init", 1.0))[0]
    raise ValueError(f"unknown attack {name!r}; choose from fgsm, bim, pgd, cw")
