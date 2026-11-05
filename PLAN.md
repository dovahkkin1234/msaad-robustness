% MSAAD-Robustness — Project Pipeline & One-Week Sprint
% Shirish Giroti (CS23B2041), IIITDM Kancheepuram
% Started 30 Oct 2026

> **Schedule update (30 Oct):** the course deadline is **10 Nov 2026**. The day-by-day
> schedule in `MSAAD_Plan_Nov10.pdf` supersedes the one-week sprint table in §5 below;
> the gap scan, novelty claim and pipeline stages here are unchanged.

# Status and findings so far (5 Nov 2026)

Research notes for the paper — facts and numbers to build on, not paper text.

| Stage | Status |
|---|---|
| S0 environment, S1 leakage-free data layer | done |
| S2 clean reproduction, IoTID20 (P1) | **gate passed on 3 seeds** (table below) |
| S2 sensitivity: campaign order, + brute force, all classes | done, 3 seeds (F5) |
| S2 clean reproduction, CICIoT2023 | **gate passed on 3 seeds** (F8) |
| S3 under-attack harness (Scenario 2) + feasibility audit | **done, 3 seeds, both datasets** (F6, F7, F10) |
| S3 label-feedback modes (delayed, self-labelled) | **done, 3 seeds, both datasets** (F11) |
| S3 RADP (Layer 1): MSAPG + GAN + RAD + purification | **done, 3 seeds, both datasets** (F12) |
| S4 adaptation-loop study + defence | **done, 3 seeds, both datasets (F9) + sweep (F9b)** |
| S4 importance-weighted strict (IW-strict) | **done, 3 seeds, both datasets (F14)** |
| Adversarial-training baseline (v13) | **done, 3 seeds, both datasets (F15)** |
| v14 on exp/conference: 15-seed replication (loop, attack, adversarial training; RADP 5 seeds) | **done (F16, 3 Nov)** |
| v14 on exp/conference: framing, audits, chain + GNN, adaptive attacks | **done, 15 seeds (adaptive: 5)** (F18–F22); predictions P1–P8 checked below |
| v14 third dataset: CIC-IDS2017 (WTMC 2021), configured from the inspector | **done, 15 seeds**: attack, loop, adversarial training, chain, uncertainty audits, framing (F17–F19); P9 held |
| Figures and tables | generated from the real results; v14d adds `fig_framing_audits`, `tab_framing_audits` and CIC-IDS2017 in `tab_audits` |
| Optional (v14d): combined attack with uncertainty audits (`--tag combounc`, Step 20) | fills the last empty column of `tab_framing_audits` |

**Where we stand (2 Nov).** Every planned experiment has run on both datasets with three
seeds; the results can be frozen for the course paper now. The evaluation findings (F2–F7, F10–F13) are
solid and new. The headline has moved: the Thompson-Sampling selector is *not* the weak point
(F9), the label-feedback channel is. The defence now holds on both counts: strict stops label
poisoning (F9, F9b) and its importance-weighted version brings the false-alarm cost to within
0.2–2.5 points of the paper's rule at 10–20% verified labels (F14).

**Run queue (1 Nov).** Each grid runs three seeds, three at a time; two grids side by side
are fine on the laptop. Commands are in the Setup Guide. From now on every run is journalled
in `RUNS.md` and pushed to the private repository (Step 15).

| # | Run | Setup Guide | Send to Claude | Status |
|---|---|---|---|---|
| 1 | Attack grid, IoTID20 | Step 10 | `results\attack_grid\summary_attack.csv` | done (F6, F7) |
| 2 | Clean grid incl. CICIoT2023 | Steps 5, 6, 9 | inspector report, `results\grid\summary.csv` | done (F8) |
| 3 | RADP quick look, IoTID20 (`--limit 3000`) | Step 12 | `results\radp\iotid20_seed42.csv` | done |
| 4 | Attack grid CICIoT2023, then label grid on both datasets | Steps 10, 11 | `summary_attack.csv`, `summary_attack_labels.csv` | done (F10, F11) |
| 5 | RADP grid, both datasets | Step 12 | `results\radp_grid\summary_radp.csv` | done (F12) |
| 6 | Adaptation-loop grid (S4), both datasets | Step 13 | `results\loop_grid\summary_loop.csv` | done (F9) |
| 8 | S4 sweep: smaller q, other audit rates | Step 13 part 4, `--tag sweep` | `results\loop_grid` (zip) | done (F9b); per-seed JSONs in the repository |
| 9 | IW-strict grid (v10), both datasets, 57 min | Step 13 part 5, `--tag iw` | `results\loop_grid\summary_loop_iw.csv` | done (F14) |
| 10 | Private GitHub repository; push after every run (`--push`) | Step 15 | the pushed repository | done (2 Nov) |
| 7 | Figures and tables | Step 14 | the `results\paper` folder (zip it) | done on current results; re-run after #11 |
| 11 | Adversarial-training baseline (v13), both datasets, 78 min | Step 16, `--exp advtrain` | `results\advtrain_grid\summary_advtrain.csv` | done (F15) |
| 12 | 15-seed replication: loop, adversarial training, attack (`--tag s15`); RADP to 5 seeds; 6.5 h | Step 17 | the terminal output | done (F16) |
| 13 | v14a: framing, uncertainty / mixed audits, low budgets (15 seeds) | Step 17 | `summary_loop_{frame,audits,auditsmix,lowbudget}.csv` | done (F18, F19, F22) |
| 14 | v14b: detector chain (15 seeds), adaptive attackers (5 seeds) | Step 18 | `summary_cascade_s15.csv`, `summary_advtrain_adaptive.csv` | done (F20, F21) |
| 15 | v14c: CIC-IDS2017 stream check, then attack, loop, adversarial training, chain (15 seeds) | Step 19 | check output, then the four summaries | done (F17) |
| 15b | CIC-IDS2017 framing with random and uncertainty audits (`--tag frame`, `--tag frameunc`) | Step 19 | the per-seed JSONs (zip) | done 5 Nov (F18, F19) |
| 16 | Paired statistics on everything finished (v14d adds the `frameunc` preset) | Step 20 | `results\paper\stats_*.csv` | `frameunc` run by Claude on the shared files, 5 Nov; re-run on the laptop |
| 17 | Optional: combined attack (poisoning + 5% framing) with uncertainty audits, three datasets, ~1.5 h | Step 20 | the terminal output | optional |

**Why #11.** The first question a reviewer asks of an evasion result is "why not adversarial
training?". Three detectors per run, identical attacker: no adversarial training, trained on
repaired PGD copies only (FGSM, BIM and C&W unseen; BIM is a near-copy of PGD), and trained on all four attacks. Expected
outcomes and what each means for the paper: (a) it stops evasion without labels at little
false-alarm cost → a strong second baseline, and the paper compares it with the label-channel
defence; (b) it helps on seen attacks only, or costs many false alarms → evidence that the
label channel, not the detector's training data, is where robustness has to come from. Either
outcome goes in the paper. Limitation to state: the attacker is not adaptive (it does not
re-train against the hardened detector), so the numbers are an upper bound on what adversarial
training buys.

## v14 (exp/conference branch, 2–5 Nov): conference-level additions, predictions registered before the runs

