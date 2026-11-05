"""Paired statistics over seeds for the paper's headline comparisons.

What it does: reads the per-seed result JSONs of the grids (one file per dataset x seed),
and for each comparison reports, per dataset and condition,
  * the mean over seeds with a 95% percentile-bootstrap confidence interval (10,000 resamples),
  * the paired difference to a baseline condition (same seed: the runs share data, model
    initialisation, attacker and audit masks), summarised by its median,
  * a two-sided Wilcoxon signed-rank test on the per-seed differences, Holm-corrected within
    the comparison (all datasets x conditions of one comparison form one family),
  * the matched-pairs rank-biserial correlation (effect size, -1..1) and how many seeds
    moved in the same direction ("wins").
Why paired Wilcoxon: the per-seed differences are not normal (several are bimodal across
seeds, e.g. CICIoT2023 transfer attacks), and the exact test makes no distributional
assumption. Its smallest attainable two-sided p-value is 2 / 2^n: 0.25 at n = 3, 0.031 at
n = 6, 6.1e-5 at n = 15 -- three seeds can never be significant, fifteen can.

Usage (repo root, msaad environment active):
    python scripts\\stats.py                      # every preset whose results exist (tag s15)
    python scripts\\stats.py --preset loop        # one preset (loop, attack, advtrain, cascade, frame,
                                                  # audits, frameunc, lowbudget, radp)
    python scripts\\stats.py --tag ""             # the untagged 3-seed grids instead
v14d: the frameunc preset compares uncertainty-directed with random audits on all three datasets
(under attack, under full poisoning, under framing during and after the campaign, and under the
combined attack once the optional combounc grid exists) and against vanilla. A comparison's key or
split may list several fields (shown joined by " | "), and may name the grids ("tags") it reads.
Outputs results\\paper\\stats_<preset>.csv and stats_<preset>.tex (booktabs), and prints the tables.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats as st

ROOT = Path(__file__).resolve().parents[1]
NAMES = {"iotid20": "IoTID20", "iotid20_campaign": "IoTID20 (P2)", "ciciot2023": "CICIoT2023",
         "cicids2017": "CIC-IDS2017", "synthetic": "Synthetic"}

# Each comparison: rows selected by `where`, grouped by `key`; every group is compared with
# the `baseline` group of the same dataset and seed. `only` restricts the compared groups.
PRESETS = {
    "loop": {"folder": "loop_grid", "comparisons": [
        {"name": "ASR (%), evasion + full poisoning (q = 1)", "metric": "asr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0"}},
        {"name": "ASR (%), evasion + half poisoning (q = 0.5)", "metric": "asr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:0.5"}},
        {"name": "ASR (%), evasion + quarter poisoning (q = 0.25)", "metric": "asr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:0.25"}},
        {"name": "ASR (%), poisoning alone (q = 1)", "metric": "asr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "clean", "learning": "poison:1.0"}},
        {"name": "FPR (%), clean traffic, true labels", "metric": "fpr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "clean", "learning": "true"}},
        {"name": "FPR (%), under attack, true labels", "metric": "fpr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"}},
        {"name": "IW-strict vs strict: FPR (%) under attack, true labels", "metric": "fpr", "key": "policy",
         "baseline": "strict:0.1", "only": ["iwstrict:0.1"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"}},
        {"name": "IW-strict vs strict: ASR (%), evasion + full poisoning", "metric": "asr", "key": "policy",
         "baseline": "strict:0.1", "only": ["iwstrict:0.1"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0"}},
    ]},
    "frame": {"folder": "loop_grid", "tag_default": "frame", "comparisons": [
        {"name": "Framing damage: FPR (%) on genuine benign flows vs true labels, same policy", "metric": "fpr",
         "key": "learning", "baseline": "true", "only": ["frame:0.02", "frame:0.1", "poison:1.0+frame:0.05"],
         "where": {"scenario": "clean"}, "split": "policy"},
        {"name": "Policies under framing (10%): FPR (%) vs strict", "metric": "fpr", "key": "policy",
         "baseline": "strict:0.1", "where": {"scenario": "clean", "learning": "frame:0.1"}},
        {"name": "Recovery: FPR (%) after the framing campaign (10%) vs strict", "metric": "fpr_after_window",
         "key": "policy", "baseline": "strict:0.1", "where": {"scenario": "clean", "learning": "frame:0.1"}},
        {"name": "Evasion + full poisoning + framing (5%): ASR (%) vs vanilla", "metric": "asr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0+frame:0.05"}},
        {"name": "Evasion + full poisoning + framing (5%): FPR (%) vs vanilla", "metric": "fpr", "key": "policy",
         "baseline": "vanilla", "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0+frame:0.05"}},
        {"name": "Price of consensus: ASR (%) under evasion, true labels, vs strict", "metric": "asr", "key": "policy",
         "baseline": "strict:0.1", "only": ["consensus:0.1", "iwconsensus:0.1"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"}},
    ]},
    "audits": {"folder": "loop_grid", "tags": {"s15": {"audit_mode": "random"}, "audits": {}, "auditsmix": {}},
               "comparisons": [
        {"name": "Audit allocation: ASR (%), evasion + full poisoning, vs random audits", "metric": "asr",
         "key": "audit_mode", "baseline": "random", "split": "policy",
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1"]}},
        {"name": "Audit allocation: share (%) of attacker flows audited, vs random audits",
         "metric": "audited_attacker_share", "key": "audit_mode", "baseline": "random", "split": "policy",
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1"]}},
        {"name": "Audit allocation: FPR (%) under attack, true labels, vs random audits", "metric": "fpr",
         "key": "audit_mode", "baseline": "random", "split": "policy",
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1"]}},
    ]},
    # v14d: uncertainty-directed audits on all three datasets, and framing with random vs uncertainty
    # audits. Random audits come from the s15 and frame grids, uncertainty audits from the audits,
    # frameunc and (optional) combounc grids; each comparison names the grids it reads ("tags").
    # A configuration repeated in two grids gives bit-identical results, so overlap is harmless.
    # vanilla never audits: its audit mode is recorded as "none" (see load_rows).
    "frameunc": {"folder": "loop_grid", "stem_tag": "",
                 "tags": {"s15": {"audit_mode": "random"}, "frame": {"audit_mode": "random"}, "audits": {},
                          "frameunc": {}, "combounc": {}},
                 "comparisons": [
        {"name": "Audits: FPR (%) under attack, true labels, uncertainty vs random audits", "metric": "fpr",
         "key": "audit_mode", "baseline": "random", "split": "policy", "tags": ["frame", "frameunc"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1", "iwconsensus:0.1"]}},
        {"name": "Audits: audits used under attack, true labels, uncertainty vs random audits (budget check)",
         "metric": "n_audited", "key": "audit_mode", "baseline": "random", "split": "policy",
         "tags": ["frame", "frameunc"], "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1", "iwconsensus:0.1"]}},
        {"name": "Audits: FPR (%) under attack, true labels, uncertainty audits vs vanilla", "metric": "fpr",
         "key": ["policy", "audit_mode"], "baseline": "vanilla | none", "tags": ["frame", "frameunc"],
         "only": ["strict:0.1 | uncertain", "iwstrict:0.1 | uncertain", "iwconsensus:0.1 | uncertain"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"}},
        {"name": "Audits: ASR (%), evasion + full poisoning, uncertainty vs random audits", "metric": "asr",
         "key": "audit_mode", "baseline": "random", "split": "policy",
         "tags": ["s15", "audits", "frameunc", "combounc"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1"]}},
        {"name": "Audits: FPR (%), evasion + full poisoning, uncertainty vs random audits", "metric": "fpr",
         "key": "audit_mode", "baseline": "random", "split": "policy",
         "tags": ["s15", "audits", "frameunc", "combounc"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1"]}},
        {"name": "Framing: FPR (%) over the whole stream, uncertainty vs random audits", "metric": "fpr",
         "key": "audit_mode", "baseline": "random", "split": ["policy", "learning", "scenario"],
         "tags": ["frame", "frameunc"],
         "where_in": {"learning": ["frame:0.02", "frame:0.1"],
                      "policy": ["strict:0.1", "iwstrict:0.1", "iwconsensus:0.1"]}},
        {"name": "Framing: FPR (%) after the campaign, uncertainty vs random audits", "metric": "fpr_after_window",
         "key": "audit_mode", "baseline": "random", "split": ["policy", "learning", "scenario"],
         "tags": ["frame", "frameunc"],
         "where_in": {"learning": ["frame:0.02", "frame:0.1"],
                      "policy": ["strict:0.1", "iwstrict:0.1", "iwconsensus:0.1"]}},
        {"name": "Framing: FPR (%) over the whole stream, uncertainty audits vs vanilla", "metric": "fpr",
         "key": ["policy", "audit_mode"], "baseline": "vanilla | none", "split": ["learning", "scenario"],
         "tags": ["frame", "frameunc"],
         "only": ["strict:0.1 | uncertain", "iwstrict:0.1 | uncertain", "iwconsensus:0.1 | uncertain"],
         "where_in": {"learning": ["frame:0.02", "frame:0.1"]}},
        {"name": "Framing: FPR (%) after the campaign, uncertainty audits vs vanilla", "metric": "fpr_after_window",
         "key": ["policy", "audit_mode"], "baseline": "vanilla | none", "split": ["learning", "scenario"],
         "tags": ["frame", "frameunc"],
         "only": ["strict:0.1 | uncertain", "iwstrict:0.1 | uncertain", "iwconsensus:0.1 | uncertain"],
         "where_in": {"learning": ["frame:0.02", "frame:0.1"]}},
        {"name": "Evasion + full poisoning + framing (5%): ASR (%), uncertainty vs random audits", "metric": "asr",
         "key": "audit_mode", "baseline": "random", "split": "policy", "tags": ["frame", "combounc"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0+frame:0.05"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1", "iwconsensus:0.1"]}},
        {"name": "Evasion + full poisoning + framing (5%): FPR (%), uncertainty vs random audits", "metric": "fpr",
         "key": "audit_mode", "baseline": "random", "split": "policy", "tags": ["frame", "combounc"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0+frame:0.05"},
         "where_in": {"policy": ["strict:0.1", "iwstrict:0.1", "iwconsensus:0.1"]}},
        {"name": "Evasion + full poisoning + framing (5%): ASR (%), uncertainty audits vs vanilla", "metric": "asr",
         "key": ["policy", "audit_mode"], "baseline": "vanilla | none", "tags": ["frame", "combounc"],
         "only": ["strict:0.1 | uncertain", "iwstrict:0.1 | uncertain", "iwconsensus:0.1 | uncertain"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0+frame:0.05"}},
    ]},
    "lowbudget": {"folder": "loop_grid", "tag_default": "lowbudget", "comparisons": [
        {"name": "Weight clipping at 5% audits: FPR (%) under attack, true labels, vs strict", "metric": "fpr",
         "key": "policy", "baseline": "strict:0.05", "only": ["iwstrict:0.05", "iwstrict:0.05:5", "iwstrict:0.05:10"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"}},
        {"name": "Weight clipping at 2% audits: FPR (%) under attack, true labels, vs strict", "metric": "fpr",
         "key": "policy", "baseline": "strict:0.02", "only": ["iwstrict:0.02:10"],
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "true"}},
        {"name": "Low budgets: ASR (%), evasion + full poisoning, vs strict at 10%", "metric": "asr",
         "key": "policy", "baseline": "strict:0.1",
         "where": {"scenario": "pgd/attack_only/feasible", "learning": "poison:1.0"}},
        {"name": "Noise-rate baseline: FPR (%) on clean traffic, true labels, vs strict", "metric": "fpr",
         "key": "policy", "baseline": "strict:0.1", "only": ["noiseaware:0.1"],
         "where": {"scenario": "clean", "learning": "true"}},
    ]},
    "attack": {"folder": "attack_grid", "comparisons": [
        {"name": "ASR (%), no labels vs instant labels", "metric": "asr", "key": "learning",
         "baseline": "online", "only": ["frozen"], "where_in": {"scenario": [
             "pgd/attack_only", "pgd/attack_only/feasible", "cw/attack_only", "cw/attack_only/feasible"]},
         "split": "scenario"},
        {"name": "ASR (%), delayed vs instant labels", "metric": "asr", "key": "learning",
         "baseline": "online", "only": ["delay:1000", "delay:5000"],
         "where_in": {"scenario": ["pgd/attack_only", "cw/attack_only"]}, "split": "scenario"},
        {"name": "ASR (%), repaired vs raw attack, no labels", "metric": "asr", "key": "variant",
         "baseline": "raw", "only": ["feasible"], "where": {"learning": "frozen"}, "split": "attack"},
    ]},
    "advtrain": {"folder": "advtrain_grid", "comparisons": [
        {"name": "ASR (%), repaired attacks, no labels: adversarial training vs none", "metric": "asr",
         "key": "at", "baseline": "none", "where": {"learning": "frozen", "variant": "feasible"}, "split": "attack"},
        {"name": "FPR (%), clean traffic, no labels: adversarial training vs none", "metric": "fpr",
         "key": "at", "baseline": "none", "where": {"learning": "frozen", "scenario": "clean"}},
    ]},
    # v14c: the chain of detectors (stage 1 MABTSE, 2 online MLP, 3 host graph); 15 seeds, tag s15.
    "cascade": {"folder": "cascade_grid", "comparisons": [
        {"name": "Chain: ASR (%) left after each chain vs MABTSE alone, repaired attacks, no labels",
         "metric": "asr", "key": "chain", "baseline": "S1",
         "only": ["S1+S2", "S1+S3:ctx", "S1+S3:gnn_full", "S1+S3:gnn_drift", "S1+S2+S3:gnn_drift"],
         "where": {"learning": "frozen"},
         "where_in": {"scenario": ["pgd/attack_only/feasible", "cw/attack_only/feasible"]}, "split": "scenario"},
        {"name": "Chain: FPR (%) on clean traffic vs MABTSE alone, no labels", "metric": "fpr", "key": "chain",
         "baseline": "S1", "only": ["S1+S2", "S1+S3:ctx", "S1+S3:gnn_full", "S1+S3:gnn_drift", "S1+S2+S3:gnn_drift"],
         "where": {"scenario": "clean", "learning": "frozen"}},
        {"name": "Message passing vs the matched control: ASR (%) after MABTSE + stage 3, repaired attacks",
         "metric": "asr", "key": "chain", "baseline": "S1+S3:ctx", "only": ["S1+S3:gnn_full", "S1+S3:gnn_drift"],
         "where": {"learning": "frozen"},
         "where_in": {"scenario": ["pgd/attack_only/feasible", "cw/attack_only/feasible"]}, "split": "scenario"},
        {"name": "Graph-aware attacker: ASR (%) after the full chain vs plain repaired PGD", "metric": "asr",
         "key": "scenario", "baseline": "pgd/attack_only/feasible",
         "only": ["pgd/attack_only/feasible/spoof:10", "pgd/attack_only/feasible/thin:0.25"],
         "where": {"learning": "frozen", "chain": "S1+S2+S3:gnn_drift"}},
        {"name": "Chain with fully poisoned labels (1,000-flow delay): ASR (%) strict vs vanilla, repaired PGD",
         "metric": "asr", "key": "learning", "baseline": "delay:1000|poison:1.0|vanilla",
         "only": ["delay:1000|poison:1.0|strict:0.1"], "where": {"scenario": "pgd/attack_only/feasible"},
         "where_in": {"chain": ["S1", "S1+S2", "S1+S2+S3:gnn_drift"]}, "split": "chain"},
    ]},
    "radp": {"folder": "radp_grid", "tag_default": "", "comparisons": [
        {"name": "End-to-end ASR (%) with RADP vs the frozen detector alone", "metric": "e2e_asr",
         "paired_metric": "asr_no_radp", "key": "rad", "where": {"learning": "frozen"}, "split": "scenario",
         "baseline_label": "the same runs without RADP"},
    ]},
}


NO_AUDIT = ("vanilla", "frozen")   # policies that never audit: audit mode recorded as "none"


def load_rows(folder: Path, tag: str, fill=None):
    """Scenario rows of every <data>_seed<k>[_<tag>].json in folder, with dataset, seed and the
    file tag (_tag). fill: values for fields older result files lack (e.g. audit_mode = random
    for v13 runs). Policies that never audit get audit_mode "none", whatever the grid's setting."""
    out = []
    for f in sorted(folder.glob("*.json")) if folder.exists() else []:
        m = re.fullmatch(r"(.+?)_seed(\d+)(?:_(.+))?\.json", f.name)
        if not m or (m.group(3) or "") != tag:
            continue
        try:
            r = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for s in r.get("scenarios", []):
            row = {**(fill or {}), **s, "dataset": r.get("dataset", m.group(1)), "seed": int(r.get("seed", m.group(2))),
                   "_tag": tag}
            for k, v in (fill or {}).items():
                if row.get(k) is None:
                    row[k] = v
            if row.get("policy") in NO_AUDIT and "audit_mode" in row:
                row["audit_mode"] = "none"
            out.append(row)
    return out


