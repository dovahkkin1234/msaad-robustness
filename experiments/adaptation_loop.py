"""S4: the adaptation loop under attack (label poisoning, selector steering) and a defence.

MABTSE adapts by learning every labelled flow. Each label trains the five learners AND
updates the Thompson-Sampling selector (per-arm correctness rewards) and the AUWPAE weights.
under_attack.py shows that with instant TRUE labels this loop makes evasion useless. Here we
ask what happens when the label source can be fooled too.

Threat model (documented assumptions):
  * The attacker controls only its own DDoS flows. It perturbs them (by default the
    repaired, feasible PGD of under_attack.py: valid traffic) and, because the labelling
    oracle (e.g. a signature IDS or an automated triage step) is fooled by the same traffic
    with probability q, each of its flows is labelled benign with probability q
    ("poison:q"). Benign flows always get their true label. q = 0 is Algorithm 1 ("true").
  * Scenario "clean": the attacker does not perturb, its labels are poisoned (poisoning
    alone). Attack scenarios: both at once.
  * The attacker does not know which flows the defender audits (below).

Defender update policies:
  vanilla   the paper: every label trains the learners and updates the selector.
  audit:a   audited selector: a random share a of flows gets a verified (true) label, and
            ONLY those update the selector (Beta rewards, AUWPAE errors). The learners still
            learn every label (an audited flow with its true label).
  guard:a   audit:a plus verified downgrades: a label that would teach "benign" for a flow
            the ensemble has just flagged as DDoS is applied only if that flow is audited;
            otherwise the update is skipped. Every other label is learned as usual.
  strict:a  audit:a plus verified benign labels: an unverified "benign" label is never
            learned; "DDoS" labels are. The attacker gains only from benign labels on its
            own flows, so this denies label poisoning by construction; the cost is that
            benign traffic is learned from audited flows only.
  iwstrict:a  strict:a with importance weighting: each audited benign flow stands for the
            1/a benign flows whose labels strict ignores, so the learners learn it
            round(1/a) times (at most IW_CAP); the selector is still updated once. This
            restores the benign/DDoS balance strict loses (its false-alarm cost) without
            learning a single unverified benign label, so the poisoning guarantee is kept.
  frozen    no learning at all (one run per scenario): the reference that learning should
            never be worse than.

Reports, per scenario x label source x policy: accuracy, recall, F1, false-alarm rate (FPR),
ASR (attacker flows classified benign) overall and per tenth of the test stream,
poison_gain (ASR minus the same run with true labels), evasion_gain (ASR minus the clean
scenario with the same labels and policy), the share of steps each learner sits in the
selected top-k ("sel_<learner>", selector steering), the learners' final Thompson-Sampling
posterior means, update / skip / audit counts and drift detections. Frozen runs also report
each learner's own ASR and FPR (which learners the perturbations fool).

Offline evaluation of our own reimplementation on public benchmark CSVs; nothing is sent
over a network.

Usage (repo root, msaad environment active):
    python experiments\\adaptation_loop.py --data iotid20
    python experiments\\adaptation_loop.py --data iotid20 --limit 3000
    python experiments\\adaptation_loop.py --data iotid20 --labels true poison:0.25 poison:1.0 --policies vanilla guard:0.05
    python experiments\\adaptation_loop.py --data iotid20 --policies strict:0.1 iwstrict:0.1 --tag iw
Options: --seed K, --limit N, --train-frac F, --eps E, --attacks ..., --variants raw feasible,
         --labels ..., --policies ..., --no-progress, --tag T, --out PATH
Defaults come from the attack: and loop: sections of configs/base.yaml.
Outputs results\\loop\\<data>_seed<k>[_<tag>].json and .csv (one row per run).
"""
from __future__ import annotations

import argparse
import copy
import csv
import datetime as dt
import json
import platform
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import yaml
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from under_attack import ATTACKS, build_scenarios, load, share  # noqa: E402
from src.attacks.constraints import ConstraintSet  # noqa: E402
from src.attacks.surrogate import Surrogate  # noqa: E402
from src.data.matrix import running_minmax, to_dict  # noqa: E402
from src.eval.metrics import BinaryMetrics  # noqa: E402
from src.models.mabtse import MABTSE  # noqa: E402
from src.models.pool import build_pool, drift_counts  # noqa: E402
from src.utils.seeding import seed_everything  # noqa: E402

