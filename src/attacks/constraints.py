"""Domain constraints of flow features — the feasibility audit for adversarial vectors.

The base paper perturbs every scaled feature by up to eps = 0.1, including counts, flags
and protocol numbers. Many such vectors could never come from real traffic. This module
(1) mines constraints from CLEAN training flows, (2) counts how many adversarial vectors
break them, and (3) repairs (projects) adversarial vectors to satisfy them, so we can
measure what the attack achieves when it is restricted to realistic vectors.

Everything here works in RAW feature space (before min-max scaling).

Per-feature constraints (learned from the data):
  constant     the feature never varies in the clean data
  binary       values in {0, 1}
  categorical  at most `max_categorical` distinct values (e.g. Protocol in {0, 6, 17})
  integer      every clean value is a whole number (counts, bytes, ports, microseconds)
  nonneg       every clean value is >= 0
Cross-feature constraints:
  equality     two informative features equal on >= 99.9% of clean rows
               (e.g. Tot_Fwd_Pkts == Subflow_Fwd_Pkts)
  ordering     Min <= Mean/Avg <= Max within a feature family (matched by name), kept only
               if it holds on >= 99.9% of clean rows
The experiment adds one more check on the scaled side, "unproducible": a feature whose
running min equals its max was moved, although the scaler can only ever output 0 for it.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

TYPES = ("constant", "binary", "categorical", "integer", "nonneg", "equality", "ordering")
_FAMILY_RE = re.compile(r"^(.*?)[_ ]?(min|mean|avg|max)$", re.IGNORECASE)
_ROLE = {"min": 0, "mean": 1, "avg": 1, "max": 2}


def _tol(x: np.ndarray) -> np.ndarray:
    return 1e-6 * np.maximum(1.0, np.abs(x))


class ConstraintSet:
    def __init__(self, names: Sequence[str]) -> None:
        self.names = list(names)
        self.constant: Dict[int, float] = {}
        self.binary: List[int] = []
        self.allowed: Dict[int, np.ndarray] = {}      # binary + categorical value sets
        self.integer: List[int] = []
        self.nonneg: List[int] = []
        self.eq_groups: List[List[int]] = []          # first index = primary
        self.orderings: List[Tuple[int, int]] = []    # (lower, upper)

    # ---- mining -------------------------------------------------------------------------
    @classmethod
    def mine(cls, X: np.ndarray, names: Sequence[str], max_categorical: int = 10,
             min_support: float = 0.999, min_spread: float = 0.01) -> "ConstraintSet":
        """Learn constraints from clean rows X (n, d); NaN = missing value."""
        cs = cls(names)
        X = np.asarray(X, dtype=float)
        d = X.shape[1]
        informative = np.zeros(d, dtype=bool)
        for j in range(d):
            v = X[:, j]
            v = v[~np.isnan(v)]
            if len(v) == 0:
                continue
            vals, counts = np.unique(v, return_counts=True)
            if len(vals) == 1:
                cs.constant[j] = float(vals[0])
                continue
            if v.min() >= 0:
                cs.nonneg.append(j)
            if np.all(v == np.round(v)):
                cs.integer.append(j)
            if len(vals) == 2 and set(vals.tolist()) <= {0.0, 1.0}:
                cs.binary.append(j)
                cs.allowed[j] = vals
            elif len(vals) <= max_categorical:
                cs.allowed[j] = vals
            # Informative = not near-constant, so two mostly-zero columns are not "equal".
            informative[j] = (1.0 - counts.max() / len(v)) >= min_spread

        # Equalities among informative features, merged into groups (union-find).
        idx = [int(j) for j in np.where(informative)[0]]
        parent = {j: j for j in idx}

        def find(a: int) -> int:
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        for p, a in enumerate(idx):
            ca = X[:, a]
            for b in idx[p + 1:]:
                cb = X[:, b]
                both = ~np.isnan(ca) & ~np.isnan(cb)
                if both.sum() == 0:
                    continue
                same = np.abs(ca[both] - cb[both]) <= _tol(ca[both])
                if same.mean() >= min_support:
                    parent[find(b)] = find(a)
        groups = defaultdict(list)
        for j in idx:
            groups[find(j)].append(j)
        cs.eq_groups = [sorted(g) for g in groups.values() if len(g) > 1]

        # Orderings inside Min/Mean/Max families, verified on the data.
        families: Dict[str, Dict[int, int]] = defaultdict(dict)
        for j, nm in enumerate(cs.names):
            if j in cs.constant:
                continue
            m = _FAMILY_RE.match(str(nm).strip())
            if m:
                families[m.group(1).lower()].setdefault(_ROLE[m.group(2).lower()], j)
        for roles in families.values():
            ranks = sorted(roles)
            for i, r1 in enumerate(ranks):
                for r2 in ranks[i + 1:]:
                    a, b = roles[r1], roles[r2]
                    both = ~np.isnan(X[:, a]) & ~np.isnan(X[:, b])
                    if both.sum() and (X[both, a] <= X[both, b] + _tol(X[both, b])).mean() >= min_support:
                        cs.orderings.append((a, b))
        return cs

    # ---- checking -----------------------------------------------------------------------
    def _raw_violations(self, X: np.ndarray) -> Dict[str, np.ndarray]:
        X = np.asarray(X, dtype=float)
        n = len(X)
        out = {t: np.zeros(n, dtype=bool) for t in TYPES}
        with np.errstate(invalid="ignore"):
            for j, c in self.constant.items():
                out["constant"] |= np.abs(X[:, j] - c) > _tol(np.full(n, c))
            for j, vals in self.allowed.items():
                dist = np.min(np.abs(X[:, j][:, None] - vals[None, :]), axis=1)
                key = "binary" if j in self.binary else "categorical"
                out[key] |= dist > _tol(X[:, j])
            for j in self.integer:
                if j in self.allowed:
                    continue
                out["integer"] |= np.abs(X[:, j] - np.round(X[:, j])) > _tol(X[:, j])
            for j in self.nonneg:
                out["nonneg"] |= X[:, j] < -_tol(X[:, j])
            for g in self.eq_groups:
                p = X[:, g[0]]
                for j in g[1:]:
                    out["equality"] |= np.abs(X[:, j] - p) > _tol(p)
            for a, b in self.orderings:
                out["ordering"] |= X[:, a] > X[:, b] + _tol(X[:, b])
        # Comparisons with NaN are False, so a missing value never counts as a violation.
        return out

    def violations(self, X_adv: np.ndarray, X_clean: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """Per-type boolean (n,) arrays plus "any". With X_clean, count only violations the
        clean row did not already have (i.e. introduced by the perturbation)."""
        v = self._raw_violations(X_adv)
        if X_clean is not None:
            r = self._raw_violations(X_clean)
            v = {t: v[t] & ~r[t] for t in TYPES}
        v["any"] = np.logical_or.reduce([v[t] for t in TYPES])
        return v

    # ---- repairing ----------------------------------------------------------------------
    def project(self, X_adv: np.ndarray, X_clean: np.ndarray) -> np.ndarray:
        """Restrict an adversarial vector to its feasible part (raw space).

        The repair is MONOTONE: no feature ever ends up further from its clean value than the
        attack put it. So the repaired vector is a sub-perturbation of the original one, it
        respects the same epsilon budget, and any change in attack success comes from removing
        the impossible parts, never from a larger perturbation. Values are moved toward the
        clean value (integers truncated toward it, categories snapped only within the attack's
        own deviation, equality groups set to a common value within every member's deviation)
        and, where a constraint still fails, reverted to the clean value.
        """
        X = np.array(X_adv, dtype=float, copy=True)
        C = np.asarray(X_clean, dtype=float)
        with np.errstate(invalid="ignore"):
            dev = np.nan_to_num(np.abs(X - C))           # the attack's deviation per entry
            changed = dev > 1e-12 * np.maximum(1.0, np.nan_to_num(np.abs(C)))

            # 1. Equality groups: one common value, within every member's own deviation.
            for g in self.eq_groups:
                cg = C[:, g]
                same_clean = np.all(np.abs(cg - cg[:, :1]) <= _tol(cg[:, :1]), axis=1)
                rows = changed[:, g].any(axis=1) & same_clean & ~np.isnan(cg).any(axis=1)
                if not rows.any():
                    continue
                c = cg[rows, 0]
                m = dev[np.ix_(rows, g)].min(axis=1)
                v = c + np.clip(X[rows, g[0]] - c, -m, m)
                for j in g:
                    X[rows, j] = v

            # 2. Per-feature constraints, never increasing the deviation.
            for j in self.constant:
                r = changed[:, j]
                X[r, j] = C[r, j]
            for j, vals in self.allowed.items():
                r = changed[:, j] & ~np.isnan(X[:, j])
                if not r.any():
                    continue
                x, c, a = X[r, j], C[r, j], dev[r, j]
                within = np.abs(vals[None, :] - c[:, None]) <= a[:, None] + _tol(c)[:, None]
                dist = np.where(within, np.abs(vals[None, :] - x[:, None]), np.inf)
                pick = vals[np.argmin(dist, axis=1)]
                X[r, j] = np.where(within.any(axis=1), pick, c)
            for j in self.integer:
                if j in self.allowed:
                    continue
                r = changed[:, j]
                c = C[r, j]
                X[r, j] = np.where(c == np.round(c), c + np.trunc(X[r, j] - c), c)
            for j in self.nonneg:
                r = X[:, j] < 0
                X[r, j] = np.where(C[r, j] >= 0, 0.0, C[r, j])

            # 3. Anything still breaking an equality or ordering is reverted to clean.
            for _ in range(20):
                moved = False
                for g in self.eq_groups:
                    xg = X[:, g]
                    bad = np.any(np.abs(xg - xg[:, :1]) > _tol(xg[:, :1]), axis=1)
                    bad &= np.any(~np.isclose(xg, C[:, g], rtol=1e-12, atol=0.0)
                                  & ~np.isnan(xg), axis=1)
                    if bad.any():
                        X[np.ix_(bad, g)] = C[np.ix_(bad, g)]
                        moved = True
                for a, b in self.orderings:
                    bad = X[:, a] > X[:, b] + _tol(X[:, b])
                    bad &= ~(np.isclose(X[:, a], C[:, a], rtol=1e-12, atol=0.0)
                             & np.isclose(X[:, b], C[:, b], rtol=1e-12, atol=0.0))
                    if bad.any():
                        X[bad, a], X[bad, b] = C[bad, a], C[bad, b]
                        moved = True
                if not moved:
                    break
        return X

    # ---- reporting ----------------------------------------------------------------------
    def summary(self) -> dict:
        nm = self.names
        return {
            "constant": len(self.constant),
            "binary": len(self.binary),
            "categorical": len(self.allowed) - len(self.binary),
            "integer": len([j for j in self.integer if j not in self.allowed]),
            "nonneg": len(self.nonneg),
            "equality_groups": [[nm[j] for j in g] for g in self.eq_groups],
            "orderings": [f"{nm[a]} <= {nm[b]}" for a, b in self.orderings],
        }
