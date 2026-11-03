"""Stream loaders.

Two sources:
  * ``stream_csv``   – stream a CSV as (features, label) pairs. Labels map to 1 = attack /
                       0 = benign; rows can be filtered by class prefix (the base paper used
                       only DDoS + benign rows) and subsampled evenly across the whole stream
                       (``subsample="stride"``) instead of taking the first rows.
  * ``stream_synth`` – a synthetic drifting binary stream so the whole pipeline can be
                       verified before the real datasets are downloaded.

Three replay orders (``order``):
  * "file"     – rows in file order. The public IoTID20 CSV is randomly shuffled with respect
                 to time, so this is a STATIONARY stream with no real drift. It mirrors the
                 base paper's setup (protocol P1).
  * "campaign" – attack rows in capture-time order, with benign rows spread evenly through
                 the stream (in their own time order) as a constant background. Attack
                 campaigns therefore arrive in their real order (genuine drift) while every
                 part of the stream still contains benign traffic (protocol P2).
  * "time"     – every row in capture-time order. On IoTID20 this is DEGENERATE: all benign
                 traffic was captured in the first week, so the stream is all-benign followed
                 by all-attack (a single class flip). Kept to document that finding.
"""
from __future__ import annotations

import math
import random
from typing import Dict, Iterator, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

Example = Tuple[Dict[str, float], int]

ORDERS = ("file", "campaign", "time")


def _to_float(v) -> Optional[float]:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def _norm(v) -> str:
    return str(v).strip().lower()


def _prefix_mask(s: pd.Series, prefixes: Tuple[str, ...]) -> np.ndarray:
    s = s.astype(str).str.strip().str.lower()
    mask = np.zeros(len(s), dtype=bool)
    for p in prefixes:
        mask |= s.str.startswith(p).to_numpy()
    return mask


def _count_kept(path: str, fcol: str, prefixes: Optional[Tuple[str, ...]],
                exclude: Optional[Set[str]] = None) -> int:
    """Count rows that pass the class filter, reading only the filter column (fast)."""
    total = 0
    for chunk in pd.read_csv(path, chunksize=200_000, low_memory=False,
                             usecols=lambda c: str(c).strip() == fcol):
        col = chunk.iloc[:, 0]
        keep = np.ones(len(col), bool) if prefixes is None else _prefix_mask(col, prefixes)
        if exclude:
            keep &= ~col.astype(str).str.strip().str.lower().isin(exclude).to_numpy()
        total += int(keep.sum())
    return total


def _even_positions(total: int, limit: Optional[int], subsample: str) -> Optional[Set[int]]:
    """Indices (into the kept rows) to yield; None = all kept rows up to ``limit``."""
    if limit is None or subsample == "head" or total <= limit:
        return None
    return {int(j * total / limit) for j in range(limit)}


class _RowConverter:
    """Turns one CSV record into (features, y[, meta]); reports skipped columns once."""

    def __init__(self, label_col: str, benign: Set[str], drop: Set[str],
                 meta_col: Optional[str] = None, context: Optional[Dict[str, str]] = None) -> None:
        self.label_col, self.benign, self.drop, self.meta_col = label_col, benign, drop, meta_col
        self.context = dict(context or {})
        self._reported = False

    def __call__(self, row: dict):
        y = 0 if _norm(row[self.label_col]) in self.benign else 1
        x: Dict[str, float] = {}
        dropped: List[str] = []
        for k, v in row.items():
            if k in self.drop:
                continue
            f = _to_float(v)
            if f is None:
                dropped.append(k)
                continue
            x[k] = f
        if dropped and not self._reported:
            print(f"[loaders] skipping non-numeric or NaN/inf values in "
                  f"{len(dropped)} column(s), e.g. {sorted(dropped)[:6]}")
            self._reported = True
        if not x:
            return None
        if self.context:          # v14: meta = dict with the class and the context columns
            meta = {k: str(row[c]) for k, c in self.context.items()}
            meta["class"] = str(row[self.meta_col]) if self.meta_col is not None else None
            return x, y, meta
        if self.meta_col is not None:
            return x, y, str(row[self.meta_col])
        return x, y


