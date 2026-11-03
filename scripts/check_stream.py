"""Check what a configured stream contains before running grids on it (v14c).

For each dataset it loads the stream exactly as the experiments do (experiments/under_attack.py's
``load``, plus src/data/context.py's ``load_ctx`` for host addresses and timestamps), splits it
with the attack section's ``train_frac`` and prints:
  - rows, features, the train/test split and the DDoS share of each part;
  - where the attack rows sit in the replay, and the DDoS share in each tenth of the test stream;
  - for time-ordered data: the clock time each part covers, its replay rate, and what a label
    delay of 1,000 / 5,000 flows means in seconds (and 60 / 300 s in flows);
  - hosts: distinct sources and destinations, and the sources sending the DDoS flows;
  - warnings when a part lacks a class or the two loaders return different rows.
It trains nothing; it takes as long as loading the CSV twice (about a minute for CIC-IDS2017).

Usage (repo root, msaad environment active):
    python scripts\\check_stream.py --data cicids2017
    python scripts\\check_stream.py --data iotid20_campaign cicids2017
    python scripts\\check_stream.py --data cicids2017 --limit 50000
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))


def _pct(k: float, n: float) -> str:
    return "  n/a" if n == 0 else f"{100.0 * k / n:5.1f}%"


def _clock(t: float) -> str:
    return "?" if not np.isfinite(t) else f"{pd.to_datetime(t, unit='s'):%Y-%m-%d %H:%M:%S}"


def _delay_seconds(t: np.ndarray, d: int):
    """Median and 90th percentile of the time spanned by d consecutive flows."""
    t = t[np.isfinite(t)]
    if len(t) <= d:
        return None
    span = t[d:] - t[:-d]
    return float(np.median(span)), float(np.percentile(span, 90))


def _flows_within(t: np.ndarray, sec: float):
    """Median number of flows that arrive within `sec` seconds after a flow."""
    t = t[np.isfinite(t)]
    if len(t) < 2:
        return None
    ahead = np.searchsorted(t, t + sec, side="left") - np.arange(len(t))
    return float(np.median(ahead))


def check(d: str, cfg: dict, limit: int, frac: float) -> int:
    from under_attack import load
    from src.data.context import load_ctx

    print(f"\n=== {d}  (rows {limit:,}, train_frac {frac}) ===")
    names, X, y, meta = load(d, cfg, limit)
    n = len(y)
    n_tr = int(round(frac * n))
    status = 0
    if n == 0:
        print("  ERROR: the stream is empty (filter, window or path)")
        return 1
    y = np.asarray(y, int)
    ytr, yte = y[:n_tr], y[n_tr:]
    print(f"  {n:,} rows x {len(names)} features")
    print(f"  train {n_tr:,} rows: DDoS {_pct(ytr.sum(), len(ytr))}  |  "
          f"test {n - n_tr:,} rows: DDoS {_pct(yte.sum(), len(yte))}")
    if ytr.min() == ytr.max():
        print("  WARNING: the training part has one class only (the surrogate needs both classes)")
        status = 1
    if yte.sum() == 0:
        print("  ERROR: the test stream has no DDoS rows")
        status = 1
    att = np.flatnonzero(y == 1)
    if len(att):
        print(f"  attack rows span {100 * att[0] / n:.1f}% -> {100 * att[-1] / n:.1f}% of the replay "
              f"(split at {100 * frac:.0f}%)")
    tenths = np.array_split(np.arange(n - n_tr), 10)
    print("  test DDoS share by tenth: " + " ".join(
        "  -  " if len(ix) == 0 else f"{100 * yte[ix].mean():4.0f}%" for ix in tenths))
    if meta is not None:
        for part, sl in (("train", slice(0, n_tr)), ("test", slice(n_tr, n))):
            c = Counter(str(m) for m in meta[sl])
            print(f"  {part} classes: " + ", ".join(f"{k} {v:,}" for k, v in c.most_common(6)))

    ds = cfg["datasets"].get(d, {})
    if not ds.get("context"):
        print("  no `context` in the config: no host addresses or timestamps (stages 1-2 of the chain only)")
        return status
    _, _, y_c, _, ctx = load_ctx(d, cfg, limit, cfg["seed"], ROOT)
    if len(y_c) != n or not np.array_equal(np.asarray(y_c, int), y):
        print(f"  ERROR: the context loader returns different rows ({len(y_c):,} vs {n:,}); "
              "the experiments would misalign timestamps and hosts")
        return 1
    print("  context loader: same rows and labels (OK)")
    src, dst, t = ctx["src"], ctx["dst"], ctx["time"]
    fin = np.isfinite(t)
    if fin.any():
        ordered = bool(np.all(np.diff(t[fin]) >= 0))
        print(f"  timestamps: {100 * fin.mean():.1f}% parsed; replay in time order: {'yes' if ordered else 'NO'}")
        for part, sl in (("train", slice(0, n_tr)), ("test", slice(n_tr, n))):
            tp = t[sl][np.isfinite(t[sl])]
            if len(tp) > 1:
                dur = tp[-1] - tp[0]
                rate = (len(tp) - 1) / dur if dur > 0 else float("nan")
                print(f"  {part}: {_clock(tp[0])} -> {_clock(tp[-1])} ({dur / 60:.1f} min, "
                      f"{rate:.1f} flows/s in this replay)")
        if len(att):
            print(f"  DDoS rows: {_clock(t[att[0]])} -> {_clock(t[att[-1]])}")
        tte = t[n_tr:]
        for dd in (1000, 5000):
            r = _delay_seconds(tte, dd)
            if r:
                print(f"  label delay of {dd:,} flows in the test stream = {r[0]:.0f} s median "
                      f"({r[1]:.0f} s at the 90th percentile)")
        for sec in (60, 300):
            k = _flows_within(tte, sec)
            if k is not None:
                print(f"  label delay of {sec} s in the test stream = {k:,.0f} flows (median)")
    else:
        print("  timestamps: none parsed (check time_format)")
        status = 1
    print(f"  hosts: {len(set(src)):,} distinct sources, {len(set(dst)):,} distinct destinations")
    if len(att):
        top = Counter(src[att]).most_common(3)
        print("  DDoS flows by source: " + ", ".join(f"{h} {_pct(c, len(att)).strip()}" for h, c in top))
        ben = np.flatnonzero(y == 0)
        shared = set(src[att]) & set(src[ben])
        print(f"  sources sending both benign and DDoS flows: {len(shared)}"
              + (f" (e.g. {sorted(shared)[:3]})" if shared else ""))
    return status


def main() -> int:
    ap = argparse.ArgumentParser(description="Print what a configured stream contains (no training).")
    ap.add_argument("--data", nargs="+", required=True)
    ap.add_argument("--limit", type=int, default=None,
                    help="rows to replay (default: the attack section's limit, as the grids use)")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    args = ap.parse_args()
    cfg = yaml.safe_load(open(args.config))
    A = cfg.get("attack", {})
    limit = args.limit or A.get("limit", 30000)
    frac = A.get("train_frac", 0.67)
    status = 0
    for d in args.data:
        if d != "synthetic" and d not in cfg.get("datasets", {}):
            print(f"[check] unknown dataset {d!r}; choose from: {', '.join(cfg.get('datasets', {}))}")
            status = 1
            continue
        status |= check(d, cfg, limit, frac)
    print("\n[check] " + ("OK" if status == 0 else "see the WARNING / ERROR lines above"))
    return status


if __name__ == "__main__":
    sys.exit(main())
