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
  v14 additions (v13 runs are unchanged, bit for bit):
  iwstrict:a:c  iwstrict with at most c copies per audited benign flow (weight clipping; the
            default cap is 20). Controls the variance of the 1/a weight at small audit shares.
  consensus:a   strict:a, and an unverified "DDoS" label is learned only when the detector's
            own verdict is DDoS too (both label directions need agreement or an audit). The
            defence against framing (below); its cost is slower adaptation to evasion.
  iwconsensus:a[:c]  consensus with iwstrict's benign re-weighting.
  noiseaware:a  a trusted-audit noise-rate baseline in the spirit of GLC (Hendrycks et al.
            2018) and class-conditional noise correction (Natarajan et al. 2013): audited flows
            that arrived with a benign label estimate rho = P(truly DDoS | labelled benign)
            (Beta(1,1) prior); every unverified benign label is learned with probability
            1 - rho. It behaves like vanilla when labels are clean and like strict when they are
            poisoned, without being told which.

Label sources (--labels): "true", "poison:q", and v14's "frame:r" (framing / availability
poisoning through the trusted direction, after Paragraph, Newsome et al. RAID 2006): the
attacker's bots send benign-looking flows (replays of benign training flows, valid traffic by
construction), r per test flow, during the first --frame-span of the test stream. They come
from attacker hosts, so the labeller (correctly) calls them DDoS, and every policy that trusts
DDoS labels learns them: the target is the false-alarm rate on genuine benign traffic.
Combine with '+', e.g. "poison:1.0+frame:0.05". Framing flows are excluded from every metric
(FPR and ASR are measured on genuine flows only); fpr_frame_window / fpr_after_window show the
damage during the campaign and whether the detector recovers after it.

Audit allocation (--audits): "random" (default: each flow audited with probability a, unseen
by the attacker), "uncertain" (the a share of flows whose verdict is least certain, chosen
online by a budget controller), or "mixed" (half of the budget each way). Uncertainty-only
audits never look at flows the detector is confident about, which is exactly where an evading
attacker puts its flows (the audit-aware attacker needs no extra knowledge: evasion already
makes its flows confidently benign).

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
    python experiments\\adaptation_loop.py --data iotid20 --labels true frame:0.05 --policies strict:0.1 consensus:0.1 --tag frame
    python experiments\\adaptation_loop.py --data iotid20 --labels poison:1.0 --policies strict:0.1 --audits uncertain --tag audits
Options: --seed K, --limit N, --train-frac F, --eps E, --attacks ..., --variants raw feasible,
         --labels ..., --policies ..., --audits random|uncertain|mixed, --frame-span F,
         --no-progress, --tag T, --out PATH
Defaults come from the attack: and loop: sections of configs/base.yaml.
Outputs results\\loop\\<data>_seed<k>[_<tag>].json and .csv (one row per run).
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
KINDS = ("audit", "guard", "strict", "iwstrict", "consensus", "iwconsensus", "noiseaware")
IW_KINDS = ("iwstrict", "iwconsensus")
IW_CAP = 20        # iwstrict: at most this many copies of one audited benign flow (default cap)
VARIANTS = ("raw", "feasible")
AUDIT_MODES = ("random", "uncertain", "mixed")


def _rate(spec: str, what: str) -> float:
    try:
        v = float(spec.split(":", 1)[1])
    except (IndexError, ValueError):
        v = -1.0
    if not 0.0 <= v <= 1.0:
        raise SystemExit(f"[loop] bad {what} {spec!r}: the number after ':' must be between 0 and 1")
    return v


def parse_labels(spec: str) -> float:
    """Poison share q of a label source: 'true' -> 0.0; 'poison:q' -> q (the share of the
    attacker's flows labelled benign); parts joined by '+' are combined (see parse_source)."""
    return parse_source(spec)[0]


