"""Stage S2 entry point — reproduce the clean-traffic MABTSE baseline.

Usage (run from the repo root):
    python experiments/repro_baseline.py --data synthetic
    python experiments/repro_baseline.py --data iotid20          # P1: file order (paper setup)
    python experiments/repro_baseline.py --data iotid20_time     # P2: capture-time order
    python experiments/repro_baseline.py --data ciciot2023
Options:
    --seed K      override the config seed (multi-seed runs)
    --limit N     override the dataset row limit (quick runs)
    --no-progress hide the progress bar (used by run_grid.py)

--data synthetic needs no files and verifies the whole pipeline end to end.
Each result JSON also stores the exact settings and library versions used.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import json
import platform
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.loaders import stream_csv, stream_synth  # noqa: E402
from src.eval.prequential import run_prequential  # noqa: E402
from src.models.mabtse import MABTSE  # noqa: E402
from src.models.pool import build_pool  # noqa: E402
from src.utils.seeding import seed_everything  # noqa: E402


def build_model(cfg: dict) -> MABTSE:
    pool = build_pool(seed=cfg["seed"])
    return MABTSE(
        pool, top_k=cfg["top_k"], eps=cfg["eps"],
        mse_window=cfg["mse_window"], seed=cfg["seed"],
    )


def get_stream(data: str, cfg: dict, limit_override=None):
    if data == "synthetic":
        return stream_synth(n=limit_override or 20_000, seed=cfg["seed"])
    ds = cfg["datasets"][data]
    path = Path(ds["path"])
    if not path.is_absolute():
        path = ROOT / path  # paths in base.yaml are relative to the repo root
    if not path.exists():
        sys.exit(f"[repro] dataset file not found: {path}\n"
                 f"        see SETUP.md (Steps 4-5) or fix the path in configs/base.yaml")
    return stream_csv(
        path=str(path), label_col=ds["label_col"], benign_values=ds["benign_values"],
        limit=ds.get("limit"), drop_cols=ds.get("drop_cols") or (),
        filter_col=ds.get("filter_col"), include_prefixes=ds.get("include_prefixes"),
        subsample=ds.get("subsample", "head"), order=ds.get("order", "file"),
        time_col=ds.get("time_col"), time_format=ds.get("time_format"),
        exclude_values=ds.get("exclude_values"), time_window=ds.get("time_window"),   # v14c
    )


def _versions() -> dict:
    out = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("river", "pandas", "numpy"):
        try:
            out[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover
            out[mod] = None
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="synthetic",
                    help="'synthetic' or any dataset name under 'datasets:' in the config "
                         "(e.g. iotid20, iotid20_time, ciciot2023)")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--seed", type=int, default=None, help="override the config seed")
    ap.add_argument("--limit", type=int, default=None, help="override the dataset row limit")
    ap.add_argument("--no-progress", action="store_true", help="hide the progress bar")
    ap.add_argument("--out", default=None, help="optional path to write the JSON result")
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    valid = ["synthetic", *cfg.get("datasets", {})]
    if args.data not in valid:
        sys.exit(f"[repro] unknown --data {args.data!r}; choose from: {', '.join(valid)}")
    if args.seed is not None:
        cfg["seed"] = args.seed
    if args.limit is not None and args.data != "synthetic":
        cfg["datasets"][args.data]["limit"] = args.limit
    seed_everything(cfg["seed"])

    model = build_model(cfg)
    stream = get_stream(args.data, cfg, limit_override=args.limit)
    result = run_prequential(
        model, stream, warmup=cfg["warmup"], scale=True,
        progress=not args.no_progress, log_every=cfg["log_every"],
    )
    result["dataset"] = args.data
    result["seed"] = cfg["seed"]

    print("\n=== MABTSE reproduction (clean) ===")
    for k in ("dataset", "seed", "n", "accuracy", "precision", "recall", "f1", "fpr",
              "fp", "fn", "majority_accuracy", "throughput_sps", "elapsed_s"):
        label = {"fpr": "false-alarm %", "fp": "false alarms", "fn": "missed attacks",
                 "majority_accuracy": "majority guess %"}.get(k, k)
        print(f"  {label:>16}: {result[k]}")

    snapshot = {k: v for k, v in cfg.items() if k != "datasets"}
    if args.data != "synthetic":
        snapshot["dataset_settings"] = copy.deepcopy(cfg["datasets"][args.data])
    result["config"] = snapshot
    result["versions"] = _versions()
    result["finished_at"] = dt.datetime.now().isoformat(timespec="seconds")

    default_name = f"repro_{args.data}" + (f"_seed{args.seed}" if args.seed is not None else "")
    out = args.out or str(ROOT / "results" / f"{default_name}.json")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(result, open(out, "w"), indent=2, default=str)
    print(f"\n  wrote {out}")


if __name__ == "__main__":
    main()
