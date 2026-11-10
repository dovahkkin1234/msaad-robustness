# Course paper

*Learn Only What You Can Verify: Hardening the Label Channel of Online IoT DDoS Detectors*,
the 10-page IEEE paper submitted for the Computer Network Security course on 10 Nov 2026.

| Path | What it is |
| --- | --- |
| `main.tex`, `references.bib`, `images/` | The Overleaf project, exactly as submitted |
| `CS23B2041_MSAAD_Paper.pdf` | The final PDF (10 pages) |
| `build/build_tables.py` | Builds Tables II–VI from the per-seed result JSONs under `results/` |
| `build/values.json` | Every table value with its mean, standard deviation and seed count |
| `build/make_paper_poison_fig.py` | Builds Fig. 3 (`fig_loop_poison_paper`) |
| `build/fig_system.tex` | TikZ source of Fig. 1 (`fig_system`) |
| `../docs/MSAAD_Honest_Review.pdf` | Review of the novelty, standing and publication path |

## Compile

Overleaf: zip `main.tex`, `references.bib` and `images/`, then New Project → Upload Project.
Locally: `pdflatex main`, `bibtex main`, then `pdflatex main` twice.

## Where every number comes from

- Tables II–VI: `build/build_tables.py`, straight from the per-seed JSONs, so nothing is rounded twice.
- Table VII: the RADP (5 seeds), adversarial-training (15 seeds) and HopSkipJump (5 seeds) summaries under `results/`.
- Figs. 2 and 4: `scripts/make_figures.py` (`results/paper/`).
- Fig. 3: `build/make_paper_poison_fig.py`. Fig. 1: `build/fig_system.tex`.

To rebuild the tables and Fig. 3, run from the repository root with the msaad environment active:

```powershell
python paper\build\build_tables.py scripts results paper\build\tables
python paper\build\make_paper_poison_fig.py scripts results paper\build\figs
```

`paper\build\tables\values.json` should then match `build/values.json` exactly.

## Corrections made after the first Turnitin check (10 Nov 2026)

- Poisoning evasion range: 99.7–99.96% (abstract, introduction).
- Table III and Section V-B: the label-delay rows are marked as PGD.
- Section V-F: vanilla lets 99.6–99.8% of attacks through without the evasion step.
- Section II-A: AUWPAE uses the base paper's own expansion.