def parse_source(spec: str):
    """A label source -> (q, r): q = poisoned share of the attacker's flows, r = framing flows
    per test flow. 'true', 'poison:q', 'frame:r' and '+' combinations such as
    'poison:1.0+frame:0.05'."""
    if spec == "true":
        return 0.0, 0.0
    q, r = 0.0, 0.0
    for part in spec.split("+"):
        if part.startswith("poison:"):
            q = _rate(part, "--labels value")
        elif part.startswith("frame:"):
            r = _rate(part, "--labels value")
        elif part != "true":
            raise SystemExit(f"[loop] unknown --labels value {spec!r}: use true, poison:q, frame:r or "
                             "a '+' combination (e.g. poison:1.0+frame:0.05)")
    return q, r


def parse_policy(spec: str):
    """'vanilla' -> ('vanilla', 0, cap); '<kind>:a' -> (kind, a, IW_CAP); 'iwstrict:a:c' and
    'iwconsensus:a:c' -> (kind, a, c) with c = the copy cap."""
    if spec == "vanilla":
        return "vanilla", 0.0, IW_CAP
    parts = spec.split(":")
    kind = parts[0]
    if kind in KINDS and len(parts) in (2, 3):
        a = _rate(f"{kind}:{parts[1]}", "--policies value")
        cap = IW_CAP
        if len(parts) == 3:
            if kind not in IW_KINDS:
                raise SystemExit(f"[loop] {spec!r}: only iwstrict and iwconsensus take a copy cap")
            try:
                cap = int(parts[2])
            except ValueError:
                cap = 0
            if cap < 1:
                raise SystemExit(f"[loop] {spec!r}: the copy cap must be a whole number >= 1")
        return kind, a, cap
    raise SystemExit(f"[loop] unknown --policies value {spec!r}: use vanilla, audit:a, guard:a, strict:a, "
                     "iwstrict:a[:cap], consensus:a, iwconsensus:a[:cap] or noiseaware:a")


def iw_copies(audit_rate: float, cap: int = IW_CAP) -> int:
    """How many times iwstrict learns one audited benign flow: round(1/a), capped at `cap`."""
    return max(1, min(cap, int(round(1.0 / audit_rate)))) if audit_rate > 0 else 1


def _mask(seed: int, salt: int, rate: float, n: int) -> np.ndarray:
    """Reproducible Bernoulli(rate) mask, identical for every policy and scenario (paired runs)."""
    rng = np.random.default_rng([int(seed), int(salt), int(round(rate * 10000))])
    return rng.random(n) < rate


