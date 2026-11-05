"""Run many experiment runs in parallel (datasets x seeds), with logs and a summary.

What it does: launches one experiment script per (dataset, seed) combination, several at a
time (one CPU core each), saves every result as JSON plus a log, and finally prints
mean +/- std over seeds and writes a summary CSV. Finished runs are skipped when you start
it again, so an interrupted overnight grid simply resumes.

Six experiments:
  --exp repro   (default) experiments/repro_baseline.py — clean prequential reproduction;
                results in results\\grid, summary per dataset.
  --exp attack  experiments/under_attack.py — the under-attack scenarios; results in
                results\\attack_grid, summary per dataset x scenario x learning mode.
  --exp radp    experiments/radp_defense.py — the paper's Layer 1 (RADP) under the same
                attacks; results in results\\radp_grid, summary per RAD x scenario x learning.
  --exp loop    experiments/adaptation_loop.py — S4: label poisoning, selector steering and
                the audited / guarded defence; results in results\\loop_grid, summary per
                policy x scenario x label source.
  --exp cascade  experiments/cascade_eval.py — v14 chain of detectors (MABTSE -> online MLP ->
                host-graph GNN, drift focus, matched control); results in results\\cascade_grid.
  --exp advtrain  experiments/adv_training.py — adversarial-training baseline: MABTSE trained
                with adversarial copies of its DDoS training flows, under the same attacks;
                results in results\\advtrain_grid, summary per variant x scenario x label mode.

Usage (from the repo root, msaad environment active):
    python experiments\\run_grid.py --data iotid20 iotid20_campaign ciciot2023 --seeds 1 2 3 --jobs 4
    python experiments\\run_grid.py --exp attack --data iotid20 ciciot2023 --seeds 1 2 3 --jobs 4
    python experiments\\run_grid.py --exp attack --data iotid20 --seeds 1 2 3 --jobs 3 --tag labels --learning delay:100 delay:1000 self
    python experiments\\run_grid.py --exp radp --data iotid20 --seeds 1 2 3 --jobs 3
    python experiments\\run_grid.py --exp loop --data iotid20 ciciot2023 --jobs 3
    python experiments\\run_grid.py --exp advtrain --data iotid20 ciciot2023 --jobs 3
    python experiments\\run_grid.py --exp loop --data iotid20 ciciot2023 --jobs 3 --tag iw --policies iwstrict:0.05 iwstrict:0.1 iwstrict:0.2
Options:
    --limit N    rows per run (default: the config's limit for that experiment)
    --jobs J     runs at the same time (4 is safe with 16 GB RAM)
    --force      redo runs that already have a result
    --tag T      name this grid: results are <data>_seed<k>_T.json, the summary gets _T too
    --outdir D   where results go
    --push       afterwards, journal the grid in RUNS.md, commit the results and push them to
                 GitHub (scripts/push_run.py; one-time setup in SETUP.md, Step 15)
    --summarise  run nothing: rewrite summary_<exp>[_<tag>].csv from the result files on disk
                 (e.g. python experiments\\run_grid.py --exp loop --tag s15 --summarise)
Summaries (v14c) cover every dataset and seed with the grid's tag that is on disk, in config
order, so a grid on one dataset (e.g. CIC-IDS2017 with --tag s15) keeps the others' rows.
Every grid is also recorded in results\\grid_runs.jsonl (command, times, which runs worked).
Any other option (e.g. --learning, --attacks, --eps, --variants) is passed on unchanged to
the experiment script.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import csv
import datetime as dt
import json
import os
import re
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {"repro": ROOT / "experiments" / "repro_baseline.py",
           "attack": ROOT / "experiments" / "under_attack.py",
           "radp": ROOT / "experiments" / "radp_defense.py",
           "loop": ROOT / "experiments" / "adaptation_loop.py",
           "advtrain": ROOT / "experiments" / "adv_training.py",
           "cascade": ROOT / "experiments" / "cascade_eval.py"}
OUTDIRS = {"repro": ROOT / "results" / "grid", "attack": ROOT / "results" / "attack_grid",
           "radp": ROOT / "results" / "radp_grid", "loop": ROOT / "results" / "loop_grid",
           "advtrain": ROOT / "results" / "advtrain_grid",
           "cascade": ROOT / "results" / "cascade_grid"}
REPRO_METRICS = ["accuracy", "precision", "recall", "f1", "fpr", "throughput_sps"]
ATTACK_METRICS = ["accuracy", "recall", "f1", "fpr", "asr", "evasion_gain", "drifts_total"]
RADP_METRICS = ["rad_flag_ddos", "benign_deleted", "asr_no_radp", "e2e_asr", "recovered_acc",
                "blocked_acc", "benign_lost"]
ARMS = ["ARF-ADWIN", "ARF-DDM", "SRP-ADWIN", "SRP-DDM", "KNN-ADWIN"]
LOOP_METRICS = (["accuracy", "fpr", "asr", "poison_gain", "evasion_gain", "n_skipped"]
                + [f"sel_{a}" for a in ARMS]
                + ["audited_attacker_share", "fpr_frame_window", "fpr_after_window", "n_frame_learned",
                   "n_audited", "auc", "fpr_at_tpr99", "fpr_at_tpr995", "fpr_at_tpr999", "tpr_at_fpr01",
                   "tpr_at_fpr1"])
ADV_METRICS = ["accuracy", "fpr", "recall", "asr", "clean_miss", "evasion_gain"]
CASCADE_METRICS = ["asr", "fpr", "accuracy", "caught_s1_misses", "evaded_volume", "drift_coverage"]
PRINTED = {"loop": 6}   # the loop summary prints its first metrics; the CSV has all of them


def _name(data: str, seed: int, tag: str) -> str:
    return f"{data}_seed{seed}" + (f"_{tag}" if tag else "")


def _run_one(exp: str, data: str, seed: int, limit, outdir: Path, force: bool, tag: str, extra,
             config: str):
    out = outdir / f"{_name(data, seed, tag)}.json"
    log = outdir / "logs" / f"{_name(data, seed, tag)}.log"
    if out.exists() and not force:
        return data, seed, "skipped (already done)", 0.0
    cmd = [sys.executable, str(SCRIPTS[exp]), "--data", data, "--seed", str(seed),
           "--out", str(out), "--no-progress", "--config", str(config)]
    if limit:
        cmd += ["--limit", str(limit)]
    cmd += list(extra)
    # One thread per run: stops numeric libraries from oversubscribing the CPU.
    env = dict(os.environ, PYTHONUNBUFFERED="1", OMP_NUM_THREADS="1",
               MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1")
    t = time.perf_counter()
    with open(log, "w", encoding="utf-8") as fh:
        rc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, cwd=ROOT, env=env).returncode
    ok = rc == 0 and out.exists()
    return data, seed, "ok" if ok else f"FAILED (exit {rc}) - see {log}", time.perf_counter() - t


def _mean_std(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None, None
    return statistics.mean(vals), (statistics.stdev(vals) if len(vals) > 1 else 0.0)


def _write_csv(rows, path: Path) -> None:
    if not rows:
        return
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"\n  wrote {path}")


def _summarise_repro(datasets, seeds, outdir: Path, tag: str) -> None:
    rows = []
    print("\n=== Grid summary (mean +/- std over seeds) ===")
    print(f"  {'dataset':<22} {'seeds':>5}  " + "  ".join(f"{m:>16}" for m in REPRO_METRICS))
    for d in datasets:
        res = [json.load(open(p)) for s in seeds if (p := outdir / f"{_name(d, s, tag)}.json").exists()]
        if not res:
            continue
        row, cells = {"dataset": d, "n_seeds": len(res)}, []
        for m in REPRO_METRICS:
            mean, std = _mean_std([r.get(m) for r in res])
            row[f"{m}_mean"] = None if mean is None else round(mean, 3)
            row[f"{m}_std"] = None if std is None else round(std, 3)
            cells.append("-" if mean is None else f"{mean:8.2f} +/- {std:5.2f}")
        rows.append(row)
        print(f"  {d:<22} {len(res):>5}  " + "  ".join(f"{c:>16}" for c in cells))
    _write_csv(rows, outdir / ("summary" + (f"_{tag}" if tag else "") + ".csv"))


def _on_disk(outdir: Path, tag: str) -> dict:
    """{dataset: sorted seeds} of the result files with exactly this tag in a grid folder."""
    found = {}
    for f in outdir.glob("*.json") if outdir.exists() else []:
        m = re.fullmatch(r"(.+?)_seed(\d+)(?:_(.+))?\.json", f.name)
        if m and (m.group(3) or "") == tag:
            found.setdefault(m.group(1), set()).add(int(m.group(2)))
    return {d: sorted(s) for d, s in found.items()}


def _complete(datasets, seeds, outdir: Path, tag: str, order=()):
    """v14c: [(dataset, seeds)] for the summary: every dataset with result files of this tag
    (config order), each with all its seeds on disk. A grid run on one dataset (e.g. CIC-IDS2017
    with --tag s15) then keeps the other datasets' rows in summary_<exp>_<tag>.csv."""
    disk = _on_disk(outdir, tag)
    names = set(disk) | set(datasets)
    ordered = [d for d in order if d in names] + sorted(names - set(order))
    return [(d, sorted(set(disk.get(d, [])) | (set(seeds) if d in datasets else set()))) for d in ordered]


