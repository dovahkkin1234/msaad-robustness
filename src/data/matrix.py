"""Turn a stream into NumPy arrays (for the attack experiments), and back.

``collect`` gathers the (features, label[, meta]) stream into a raw matrix with NaN for
missing values; ``running_minmax`` scales it row by row exactly as RunningMinMax does in the
dict pipeline (transform with the statistics seen so far, then learn); ``to_dict`` turns a
scaled row back into the dict a River model consumes.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


def collect(stream: Iterable, header: Optional[Sequence[str]] = None
            ) -> Tuple[List[str], np.ndarray, np.ndarray, Optional[List[str]]]:
    """Return (feature names, X_raw (n, d) with NaN = missing, y (n,), meta list or None).

    Feature order follows the CSV header when given (else first appearance), so the dicts
    rebuilt by ``to_dict`` keep the same key order as the loader's dicts.
    """
    rows, ys, metas = [], [], []
    seen: Dict[str, int] = {}
    for item in stream:
        x, y = item[0], item[1]
        rows.append(x)
        ys.append(int(y))
        if len(item) > 2:
            metas.append(item[2])
        for k in x:
            if k not in seen:
                seen[k] = len(seen)
    names = list(seen)
    if header is not None:
        pos = {str(h).strip(): i for i, h in enumerate(header)}
        names.sort(key=lambda k: (pos.get(k, len(pos)), seen[k]))
    col = {k: j for j, k in enumerate(names)}
    X = np.full((len(rows), len(names)), np.nan)
    for i, x in enumerate(rows):
        for k, v in x.items():
            X[i, col[k]] = v
    return names, X, np.asarray(ys, dtype=int), (metas if metas else None)


def running_minmax(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Scale rows in order with the running min/max seen so far (transform, then learn).

    Returns S (scaled values, NaN where missing) and R (the max - min range used for each
    scaled value; 0 means the scaler output 0 because the feature had not varied yet).
    Matches src.data.preprocessing.RunningMinMax.transform_then_learn exactly.
    """
    X = np.asarray(X, dtype=float)
    n, d = X.shape
    S = np.full((n, d), np.nan)
    R = np.full((n, d), np.nan)
    mn = np.full(d, np.nan)
    mx = np.full(d, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        for i in range(n):
            x = X[i]
            present = ~np.isnan(x)
            lo = np.where(np.isnan(mn), x, mn)
            hi = np.where(np.isnan(mx), x, mx)
            rng = hi - lo
            s = np.where(rng == 0, 0.0, (x - lo) / rng)
            S[i] = np.where(present, s, np.nan)
            R[i] = np.where(present, rng, np.nan)
            mn = np.where(present, np.fmin(mn, x), mn)
            mx = np.where(present, np.fmax(mx, x), mx)
    return S, R


def to_dict(row: np.ndarray, names: Sequence[str]) -> Dict[str, float]:
    """A scaled row as the {feature: value} dict a River model expects (NaN = left out)."""
    return {names[j]: float(v) for j, v in enumerate(row) if not np.isnan(v)}