def replay(model: MABTSE, S, y, names, att, policy: str, audit_rate: float, flip, audit,
           per_arm: bool, label: str, progress: bool, cap: int = IW_CAP, frame=None,
           audit_mode: str = "random", seed: int = 0) -> dict:
    """One test-stream replay under one label source (flip mask) and update policy.

    frame: optional mask of injected framing flows (labelled DDoS, the truth for bot traffic).
    audit_mode: "random" uses the precomputed `audit` mask; "uncertain" audits the least
    certain verdicts (target share audit_rate, online budget controller); "mixed" = the
    precomputed mask at half the rate OR uncertainty at the other half (the caller passes the
    half-rate mask)."""
    m = copy.deepcopy(model)
    learners = m.learners
    d0 = drift_counts(learners)
    n = len(y)
    frame = np.zeros(n, dtype=bool) if frame is None else frame
    preds = np.zeros(n, dtype=int)
    audited = np.zeros(n, dtype=bool)
    arm_preds = {a: np.zeros(n, dtype=int) for a in m.names} if per_arm else None
    sel = Counter()
    cnt = Counter()
    unc_target = {"uncertain": audit_rate, "mixed": audit_rate / 2.0}.get(audit_mode, 0.0)
    # Uncertainty audits: a budget of unc_target audits per flow (credit), spent on flows whose
    # uncertainty is in the top unc_target share of the last 500 verdicts (threshold refreshed
    # every 50 flows). Long-run audit rate = unc_target exactly; ties degrade to even spacing.
    u_hist = collections.deque(maxlen=500)
    thr, credit = 0.0, 0.0
    n_ben_lab, n_ben_wrong = 0, 0                            # noiseaware: audited benign-labelled flows
    coin = np.random.default_rng([int(seed), 17])            # noiseaware's Bernoulli draws
    it = range(n)
    if progress:
        it = tqdm(it, desc=label, unit="smp", leave=False)
    for i in it:
        x = to_dict(S[i], names)
        # predict_proba_one + argmax == predict_one (same single selector draw): v13-identical.
        proba = m.predict_proba_one(x)
        p = max(proba, key=proba.get) if proba else None
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
        if frame[i]:
            lab = 1                                          # framing flow: bot traffic, labelled DDoS
        else:
            lab = 0 if (att[i] and flip[i]) else y_true     # poisoned label for attacker flows
        if policy == "vanilla":
            m.learn_one(x, lab)
            cnt["learn"] += 1
            cnt["selector_updates"] += 1
            cnt["poisoned_learned"] += int(lab != y_true)
            cnt["frame_learned"] += int(frame[i])
            continue
        is_audit = bool(audit[i])
        if unc_target > 0:
            p1 = float(proba.get(1, 0.0)) if proba else 0.5
            u = 1.0 - abs(2.0 * p1 - 1.0)                    # 1 = coin flip, 0 = certain
            u_hist.append(u)
            if len(u_hist) % 50 == 0 or len(u_hist) < 50:
                thr = float(np.quantile(np.fromiter(u_hist, float), 1.0 - unc_target))
            credit = min(credit + unc_target, 50.0)
            if not is_audit and credit >= 1.0 and u >= thr:
                credit -= 1.0
                is_audit = True
        audited[i] = is_audit
        if is_audit:                                         # verified label: the truth
            m.learn_one(x, y_true, update_selector=True)
            reps = iw_copies(audit_rate, cap) if (policy in IW_KINDS and y_true == 0) else 1
            for _ in range(reps - 1):                        # iwstrict: the 1/a benign flows it stands for
                m.learn_one(x, y_true, update_selector=False)
            cnt["audited"] += 1
            cnt["learn"] += reps
            cnt["selector_updates"] += 1
            cnt["frame_learned"] += int(frame[i])
            if lab == 0:
                n_ben_lab += 1
                n_ben_wrong += int(y_true == 1)
            continue
        if policy == "noiseaware" and lab == 0:
            rho = (n_ben_wrong + 1.0) / (n_ben_lab + 2.0)
            skip = coin.random() < rho
        else:
            skip = ((policy == "guard" and lab == 0 and preds[i] == 1)
                    or (policy in ("strict", "iwstrict", "consensus", "iwconsensus") and lab == 0)
                    or (policy in ("consensus", "iwconsensus") and lab == 1 and preds[i] == 0))
        if skip:
            cnt["skipped"] += 1                              # unverified label not applied
            cnt["poisoned_blocked"] += int(lab != y_true)
            cnt["frame_blocked"] += int(frame[i])
        else:
            m.learn_one(x, lab, update_selector=False)
            cnt["learn"] += 1
            cnt["poisoned_learned"] += int(lab != y_true)
            cnt["frame_learned"] += int(frame[i])
    drifts = {k: v - d0.get(k, 0) for k, v in drift_counts(learners).items()}
    post = {a: round(m.alpha[a] / (m.alpha[a] + m.beta[a]), 4) for a in m.names}
    return {"preds": preds, "arm_preds": arm_preds, "sel": sel, "counts": cnt,
            "drifts": drifts, "posterior_mean": post, "names": list(m.names), "audited": audited}