def _val(row, fields):
    """A row's value for one field, or ' | '-joined values for a list of fields (composite key)."""
    if isinstance(fields, (list, tuple)):
        return " | ".join(str(row.get(f)) for f in fields)
    return row.get(fields)


def _match(row, comp):
    if "tags" in comp and row.get("_tag") not in comp["tags"]:
        return False
    for k, v in comp.get("where", {}).items():
        if row.get(k) != v:
            return False
    for k, vs in comp.get("where_in", {}).items():
        if row.get(k) not in vs:
            return False
    for k, p in comp.get("where_prefix", {}).items():
        if not str(row.get(k, "")).startswith(p):
            return False
    return True


def boot_ci(vals, n_boot=10_000, seed=0):
    vals = np.asarray(vals, float)
    if len(vals) < 2:
        return (float(vals[0]), float(vals[0])) if len(vals) else (None, None)
    rng = np.random.default_rng(seed)
    means = vals[rng.integers(0, len(vals), size=(n_boot, len(vals)))].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def wilcoxon(d):
    """Two-sided Wilcoxon signed-rank p-value and matched-pairs rank-biserial correlation."""
    d = np.asarray(d, float)
    nz = d[d != 0]
    if len(nz) == 0:
        return 1.0, 0.0
    ranks = st.rankdata(np.abs(nz))
    rb = float((ranks[nz > 0].sum() - ranks[nz < 0].sum()) / ranks.sum())
    try:
        p = float(st.wilcoxon(d, zero_method="pratt", alternative="two-sided").pvalue)
    except ValueError:
        p = 1.0
    return p, rb