def stream_csv(
    path: str,
    label_col: str,
    benign_values: Sequence[str],
    limit: Optional[int] = None,
    drop_cols: Sequence[str] = (),
    filter_col: Optional[str] = None,
    include_prefixes: Optional[Sequence[str]] = None,
    subsample: str = "head",
    order: str = "file",
    time_col: Optional[str] = None,
    time_format: Optional[str] = None,
    meta_col: Optional[str] = None,
    context_cols: Optional[Dict[str, str]] = None,
    exclude_values: Optional[Sequence[str]] = None,
    time_window: Optional[Sequence[str]] = None,
):
    """Yield (features, y), or (features, y, meta) when ``meta_col`` is given.

    ``context_cols`` (v14): e.g. {"src": "Src_IP", "dst": "Dst_IP", "time": "Timestamp"}. The
    columns are never features; meta becomes a dict with these values plus "class" (the
    ``meta_col`` value), for the host-graph stage and label delays in seconds.
    ``exclude_values`` (v14): filter-column values to drop (exact, case-insensitive), e.g.
    "DDoS - Attempted" in the corrected CIC-IDS2017. ``time_window`` (v14, time/campaign
    order only): [start, end] timestamps (parsed like the time column); rows outside are
    dropped before sampling.

    y = 0 if the label is in ``benign_values`` (case-insensitive) else 1.
    ``include_prefixes``: keep only rows whose ``filter_col`` value (default: the label
    column) starts with one of the prefixes, e.g. ["DDoS", "Benign"].
    ``order``: "file", "campaign" or "time" (see the module docstring). "campaign" and
    "time" load the kept rows and sort them by ``time_col`` (parsed with ``time_format``).
    ``subsample`` (with ``limit``): "head" takes the first ``limit`` rows of the chosen
    order; "stride" takes ``limit`` rows evenly spaced across the whole ordered stream.
    ``meta_col``: also yield this column's raw value (e.g. the attack sub-category), for
    per-class analysis. It is never used as a feature.
    """
    if subsample not in ("head", "stride"):
        raise ValueError(f"subsample must be 'head' or 'stride', got {subsample!r}")
    if order not in ORDERS:
        raise ValueError(f"order must be one of {ORDERS}, got {order!r}")
    if order in ("time", "campaign") and not time_col:
        raise ValueError(f"order='{order}' needs time_col (and ideally time_format) in the config")
    benign = {_norm(b) for b in benign_values}
    fcol = filter_col or label_col
    prefixes = tuple(_norm(p) for p in include_prefixes) if include_prefixes else None
    exclude = {_norm(v) for v in exclude_values} if exclude_values else None
    drop = ({label_col, fcol, *drop_cols} | ({time_col} if time_col else set())
            | ({meta_col} if meta_col else set()) | set((context_cols or {}).values()))
    convert = _RowConverter(label_col, benign, drop, meta_col, context_cols)

    # Header check up front, so a wrong column name fails fast with a clear message.
    header = [str(c).strip() for c in pd.read_csv(path, nrows=0).columns]
    needed = ([label_col, fcol] + ([time_col] if order != "file" else [])
              + ([meta_col] if meta_col else []) + list((context_cols or {}).values()))
    missing = [c for c in dict.fromkeys(needed) if c not in header]
    if missing:
        raise KeyError(f"column(s) {missing} not in {path}. Available columns: {header}. "
                       f"Fix label_col/filter_col/time_col in configs/base.yaml.")

    if order != "file":
        yield from _stream_time_ordered(path, fcol, prefixes, time_col, time_format,
                                        limit, subsample, convert,
                                        campaign=(order == "campaign"),
                                        label_col=label_col, benign=benign,
                                        exclude=exclude, time_window=time_window)
        return

    # ---- file order: stream in chunks, never holding the whole file in memory ----------
    positions = None
    if subsample == "stride" and limit is not None:
        total = _count_kept(path, fcol, prefixes, exclude)
        positions = _even_positions(total, limit, subsample)
        if positions is not None:
            print(f"[loaders] file order, stride sampling: {total:,} rows pass the filter; "
                  f"taking {limit:,} evenly spaced (about 1 in {total / limit:.1f})")
        else:
            print(f"[loaders] {total:,} rows pass the filter (<= limit): using all of them")

    kept_idx = -1
    n = 0
    for chunk in pd.read_csv(path, chunksize=20_000, low_memory=False):
        chunk.columns = [str(c).strip() for c in chunk.columns]
        for row in chunk.to_dict("records"):
            if prefixes is not None and not _norm(row[fcol]).startswith(prefixes):
                continue
            if exclude and _norm(row[fcol]) in exclude:
                continue
            kept_idx += 1
            if positions is not None and kept_idx not in positions:
                continue
            ex = convert(row)
            if ex is None:
                continue
            yield ex
            n += 1
            if limit is not None and n >= limit:
                return


def _campaign_key(is_benign: np.ndarray) -> np.ndarray:
    """Sort key that spreads benign rows evenly among attack rows.

    Each class keeps its own (time) order: the k-th row of a class gets key (k + 0.5) / n_class.
    Sorting by this key interleaves the two classes uniformly over the whole stream.
    """
    key = np.empty(len(is_benign), dtype=float)
    n_b = int(is_benign.sum())
    n_a = len(is_benign) - n_b
    key[is_benign] = (np.arange(n_b) + 0.5) / max(n_b, 1)
    key[~is_benign] = (np.arange(n_a) + 0.5) / max(n_a, 1)
    return key


