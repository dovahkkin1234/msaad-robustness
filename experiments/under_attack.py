"""The base paper's Scenario 2 (MABTSE under adversarial attack), re-done with explicit choices.

What it does, for one dataset and one seed:
 1. Streams the dataset exactly as repro_baseline.py does (same filter, order and sampling),
    collects it into arrays and scales it with the same running min-max.
 2. Algorithm 1 split: the first `train_frac` of the stream trains MABTSE (learn only); the
    rest is the TEST stream, replayed under one or more label-feedback modes:
       online    predict, then learn the true label at once (Algorithm 1; the paper's setting)
       frozen    predict only: no labels arrive during the test
       delay:D   the true label of each flow arrives D flows later (D = 0 is "online")
       delaysec:T  (v14) the true label arrives T seconds later (time-ordered datasets with a
                 timestamp in their `context` config, e.g. the corrected CIC-IDS2017)
       self      no labels: the model learns its own prediction (self-training)
    Delayed and self-labelled runs cost as much as online ones, so they cover the clean and
    the raw attack_only scenarios only.
 3. Fits the attacker's differentiable surrogate (MLP or logistic regression) on the clean
    training part and crafts FGSM, BIM, PGD and C&W perturbations of the test stream
    (eps = 0.1 in the scaled feature space), perturbing only the DDoS flows ("attack_only",
    the realistic threat model) or every flow ("all", as the paper's untargeted attacks do).
 4. Mines domain constraints from the clean training flows, measures how many adversarial
    vectors are impossible as real traffic, and builds repaired ("feasible") versions of the
    attack_only attacks.
 5. Runs every scenario from the SAME trained model (deep copies with the same random state)
    and reports the paper's metrics plus end-to-end ones:
       asr           share of perturbed DDoS flows classified benign (evaded)
       clean_miss    share of the same flows missed when NOT perturbed (same learning mode)
       evasion_gain  asr - clean_miss: what the perturbation itself adds
       benign_flip   share of perturbed benign flows flagged as DDoS ("all" mode only)
       sur_success   share of perturbed flows that fool the surrogate itself (transfer check)
       drifts        drift detections per learner during the test stream (adaptation activity)

This is an offline robustness evaluation of our own reimplementation on public benchmark
CSVs; it does not generate or send any network traffic.

Usage (repo root, msaad environment active):
    python experiments\\under_attack.py --data iotid20
    python experiments\\under_attack.py --data iotid20 --seed 2 --attacks fgsm pgd --perturb attack_only
    python experiments\\under_attack.py --data iotid20 --learning delay:100 delay:1000 self --tag labels
Options: --seed K, --limit N, --train-frac F, --eps E, --attacks ..., --perturb ...,
         --surrogate mlp|lr, --learning MODE ..., --no-feasible, --no-frozen, --no-progress,
         --tag T (adds _T to the output name), --out PATH
Defaults come from the `attack:` section of configs/base.yaml.
Outputs results\\under_attack\\<data>_seed<k>[_<tag>].json and .csv (one row per scenario).
"""
from __future__ import annotations

import argparse
import collections
import copy
import csv
import datetime as dt
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.attacks.constraints import TYPES, ConstraintSet  # noqa: E402
from src.attacks.evasion import run_attack  # noqa: E402
from src.attacks.surrogate import Surrogate  # noqa: E402
from src.data.loaders import stream_csv, stream_synth  # noqa: E402
from src.data.matrix import collect, running_minmax, to_dict  # noqa: E402
from src.eval.metrics import BinaryMetrics  # noqa: E402
from src.models.mabtse import MABTSE  # noqa: E402
from src.models.pool import build_pool, drift_counts  # noqa: E402
from src.utils.seeding import seed_everything  # noqa: E402

ATTACKS = ("fgsm", "bim", "pgd", "cw")
MODES = ("attack_only", "all")
LEARNING = ("online", "frozen")   # default label-feedback modes