LABELS = ("true", "poison:0.5", "poison:1.0")
POLICIES = ("vanilla", "audit:0.1", "guard:0.1", "strict:0.1")
KINDS = ("audit", "guard", "strict", "iwstrict")
IW_CAP = 20        # iwstrict: at most this many copies of one audited benign flow
VARIANTS = ("raw", "feasible")


def _rate(spec: str, what: str) -> float:
    try:
        v = float(spec.split(":", 1)[1])
    except (IndexError, ValueError):
        v = -1.0
    if not 0.0 <= v <= 1.0:
        raise SystemExit(f"[loop] bad {what} {spec!r}: the number after ':' must be between 0 and 1")
    return v


def parse_labels(spec: str) -> float:
    """'true' -> 0.0; 'poison:q' -> q (share of the attacker's flows labelled benign)."""
    if spec == "true":
        return 0.0
    if spec.startswith("poison:"):
        return _rate(spec, "--labels value")
    raise SystemExit(f"[loop] unknown --labels value {spec!r}: use true or poison:q (e.g. poison:0.5)")


def parse_policy(spec: str):
    """'vanilla' -> ('vanilla', 0); 'audit:a' / 'guard:a' / 'strict:a' / 'iwstrict:a' -> (kind, a)."""
    if spec == "vanilla":
        return "vanilla", 0.0
    kind = spec.split(":", 1)[0]
    if kind in KINDS and ":" in spec:
        return kind, _rate(spec, "--policies value")
    raise SystemExit(f"[loop] unknown --policies value {spec!r}: use vanilla, audit:a, guard:a, strict:a "
                     "or iwstrict:a")


def iw_copies(audit_rate: float) -> int:
    """How many times iwstrict learns one audited benign flow: round(1/a), capped at IW_CAP."""
    return max(1, min(IW_CAP, int(round(1.0 / audit_rate)))) if audit_rate > 0 else 1


def _mask(seed: int, salt: int, rate: float, n: int) -> np.ndarray:
    """Reproducible Bernoulli(rate) mask, identical for every policy and scenario (paired runs)."""
    rng = np.random.default_rng([int(seed), int(salt), int(round(rate * 10000))])
    return rng.random(n) < rate


def replay(model: MABTSE, S, y, names, att, policy: str, audit_rate: float, flip, audit,
           per_arm: bool, label: str, progress: bool) -> dict:
    """One test-stream replay under one label source (flip mask) and update policy."""
    m = copy.deepcopy(model)
    learners = m.learners
    d0 = drift_counts(learners)
    n = len(y)
    preds = np.zeros(n, dtype=int)
    arm_preds = {a: np.zeros(n, dtype=int) for a in m.names} if per_arm else None
    sel = Counter()
    cnt = Counter()
    it = range(n)
    if progress:
        it = tqdm(it, desc=label, unit="smp", leave=False)
    for i in it:
        x = to_dict(S[i], names)
        p = m.predict_one(x)
        preds[i] = 0 if p is None else int(p)
        for a in m._last_selected:
            sel[a] += 1
        if per_arm:
            for a in m.names:
                q = learners[a].predict_one(x)
                arm_preds[a][i] = 0 if q is None else int(q)
        if policy == "frozen":
            continue
        y_true = int(y[i])
        lab = 0 if (att[i] and flip[i]) else y_true          # poisoned label for attacker flows
        if policy == "vanilla":
            m.learn_one(x, lab)
            cnt["learn"] += 1
            cnt["selector_updates"] += 1
            cnt["poisoned_learned"] += int(lab != y_true)
            continue
        if audit[i]:                                         # verified label: the truth
            m.learn_one(x, y_true, update_selector=True)
            reps = iw_copies(audit_rate) if (policy == "iwstrict" and y_true == 0) else 1
            for _ in range(reps - 1):                        # iwstrict: the 1/a benign flows it stands for
                m.learn_one(x, y_true, update_selector=False)
            cnt["audited"] += 1
            cnt["learn"] += reps
            cnt["selector_updates"] += 1
        elif (policy == "guard" and lab == 0 and preds[i] == 1) or (policy in ("strict", "iwstrict") and lab == 0):
            cnt["skipped"] += 1                              # unverified benign label: not applied
            cnt["poisoned_blocked"] += int(lab != y_true)
        else:
            m.learn_one(x, lab, update_selector=False)
            cnt["learn"] += 1
            cnt["poisoned_learned"] += int(lab != y_true)
    drifts = {k: v - d0.get(k, 0) for k, v in drift_counts(learners).items()}
    post = {a: round(m.alpha[a] / (m.alpha[a] + m.beta[a]), 4) for a in m.names}
    return {"preds": preds, "arm_preds": arm_preds, "sel": sel, "counts": cnt,
            "drifts": drifts, "posterior_mean": post, "names": list(m.names)}


