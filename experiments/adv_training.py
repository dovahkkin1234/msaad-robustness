"""Adversarial-training baseline: does training MABTSE on adversarial DDoS flows stop evasion?

The obvious defence a reviewer will ask about. The defender adds adversarial copies of its own
DDoS training flows to the training stream, labelled DDoS, and the attacker then attacks as
in under_attack.py. For one dataset and one seed:

 1. Same stream, split, scaling and attacker as under_attack.py (identical perturbations for
    the same seed), so the "none" variant reproduces under_attack.py's numbers exactly.
 2. The DEFENDER's own surrogate (a different seed from the attacker's, as in radp_defense.py)
    crafts adversarial copies of every DDoS training flow with the chosen attack(s), at the
    same eps, and repairs them to valid traffic with constraints mined from the training flows
    ("feasible", default) or leaves them raw.
 3. For each variant, a fresh MABTSE is trained on the training stream with each DDoS flow
    followed by its adversarial copy (Algorithm 1 training, learn only):
       none                 no adversarial copies (the baseline detector)
       at:pgd               copies made with PGD only (FGSM, BIM and C&W stay unseen;
                            BIM is PGD without the random start, so it is the "near" case)
       at:fgsm+bim+pgd+cw   copies made with all four attacks, in turn (one copy per flow, so
                            every variant trains on the same number of flows)
 4. Every trained detector faces the attacker's perturbed test streams (attack_only: only DDoS
    flows are perturbed; raw and repaired), under
       frozen     no labels during the test: where MABTSE is weakest (F10)
       delay:D    true labels D flows late (F11); covers clean + repaired PGD and C&W only
    and reports accuracy, FPR, recall, ASR (share of perturbed DDoS flows classified benign),
    clean_miss and evasion_gain as under_attack.py does, plus whether the attack was "seen"
    in training.

v14 adds ADAPTIVE attackers (--adaptive), each evaluated against every trained detector:
       distill    the attacker labels its own data by querying the deployed detector and trains
                  its surrogate on those verdicts (model extraction), then crafts repaired PGD
       atsur      the attacker adversarially trains its own surrogate (clean + PGD examples
                  against itself) before crafting repaired PGD, so its gradients follow robust
                  directions (answers "both surrogates are plain MLPs")
       hsj        label-only HopSkipJump (src/attacks/decision.py) against the frozen detector
                  itself, on a sample of attacker flows, then repaired; success is reported per
                  query budget (250 / 500 / 1,000 / 2,000 queries per flow)
Without --adaptive the attacker is the non-adaptive transfer attacker of v13 (unchanged). This is an offline evaluation on public
benchmark CSVs; it does not generate or send any network traffic.

Usage (repo root, msaad environment active):
    python experiments\\adv_training.py --data iotid20
    python experiments\\adv_training.py --data ciciot2023 --seed 2 --variants none at:pgd
Options: --seed K, --limit N, --variants V ..., --learning MODE ..., --copies raw|feasible,
         --tag T, --out PATH, --no-progress
Defaults come from the `advtrain:` (and `attack:`) sections of configs/base.yaml.
Outputs results\\advtrain\\<data>_seed<k>[_<tag>].json and .csv (one row per variant x scenario).
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
from pathlib import Path

import numpy as np
import yaml
from tqdm import tqdm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

from under_attack import ATTACKS, build_scenarios, load, parse_learning, run_stream, share  # noqa: E402
from src.attacks.constraints import ConstraintSet  # noqa: E402
from src.attacks.decision import hsja_linf  # noqa: E402
from src.attacks.evasion import run_attack  # noqa: E402
from src.attacks.surrogate import Surrogate  # noqa: E402
from src.data.matrix import running_minmax, to_dict  # noqa: E402
from src.eval.metrics import BinaryMetrics  # noqa: E402
from src.models.mabtse import MABTSE  # noqa: E402
from src.models.pool import build_pool  # noqa: E402
from src.utils.seeding import seed_everything  # noqa: E402

VARIANTS = ("none", "at:pgd", "at:fgsm+bim+pgd+cw")
LEARNING = ("frozen", "delay:1000")


def parse_variant(v: str):
    """'none' -> []; 'at:pgd' or 'at:fgsm+pgd' -> list of attacks used to make the copies."""
    if v == "none":
        return []
    if v.startswith("at:"):
        atks = [a for a in v[3:].split("+") if a]
        if atks and all(a in ATTACKS for a in atks):
            return atks
    raise SystemExit(f"[advtrain] unknown variant {v!r}: use none or at:<attacks joined by +>, "
                     f"e.g. at:pgd or at:fgsm+bim+pgd+cw (attacks: {', '.join(ATTACKS)})")


def repair(S_adv, S, X, R, cs):
    """Map scaled perturbations back to raw traffic, project them onto the mined constraints
    and return the repaired scaled vectors (rows with no feasible point stay unperturbed)."""
    dS = np.nan_to_num(S_adv - S)
    X_adv = X + dS * np.where(R > 0, R, 0.0)
    X_proj = cs.project(X_adv, X)
    with np.errstate(invalid="ignore", divide="ignore"):
        S_proj = np.where(R > 0, S + (X_proj - X) / R, S)
    resid = cs.violations(X_proj, X)["any"]
    S_proj[resid] = S[resid]
    return S_proj, resid


def make_copies(atks, sur_d, S_tr, X_tr, R_tr, y_tr, cs, eps, A, seed, kind):
    """One adversarial copy per DDoS training flow; with several attacks, flow j uses attack
    j mod len(atks). Returns (copies of S_tr rows (NaN rows where no copy), info)."""
    ddos = np.flatnonzero(y_tr == 1)
    out = np.full_like(S_tr, np.nan)
    info = {"attacks": atks, "copies": kind, "n_copies": int(len(ddos)), "per_attack": {}}
    for k, atk in enumerate(atks):
        idx = ddos[k::len(atks)]
        if len(idx) == 0:
            continue
        rows = np.ones(len(idx), dtype=bool)
        t = time.perf_counter()
        S_adv = run_attack(atk, sur_d, S_tr[idx], y_tr[idx], rows, eps, params=A.get(atk), seed=seed)
        resid = np.zeros(len(idx), dtype=bool)
        if kind == "feasible":
            S_adv, resid = repair(S_adv, S_tr[idx], X_tr[idx], R_tr[idx], cs)
        out[idx] = S_adv
        info["per_attack"][atk] = {
            "n": int(len(idx)), "seconds": round(time.perf_counter() - t, 1),
            "fools_defender_surrogate": round(100.0 * float((sur_d.predict(S_adv) == 0).mean()), 2),
            "left_unperturbed": round(100.0 * float(resid.mean()), 2)}
    return out, info


def train_detector(S, y, n_tr, names, copies, cfg, seed, label, progress):
    """Algorithm 1 training (learn only); each DDoS flow is followed by its adversarial copy."""
    model = MABTSE(build_pool(seed=seed), top_k=cfg["top_k"], eps=cfg["eps"],
                   mse_window=cfg["mse_window"], seed=seed)
    it = range(n_tr)
    if progress:
        it = tqdm(it, desc=f"train {label}", unit="smp", leave=False)
    n_learn = 0
    for i in it:
        model.learn_one(to_dict(S[i], names), int(y[i]))
        n_learn += 1
        if copies is not None and y[i] == 1 and not np.isnan(copies[i]).all():
            model.learn_one(to_dict(copies[i], names), 1)
            n_learn += 1
    return model, n_learn


def adaptive_scenario(name, sur_x, S_te, X_te, R_te, y_te, cs, eps, A, seed):
    """Repaired PGD on the attacker's test flows, crafted on an adaptive attacker's surrogate."""
    rows = y_te == 1
    S_adv = run_attack("pgd", sur_x, S_te, y_te, rows, eps, params=A.get("pgd"), seed=seed)
    S_rep, _ = repair(S_adv, S_te, X_te, R_te, cs)
    S_rep = np.where(rows[:, None], S_rep, S_te)
    return {"scenario": f"{name}/attack_only/feasible", "attack": name, "perturb": "attack_only",
            "variant": "feasible", "S": S_rep, "rows": rows}


def hsj_eval(model, names, S, y, n_tr, S_te, X_te, R_te, y_te, cs, eps, n_flows, budget, seed):
    """Label-only HopSkipJump against a frozen copy of the detector, on n_flows attacker flows
    the detector currently catches, in two versions:
      raw       queries are arbitrary points of the scaled feature space (the usual setting);
                success is then re-checked after repairing the final point to valid traffic
      feasible  every query is repaired to valid traffic before the detector sees it (the
                attacker can only send real flows), so every success is a valid flow
    Success is reported per query budget."""
    q = copy.deepcopy(model)
    rng = np.random.default_rng([seed, 41])

    def verdicts(Xb, nanmask):
        Xb = np.array(Xb, dtype=float)
        Xb[:, nanmask] = np.nan
        return np.array([0 if (p := q.predict_one(to_dict(r, names))) is None else int(p) for r in Xb])

    def repaired(Xb, i):
        k = len(Xb)
        S_rep, _ = repair(np.asarray(Xb, float), np.repeat(np.nan_to_num(S_te[i])[None, :], k, 0),
                          np.repeat(X_te[i][None, :], k, 0), np.repeat(R_te[i][None, :], k, 0), cs)
        return S_rep

    att_idx = np.flatnonzero(y_te == 1)
    caught = [i for i in rng.permutation(att_idx)[: 4 * n_flows]
              if (q.predict_one(to_dict(S_te[i], names)) or 0) == 1][:n_flows]
    ben0 = np.nan_to_num(S[:n_tr][y[:n_tr] == 0])
    budgets = [b for b in (250, 500, 1000, 2000) if b <= budget] or [budget]
    out = {"n_flows": len(caught)}
    for space in ("raw", "feasible"):
        first, final, used = [], [], []
        for i in caught:
            x0 = S_te[i]
            nanmask = np.isnan(x0)
            if space == "raw":
                decide = lambda Xb, nm=nanmask: verdicts(Xb, nm)  # noqa: E731
            else:
                decide = lambda Xb, nm=nanmask, ii=i: verdicts(repaired(Xb, ii), nm)  # noqa: E731
            order = np.argsort(np.max(np.abs(ben0 - np.nan_to_num(x0)), axis=1))[:10]
            res = hsja_linf(decide, x0, ben0[order], eps, max_queries=budget,
                            rng=np.random.default_rng([seed, 43, int(i)]), movable=~nanmask)
            used.append(res["queries"])
            first.append(res["first_success_query"] if res["success"] else None)
            if res["success"] and space == "raw":          # does the raw-space evasion survive repair?
                xr = repaired(res["x"][None, :], i)[0]
                final.append(int(verdicts(xr[None, :], nanmask)[0] == 0))
            else:
                final.append(int(res["success"]))
        n_ok = max(len(caught), 1)
        by_b = {str(b): round(100.0 * sum(1 for f in first if f is not None and f <= b) / n_ok, 2) for b in budgets}
        out[f"asr_{space}_by_budget"] = by_b
        out[f"asr_{space}"] = by_b[str(budgets[-1])]
        out[f"median_queries_{space}"] = int(np.median(used)) if used else None
        if space == "raw":
            out["asr_raw_after_repair"] = round(100.0 * sum(final) / n_ok, 2)
    out["asr"] = out["asr_feasible"]          # the realistic attacker: valid traffic only
    out["asr_by_budget"] = out["asr_feasible_by_budget"]
    out["median_queries"] = out["median_queries_feasible"]
    return out


def wants(sc: dict, learning: str) -> bool:
    """Frozen covers every scenario; label modes that learn (as slow as online) cover clean and
    the repaired PGD and C&W attacks (BIM behaves like PGD; FGSM is the weakest attack)."""
    return (learning == "frozen" or sc["variant"] == "clean"
            or (sc["variant"] == "feasible" and sc["attack"] in ("pgd", "cw")))


def main() -> int:
    ap = argparse.ArgumentParser(description="Adversarial-training baseline for MABTSE.")
    ap.add_argument("--data", default="synthetic")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--variants", nargs="+", default=None,
                    help="none, at:pgd, at:fgsm+bim+pgd+cw, ... (default from the config)")
    ap.add_argument("--learning", nargs="+", default=None,
                    help="label modes for the test stream: frozen, online, delay:D (default frozen delay:1000)")
    ap.add_argument("--copies", default=None, choices=["feasible", "raw"])
    ap.add_argument("--adaptive", nargs="+", default=None, choices=["distill", "atsur", "hsj"],
                    help="v14 adaptive attackers (default: none, the v13 transfer attacker only)")
    ap.add_argument("--hsj-flows", type=int, default=None, help="attacker flows attacked by HopSkipJump (default 100)")
    ap.add_argument("--hsj-queries", type=int, default=None, help="query budget per flow (default 2000)")
    ap.add_argument("--tag", default=None)
    ap.add_argument("--no-progress", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    valid = ["synthetic", *cfg.get("datasets", {})]
    if args.data not in valid:
        sys.exit(f"[advtrain] unknown --data {args.data!r}; choose from: {', '.join(valid)}")
    A = dict(cfg.get("attack", {}))
    T = dict(cfg.get("advtrain", {}))
    if args.seed is not None:
        cfg["seed"] = args.seed
    seed = cfg["seed"]
    limit = args.limit or A.get("limit", 30000)
    train_frac = A.get("train_frac", 0.67)
    eps = A.get("eps", 0.1)
    attacks = A.get("attacks", list(ATTACKS))
    sur_kind = A.get("surrogate", "mlp")
    variants = list(args.variants or T.get("variants", list(VARIANTS)))
    learning_modes = list(args.learning or T.get("learning", list(LEARNING)))
    kind = args.copies or T.get("copies", "feasible")
    adaptive = list(args.adaptive if args.adaptive is not None else T.get("adaptive", []))
    hsj_n = args.hsj_flows or int(T.get("hsj_flows", 100))
    hsj_q = args.hsj_queries or int(T.get("hsj_queries", 2000))
    off = int(T.get("defender_seed_offset", 1000))
    for v in variants:
        parse_variant(v)
    for m in learning_modes:
        if m == "self":
            sys.exit("[advtrain] the self-labelling mode is not used here")
        parse_learning(m)
    progress = not args.no_progress
    seed_everything(seed)
    t_start = time.perf_counter()

    # 1. Data, split and scaling (identical to under_attack.py for the same seed).
    names, X, y, meta = load(args.data, cfg, limit)
    n = len(y)
    n_tr = int(round(train_frac * n))
    if n_tr < 100 or n - n_tr < 100:
        sys.exit(f"[advtrain] stream too short for a train/test split ({n} rows)")
    S, R = running_minmax(X)
    te = slice(n_tr, n)
    S_te, X_te, R_te, y_te = S[te], X[te], R[te], y[te]
    print(f"[advtrain] {args.data}: {n:,} rows x {len(names)} features; train {n_tr:,} "
          f"({int(y[:n_tr].sum()):,} DDoS) / test {n - n_tr:,}; seed {seed}; copies {kind}")

    # 2. The attacker: same surrogate, constraints and perturbations as under_attack.py.
    sur = Surrogate(kind=sur_kind, seed=seed).fit(S[:n_tr], y[:n_tr])
    cs = ConstraintSet.mine(X[:n_tr], names)
    scen, attack_info = build_scenarios(S_te, X_te, R_te, y_te, sur, cs, attacks,
                                        ["attack_only"], eps, A, seed)

    # 3. The defender's surrogate (its own seed) for crafting the training copies.
    sur_d = Surrogate(kind=sur_kind, seed=seed + off).fit(S[:n_tr], y[:n_tr])

    # 3b. v14: an adversarially trained attacker surrogate (independent of the detector).
    adapt_scen = []
    if "atsur" in adaptive:
        tr_att = y[:n_tr] == 1
        adv_tr = run_attack("pgd", sur, S[:n_tr], y[:n_tr], tr_att, eps, params=A.get("pgd"), seed=seed + 7)
        S_aug = np.vstack([S[:n_tr], adv_tr[tr_att]])
        y_aug = np.concatenate([y[:n_tr], np.ones(int(tr_att.sum()), dtype=int)])
        sur_at = Surrogate(kind=sur_kind, seed=seed).fit(S_aug, y_aug)
        adapt_scen.append(adaptive_scenario("pgd-atsur", sur_at, S_te, X_te, R_te, y_te, cs, eps, A, seed))

    rows_out, train_info = [], {}
    att = y_te == 1
    for v in variants:
        atks = parse_variant(v)
        t = time.perf_counter()
        copies, cinfo = (None, {"attacks": [], "n_copies": 0})
        if atks:
            copies, cinfo = make_copies(atks, sur_d, S[:n_tr], X[:n_tr], R[:n_tr], y[:n_tr],
                                        cs, eps, A, seed + off, kind)
        model, n_learn = train_detector(S, y, n_tr, names, copies, cfg, seed, v, progress)
        cinfo.update({"n_learn": n_learn, "train_seconds": round(time.perf_counter() - t, 1)})
        train_info[v] = cinfo
        print(f"[advtrain] {v}: trained on {n_learn:,} flows ({cinfo['n_copies']:,} adversarial "
              f"copies) in {cinfo['train_seconds']}s"
              + "".join(f"; {a}: fools own surrogate {p['fools_defender_surrogate']}%"
                        for a, p in cinfo.get("per_attack", {}).items()), flush=True)

        # v14: detector-specific adaptive attackers (they query this detector).
        v_scen = list(adapt_scen)
        if "distill" in adaptive:
            q = copy.deepcopy(model)
            lab_hat = np.array([0 if (p := q.predict_one(to_dict(S[i], names))) is None else int(p)
                                for i in range(n_tr)])
            if len(np.unique(lab_hat)) == 2:
                sur_x = Surrogate(kind=sur_kind, seed=seed).fit(S[:n_tr], lab_hat)
                v_scen.append(adaptive_scenario("pgd-distill", sur_x, S_te, X_te, R_te, y_te, cs, eps, A, seed))
        if "hsj" in adaptive:
            r = hsj_eval(model, names, S, y, n_tr, S_te, X_te, R_te, y_te, cs, eps, hsj_n, hsj_q, seed)
            r.update({"at": v, "scenario": "hsj/attack_only/feasible", "attack": "hsj", "variant": "feasible",
                      "learning": "frozen", "seen": False})
            rows_out.append(r)
            print(f"[advtrain] {v:<20} hsj (label-only, {r['n_flows']} flows): raw-space {r['asr_raw_by_budget']} "
                  f"(valid after repair {r['asr_raw_after_repair']}%); valid-traffic queries "
                  f"{r['asr_feasible_by_budget']}", flush=True)

        clean_preds = {}
        for sc in scen + v_scen:
            for learning in learning_modes:
                if not wants(sc, learning):
                    continue
                t = time.perf_counter()
                preds, drifts = run_stream(model, sc["S"], y_te, names, learning,
                                           label=f"{v} {sc['scenario']} ({learning})", progress=progress)
                if sc["variant"] == "clean":
                    clean_preds[learning] = preds
                bm = BinaryMetrics()
                for yt, yp in zip(y_te, preds):
                    bm.update(int(yt), int(yp))
                r = {"at": v, "scenario": sc["scenario"], "attack": sc["attack"],
                     "variant": sc["variant"], "learning": learning,
                     "seen": (None if sc["attack"] is None else sc["attack"] in atks), **bm.as_dict()}
                rows = sc["rows"] & att
                cp = clean_preds[learning]
                r["asr"] = share(rows, preds == 0)
                r["clean_miss"] = share(rows, cp == 0)
                r["evasion_gain"] = None if r["asr"] is None else round(r["asr"] - r["clean_miss"], 2)
                r["drifts_total"] = int(sum(drifts.values()))
                r["seconds"] = round(time.perf_counter() - t, 1)
                rows_out.append(r)
                print(f"[advtrain] {v:<20} {sc['scenario']:<26} {learning:<11} acc {r['accuracy']:6.2f}  "
                      f"fpr {r['fpr']:6.2f}  rec {r['recall']:6.2f}  "
                      f"asr {r['asr'] if r['asr'] is not None else '-':>6}  ({r['seconds']}s)", flush=True)

    # 4. Save.
    tag = f"_{args.tag}" if args.tag else ""
    out = (Path(args.out) if args.out
           else ROOT / "results" / "advtrain" / f"{args.data}_seed{seed}{tag}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("river", "numpy", "sklearn"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover
            versions[mod] = None
    result = {
        "dataset": args.data, "seed": seed, "n": n, "n_train": n_tr, "n_test": n - n_tr,
        "n_features": len(names), "test_ddos_share": round(100 * float(y_te.mean()), 2),
        "settings": {"limit": limit, "train_frac": train_frac, "eps": eps, "attacks": attacks,
                     "surrogate": sur_kind, "variants": variants, "learning": learning_modes,
                     "copies": kind, "defender_seed_offset": off},
        "training": train_info, "attacks": attack_info, "scenarios": rows_out,
        "versions": versions, "elapsed_s": round(time.perf_counter() - t_start, 1),
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(result, open(out, "w"), indent=2, default=str)
    flat = [{k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()} for r in rows_out]
    with open(out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(k for r in flat for k in r)))
        w.writeheader()
        w.writerows(flat)
    print(f"\n[advtrain] done in {result['elapsed_s'] / 60:.1f} min; wrote {out} and {out.with_suffix('.csv').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