Written before any v14 result exists, so the paper can report which predictions held (the
FANET project's discipline). Each is checked on 15 seeds unless stated.

| # | Experiment (Setup Guide step) | Prediction |
|---|---|---|
| P1 | Framing `frame:r` (17) | Framing raises strict's false alarms far more than vanilla's (vanilla also learns benign labels); IW-strict cuts strict's rise roughly in half; consensus blocks framing but raises ASR under evasion with true labels (slower adaptation). |
| P2 | Audit allocation (17) | Uncertainty-only audits check fewer attacker flows than random audits (evading flows look confidently benign), so strict's ASR under evasion + full poisoning rises; mixed audits sit in between. |
| P3 | Low budgets (17) | Copy caps of 5–10 remove most of IW-strict's instability at 5% audits; 2% audits stay worse than 10%. |
| P4 | Noise-aware baseline (17) | Between vanilla and strict under full poisoning (it still learns 1 − rho of the poisoned labels); close to vanilla on clean traffic. |
| P5 | Detector chain (18) | The online MLP catches few of MABTSE's misses (the attacker's surrogate is also an MLP, so the same perturbations transfer); the host-graph stage catches most of them on IoTID20 (campaign order); the matched control is within 5 points of the GNN (host aggregates and message passing substitute, as in FANET); the drift focus keeps most of the catch while scoring fewer flows. Calibrated thresholds may not hold their 1% false-alarm target on test traffic (drift). |
| P6 | Graph-aware attacker (18) | Spoofing sources lowers the graph stage's catch rate (it never saw spoofed patterns in training); thinning keeps the catch rate, so the evaded volume falls with the rate: evading the graph stage costs attack volume. |
| P7 | Adaptive evasion (18, 5 seeds) | A surrogate distilled from the detector transfers better than the plain surrogate; label-only HopSkipJump restricted to valid traffic succeeds on most flows within 2,000 queries against the plain detector but far fewer against the adversarially trained one; raw-space HopSkipJump evasions rarely survive repair to valid traffic. |
| P8 | 15-seed statistics | Every large effect of F6, F9, F10, F12, F14, F15 stays significant after Holm correction (p < 0.01); IW-strict's false-alarm advantage over strict is significant on CICIoT2023, less certain on IoTID20. |
| P9 | CIC-IDS2017, third dataset (19; registered 3 Nov, before any run) | The label-channel results replicate on an independently labelled, time-ordered stream: with instant true labels evasion stays ≤ 1%; vanilla lets ≥ 95% through under evasion + full poisoning while strict and IW-strict keep it ≤ 2%; evasion grows with the label delay, in seconds as in flows. Frozen transfer evasion: no prediction (the first two datasets disagree, 17% vs 49%). In the chain, the host-graph stage catches most of MABTSE's misses (one source floods one victim, which stands out in the host graph) and spoofing many sources lowers that catch. |


**Prediction outcomes (5 Nov).** Five held, three held in part, one was wrong. The wrong one (P2)
and the consensus half of P1 led to the strongest new results (F18, F19); report the misses.

| # | Outcome | Verdict |
|---|---|---|
| P1 | Strict 61% / 92% vs vanilla 11% / 25% at 2% framing; IW-strict cuts strict's rise by about a third; consensus does not block framing (79–93% at 10%) | partly |
| P2 | Uncertainty audits do check fewer attacker flows (6–9% vs 10%), yet evasion falls on IoTID20 (0.88 → 0.28%), is level elsewhere, and false alarms fall 4–12× on all three datasets | wrong, better than predicted |
| P3 | Copy caps halve IW-strict's false alarms at 5% audits; at 2% evasion is 1.8–4.0% vs 0.4–0.9% at 10% | held |
| P4 | Noise-aware: 60% (IoTID20) and 5.6% (CICIoT2023) evasion under full poisoning; clean false alarms near vanilla's | held |
| P5 | MLP catches 86% of misses on CICIoT2023, fails on IoTID20; GNN catches 37–43% (IoTID20 P2) and 98% (CIC-IDS2017), the matched control 48% and 97%; drift focus still scores 87–95% of flows | partly (control: held) |
| P6 | Spoofing raises evasion after the chain 12.5 → 18.9% and 1.3 → 17.8%; thinning leaves 2.6% / 0.03% of the volume getting through | held |
| P7 | Distilled surrogate no better; HopSkipJump on valid traffic 25% / 51% (not most) on the plain detector, 14% / 2% on the AT one; repair kills raw evasions (31.6 → 4.0%) | partly |
| P8 | Every large effect survives Holm; IW-strict's false-alarm gain over strict significant on all three datasets (p_Holm ≤ 0.0004) | held (stronger) |
| P9 | Vanilla 99.95% vs strict 0.14% at q = 1; instant labels 0.02%; graph catch 98%; spoofing raises evasion to 17.8% | held |

**Third dataset, confirmed by the inspector (3 Nov).** Corrected CIC-IDS2017 (Engelen et al.,
WTMC 2021), Friday file: 547,915 flows, 84 columns; BENIGN 291,433, PortScan 159,151, DDoS 95,123,
Bot 738, Bot - Attempted 1,470. Timestamps parse 100% (`%d/%m/%Y %I:%M:%S %p`); the file is not
in time order (56.6% of consecutive rows), so it is replayed sorted by time.
- The LOIC flood runs 20:56:31–21:16:10 on the file's clock; CIC's published schedule says
  15:56–16:16, so the file's clock is 5 h ahead (a time-zone shift; only relative times matter).
- Every PortScan and DDoS flow comes from one address, 172.16.0.1 (the attackers' NAT address):
  an address feature would label the attack by itself. Addresses are context only (host graph,
  label delays in seconds), never features; ports and protocol stay features, as for IoTID20.
  Paper: one sentence on this, and the spoofing attacker (P6) is the honest test of the graph stage.
- Replay: 20:31–21:26 (25 min of normal traffic, the 20-min flood, 10 min after), BENIGN + DDoS,
  30,000 flows evenly spaced. Training (the first 67%) ends inside the flood, so the detector
  has seen the flood start; the test stream holds the rest of it and the quiet period after.
  `scripts\check_stream.py --data cicids2017` prints the exact split, classes per part, the
  clock times, and what a delay of 1,000 / 5,000 flows means in seconds.
- Found while configuring it (fixed in v14c): the attack, loop, adversarial-training and RADP
  scripts ignored `time_window` and `exclude_values` (only the chain honoured them). IoTID20 and
  CICIoT2023 use neither, so every result so far is unaffected (their streams are identical
  between v14b and v14c, checked on the mock file).

Dropped on purpose: a host-hash partition ensemble with a DPA-style certificate. Attack
traffic comes from few hosts, so host partitions without them never learn what an attack
looks like (the vote fails on clean data), and flow-level partitions certify only a handful
of poisoned flows, orders of magnitude fewer than one flood. Discussed, not built.

**F1 — The clean result reproduces.** IoTID20, P1 (file order), 50,000 flows, 3 seeds,
mean ± std. The seeds vary only the models' randomness; every seed sees the same flows.

| Metric | Ours | Paper |
|---|---|---|
| Accuracy | 99.33 ± 0.08 | 99.50 |
| Precision | 99.33 ± 0.07 | 99.47 |
| Recall | 99.91 ± 0.02 | 100 |
| F1 | 99.62 ± 0.05 | 99.74 |
| False-alarm rate | 4.98 ± 0.51 % | not reported |

Our setup is stricter than the paper's: running (leakage-free) scaling, no oversampling
in the evaluated stream, exact KNN-ADWIN, and a learning bandit.

**F2 — Accuracy hides false alarms.** About 5% of benign flows are flagged as DDoS
(4.98 ± 0.51% over 3 seeds, ~300 of ~6,000), against ~40 missed attacks. A model
that always says "attack" already scores ~88% accuracy on this subset. This matters because
the paper's defence *deletes* flagged traffic. (v6+ reports the false-alarm rate directly.)

**F3 — IoTID20's file order carries no drift.** Only 50.0% of consecutive rows are in time
order and every tenth of the file has the same class mix: the public CSV is shuffled. The
paper's "3 concept drifts" on IoTID20 therefore cannot reflect real change in the traffic.

**F4 — IoTID20 confounds class with capture date.** All 40,073 benign flows were captured
in the first week (20–26 May 2019); everything after is attack traffic (DoS/ARP spoofing,
then scans, then Mirai floods on 11–25 Jul, then brute force to 10 Sep). A plain
time-ordered replay is a single all-benign → all-attack switch, and any model could
separate the classes by capture-session artefacts. Our P2 protocol ("campaign order")
keeps attacks in their real order with benign flows spread evenly as background.

Measured (3 seeds): the time-ordered replay (`iotid20_time`) scores 99.99 ± 0.01% accuracy,
100.00% F1 and 0.00% false alarms, so the replay order alone produces a perfect score.
About 85% of the UDP/ACK/HTTP flood flows in our subset (~250,000 of 294,496) were
captured within seven minutes (25 Jul 2019, 03:20–03:27), two months after the last
benign flow.

**Prior work on IoTID20's validity (checked 1 Nov).** IoTGeM (Kostas, Just & Lones, preprint
submitted to Elsevier, arXiv 2401.01343), Appendix A.3, re-extracted the IoT-NID pcaps and
reports that IoTID20's feature extraction / labelling looks flawed: the raw data has 10
attacks but IoTID20 has 8; the attack pcaps also contain benign packets, yet IoTID20 appears
to label whole attack files as attacks; and for several attacks IoTID20 has MORE flows than
the raw data has attack packets (their Table 8; a flow holds at least one packet), e.g.
Telnet brute force 1,924 packets vs 121,181 flows and HTTP flooding 10,464 packets vs 55,818
flows (UDP, ACK and SYN floods are consistent). IoTGeM does not report the file shuffling,
the class/capture-date confound or the degenerate time replay: F3 and F4 are new
observations. Cite IoTGeM for the labelling problems; together they are a threat-to-validity
paragraph for every IoTID20 result, including the base paper's.