def score(out: dict, y: np.ndarray, att: np.ndarray, frame=None, pos=None, frame_end=None) -> dict:
    """Metrics on the GENUINE flows (framing flows excluded). pos: each row's position in the
    original test stream (for the per-tenth curves); frame_end: where the framing campaign
    stops, in original positions."""
    preds = out["preds"]
    n = len(y)
    keep = np.ones(n, dtype=bool) if frame is None else ~frame
    pos = np.arange(n) if pos is None else pos
    bm = BinaryMetrics()
    for yt, yp in zip(y[keep], preds[keep]):
        bm.update(int(yt), int(yp))
    r = dict(bm.as_dict())
    a_k = att & keep
    ben = (y == 0) & keep
    r["asr"] = share(a_k, preds == 0)
    n_orig = int(pos[keep].max()) + 1 if keep.any() else 1
    bounds = np.cumsum([len(c) for c in np.array_split(np.arange(n_orig), 10)])   # as v13's array_split
    tenth = np.clip(np.searchsorted(bounds, pos, side="right"), 0, 9)
    r["asr_by_tenth"] = [share(a_k & (tenth == k), preds == 0) for k in range(10)]
    r["fpr_by_tenth"] = [share(ben & (tenth == k), preds == 1) for k in range(10)]
    if frame is not None and frame.any() and frame_end is not None:
        r["fpr_frame_window"] = share(ben & (pos < frame_end), preds == 1)
        r["fpr_after_window"] = share(ben & (pos >= frame_end), preds == 1)
        r["frame_flagged"] = share(frame, preds == 1)
    steps = max(1, n)
    for a in out["names"]:
        r[f"sel_{a}"] = round(100.0 * out["sel"][a] / steps, 2)
    c = out["counts"]
    for k in ("learn", "selector_updates", "audited", "skipped", "poisoned_learned", "poisoned_blocked",
              "frame_learned", "frame_blocked"):
        r[f"n_{k}"] = int(c.get(k, 0))
    r["audited_attacker_share"] = share(a_k, out["audited"]) if "audited" in out else None
    r["drifts_total"] = int(sum(out["drifts"].values()))
    r["drifts"] = out["drifts"]
    r["posterior_mean"] = out["posterior_mean"]
    if out["arm_preds"] is not None:
        r["arm_asr"] = {a: share(a_k, v == 0) for a, v in out["arm_preds"].items()}
        r["arm_fpr"] = {a: share(ben, v == 1) for a, v in out["arm_preds"].items()}
    return r


