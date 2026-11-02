"""Inspect a dataset CSV and save a short report to send to Claude.

What it does: prints the file size, row count, every column with its type, the full value
counts of the label-like columns (e.g. IoTID20's Label/Cat/Sub_Cat, CICIoT2023's label),
and an ORDER CHECK: whether the rows are in time order and how the classes are spread
along the file. Our stream replays rows in file order, so this decides whether the stream
(and the concept drift in it) is realistic.

Usage (from the repo root, with the msaad environment active):
    python scripts\\inspect_dataset.py "data\\iotid20\\IoT_Network_Intrusion_Dataset.csv"
    python scripts\\inspect_dataset.py "data\\ciciot2023\\part-00000.csv"

The report is also saved to results\\inspect_<file>.txt — paste or attach that file.
It only reads the CSV; it never modifies or uploads anything.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd

SAMPLE_ROWS = 200_000   # rows sampled to detect columns and types
MAX_CLASSES = 60        # a text column with <= this many distinct values is "label-like"
N_BLOCKS = 10           # the order check splits the file into this many consecutive blocks
TS_FORMATS = [          # tried in order; CICFlowMeter writes the first style
    "%d/%m/%Y %I:%M:%S %p", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
    "%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
]


def _parse_timestamps(s: pd.Series) -> Tuple[pd.Series, str]:
    """Pick the format that parses the most of a sample, then parse the whole column."""
    sample = s.dropna().astype(str).head(2000)
    best_fmt, best_ok = None, 0
    for fmt in TS_FORMATS:
        ok = int(pd.to_datetime(sample, format=fmt, errors="coerce").notna().sum())
        if ok > best_ok:
            best_fmt, best_ok = fmt, ok
    if best_fmt is not None and best_ok >= 0.9 * max(len(sample), 1):
        return pd.to_datetime(s.astype(str), format=best_fmt, errors="coerce"), best_fmt
    return pd.to_datetime(s.astype(str), errors="coerce", dayfirst=True), "inferred"


def _mix(values: pd.Series, k: int) -> str:
    top = values.value_counts(normalize=True).head(k)
    return ", ".join(f"{name} {100 * share:.0f}%" for name, share in top.items())


def _order_check(full: pd.DataFrame, ts_col: Optional[str], class_col: Optional[str],
                 binary_col: Optional[str]) -> List[str]:
    out = ["", "ORDER CHECK  (is the file in time order? are the classes mixed along it?)"]
    n = len(full)
    ts, parsed, in_order = None, 0.0, 1.0
    if ts_col is not None:
        ts, fmt = _parse_timestamps(full[ts_col])
        parsed = float(ts.notna().mean())
        out.append(f"  timestamp column: {ts_col}   format: {fmt}   parsed: {100 * parsed:.1f}%")
        if parsed > 0:
            valid = ts.dropna()
            in_order = float((valid.diff().dropna() >= pd.Timedelta(0)).mean())
            out.append(f"  time range: {valid.min()}  ->  {valid.max()}")
            out.append(f"  consecutive rows in time order: {100 * in_order:.1f}%"
                       "   (100% = sorted by time; ~50% = randomly shuffled)")
    else:
        out.append("  no timestamp column (file order is the only order available)")

    if class_col is not None and n > 0:
        out.append(f"  class mix of '{class_col}' in {N_BLOCKS} consecutive blocks of the FILE:")
        edges = [int(i * n / N_BLOCKS) for i in range(N_BLOCKS + 1)]
        for b in range(N_BLOCKS):
            block = full[class_col].iloc[edges[b]:edges[b + 1]]
            out.append(f"    block {b + 1:>2} (rows {edges[b]:,}-{edges[b + 1] - 1:,}): {_mix(block, 3)}")

    # If the file is not already time-sorted, show what a time-ordered replay would contain.
    if ts is not None and parsed > 0.5 and in_order < 0.99 and class_col is not None:
        order = ts.dropna().sort_values(kind="mergesort").index
        m = len(order)
        edges = [int(i * m / N_BLOCKS) for i in range(N_BLOCKS + 1)]
        out.append(f"  the same rows in TIME order ({N_BLOCKS} blocks; what a time-sorted replay contains):")
        for b in range(N_BLOCKS):
            idx = order[edges[b]:edges[b + 1]]
            span = f"{ts[idx[0]]:%Y-%m-%d %H:%M} -> {ts[idx[-1]]:%Y-%m-%d %H:%M}"
            parts = []
            if binary_col is not None:
                parts.append(_mix(full.loc[idx, binary_col], 2))
            if class_col != binary_col:
                parts.append(_mix(full.loc[idx, class_col], 3))
            out.append(f"    block {b + 1:>2} [{span}]: " + " | ".join(parts))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect a dataset CSV for configuration.")
    ap.add_argument("path", help="path to the CSV file")
    args = ap.parse_args()

    p = Path(args.path)
    if not p.exists():
        print(f"[inspect] file not found: {p}")
        return 1

    sample = pd.read_csv(p, nrows=SAMPLE_ROWS, low_memory=False)
    sample.columns = [str(c).strip() for c in sample.columns]

    lines = [
        f"file: {p.name}",
        f"size_on_disk_MB: {p.stat().st_size / 1e6:.1f}",
        f"columns: {sample.shape[1]}",
        "",
        "COLUMNS  (name : dtype : distinct values in first "
        f"{len(sample):,} rows)",
    ]
    for c in sample.columns:
        lines.append(f"  {c} : {sample[c].dtype} : {sample[c].nunique(dropna=False)}")

    label_like = [c for c in sample.columns
                  if sample[c].dtype == object and sample[c].nunique(dropna=False) <= MAX_CLASSES]
    ts_col = next((c for c in sample.columns if c.lower() == "timestamp"), None)

    # Full pass over ONLY the label-like (+ timestamp) columns: exact counts and order.
    wanted = set(label_like) | ({ts_col} if ts_col else set())
    full = (pd.read_csv(p, usecols=lambda c: str(c).strip() in wanted, low_memory=False)
            if wanted else pd.DataFrame())
    full.columns = [str(c).strip() for c in full.columns]

    if label_like:
        lines += ["", f"TOTAL ROWS IN FILE: {len(full):,}", "",
                  "LABEL-LIKE COLUMNS  (full-file value counts)"]
        for c in label_like:
            lines.append(f"--- {c} ---")
            for k, v in full[c].value_counts(dropna=False).items():
                lines.append(f"  {k!r}: {v:,}")
        class_col = max(label_like, key=lambda c: full[c].nunique(dropna=False))
        binary_col = next((c for c in label_like if full[c].nunique(dropna=False) == 2), None)
        lines += _order_check(full, ts_col, class_col, binary_col)
    else:
        lines += ["", "No text label column found. Numeric columns with <= 10 values:"]
        for c in sample.columns:
            if sample[c].nunique(dropna=False) <= 10:
                lines.append(f"--- {c} ---")
                for k, v in sample[c].value_counts(dropna=False).items():
                    lines.append(f"  {k!r}: {v:,}")

    report = "\n".join(lines)
    print(report)
    out = Path(__file__).resolve().parents[1] / "results" / f"inspect_{p.stem}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(f"\n[inspect] report saved to: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
