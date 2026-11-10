"""Compact paper version of fig_loop_poison: one row, evasion + poisoning only, one panel per
dataset. Same data, styles and helpers as scripts/make_figures.py (v14f).
Usage: python make_paper_poison_fig.py <repo>/scripts <results dir> <out dir>"""
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
import make_figures as mf  # noqa: E402
import numpy as np  # noqa: E402

res, out = Path(sys.argv[2]), Path(sys.argv[3])
main, rows = mf.loop_rows(res)
runs = mf.seed_runs(res / "loop_grid")
ds = mf.datasets_in(main)
pols = []
for r in main:
    if r["policy"] != "frozen" and r["policy"] not in pols:
        pols.append(r["policy"])
sc = next(r["scenario"] for r in main if r["scenario"] != "clean")
qs = sorted({mf._q(r["learning"]) for r in rows if r["policy"] in pols and mf._q(r["learning"]) is not None})
fig, axes = mf.panels(len(ds), height=2.25)
for ax, d in zip(axes, ds):
    fr = mf.ms(mf.pick(rows, dataset=d, scenario=sc, learning="frozen"), "asr")[0]
    if fr is not None:
        ax.axhline(fr, color=mf.GREY, linestyle=":", linewidth=1.2, label="no learning")
    for p in pols:
        byq = {q: mf.find(rows, d, p, sc, q) for q in qs}
        if not any(byq.values()):
            continue
        st = mf.pol_style(p)
        y = np.array([np.nan if byq[q] is None or mf.ms(byq[q], "asr")[0] is None else mf.ms(byq[q], "asr")[0]
                      for q in qs])
        ax.plot(qs, y, label=mf.pol_label(p), zorder=3, **st)
        for q in qs:
            if byq[q] is not None:
                mm, ss, vals = mf.stat(byq[q], runs, "asr", dataset=d, scenario=sc, policy=p,
                                       learning=byq[q]["learning"])
                mf.spread_marks(ax, q, mm, ss, vals, 0.012, color=st["color"], size=4, alpha=0.6)
    ax.set_title(mf.NAMES.get(d, d))
    ax.set_xticks(qs, [f"{q:g}" for q in qs])
    ax.set_xlabel("attacker flows labelled benign (q)")
axes[0].set_ylabel("DDoS flows evading (%)")
mf.top_legend(fig, axes)
mf.save(fig, out, "fig_loop_poison_paper")