**Hypothesis H5 (links F5 to IoTGeM).** By IoTGeM's counts at least 98% of the 121,181
"brute force" flows cannot be brute-force attack flows, so adding that class teaches the
detector to call benign-looking flows "attack" — consistent with false alarms jumping from
5% to 12% (F5). Our default subset contains HTTP flooding, where at least 81% of the 55,818
flows cannot be attack flows either. Check: per-class evasion (`asr_by_class` in the attack
JSONs) — mislabelled, benign-looking classes should evade far more often than UDP/ACK floods.

**H5 result (1 Nov): not supported.** IoTID20, repaired PGD, no labels, per class over the
3 seeds: HTTP flooding 23.4 / 29.1 / 34.3%, ACK flooding 23.5 / 29.1 / 33.7%, UDP flooding
6.2 / 8.3 / 11.1%. HTTP (mostly not attack flows by IoTGeM's counts) evades no more than ACK
(consistent counts); UDP floods are simply harder to disguise. The other attacks show the same
pattern (FGSM: 29–31% vs 29–31% vs 8.5–9.0%). Report it as a checked and rejected
explanation; the false-alarm jump in F5 still needs one.

**Speed numbers:** grid throughput depends on how many runs share the CPU (the same
`iotid20_time` run took 10.0 min with four runs in parallel and 3.7–3.8 min with fewer;
P1 ran at ~73 flows/s in the morning grid and comparable runs at ~154 flows/s later).
Speed figures for the paper must come from dedicated single-run timings.

**F5 — The subset choice moves false alarms, not accuracy.** IoTID20, 50,000 flows, 3 seeds:

| Stream | Accuracy | F1 | False-alarm rate |
|---|---|---|---|
| P1 file order (Normal + UDP/HTTP/ACK floods) | 99.33 ± 0.08 | 99.62 ± 0.05 | 4.98 ± 0.51 % |
| P2 campaign order (same rows) | 99.41 ± 0.04 | 99.67 ± 0.02 | 3.85 ± 0.58 % |
| + Mirai brute force (the paper's listed "DDoS types") | 98.85 ± 0.37 | 99.37 ± 0.21 | 12.15 ± 3.82 % |
| All attack classes | 99.15 ± 0.20 | 99.55 ± 0.10 | 12.20 ± 3.18 % |
| Time order (degenerate, F4) | 99.99 ± 0.01 | 100.00 | 0.00 % |

The real attack-campaign drift (P2) does not hurt MABTSE: the floods are easy to separate
from benign IoT traffic. Adding brute force or all classes moves accuracy by < 0.5 points
but multiplies false alarms by ~2.4 (about one benign flow in eight flagged).

**F6 — Under the paper's own protocol the attacks do nothing; without labels gradient-sign
attacks evade ~16% of DDoS flows. The paper's collapse is not reproduced.** IoTID20, 30,000
flows (train 20,100 / test 9,900), 3 seeds. Attacker: MLP surrogate trained on the same clean
training flows, eps 0.1 in the scaled space, perturbing DDoS flows only (attack_only).
ASR = share of perturbed DDoS flows classified benign (%).

| Attack | ASR online (instant labels) | ASR frozen (no labels) | Accuracy online / frozen |
|---|---|---|---|
| none (clean miss rate) | 0.08 | 0.08 | 99.49 / 99.48 |
| FGSM | 0.07 ± 0.05 | 17.05 ± 2.42 | 99.78 / 84.61 |
| BIM | 0.09 ± 0.02 | 15.80 ± 3.99 | 99.75 / 85.72 |
| PGD | 0.09 ± 0.04 | 15.94 ± 3.14 | 99.71 / 85.59 |
| C&W | 0.09 ± 0.01 | 5.85 ± 3.51 | 99.45 / 94.43 |

- The paper reports accuracy falling to 38.92–67.12% on IoTID20 under these attacks.
  Under its own Algorithm 1 (true label at once) the evasion gain is zero for every attack
  (-0.03 to +0.05 points); with no labels accuracy stays at 84.6–94.4%.
- C&W is the weakest attack here, not the strongest as the paper reports: its minimal
  perturbations fool the surrogate on every flow but rarely carry over to the tree
  ensemble (6% vs 26% in the 3,000-flow quick look, which had a weaker surrogate).
- Side observation to investigate: under instant labels the attacked runs have FEWER false
  alarms than the clean run (1.2–2.2% vs 3.6% for FGSM/BIM/PGD).
- Reading: robustness in the paper's setting comes from the instant-label assumption, not
  from the defence layers. This motivates the label-channel experiments (Step 11, S4).

**F7 — Every raw adversarial flow is impossible traffic, yet valid (repaired) attacks evade
just as well.** In the 3,000-flow run, 100% of the raw FGSM/BIM/PGD/C&W DDoS vectors break at
least one constraint mined from clean flows (15 constant, 5 binary, 5 categorical, 30
integer, 63 non-negative features, 7 equality groups, 24 Min ≤ Mean ≤ Max orderings); the
full runs' audits are in the result JSONs. After the monotone repair (never enlarging any
feature's change), frozen ASR over 3 seeds: FGSM 17.05 → 16.59, BIM 15.80 → 15.55,
PGD 15.94 → 16.07, C&W 5.85 → 4.45 — all inside one seed standard deviation. The evasion
lives in features an attacker can really change. Hypothesis for RADP: RAD separates raw
attacks by their impossible values, so its detection should drop on the repaired ones.

**F8 — CICIoT2023 reproduces.** Source: a pre-split Kaggle copy of CICIoT2023
(<https://www.kaggle.com/datasets/himadri07/ciciot2023>; `CICIOT23/test/test.csv`,
1,176,851 rows, the original 46 features and 34 labels; rows shuffled — every tenth of the
file has the same class mix). The page does not document how the split was made: state this
in the paper, together with the checks above. DDoS + benign subset: 883,690 rows,
benign 3.1% (always answering "attack" scores 96.9%). 50,000 flows (stride), 3 seeds:

| Metric | Ours | Paper |
|---|---|---|
| Accuracy | 99.76 ± 0.10 | 99.28 |
| Precision | 99.80 ± 0.09 | 98.88 |
| Recall | 99.95 ± 0.02 | 96.53 |
| F1 | 99.87 ± 0.06 | 97.98 |
| False-alarm rate | 6.19 ± 2.78 % | not reported |

The paper's own CICIoT2023 figures are inconsistent: precision 98.88 and recall 96.53 give
F1 = 97.69, not the 97.98 it reports.

**F9 — S4: the adaptation loop is both MABTSE's defence and its weak point; asymmetric trust
fixes it.** 30,000 flows, 3 seeds. Attacker: the repaired (valid) PGD of F7 on its own DDoS
flows; a fooled labeller calls each of those flows benign with probability q; audits verify
a random 10% of all flows. ASR (%) under evasion + poisoning, poisoning alone in brackets:

| Policy | IoTID20 q=0 | q=0.5 | q=1 | CICIoT2023 q=0 | q=0.5 | q=1 |
|---|---|---|---|---|---|---|
| no learning | 16.07 (0.08) | — | — | 83.72 (0.08) | — | — |
| vanilla (paper) | 0.12 | 48.61 (50.73) | 99.74 (99.64) | 0.08 | 46.99 (46.41) | 99.97 (99.80) |
| audit (selector only) | 0.13 | 35.31 (37.83) | 99.55 (99.48) | 0.10 | 28.31 (30.09) | 99.90 (99.64) |
| guard | 0.13 | 0.33 (0.07) | 68.41 ± 37.66 (0.16) | 0.10 | 0.19 (0.16) | 67.42 ± 55.58 (0.43) |
| strict | 0.12 | 0.21 (0.06) | 0.92 (0.08) | 0.11 | 0.15 (0.07) | 0.49 (0.10) |

False alarms (%), true labels, clean traffic / under attack: vanilla 3.56 / 2.23 (IoTID20),
3.30 / 2.00 (CICIoT2023); strict 4.92 / 4.62 and 9.11 / 17.72 ± 9.53; no learning 3.59 / 4.20.

- With instant true labels every policy neutralises even CICIoT2023's strong attack
  (83.7% evasion without learning → ~0.1%): F6 holds on both datasets.
- Poisoning alone, with no perturbation at all, lets about q of the DDoS flows through under
  the paper's rule; at q = 1 the detector inverts (accuracy 12.7% IoTID20, 3.6% CICIoT2023).
- Securing only the Thompson-Sampling selector (audit) helps at q = 0.5 (−13 to −19 points) and
  not at all at q = 1. Selection shares barely move: on IoTID20 the selector always keeps
  ARF-DDM, SRP-ADWIN and SRP-DDM and never picks ARF-ADWIN or KNN-ADWIN (each flags ~85% of
  benign flows on its own). The poison acts through the learners, not by steering the selector.
- guard contains poisoning alone and q = 0.5 but fails at q = 1 with evasion, unstably across
  seeds: evaded attacker flows labelled benign agree with the verdict, are learned, and make
  the next flows evade (a self-reinforcing loop).
- strict (10% verified) keeps ASR below 1% in every case on both datasets. Its cost is false
  alarms (+1.4 to +15.7 points). The worst case — CICIoT2023, true labels, under attack — comes from learning
  the attacker's perturbed flows as DDoS with no benign counterweight, which pushes the
  boundary into benign traffic: a remaining availability lever to discuss in the paper.
- CICIoT2023, repaired PGD, no learning: accuracy 18.95 ± 11.16%, inside the range the paper
  reports for CICIoT2023 under attack (13.08–32.38%). IoTID20 is not reproduced (85.5% vs
  38.92–67.12%). Compare all four attacks once the CICIoT2023 attack grid is read.

**F9b — S4 sweep (1 Nov): the poisoning curve is threshold-like, and the verified-label budget
trades evasion for false alarms.** Same setup as F9; the sweep adds q = 0.1, 0.25 for vanilla
and verified shares of 1%, 5%, 20% for strict (numbers rebuilt from the sweep log; the per-seed
JSONs are still to be sent).

| vanilla, ASR (%) | q = 0.1 | 0.25 | 0.5 | 1 |
|---|---|---|---|---|
| IoTID20, poisoning only / + evasion | 0.73 / 0.27 | 4.87 / 3.46 | 50.73 / 48.61 | 99.64 / 99.74 |
| CICIoT2023, poisoning only / + evasion | 0.30 / 0.20 | 1.85 / 1.66 | 46.41 / 46.99 | 99.80 / 99.97 |

| strict, verified share | 1% | 5% | 10% | 20% | vanilla |
|---|---|---|---|---|---|
| IoTID20 ASR, evasion + q=1 | 4.42 ± 1.96 | 1.37 ± 0.19 | 0.92 | 0.48 ± 0.17 | 99.74 |
| IoTID20 FPR clean / under attack | 6.65 / 25.13 | 5.32 / 7.47 | 4.92 / 4.62 | 4.62 / 4.35 | 3.56 / 2.23 |
| CICIoT2023 ASR, evasion + q=1 | 2.92 ± 1.33 | 0.75 ± 0.29 | 0.49 | 0.35 ± 0.13 | 99.97 |
| CICIoT2023 FPR clean / under attack | 19.62 / 38.84 | 13.92 / 25.52 | 9.11 / 17.72 | 7.01 / 11.11 | 3.30 / 2.00 |

- Up to a quarter of the attacker's flows mislabelled, the loop absorbs the poison (< 5%
  evasion); at half it lets about half through; at all of them, everything. The jump between
  0.25 and 0.5 matches the threshold behaviour predicted for label attacks on online learners
  (Margiotta, Goldt & Sanguinetti, NeurIPS 2023). A finer grid (0.3, 0.4) would pin it down.
- Even 1% verified labels hold evasion under 5% at q = 1. The price is false alarms, and it
  falls as the budget grows; on CICIoT2023 under attack it is still 11.1% at 20% verified
  (vanilla 2.0%).
- Mechanism check: with q = 1 the strict false alarms under attack drop back (IoTID20
  3.9–4.5%, CICIoT2023 3.8–9.0%, against 4.4–25.1% and 11.1–38.8% with true labels), because the attacker's flows now carry benign labels that strict skips. The cost
  comes from learning the attacker's perturbed, benign-looking flows as DDoS with benign
  traffic learned only from audits. IW-strict (v10, run #9) re-weights each audited benign flow
  by 1/a to restore that counterweight without trusting a single unverified benign label. On a
  hard synthetic stream it removed about a third of strict's extra false alarms; run #9
  measures it on the real data.

**F10 — CICIoT2023 under attack: without labels the detector collapses, and repaired (valid)
attacks are stronger and steadier than raw ones.** 30,000 flows, 3 seeds, setup as F6.

| Attack | Instant labels | No labels, raw | No labels, repaired | Accuracy, repaired |
|---|---|---|---|---|
| FGSM | 0.05 | 64.49 ± 53.38 | 79.57 ± 18.76 | 22.96 |
| BIM | 0.05 | 64.58 ± 53.45 | 84.68 ± 12.42 | 18.03 |
| PGD | 0.06 | 58.59 ± 49.96 | 83.72 ± 11.51 | 18.95 |
| C&W | 0.09 | 81.29 ± 15.46 | 86.55 ± 11.13 | 16.22 |

- With instant true labels nothing gets through (≤ 0.12% for every attack, raw or repaired):
  F6 holds on both datasets.
- Without labels, accuracy falls to 16–23%, inside the 13.08–32.38% the paper reports for
  CICIoT2023 under attack. So the paper's CICIoT2023 collapse reproduces, but only once the
  label feedback its own Algorithm 1 relies on is removed.
- Raw FGSM/BIM/PGD are bimodal across seeds (seed 1: 99.7%, seed 2: 73–91%, seed 3: 3%);
  repaired versions evade 62–99% on every seed. Impossible feature values can be *caught*, so
  raw-space evaluation can understate the threat: feasibility is not just a constraint that
  weakens attacks. The figures show every seed as a dot for this reason.
- Which DDoS classes evade changes with the seed (repaired PGD: ICMP flood 0.4% on seed 1,
  99.7% on seed 2): transfer depends on the surrogate. Five seeds for CICIoT2023 would make the means
  steadier for the paper.
- Seed 1: repaired FGSM, BIM and PGD give identical results (78.05%): the repair maps the three
  perturbations to the same valid flows. A sign that, on CICIoT2023, the repair (rounding,
  orderings) decides much of the final perturbation.
- Caveat for the paper: the constraint miner treats CICIoT2023's window features (`Number`,
  `Weight`) as continuous.

**F11 — Label delay decides evasion; self-labelling does not protect.** Raw PGD and C&W, ASR (%)
when true labels arrive D flows late:

| | instant | 100 | 1,000 | 5,000 | no labels | self-labels |
|---|---|---|---|---|---|---|
| IoTID20 PGD | 0.09 | 0.22 | 1.77 | 8.50 | 15.94 | 15.03 |
| IoTID20 C&W | 0.09 | 0.17 | 0.96 | 3.30 | 5.85 | 0.28 |
| CICIoT2023 PGD | 0.06 | 0.68 | 6.20 | 30.07 ± 25.46 | 58.59 | 66.70 ± 57.67 |
| CICIoT2023 C&W | 0.09 | 0.90 | 7.94 | 40.84 ± 8.15 | 81.29 | 49.53 ± 48.57 |

- Evasion grows smoothly with the delay. At flood rates 1,000–5,000 flows is seconds of
  traffic, so "instant labels" is the assumption doing the work in the paper's robustness.
- Self-labelling (learning the model's own verdicts) gives no protection on average and is
  bimodal on CICIoT2023; the one exception is C&W on IoTID20 (0.28%), whose small perturbations
  are mostly still classified correctly, so the self-labels are mostly right.

**F12 — RADP (the paper's Layer 1) detects impossible values, not adversarial traffic.**
3 seeds, detector frozen. Flagged: perturbed DDoS flows RAD deletes. ASR: DDoS flows that get
through end to end.

| | IoTID20 | CICIoT2023 |
|---|---|---|
| RAD hold-out accuracy (the paper-style check) | 99.4–100% | 99.4–100% |
| GAN fidelity (C2ST AUC, 0.5 = indistinguishable) | 1.000 | 1.000 |
| Flagged, raw attacks | 100% (C&W 93.9) | 100% (C&W 99.2) |
| Flagged, repaired attacks | 13.0–13.7% | 98.9–99.8% |
| Flagged, repaired, RAD without the GAN | 36.5–47.3% | 98.9–99.9% |
| ASR repaired PGD: no RADP → with RADP | 16.1 → 12.5 | 83.7 → 0.7 |
| Benign flows deleted (with / without GAN) | 0.1 / 0.1% | 18.4 ± 17.7 / 4.8 ± 2.1% |
| Unseen C&W (leave-one-out), repaired: flagged → ASR | 0.0% → 4.5 | 19.9% (seeds 60 / 0 / 0) → 71.7 |

- On IoTID20 RAD separates raw attacks by their impossible values (F7's hypothesis confirmed)
  and misses 87% of the repaired ones; the GAN's samples make it worse.
- On CICIoT2023 it catches the known attacks, repaired or not, but deletes 18% of legitimate
  flows (22% of benign traffic lost with false alarms) and misses C&W when it has not trained on
  it: an "unknown attack" claim the paper never tested (gap 5).
- The GAN never produces samples a classifier cannot tell apart from the real adversarial
  ones (AUC 1.000 everywhere) and only adds collateral damage (4.8% → 18.4% benign deleted on
  CICIoT2023).
- The paper's "recovered accuracy" (survivors only) hides this: on clean CICIoT2023 traffic it
  reads 99.8% while 22% of benign traffic is lost (gap 10).

**F13 — The paper's attack setting perturbs benign traffic too.** Perturbing every flow
("all", which an attacker controlling only its own flows cannot do), no labels, PGD: false
alarms 65.1 ± 11.7% (IoTID20) and 78.4 ± 9.6% (CICIoT2023), accuracy 78.0% and 40.8%. This
moves IoTID20 toward the paper's 38.92–67.12% but does not reach it; the realistic setting
(attacker's flows only) is F6 / F10.

**F14 — IW-strict removes most of strict's false-alarm cost at 10–20% verified labels, and
evasion stays ≤ 1.2% under full poisoning.** 30,000 flows, 3 seeds, paired with strict (same
seeds, audit and label masks). False alarms (%) with true labels, clean / under the repaired PGD
attack; ASR (%) under evasion + full poisoning (q = 1):

| Dataset | Verified | strict FPR | IW-strict FPR | strict ASR | IW-strict ASR |
|---|---|---|---|---|---|
| IoTID20 | 5% | 5.32 / 7.47 | 6.63 / 11.36 ± 9.30 | 1.37 | 1.74 |
| IoTID20 | 10% | 4.92 / 4.62 | 4.35 / 2.99 | 0.92 | 1.19 |
| IoTID20 | 20% | 4.62 / 4.35 | 4.13 / 2.39 | 0.48 | 0.46 |
| CICIoT2023 | 5% | 13.92 / 25.52 | 8.61 / 16.52 | 0.75 | 0.83 |
| CICIoT2023 | 10% | 9.11 / 17.72 | 5.70 / 4.51 | 0.49 | 0.51 |
| CICIoT2023 | 20% | 7.01 / 11.11 | 4.70 / 3.40 | 0.35 | 0.33 |

Paper's rule (vanilla): FPR 3.56 / 2.23 (IoTID20), 3.30 / 2.00 (CICIoT2023); ASR 99.74 / 99.97.

- At 10–20% verified, IW-strict costs +0.2 to +2.5 points of false alarms over the paper's rule
  (strict: +1.1 to +15.7). CICIoT2023 under attack: 17.7% → 4.5% at 10%, 11.1% → 3.4% at 20%.
- Robustness is kept: ASR ≤ 1.2% under evasion + full poisoning (IoTID20 0.92 → 1.19 at 10%;
  CICIoT2023 unchanged), ≤ 0.4% under poisoning alone. Vanilla lets 99.7–100% through.
- At 5% verified, 20 copies per audited benign flow are too many: IoTID20 gets worse and unstable
  (11.4 ± 9.3% under attack) and CICIoT2023 improves but stays high (16.5%). Design rule for the
  paper: re-weighting needs about 10% of flows verified; below that, verify more rather than
  weight more (a lower copy cap is untested).
- Under full poisoning IW-strict's false alarms are lowest (CICIoT2023 1.5–4.6%): the attacker's
  flows arrive labelled benign and are skipped, as the F9b mechanism predicts.
- Selection shares do not move here either (IoTID20 keeps ARF-DDM, SRP-ADWIN, SRP-DDM), as in F9.

**F15 — Adversarial training stops label-free evasion from this attacker, at a false-alarm
cost, and cannot touch label poisoning.** E9 (run #11), 30,000 flows, 3 seeds; one repaired copy
per DDoS training flow, crafted on the defender's surrogate. The "none" detector reproduces F6/F10.

| Dataset | Detector | FPR clean, no labels / delay 1,000 | Worst ASR, repaired, no labels | ASR rep. PGD / C&W, delay 1,000 |
|---|---|---|---|---|
| IoTID20 | none | 3.59 / 3.56 | 16.59 (FGSM) | 1.79 / 0.67 |
| IoTID20 | AT PGD only | 5.38 / 5.24 | 0.03 (C&W, unseen) | 0.00 / 0.03 |
| IoTID20 | AT all four | 5.87 / 4.86 | 0.19 (PGD) | 0.02 / 0.04 |
| CICIoT2023 | none | 4.20 / 3.90 | 86.55 (C&W) | 8.79 / 8.81 |
| CICIoT2023 | AT PGD only | 8.41 ± 6.25 / 7.60 | 0.05 (C&W, unseen) | 0.02 / 0.06 |
| CICIoT2023 | AT all four | 8.11 ± 6.31 / 5.71 | 0.06 | 0.01 / 0.03 |

- Evasion without labels: 80–87% → < 0.1% (CICIoT2023), 16% → < 0.2% (IoTID20); PGD-only training
  covers FGSM, BIM, C&W. Cost: +1.8 to +2.3 FPR points (IoTID20), ~+4 (CICIoT2023, unstable).
- Beats RADP: unseen C&W 0.05% vs 71.7% ASR; nothing deleted vs up to 18% of benign flows.
- Likely optimistic: non-adaptive attacker; attacker and defender surrogates share architecture and
  data (different seeds), so "unseen" attacks share a gradient source.
- Cannot address poisoning: F9's poisoning-only attack uses unperturbed flows (99.64% at q = 1).
  Prediction (untested): AT + IW-strict are complementary.

**F16 — 15 seeds (run #12, 2–3 Nov): the label-channel results replicate; four 3-seed numbers
change.** Same settings as F6–F15 (30,000 flows, eps 0.1), seeds 1–15 (`--tag s15`); RADP seeds
1–5. Mean ± std over seeds; ASR in %, repaired PGD unless stated.

| | IoTID20 | CICIoT2023 |
|---|---|---|
| Instant true labels | 0.10 | 0.08 |
| Label delay 1,000 / 5,000 flows (raw PGD) | 1.80 / 8.65 | 5.27 / 26.17 ± 18.32 |
| No labels: raw / repaired | 16.42 ± 5.41 / 17.32 ± 4.22 | 51.73 ± 36.20 / 48.52 ± 39.02 |
| No labels, C&W: raw / repaired | 11.50 ± 5.74 / 11.25 ± 6.03 | 47.06 ± 35.16 / 47.69 ± 37.38 |
| Vanilla, q = 0.25 / 0.5 / 1 | 3.37 / 51.50 / 99.74 | 1.60 / 50.55 / 99.96 |
| Poisoning alone (no perturbation), vanilla q = 0.5 | 52.94 | 48.63 |
| Audit (selector only) q = 0.5 / 1 | 36.94 / 99.59 | 30.97 / 99.84 |
| Guard q = 1: with evasion / poisoning alone | 83.73 ± 23.97 / 0.19 | 62.18 ± 45.54 / 0.48 |
| Strict / IW-strict 10% / IW-strict 20%, q = 1 | 0.88 / 1.15 / 0.53 | 0.44 / 0.43 / 0.30 |

False alarms (%) with true labels, clean traffic / under attack:

| Policy | IoTID20 | CICIoT2023 |
|---|---|---|
| Vanilla (paper's rule) | 3.33 / 2.17 | 5.77 / 3.52 |
| Strict 10% | 4.53 / 5.33 | 12.61 / 23.12 ± 15.26 |
| IW-strict 10% | 4.21 / 3.52 | 10.25 / 6.95 |
| IW-strict 20% | 3.95 / 2.64 | 7.47 / 4.68 |

- Replicates: F6 (instant labels stop transfer evasion), F9 and F9b (the threshold lies between
  q = 0.25 and 0.5; poisoning, not the perturbation, does the damage: evasion adds ≤ 2 points),
  F11 (evasion grows with the delay), the robustness half of F14 (strict and IW-strict ≤ 1.2%
  everywhere) and F15's evasion result.
- New: guard holds against poisoning alone but not against evasion + full poisoning, where it
  fails on some seeds and holds on others (± 24 and ± 46).
- Correction to F10: "repaired attacks are stronger and steadier" is withdrawn. With 15 seeds,
  raw and repaired transfer are alike on CICIoT2023 (FGSM 50.8 / 47.3, BIM 52.6 / 48.7, PGD
  51.7 / 48.5, C&W 47.1 / 47.7; std 35–39), and the 3-seed means (58.6–86.6) were high. A std
  this large around a mean near 50 suggests seeds at both ends; confirm with
  `scripts\per_seed.py` and report median, IQR and per-seed dots, not the mean alone.
- Correction to F11: C&W on IoTID20 without labels evades 11.3–11.5%, not 5.9%.
- Correction to F14: IW-strict's false-alarm price over vanilla is +0.5 to +1.7 points at 20%
  verified and +0.9 to +4.5 at 10% (3 seeds: +0.2 to +2.5). Its gain over strict under attack
  holds: CICIoT2023 23.1% → 7.0% (vanilla 3.5%), 82% of strict's extra false alarms removed.
- Correction to F15: adversarial training's false-alarm cost on CICIoT2023 is +7.7 points without
  labels (6.41 → 14.13 ± 7.30) and +3.7 with labels 1,000 flows late (6.05 → 9.75); IoTID20 +2.2 /
  +1.8. Evasion without labels: IoTID20 17.3 → 0.1% (PGD), 11.3 → 0.7% (C&W); CICIoT2023 48.5 →
  0.03%, 47.7 → 0.04%.
- RADP (F12), 5 seeds: on IoTID20 RAD flags 10.9–17.1% of repaired attacks (91–100% of raw ones);
  repaired PGD still gets through end to end, 16.0 → 13.0%. On CICIoT2023 it flags 98–100% of them
  but deletes 26.4 ± 17.2% of benign flows (2.9 ± 3.0% without the GAN, which still flags 93–96%).
- P8 (significance after Holm) awaits `scripts\stats.py` on the laptop. With 15 seeds the
  smallest exact two-sided Wilcoxon p is 6.1 × 10⁻⁵, so every comparison where all seeds agree
  survives Holm over these families.


**F17 — CIC-IDS2017 replicates the label-channel results (15 seeds; P9 held).** Corrected
CIC-IDS2017, Friday 20:31–21:26, 30,000 flows (test 75.4% DDoS, one source). Instant true labels:
0.02% evasion. No labels, repaired PGD: 45.4 ± 34.1% (median 39.3%; seeds at both ends, as on
CICIoT2023). Labels 5,000 flows late (raw PGD): 28.2%; 300 s late: 35.8%. Evasion + full
poisoning: vanilla 99.95%, strict 0.14%, IW-strict 0.13%. Adversarial training and the chain:
see F20, F21. A third, time-ordered, independently labelled stream now carries every
label-channel claim.

**F18 — Uncertainty-directed audits use fewer audits and give far fewer false alarms (three
datasets).** Audits go to the flows the detector is least sure about instead of at random; same
10% budget. 15 seeds, paired Wilcoxon + Holm (`scripts\stats.py --preset frameunc`):

| | IoTID20 | CICIoT2023 | CIC-IDS2017 |
|---|---|---|---|
| Audits used under attack, true labels (random: 992) — strict / IW-strict | 911 / 899 | 902 / 897 | 818 / 727 |
| False alarms under attack, true labels — IW-strict, random → uncertain | 3.52 → 0.45 | 6.95 → 0.64 | 0.25 → 0.02 |
| — strict, random → uncertain | 5.33 → 2.45 | 23.12 → 3.78 | 0.66 → 0.11 |
| — vanilla (learns every label), for reference | 2.17 | 3.52 | 0.11 |
| Evasion + full poisoning — strict, random → uncertain | 0.88 → 0.28 | 0.44 → 0.45 | 0.14 → 0.13 |
| — IW-strict, random → uncertain | 1.15 → 0.31 | 0.43 → 0.46 | 0.13 → 0.12 |
| False alarms, evasion + full poisoning — IW-strict, random → uncertain | 2.25 → 0.43 | 3.62 → 0.78 | 0.16 → 0.03 |

- Every false-alarm difference is significant (p_Holm ≤ 0.005; at most one seed the other way).
  Uncertainty audits also used fewer audits than random (p_Holm ≤ 0.001, 14–15 of 15 seeds), so
  the gain does not come from a bigger budget.
- Against vanilla, under attack with true labels: IW-strict and IW-consensus with uncertainty
  audits have fewer false alarms on all three datasets (p_Holm ≤ 0.006); strict is level.
- Evasion under full poisoning falls only on IoTID20; elsewhere it was already at the floor.
- Caveat: CIC-IDS2017's test stream has ~2,400 benign flows, so 0.25% is ~6 flows and 0.02% is
  under one flow per run: direction, not magnitude. Open: a matched operating-point check (equal
  detection rate), so the drop cannot be read as a shifted threshold.

**F19 — Framing: trusting attack labels opens a false-alarm attack; uncertainty-directed audits
make the damage temporary (three datasets).** The attacker gets benign-looking flows labelled DDoS
for half the test stream (2% or 10% of flows). With random audits every policy that trusts
attack labels suffers; strict most (2% framing: 61 / 92 / 23% vs vanilla 11 / 25 / 2.5%).
Paired tests, uncertainty vs random audits, 3 datasets × 3 policies × 2 rates × clean / under
attack:

- Whole stream: lower false alarms in 34 of 36 cells (p_Holm ≤ 0.01), 2 not significant.
- After the campaign: lower in all 36 (p_Holm ≤ 0.012).

Versus vanilla (no audits), with uncertainty audits:

- IW-consensus is never worse: lower in 10 of 12 whole-stream cells (CIC-IDS2017 at 10% is a
  tie) and in 12 of 12 after the campaign.
- IW-strict is lower in all 6 cells at 2% framing, and significantly lower after the campaign in
  11 of 12 (the twelfth lower, n.s.), but during
  a 10% campaign it is level on IoTID20 and higher on CIC-IDS2017 (10.6 vs 7.1%, p_Holm = 0.003).
- Strict is worse than vanilla in most cells: do not pair strict with trusted attack labels.

Clean traffic, 10% framing (false alarms %, whole stream / after the campaign):

| | IoTID20 | CICIoT2023 | CIC-IDS2017 |
|---|---|---|---|
| vanilla | 37.0 / 14.8 | 51.0 / 15.6 | 7.1 / 0.9 |
| IW-strict, random → uncertain | 62.4 → 38.2 / 36.2 → 8.9 | 70.5 → 38.8 / 43.0 → 1.6 | 16.7 → 10.6 / 2.5 → 0.7 |
| IW-consensus, random → uncertain | 49.0 → 27.6 / 33.4 → 7.7 | 62.7 → 37.8 / 39.1 → 1.5 | 13.5 → 7.0 / 2.3 → 0.4 |

- CIC-IDS2017 is far less sensitive to framing (vanilla 7.1% vs 37–51%): one LOIC source is easy
  to separate from benign traffic, so framed flows generalise less.
- Under full poisoning alone IW-consensus equals IW-strict by construction (no attack labels
  reach the consensus check); the configuration that holds against poisoning and framing is
  IW-consensus with uncertainty audits. Its cost: under poisoning + 5% framing with random
  audits it lets 1.8% (IoTID20) through vs 1.1% for IW-strict and 0.2% for strict. Whether
  uncertainty audits close that gap is the optional `combounc` run (Step 20).

**F20 — Detector chain: model diversity helps; message passing does not beat a matched
control (15 seeds).** No labels, repaired PGD, thresholds calibrated to 1% false alarms.

- Online MLP after MABTSE: CICIoT2023 48.5 → 1.9% (catches 86% of MABTSE's misses); fails on
  IoTID20, and on CIC-IDS2017 PGD where its architecture matches the attacker's surrogate.
- Host-graph GNN: catches 37–43% of MABTSE's misses on IoTID20 (P2) and 98% on CIC-IDS2017, but
  the parameter-matched host-feature MLP (48% and 97%) is never significantly worse (evasion left:
  8.8% vs 11.0% on IoTID20, 1.25% vs 0.72% on CIC-IDS2017, both n.s.); the one significant
  difference favours the control (C&W on CIC-IDS2017, drift-focused GNN). CIC-IDS2017's 98% is the
  volume of one NAT source.
- Graph-aware attacker: spoofing 10 source identities raises evasion after the full chain
  12.5 → 18.9% (IoTID20 P2) and 1.3 → 17.8% (CIC-IDS2017); thinning to 25% of the flows leaves
  2.6% / 0.03% of the attack volume getting through.
- The drift-focused GNN still scores 87–95% of flows; calibrated thresholds overshoot the 1%
  target by 0.8–2.9 points on test traffic.
- Matches the literature (simple temporal baselines match temporal GNNs: GraphMixer, TGB /
  EdgeBank). Reported as a negative result; temporal GNNs go to Future Work.

**F21 — Label-only attacks partly defeat adversarial training (5 seeds).** HopSkipJump, 2,000
queries per flow, restricted to valid traffic: 25.2% (IoTID20) and 51.2% (CICIoT2023) evade the
plain detector; 14.0% and 2.0% evade the adversarially trained one, whose transfer evasion is
0.03% / 0.06%. A surrogate distilled from the detector's verdicts transfers no better than the
plain one (IoTID20 17.6 vs 16.0%). Raw-space HopSkipJump evasions mostly die when repaired to
valid traffic (31.6 → 4.0%).

**F22 — Small audit budgets need copy caps; a noise-rate estimate is not a defence (15 seeds).**
At 5% audits, capping IW-strict's copies at 5–10 halves its false alarms; at 2% audits evasion
under full poisoning is 1.8–4.0% vs 0.4–0.9% at 10%. The noise-aware baseline (learns 1 − rho of
unverified benign labels) lets 60% (IoTID20) and 5.6% (CICIoT2023) through under full poisoning,
with clean false alarms near vanilla's.

**S4 design (v9) — what the adaptation-loop experiment tests.** F6 says MABTSE's robustness
comes from learning true labels at once. S4 asks what happens when the label source is also
fooled: each of the attacker's flows is labelled benign with probability q. Questions:
(1) how fast does label poisoning turn adaptation against the detector, alone and combined
with evasion; (2) does it steer the Thompson-Sampling selector (selection shares, posterior
means; per-learner evasion from the frozen runs); (3) which update policy contains it —
protecting only the selector (`audit`), verifying downgrades of flagged flows (`guard`), or
never learning an unverified benign label (`strict`) — and at what false-alarm cost. Mock-data
tests only check the machinery; the real numbers come from the Step 13 grid.

# 0. What we are doing, in one paragraph

We take a published online IoT DDoS **defence** (Beshah et al., MSAAD, IEEE Access 2025),
reproduce it faithfully, and then do what the paper did not: evaluate its robustness
*properly* and build a **more robust, better-justified** version. The work is defensive and
runs entirely on public benchmark datasets (IoTID20, CICIoT2023) against our own
reimplemented model. The headline novel contribution is a rigorous study of the
**adaptation loop** — the Thompson-Sampling classifier selector, the ADWIN/DDM drift
detectors, and the label-feedback channel — which the base paper leaves completely
untested, plus a corruption-robust update rule for that loop (results: the label channel, not
the selector, is the weak point; see §1).

# 1. The claim we can defend as novel

**Revised after the results (1 Nov).** The selector hypothesis below was tested and did not
hold (F9: securing the selector barely helps, selection shares do not move; the poison acts
through the learners). The claim the results support:

> *The robustness of an adaptive online IoT DDoS detector (MSAAD) rests on an instant,
> trustworthy label channel. With true labels at once, evasion is neutralised; as labels are
> delayed it returns (F11), and an attacker who makes the labeller call its own flows benign
> turns the adaptation loop against the detector, with a threshold-like effect in the poisoned
> share (F9, F9b). Protecting the bandit selector does not help. One-sided label trust with a
> small random audit budget (strict) bounds evasion below 1% at 10% audits, and weighting each
> verified benign flow by the inverse audit rate (IW-strict) brings its false-alarm cost to within
> 0.2–2.5 points of the paper's rule at 10–20% audits (F14). The paper's Layer 1 (RADP) detects
> impossible feature values rather than adversarial traffic (F12).*

Prior work to position against (checked 1 Nov): label attacks on online learners are known in
theory — Margiotta, Goldt & Sanguinetti, "Attacks on Online Learners: a Teacher-Student
Analysis", NeurIPS 2023 (threshold-like accuracy drop, no defence); poisoning of an online
network anomaly detector with a bounded-false-positive protection — Kloft & Laskov, "Security
Analysis of Online Centroid Anomaly Detection", JMLR 13:3681–3724, 2012; defences for online
poisoning including a labelling-oracle defence — Wang, Jha & Chaudhuri, "An Investigation of
Data Poisoning Defenses for Online Learning", arXiv 1905.12121, 2019. What none of them do:
evaluate a published adaptive IoT DDoS detector under an attacker that controls only its own
flows, combine evasion with label poisoning, test the bandit selector as the lever (negative
result), or give a one-sided trust rule with its audit-budget / false-alarm trade-off.

The original claim (30 Oct), kept for the record:

> *No prior work evaluates or hardens the online model-selection loop of a streaming IoT
> DDoS detector.* Bandit reward-poisoning is known in theory (Liu & Shroff, ICML 2019; Jun
> et al., NeurIPS 2018) and Thompson-Sampling **routing** exists in IDS (IDS-Anta / SHIELD-IDS),
> but nobody has studied that selector as a weak point, nor replaced it with a
> corruption-robust selector, for an online DDoS detector — with end-to-end metrics and a
> leakage-free streaming protocol.

This is the "don't reinvent the wheel" choice: it reuses the base paper's own design as the
baseline, needs no new dataset to be novel, and is cheap enough to finish on a laptop.

# 2. Gap scan — what is wrong with the base paper (the openings we exploit)

Grouped by how we turn each gap into a contribution. (Severity is our reading against the
Carlini / Tramèr / Arp evaluation standards.)

| # | Gap in the base paper | Severity | We turn it into |
|---|------------------------|----------|-----------------|
| 1 | No threat model (attacker knowledge / capability / goal never stated; benign *and* attack samples perturbed although an attacker controls only attack traffic) | Critical | A formal threat model, re-run under each cell |
| 2 | Gradient attacks on non-differentiable River models imply an undisclosed surrogate → transfer attacks mislabelled white-box | Critical | Attacks that need no surrogate; report the surrogate-vs-direct gap |
| 3 | Unconstrained ε=0.1 over all features (incl. one-hot / counts) → many "adversarial" samples are not valid traffic | Critical | Feasibility-constrained evaluation; measure how many of the paper's perturbations are invalid |
| 4 | No adaptive / defence-aware evaluation | Critical | Defence-aware robustness tests (EOT over the random selector) |
| 5 | "Unknown attacks" never actually tested (RAD trained on the same four attacks/ε it is tested on) | High | Leave-one-attack-out + ε sweep → the real generalisation gap |
| 6 | Layers 2–3 give no measured robustness; all recovery comes from RADP deletion; no ablation | High | Full ablation isolating each layer |
| 7 | "Hard to replicate" pool claim untested; 4/5 learners are the same family | High | Transfer / extraction test of the claim |
| 8 | Bandit never learns as printed; reward undefined → **the selector is an unstudied weak point** | High | **Headline:** selector-robustness study + corruption-robust selector |
| 9 | Purification = deletion → RAD false positives are self-inflicted DoS; TPR/FPR never reported | High | Report detector TPR/FPR + benign-drop |
| 10 | "Recovered accuracy" computed only on surviving samples (near-tautological) | Critical | End-to-end metrics (attack-success rate, benign-drop) |
| 11 | Tiny streams; drifts fall in warm-up | Medium | Full-scale prequential streams |
| 12 | Leakage risks (global min-max, offline feature selection, in-stream SMOTE) | High | Strictly leakage-free streaming pipeline (**already built** in `preprocessing.py`) |
| 13 | Single run; unnamed statistical test | Medium | Multi-seed runs + CIs + named test |
| 14 | Internal inconsistencies (precision reported as accuracy; impossible F1 values; swapped legends) | Medium | A corrected, open reproduction is itself a contribution |
| 15 | Throughput far below flood rates; no edge numbers; RADP overhead unmeasured | High | Latency/throughput measurement (optional edge board) |

# 3. Current advancements and where they still leave room

- **Drift-detector poisoning** (Korycki & Krawczyk 2023; "Online AutoML" arXiv 2610.05810, 2026;
  "Learn to Adapt" 2206.07581) — this area is now crowded, so we keep drift-detector
  manipulation as a *secondary* experiment, not the headline, and cite it explicitly.
- **Adversarial-vs-natural drift** (AISec 2024; AMDS 2026) — AMDS even names "distinguishing
  genuine attack evolution from adversarial manipulation of the learning signal" as open.
  We cite it as motivation, not overlap.
- **Thompson-Sampling routed IDS** (IDS-Anta, SHIELD-IDS 2026) — they *use* a bandit selector
  but never study it as a weak point. **That is precisely our gap.**
- **Constrained tabular robustness** (CAPGD/CAA, TabularBench) and **exact tree-ensemble
  evaluation** (Kantchelian ICML 2016) are mature tools we *reuse* rather than reinvent.
- **Corruption-robust bandits** (robust Thompson Sampling, arXiv 2410.19705; BARBAR) give us
  an off-the-shelf, citable defence with regret guarantees.

- **Label attacks on online learners** (Margiotta et al., NeurIPS 2023; Kloft & Laskov, JMLR
  2012; Wang, Jha & Chaudhuri 2019) — the general idea is known; our contribution is the
  measured, system-level version on a published IoT DDoS detector plus the one-sided defence.
  Cite all three.

**Net (30 Oct):** the selector-loop angle is open; everything we need to evaluate it is a
mature, reusable library. **Update (1 Nov):** the selector turned out not to be the lever; the
label channel is, and its general idea has prior work, so the paper's novelty is the realistic
threat model, the measurements and the one-sided trust defence (§1).

# 4. The project pipeline (permanent stages)

Each stage has an owner module, an output, and a gate. Stages run roughly in order; S5/S6
interleave once S4 produces results.

| Stage | Name | Output | Gate |
|------|------|--------|------|
| **S0** | Environment & repo | runnable scaffold | `smoke_test.py` PASS ✅ (done) |
| **S1** | Leakage-free data layer | prequential streamers + running scaler | loads both datasets in order, no shuffle ✅ (built) |
| **S2** | Reproduce MABTSE (the defence) | clean accuracy on both datasets | within ~1–2 pts of 99.50 / 99.28 |
| **S3** | Robustness harness + end-to-end metrics | ASR / benign-drop / TPR-FPR instruments on our own model | metrics produced on a dry run; RADP (Layer 1) reproduced |
| **S4** | **Novel:** adaptation-loop study + robust update rule | label-channel result + update policy (strict / IW-strict) | a policy that bounds evasion under poisoning vs vanilla under the same test ✅ (strict, F9); open: its false-alarm cost |
| **S5** | Benchmarking | multi-seed, ablations, cross-dataset, (optional) edge latency | all headline tables multi-seed with CIs |
| **S6** | Writing + artifact | paper + open-source repo + Zenodo DOI | preprint posted; submission packaged |

**Compute note.** S2 and S5 are CPU-bound (River tree ensembles) — your i7-14650HX handles
the 50k–200k subsamples in minutes per run. The **RTX 5060 matters only at S3+** (training
the RADP GAN and any differentiable surrogate; ~1–4 GPU-hours each, fits in 8 GB with small
batches). Plan GPU sessions around S3/S4, not S2.

# 5. The one-week sprint (30 Oct → 6 Nov 2026)

Baseline target: a **B-tier** venue is the floor; the A-tier plan (DSN / EuroS&P 2027) is
the stretch. This week is S0–S2 plus the start of S3.

| Day | Goal | Gate / fallback |
|-----|------|-----------------|
| **D1 (done)** | Repo + pipeline + MABTSE reproduction code; smoke test green | ✅ pipeline learns synthetic stream |
| **D2** | Download IoTID20 + CICIoT2023; fix `base.yaml` label columns; first real `repro_baseline` runs | both datasets stream without error |
| **D3** | Tune the subsample + confirm clean accuracy on both datasets | **within ~1–2 pts of paper** → S2 passes. Else: pivot to a reproducibility/corrected-evaluation paper (still publishable) |
| **D4** | Add end-to-end metric instruments (ASR, benign-drop, detector TPR/FPR) to `src/eval`; wire an "under perturbation" eval mode | metrics produced on a dry run |
| **D5** | Reproduce RADP Layer-1 (GAN + detector) — documented assumptions; GPU session | detector trains; flags a held-out perturbed set |
| **D6** | First selector-loop probe on our own model: does concentrating selection on a weak learner measurably change end-to-end robustness? | a measurable effect → S4 is alive |
| **D7** | Write up Week-1: reproduction table + corrected-evaluation notes + the S4 plan; freeze a tagged commit | one-page progress report + green CI |

**End-of-week deliverable:** a reproduced, leakage-free MABTSE baseline on both datasets,
end-to-end metrics in place, and a first signal on the novel direction — enough to commit to
the S4 contribution with confidence.

# 6. Metrics we instrument from the start

End-to-end **attack-success rate** and **benign-drop rate** (not just post-filter accuracy);
detector **TPR/FPR**; **prequential F1/accuracy** over the whole stream; **throughput**
(samples/s). These replace the base paper's near-tautological "recovered accuracy".

# 7. Risks and the enforced rule

| Risk | Mitigation |
|------|------------|
| Base paper won't reproduce (underspecified GAN/bandit) | Document every assumption; if it fails, the corrected-evaluation paper is the fallback |
| Selector effect underwhelms | **Happened (F9).** The label channel became the headline instead; drift-detector manipulation stays a backup |
| Defence costs too many false alarms | **Mitigated (F14):** IW-strict at ≥ 10% verified; report that 5% is too few for re-weighting |
| Reviewers ask for an adaptive attacker or a second detector | A-tier only: an attacker that labels benign flows as DDoS (the trusted direction), a second online detector, a third dataset, 5 seeds |
| Timeline slips | B-tier / workshop (AISec, DLSP) and Q1 journals are the safety net below A-tier |

**Enforced rule for the whole project:** *reproduce before you attack; measure end-to-end,
not post-filter; document every assumption; one tagged commit per stage gate.* No stage is
"done" until its gate is green.