def _summarise_scenarios(datasets, seeds, outdir: Path, tag: str, exp: str, order=()) -> None:
    """Attack, RADP and loop grids: mean +/- std over seeds per
    (dataset, [RAD | policy,] scenario, learning), over every dataset and seed of this tag on disk."""
    metrics = {"attack": ATTACK_METRICS, "radp": RADP_METRICS, "loop": LOOP_METRICS,
               "advtrain": ADV_METRICS, "cascade": CASCADE_METRICS}[exp]
    key = {"radp": "rad", "loop": "policy", "advtrain": "at", "cascade": "chain"}.get(exp, "")
    shown = PRINTED.get(exp, len(metrics))
    rows = []
    print(f"\n=== {exp} grid summary (mean +/- std over seeds) ===")
    print(f"  {'dataset':<16} {key:<20} {'scenario':<28} {'learning':<11} "
          f"{'seeds':>5}  " + "  ".join(f"{m[:15]:>15}" for m in metrics[:shown]))
    for d, dseeds in _complete(datasets, seeds, outdir, tag, order):
        groups = defaultdict(list)
        for s in dseeds:
            p = outdir / f"{_name(d, s, tag)}.json"
            if p.exists():
                for r in json.load(open(p))["scenarios"]:
                    groups[(r.get(key, "") if key else "", r["scenario"], r["learning"])].append(r)
        for (k0, scenario, learning), res in groups.items():
            row = {"dataset": d, **({key: k0} if key else {}), "scenario": scenario,
                   "learning": learning, "n_seeds": len(res)}
            cells = []
            for m in metrics:
                mean, std = _mean_std([r.get(m) for r in res])
                row[f"{m}_mean"] = None if mean is None else round(mean, 3)
                row[f"{m}_std"] = None if std is None else round(std, 3)
                cells.append("-" if mean is None else f"{mean:7.2f} +/- {std:5.2f}")
            rows.append(row)
            print(f"  {d:<16} {k0:<20} {scenario:<28} {learning:<11} {len(res):>5}  "
                  + "  ".join(f"{c:>15}" for c in cells[:shown]))
    _write_csv(rows, outdir / (f"summary_{exp}" + (f"_{tag}" if tag else "") + ".csv"))