def parse_learning(mode: str):
    """Validate a label-feedback mode; return the delay for 'delay:D', else None
    ('delaysec:T' is validated here and handled by run_stream with timestamps)."""
    if mode in ("online", "frozen", "self"):
        return None
    if mode.startswith("delaysec:"):
        try:
            sec = float(mode.split(":", 1)[1])
        except ValueError:
            sec = -1.0
        if sec >= 0:
            return None
        raise SystemExit(f"[attack] bad label mode {mode!r}: delaysec:T needs T >= 0 seconds")
    if mode.startswith("delay:"):
        try:
            d = int(mode.split(":", 1)[1])
        except ValueError:
            d = -1
        if d >= 0:
            return d
    raise SystemExit(f"[attack] unknown --learning mode {mode!r}: use online, frozen, self or "
                     f"delay:D (D = flows of label delay, e.g. delay:100)")


def wants(sc: dict, learning: str) -> bool:
    """Which scenarios each label mode covers (delayed/self runs are as slow as online ones)."""
    if learning in ("online", "frozen"):
        return True
    return sc["variant"] == "clean" or (sc["perturb"] == "attack_only" and sc["variant"] == "raw")


def load(data: str, cfg: dict, limit: int):
    """Return (names, X_raw, y, meta) for the configured stream."""
    if data == "synthetic":
        return collect(stream_synth(n=limit, seed=cfg["seed"]))
    ds = cfg["datasets"][data]
    path = Path(ds["path"])
    path = path if path.is_absolute() else ROOT / path
    if not path.exists():
        sys.exit(f"[attack] dataset file not found: {path}\n"
                 f"         see SETUP.md (Steps 4-5) or fix the path in configs/base.yaml")
    header = [str(c).strip() for c in pd.read_csv(path, nrows=0).columns]
    meta_col = ds.get("class_col")
    meta_col = meta_col if meta_col in header else None
    stream = stream_csv(
        path=str(path), label_col=ds["label_col"], benign_values=ds["benign_values"],
        limit=limit, drop_cols=ds.get("drop_cols") or (),
        filter_col=ds.get("filter_col"), include_prefixes=ds.get("include_prefixes"),
        subsample=ds.get("subsample", "head"), order=ds.get("order", "file"),
        time_col=ds.get("time_col"), time_format=ds.get("time_format"), meta_col=meta_col,
        # v14c: honour the same row selection as src/data/context.py (CIC-IDS2017 window);
        # both keys are absent for IoTID20 and CICIoT2023, so their streams are unchanged.
        exclude_values=ds.get("exclude_values"), time_window=ds.get("time_window"),
    )
    return collect(stream, header)


def run_stream(model, S, y, names, learning: str, label: str, progress: bool, times=None):
    """Replay S on a copy of the model under one label-feedback mode.

    times: per-row timestamps in seconds, needed by 'delaysec:T'.
    Returns (predictions, drift detections per learner during this replay)."""
    m = copy.deepcopy(model)
    delay = parse_learning(learning)
    dsec = float(learning.split(":", 1)[1]) if learning.startswith("delaysec:") else None
    if dsec is not None and times is None:
        raise SystemExit("[attack] delaysec:T needs timestamps (a dataset with context.time)")
    learners = getattr(m, "learners", None)
    d0 = drift_counts(learners) if learners else {}
    preds = np.zeros(len(y), dtype=int)
    queue = collections.deque()
    it = range(len(y))
    if progress:
        it = tqdm(it, desc=label, unit="smp", leave=False)
    for i in it:
        x = to_dict(S[i], names)
        p = m.predict_one(x)
        preds[i] = 0 if p is None else int(p)
        if learning == "online":
            m.learn_one(x, int(y[i]))
        elif learning == "self":
            m.learn_one(x, int(preds[i]))
        elif delay is not None:
            queue.append((x, int(y[i])))
            if len(queue) > delay:
                xq, yq = queue.popleft()
                m.learn_one(xq, yq)
        elif dsec is not None:
            queue.append((x, int(y[i]), times[i]))
            while queue and times[i] - queue[0][2] >= dsec:
                xq, yq, _ = queue.popleft()
                m.learn_one(xq, yq)
    drifts = {k: v - d0.get(k, 0) for k, v in drift_counts(learners).items()} if learners else {}
    return preds, drifts


def share(mask: np.ndarray, hit: np.ndarray):
    """Share of rows in mask where hit is True (None if the mask is empty)."""
    k = int(mask.sum())
    return None if k == 0 else round(100.0 * float(hit[mask].mean()), 2)