def score(out: dict, y: np.ndarray, att: np.ndarray) -> dict:
    preds = out["preds"]
    bm = BinaryMetrics()
    for yt, yp in zip(y, preds):
        bm.update(int(yt), int(yp))
    r = dict(bm.as_dict())
    r["asr"] = share(att, preds == 0)
    tenths = np.array_split(np.arange(len(y)), 10)
    r["asr_by_tenth"] = [share(att[t], preds[t] == 0) for t in tenths]
    steps = max(1, len(y))
    for a in out["names"]:
        r[f"sel_{a}"] = round(100.0 * out["sel"][a] / steps, 2)
    c = out["counts"]
    for k in ("learn", "selector_updates", "audited", "skipped", "poisoned_learned", "poisoned_blocked"):
        r[f"n_{k}"] = int(c.get(k, 0))
    r["drifts_total"] = int(sum(out["drifts"].values()))
    r["drifts"] = out["drifts"]
    r["posterior_mean"] = out["posterior_mean"]
    if out["arm_preds"] is not None:
        ben = y == 0
        r["arm_asr"] = {a: share(att, v == 0) for a, v in out["arm_preds"].items()}
        r["arm_fpr"] = {a: share(ben, v == 1) for a, v in out["arm_preds"].items()}
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="S4: label poisoning, selector steering and a defence.")
    ap.add_argument("--data", default="synthetic")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--train-frac", type=float, default=None)
    ap.add_argument("--eps", type=float, default=None)
    ap.add_argument("--attacks", nargs="+", default=None, choices=ATTACKS)
    ap.add_argument("--variants", nargs="+", default=None, choices=VARIANTS,
                    help="which attack versions to test: raw and/or feasible (repaired)")
    ap.add_argument("--labels", nargs="+", default=None, help="true and/or poison:q")
    ap.add_argument("--policies", nargs="+", default=None, help="vanilla, audit:a, guard:a, strict:a, iwstrict:a")
    ap.add_argument("--no-progress", action="store_true")
    ap.add_argument("--tag", default=None, help="suffix for the default output name")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    valid = ["synthetic", *cfg.get("datasets", {})]
    if args.data not in valid:
        sys.exit(f"[loop] unknown --data {args.data!r}; choose from: {', '.join(valid)}")
    A = dict(cfg.get("attack", {}))
    L = dict(cfg.get("loop", {}))
    if args.seed is not None:
        cfg["seed"] = args.seed
    seed = cfg["seed"]
    limit = args.limit or A.get("limit", 30000)
    train_frac = args.train_frac or A.get("train_frac", 0.67)
    eps = args.eps if args.eps is not None else A.get("eps", 0.1)
    attacks = args.attacks or L.get("attacks", ["pgd"])
    variants = args.variants or L.get("variants", ["feasible"])
    label_specs = list(args.labels or L.get("labels", list(LABELS)))
    policy_specs = list(args.policies or L.get("policies", list(POLICIES)))
    q_of = {s: parse_labels(s) for s in label_specs}
    pol_of = {s: parse_policy(s) for s in policy_specs}
    sur_kind = A.get("surrogate", "mlp")
    progress = not args.no_progress
    seed_everything(seed)
    t_start = time.perf_counter()

    # 1. Data, split, detector and attacker: identical to under_attack.py for the same seed.
    names, X, y, meta = load(args.data, cfg, limit)
    n = len(y)
    n_tr = int(round(train_frac * n))
    if n_tr < 100 or n - n_tr < 100:
        sys.exit(f"[loop] stream too short for a train/test split ({n} rows)")
    S, R = running_minmax(X)
    te = slice(n_tr, n)
    S_te, X_te, R_te, y_te = S[te], X[te], R[te], y[te]
    print(f"[loop] {args.data}: {n:,} rows x {len(names)} features; train {n_tr:,} / test "
          f"{n - n_tr:,} (test DDoS share {100 * y_te.mean():.1f}%), seed {seed}")
    model = MABTSE(build_pool(seed=seed), top_k=cfg["top_k"], eps=cfg["eps"],
                   mse_window=cfg["mse_window"], seed=seed)
    it = range(n_tr)
    if progress:
        it = tqdm(it, desc="train", unit="smp", leave=False)
    for i in it:
        model.learn_one(to_dict(S[i], names), int(y[i]))
    sur = Surrogate(kind=sur_kind, seed=seed).fit(S[:n_tr], y[:n_tr])
    cs = ConstraintSet.mine(X[:n_tr], names) if "feasible" in variants else None
    scen, attack_info = build_scenarios(S_te, X_te, R_te, y_te, sur, cs, attacks,
                                        ["attack_only"], eps, A, seed)
    keep = {"clean"} | ({"raw"} if "raw" in variants else set()) | ({"feasible"} if "feasible" in variants else set())
    scen = [sc for sc in scen if sc["variant"] in keep]
    att = y_te == 1                       # the attacker's flows: every DDoS flow of the test stream
    n_te = len(y_te)

    # 2. Replays: one frozen run per scenario (with per-learner verdicts), then every
    #    label source x policy. Masks are shared by all runs (paired comparison).
    flips = {s: _mask(seed, 7, q, n_te) for s, q in q_of.items()}
    audits = {s: _mask(seed, 11, a, n_te) for s, (_, a) in pol_of.items()}
    rows_out = []
    for sc in scen:
        runs = [("frozen", "frozen")] + [(ls, ps) for ls in label_specs for ps in policy_specs]
        for ls, ps in runs:
            kind, a = ("frozen", 0.0) if ps == "frozen" else pol_of[ps]
            flip = np.zeros(n_te, dtype=bool) if ls == "frozen" else flips[ls]
            audit = np.zeros(n_te, dtype=bool) if ps == "frozen" else audits[ps]
            t = time.perf_counter()
            out = replay(model, sc["S"], y_te, names, att, kind, a, flip, audit,
                         per_arm=(ps == "frozen"), label=f"{sc['scenario']} {ls} {ps}",
                         progress=progress)
            r = {"scenario": sc["scenario"], "attack": sc["attack"], "variant": sc["variant"],
                 "learning": ls, "policy": ps, "poison_q": 0.0 if ls == "frozen" else q_of[ls],
                 "audit_rate": a, **score(out, y_te, att)}
            r["seconds"] = round(time.perf_counter() - t, 1)
            rows_out.append(r)
            print(f"[loop] {sc['scenario']:<26} {ls:<11} {ps:<10} acc {r['accuracy']:6.2f}  "
                  f"fpr {r['fpr']:6.2f}  asr {str(r['asr']):>6}  KNN sel {r.get('sel_KNN-ADWIN', '-'):>6}  "
                  f"skipped {r['n_skipped']:>5}  ({r['seconds']}s)", flush=True)

    # 3. Paired gains: what poisoning adds (vs true labels, same scenario and policy) and what
    #    the perturbation adds (vs the clean scenario, same labels and policy).
    look = {(r["scenario"], r["learning"], r["policy"]): r for r in rows_out}
    for r in rows_out:
        base_true = look.get((r["scenario"], "true", r["policy"]))
        base_clean = look.get(("clean", r["learning"], r["policy"]))
        r["poison_gain"] = (None if r["asr"] is None or base_true is None or r["learning"] in ("true", "frozen")
                            else round(r["asr"] - base_true["asr"], 2))
        r["evasion_gain"] = (None if r["asr"] is None or base_clean is None or r["scenario"] == "clean"
                             else round(r["asr"] - base_clean["asr"], 2))

    # 4. Save.
    tag = f"_{args.tag}" if args.tag else ""
    out_path = Path(args.out) if args.out else ROOT / "results" / "loop" / f"{args.data}_seed{seed}{tag}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("river", "pandas", "numpy", "sklearn"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover
            versions[mod] = None
    result = {
        "dataset": args.data, "seed": seed, "n": n, "n_train": n_tr, "n_test": n_te,
        "n_features": len(names), "test_ddos_share": round(100 * float(y_te.mean()), 2),
        "settings": {"limit": limit, "train_frac": train_frac, "eps": eps, "attacks": attacks,
                     "variants": variants, "labels": label_specs, "policies": policy_specs,
                     "surrogate": sur_kind},
        "attacks": attack_info, "scenarios": rows_out,
        "versions": versions, "elapsed_s": round(time.perf_counter() - t_start, 1),
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(result, open(out_path, "w"), indent=2, default=str)
    nested = ("asr_by_tenth", "drifts", "posterior_mean", "arm_asr", "arm_fpr")
    flat = [{k: v for k, v in r.items() if k not in nested} for r in rows_out]
    fields = list(dict.fromkeys(k for r in flat for k in r))
    with open(out_path.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(flat)
    print(f"\n[loop] done in {result['elapsed_s'] / 60:.1f} min; wrote {out_path} and {out_path.with_suffix('.csv').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
