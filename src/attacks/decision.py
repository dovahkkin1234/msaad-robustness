"""Decision-based (label-only) evasion: HopSkipJump, L-infinity version.

The transfer attacks need a differentiable surrogate. An adaptive attacker can instead query
the deployed detector and see only its verdict (benign / DDoS), as a real attacker probing
an IDS does. HopSkipJumpAttack (Chen, Jordan & Wainwright, IEEE S&P 2020) needs nothing
else: it finds a point on the decision boundary between the flow and a benign-looking
starting point, estimates the boundary's normal from the signs of verdicts at random probes
around it, and walks along it towards the original flow.

This implementation follows the paper's L-infinity variant (sign-gradient steps, geometric
step-size search, binary search back to the boundary, batch size growing with sqrt(t)) with
three choices of ours: the starting point is the attacker's closest benign-looking flow
from its own data that the detector already calls benign; only perturbable coordinates
(non-missing) move and every point is clipped to the scaled domain box; and the result is
judged at the paper's budget eps (L-inf 0.1 in the scaled space), with the number of
queries spent recorded so success can be reported per query budget.
"""
from __future__ import annotations

from typing import Callable, Dict, Optional

import numpy as np


def _clip(x, lo, hi):
    return np.minimum(np.maximum(x, lo), hi)


def hsja_linf(decide: Callable[[np.ndarray], np.ndarray], x0: np.ndarray, starts: np.ndarray,
              eps: float, max_queries: int = 2000, iters: int = 40, init_batch: int = 50,
              rng: Optional[np.random.Generator] = None, movable: Optional[np.ndarray] = None,
              lo: Optional[np.ndarray] = None, hi: Optional[np.ndarray] = None) -> Dict:
    """Search for x with decide(x) == 0 (benign) and ||x - x0||_inf <= eps.

    decide: batch -> 0/1 verdicts (counts as len(batch) queries). starts: candidate benign
    flows (rows) tried in order as the starting point. Returns {"x": best adversarial point
    or None, "dist": its L-inf distance, "queries": spent, "success": dist <= eps,
    "first_success_query": queries spent when dist first fell to <= eps (or None)}."""
    rng = rng or np.random.default_rng(0)
    x0 = np.nan_to_num(np.asarray(x0, float))
    movable = np.ones_like(x0, bool) if movable is None else movable
    lo = np.minimum(0.0, x0) if lo is None else lo
    hi = np.maximum(1.0, x0) if hi is None else hi
    q = 0

    def ask(X):
        nonlocal q
        X = np.atleast_2d(X)
        q += len(X)
        return np.asarray(decide(X)).astype(int)

    # 1. Starting point: the first benign-looking flow the detector calls benign.
    xa = None
    for s in starts:
        if q >= max_queries:
            break
        cand = np.where(movable, _clip(np.nan_to_num(s), lo, hi), x0)
        if ask(cand)[0] == 0:
            xa = cand
            break
    out = {"x": None, "dist": float("inf"), "queries": q, "success": False, "first_success_query": None}
    if xa is None:
        return out

    def boundary(xadv, steps=12):
        """Binary search on the segment x0 -> xadv (in L-inf blend) for the boundary."""
        lo_t, hi_t = 0.0, 1.0                    # t = share of the way from x0 to xadv
        for _ in range(steps):
            if q >= max_queries:
                break
            mid = (lo_t + hi_t) / 2
            if ask(x0 + mid * (xadv - x0))[0] == 0:
                hi_t = mid
            else:
                lo_t = mid
        return x0 + hi_t * (xadv - x0)

    xb = boundary(xa)
    best = xb
    bd = float(np.max(np.abs(best - x0)))
    if bd <= eps:
        out["first_success_query"] = q
    d = int(movable.sum())
    for t in range(1, iters + 1):
        if q >= max_queries:
            break
        # 2. Estimate the boundary normal from the signs of verdicts at random probes.
        nb = int(min(init_batch * np.sqrt(t), max(1, max_queries - q - 20)))
        if nb < 2:
            break
        delta = max(1e-3, np.sqrt(d) * 1e-2 * float(np.max(np.abs(xb - x0))))
        U = rng.choice([-1.0, 1.0], size=(nb, len(x0))) * movable
        probes = _clip(xb + delta * U, lo, hi)
        phi = np.where(ask(probes) == 0, 1.0, -1.0)
        phi = phi - phi.mean() if np.abs(phi.mean()) < 1.0 else phi
        g = (phi[:, None] * U).mean(0)
        if not np.any(g):
            continue
        direction = np.sign(g) * movable
        # 3. Geometric step search along the estimated normal, then back to the boundary.
        dist = float(np.max(np.abs(xb - x0)))
        step = dist / np.sqrt(t)
        moved = None
        while step > 1e-4 and q < max_queries:
            cand = _clip(xb + step * direction, lo, hi)
            if ask(cand)[0] == 0:
                moved = cand
                break
            step /= 2
        if moved is None:
            continue
        xb = boundary(moved)
        nd = float(np.max(np.abs(xb - x0)))
        if nd < bd:
            best, bd = xb, nd
            if bd <= eps and out["first_success_query"] is None:
                out["first_success_query"] = q
    # Final: if the boundary point is outside the budget, try its projection onto the eps-ball.
    if bd > eps and q < max_queries:
        proj = _clip(np.clip(best, x0 - eps, x0 + eps), lo, hi)
        if ask(proj)[0] == 0:
            best, bd = proj, float(np.max(np.abs(proj - x0)))
            out["first_success_query"] = q
    out.update({"x": best, "dist": bd, "queries": q, "success": bd <= eps + 1e-9})
    return out
