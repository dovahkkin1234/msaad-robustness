"""Make the paper's figures and LaTeX tables from the grid results.

Reads the summary CSVs written by experiments\\run_grid.py (means and standard deviations)
and the per-seed JSONs next to them (to draw every seed), and writes, for every input that
exists:

  figures (PDF for Overleaf + PNG for a quick look), IEEE column widths, 8-pt text:
    fig_attack_asr      evasion rate per attack: instant labels vs no labels vs repaired attack
    fig_label_delay     evasion rate as the label delay grows (online -> no labels, + self-labels)
    fig_radp_detect     RADP: share of perturbed DDoS flows RAD flags (raw / repaired / unseen attack)
    fig_radp_e2e        RADP: DDoS flows that get through end to end, repaired attacks
    fig_loop_poison     S4: evasion rate vs label poisoning q for each update policy
    fig_loop_time       S4: evasion rate over the test stream under full poisoning
    fig_audit_tradeoff  S4: what strict (and IW-strict) buy and cost per verified-label budget
    fig_advtrain        adversarial-training baseline: evasion (repaired attacks, no labels) and
                        false alarms on clean traffic, per training variant
  tables (booktabs; add \\usepackage{booktabs} to the paper):
    tab_repro, tab_attack, tab_radp, tab_loop, tab_audit, tab_advtrain

Bars and lines show the mean over seeds. Every seed is drawn as a small dot when its JSON is
present; where it is not, an error bar shows +/- one standard deviation instead. Tables give
mean +/- std exactly as in the summary CSVs. Missing inputs are skipped with a message, so it
can be re-run as results arrive.

Usage (repo root, msaad environment active; needs matplotlib, see SETUP.md):
    python scripts\\make_figures.py
    python scripts\\make_figures.py --results results --out results\\paper
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

# Categorical slots in fixed order (validated: colour-blind separation passes; slots 3-5 are
# under 3:1 on white, so every series also has a marker or hatch and the tables give the numbers).
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]
GREY = "#7a7a7a"
INK = "#222222"
INK2 = "#52514e"
MARK = ["o", "s", "^", "D", "v"]
HATCH = ["", "////", "....", "xxxx", "\\\\\\\\"]
W1, W2 = 3.5, 7.16           # IEEE single / double column width (inches)
NAMES = {"iotid20": "IoTID20", "ciciot2023": "CICIoT2023", "synthetic": "Synthetic"}
ATK = {"fgsm": "FGSM", "bim": "BIM", "pgd": "PGD", "cw": "C&W"}
PAPER = {"iotid20": {"accuracy": 99.50, "precision": 99.47, "recall": 100.0, "f1": 99.74},
         "ciciot2023": {"accuracy": 99.28, "precision": 98.88, "recall": 96.53, "f1": 97.98}}
# S4 update policies keep one colour, marker and line style in every figure.
POL_SLOT = {"vanilla": 0, "audit": 1, "guard": 2, "strict": 3, "iwstrict": 4}
POL_LS = {"vanilla": "-", "audit": (0, (5, 2)), "guard": "-.", "strict": "-", "iwstrict": (0, (2, 1.2))}
POL_NAME = {"vanilla": "vanilla", "audit": "audit", "guard": "guard", "strict": "strict", "iwstrict": "IW-strict"}

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "axes.spines.top": False,
    "axes.spines.right": False, "axes.grid": True, "grid.color": "#e3e3e3",
    "grid.linewidth": 0.6, "axes.axisbelow": True, "axes.edgecolor": "#555555",
    "lines.linewidth": 1.6, "lines.markersize": 4.5, "legend.frameon": False,
    "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.bbox": "tight", "savefig.dpi": 300,
})


# ---- input helpers --------------------------------------------------------------------
def read(path: Path):
    if not path.exists():
        print(f"[figures] skipped: {path} not found")
        return None
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(v):
    try:
        return None if v in (None, "", "None") else float(v)
    except ValueError:
        return None


def ms(row, metric):
    """(mean, std) of a metric from a summary row, or (None, None)."""
    if row is None:
        return None, None
    return num(row.get(f"{metric}_mean")), num(row.get(f"{metric}_std"))


def pick(rows, **kw):
    for r in rows or []:
        if all(r.get(k) == v for k, v in kw.items()):
            return r
    return None


def datasets_in(rows):
    seen = []
    for r in rows or []:
        if r["dataset"] not in seen:
            seen.append(r["dataset"])
    return seen


def fmt(m, s, d=2):
    return "--" if m is None else (f"{m:.{d}f}" if s is None else f"{m:.{d}f} $\\pm$ {s:.{d}f}")


def seed_runs(folder: Path, tags=None):
    """Scenario rows of the per-seed result JSONs in a grid folder, each tagged with its
    dataset, seed and file tag. tags: which file tags to read ('' = untagged); None = all."""
    out = []
    for f in (sorted(folder.glob("*.json")) if folder.exists() else []):
        mt = re.fullmatch(r"(.+?)_seed(\d+)(?:_(.+))?\.json", f.name)
        if not mt or (tags is not None and (mt.group(3) or "") not in tags):
            continue
        try:
            r = json.load(open(f, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for s in r.get("scenarios", []):
            out.append({**s, "dataset": r.get("dataset", mt.group(1)), "seed": r.get("seed", int(mt.group(2))),
                        "tag": mt.group(3) or ""})
    return out


def per_seed(runs, metric, **kw):
    """One value per seed for the scenario rows matching kw (the first file read wins)."""
    got = {}
    for s in runs or []:
        if s["seed"] not in got and s.get(metric) is not None and all(s.get(k) == v for k, v in kw.items()):
            got[s["seed"]] = float(s[metric])
    return [got[k] for k in sorted(got)]


def stat(row, runs, metric, **kw):
    """(mean, std, per-seed values) of one plotted point. Mean and std come from the summary
    row (the tables print the same numbers); without one, from the per-seed values."""
    vals = per_seed(runs, metric, **kw)
    m, s = ms(row, metric)
    if m is None and vals:
        m = float(np.mean(vals))
        s = statistics.stdev(vals) if len(vals) > 1 else None
    return m, s, vals


def pol_kind(p: str) -> str:
    return p.split(":", 1)[0]


def pol_rate(p: str):
    try:
        return float(p.split(":", 1)[1])
    except (IndexError, ValueError):
        return None


def pol_style(p: str) -> dict:
    k = POL_SLOT.get(pol_kind(p), 0)
    return {"color": C[k], "marker": MARK[k], "linestyle": POL_LS.get(pol_kind(p), "-")}


def pol_label(p: str) -> str:
    a = pol_rate(p)
    name = POL_NAME.get(pol_kind(p), pol_kind(p))
    return name if a is None else f"{name} {100 * a:g}%"


def _q(learning: str):
    return 0.0 if learning == "true" else (float(learning.split(":")[1]) if learning.startswith("poison:") else None)


def find(rows, d, policy, scenario, q):
    """The summary row of one loop run, matching the label source by its q value."""
    for r in rows or []:
        if r["dataset"] == d and r["policy"] == policy and r["scenario"] == scenario and _q(r["learning"]) == q:
            return r
    return None


def loop_rows(res: Path):
    """(main grid rows, rows of every loop grid: main first, then summary_loop_<tag>.csv)."""
    folder = res / "loop_grid"
    main = read(folder / "summary_loop.csv") or []
    rows, have = [], set()
    for part in [main] + [read(f) or [] for f in sorted(folder.glob("summary_loop_*.csv"))]:
        for r in part:
            key = (r["dataset"], r["policy"], r["scenario"], r["learning"])
            if key not in have:
                have.add(key)
                rows.append(r)
    return main, rows


# ---- output helpers -------------------------------------------------------------------
def save(fig, out: Path, name: str):
    for ax in fig.axes:   # percentages: keep the axis inside [0, 100] even when error bars spill over
        lo, hi = ax.get_ylim()
        ax.set_ylim(0, min(hi, 105))
    out.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(out / f"{name}.{ext}")
    plt.close(fig)
    print(f"[figures] wrote {out / name}.pdf (+ .png)")


def write_tex(out: Path, name: str, caption: str, label: str, header, rows, align):
    out.mkdir(parents=True, exist_ok=True)
    env = "table*" if len(header) > 6 else "table"     # wide tables span both columns
    lines = [f"\\begin{{{env}}}[t]", "\\centering", f"\\caption{{{caption}}}", f"\\label{{{label}}}",
             "\\footnotesize", "\\setlength{\\tabcolsep}{3pt}", f"\\begin{{tabular}}{{{align}}}",
             "\\toprule", " & ".join(header) + " \\\\", "\\midrule"]
    lines += [" & ".join(r) + " \\\\" for r in rows]
    lines += ["\\bottomrule", "\\end{tabular}", f"\\end{{{env}}}", ""]
    (out / f"{name}.tex").write_text("\n".join(lines), encoding="utf-8")
    print(f"[figures] wrote {out / name}.tex")


def esc(s: str) -> str:
    return s.replace("&", "\\&").replace("_", "\\_").replace("%", "\\%")


def panels(n, width=W2, height=2.4):
    fig, axes = plt.subplots(1, n, figsize=(width if n > 1 else W1, height), squeeze=False, sharey=True,
                             constrained_layout=True)
    return fig, axes[0]


def top_legend(fig, axes, ncol=None):
    """One legend above all panels (entries gathered from every panel), so it never covers data."""
    hs, ls = [], []
    for ax in np.atleast_1d(axes).ravel():
        for h, lab in zip(*ax.get_legend_handles_labels()):
            if lab not in ls:
                hs.append(h)
                ls.append(lab)
    if hs:
        fig.legend(hs, ls, loc="outside upper center", ncol=ncol or len(hs))


def dots(ax, x, vals, spread, color=INK, size=5.0, alpha=1.0):
    """Every seed as a small dot, spread sideways so equal values stay visible."""
    if not vals:
        return
    off = np.linspace(-spread, spread, len(vals)) if len(vals) > 1 else np.zeros(1)
    ax.scatter(x + off, vals, s=size, color=color, alpha=alpha, zorder=5, linewidths=0)


def spread_marks(ax, x, m, s, vals, spread, color=INK, size=5.0, alpha=1.0):
    """The seeds as dots when their JSONs are present, else a +/- std error bar."""
    if vals:
        dots(ax, x, vals, spread, color, size, alpha)
    elif m is not None and s:
        ax.errorbar([x], [m], yerr=[s], fmt="none", ecolor=color, elinewidth=0.7, capsize=1.5, zorder=4)


def bar_group(ax, xs, pts, width, k, label):
    """Bars at the means in slot k, each seed as a dot on top. Returns the means."""
    means = [p[0] if p[0] is not None else np.nan for p in pts]
    ax.bar(xs, means, width, color=C[k], hatch=HATCH[k], edgecolor="white", linewidth=0.4, label=label)
    for xi, (m, s, vals) in zip(xs, pts):
        spread_marks(ax, xi, m, s, vals, width * 0.28)
    return means


# ---- figures and tables ----------------------------------------------------------------
def repro_table(res: Path, out: Path):
    rows = read(res / "grid" / "summary.csv")
    if not rows:
        return
    body = []
    for r in rows:
        d = r["dataset"]
        cells = [esc(d)] + [fmt(*ms(r, m)) for m in ("accuracy", "precision", "recall", "f1", "fpr")]
        p = PAPER.get(d)
        cells.append("--" if not p else f"{p['accuracy']:.2f}")
        body.append(cells)
    write_tex(out, "tab_repro", "Clean prequential reproduction (mean $\\pm$ std over seeds, \\%). "
              "FPR: benign flows flagged as DDoS. Last column: accuracy reported by the base paper.",
              "tab:repro", ["Stream", "Acc.", "Prec.", "Rec.", "F1", "FPR", "Paper acc."], body, "lcccccc")


def attack_fig_and_table(res: Path, out: Path):
    rows = read(res / "attack_grid" / "summary_attack.csv")
    if not rows:
        return
    runs = seed_runs(res / "attack_grid", tags={""})
    ds = datasets_in(rows)
    fig, axes = panels(len(ds))
    series = [("instant labels", "online", "attack_only"), ("no labels", "frozen", "attack_only"),
              ("no labels, repaired", "frozen", "attack_only/feasible")]
    body = []
    for ax, d in zip(axes, ds):
        atks = [a for a in ATK if pick(rows, dataset=d, scenario=f"{a}/attack_only", learning="frozen")]
        x = np.arange(len(atks))
        w = 0.26
        for k, (lab, learn, suf) in enumerate(series):
            pts = [stat(pick(rows, dataset=d, scenario=f"{a}/{suf}", learning=learn), runs, "asr",
                        dataset=d, scenario=f"{a}/{suf}", learning=learn) for a in atks]
            means = bar_group(ax, x + (k - 1) * w, pts, w * 0.92, k, lab)
            if k == 0:   # near-zero bars: print their value so they are not mistaken for missing
                for xi, mi in zip(x, means):
                    if mi == mi:
                        ax.annotate(f"{mi:.1f}", (xi - w, mi), xytext=(0, 3), textcoords="offset points",
                                    ha="center", va="bottom", fontsize=6, color=INK2)
        ax.set_xticks(x, [ATK[a] for a in atks])
        ax.set_title(NAMES.get(d, d))
        for a in atks:
            on = ms(pick(rows, dataset=d, scenario=f"{a}/attack_only", learning="online"), "asr")
            fr = ms(pick(rows, dataset=d, scenario=f"{a}/attack_only", learning="frozen"), "asr")
            fe = ms(pick(rows, dataset=d, scenario=f"{a}/attack_only/feasible", learning="frozen"), "asr")
            acc = ms(pick(rows, dataset=d, scenario=f"{a}/attack_only", learning="frozen"), "accuracy")
            body.append([esc(NAMES.get(d, d)), esc(ATK[a]), fmt(*on), fmt(*fr), fmt(*fe), fmt(*acc)])
    axes[0].set_ylabel("DDoS flows evading (%)")
    top_legend(fig, axes)
    save(fig, out, "fig_attack_asr")
    write_tex(out, "tab_attack", "Evasion (attack success) rate, \\% of perturbed DDoS flows classified "
              "benign, mean $\\pm$ std over seeds. Instant labels: the base paper's Algorithm~1. "
              "Repaired: the attack restricted to valid traffic.", "tab:attack",
              ["Dataset", "Attack", "Instant labels", "No labels", "No labels, repaired", "Acc., no labels"],
              body, "llcccc")


def label_delay_fig(res: Path, out: Path):
    lab = read(res / "attack_grid" / "summary_attack_labels.csv")
    base = read(res / "attack_grid" / "summary_attack.csv")
    if not lab:
        return
    runs_lab = seed_runs(res / "attack_grid", tags={"labels"})
    runs_base = seed_runs(res / "attack_grid", tags={""})
    ds = datasets_in(lab)
    fig, axes = panels(len(ds))
    for ax, d in zip(axes, ds):
        delays = sorted({int(r["learning"].split(":")[1]) for r in lab
                         if r["dataset"] == d and r["learning"].startswith("delay:")})
        cats = ["instant"] + [f"{k:,}" for k in delays] + ["no labels", "self"]
        x = np.arange(len(cats))
        atks = [a for a in ATK if pick(lab, dataset=d, scenario=f"{a}/attack_only")]
        for k, a in enumerate(atks):
            sc = f"{a}/attack_only"
            pts = [stat(pick(base, dataset=d, scenario=sc, learning="online"), runs_base, "asr",
                        dataset=d, scenario=sc, learning="online")]
            pts += [stat(pick(lab, dataset=d, scenario=sc, learning=f"delay:{k2}"), runs_lab, "asr",
                         dataset=d, scenario=sc, learning=f"delay:{k2}") for k2 in delays]
            if pick(lab, dataset=d, scenario=sc, learning="frozen"):
                pts.append(stat(pick(lab, dataset=d, scenario=sc, learning="frozen"), runs_lab, "asr",
                                dataset=d, scenario=sc, learning="frozen"))
            else:
                pts.append(stat(pick(base, dataset=d, scenario=sc, learning="frozen"), runs_base, "asr",
                                dataset=d, scenario=sc, learning="frozen"))
            pts.append(stat(pick(lab, dataset=d, scenario=sc, learning="self"), runs_lab, "asr",
                            dataset=d, scenario=sc, learning="self"))
            m = np.array([p[0] if p[0] is not None else np.nan for p in pts])
            ax.plot(x[:-1], m[:-1], color=C[k], marker=MARK[k], label=ATK[a], zorder=3)
            ax.plot(x[-1:], m[-1:], color=C[k], marker=MARK[k], linestyle="none", zorder=3)
            off = (k - (len(atks) - 1) / 2) * 0.16      # each attack's seed dots beside its mean
            for xi, (mm, ss, vals) in zip(x, pts):
                spread_marks(ax, xi + off, mm, ss, vals, 0.05, color=C[k], size=4, alpha=0.6)
        ax.axvline(x[-1] - 0.5, color=GREY, linewidth=0.6, linestyle=":")
        ax.set_xticks(x, cats)
        ax.set_xlabel("label delay (flows)")
        ax.set_title(NAMES.get(d, d))
    axes[0].set_ylabel("DDoS flows evading (%)")
    top_legend(fig, axes)
    save(fig, out, "fig_label_delay")


def radp_fig_and_table(res: Path, out: Path):
    rows = read(res / "radp_grid" / "summary_radp.csv")
    if not rows:
        return
    runs = seed_runs(res / "radp_grid", tags={""})
    ds = datasets_in(rows)
    fig1, ax1 = panels(len(ds))
    fig2, ax2 = panels(len(ds))
    body = []
    for j, d in enumerate(ds):
        atks = [a for a in ATK if pick(rows, dataset=d, rad="rad", scenario=f"{a}/attack_only", learning="frozen")]
        x = np.arange(len(atks))
        det = [("RAD, raw attack", "rad", ""), ("RAD, repaired attack", "rad", "/feasible"),
               ("unseen attack, raw", "loao", ""), ("unseen attack, repaired", "loao", "/feasible")]
        for k, (lab, var, suf) in enumerate(det):
            pts = []
            for a in atks:
                v = var if var == "rad" else f"loao_{a}"
                sc = f"{a}/attack_only{suf}"
                pts.append(stat(pick(rows, dataset=d, rad=v, scenario=sc, learning="frozen"), runs, "rad_flag_ddos",
                                dataset=d, rad=v, scenario=sc, learning="frozen"))
            bar_group(ax1[j], x + (k - 1.5) * 0.2, pts, 0.184, k, lab)
        e2e = [("no defence", "rad", "asr_no_radp"), ("RAD", "rad", "e2e_asr"),
               ("RAD, attack unseen in training", "loao", "e2e_asr")]
        for k, (lab, var, met) in enumerate(e2e):
            pts = []
            for a in atks:
                v = var if var == "rad" else f"loao_{a}"
                sc = f"{a}/attack_only/feasible"
                pts.append(stat(pick(rows, dataset=d, rad=v, scenario=sc, learning="frozen"), runs, met,
                                dataset=d, rad=v, scenario=sc, learning="frozen"))
            bar_group(ax2[j], x + (k - 1) * 0.26, pts, 0.24, k, lab)
        for ax in (ax1[j], ax2[j]):
            ax.set_xticks(x, [ATK[a] for a in atks])
            ax.set_title(NAMES.get(d, d))
        for a in atks:
            for var in ("rad", "rad_nogan", f"loao_{a}"):
                for suf in ("", "/feasible"):
                    r = pick(rows, dataset=d, rad=var, scenario=f"{a}/attack_only{suf}", learning="frozen")
                    if r is None:
                        continue
                    body.append([esc(NAMES.get(d, d)), esc(var.replace(f"_{a}", "")), esc(ATK[a] + (" rep." if suf else "")),
                                 fmt(*ms(r, "rad_flag_ddos")), fmt(*ms(r, "benign_deleted")),
                                 fmt(*ms(r, "asr_no_radp")), fmt(*ms(r, "e2e_asr")),
                                 fmt(*ms(r, "recovered_acc")), fmt(*ms(r, "blocked_acc"))])
    ax1[0].set_ylabel("perturbed DDoS flagged (%)")
    ax2[0].set_ylabel("DDoS flows evading (%)")
    top_legend(fig1, ax1, ncol=2)
    top_legend(fig2, ax2)
    save(fig1, out, "fig_radp_detect")
    save(fig2, out, "fig_radp_e2e")
    write_tex(out, "tab_radp", "RADP (the base paper's Layer~1), detector frozen, mean $\\pm$ std over seeds (\\%). "
              "Flagged: perturbed DDoS flows RAD deletes. Benign del.: legitimate flows RAD deletes. "
              "ASR without / with RADP: DDoS flows that get through. Recovered: the paper's accuracy on "
              "surviving flows only; Blocked: accuracy over all flows, deleted flows counted as blocked. "
              "loao: RAD never trained on that attack.", "tab:radp",
              ["Dataset", "RAD", "Attack", "Flagged", "Benign del.", "ASR w/o", "ASR with", "Recovered", "Blocked"],
              body, "lllcccccc")


def loop_figs_and_table(res: Path, out: Path):
    main, rows = loop_rows(res)
    if not main:
        return
    runs = seed_runs(res / "loop_grid")
    ds = datasets_in(main)
    pols = []
    for r in main:
        if r["policy"] != "frozen" and r["policy"] not in pols:
            pols.append(r["policy"])
    # IW-strict joins the main figure at the main grid's verified share (e.g. iwstrict:0.1).
    rate = next((pol_rate(p) for p in pols if pol_kind(p) == "strict"), None)
    pols += sorted({r["policy"] for r in rows if pol_kind(r["policy"]) == "iwstrict" and pol_rate(r["policy"]) == rate
                    and r["policy"] not in pols})
    scens = []
    for r in main:
        if r["scenario"] not in scens:
            scens.append(r["scenario"])
    qs = sorted({_q(r["learning"]) for r in rows if r["policy"] in pols and _q(r["learning"]) is not None})
    qlab = [f"{q:g}" for q in qs]
    fig, axes = plt.subplots(len(ds), len(scens), figsize=(W2, 2.0 * len(ds) + 0.4), squeeze=False,
                             sharey=True, constrained_layout=True)
    body = []
    for i, d in enumerate(ds):
        for j, sc in enumerate(scens):
            ax = axes[i][j]
            fr = ms(pick(rows, dataset=d, scenario=sc, learning="frozen"), "asr")[0]
            if fr is not None:
                ax.axhline(fr, color=GREY, linestyle=":", linewidth=1.2, label="no learning")
            for p in pols:
                byq = {q: find(rows, d, p, sc, q) for q in qs}
                if not any(byq.values()):
                    continue
                st = pol_style(p)
                y = np.array([np.nan if byq[q] is None or ms(byq[q], "asr")[0] is None else ms(byq[q], "asr")[0]
                              for q in qs])
                ax.plot(qs, y, label=pol_label(p), zorder=3, **st)    # gaps where a q was not run
                for q in qs:
                    if byq[q] is not None:
                        mm, ss, vals = stat(byq[q], runs, "asr", dataset=d, scenario=sc, policy=p,
                                            learning=byq[q]["learning"])
                        spread_marks(ax, q, mm, ss, vals, 0.012, color=st["color"], size=4, alpha=0.6)
            ax.set_title(f"{NAMES.get(d, d)}: " + ("poisoning only" if sc == "clean" else "evasion + poisoning"))
            ax.set_xticks(qs, qlab)
            if i == len(ds) - 1:
                ax.set_xlabel("share of attacker flows labelled benign (q)")
            if j == 0:
                ax.set_ylabel("DDoS flows evading (%)")
        atk = next((s for s in scens if s != "clean"), None)
        for p in pols:
            cells = [esc(NAMES.get(d, d)), esc(pol_label(p)), fmt(*ms(find(rows, d, p, "clean", 0.0), "fpr")),
                     fmt(*ms(find(rows, d, p, atk, 0.0), "fpr")) if atk else "--"]
            for sc in scens:
                for q in (0.5, 1.0):
                    cells.append(fmt(*ms(find(rows, d, p, sc, q), "asr")))
            body.append(cells)
    top_legend(fig, axes)
    save(fig, out, "fig_loop_poison")
    hdr = ["Dataset", "Policy", "FPR clean", "FPR attack"]
    for sc in scens:
        tag = "poison" if sc == "clean" else "evade+poison"
        hdr += [f"ASR {tag} q=0.5", f"ASR {tag} q=1"]
    write_tex(out, "tab_loop", "Adaptation loop under label poisoning: the attacker's flows are labelled "
              "benign with probability $q$. FPR with true labels (clean traffic / under the repaired PGD "
              "attack) shows each policy's cost; the percentage is the share of flows with a verified "
              "label (\\%, mean $\\pm$ std over seeds).", "tab:loop", hdr, body, "ll" + "c" * (len(hdr) - 2))

    # Over time, from the per-seed JSONs (full poisoning, attack scenario).
    atk = next((s for s in scens if s != "clean"), None)
    tenths = {}
    for s in runs:
        if s["scenario"] != atk or not s.get("asr_by_tenth"):
            continue
        if s["policy"] == "frozen" or (s["policy"] in pols and _q(s["learning"]) == 1.0):
            tenths.setdefault((s["dataset"], s["policy"]), {}).setdefault(s["seed"], s["asr_by_tenth"])
    if not tenths:
        return
    ds2 = [d for d in ds if any(k[0] == d for k in tenths)]
    fig, axes = panels(len(ds2))
    for ax, d in zip(axes, ds2):
        x = np.arange(1, 11)

        def mean_of(key):
            arr = np.array([[np.nan if v is None else v for v in t] for t in tenths[key].values()], dtype=float)
            return np.nanmean(arr, axis=0)

        if (d, "frozen") in tenths:
            ax.plot(x, mean_of((d, "frozen")), color=GREY, linestyle=":", linewidth=1.2, label="no learning")
        for p in pols:
            if (d, p) in tenths:
                ax.plot(x, mean_of((d, p)), label=pol_label(p), zorder=3, **pol_style(p))
        ax.set_xticks(x)
        ax.set_xlabel("tenth of the test stream")
        ax.set_title(f"{NAMES.get(d, d)}: evasion + full poisoning (q = 1)")
    axes[0].set_ylabel("DDoS flows evading (%)")
    top_legend(fig, axes)
    save(fig, out, "fig_loop_time")


def audit_tradeoff(res: Path, out: Path):
    """strict (and IW-strict, once run): evasion under full poisoning and false alarms under
    attack, across verified-label budgets."""
    main, rows = loop_rows(res)
    fams = [k for k in ("strict", "iwstrict") if any(pol_kind(r["policy"]) == k for r in rows)]
    rates = sorted({pol_rate(r["policy"]) for r in rows if pol_kind(r["policy"]) in fams} - {None})
    if not fams or len(rates) < 2:
        return
    runs = seed_runs(res / "loop_grid")
    ds = datasets_in(rows)
    atk = next((r["scenario"] for r in main if r["scenario"] != "clean"), None)
    x = np.arange(len(rates))
    fig, axes = plt.subplots(2, len(ds), figsize=(W2, 3.9), squeeze=False, sharex=True, sharey="row",
                             constrained_layout=True)
    body = []
    for j, d in enumerate(ds):
        a1, a2 = axes[0][j], axes[1][j]
        for fam in fams:
            st = pol_style(fam)
            ys = {"asr": [], "fpr": []}
            for xi, a in zip(x, rates):
                pol = next((r["policy"] for r in rows if r["dataset"] == d and pol_kind(r["policy"]) == fam
                            and pol_rate(r["policy"]) == a), None)
                for key, ax, q, met in (("asr", a1, 1.0, "asr"), ("fpr", a2, 0.0, "fpr")):
                    r = find(rows, d, pol, atk, q) if pol else None
                    mm, ss, vals = stat(r, runs, met, dataset=d, scenario=atk, policy=pol,
                                        learning=r["learning"]) if r else (None, None, [])
                    ys[key].append(np.nan if mm is None else mm)
                    spread_marks(ax, xi, mm, ss, vals, 0.06, color=st["color"], size=4, alpha=0.6)
                if pol:
                    body.append([esc(NAMES.get(d, d)), esc(POL_NAME[fam]), f"{100 * a:g}\\%",
                                 fmt(*ms(find(rows, d, pol, "clean", 0.0), "fpr")),
                                 fmt(*ms(find(rows, d, pol, atk, 0.0), "fpr")),
                                 fmt(*ms(find(rows, d, pol, "clean", 1.0), "asr")),
                                 fmt(*ms(find(rows, d, pol, atk, 1.0), "asr"))])
            a1.plot(x, ys["asr"], label=POL_NAME[fam], zorder=3, **st)
            a2.plot(x, ys["fpr"], label=POL_NAME[fam], zorder=3, **st)
        van_fpr = ms(find(rows, d, "vanilla", atk, 0.0), "fpr")[0]
        if van_fpr is not None:
            a2.axhline(van_fpr, color=GREY, linestyle=":", linewidth=1.2, label="vanilla (paper's rule)")
        van_asr = ms(find(rows, d, "vanilla", atk, 1.0), "asr")[0]
        if van_asr is not None:
            a1.text(0.98, 0.95, f"vanilla: {van_asr:.1f}% evade", transform=a1.transAxes, ha="right", va="top",
                    fontsize=6.5, color=INK2)
        a1.set_title(f"{NAMES.get(d, d)}: evasion + full poisoning (q = 1)")
        a2.set_title(f"{NAMES.get(d, d)}: false alarms under attack, true labels")
        a2.set_xticks(x, [f"{100 * a:g}%" for a in rates])
        a2.set_xlabel("flows with a verified label")
        if j == 0:
            a1.set_ylabel("DDoS flows evading (%)")
            a2.set_ylabel("benign flows flagged (%)")
    handles = [Line2D([], [], label=POL_NAME[f], **pol_style(f)) for f in fams]
    handles.append(Line2D([], [], color=GREY, linestyle=":", linewidth=1.2, label="vanilla (paper's rule)"))
    fig.legend(handles=handles, loc="outside upper center", ncol=len(handles))
    save(fig, out, "fig_audit_tradeoff")
    write_tex(out, "tab_audit", "strict and importance-weighted strict (IW-strict) across verified-label budgets "
              "(\\%, mean $\\pm$ std over seeds): false alarms with true labels on clean traffic and under the "
              "repaired PGD attack, and evasion under full label poisoning ($q=1$) without and with the "
              "perturbation.", "tab:audit",
              ["Dataset", "Policy", "Verified", "FPR clean", "FPR attack", "ASR poison", "ASR evade+poison"],
              body, "lllcccc")


def at_label(v: str) -> str:
    if v == "none":
        return "no adv. training"
    atks = v[3:].split("+")
    return "adv. training, all four" if len(atks) == 4 else "adv. training, " + "+".join(ATK.get(a, a) for a in atks)


def advtrain_fig_and_table(res: Path, out: Path):
    rows = read(res / "advtrain_grid" / "summary_advtrain.csv")
    if not rows:
        return
    runs = seed_runs(res / "advtrain_grid")
    ds = datasets_in(rows)
    variants = []
    for r in rows:
        if r["at"] not in variants:
            variants.append(r["at"])
    delay = next((r["learning"] for r in rows if r["learning"].startswith("delay:")), None)
    fig, axes = panels(len(ds))
    body = []
    for ax, d in zip(axes, ds):
        atks = [a for a in ATK if pick(rows, dataset=d, scenario=f"{a}/attack_only/feasible", learning="frozen")]
        # one group per attack (evasion), then one for the price: false alarms on clean traffic
        x = np.append(np.arange(len(atks)), len(atks) + 0.4)
        w = 0.8 / max(1, len(variants))
        for k, v in enumerate(variants):
            pts = [stat(pick(rows, dataset=d, at=v, scenario=f"{a}/attack_only/feasible", learning="frozen"),
                        runs, "asr", dataset=d, at=v, scenario=f"{a}/attack_only/feasible", learning="frozen")
                   for a in atks]
            pts.append(stat(pick(rows, dataset=d, at=v, scenario="clean", learning="frozen"), runs, "fpr",
                            dataset=d, at=v, scenario="clean", learning="frozen"))
            xs = x + (k - (len(variants) - 1) / 2) * w
            means = bar_group(ax, xs, pts, w * 0.92, k, at_label(v))
            seen = v[3:].split("+") if v != "none" else []
            for xi, mi, a in zip(xs, means, atks):
                if seen and a not in seen and mi == mi:   # attacks this detector never trained on
                    ax.annotate("unseen", (xi, mi), xytext=(0, 3), textcoords="offset points", ha="center",
                                va="bottom", fontsize=5.5, color=INK2, rotation=90)
        ax.axvline(len(atks) - 0.3, color=GREY, linewidth=0.6, linestyle=":")
        ax.set_xticks(x, [ATK[a] for a in atks] + ["false alarms\n(clean)"])
        ax.set_title(NAMES.get(d, d))
        for v in variants:
            cells = [esc(NAMES.get(d, d)), esc(at_label(v))]
            cells.append(fmt(*ms(pick(rows, dataset=d, at=v, scenario="clean", learning="frozen"), "fpr")))
            if delay:
                cells.append(fmt(*ms(pick(rows, dataset=d, at=v, scenario="clean", learning=delay), "fpr")))
            cells += [fmt(*ms(pick(rows, dataset=d, at=v, scenario=f"{a}/attack_only/feasible", learning="frozen"),
                              "asr")) for a in atks]
            if delay:
                cells += [fmt(*ms(pick(rows, dataset=d, at=v, scenario=f"{a}/attack_only/feasible", learning=delay),
                                  "asr")) for a in ("pgd", "cw")]
            body.append(cells)
    axes[0].set_ylabel("Evading DDoS / flagged benign (%)")
    top_legend(fig, axes)
    save(fig, out, "fig_advtrain")
    dl = delay.split(":")[1] if delay else ""
    header = ["Dataset", "Detector", "FPR, no labels"] + ([f"FPR, delay {dl}"] if delay else []) \
        + [f"{esc(ATK[a])}" for a in ATK] + ([f"PGD, delay {dl}", f"C\\&W, delay {dl}"] if delay else [])
    write_tex(out, "tab_advtrain", "Adversarial-training baseline: false-positive rate on clean traffic and "
              "evasion rate (\\% of perturbed DDoS flows classified benign) of the repaired attacks, with no "
              f"labels during the test{' and with labels ' + dl + ' flows late' if delay else ''}; mean "
              "$\\pm$ std over seeds. The detector trains on one repaired adversarial copy of each DDoS "
              "training flow, crafted on the defender's own surrogate.", "tab:advtrain",
              header, body, "ll" + "c" * (len(header) - 2))


def main() -> int:
    ap = argparse.ArgumentParser(description="Paper figures and tables from the grid results.")
    ap.add_argument("--results", default=str(ROOT / "results"))
    ap.add_argument("--out", default=None, help="default: <results>\\paper")
    args = ap.parse_args()
    res = Path(args.results)
    out = Path(args.out) if args.out else res / "paper"
    for step in (repro_table, attack_fig_and_table, label_delay_fig, radp_fig_and_table, loop_figs_and_table,
                 audit_tradeoff, advtrain_fig_and_table):
        try:
            step(res, out)
        except Exception as exc:  # one broken input must not stop the others
            print(f"[figures] {step.__name__} failed: {exc!r}")
    print(f"[figures] done; outputs in {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
