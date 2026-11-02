# MSAAD-Robustness

A rigorous **robustness re-evaluation and hardening** of the online IoT DDoS detector
proposed in Beshah et al., *"Multi-Stage Adversarial Defense for Online DDoS Attack
Detection System in IoT"* (IEEE Access 2025, doi:10.1109/ACCESS.2025.3560186).

This is defensive security research: we reproduce the published **defence** (MABTSE), test
our own reimplementation for robustness on **public benchmark datasets** (IoTID20,
CICIoT2023), and build a more robust version. Everything runs offline on the dataset CSVs;
nothing here generates traffic or runs against any live system.

**Author:** Shirish Giroti (CS23B2041), IIITDM Kancheepuram.

---

## What is here (stages S0–S4 + adversarial-training baseline, v13)

```
msaad-robustness/
├── README.md
├── SETUP.md                 # START HERE: step-by-step Windows setup, datasets, experiments
├── PLAN.md                  # gap scan, pipeline stages, findings so far
├── RUNS.md                  # run journal: every run, its command, code version and outputs
├── requirements.txt
├── configs/base.yaml        # datasets (filters, replay order), hyperparameters, attack defaults
├── scripts/
│   ├── DOWNLOAD_DATA.md      # where to get IoTID20 / CICIoT2023 (verified sources)
│   ├── inspect_dataset.py    # columns, class counts, file order vs time order
│   ├── make_figures.py       # paper figures (PDF/PNG, every seed as a dot) + LaTeX tables
│   └── push_run.py           # journal the latest run in RUNS.md, commit it, push to GitHub
├── src/
│   ├── data/
│   │   ├── loaders.py        # CSV + synthetic streams; file / campaign / time replay orders
│   │   ├── preprocessing.py  # leakage-free running min-max (transform-then-learn)
│   │   └── matrix.py         # stream -> arrays, vectorised identical scaler, -> dicts
│   ├── models/
│   │   ├── pool.py           # the 5 online learners (Layer 2) + drift-detection counts
│   │   ├── knn_adwin.py      # KNN-ADWIN rebuilt for River 0.22 (exact, deterministic)
│   │   └── mabtse.py         # Thompson-Sampling + AUWPAE ensemble (Layer 3), reward fix,
│   │                         #   optional learner-only updates (used by the S4 defence)
│   ├── attacks/
│   │   ├── surrogate.py      # attacker's differentiable stand-in (MLP / LR, NumPy gradients)
│   │   ├── evasion.py        # FGSM, BIM, PGD, C&W-L2 (eps ball, domain box, NaN-safe)
│   │   └── constraints.py    # mined flow-feature constraints: audit + monotone repair
│   ├── defense/
│   │   ├── gan.py            # small tabular GAN in NumPy (hand-written backprop, Adam)
│   │   └── radp.py           # RADP (Layer 1): MSAPG, RAD training mix, RAD, purification
│   ├── eval/
│   │   ├── metrics.py        # accuracy / precision / recall / F1 / false-alarm rate
│   │   └── prequential.py    # test-then-train loop + throughput
│   └── utils/seeding.py
├── experiments/
│   ├── repro_baseline.py     # S2: clean prequential reproduction (one run)
│   ├── under_attack.py       # S3: the paper's Scenario 2 + label modes (online/frozen/delay/self)
│   ├── radp_defense.py       # S3: the paper's Scenario 3 — RADP vs raw and realistic attacks
│   ├── adaptation_loop.py    # S4: label poisoning, selector steering; audit/guard/strict/IW-strict policies
│   ├── adv_training.py       # baseline defence: MABTSE trained on repaired adversarial copies
│   └── run_grid.py           # many runs in parallel (datasets x seeds) + mean/std summary
└── tests/
    ├── smoke_test.py         # pipeline self-check (no data needed)
    ├── attack_smoke_test.py  # attack-stack self-check (no data needed)
    ├── radp_smoke_test.py    # RADP + label-mode self-check (no data needed)
    ├── loop_smoke_test.py    # S4 self-check (no data needed)
    └── advtrain_smoke_test.py  # adversarial-training self-check (no data needed)
```

## Quick start

**Follow `SETUP.md` step by step** (also provided as a PDF). In short, all in a normal
(non-admin) **PowerShell** window:

