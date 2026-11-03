"""Streams with host context (source / destination address, timestamp) -- v14.

``load_ctx`` returns the same rows, features and labels as experiments/under_attack.py's
``load`` (same filter, order and sampling), plus a context dict for datasets whose config
has a ``context`` entry, e.g. ``context: {src: Src_IP, dst: Dst_IP, time: Timestamp}``:
    src, dst   host addresses as strings (for the host graph; never features)
    time       seconds since 1970 (NaN when missing), for label delays in seconds
Datasets without a ``context`` entry return context None. ``synth_ctx`` is a synthetic
stream with hosts and two attack campaigns, for the self-checks.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

from .loaders import stream_csv, stream_synth
from .matrix import collect


def synth_ctx(n: int, seed: int):
    """Synthetic stream with hosts: 30 clients x 10 servers (benign), 3 bots -> 1 victim
    (attack), in time order. Attack bursts arrive in two campaigns so drift exists."""
    rng = np.random.default_rng(seed)
    d = 12
    t = np.arange(n, dtype=float)
    phase = (t > n * 0.3) & (t < n * 0.55) | (t > n * 0.75)
    y = (rng.random(n) < np.where(phase, 0.7, 0.15)).astype(int)
    X = rng.normal(0.0, 1.0, size=(n, d))
    X[y == 1] += rng.normal(1.6, 0.4, size=(int(y.sum()), d)) * (rng.random((int(y.sum()), d)) < 0.5)
    src = np.where(y == 1, rng.integers(100, 103, n), rng.integers(0, 30, n))
    dst = np.where(y == 1, 200, rng.integers(30, 40, n))
    names = [f"f{j}" for j in range(d)]
    return names, X, y, None, {"src": src.astype(str), "dst": dst.astype(str), "time": t}


def load_ctx(data: str, cfg: dict, limit: int, seed: int, root: Path):
    """(names, X, y, class meta, context dict or None). Context: src/dst host strings and
    time in seconds (NaN when missing)."""
    if data == "synthetic":
        return synth_ctx(limit, seed)
    ds = cfg["datasets"][data]
    cc = ds.get("context")
    path = Path(ds["path"])
    path = path if path.is_absolute() else root / path
    if not path.exists():
        sys.exit(f"[cascade] dataset file not found: {path}")
    header = [str(c).strip() for c in pd.read_csv(path, nrows=0).columns]
    meta_col = ds.get("class_col") if ds.get("class_col") in header else None
    stream = stream_csv(
        path=str(path), label_col=ds["label_col"], benign_values=ds["benign_values"], limit=limit,
        drop_cols=ds.get("drop_cols") or (), filter_col=ds.get("filter_col"),
        include_prefixes=ds.get("include_prefixes"), subsample=ds.get("subsample", "head"),
        order=ds.get("order", "file"), time_col=ds.get("time_col"), time_format=ds.get("time_format"),
        meta_col=meta_col, context_cols=cc or None, exclude_values=ds.get("exclude_values"),
        time_window=ds.get("time_window"))
    names, X, y, metas = collect(stream, header)
    if not cc:
        return names, X, y, metas, None
    src = np.array([m.get("src", "?") for m in metas], dtype=object).astype(str)
    dst = np.array([m.get("dst", "?") for m in metas], dtype=object).astype(str)
    tt = pd.to_datetime(pd.Series([m.get("time") for m in metas]), format=ds.get("time_format"), errors="coerce")
    times = (tt - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy(dtype=float)
    cls = [m.get("class") for m in metas] if meta_col else None
    return names, X, y, cls, {"src": src, "dst": dst, "time": times}