def holm(ps):
    """Holm-Bonferroni adjusted p-values (same order as the input)."""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    adj, run = [0.0] * m, 0.0
    for rank, i in enumerate(order):
        run = max(run, min(1.0, (m - rank) * ps[i]))
        adj[i] = run
    return adj


def run_comparison(rows, comp):
    """One family of paired tests. Returns result dicts (Holm applied across the family)."""
    sel = [r for r in rows if _match(r, comp)]
    key, metric = comp["key"], comp["metric"]
    split = comp.get("split")
    # values[(dataset, split value, group)][seed] = metric
    values = defaultdict(dict)
    for r in sel:
        v = r.get(metric)
        if v is None:
            continue
        sp = _val(r, split) if split else ""
        values[(r["dataset"], sp, _val(r, key))][r["seed"]] = float(v)
        if comp.get("paired_metric") and r.get(comp["paired_metric"]) is not None:
            values[(r["dataset"], sp, f"{_val(r, key)} (without)")][r["seed"]] = float(r[comp["paired_metric"]])
    results = []
    for (ds, sp, grp), by_seed in sorted(values.items(), key=lambda kv: (kv[0][0], str(kv[0][1]), str(kv[0][2]))):
        if comp.get("paired_metric"):
            if grp.endswith(" (without)"):
                continue
            base = values.get((ds, sp, f"{grp} (without)"), {})
            base_name = f"{grp} without"
        else:
            if grp == comp["baseline"] or (comp.get("only") and grp not in comp["only"]):
                continue
            base = values.get((ds, sp, comp["baseline"]), {})
            base_name = comp["baseline"]
        seeds = sorted(set(by_seed) & set(base))
        if not seeds:
            continue
        a = np.array([by_seed[s] for s in seeds])
        b = np.array([base[s] for s in seeds])
        d = a - b
        p, rb = wilcoxon(d)
        lo, hi = boot_ci(a)
        blo, bhi = boot_ci(b)
        results.append({"comparison": comp["name"], "dataset": ds, "split": sp, "group": grp,
                        "baseline": base_name, "n": len(seeds), "mean": float(a.mean()), "ci_lo": lo, "ci_hi": hi,
                        "base_mean": float(b.mean()), "base_ci_lo": blo, "base_ci_hi": bhi,
                        "median_diff": float(np.median(d)), "mean_diff": float(d.mean()),
                        "wins_lower": int((d < 0).sum()), "wins_higher": int((d > 0).sum()),
                        "p": p, "rank_biserial": rb})
    for r, pa in zip(results, holm([r["p"] for r in results])):
        r["p_holm"] = pa
    return results