```powershell
conda create -n msaad -c conda-forge --override-channels python=3.11 -y
conda activate msaad
python -m pip install -r requirements.txt
python tests\smoke_test.py                                   # expect [smoke] PASS
python tests\attack_smoke_test.py                            # expect [attack-smoke] PASS
python tests\radp_smoke_test.py                              # expect [radp-smoke] PASS
python tests\loop_smoke_test.py                              # expect [loop-smoke] PASS
python tests\advtrain_smoke_test.py                          # expect [advtrain-smoke] PASS
python scripts\inspect_dataset.py ".\data\iotid20\IoT_Network_Intrusion_Dataset.csv"
python experiments\repro_baseline.py --data iotid20          # P1: file order (paper setup)
python experiments\repro_baseline.py --data iotid20_campaign # P2: attack campaigns in time order
python experiments\run_grid.py --data iotid20 iotid20_campaign ciciot2023 --seeds 1 2 3 --jobs 4
python experiments\run_grid.py --exp attack --data iotid20 ciciot2023 --seeds 1 2 3 --jobs 3
python experiments\run_grid.py --exp attack --data iotid20 --jobs 3 --tag labels --attacks pgd cw --learning frozen delay:100 delay:1000 delay:5000 self
python experiments\run_grid.py --exp radp --data iotid20 --seeds 1 2 3 --jobs 3
python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --jobs 3
python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --jobs 3 --tag iw --policies iwstrict:0.05 iwstrict:0.1 iwstrict:0.2
python scripts\make_figures.py                                # needs: python -m pip install matplotlib
```

Every result reports accuracy, precision, recall and F1 **plus the false-alarm rate on
benign traffic, the confusion matrix and the majority-class baseline** — on imbalanced IDS
data accuracy alone hides how much legitimate traffic gets flagged.

## Version control and the run journal

The project lives in a private GitHub repository (SETUP.md, Step 15). After every run,
`python scripts\push_run.py` (or `--push` on any `run_grid.py` command) appends an entry to
`RUNS.md` — the exact command, the code version, which runs worked, which result files changed —
commits code, documents and `results\`, and pushes. Datasets (`data\`) are never committed; the
laptop pushes with a deploy key that can reach this one repository only.

## Replay protocols (IoTID20)

| Name | Order | What it tests |
|---|---|---|
| `iotid20` (P1) | file order — the public CSV is randomly shuffled w.r.t. time | stationary stream; the paper's setting |
| `iotid20_campaign` (P2) | attack flows in capture-time order, benign flows spread evenly | real attack-campaign drift over a constant benign background |
| `iotid20_time` | plain time sort | **degenerate**: all benign flows were captured in the first week, so this is one all-benign → all-attack switch; kept only to document that |
| `iotid20_mirai`, `iotid20_all` | file order | subset sensitivity: + Mirai brute force (the paper lists it as a DDoS type), or every attack |

## Reproduction assumptions (the paper underspecifies these)
- **KNN-ADWIN** → River 0.22 no longer ships it, so `src/models/knn_adwin.py` rebuilds its
  behaviour: exact k-NN (k=5, River `LazySearch`) over a 100-sample window, with ADWIN on the
  0/1 error shrinking the window on drift.
- **Determinism** → every learner is seeded or exact; repeated runs give identical results.
- **Thompson-Sampling reward** → the paper's Algorithm 1 never updates the Beta posteriors;
  we use per-arm correctness as the reward and flag this as a correction.
- **Attacks (Scenario 2)** → the River learners have no gradients, so perturbations are
  crafted on a differentiable surrogate (MLP 64-32 by default) trained on the same clean
  training rows (grey-box transfer), in the scaled feature space with eps = 0.1.
  BIM/PGD use 20 steps of eps/4; PGD adds one random start; C&W is the binary L2 form with
  projected Adam and a 6-step binary search on c.
- **Label feedback** → the paper assumes each flow's true label arrives at once
  (`online`). We also replay with no labels (`frozen`), labels D flows late (`delay:D`) and
  the model's own predictions as labels (`self`).
- **RADP (Layer 1)** → the paper does not specify its GAN, the RAD training mix or what the
  defender knows. We assume: the defender crafts MSAPG samples on its own surrogate (same
  architecture, different seed) from its clean training flows; benign and DDoS flows are
  both perturbed; a NumPy GAN (32-128-128-d generator, d-128-64-1 discriminator,
  non-saturating loss, Adam 2e-4, 3,000 steps) mimics those samples; RAD is a fresh MABTSE
  trained on a balanced mix of clean flows vs MSAPG + GAN samples and frozen on the test
  stream; deleted flows never reach the detector. Full list: `src/defense/radp.py`.
- **Adaptation loop (S4)** → the labelling system is fooled by the attacker's own flows with
  probability q (they are labelled benign); benign flows always get true labels; the
  attacker does not know which flows are audited. Defences: `audit:a` (only a verified random
  share a of labels updates the selector), `guard:a` (plus: a benign label for a flow just
  flagged as DDoS needs verification), `strict:a` (plus: no unverified benign label is
  learned). Full description: `experiments/adaptation_loop.py`.
