"""RADP, the base paper's Layer 1, reproduced and stress-tested (the paper's Scenario 3).

What it does, for one dataset and one seed:
 1. Builds the same stream, split and trained MABTSE as under_attack.py (Algorithm 1), and the
    same attacker: FGSM, BIM, PGD and C&W perturbations of the test DDoS flows crafted on the
    attacker's surrogate (attack_only threat model), plus their repaired (feasible) versions.
    For the same seed, the perturbations are identical to under_attack.py's.
 2. Builds RADP the way the paper describes, from the defender's clean training flows only:
      MSAPG   the defender's own surrogate + the four attacks (eps 0.1) on every flow
      GAN     trained to mimic the MSAPG samples (src/defense/gan.py)
      RAD     a fresh MABTSE trained on clean (0) vs MSAPG + GAN (1), class-balanced
      purify  every flow RAD flags is deleted before it reaches the DDoS detector
    The assumptions behind each step (A1-A4) are listed in src/defense/radp.py.
 3. RAD variants:
      rad           all four attacks + GAN (the paper's design)
      rad_nogan     all four attacks, no GAN (ablation: what does the GAN add?)
      loao_<atk>    trained without that attack and tested on it (the "unknown attacks" claim)
 4. Reports, per RAD variant and test scenario (percentages):
      rad_flag_ddos    DDoS flows RAD flags (on attack scenarios: its detection rate)
      benign_deleted   benign flows RAD flags: legitimate traffic deleted by the defence
      asr_no_radp      perturbed DDoS flows the detector calls benign without RADP (frozen)
      e2e_asr          perturbed DDoS flows that pass RAD AND are called benign (end to end)
      recovered_acc    the paper's metric: detector accuracy on the surviving flows only
      blocked_acc      accuracy over ALL flows when deleted flows count as blocked (DDoS)
      benign_lost      benign flows that are deleted or flagged as DDoS by the detector
    The DDoS detector runs frozen for every RAD variant; for "rad" it also runs online on the
    purified stream (true labels at once, as in Algorithm 1).

Offline evaluation of our own reimplementation on public benchmark CSVs; nothing is sent
over a network.

Usage (repo root, msaad environment active):
    python experiments\\radp_defense.py --data iotid20
    python experiments\\radp_defense.py --data iotid20 --limit 3000 --variants rad rad_nogan
Options: --seed K, --limit N, --train-frac F, --eps E, --attacks ..., --variants ...,
         --no-online, --no-progress, --tag T, --out PATH
Defaults come from the attack: and radp: sections of configs/base.yaml.
Outputs results\\radp\\<data>_seed<k>[_<tag>].json and .csv (one row per variant x scenario).
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

from under_attack import ATTACKS, build_scenarios, load, run_stream, share  # noqa: E402
from src.attacks.constraints import ConstraintSet  # noqa: E402
from src.attacks.surrogate import Surrogate  # noqa: E402
from src.data.matrix import running_minmax, to_dict  # noqa: E402
from src.defense.gan import TabularGAN  # noqa: E402
from src.defense.radp import flag, msapg, train_rad, training_mix, with_missing_like  # noqa: E402
from src.models.mabtse import MABTSE  # noqa: E402
from src.models.pool import build_pool  # noqa: E402
from src.utils.seeding import seed_everything  # noqa: E402

VARIANTS = ("rad", "rad_nogan", "loao")


def score(y: np.ndarray, flagged: np.ndarray, pred: np.ndarray, att: np.ndarray,
          ben: np.ndarray, with_no_radp: bool) -> dict:
    """Metrics for one (RAD, scenario, learning) combination; deleted flows count as blocked."""
    full = np.where(flagged, 1, pred)
    surv = ~flagged
    rec = None if not surv.any() else round(100.0 * float((pred[surv] == y[surv]).mean()), 2)
    return {
        "rad_flag_ddos": share(att, flagged),
        "benign_deleted": share(ben, flagged),
        "asr_no_radp": share(att, pred == 0) if with_no_radp else None,
        "e2e_asr": share(att, full == 0),
        "recovered_acc": rec,
        "blocked_acc": round(100.0 * float((full == y).mean()), 2),
        "benign_lost": share(ben, full == 1),
        "n_deleted": int(flagged.sum()),
        "n_survivors": int(surv.sum()),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="RADP (the paper's Layer 1) under the same attacks.")
    ap.add_argument("--data", default="synthetic")
    ap.add_argument("--config", default=str(ROOT / "configs" / "base.yaml"))
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--train-frac", type=float, default=None)
    ap.add_argument("--eps", type=float, default=None)
    ap.add_argument("--attacks", nargs="+", default=None, choices=ATTACKS)
    ap.add_argument("--variants", nargs="+", default=None, choices=VARIANTS)
    ap.add_argument("--no-online", action="store_true", help="skip the online detector runs")
    ap.add_argument("--no-progress", action="store_true")
    ap.add_argument("--tag", default=None, help="suffix for the default output name")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cfg = yaml.safe_load(open(args.config))
    valid = ["synthetic", *cfg.get("datasets", {})]
    if args.data not in valid:
        sys.exit(f"[radp] unknown --data {args.data!r}; choose from: {', '.join(valid)}")
    A = dict(cfg.get("attack", {}))
    P = dict(cfg.get("radp", {}))
    if args.seed is not None:
        cfg["seed"] = args.seed
    seed = cfg["seed"]
    limit = args.limit or A.get("limit", 30000)
    train_frac = args.train_frac or A.get("train_frac", 0.67)
    eps = args.eps if args.eps is not None else A.get("eps", 0.1)
    attacks = args.attacks or A.get("attacks", list(ATTACKS))
    sur_kind = A.get("surrogate", "mlp")
    variants = args.variants or P.get("variants", list(VARIANTS))
    m_rows = int(P.get("rows", 4000))
    gan_share = float(P.get("gan_share", 0.5))
    gan_cfg = dict(P.get("gan", {}))
    holdout = float(P.get("holdout", 0.2))
    off = int(P.get("defender_seed_offset", 1000))
    online = not args.no_online
    progress = not args.no_progress
    seed_everything(seed)
    t_start = time.perf_counter()

    # 1. Data, split and the DDoS detector (identical to under_attack.py for the same seed).
    names, X, y, meta = load(args.data, cfg, limit)
    n = len(y)
    n_tr = int(round(train_frac * n))
    if n_tr < 100 or n - n_tr < 100:
        sys.exit(f"[radp] stream too short for a train/test split ({n} rows)")
    S, R = running_minmax(X)
    te = slice(n_tr, n)
    S_te, X_te, R_te, y_te = S[te], X[te], R[te], y[te]
    print(f"[radp] {args.data}: {n:,} rows x {len(names)} features; train {n_tr:,} / test "
          f"{n - n_tr:,} (test DDoS share {100 * y_te.mean():.1f}%), seed {seed}")
    model = MABTSE(build_pool(seed=seed), top_k=cfg["top_k"], eps=cfg["eps"],
                   mse_window=cfg["mse_window"], seed=seed)
    it = range(n_tr)
    if progress:
        it = tqdm(it, desc="train detector", unit="smp", leave=False)
    for i in it:
        model.learn_one(to_dict(S[i], names), int(y[i]))

    # 2. The attacker (same surrogate, constraints and perturbations as under_attack.py).
    sur = Surrogate(kind=sur_kind, seed=seed).fit(S[:n_tr], y[:n_tr])
    cs = ConstraintSet.mine(X[:n_tr], names)
    scen, attack_info = build_scenarios(S_te, X_te, R_te, y_te, sur, cs, attacks,
                                        ["attack_only"], eps, A, seed)
    by_name = {sc["scenario"]: sc for sc in scen}
    att = y_te == 1
    ben = y_te == 0

    # 3. Frozen detector verdicts per scenario (they do not depend on RADP: frozen model).
    frozen = {}
    for sc in scen:
        frozen[sc["scenario"]], _ = run_stream(model, sc["S"], y_te, names, "frozen",
                                               label=f"detector {sc['scenario']}", progress=progress)

    # 4. The defender's RADP ingredients, from its clean training flows only.
    sur_d = Surrogate(kind=sur_kind, seed=seed + off).fit(S[:n_tr], y[:n_tr])
    m = min(m_rows, n_tr)
    idx = np.unique(np.linspace(0, n_tr - 1, m).round().astype(int))
    S_def, y_def = S[idx], y[idx]
    t = time.perf_counter()
    adv = msapg(sur_d, S_def, y_def, attacks, eps, {a: A.get(a) for a in attacks}, seed + off)
    print(f"[radp] MSAPG: {len(idx):,} clean training flows x {len(attacks)} attacks on the "
          f"defender's surrogate ({time.perf_counter() - t:.1f}s)")

    plan = []
    if "rad" in variants:
        plan.append(("rad", list(attacks), True))
    if "rad_nogan" in variants:
        plan.append(("rad_nogan", list(attacks), False))
    if "loao" in variants and len(attacks) > 1:
        for a in attacks:
            plan.append((f"loao_{a}", [b for b in attacks if b != a], True))

    rows_out, rad_info = [], {}
    for k, (vname, known, use_gan) in enumerate(plan):
        t = time.perf_counter()
        rng = np.random.default_rng(seed + off + 17 * (k + 1))
        gan_rows, gan_fid = None, None
        if use_gan:
            pooled = np.vstack([adv[a] for a in known])
            gan = TabularGAN(steps=int(gan_cfg.get("steps", 3000)), batch=int(gan_cfg.get("batch", 128)),
                             lr=float(gan_cfg.get("lr", 2e-4)), seed=seed + off + k).fit(pooled)
            n_gan = int(round(gan_share * len(S_def)))
            gan_rows = with_missing_like(gan.sample(n_gan), pooled, rng)
            gan_fid = gan.fidelity(pooled, seed=seed)
        Xr, yr = training_mix(S_def, adv, known, gan_rows, rng)
        cut = int(round((1 - holdout) * len(yr)))
        rad = train_rad(Xr[:cut], yr[:cut], names, cfg, seed + 2 * off + k)
        hold = flag(copy.deepcopy(rad), Xr[cut:], names)
        info = {"known_attacks": known, "gan": use_gan, "train_rows": cut,
                "holdout_acc": round(100.0 * float((hold == (yr[cut:] == 1)).mean()), 2),
                "gan_fidelity": gan_fid}
        held = [a for a in attacks if a not in known]
        tests = (scen if not held else
                 [by_name["clean"], by_name[f"{held[0]}/attack_only"], by_name[f"{held[0]}/attack_only/feasible"]])
        for sc in tests:
            fl = flag(copy.deepcopy(rad), sc["S"], names)
            base = {"rad": vname, "unknown_attack": held[0] if held else None, "scenario": sc["scenario"],
                    "attack": sc["attack"], "variant": sc["variant"]}
            r = {**base, "learning": "frozen",
                 **score(y_te, fl, frozen[sc["scenario"]], att, ben, with_no_radp=True)}
            rows_out.append(r)
            print(f"[radp] {vname:<11} {sc['scenario']:<26} frozen  flag DDoS {str(r['rad_flag_ddos']):>6}  "
                  f"benign deleted {str(r['benign_deleted']):>6}  ASR {str(r['asr_no_radp']):>6} -> "
                  f"{str(r['e2e_asr']):>6}  recovered acc {r['recovered_acc']}  blocked acc {r['blocked_acc']}",
                  flush=True)
            if online and vname == "rad":
                surv = ~fl
                pred = np.ones(len(y_te), dtype=int)
                if surv.any():
                    p_s, _ = run_stream(model, sc["S"][surv], y_te[surv], names, "online",
                                        label=f"purified {sc['scenario']}", progress=progress)
                    pred[surv] = p_s
                r2 = {**base, "learning": "online", **score(y_te, fl, pred, att, ben, with_no_radp=False)}
                rows_out.append(r2)
                print(f"[radp] {vname:<11} {sc['scenario']:<26} online  e2e ASR {str(r2['e2e_asr']):>6}  "
                      f"recovered acc {r2['recovered_acc']}  blocked acc {r2['blocked_acc']}", flush=True)
        info["seconds"] = round(time.perf_counter() - t, 1)
        rad_info[vname] = info
        print(f"[radp] {vname}: RAD hold-out accuracy {info['holdout_acc']}%"
              + (f"; GAN two-sample AUC {gan_fid['c2st_auc']}" if gan_fid else "")
              + f" ({info['seconds']}s)", flush=True)

    # 5. Save.
    tag = f"_{args.tag}" if args.tag else ""
    out = Path(args.out) if args.out else ROOT / "results" / "radp" / f"{args.data}_seed{seed}{tag}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for mod in ("river", "pandas", "numpy", "sklearn", "scipy"):
        try:
            versions[mod] = __import__(mod).__version__
        except Exception:  # pragma: no cover
            versions[mod] = None
    result = {
        "dataset": args.data, "seed": seed, "n": n, "n_train": n_tr, "n_test": n - n_tr,
        "n_features": len(names), "test_ddos_share": round(100 * float(y_te.mean()), 2),
        "settings": {"limit": limit, "train_frac": train_frac, "eps": eps, "attacks": attacks,
                     "surrogate": sur_kind, "variants": variants, "online": online, "radp": P},
        "attacks": attack_info, "rad": rad_info, "scenarios": rows_out,
        "versions": versions, "elapsed_s": round(time.perf_counter() - t_start, 1),
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(result, open(out, "w"), indent=2, default=str)
    with open(out.with_suffix(".csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"\n[radp] done in {result['elapsed_s'] / 60:.1f} min; wrote {out} and {out.with_suffix('.csv').name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
