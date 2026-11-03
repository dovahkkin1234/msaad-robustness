"""Per-seed values behind one line of a grid summary (v14c).

A grid summary prints mean +/- std over seeds. When the std is large (e.g. frozen transfer
evasion on CICIoT2023: 48.5 +/- 39.0 over 15 seeds) the mean hides the shape: this prints
every seed's value, the median and interquartile range, and how many seeds sit near either
end, so the paper can report the spread honestly (and the figures show per-seed dots).

Usage (repo root, msaad environment active):
    python scripts\\per_seed.py --exp attack --tag s15 --data ciciot2023 --scenario pgd/attack_only/feasible --learning frozen
    python scripts\\per_seed.py --exp loop --tag s15 --data iotid20 --scenario pgd/attack_only/feasible --learning poison:1.0 --where policy=guard:0.1
    python scripts\\per_seed.py --exp advtrain --tag s15 --data ciciot2023 --scenario clean --learning frozen --where at=at:pgd --metric fpr
Options:
    --exp      attack | loop | advtrain | radp | cascade (which results folder)
    --tag      the grid's tag ("" for untagged runs)
    --metric   any per-run field (default asr)
    --where    extra filters as key=value (policy=..., at=..., rad=..., chain=...)
    --low/--high  thresholds (in the metric's units) for the "near either end" count (10 / 90)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = {"attack": "attack_grid", "loop": "loop_grid", "advtrain": "advtrain_grid",
           "radp": "radp_grid", "cascade": "cascade_grid"}


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-seed values of one grid summary line.")
    ap.add_argument("--exp", required=True, choices=sorted(FOLDERS))
    ap.add_argument("--data", required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--learning", required=True)
    ap.add_argument("--metric", default="asr")
    ap.add_argument("--where", nargs="*", default=[], help="key=value filters")
    ap.add_argument("--low", type=float, default=10.0)
    ap.add_argument("--high", type=float, default=90.0)
    ap.add_argument("--results", default=str(ROOT / "results"))
    args = ap.parse_args()

    where = {}
    for w in args.where:
        if "=" not in w:
            print(f"[per-seed] --where needs key=value, got {w!r}")
            return 1
        k, v = w.split("=", 1)
        where[k] = v
    folder = Path(args.results) / FOLDERS[args.exp]
    vals = {}
    for f in sorted(folder.glob(f"{args.data}_seed*.json")):
        m = re.fullmatch(re.escape(args.data) + r"_seed(\d+)(?:_(.+))?\.json", f.name)
        if not m or (m.group(2) or "") != args.tag:
            continue
        try:
            run = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for s in run.get("scenarios", []):
            if s.get("scenario") != args.scenario or s.get("learning") != args.learning:
                continue
            if any(str(s.get(k)) != v for k, v in where.items()):
                continue
            v = s.get(args.metric)
            if isinstance(v, (int, float)):
                vals[int(m.group(1))] = float(v)
    if not vals:
        print(f"[per-seed] no matching rows in {folder} (tag {args.tag!r}); check --scenario, "
              f"--learning, --where and --tag against the summary CSV")
        return 1
    seeds = sorted(vals)
    a = np.array([vals[k] for k in seeds])
    label = f"{args.exp} {args.data} {args.scenario} {args.learning}" + "".join(f" {k}={v}" for k, v in where.items())
    print(f"[per-seed] {label}: {args.metric} for {len(a)} seed(s)")
    for k in seeds:
        print(f"  seed {k:>3}: {vals[k]:8.2f}")
    q1, med, q3 = np.percentile(a, [25, 50, 75])
    sd = a.std(ddof=1) if len(a) > 1 else 0.0
    print(f"  mean {a.mean():.2f} +/- {sd:.2f} | median {med:.2f}, IQR {q1:.2f}-{q3:.2f} | "
          f"min {a.min():.2f}, max {a.max():.2f}")
    lo, hi = int((a < args.low).sum()), int((a > args.high).sum())
    print(f"  seeds below {args.low:g}: {lo}  |  between: {len(a) - lo - hi}  |  above {args.high:g}: {hi}")
    if lo + hi >= 0.8 * len(a) and lo and hi:
        print("  -> most seeds sit at one of the two ends: report the median, the IQR and the per-seed "
              "values, not the mean alone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
