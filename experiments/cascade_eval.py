"""A chain of detectors: can later stages catch the flows the first one misses?

The chain (cascade). Stage 1 is MABTSE (the paper's detector, trained exactly as in
under_attack.py, so its verdicts reproduce the attack grid). Stage 2 is an online MLP on the
same scaled flow features (src/models/online_mlp.py). Stage 3 is a graph neural network over
the host graph of the last W flows (src/models/graph_stage.py), in three versions:
    gnn_full    graph attention over the whole window graph
    gnn_drift   the same trained network, but only the 2-hop neighbourhoods of hosts whose
                traffic drifted (per-host ADWIN) or that are new are encoded and scored;
                other flows abstain ("the drifting nodes' graphs")
    ctx         the matched control: the same node features and scorer, per-node MLP blocks
                instead of attention (no message passing)
A later stage only re-checks flows the earlier stages let through, with its threshold set
so that it adds at most --alpha false alarms on the benign flows of the second half of the
training stream (prequential scores, never test data). Stages learn independently from the
same released labels, so every chain is evaluated from one replay per condition.

Attacker: as under_attack.py (MLP surrogate, attack_only, raw and repaired), plus two
graph-aware adaptations of the repaired PGD attack against stage 3:
    spoof:k     each attacker flow gets a random source address from a pool of k addresses
                per real attacker host (spreads the flood over many sources)
    thin:rho    the attacker sends only a share rho of its flows (slows down); evaded volume =
                rho x ASR is what still reaches the victim, relative to the full attack
Label conditions (--conditions): "frozen" (no labels) or "<labels>|<label source>|<policy>",
e.g. "delay:1000|true|vanilla", "delay:1000|poison:1.0|strict:0.1"; label modes online,
delay:D (flows) and delaysec:T (seconds, needs timestamps in time order); label sources true /
poison:q; policies vanilla / strict:a / iwstrict:a (adaptation_loop.py). Learning conditions
run on the clean, repaired PGD and repaired C&W scenarios; adaptive scenarios run frozen.

Datasets without host addresses (the Kaggle CICIoT2023 copy) run stages 1-2 only. Use the
time-ordered or campaign-ordered streams for the graph (iotid20_campaign, cicids2017): the
file order of IoTID20 is shuffled, so its windows are not time windows.

Usage (repo root, msaad environment active; needs PyTorch, see SETUP.md Step 18):
    python experiments\\cascade_eval.py --data iotid20_campaign
    python experiments\\cascade_eval.py --data ciciot2023 --seed 2
Outputs results\\cascade\\<data>_seed<k>[_<tag>].json and .csv (one row per scenario x
condition x chain).
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
sys.path.insert(0, str(ROOT / "experiments"))

from adaptation_loop import _mask, iw_copies, parse_policy, parse_source  # noqa: E402
from under_attack import ATTACKS, build_scenarios, share  # noqa: E402
from src.attacks.constraints import ConstraintSet  # noqa: E402
from src.attacks.surrogate import Surrogate  # noqa: E402
from src.data.context import load_ctx  # noqa: E402
from src.data.matrix import running_minmax, to_dict  # noqa: E402
from src.models.graph_stage import GraphStage, HostGraphs  # noqa: E402
from src.models.mabtse import MABTSE  # noqa: E402
from src.models.online_mlp import OnlineMLP, torch_setup  # noqa: E402
from src.models.pool import build_pool  # noqa: E402
from src.utils.seeding import seed_everything  # noqa: E402

CONDITIONS = ("frozen", "delay:1000|true|vanilla", "delay:1000|poison:1.0|vanilla",
              "delay:1000|poison:1.0|strict:0.1")
ADAPTIVE = ("spoof:10", "thin:0.25")
STAGE3 = ("gnn_full", "gnn_drift", "ctx")


def parse_condition(c: str):
    """'frozen' -> ('frozen', None, None); 'mode|labels|policy' -> parts (validated)."""
    if c == "frozen":
        return "frozen", "true", "vanilla"
    parts = c.split("|")
    if len(parts) != 3:
        raise SystemExit(f"[cascade] bad --conditions value {c!r}: use frozen or mode|labels|policy, "
                         "e.g. delay:1000|poison:1.0|strict:0.1")
    mode, lab, pol = parts
    if not (mode == "online" or mode.startswith("delay:") or mode.startswith("delaysec:")):
        raise SystemExit(f"[cascade] bad label mode {mode!r}: online, delay:D or delaysec:T")
    parse_source(lab)
    kind = parse_policy(pol)[0]
    if kind not in ("vanilla", "strict", "iwstrict"):
        raise SystemExit(f"[cascade] policy {pol!r}: the chain supports vanilla, strict:a and iwstrict:a")
    return mode, lab, pol


# ---- one replay --------------------------------------------------------------------------
def replay(sc, cond, n_tr, S_tr, src_tr, dst_tr, t_tr, models, names, seed, W, B, progress):
    """Run the chain over one scenario's test stream under one label condition.
    Returns per-flow arrays: v1 (stage-1 verdict), p2, and stage-3 scores per variant."""
    mode, lab_src, pol = cond
    kind, a, cap = parse_policy(pol)
    q = parse_source(lab_src)[0]
    learn = mode != "frozen"
    delay = 0 if mode == "online" else (int(mode.split(":")[1]) if mode.startswith("delay:") else None)
    dsec = float(mode.split(":")[1]) if mode.startswith("delaysec:") else None
    S_te, y_te, att = sc["S"], sc["y"], sc["att"]
    n = len(y_te)
    pos = sc["pos"]                                     # original test positions (masks are paired)
    flip = _mask(seed, 7, q, sc["n_orig"])[pos]
    audit = _mask(seed, 11, a, sc["n_orig"])[pos] if kind != "vanilla" else np.zeros(n, bool)
    m1, m2 = copy.deepcopy(models["m1"]), copy.deepcopy(models["m2"])
    g3 = {k: copy.deepcopy(v) for k, v in models["g3"].items()}
    graph = bool(g3)
    if graph:
        S_full = np.vstack([S_tr, S_te])
        hg = HostGraphs(S_full, np.concatenate([src_tr, sc["src"]]), np.concatenate([dst_tr, sc["dst"]]), W)
        for v in g3.values():
            v.bind(hg)
    times = sc.get("time")
    v1 = np.zeros(n, dtype=int)
    p2 = np.zeros(n)
    p3 = {k: np.full(n, np.nan) for k in STAGE3} if graph else {}
    pending = collections.deque()                       # (i, label, truth, audited) awaiting release
    gbuf = collections.defaultdict(list)                # frame start -> [(abs row, label, weight)]
    cnt = collections.Counter()

    def apply(j, lab, truth, aud):
        x = to_dict(S_te[j], names)
        if kind == "vanilla":
            m1.learn_one(x, lab)
            m2.learn(S_te[j], lab)
            gl, gw = lab, 1.0
            cnt["poisoned_learned"] += int(lab != truth)
        elif aud:
            reps = iw_copies(a, cap) if (kind == "iwstrict" and truth == 0) else 1
            m1.learn_one(x, truth, update_selector=True)
            for _ in range(reps - 1):
                m1.learn_one(x, truth, update_selector=False)
            m2.learn(S_te[j], truth, weight=reps)
            gl, gw = truth, float(reps)
            cnt["audited"] += 1
        elif lab == 1:
            m1.learn_one(x, 1, update_selector=False)
            m2.learn(S_te[j], 1)
            gl, gw = 1, 1.0
        else:
            cnt["skipped"] += 1
            cnt["poisoned_blocked"] += int(lab != truth)
            return
        if graph:
            fs = n_tr + (j // B) * B
            gbuf[fs].append((n_tr + j, gl, gw))
        cnt["learn"] += 1

    frames = range(0, n, B)
    if progress:
        frames = tqdm(frames, desc=f"{sc['scenario']} {'|'.join(cond)}", unit="frame", leave=False)
    for f in frames:
        rows = np.arange(f, min(f + B, n))
        if graph:
            absrows = n_tr + rows
            r_g = g3["gnn"].score_frame(n_tr + f, absrows, focus=("full", "drift"), update_drift=True)
            p3["gnn_full"][rows], p3["gnn_drift"][rows] = r_g["full"], r_g["drift"]
            p3["ctx"][rows] = g3["ctx"].score_frame(n_tr + f, absrows, focus=("full",), update_drift=False)["full"]
        for i in rows:
            x = to_dict(S_te[i], names)
            proba = m1.predict_proba_one(x)
            pr = max(proba, key=proba.get) if proba else None
            v1[i] = 0 if pr is None else int(pr)
            p2[i] = m2.predict_proba(S_te[i])
            if not learn:
                continue
            truth = int(y_te[i])
            lab = 0 if (att[i] and flip[i]) else truth
            pending.append((i, lab, truth, bool(audit[i])))
            while pending:
                j = pending[0][0]
                ready = ((i - j) >= delay) if delay is not None else (times[i] - times[j] >= dsec)
                if not ready:
                    break
                apply(*pending.popleft())
        if graph and gbuf:                               # one step per frame with released labels
            for fs in sorted(gbuf):
                items = gbuf.pop(fs)
                r = np.array([t[0] for t in items])
                yy = np.array([t[1] for t in items])
                ww = np.array([t[2] for t in items])
                for k in ("gnn", "ctx"):
                    g3[k].step(fs, r, yy, ww)
    return {"v1": v1, "p2": p2, "p3": p3, "counts": cnt}


def chains(out, tau, graph):
    """Verdict arrays for every stage and chain."""
    v1, p2, p3 = out["v1"], out["p2"], out["p3"]
    ge = lambda p, t: np.nan_to_num(p, nan=-1.0) >= t  # noqa: E731  (abstained = not flagged)
    c = {"S1": v1 == 1, "S2": ge(p2, 0.5), "S1+S2": (v1 == 1) | ge(p2, tau["p2"])}
    if graph:
        for k in STAGE3:
            tk = tau["gnn"] if k.startswith("gnn") else tau["ctx"]
            c[f"S3:{k}"] = ge(p3[k], 0.5)
            c[f"S1+S3:{k}"] = (v1 == 1) | ge(p3[k], tk)
            c[f"S1+S2+S3:{k}"] = (v1 == 1) | ge(p2, tau["p2"]) | ge(p3[k], tk)
    return c


def metrics(flag, y, att, s1):
    ben = y == 0
    tp = int((flag & (y == 1)).sum())
    tn = int((~flag & ben).sum())
    acc = 100.0 * (tp + tn) / max(len(y), 1)
    missed1 = att & ~s1
    return {"accuracy": round(acc, 3), "fpr": share(ben, flag), "recall": share(y == 1, flag),
            "asr": share(att, ~flag), "caught_s1_misses": share(missed1, flag)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Chain of detectors (MABTSE -> online MLP -> host-graph GNN).")
    ap.add_argument("--data", default="synthetic")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--attacks", nargs="+", default=None, choices=ATTACKS)
    ap.add_argument("--variants", nargs="+", default=None, choices=("raw", "feasible"))
    ap.add_argument("--conditions", nargs="+", default=None)
    ap.add_argument("--adaptive", nargs="+", default=None, help="spoof:k and/or thin:rho (graph-aware attacker)")
    ap.add_argument("--alpha", type=float, default=None, help="false alarms each later stage may add (default 0.01)")
    ap.add_argument("--window", type=int, default=None)
    ap.add_argument("--frame", type=int, default=None)
    ap.add_argument("--epochs", type=int, default=None)
    ap.add_argument("--no-graph", action="store_true")
    ap.add_argument("--no-progress", action="store_true")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    valid = ["synthetic", *cfg.get("datasets", {})]
    if args.data not in valid:
        sys.exit(f"[cascade] unknown --data {args.data!r}; choose from: {', '.join(valid)}")
    A = dict(cfg.get("attack", {}))
    C = dict(cfg.get("cascade", {}))
    if args.seed is not None:
        cfg["seed"] = args.seed
    seed = cfg["seed"]
    limit = args.limit or A.get("limit", 30000)
    train_frac = A.get("train_frac", 0.67)
    eps = A.get("eps", 0.1)
    attacks = args.attacks or C.get("attacks", ["pgd", "cw"])
    variants = args.variants or C.get("variants", ["raw", "feasible"])
    conds = [parse_condition(c) for c in (args.conditions or C.get("conditions", list(CONDITIONS)))]
    adaptive = list(args.adaptive if args.adaptive is not None else C.get("adaptive", list(ADAPTIVE)))
    alpha = args.alpha if args.alpha is not None else float(C.get("alpha", 0.01))
    W = args.window or int(C.get("window", 800))
    B = args.frame or int(C.get("frame", 64))
    epochs = args.epochs or int(C.get("epochs", 2))
    progress = not args.no_progress
    seed_everything(seed)
    torch_setup(seed)
    t0 = time.perf_counter()

    # 1. Data (+ host context), split, scaling.
    names, X, y, meta, ctx = load_ctx(args.data, cfg, limit, seed, ROOT)
    graph = ctx is not None and not args.no_graph
    n = len(y)
    n_tr = int(round(train_frac * n))
    S, R = running_minmax(X)
    S_tr, S_te, X_te, R_te, y_te = S[:n_tr], S[n_tr:], X[n_tr:], R[n_tr:], y[n_tr:]
    n_te = len(y_te)
    print(f"[cascade] {args.data}: {n:,} rows x {len(names)} features; train {n_tr:,} / test {n_te:,}; "
          f"seed {seed}; graph stage {'on' if graph else 'off (no host addresses)'}")
    if graph:
        codes, _ = pd.factorize(np.concatenate([ctx["src"], ctx["dst"]]))
        src_c, dst_c = codes[:n], codes[n:]
        n_hosts = int(codes.max()) + 1
        times = ctx["time"]
        ordered = bool(np.all(np.diff(times[np.isfinite(times)]) >= 0)) if np.isfinite(times).any() else False
        print(f"[cascade] {n_hosts:,} hosts; timestamps {'in time order' if ordered else 'NOT in time order'}")
        if any(c[0].startswith("delaysec:") for c in conds) and not ordered:
            sys.exit("[cascade] delaysec:T needs a time-ordered stream (use a time/campaign-ordered dataset)")
    else:
        times = None
        if any(c[0].startswith("delaysec:") for c in conds):
            sys.exit("[cascade] delaysec:T needs timestamps (dataset 'context' in configs/base.yaml)")

    # 2. Stage 1 (identical to under_attack.py), stage 2 and stage 3 on the training stream.
    m1 = MABTSE(build_pool(seed=seed), top_k=cfg["top_k"], eps=cfg["eps"], mse_window=cfg["mse_window"], seed=seed)
    it = range(n_tr)
    if progress:
        it = tqdm(it, desc="stage 1", unit="smp", leave=False)
    for i in it:
        m1.learn_one(to_dict(S[i], names), int(y[i]))
    m2 = OnlineMLP(len(names), seed=seed)
    pre2 = np.zeros(n_tr)
    for i in range(n_tr):
        pre2[i] = m2.predict_proba(S[i])
        m2.learn(S[i], int(y[i]))
    calib = np.zeros(n_tr, bool)
    calib[n_tr // 2:] = True
    calib &= (y[:n_tr] == 0)
    tau = {"p2": float(np.quantile(pre2[calib], 1 - alpha)) if calib.any() else 0.5}
    g3, train_info = {}, {"stage2_params": m2.n_params()}
    if graph:
        hg_tr = HostGraphs(S, src_c, dst_c, W)
        for key, mixer in (("gnn", "attention"), ("ctx", "mlp")):
            t1 = time.perf_counter()
            st = GraphStage(hg_tr, mixer=mixer, frame=B, seed=seed)
            pre3 = st.fit(n_tr, y, epochs=epochs)
            ok = calib & np.isfinite(pre3)
            tau[key] = float(np.quantile(pre3[ok], 1 - alpha)) if ok.any() else 0.5
            g3[key] = st
            train_info[f"stage3_{key}_params"] = st.n_params()
            train_info[f"stage3_{key}_seconds"] = round(time.perf_counter() - t1, 1)
    print(f"[cascade] thresholds (added false alarms <= {alpha:.0%} on calibration benign flows): "
          + ", ".join(f"{k} {v:.3f}" for k, v in tau.items()) + f"; params {train_info}")

    # 3. The attacker (same surrogate, constraints and perturbations as under_attack.py).
    sur = Surrogate(kind=A.get("surrogate", "mlp"), seed=seed).fit(S[:n_tr], y[:n_tr])
    cs = ConstraintSet.mine(X[:n_tr], names) if "feasible" in variants else None
    scen, attack_info = build_scenarios(S_te, X_te, R_te, y_te, sur, cs, attacks, ["attack_only"], eps, A, seed)
    keep = {"clean"} | set(variants)
    scen = [sc for sc in scen if sc["variant"] in keep]
    base_ctx = {"src": src_c[n_tr:], "dst": dst_c[n_tr:]} if graph else {"src": None, "dst": None}
    scenarios = []
    for sc in scen:
        scenarios.append({"scenario": sc["scenario"], "attack": sc["attack"], "variant": sc["variant"],
                          "S": sc["S"], "y": y_te, "att": y_te == 1, "pos": np.arange(n_te), "n_orig": n_te,
                          "src": base_ctx["src"], "dst": base_ctx["dst"],
                          "time": None if times is None else times[n_tr:], "rho": 1.0})
    base = next((s for s in scenarios if s["scenario"] == "pgd/attack_only/feasible"), None)
    rng = np.random.default_rng([seed, 31])
    if graph and base is not None:
        att_te = y_te == 1
        for spec in adaptive:
            kind_, val = spec.split(":", 1)
            if kind_ == "spoof":
                k = int(val)
                bots = np.unique(base["src"][att_te])
                pool = int(n_hosts) + np.arange(k * max(len(bots), 1))
                src_new = base["src"].copy()
                src_new[att_te] = rng.choice(pool, size=int(att_te.sum()))
                scenarios.append({**base, "scenario": f"pgd/attack_only/feasible/spoof:{k}", "src": src_new})
            elif kind_ == "thin":
                rho = float(val)
                keep_rows = (~att_te) | (rng.random(n_te) < rho)
                idx = np.flatnonzero(keep_rows)
                scenarios.append({**base, "scenario": f"pgd/attack_only/feasible/thin:{rho}", "S": base["S"][idx],
                                  "y": y_te[idx], "att": att_te[idx], "pos": idx, "src": base["src"][idx],
                                  "dst": base["dst"][idx], "time": None if times is None else times[n_tr:][idx],
                                  "rho": rho})
            else:
                sys.exit(f"[cascade] unknown --adaptive value {spec!r}: spoof:k or thin:rho")

    # 4. Replays.
    models = {"m1": m1, "m2": m2, "g3": g3}
    learn_scen = {"clean", "pgd/attack_only/feasible", "cw/attack_only/feasible"}
    rows_out = []
    t_tr = None if times is None else times[:n_tr]
    for sc in scenarios:
        for cond in conds:
            if cond[0] != "frozen" and sc["scenario"] not in learn_scen:
                continue
            t1 = time.perf_counter()
            out = replay(sc, cond, n_tr, S_tr, src_c[:n_tr] if graph else None, dst_c[:n_tr] if graph else None,
                         t_tr, models, names, seed, W, B, progress)
            c = chains(out, tau, graph)
            s1 = c["S1"]
            cov = (float(np.isfinite(out["p3"]["gnn_drift"]).mean() * 100) if graph else None)
            label = "frozen" if cond[0] == "frozen" else "|".join(cond)
            for name, flag in c.items():
                r = {"scenario": sc["scenario"], "attack": sc["attack"], "variant": sc["variant"],
                     "learning": label, "chain": name, **metrics(flag, sc["y"], sc["att"], s1)}
                if sc["rho"] < 1.0 and r["asr"] is not None:
                    r["evaded_volume"] = round(sc["rho"] * r["asr"], 3)
                r["drift_coverage"] = round(cov, 2) if cov is not None else None
                rows_out.append(r)
            secs = round(time.perf_counter() - t1, 1)
            get = {r["chain"]: r for r in rows_out[-len(c):]}
            best = "S1+S2+S3:gnn_drift" if graph else "S1+S2"
            print(f"[cascade] {sc['scenario']:<38} {label:<32} S1 asr {get['S1']['asr']!s:>6} fpr {get['S1']['fpr']!s:>6} | "
                  f"{best} asr {get[best]['asr']!s:>6} fpr {get[best]['fpr']!s:>6} | caught {get[best]['caught_s1_misses']!s:>6}"
                  + (f" | drift cover {cov:.0f}%" if cov is not None else "") + f"  ({secs}s)", flush=True)

    # 5. Save.
    tag = f"_{args.tag}" if args.tag else ""
    out_path = Path(args.out) if args.out else ROOT / "results" / "cascade" / f"{args.data}_seed{seed}{tag}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("river", "numpy", "sklearn", "torch"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover
            versions[mod] = None
    result = {"dataset": args.data, "seed": seed, "n": n, "n_train": n_tr, "n_test": n_te,
              "n_features": len(names), "graph": graph, "n_hosts": int(n_hosts) if graph else None,
              "settings": {"limit": limit, "attacks": attacks, "variants": variants,
                           "conditions": ["|".join(c) if c[0] != "frozen" else "frozen" for c in conds],
                           "adaptive": adaptive, "alpha": alpha, "window": W, "frame": B, "epochs": epochs},
              "thresholds": tau, "training": train_info, "attacks": attack_info, "scenarios": rows_out,
              "versions": versions, "elapsed_s": round(time.perf_counter() - t0, 1),
              "finished_at": dt.datetime.now().isoformat(timespec="seconds")}
    json.dump(result, open(out_path, "w"), indent=2, default=str)
    with open(out_path.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        fields = list(dict.fromkeys(k for r in rows_out for k in r))
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows_out)
    print(f"\n[cascade] done in {result['elapsed_s'] / 60:.1f} min; wrote {out_path} and {out_path.with_suffix('.csv').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