def norms(S_adv: np.ndarray, S: np.ndarray, rows: np.ndarray) -> dict:
    d = np.nan_to_num(S_adv - S)[rows]
    if len(d) == 0:
        return {"linf_mean": None, "linf_max": None, "l2_mean": None, "changed_feats_mean": None}
    a = np.abs(d)
    return {"linf_mean": round(float(a.max(1).mean()), 4), "linf_max": round(float(a.max()), 4),
            "l2_mean": round(float(np.sqrt((d ** 2).sum(1)).mean()), 4),
            "changed_feats_mean": round(float((a > 1e-12).sum(1).mean()), 2)}


def build_scenarios(S_te, X_te, R_te, y_te, sur, cs, attacks, modes, eps, A, seed):
    """Clean + every attack x perturbation mode (+ repaired feasible versions of attack_only).

    Returns (scenarios, attack_info). Shared with experiments/radp_defense.py so both
    experiments face exactly the same perturbations for the same seed."""
    scen = [{"scenario": "clean", "attack": None, "perturb": None, "variant": "clean",
             "S": S_te, "rows": np.zeros(len(y_te), dtype=bool)}]
    attack_info = {}
    for atk in attacks:
        for mode in modes:
            rows = (y_te == 1) if mode == "attack_only" else np.ones(len(y_te), dtype=bool)
            t = time.perf_counter()
            S_adv = run_attack(atk, sur, S_te, y_te, rows, eps, params=A.get(atk), seed=seed)
            key = f"{atk}/{mode}"
            info = {"seconds": round(time.perf_counter() - t, 2),
                    "sur_success": share(rows, sur.predict(S_adv) != y_te), **norms(S_adv, S_te, rows)}
            scen.append({"scenario": key, "attack": atk, "perturb": mode, "variant": "raw",
                         "S": S_adv, "rows": rows})
            if cs is not None:
                # Back to raw feature space: x_raw' = x_raw + (scaled change) * (max - min).
                moved = np.abs(np.nan_to_num(S_adv - S_te)) > 1e-12
                unprod = (moved & (R_te == 0)).any(axis=1)
                X_adv = X_te + np.nan_to_num(S_adv - S_te) * np.where(R_te > 0, R_te, 0.0)
                viol = cs.violations(X_adv, X_te)
                viol["unproducible"] = unprod
                viol["any"] = viol["any"] | unprod
                info["infeasible"] = {k: share(rows, v) for k, v in viol.items()}
                if mode == "attack_only":
                    X_proj = cs.project(X_adv, X_te)
                    with np.errstate(invalid="ignore", divide="ignore"):
                        S_proj = np.where(R_te > 0, S_te + (X_proj - X_te) / R_te, S_te)
                    resid = cs.violations(X_proj, X_te)["any"]
                    S_proj[resid] = S_te[resid]          # no feasible point: send the flow as is
                    info["feasible"] = {"residual_infeasible": share(rows, resid),
                                        "sur_success": share(rows, sur.predict(S_proj) != y_te),
                                        **norms(S_proj, S_te, rows)}
                    scen.append({"scenario": f"{key}/feasible", "attack": atk, "perturb": mode,
                                 "variant": "feasible", "S": S_proj, "rows": rows})
            attack_info[key] = info
            print(f"[attack] {key}: surrogate fooled on {info['sur_success']}% of perturbed rows"
                  + (f"; infeasible {info['infeasible']['any']}%" if cs is not None else ""))
    return scen, attack_info