def frame_stream(S_sc, y_te, att, S_ben, n_frame: int, span_end: int, seed: int, salt: int):
    """Insert n_frame framing flows (rows of S_ben, sampled with replacement) at random positions
    before original position span_end. Returns (S, y, att, frame, pos, src) where src maps each
    row to its original test index (-1 for framing rows)."""
    rng = np.random.default_rng([int(seed), int(salt), 23])
    n_te = len(y_te)
    at = np.sort(rng.integers(0, max(1, span_end), size=n_frame))       # insert before these positions
    rows = rng.integers(0, len(S_ben), size=n_frame)
    order_src, order_frame_row = [], []
    k = 0
    for i in range(n_te):
        while k < n_frame and at[k] <= i:
            order_src.append(-1)
            order_frame_row.append(rows[k])
            k += 1
        order_src.append(i)
        order_frame_row.append(-1)
    src = np.asarray(order_src, dtype=int)
    frame = src < 0
    fr = np.asarray(order_frame_row, dtype=int)
    S = np.where(frame[:, None], S_ben[np.clip(fr, 0, None)], S_sc[np.clip(src, 0, None)])
    y = np.where(frame, 1, y_te[np.clip(src, 0, None)])
    a = np.where(frame, False, att[np.clip(src, 0, None)])
    # each framing row takes the original position it was inserted before
    pos = np.where(frame, np.maximum.accumulate(np.where(frame, -1, src)) + 1, src)
    return S, y, a, frame, pos, src


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
    ap.add_argument("--policies", nargs="+", default=None,
                    help="vanilla, audit:a, guard:a, strict:a, iwstrict:a[:cap], consensus:a, iwconsensus:a[:cap], noiseaware:a")
    ap.add_argument("--audits", default=None, choices=AUDIT_MODES,
                    help="how audited flows are chosen: random (default), uncertain or mixed")
    ap.add_argument("--frame-span", type=float, default=None,
                    help="share of the test stream during which framing flows are sent (default 0.5)")
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
    src_of = {s: parse_source(s) for s in label_specs}
    q_of = {s: v[0] for s, v in src_of.items()}
    pol_of = {s: parse_policy(s) for s in policy_specs}
    audit_mode = args.audits or L.get("audits", "random")
    if audit_mode not in AUDIT_MODES:
        sys.exit(f"[loop] unknown audit mode {audit_mode!r}; use {', '.join(AUDIT_MODES)}")
    frame_span = args.frame_span if args.frame_span is not None else float(L.get("frame_span", 0.5))
    if not 0.0 < frame_span <= 1.0:
        sys.exit("[loop] --frame-span must be in (0, 1]")
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
    # Masks live in ORIGINAL test positions, so the attacker's flows get the same flips and
    # audits in every run (paired); framing flows draw their own masks.
    flips = {s: _mask(seed, 7, q, n_te) for s, q in q_of.items()}
    mask_rate = (lambda a: a / 2.0) if audit_mode == "mixed" else (lambda a: a)
    audits = {s: (_mask(seed, 11, mask_rate(a), n_te) if audit_mode != "uncertain"
                  else np.zeros(n_te, dtype=bool)) for s, (_, a, _) in pol_of.items()}
    S_ben = S[:n_tr][y[:n_tr] == 0]           # what the framing bots replay: benign TRAINING flows
    span_end = int(round(frame_span * n_te))
    rows_out = []
    for sc in scen:
        runs = [("frozen", "frozen")] + [(ls, ps) for ls in label_specs for ps in policy_specs]
        for ls, ps in runs:
            kind, a, cap = ("frozen", 0.0, IW_CAP) if ps == "frozen" else pol_of[ps]
            flip = np.zeros(n_te, dtype=bool) if ls == "frozen" else flips[ls]
            audit = np.zeros(n_te, dtype=bool) if ps == "frozen" else audits[ps]
            r_frame = 0.0 if ls == "frozen" else src_of[ls][1]
            S_run, y_run, att_run, frame, pos = sc["S"], y_te, att, None, None
            if r_frame > 0 and len(S_ben):
                n_frame = int(round(r_frame * n_te))
                S_run, y_run, att_run, frame, pos, src = frame_stream(
                    sc["S"], y_te, att, S_ben, n_frame, span_end, seed, salt=int(round(r_frame * 10000)))
                fsalt = 19 + int(round(r_frame * 10000))
                flip = np.where(frame, False, flip[np.clip(src, 0, None)])
                audit = np.where(frame, _mask(seed, fsalt, mask_rate(a), len(src)) if audit_mode != "uncertain"
                                 else False, audit[np.clip(src, 0, None)])
            t = time.perf_counter()
            out = replay(model, S_run, y_run, names, att_run, kind, a, flip, audit,
                         per_arm=(ps == "frozen"), label=f"{sc['scenario']} {ls} {ps}",
                         progress=progress, cap=cap, frame=frame, audit_mode=audit_mode, seed=seed)
            r = {"scenario": sc["scenario"], "attack": sc["attack"], "variant": sc["variant"],
                 "learning": ls, "policy": ps, "poison_q": 0.0 if ls == "frozen" else q_of[ls],
                 "frame_rate": r_frame, "audit_rate": a, "audit_mode": audit_mode,
                 "iw_cap": cap if kind in IW_KINDS else None,
                 **score(out, y_run, att_run, frame=frame, pos=pos,
                         frame_end=span_end if frame is not None else None)}
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
                     "surrogate": sur_kind, "audits": audit_mode, "frame_span": frame_span},
        "attacks": attack_info, "scenarios": rows_out,
        "versions": versions, "elapsed_s": round(time.perf_counter() - t_start, 1),
        "finished_at": dt.datetime.now().isoformat(timespec="seconds"),
    }
    json.dump(result, open(out_path, "w"), indent=2, default=str)
    nested = ("asr_by_tenth", "fpr_by_tenth", "drifts", "posterior_mean", "arm_asr", "arm_fpr")
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