def _stream_time_ordered(path, fcol, prefixes, time_col, time_format, limit, subsample,
                         convert, campaign=False, label_col=None, benign=None, exclude=None,
                         time_window=None):
    frames = []
    for chunk in pd.read_csv(path, chunksize=100_000, low_memory=False):
        chunk.columns = [str(c).strip() for c in chunk.columns]
        if prefixes is not None:
            chunk = chunk[_prefix_mask(chunk[fcol], prefixes)]
        if exclude:
            chunk = chunk[~chunk[fcol].astype(str).str.strip().str.lower().isin(exclude).to_numpy()]
        frames.append(chunk)
    df = pd.concat(frames, ignore_index=True)
    ts = pd.to_datetime(df[time_col].astype(str), format=time_format, errors="coerce")
    bad = int(ts.isna().sum())
    if bad:
        print(f"[loaders] dropping {bad:,} row(s) whose {time_col} could not be parsed")
    df = df.assign(_t=ts)[ts.notna().to_numpy()]
    if time_window:
        t0 = pd.to_datetime(str(time_window[0]), format=time_format, errors="coerce")
        t1 = pd.to_datetime(str(time_window[1]), format=time_format, errors="coerce")
        if pd.isna(t0) or pd.isna(t1):                    # window written in ISO form
            t0, t1 = pd.Timestamp(str(time_window[0])), pd.Timestamp(str(time_window[1]))
        inside = ((df["_t"] >= t0) & (df["_t"] <= t1)).to_numpy()
        print(f"[loaders] time window {t0} -> {t1}: keeping {int(inside.sum()):,} of {len(df):,} rows")
        df = df[inside]
    df = df.sort_values("_t", kind="mergesort")  # stable: ties keep file order
    total = len(df)
    if total == 0:
        print("[loaders] no rows left after the filter and timestamp parsing")
        return

    # Even (stride) sampling is done on the time-sorted rows, BEFORE any campaign interleave:
    # each class is then sampled evenly along its own timeline and in its true proportion.
    # (Striding over the already-interleaved stream would alias with the regular benign
    # spacing and distort the class shares.)
    positions = _even_positions(total, limit, subsample)
    if positions is not None:
        df = df.iloc[sorted(positions)]
    elif limit is not None and not campaign:
        df = df.iloc[:limit]

    def benign_mask(frame):
        return frame[label_col].astype(str).str.strip().str.lower().isin(benign).to_numpy()

    if campaign:
        is_benign = benign_mask(df)
        n_b, n_a = int(is_benign.sum()), int((~is_benign).sum())
        if n_b and n_a:
            df = (df.assign(_k=_campaign_key(is_benign))
                    .sort_values("_k", kind="mergesort").drop(columns="_k"))
        if positions is None and limit is not None:
            df = df.iloc[:limit]
        att_t = df["_t"][~benign_mask(df)]
        span = (f"attacks {att_t.min():%Y-%m-%d} -> {att_t.max():%Y-%m-%d}"
                if len(att_t) else "no attack rows")
        how = (f"campaign order: {total:,} rows pass the filter; attack rows in capture-time "
               f"order ({span}) with benign rows spread evenly")
    else:
        how = (f"time order: {total:,} rows pass the filter, sorted by {time_col} "
               f"({df['_t'].iloc[0]:%Y-%m-%d} -> {df['_t'].iloc[-1]:%Y-%m-%d})")
    print(f"[loaders] {how}; replaying {len(df):,}"
          + (" evenly spaced" if positions is not None else ""))
    df = df.drop(columns="_t")
    for row in df.to_dict("records"):
        ex = convert(row)
        if ex is not None:
            yield ex


def stream_synth(
    n: int = 20_000,
    n_features: int = 12,
    drift_at: Sequence[float] = (0.33, 0.66),
    attack_rate: float = 0.5,
    seed: int = 42,
) -> Iterator[Example]:
    """Gaussian two-class stream with mean shifts (concept drift) at the given fractions."""
    rng = random.Random(seed)
    drift_points = sorted(int(d * n) for d in drift_at)
    regime = 0
    for i in range(n):
        if drift_points and regime < len(drift_points) and i >= drift_points[regime]:
            regime += 1
        y = 1 if rng.random() < attack_rate else 0
        # Attack-class mean moves each regime; benign stays near 0. Classes stay separable
        # but the boundary shifts, so drift detectors have something real to react to.
        shift = 2.0 + 1.5 * regime
        mu = shift if y == 1 else 0.0
        x = {f"f{j}": rng.gauss(mu if j % 2 == 0 else mu * 0.5, 1.0) for j in range(n_features)}
        yield x, y