def _record(args, extra, datasets, outdir: Path, started: str, runs, minutes: float) -> None:
    """Append this grid to results/grid_runs.jsonl; scripts/push_run.py turns it into a RUNS.md entry."""
    try:
        out_rel = outdir.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        out_rel = str(outdir)
    rec = {"started_at": started, "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
           "exp": args.exp, "tag": args.tag, "datasets": datasets, "seeds": args.seeds, "jobs": args.jobs,
           "limit": args.limit, "extra": list(extra), "outdir": out_rel,
           "command": "python " + subprocess.list2cmdline(sys.argv),
           "runs": sorted(runs, key=lambda r: (r["data"], r["seed"])),
           "failed": sum(1 for r in runs if r["status"].startswith("FAILED")), "minutes": round(minutes, 1)}
    path = ROOT / "results" / "grid_runs.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description="Run an experiment over datasets x seeds in parallel.")
    ap.add_argument("--exp", default="repro", choices=sorted(SCRIPTS))
    ap.add_argument("--data", nargs="+", default=None, help="datasets to run (not needed with --summarise)")
    ap.add_argument("--summarise", action="store_true",
                    help="run nothing: rewrite summary_<exp>[_<tag>].csv from every result file of "
                         "this tag on disk (all datasets and seeds)")
    ap.add_argument("--seeds", nargs="+", type=int, default=[1, 2, 3])
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--tag", default="", help="name this grid's result files")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--push", action="store_true",
                    help="afterwards, journal, commit and push the results (scripts/push_run.py)")
    args, extra = ap.parse_known_args()
    if extra and args.exp == "repro":
        print(f"[grid] options {extra} are not used by the repro experiment")
        return 1

    cfg = yaml.safe_load(open(args.config))
    known = cfg.get("datasets", {})
    if args.summarise:   # v14c: summary only, from the result files already on disk
        outdir = Path(args.outdir) if args.outdir else OUTDIRS[args.exp]
        disk = _on_disk(outdir, args.tag)
        if not disk:
            print(f"[grid] no result files with tag {args.tag!r} in {outdir}")
            return 1
        print(f"[grid] summarising {args.exp}{' [' + args.tag + ']' if args.tag else ''} from disk: "
              + ", ".join(f"{d} ({len(s)} seeds)" for d, s in disk.items()))
        if args.exp == "repro":
            names = [d for d in known if d in disk] + sorted(set(disk) - set(known))
            _summarise_repro(names, sorted({s for v in disk.values() for s in v}), outdir, args.tag)
        else:
            _summarise_scenarios([], [], outdir, args.tag, args.exp, order=list(known))
        return 0
    if not args.data:
        print("[grid] --data is required (or use --summarise)")
        return 1
    datasets = []
    for d in args.data:  # fail fast, before launching anything
        if d == "synthetic":
            datasets.append(d)
            continue
        if d not in known:
            print(f"[grid] unknown dataset {d!r}; choose from: synthetic, {', '.join(known)}")
            return 1
        path = Path(known[d]["path"])
        path = path if path.is_absolute() else ROOT / path
        if not path.exists():
            print(f"[grid] skipping {d}: data file not found ({path})")
            continue
        datasets.append(d)
    if not datasets:
        print("[grid] nothing to run")
        return 1

    outdir = Path(args.outdir) if args.outdir else OUTDIRS[args.exp]
    (outdir / "logs").mkdir(parents=True, exist_ok=True)
    combos = [(d, s) for d in datasets for s in args.seeds]
    print(f"[grid] {args.exp}{' [' + args.tag + ']' if args.tag else ''}: {len(combos)} runs "
          f"({', '.join(datasets)} x seeds {args.seeds}), {args.jobs} at a time; logs in {outdir / 'logs'}"
          + (f"\n[grid] passing on to each run: {' '.join(extra)}" if extra else ""))
    t0 = time.perf_counter()
    started = dt.datetime.now().isoformat(timespec="seconds")
    failed = 0
    runs = []
    with cf.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(_run_one, args.exp, d, s, args.limit, outdir, args.force,
                               args.tag, extra, args.config) for d, s in combos]
        for fut in cf.as_completed(futures):
            d, s, status, secs = fut.result()
            failed += status.startswith("FAILED")
            runs.append({"data": d, "seed": s, "status": status, "minutes": round(secs / 60, 1)})
            print(f"[grid] {d:<22} seed {s:<3} {status}"
                  + (f"  ({secs / 60:.1f} min)" if secs else ""), flush=True)
    print(f"[grid] all done in {(time.perf_counter() - t0) / 60:.1f} min, {failed} failed")
    minutes = (time.perf_counter() - t0) / 60
    if args.exp == "repro":
        _summarise_repro(datasets, args.seeds, outdir, args.tag)
    else:
        _summarise_scenarios(datasets, args.seeds, outdir, args.tag, args.exp, order=list(known))
    _record(args, extra, datasets, outdir, started, runs, minutes)
    if args.push:
        print("\n[grid] --push: journalling, committing and pushing the results")
        subprocess.run([sys.executable, str(ROOT / "scripts" / "push_run.py")], cwd=ROOT)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