def main() -> int:
    ap = argparse.ArgumentParser(description="MABTSE under evasion attacks (paper Scenario 2).")
    ap.add_argument("--data", default="synthetic")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--train-frac", type=float, default=None)
    ap.add_argument("--eps", type=float, default=None)
    ap.add_argument("--attacks", nargs="+", default=None, choices=ATTACKS)
    ap.add_argument("--perturb", nargs="+", default=None, choices=MODES)
    ap.add_argument("--surrogate", default=None, choices=["mlp", "lr"])
    ap.add_argument("--learning", nargs="+", default=None,
                    help="label-feedback modes: online, frozen, self, delay:D (default: online frozen)")
    ap.add_argument("--tag", default=None, help="suffix for the default output name")
    ap.add_argument("--no-feasible", action="store_true")
    ap.add_argument("--no-frozen", action="store_true")
    ap.add_argument("--no-progress", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    valid = ["synthetic", *cfg.get("datasets", {})]
    if args.data not in valid:
        sys.exit(f"[attack] unknown --data {args.data!r}; choose from: {', '.join(valid)}")
    A = dict(cfg.get("attack", {}))
    if args.seed is not None:
        cfg["seed"] = args.seed
    seed = cfg["seed"]
    limit = args.limit or A.get("limit", 30000)
    train_frac = args.train_frac or A.get("train_frac", 0.67)
    eps = args.eps if args.eps is not None else A.get("eps", 0.1)
    attacks = args.attacks or A.get("attacks", list(ATTACKS))
    modes = args.perturb or A.get("perturb", list(MODES))
    sur_kind = args.surrogate or A.get("surrogate", "mlp")
    feasible = A.get("feasible", True) and not args.no_feasible
    learning_modes = list(args.learning or A.get("learning", list(LEARNING)))
    if args.no_frozen or not A.get("frozen", True):
        learning_modes = [m for m in learning_modes if m != "frozen"]
    for m in learning_modes:
        parse_learning(m)
    if not learning_modes:
        sys.exit("[attack] no label-feedback mode left to run")
    progress = not args.no_progress
    seed_everything(seed)
    t_start = time.perf_counter()

    # 1. Data, in stream order, scaled exactly as the dict pipeline does.
    names, X, y, meta = load(args.data, cfg, limit)
    times = None
    if any(m.startswith("delaysec:") for m in learning_modes):
        from src.data.context import load_ctx
        _, _, y_c, _, ctx = load_ctx(args.data, cfg, limit, cfg["seed"], ROOT)
        if ctx is None or not np.isfinite(ctx["time"]).any() or not np.array_equal(y_c, y):
            sys.exit("[attack] delaysec:T needs a dataset with a timestamp in its `context` config")
        times = ctx["time"]
        if not np.all(np.diff(times[np.isfinite(times)]) >= 0):
            sys.exit("[attack] delaysec:T needs a time-ordered stream (order: time or campaign)")
    n = len(y)
    n_tr = int(round(train_frac * n))
    if n_tr < 100 or n - n_tr < 100:
        sys.exit(f"[attack] stream too short for a train/test split ({n} rows)")
    S, R = running_minmax(X)
    te = slice(n_tr, n)
    S_te, X_te, R_te, y_te = S[te], X[te], R[te], y[te]
    meta_te = np.asarray(meta[n_tr:]) if meta is not None else None
    print(f"[attack] {args.data}: {n:,} rows x {len(names)} features; train {n_tr:,} / test "
          f"{n - n_tr:,} (test DDoS share {100 * y_te.mean():.1f}%), seed {seed}")

    # 2. Algorithm 1, lines 5-7: train MABTSE on the first part (learn only).
    model = MABTSE(build_pool(seed=seed), top_k=cfg["top_k"], eps=cfg["eps"],
                   mse_window=cfg["mse_window"], seed=seed)
    it = range(n_tr)
    if progress:
        it = tqdm(it, desc="train", unit="smp", leave=False)
    for i in it:
        model.learn_one(to_dict(S[i], names), int(y[i]))

    # 3. The attacker's surrogate, trained on the same clean (scaled) training rows.
    sur = Surrogate(kind=sur_kind, seed=seed).fit(S[:n_tr], y[:n_tr])
    sur_info = {"kind": sur_kind, "train_acc": round(100 * sur.accuracy(S[:n_tr], y[:n_tr]), 2),
                "test_acc": round(100 * sur.accuracy(S_te, y_te), 2)}
    print(f"[attack] surrogate {sur_kind}: train acc {sur_info['train_acc']}%, "
          f"clean test acc {sur_info['test_acc']}%")

    # 4. Constraints from clean training flows (raw space).
    cs = ConstraintSet.mine(X[:n_tr], names) if feasible else None
    if cs is not None:
        s = cs.summary()
        print(f"[attack] constraints: {s['constant']} constant, {s['binary']} binary, "
              f"{s['categorical']} categorical, {s['integer']} integer, {s['nonneg']} non-negative, "
              f"{len(s['equality_groups'])} equality groups, {len(s['orderings'])} orderings")

    # 5. Build the scenario inputs.
    scen, attack_info = build_scenarios(S_te, X_te, R_te, y_te, sur, cs, attacks, modes, eps, A, seed)

    # 6. Evaluate every scenario from the same trained model.
    runs = [(sc, mode) for sc in scen for mode in learning_modes if wants(sc, mode)]
    clean_preds = {}
    rows_out = []
    for sc, learning in runs:
        t = time.perf_counter()
        preds, drifts = run_stream(model, sc["S"], y_te, names, learning,
                                   label=f"{sc['scenario']} ({learning})", progress=progress,
                                   times=None if times is None else times[n_tr:])
        if sc["variant"] == "clean":
            clean_preds[learning] = preds
        bm = BinaryMetrics()
        for yt, yp in zip(y_te, preds):
            bm.update(int(yt), int(yp))
        r = {"scenario": sc["scenario"], "attack": sc["attack"], "perturb": sc["perturb"],
             "variant": sc["variant"], "learning": learning, **bm.as_dict()}
        att_rows = sc["rows"] & (y_te == 1)
        ben_rows = sc["rows"] & (y_te == 0)
        cp = clean_preds[learning]
        r["asr"] = share(att_rows, preds == 0)
        r["clean_miss"] = share(att_rows, cp == 0)
        r["evasion_gain"] = (None if r["asr"] is None else round(r["asr"] - r["clean_miss"], 2))
        r["benign_flip"] = share(ben_rows, preds == 1)
        r["clean_fpr_same_rows"] = share(ben_rows, cp == 1)
        if meta_te is not None and att_rows.any():
            r["asr_by_class"] = {str(c): share(att_rows & (meta_te == c), preds == 0)
                                 for c in sorted(set(meta_te[att_rows].tolist()))}
        r["drifts_total"] = int(sum(drifts.values()))
        r["drifts"] = drifts
        r["seconds"] = round(time.perf_counter() - t, 1)
        rows_out.append(r)
        print(f"[attack] {sc['scenario']:<26} {learning:<10} acc {r['accuracy']:6.2f}  "
              f"rec {r['recall']:6.2f}  f1 {r['f1']:6.2f}  fpr {r['fpr']:6.2f}  "
              f"asr {r['asr'] if r['asr'] is not None else '-':>6}  drifts {r['drifts_total']:>3}  "
              f"({r['seconds']}s)", flush=True)

    # 7. Save.
    tag = f"_{args.tag}" if args.tag else ""
    out = (Path(args.out) if args.out
           else ROOT / "results" / "under_attack" / f"{args.data}_seed{seed}{tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("river", "pandas", "numpy", "sklearn"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover
            versions[mod] = None
    settings = {"limit": limit, "train_frac": train_frac, "eps": eps, "attacks": attacks,
                "perturb": modes, "surrogate": sur_kind, "feasible": feasible,
                "learning": learning_modes,
                "attack_params": {a: A.get(a) for a in attacks}}
    result = {
        "dataset": args.data, "seed": seed, "n": n, "n_train": n_tr, "n_test": n - n_tr,
        "n_features": len(names), "test_ddos_share": round(100 * float(y_te.mean()), 2),
        "settings": settings, "surrogate": sur_info,
        "constraints": cs.summary() if cs is not None else None,
        "attacks": attack_info, "scenarios": rows_out,
        "config": {k: v for k, v in cfg.items() if k not in ("datasets", "attack")}
                  | ({"dataset_settings": cfg["datasets"][args.data]} if args.data != "synthetic" else {}),
        "versions": versions, "elapsed_s": round(time.perf_counter() - t_start, 1),
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(result, open(out, "w"), indent=2, default=str)
    flat = [{k: v for k, v in r.items() if k not in ("asr_by_class", "drifts")} for r in rows_out]
    with open(out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flat[0].keys()))
        w.writeheader()
        w.writerows(flat)
    print(f"\n[attack] done in {result['elapsed_s'] / 60:.1f} min; wrote {out} and {out.with_suffix('.csv').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