def _short(text) -> str:
    """Display form of a condition: composite values joined by commas, long scenario names shortened."""
    return (str(text).replace(" | ", ", ").replace("pgd/attack_only/feasible", "repaired PGD")
            .replace("cw/attack_only/feasible", "repaired C&W"))


def fmt_p(p):
    return "--" if p is None else ("<1e-4" if p < 1e-4 else f"{p:.4f}")


def write_outputs(preset: str, results, out_dir: Path, tag: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"stats_{preset}" + (f"_{tag.replace('+', '_')}" if tag and tag != "s15" else "")
    if results:
        with open(out_dir / f"{stem}.csv", "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(results[0].keys()))
            w.writeheader()
            w.writerows(results)
    lines = ["\\begin{table*}[t]", "\\centering",
             f"\\caption{{Paired statistics over seeds ({preset}): mean with 95\\% bootstrap CI, the median per-seed "
             "difference to the baseline, two-sided Wilcoxon signed-rank test (Holm-corrected within each "
             "comparison) and the matched-pairs rank-biserial correlation $r$.}}",
             f"\\label{{tab:{stem}}}", "\\footnotesize", "\\setlength{\\tabcolsep}{3pt}",
             "\\begin{tabular}{lllcccccc}", "\\toprule",
             "Comparison & Dataset & Condition & $n$ & Mean [95\\% CI] & Baseline mean & Median $\\Delta$ & "
             "$p_\\mathrm{Holm}$ & $r$ \\\\", "\\midrule"]
    esc = lambda s: str(s).replace("&", "\\&").replace("_", "\\_").replace("%", "\\%")  # noqa: E731
    last = None
    for r in results:
        comp = esc(r["comparison"]) if r["comparison"] != last else ""
        last = r["comparison"]
        cond = esc(_short(r["group"])) + (f" ({esc(_short(r['split']))})" if r["split"] else "")
        lines.append(f"{comp} & {esc(NAMES.get(r['dataset'], r['dataset']))} & {cond} & {r['n']} & "
                     f"{r['mean']:.2f} [{r['ci_lo']:.2f}, {r['ci_hi']:.2f}] & {r['base_mean']:.2f} & "
                     f"{r['median_diff']:+.2f} & {fmt_p(r['p_holm'])} & {r['rank_biserial']:+.2f} \\\\")
    lines += ["\\bottomrule", "\\end{tabular}", "\\end{table*}", ""]
    (out_dir / f"{stem}.tex").write_text("\n".join(lines), encoding="utf-8")
    print(f"[stats] wrote {out_dir / stem}.csv and .tex")


def main() -> int:
    ap = argparse.ArgumentParser(description="Paired seed statistics for the paper.")
    ap.add_argument("--preset", nargs="+", default=None, choices=sorted(PRESETS))
    ap.add_argument("--tag", default=None, help="result-file tag (default: s15; radp: untagged)")
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=None, help="default: <results>\\paper")
    args = ap.parse_args()
    res = Path(args.results)
    out_dir = Path(args.out) if args.out else res / "paper"
    for preset in args.preset or sorted(PRESETS):
        P = PRESETS[preset]
        if "tags" in P:                       # several result sets compared by seed (e.g. audit modes)
            tag = "+".join(P["tags"])
            rows = [r for t, fill in P["tags"].items() for r in load_rows(res / P["folder"], t, fill)]
        else:
            tag = args.tag if args.tag is not None else P.get("tag_default", "s15")
            rows = load_rows(res / P["folder"], tag)
        if not rows:
            print(f"[stats] {preset}: no result files with tag {tag!r} in {res / P['folder']} (skipped)")
            continue
        seeds = sorted({r["seed"] for r in rows})
        print(f"\n=== {preset} (tag {tag!r}; {len(seeds)} seeds: {seeds[0]}..{seeds[-1]}) ===")
        if len(seeds) < 6:
            print("[stats] note: fewer than 6 seeds -- no two-sided Wilcoxon test can reach p < 0.05")
        results = []
        for comp in P["comparisons"]:
            got = run_comparison(rows, comp)
            results += got
            if got:
                print(f"\n  {comp['name']}  (baseline: {_short(comp.get('baseline_label') or got[0]['baseline'])})")
            else:
                print(f"\n  {comp['name']}: no matching runs yet (skipped)")
            for r in got:
                cond = _short(r["group"]) + (f" [{_short(r['split'])}]" if r["split"] else "")
                print(f"    {NAMES.get(r['dataset'], r['dataset']):<13} {cond:<34} n={r['n']:<3} "
                      f"{r['mean']:7.2f} [{r['ci_lo']:6.2f}, {r['ci_hi']:6.2f}]  base {r['base_mean']:7.2f}  "
                      f"med.d {r['median_diff']:+7.2f}  p_holm {fmt_p(r['p_holm']):>7}  r {r['rank_biserial']:+.2f}  "
                      f"lower/higher {r['wins_lower']}/{r['wins_higher']}")
        write_outputs(preset, results, out_dir, P.get("stem_tag", tag))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
