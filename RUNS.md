# Run journal

Every experiment run, newest last: what ran, the exact command, the code version, what came out,
and a note. `scripts/push_run.py` writes the entries, commits the results and pushes them (SETUP.md,
Step 15). The table at the end is rebuilt from the result JSONs on every push. Findings and their
numbers live in PLAN.md (F1–F13).

## Before the repository (30 Oct – 1 Nov 2026)

Reconstructed from the result files and the project notes; times are when the runs finished
(laptop time, IST). The exact per-run times are in the history table at the end.

| When | What ran | Setup Guide | Findings |
|---|---|---|---|
| 30 Oct | Environment, leakage-free data layer, MABTSE reproduction code; self-checks (v1–v6) | Steps 1–8 | — |
| 30–31 Oct | Clean reproduction grid, IoTID20: file order (P1), campaign order (P2), time order, + Mirai brute force, all classes; 3 seeds | Step 9 | F1–F5 |
| 31 Oct | CICIoT2023 (Kaggle pre-split copy): extraction, inspector report, clean grid; 3 seeds | Steps 5, 6, 9 | F8 |
| 31 Oct, 09:23–15:49 | Attack grid, IoTID20 and CICIoT2023: FGSM / BIM / PGD / C&W, raw and repaired, instant labels vs none; 3 seeds | Step 10 | F6, F7, F10, F13 |
| 31 Oct, 16:38–16:49 | Label grid (`--tag labels`): PGD and C&W with label delays 100 / 1,000 / 5,000 and self-labels; both datasets | Step 11 | F11, F13 |
| 1 Nov, morning | RADP quick look, IoTID20 (`--limit 3000`) | Step 12 | — |
| 1 Nov, 13:31–13:47 | Adaptation-loop grid (S4): poisoning q = 0 / 0.5 / 1 x vanilla / audit / guard / strict at 10% verified; both datasets | Step 13 | F9 |
| 1 Nov, 16:16–16:53 | RADP grid: RAD with and without the GAN, leave-one-attack-out; both datasets | Step 12 | F12 |
| 1 Nov, evening | S4 sweep (`--tag sweep`): q = 0.1 / 0.25 for vanilla; strict at 1 / 5 / 20% verified | Step 13, part 4 | F9b |
| 1 Nov, night | Code v10: IW-strict policy, figures with every seed as a dot, findings F9b–F13 | — | — |
| 1–2 Nov, night (57 min) | IW-strict grid (`--tag iw`): IW-strict at 5 / 10 / 20% verified, q = 0 / 0.5 / 1; both datasets | Step 13, part 5 | F14 |
| 2 Nov | Code v11–v12: this journal, `scripts/push_run.py`, `run_grid.py --push`, Step 15; findings F14 | Step 15 | — |

## Journal

### 2026-11-02 13:02 (UTC+05:30) - Repository created: code v12, documents and all results up to 2 Nov

- **Code version:** first commit; this commit also changes 39 code/document file(s): `.gitattributes`, `.gitignore`, `PLAN.md`, `PLAN.pdf`, `README.md`, `SETUP.md`, `SETUP.pdf`, `configs/base.yaml` ...
- **Results:**
  - `results`: 1 new JSON; inspect_IoT_Network_Intrusion_Dataset.txt (new), inspect_part-00000.txt (new)
  - `results/attack_grid`: 12 new CSV; 12 new JSON; 12 new log; summary_attack.csv (new), summary_attack_labels.csv (new)
  - `results/grid`: 18 new JSON; 18 new log; summary.csv (new)
  - `results/loop`: 1 new CSV; 1 new JSON
  - `results/loop_grid`: 18 new CSV; 18 new JSON; 18 new log; summary_loop.csv (new), summary_loop_iw.csv (new), summary_loop_sweep.csv (new)
  - `results/radp`: 1 new CSV; 1 new JSON
  - `results/radp_grid`: 6 new CSV; 6 new JSON; 6 new log; summary_radp.csv (new)
  - `results/under_attack`: 1 new CSV; 1 new JSON

### 2026-11-02 13:05 (UTC+05:30) - Figures and tables rebuilt from the laptop's per-seed results

- **Code version:** 87219aa
- **Results:**
  - `results/paper`: fig_attack_asr.pdf (new), fig_attack_asr.png (new), fig_audit_tradeoff.pdf (new), fig_audit_tradeoff.png (new), fig_label_delay.pdf (new), fig_label_delay.png (new), fig_loop_poison.pdf (new), fig_loop_poison.png (new), fig_loop_time.pdf (new), fig_loop_time.png (new), fig_radp_detect.pdf (new), fig_radp_detect.png (new) and 7 more

### 2026-11-02 13:08 (UTC+05:30) - Provenance: environment, package versions, dataset SHA-256

- **Code version:** 14dc769
- **Results:**
  - `results/provenance`: data_sha256.csv (new), environment.yml (new), pip_freeze.txt (new)

### 2026-11-02 14:53 (UTC+05:30) - advtrain grid: iotid20, ciciot2023 x seeds 1, 2, 3

- **Command:** `python experiments\run_grid.py --exp advtrain --data iotid20 ciciot2023 --jobs 3 --push`
- **Runs:** 6 ok, 0 failed; 78.2 min (2026-11-02 13:35:44 to 2026-11-02 14:53:58)
- **Code version:** c46009e; this commit also changes 15 code/document file(s): `.gitignore`, `PLAN.md`, `PLAN.pdf`, `README.md`, `SETUP.md`, `SETUP.pdf`, `configs/base.yaml`, `experiments/run_grid.py` ...
- **Results:**
  - `results`: grid_runs.jsonl (new)
  - `results/advtrain_grid`: 6 new CSV; 6 new JSON; 6 new log; summary_advtrain.csv (new)

### 2026-11-02 16:40 (UTC+05:30) - Figures with the adversarial-training baseline

- **Code version:** 984122b
- **Results:**
  - `results/paper`: fig_attack_asr.pdf (changed), fig_audit_tradeoff.pdf (changed), fig_label_delay.pdf (changed), fig_loop_poison.pdf (changed), fig_loop_time.pdf (changed), fig_radp_detect.pdf (changed), fig_radp_e2e.pdf (changed), fig_advtrain.pdf (new), fig_advtrain.png (new), tab_advtrain.tex (new)

### 2026-11-03 03:11 (UTC+05:30) - loop grid [s15]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag s15 --labels true poison:0.25 poison:0.5 poison:1.0 --policies vanilla audit:0.1 guard:0.1 strict:0.1 iwstrict:0.1 iwstrict:0.2 --push`
- **Runs:** 30 ok, 0 failed; 236.9 min (2026-11-02 23:14:46 to 2026-11-03 03:11:40)
- **Code version:** 124fae0
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 30 new CSV; 30 new JSON; 30 new log; summary_loop_s15.csv (new)

### 2026-11-03 04:23 (UTC+05:30) - advtrain grid [s15]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp advtrain --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag s15 --variants none at:pgd --push`
- **Runs:** 30 ok, 0 failed; 71.8 min (2026-11-03 03:11:45 to 2026-11-03 04:23:34)
- **Code version:** 7b6d20f
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/advtrain_grid`: 30 new CSV; 30 new JSON; 30 new log; summary_advtrain_s15.csv (new)

### 2026-11-03 05:29 (UTC+05:30) - attack grid [s15]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp attack --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag s15 --attacks pgd cw --perturb attack_only --learning online frozen delay:1000 delay:5000 --push`
- **Runs:** 30 ok, 0 failed; 66.1 min (2026-11-03 04:23:39 to 2026-11-03 05:29:48)
- **Code version:** 3289d3b
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/attack_grid`: 30 new CSV; 30 new JSON; 30 new log; summary_attack_s15.csv (new)

### 2026-11-03 05:47 (UTC+05:30) - radp grid: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5

- **Command:** `python experiments\run_grid.py --exp radp --data iotid20 ciciot2023 --seeds 1 2 3 4 5 --jobs 6 --push`
- **Runs:** 4 ok, 0 failed, 6 already done; 17.2 min (2026-11-03 05:29:52 to 2026-11-03 05:47:04)
- **Code version:** 4676ae2
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/radp_grid`: 4 new CSV; 4 new JSON; 4 new log; summary_radp.csv (changed)

### 2026-11-03 14:58 (UTC+05:30) - Code v14c: CIC-IDS2017 configured, time-window fix, stream check, chain statistics

- **Code version:** 35a67db; this commit also changes 24 code/document file(s): `PLAN.md`, `PLAN.pdf`, `README.md`, `SETUP.md`, `SETUP.pdf`, `configs/base.yaml`, `experiments/adaptation_loop.py`, `experiments/adv_training.py` ...
- **Results:**
  - `results`: inspect_friday.txt (new)
  - `results/loop_grid`: 6 new log
  - `results/paper`: stats_advtrain.csv (new), stats_advtrain.tex (new), stats_attack.csv (new), stats_attack.tex (new), stats_loop.csv (new), stats_loop.tex (new), stats_radp.csv (new), stats_radp.tex (new)

### 2026-11-03 17:00 (UTC+05:30) - attack grid [s15]: cicids2017 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp attack --data cicids2017 --jobs 3 --tag s15 --push --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --attacks pgd cw --perturb attack_only --learning online frozen delay:1000 delay:5000 delaysec:60 delaysec:300`
- **Runs:** 15 ok, 0 failed; 121.1 min (2026-11-03 14:59:07 to 2026-11-03 17:00:12)
- **Code version:** bac33cf
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/attack_grid`: 15 new CSV; 15 new JSON; 15 new log; summary_attack_s15.csv (changed)
  - `results/loop_grid`: 6 changed log; 15 new CSV; 15 new JSON; 15 new log

### 2026-11-03 18:09 (UTC+05:30) - loop grid [frame]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag frame --labels true frame:0.02 frame:0.1 poison:1.0+frame:0.05 --policies vanilla strict:0.1 iwstrict:0.1 consensus:0.1 iwconsensus:0.1 --push`
- **Runs:** 30 ok, 0 failed; 243.5 min (2026-11-03 14:05:43 to 2026-11-03 18:09:14)
- **Code version:** ce8834f
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 6 changed log; 18 new CSV; 18 new JSON; 15 new log; summary_loop_frame.csv (new)

### 2026-11-03 19:14 (UTC+05:30) - cascade grid [s15]: iotid20_campaign, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp cascade --data iotid20_campaign ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag s15 --push`
- **Runs:** 30 ok, 0 failed; 64.8 min (2026-11-03 18:09:22 to 2026-11-03 19:14:08)
- **Code version:** e3b6e16
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/cascade_grid`: 30 new CSV; 30 new JSON; 30 new log; summary_cascade_s15.csv (new)
  - `results/loop_grid`: 3 changed log; 3 new CSV; 3 new JSON; 3 new log

### 2026-11-03 19:41 (UTC+05:30) - advtrain grid [adaptive]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5

- **Command:** `python experiments\run_grid.py --exp advtrain --data iotid20 ciciot2023 --seeds 1 2 3 4 5 --jobs 6 --tag adaptive --variants none at:pgd --learning frozen --adaptive distill atsur hsj --push`
- **Runs:** 10 ok, 0 failed; 27.1 min (2026-11-03 19:14:31 to 2026-11-03 19:41:34)
- **Code version:** a18e58c
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/advtrain_grid`: 10 new CSV; 10 new JSON; 10 new log; summary_advtrain_adaptive.csv (new)
  - `results/loop_grid`: 3 changed log; 3 new CSV; 3 new JSON; 3 new log

### 2026-11-03 20:28 (UTC+05:30) - loop grid [audits]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag audits --audits uncertain --labels true poison:1.0 --policies strict:0.1 iwstrict:0.1 --push`
- **Runs:** 30 ok, 0 failed; 46.9 min (2026-11-03 19:41:40 to 2026-11-03 20:28:35)
- **Code version:** 1b0f6b7
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 30 new CSV; 30 new JSON; 30 new log; summary_loop_audits.csv (new)

### 2026-11-03 21:14 (UTC+05:30) - loop grid [auditsmix]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag auditsmix --audits mixed --labels true poison:1.0 --policies strict:0.1 iwstrict:0.1 --push`
- **Runs:** 30 ok, 0 failed; 46.3 min (2026-11-03 20:28:41 to 2026-11-03 21:14:58)
- **Code version:** 2fdcd51
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 3 changed log; 33 new CSV; 33 new JSON; 33 new log; summary_loop_auditsmix.csv (new)

### 2026-11-03 21:22 (UTC+05:30) - loop grid [s15]: cicids2017 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data cicids2017 --jobs 3 --tag s15 --push --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --labels true poison:0.25 poison:0.5 poison:1.0 --policies vanilla audit:0.1 guard:0.1 strict:0.1 iwstrict:0.1 iwstrict:0.2`
- **Runs:** 15 ok, 0 failed; 261.9 min (2026-11-03 17:00:18 to 2026-11-03 21:22:15)
- **Code version:** 770c602
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 3 changed log; 3 new CSV; 3 new JSON; summary_loop_s15.csv (changed)

### 2026-11-03 22:26 (UTC+05:30) - advtrain grid [s15]: cicids2017 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp advtrain --data cicids2017 --jobs 3 --tag s15 --push --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --variants none at:pgd`
- **Runs:** 15 ok, 0 failed; 64.2 min (2026-11-03 21:22:20 to 2026-11-03 22:26:33)
- **Code version:** a730a9d
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/advtrain_grid`: 15 new CSV; 15 new JSON; 15 new log; summary_advtrain_s15.csv (changed)

### 2026-11-04 01:22 (UTC+05:30) - cascade grid [s15]: cicids2017 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp cascade --data cicids2017 --jobs 3 --tag s15 --push --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15`
- **Runs:** 15 ok, 0 failed; 175.7 min (2026-11-03 22:26:38 to 2026-11-04 01:22:20)
- **Code version:** 85280ef
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/cascade_grid`: 15 new CSV; 15 new JSON; 15 new log; summary_cascade_s15.csv (changed)
  - `results/loop_grid`: 12 new CSV; 12 new JSON; 18 new log

### 2026-11-04 01:57 (UTC+05:30) - loop grid [lowbudget]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag lowbudget --labels true poison:1.0 --policies strict:0.1 noiseaware:0.1 strict:0.05 iwstrict:0.05:5 iwstrict:0.05:10 strict:0.02 iwstrict:0.02:10 --push`
- **Runs:** 30 ok, 0 failed; 203.8 min (2026-11-03 22:33:23 to 2026-11-04 01:57:11)
- **Code version:** fbfd874
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 6 changed log; 18 new CSV; 18 new JSON; 12 new log; summary_loop_lowbudget.csv (new)

### 2026-11-04 04:47 (UTC+05:30) - 15-seed summaries, statistics and figures, three datasets

- **Code version:** f5ac9b4
- **Results:**
  - `results/paper`: fig_advtrain.pdf (changed), fig_advtrain.png (changed), fig_attack_asr.pdf (changed), fig_attack_asr.png (changed), fig_audit_tradeoff.pdf (changed), fig_audit_tradeoff.png (changed), fig_label_delay.pdf (changed), fig_label_delay.png (changed), fig_loop_poison.pdf (changed), fig_loop_poison.png (changed), fig_loop_time.pdf (changed), fig_loop_time.png (changed) and 35 more

### 2026-11-04 07:02 (UTC+05:30) - loop grid [frameunc]: iotid20, ciciot2023 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data iotid20 ciciot2023 --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --jobs 6 --tag frameunc --audits uncertain --labels true frame:0.02 frame:0.1 --policies strict:0.1 iwstrict:0.1 iwconsensus:0.1 --push`
- **Runs:** 30 ok, 0 failed; 110.5 min (2026-11-04 05:12:22 to 2026-11-04 07:02:50)
- **Code version:** fa2dd9d
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 30 new CSV; 30 new JSON; 30 new log; summary_loop_frameunc.csv (new)

### 2026-11-04 18:13 (UTC+05:30) - loop grid [frameunc]: cicids2017 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data cicids2017 --jobs 6 --push --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --tag frameunc --audits uncertain --labels true poison:1.0 frame:0.02 frame:0.1 --policies strict:0.1 iwstrict:0.1 iwconsensus:0.1`
- **Runs:** 15 ok, 0 failed; 91.2 min (2026-11-04 16:42:43 to 2026-11-04 18:13:55)
- **Code version:** 83a3bb9
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 15 new CSV; 15 new JSON; 15 new log; summary_loop_frameunc.csv (changed)

### 2026-11-05 18:02 (UTC+05:30) - loop grid [frame]: cicids2017 x seeds 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15

- **Command:** `python experiments\run_grid.py --exp loop --data cicids2017 --jobs 6 --push --seeds 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 --tag frame --labels true frame:0.02 frame:0.1 --policies vanilla strict:0.1 iwstrict:0.1 iwconsensus:0.1`
- **Runs:** 15 ok, 0 failed; 198.0 min (2026-11-05 14:44:01 to 2026-11-05 18:02:02)
- **Code version:** 816c868
- **Results:**
  - `results`: grid_runs.jsonl (changed)
  - `results/loop_grid`: 15 new CSV; 15 new JSON; 15 new log; summary_loop_frame.csv (changed)

### 2026-11-05 23:33 (UTC+05:30) - Code v14d: frameunc statistics, framing-vs-audits figure and table, F17-F22

- **Code version:** ed3e4bb; this commit also changes 7 code/document file(s): `PLAN.md`, `PLAN.pdf`, `README.md`, `SETUP.md`, `SETUP.pdf`, `scripts/make_figures.py`, `scripts/stats.py`

## Run history (rebuilt from the result files on every push)

<!-- history:start -->
| Finished | Experiment | Dataset | Seed | Tag | Rows | Minutes | Result file |
|---|---|---|---|---|---|---|---|
| 2026-10-31 01:03:06 | repro grid | iotid20_time | 1 |  | 50,000 | 9.9 | `results/grid/iotid20_time_seed1.json` |
| 2026-10-31 01:04:33 | repro grid | iotid20 | 2 |  | 50,000 | 11.4 | `results/grid/iotid20_seed2.json` |
| 2026-10-31 01:04:34 | repro grid | iotid20 | 1 |  | 50,000 | 11.4 | `results/grid/iotid20_seed1.json` |
| 2026-10-31 01:04:38 | repro grid | iotid20 | 3 |  | 50,000 | 11.4 | `results/grid/iotid20_seed3.json` |
| 2026-10-31 01:06:52 | repro grid | iotid20_time | 2 |  | 50,000 | 3.7 | `results/grid/iotid20_time_seed2.json` |
| 2026-10-31 01:08:13 | repro grid | iotid20_time | 3 |  | 50,000 | 3.6 | `results/grid/iotid20_time_seed3.json` |
| 2026-10-31 07:04:42 | attack | iotid20 | 42 |  | 3,000 | 8.1 | `results/under_attack/iotid20_seed42.json` |
| 2026-10-31 07:23:02 | repro grid | iotid20_campaign | 1 |  | 50,000 | 5.4 | `results/grid/iotid20_campaign_seed1.json` |
| 2026-10-31 07:23:02 | repro grid | iotid20_campaign | 2 |  | 50,000 | 5.4 | `results/grid/iotid20_campaign_seed2.json` |
| 2026-10-31 07:23:04 | repro grid | iotid20_campaign | 3 |  | 50,000 | 5.4 | `results/grid/iotid20_campaign_seed3.json` |
| 2026-10-31 07:28:27 | repro grid | iotid20_mirai | 1 |  | 50,000 | 5.4 | `results/grid/iotid20_mirai_seed1.json` |
| 2026-10-31 07:28:33 | repro grid | iotid20_mirai | 2 |  | 50,000 | 5.4 | `results/grid/iotid20_mirai_seed2.json` |
| 2026-10-31 07:28:34 | repro grid | iotid20_mirai | 3 |  | 50,000 | 5.4 | `results/grid/iotid20_mirai_seed3.json` |
| 2026-10-31 07:33:53 | repro grid | iotid20_all | 1 |  | 50,000 | 5.4 | `results/grid/iotid20_all_seed1.json` |
| 2026-10-31 07:33:58 | repro grid | iotid20_all | 2 |  | 50,000 | 5.4 | `results/grid/iotid20_all_seed2.json` |
| 2026-10-31 07:34:01 | repro grid | iotid20_all | 3 |  | 50,000 | 5.4 | `results/grid/iotid20_all_seed3.json` |
| 2026-10-31 09:23:41 | attack grid | iotid20 | 3 |  | 30,000 | 56.9 | `results/attack_grid/iotid20_seed3.json` |
| 2026-10-31 09:24:20 | attack grid | iotid20 | 1 |  | 30,000 | 57.5 | `results/attack_grid/iotid20_seed1.json` |
| 2026-10-31 09:24:20 | attack grid | iotid20 | 2 |  | 30,000 | 57.5 | `results/attack_grid/iotid20_seed2.json` |
| 2026-10-31 09:30:22 | repro grid | ciciot2023 | 3 |  | 50,000 | 3.3 | `results/grid/ciciot2023_seed3.json` |
| 2026-10-31 09:30:27 | repro grid | ciciot2023 | 1 |  | 50,000 | 3.3 | `results/grid/ciciot2023_seed1.json` |
| 2026-10-31 09:30:28 | repro grid | ciciot2023 | 2 |  | 50,000 | 3.4 | `results/grid/ciciot2023_seed2.json` |
| 2026-10-31 15:14:27 | RADP | iotid20 | 42 |  | 3,000 | 5.1 | `results/radp/iotid20_seed42.json` |
| 2026-10-31 15:47:01 | attack grid | ciciot2023 | 2 |  | 30,000 | 27.9 | `results/attack_grid/ciciot2023_seed2.json` |
| 2026-10-31 15:48:07 | attack grid | ciciot2023 | 1 |  | 30,000 | 29.0 | `results/attack_grid/ciciot2023_seed1.json` |
| 2026-10-31 15:49:11 | attack grid | ciciot2023 | 3 |  | 30,000 | 30.1 | `results/attack_grid/ciciot2023_seed3.json` |
| 2026-10-31 16:38:50 | attack grid | iotid20 | 3 | labels | 30,000 | 48.2 | `results/attack_grid/iotid20_seed3_labels.json` |
| 2026-10-31 16:38:55 | attack grid | iotid20 | 2 | labels | 30,000 | 48.3 | `results/attack_grid/iotid20_seed2_labels.json` |
| 2026-10-31 16:39:13 | attack grid | iotid20 | 1 | labels | 30,000 | 48.6 | `results/attack_grid/iotid20_seed1_labels.json` |
| 2026-10-31 16:49:05 | attack grid | ciciot2023 | 2 | labels | 30,000 | 10.1 | `results/attack_grid/ciciot2023_seed2_labels.json` |
| 2026-10-31 16:49:15 | attack grid | ciciot2023 | 1 | labels | 30,000 | 10.4 | `results/attack_grid/ciciot2023_seed1_labels.json` |
| 2026-10-31 16:49:54 | attack grid | ciciot2023 | 3 | labels | 30,000 | 10.7 | `results/attack_grid/ciciot2023_seed3_labels.json` |
| 2026-11-01 12:51:32 | loop | iotid20 | 42 |  | 3,000 | 2.8 | `results/loop/iotid20_seed42.json` |
| 2026-11-01 13:31:11 | loop grid | iotid20 | 3 |  | 30,000 | 39.4 | `results/loop_grid/iotid20_seed3.json` |
| 2026-11-01 13:31:35 | loop grid | iotid20 | 2 |  | 30,000 | 39.8 | `results/loop_grid/iotid20_seed2.json` |
| 2026-11-01 13:31:55 | loop grid | iotid20 | 1 |  | 30,000 | 40.1 | `results/loop_grid/iotid20_seed1.json` |
| 2026-11-01 13:46:14 | loop grid | ciciot2023 | 1 |  | 30,000 | 15.0 | `results/loop_grid/ciciot2023_seed1.json` |
| 2026-11-01 13:47:01 | loop grid | ciciot2023 | 2 |  | 30,000 | 15.4 | `results/loop_grid/ciciot2023_seed2.json` |
| 2026-11-01 13:47:39 | loop grid | ciciot2023 | 3 |  | 30,000 | 15.7 | `results/loop_grid/ciciot2023_seed3.json` |
| 2026-11-01 16:16:42 | RADP grid | iotid20 | 2 |  | 30,000 | 33.3 | `results/radp_grid/iotid20_seed2.json` |
| 2026-11-01 16:19:38 | RADP grid | iotid20 | 3 |  | 30,000 | 36.2 | `results/radp_grid/iotid20_seed3.json` |
| 2026-11-01 16:21:05 | RADP grid | iotid20 | 1 |  | 30,000 | 37.6 | `results/radp_grid/iotid20_seed1.json` |
| 2026-11-01 16:51:12 | RADP grid | ciciot2023 | 1 |  | 30,000 | 34.5 | `results/radp_grid/ciciot2023_seed1.json` |
| 2026-11-01 16:53:42 | RADP grid | ciciot2023 | 2 |  | 30,000 | 34.0 | `results/radp_grid/ciciot2023_seed2.json` |
| 2026-11-01 16:53:58 | RADP grid | ciciot2023 | 3 |  | 30,000 | 32.9 | `results/radp_grid/ciciot2023_seed3.json` |
| 2026-11-01 16:55:26 | loop grid | iotid20 | 3 | sweep | 30,000 | 71.5 | `results/loop_grid/iotid20_seed3_sweep.json` |
| 2026-11-01 16:55:37 | loop grid | iotid20 | 2 | sweep | 30,000 | 71.7 | `results/loop_grid/iotid20_seed2_sweep.json` |
| 2026-11-01 16:56:13 | loop grid | iotid20 | 1 | sweep | 30,000 | 72.3 | `results/loop_grid/iotid20_seed1_sweep.json` |
| 2026-11-01 17:13:27 | loop grid | ciciot2023 | 2 | sweep | 30,000 | 17.8 | `results/loop_grid/ciciot2023_seed2_sweep.json` |
| 2026-11-01 17:13:33 | loop grid | ciciot2023 | 1 | sweep | 30,000 | 18.1 | `results/loop_grid/ciciot2023_seed1_sweep.json` |
| 2026-11-01 17:14:41 | loop grid | ciciot2023 | 3 | sweep | 30,000 | 18.4 | `results/loop_grid/ciciot2023_seed3_sweep.json` |
| 2026-11-02 00:01:34 | loop grid | iotid20 | 2 | iw | 30,000 | 41.6 | `results/loop_grid/iotid20_seed2_iw.json` |
| 2026-11-02 00:01:35 | loop grid | iotid20 | 3 | iw | 30,000 | 41.6 | `results/loop_grid/iotid20_seed3_iw.json` |
| 2026-11-02 00:01:54 | loop grid | iotid20 | 1 | iw | 30,000 | 41.9 | `results/loop_grid/iotid20_seed1_iw.json` |
| 2026-11-02 00:14:38 | loop grid | ciciot2023 | 2 | iw | 30,000 | 13.0 | `results/loop_grid/ciciot2023_seed2_iw.json` |
| 2026-11-02 00:14:55 | loop grid | ciciot2023 | 1 | iw | 30,000 | 13.3 | `results/loop_grid/ciciot2023_seed1_iw.json` |
| 2026-11-02 00:17:18 | loop grid | ciciot2023 | 3 | iw | 30,000 | 15.4 | `results/loop_grid/ciciot2023_seed3_iw.json` |
| 2026-11-02 14:18:59 | advtrain_grid | iotid20 | 3 |  | 30,000 | 43.2 | `results/advtrain_grid/iotid20_seed3.json` |
| 2026-11-02 14:20:21 | advtrain_grid | iotid20 | 2 |  | 30,000 | 44.6 | `results/advtrain_grid/iotid20_seed2.json` |
| 2026-11-02 14:20:57 | advtrain_grid | iotid20 | 1 |  | 30,000 | 45.2 | `results/advtrain_grid/iotid20_seed1.json` |
| 2026-11-02 14:53:38 | advtrain_grid | ciciot2023 | 1 |  | 30,000 | 34.6 | `results/advtrain_grid/ciciot2023_seed1.json` |
| 2026-11-02 14:53:38 | advtrain_grid | ciciot2023 | 2 |  | 30,000 | 33.3 | `results/advtrain_grid/ciciot2023_seed2.json` |
| 2026-11-02 14:53:58 | advtrain_grid | ciciot2023 | 3 |  | 30,000 | 33.0 | `results/advtrain_grid/ciciot2023_seed3.json` |
| 2026-11-03 00:39:32 | loop grid | iotid20 | 3 | s15 | 30,000 | 84.7 | `results/loop_grid/iotid20_seed3_s15.json` |
| 2026-11-03 00:40:17 | loop grid | iotid20 | 2 | s15 | 30,000 | 85.5 | `results/loop_grid/iotid20_seed2_s15.json` |
| 2026-11-03 00:40:31 | loop grid | iotid20 | 5 | s15 | 30,000 | 85.7 | `results/loop_grid/iotid20_seed5_s15.json` |
| 2026-11-03 00:40:41 | loop grid | iotid20 | 4 | s15 | 30,000 | 85.9 | `results/loop_grid/iotid20_seed4_s15.json` |
| 2026-11-03 00:40:45 | loop grid | iotid20 | 6 | s15 | 30,000 | 85.9 | `results/loop_grid/iotid20_seed6_s15.json` |
| 2026-11-03 00:41:08 | loop grid | iotid20 | 1 | s15 | 30,000 | 86.3 | `results/loop_grid/iotid20_seed1_s15.json` |
| 2026-11-03 01:26:51 | loop grid | iotid20 | 7 | s15 | 30,000 | 47.3 | `results/loop_grid/iotid20_seed7_s15.json` |
| 2026-11-03 01:27:33 | loop grid | iotid20 | 8 | s15 | 30,000 | 47.2 | `results/loop_grid/iotid20_seed8_s15.json` |
| 2026-11-03 01:28:06 | loop grid | iotid20 | 9 | s15 | 30,000 | 47.6 | `results/loop_grid/iotid20_seed9_s15.json` |
| 2026-11-03 01:28:08 | loop grid | iotid20 | 11 | s15 | 30,000 | 47.4 | `results/loop_grid/iotid20_seed11_s15.json` |
| 2026-11-03 01:28:08 | loop grid | iotid20 | 12 | s15 | 30,000 | 47.0 | `results/loop_grid/iotid20_seed12_s15.json` |
| 2026-11-03 01:28:21 | loop grid | iotid20 | 10 | s15 | 30,000 | 47.6 | `results/loop_grid/iotid20_seed10_s15.json` |
| 2026-11-03 01:56:14 | loop grid | ciciot2023 | 1 | s15 | 30,000 | 28.1 | `results/loop_grid/ciciot2023_seed1_s15.json` |
| 2026-11-03 01:56:30 | loop grid | ciciot2023 | 2 | s15 | 30,000 | 28.3 | `results/loop_grid/ciciot2023_seed2_s15.json` |
| 2026-11-03 01:57:32 | loop grid | ciciot2023 | 3 | s15 | 30,000 | 29.2 | `results/loop_grid/ciciot2023_seed3_s15.json` |
| 2026-11-03 02:13:56 | loop grid | iotid20 | 13 | s15 | 30,000 | 47.1 | `results/loop_grid/iotid20_seed13_s15.json` |
| 2026-11-03 02:15:07 | loop grid | iotid20 | 15 | s15 | 30,000 | 47.0 | `results/loop_grid/iotid20_seed15_s15.json` |
| 2026-11-03 02:15:25 | loop grid | iotid20 | 14 | s15 | 30,000 | 47.9 | `results/loop_grid/iotid20_seed14_s15.json` |
| 2026-11-03 02:24:22 | loop grid | ciciot2023 | 4 | s15 | 30,000 | 28.1 | `results/loop_grid/ciciot2023_seed4_s15.json` |
| 2026-11-03 02:25:20 | loop grid | ciciot2023 | 5 | s15 | 30,000 | 28.8 | `results/loop_grid/ciciot2023_seed5_s15.json` |
| 2026-11-03 02:25:48 | loop grid | ciciot2023 | 6 | s15 | 30,000 | 28.2 | `results/loop_grid/ciciot2023_seed6_s15.json` |
| 2026-11-03 02:42:50 | loop grid | ciciot2023 | 7 | s15 | 30,000 | 28.9 | `results/loop_grid/ciciot2023_seed7_s15.json` |
| 2026-11-03 02:43:58 | loop grid | ciciot2023 | 8 | s15 | 30,000 | 28.8 | `results/loop_grid/ciciot2023_seed8_s15.json` |
| 2026-11-03 02:44:09 | loop grid | ciciot2023 | 9 | s15 | 30,000 | 28.7 | `results/loop_grid/ciciot2023_seed9_s15.json` |
| 2026-11-03 02:52:27 | loop grid | ciciot2023 | 10 | s15 | 30,000 | 28.1 | `results/loop_grid/ciciot2023_seed10_s15.json` |
| 2026-11-03 02:53:38 | loop grid | ciciot2023 | 11 | s15 | 30,000 | 28.3 | `results/loop_grid/ciciot2023_seed11_s15.json` |
| 2026-11-03 02:54:09 | loop grid | ciciot2023 | 12 | s15 | 30,000 | 28.3 | `results/loop_grid/ciciot2023_seed12_s15.json` |
| 2026-11-03 03:10:42 | loop grid | ciciot2023 | 13 | s15 | 30,000 | 27.8 | `results/loop_grid/ciciot2023_seed13_s15.json` |
| 2026-11-03 03:11:06 | loop grid | ciciot2023 | 14 | s15 | 30,000 | 27.1 | `results/loop_grid/ciciot2023_seed14_s15.json` |
| 2026-11-03 03:11:40 | loop grid | ciciot2023 | 15 | s15 | 30,000 | 27.5 | `results/loop_grid/ciciot2023_seed15_s15.json` |
| 2026-11-03 03:29:00 | advtrain_grid | iotid20 | 3 | s15 | 30,000 | 17.2 | `results/advtrain_grid/iotid20_seed3_s15.json` |
| 2026-11-03 03:29:08 | advtrain_grid | iotid20 | 1 | s15 | 30,000 | 17.4 | `results/advtrain_grid/iotid20_seed1_s15.json` |
| 2026-11-03 03:29:09 | advtrain_grid | iotid20 | 2 | s15 | 30,000 | 17.4 | `results/advtrain_grid/iotid20_seed2_s15.json` |
| 2026-11-03 03:29:10 | advtrain_grid | iotid20 | 4 | s15 | 30,000 | 17.4 | `results/advtrain_grid/iotid20_seed4_s15.json` |
| 2026-11-03 03:29:14 | advtrain_grid | iotid20 | 5 | s15 | 30,000 | 17.4 | `results/advtrain_grid/iotid20_seed5_s15.json` |
| 2026-11-03 03:29:38 | advtrain_grid | iotid20 | 6 | s15 | 30,000 | 17.9 | `results/advtrain_grid/iotid20_seed6_s15.json` |
| 2026-11-03 03:46:17 | advtrain_grid | iotid20 | 7 | s15 | 30,000 | 17.3 | `results/advtrain_grid/iotid20_seed7_s15.json` |
| 2026-11-03 03:46:27 | advtrain_grid | iotid20 | 12 | s15 | 30,000 | 16.8 | `results/advtrain_grid/iotid20_seed12_s15.json` |
| 2026-11-03 03:46:27 | advtrain_grid | iotid20 | 8 | s15 | 30,000 | 17.3 | `results/advtrain_grid/iotid20_seed8_s15.json` |
| 2026-11-03 03:46:44 | advtrain_grid | iotid20 | 10 | s15 | 30,000 | 17.5 | `results/advtrain_grid/iotid20_seed10_s15.json` |
| 2026-11-03 03:46:54 | advtrain_grid | iotid20 | 9 | s15 | 30,000 | 17.7 | `results/advtrain_grid/iotid20_seed9_s15.json` |
| 2026-11-03 03:46:58 | advtrain_grid | iotid20 | 11 | s15 | 30,000 | 17.7 | `results/advtrain_grid/iotid20_seed11_s15.json` |
| 2026-11-03 03:57:14 | advtrain_grid | ciciot2023 | 1 | s15 | 30,000 | 10.5 | `results/advtrain_grid/ciciot2023_seed1_s15.json` |
| 2026-11-03 03:57:15 | advtrain_grid | ciciot2023 | 2 | s15 | 30,000 | 10.3 | `results/advtrain_grid/ciciot2023_seed2_s15.json` |
| 2026-11-03 03:57:35 | advtrain_grid | ciciot2023 | 3 | s15 | 30,000 | 10.6 | `results/advtrain_grid/ciciot2023_seed3_s15.json` |
| 2026-11-03 04:03:01 | advtrain_grid | iotid20 | 13 | s15 | 30,000 | 16.7 | `results/advtrain_grid/iotid20_seed13_s15.json` |
| 2026-11-03 04:03:58 | advtrain_grid | iotid20 | 14 | s15 | 30,000 | 17.5 | `results/advtrain_grid/iotid20_seed14_s15.json` |
| 2026-11-03 04:04:04 | advtrain_grid | iotid20 | 15 | s15 | 30,000 | 17.6 | `results/advtrain_grid/iotid20_seed15_s15.json` |
| 2026-11-03 04:07:20 | advtrain_grid | ciciot2023 | 4 | s15 | 30,000 | 10.1 | `results/advtrain_grid/ciciot2023_seed4_s15.json` |
| 2026-11-03 04:07:20 | advtrain_grid | ciciot2023 | 5 | s15 | 30,000 | 10.1 | `results/advtrain_grid/ciciot2023_seed5_s15.json` |
| 2026-11-03 04:07:21 | advtrain_grid | ciciot2023 | 6 | s15 | 30,000 | 9.7 | `results/advtrain_grid/ciciot2023_seed6_s15.json` |
| 2026-11-03 04:12:47 | advtrain_grid | ciciot2023 | 7 | s15 | 30,000 | 9.7 | `results/advtrain_grid/ciciot2023_seed7_s15.json` |
| 2026-11-03 04:14:03 | advtrain_grid | ciciot2023 | 8 | s15 | 30,000 | 10.1 | `results/advtrain_grid/ciciot2023_seed8_s15.json` |
| 2026-11-03 04:14:18 | advtrain_grid | ciciot2023 | 9 | s15 | 30,000 | 10.2 | `results/advtrain_grid/ciciot2023_seed9_s15.json` |
| 2026-11-03 04:17:20 | advtrain_grid | ciciot2023 | 10 | s15 | 30,000 | 10.0 | `results/advtrain_grid/ciciot2023_seed10_s15.json` |
| 2026-11-03 04:17:23 | advtrain_grid | ciciot2023 | 11 | s15 | 30,000 | 10.0 | `results/advtrain_grid/ciciot2023_seed11_s15.json` |
| 2026-11-03 04:17:32 | advtrain_grid | ciciot2023 | 12 | s15 | 30,000 | 10.2 | `results/advtrain_grid/ciciot2023_seed12_s15.json` |
| 2026-11-03 04:22:33 | advtrain_grid | ciciot2023 | 13 | s15 | 30,000 | 9.7 | `results/advtrain_grid/ciciot2023_seed13_s15.json` |
| 2026-11-03 04:23:20 | advtrain_grid | ciciot2023 | 14 | s15 | 30,000 | 9.3 | `results/advtrain_grid/ciciot2023_seed14_s15.json` |
| 2026-11-03 04:23:34 | advtrain_grid | ciciot2023 | 15 | s15 | 30,000 | 9.2 | `results/advtrain_grid/ciciot2023_seed15_s15.json` |
| 2026-11-03 04:39:27 | attack grid | iotid20 | 5 | s15 | 30,000 | 15.8 | `results/attack_grid/iotid20_seed5_s15.json` |
| 2026-11-03 04:39:35 | attack grid | iotid20 | 3 | s15 | 30,000 | 15.9 | `results/attack_grid/iotid20_seed3_s15.json` |
| 2026-11-03 04:39:46 | attack grid | iotid20 | 4 | s15 | 30,000 | 16.1 | `results/attack_grid/iotid20_seed4_s15.json` |
| 2026-11-03 04:39:54 | attack grid | iotid20 | 2 | s15 | 30,000 | 16.2 | `results/attack_grid/iotid20_seed2_s15.json` |
| 2026-11-03 04:40:00 | attack grid | iotid20 | 1 | s15 | 30,000 | 16.3 | `results/attack_grid/iotid20_seed1_s15.json` |
| 2026-11-03 04:40:11 | attack grid | iotid20 | 6 | s15 | 30,000 | 16.5 | `results/attack_grid/iotid20_seed6_s15.json` |
| 2026-11-03 04:54:59 | attack grid | iotid20 | 7 | s15 | 30,000 | 15.5 | `results/attack_grid/iotid20_seed7_s15.json` |
| 2026-11-03 04:55:34 | attack grid | iotid20 | 12 | s15 | 30,000 | 15.4 | `results/attack_grid/iotid20_seed12_s15.json` |
| 2026-11-03 04:55:38 | attack grid | iotid20 | 9 | s15 | 30,000 | 15.8 | `results/attack_grid/iotid20_seed9_s15.json` |
| 2026-11-03 04:55:43 | attack grid | iotid20 | 8 | s15 | 30,000 | 16.1 | `results/attack_grid/iotid20_seed8_s15.json` |
| 2026-11-03 04:55:48 | attack grid | iotid20 | 11 | s15 | 30,000 | 15.8 | `results/attack_grid/iotid20_seed11_s15.json` |
| 2026-11-03 04:55:59 | attack grid | iotid20 | 10 | s15 | 30,000 | 16.1 | `results/attack_grid/iotid20_seed10_s15.json` |
| 2026-11-03 05:05:10 | attack grid | ciciot2023 | 2 | s15 | 30,000 | 9.3 | `results/attack_grid/ciciot2023_seed2_s15.json` |
| 2026-11-03 05:05:16 | attack grid | ciciot2023 | 1 | s15 | 30,000 | 9.5 | `results/attack_grid/ciciot2023_seed1_s15.json` |
| 2026-11-03 05:05:47 | attack grid | ciciot2023 | 3 | s15 | 30,000 | 9.8 | `results/attack_grid/ciciot2023_seed3_s15.json` |
| 2026-11-03 05:10:52 | attack grid | iotid20 | 13 | s15 | 30,000 | 15.9 | `results/attack_grid/iotid20_seed13_s15.json` |
| 2026-11-03 05:11:08 | attack grid | iotid20 | 15 | s15 | 30,000 | 15.5 | `results/attack_grid/iotid20_seed15_s15.json` |
| 2026-11-03 05:11:41 | attack grid | iotid20 | 14 | s15 | 30,000 | 16.1 | `results/attack_grid/iotid20_seed14_s15.json` |
| 2026-11-03 05:14:38 | attack grid | ciciot2023 | 4 | s15 | 30,000 | 9.4 | `results/attack_grid/ciciot2023_seed4_s15.json` |
| 2026-11-03 05:14:39 | attack grid | ciciot2023 | 5 | s15 | 30,000 | 9.4 | `results/attack_grid/ciciot2023_seed5_s15.json` |
| 2026-11-03 05:14:50 | attack grid | ciciot2023 | 6 | s15 | 30,000 | 9.0 | `results/attack_grid/ciciot2023_seed6_s15.json` |
| 2026-11-03 05:20:28 | attack grid | ciciot2023 | 7 | s15 | 30,000 | 9.6 | `results/attack_grid/ciciot2023_seed7_s15.json` |
| 2026-11-03 05:20:34 | attack grid | ciciot2023 | 8 | s15 | 30,000 | 9.4 | `results/attack_grid/ciciot2023_seed8_s15.json` |
| 2026-11-03 05:21:10 | attack grid | ciciot2023 | 9 | s15 | 30,000 | 9.5 | `results/attack_grid/ciciot2023_seed9_s15.json` |
| 2026-11-03 05:23:48 | attack grid | ciciot2023 | 10 | s15 | 30,000 | 9.1 | `results/attack_grid/ciciot2023_seed10_s15.json` |
| 2026-11-03 05:24:02 | attack grid | ciciot2023 | 12 | s15 | 30,000 | 9.2 | `results/attack_grid/ciciot2023_seed12_s15.json` |
| 2026-11-03 05:24:03 | attack grid | ciciot2023 | 11 | s15 | 30,000 | 9.4 | `results/attack_grid/ciciot2023_seed11_s15.json` |
| 2026-11-03 05:29:22 | attack grid | ciciot2023 | 14 | s15 | 30,000 | 8.8 | `results/attack_grid/ciciot2023_seed14_s15.json` |
| 2026-11-03 05:29:41 | attack grid | ciciot2023 | 13 | s15 | 30,000 | 9.2 | `results/attack_grid/ciciot2023_seed13_s15.json` |
| 2026-11-03 05:29:48 | attack grid | ciciot2023 | 15 | s15 | 30,000 | 8.6 | `results/attack_grid/ciciot2023_seed15_s15.json` |
| 2026-11-03 05:38:16 | RADP grid | ciciot2023 | 5 |  | 30,000 | 8.4 | `results/radp_grid/ciciot2023_seed5.json` |
| 2026-11-03 05:38:23 | RADP grid | ciciot2023 | 4 |  | 30,000 | 8.5 | `results/radp_grid/ciciot2023_seed4.json` |
| 2026-11-03 05:46:08 | RADP grid | iotid20 | 4 |  | 30,000 | 16.2 | `results/radp_grid/iotid20_seed4.json` |
| 2026-11-03 05:47:04 | RADP grid | iotid20 | 5 |  | 30,000 | 17.2 | `results/radp_grid/iotid20_seed5.json` |
| 2026-11-03 15:23:11 | attack grid | cicids2017 | 2 | s15 | 30,000 | 24.0 | `results/attack_grid/cicids2017_seed2_s15.json` |
| 2026-11-03 15:23:18 | attack grid | cicids2017 | 1 | s15 | 30,000 | 24.2 | `results/attack_grid/cicids2017_seed1_s15.json` |
| 2026-11-03 15:23:23 | attack grid | cicids2017 | 3 | s15 | 30,000 | 24.2 | `results/attack_grid/cicids2017_seed3_s15.json` |
| 2026-11-03 15:30:16 | loop grid | iotid20 | 2 | frame | 30,000 | 84.5 | `results/loop_grid/iotid20_seed2_frame.json` |
| 2026-11-03 15:30:36 | loop grid | iotid20 | 3 | frame | 30,000 | 84.9 | `results/loop_grid/iotid20_seed3_frame.json` |
| 2026-11-03 15:30:41 | loop grid | iotid20 | 5 | frame | 30,000 | 84.9 | `results/loop_grid/iotid20_seed5_frame.json` |
| 2026-11-03 15:30:44 | loop grid | iotid20 | 6 | frame | 30,000 | 85.0 | `results/loop_grid/iotid20_seed6_frame.json` |
| 2026-11-03 15:31:13 | loop grid | iotid20 | 4 | frame | 30,000 | 85.5 | `results/loop_grid/iotid20_seed4_frame.json` |
| 2026-11-03 15:31:57 | loop grid | iotid20 | 1 | frame | 30,000 | 86.2 | `results/loop_grid/iotid20_seed1_frame.json` |
| 2026-11-03 15:47:00 | attack grid | cicids2017 | 4 | s15 | 30,000 | 23.8 | `results/attack_grid/cicids2017_seed4_s15.json` |
| 2026-11-03 15:47:23 | attack grid | cicids2017 | 6 | s15 | 30,000 | 24.0 | `results/attack_grid/cicids2017_seed6_s15.json` |
| 2026-11-03 15:47:25 | attack grid | cicids2017 | 5 | s15 | 30,000 | 24.1 | `results/attack_grid/cicids2017_seed5_s15.json` |
| 2026-11-03 16:10:53 | attack grid | cicids2017 | 7 | s15 | 30,000 | 23.8 | `results/attack_grid/cicids2017_seed7_s15.json` |
| 2026-11-03 16:11:23 | attack grid | cicids2017 | 8 | s15 | 30,000 | 24.0 | `results/attack_grid/cicids2017_seed8_s15.json` |
| 2026-11-03 16:11:36 | attack grid | cicids2017 | 9 | s15 | 30,000 | 24.2 | `results/attack_grid/cicids2017_seed9_s15.json` |
| 2026-11-03 16:21:40 | loop grid | iotid20 | 7 | frame | 30,000 | 51.4 | `results/loop_grid/iotid20_seed7_frame.json` |
| 2026-11-03 16:21:54 | loop grid | iotid20 | 8 | frame | 30,000 | 51.3 | `results/loop_grid/iotid20_seed8_frame.json` |
| 2026-11-03 16:22:10 | loop grid | iotid20 | 9 | frame | 30,000 | 51.5 | `results/loop_grid/iotid20_seed9_frame.json` |
| 2026-11-03 16:22:28 | loop grid | iotid20 | 11 | frame | 30,000 | 51.2 | `results/loop_grid/iotid20_seed11_frame.json` |
| 2026-11-03 16:22:32 | loop grid | iotid20 | 10 | frame | 30,000 | 51.8 | `results/loop_grid/iotid20_seed10_frame.json` |
| 2026-11-03 16:23:11 | loop grid | iotid20 | 12 | frame | 30,000 | 51.2 | `results/loop_grid/iotid20_seed12_frame.json` |
| 2026-11-03 16:35:06 | attack grid | cicids2017 | 10 | s15 | 30,000 | 24.2 | `results/attack_grid/cicids2017_seed10_s15.json` |
| 2026-11-03 16:35:49 | attack grid | cicids2017 | 11 | s15 | 30,000 | 24.4 | `results/attack_grid/cicids2017_seed11_s15.json` |
| 2026-11-03 16:35:54 | attack grid | cicids2017 | 12 | s15 | 30,000 | 24.3 | `results/attack_grid/cicids2017_seed12_s15.json` |
| 2026-11-03 16:53:10 | loop grid | ciciot2023 | 2 | frame | 30,000 | 30.6 | `results/loop_grid/ciciot2023_seed2_frame.json` |
| 2026-11-03 16:53:27 | loop grid | ciciot2023 | 1 | frame | 30,000 | 30.9 | `results/loop_grid/ciciot2023_seed1_frame.json` |
| 2026-11-03 16:54:46 | loop grid | ciciot2023 | 3 | frame | 30,000 | 31.6 | `results/loop_grid/ciciot2023_seed3_frame.json` |
| 2026-11-03 16:59:09 | attack grid | cicids2017 | 13 | s15 | 30,000 | 24.0 | `results/attack_grid/cicids2017_seed13_s15.json` |
| 2026-11-03 17:00:10 | attack grid | cicids2017 | 14 | s15 | 30,000 | 24.3 | `results/attack_grid/cicids2017_seed14_s15.json` |
| 2026-11-03 17:00:12 | attack grid | cicids2017 | 15 | s15 | 30,000 | 24.3 | `results/attack_grid/cicids2017_seed15_s15.json` |
| 2026-11-03 17:12:18 | loop grid | iotid20 | 15 | frame | 30,000 | 50.1 | `results/loop_grid/iotid20_seed15_frame.json` |
| 2026-11-03 17:12:35 | loop grid | iotid20 | 13 | frame | 30,000 | 50.9 | `results/loop_grid/iotid20_seed13_frame.json` |
| 2026-11-03 17:13:16 | loop grid | iotid20 | 14 | frame | 30,000 | 51.3 | `results/loop_grid/iotid20_seed14_frame.json` |
| 2026-11-03 17:23:09 | loop grid | ciciot2023 | 4 | frame | 30,000 | 29.9 | `results/loop_grid/ciciot2023_seed4_frame.json` |
| 2026-11-03 17:23:10 | loop grid | ciciot2023 | 5 | frame | 30,000 | 29.7 | `results/loop_grid/ciciot2023_seed5_frame.json` |
| 2026-11-03 17:24:47 | loop grid | ciciot2023 | 6 | frame | 30,000 | 30.0 | `results/loop_grid/ciciot2023_seed6_frame.json` |
| 2026-11-03 17:42:41 | loop grid | ciciot2023 | 8 | frame | 30,000 | 30.1 | `results/loop_grid/ciciot2023_seed8_frame.json` |
| 2026-11-03 17:42:44 | loop grid | ciciot2023 | 7 | frame | 30,000 | 30.4 | `results/loop_grid/ciciot2023_seed7_frame.json` |
| 2026-11-03 17:43:07 | loop grid | ciciot2023 | 9 | frame | 30,000 | 29.8 | `results/loop_grid/ciciot2023_seed9_frame.json` |
| 2026-11-03 17:52:24 | loop grid | cicids2017 | 2 | s15 | 30,000 | 52.1 | `results/loop_grid/cicids2017_seed2_s15.json` |
| 2026-11-03 17:52:55 | loop grid | ciciot2023 | 10 | frame | 30,000 | 29.8 | `results/loop_grid/ciciot2023_seed10_frame.json` |
| 2026-11-03 17:53:06 | loop grid | ciciot2023 | 11 | frame | 30,000 | 29.9 | `results/loop_grid/ciciot2023_seed11_frame.json` |
| 2026-11-03 17:53:39 | loop grid | cicids2017 | 1 | s15 | 30,000 | 53.3 | `results/loop_grid/cicids2017_seed1_s15.json` |
| 2026-11-03 17:53:48 | loop grid | cicids2017 | 3 | s15 | 30,000 | 53.5 | `results/loop_grid/cicids2017_seed3_s15.json` |
| 2026-11-03 17:54:14 | loop grid | ciciot2023 | 12 | frame | 30,000 | 29.4 | `results/loop_grid/ciciot2023_seed12_frame.json` |
| 2026-11-03 18:09:02 | loop grid | ciciot2023 | 13 | frame | 30,000 | 26.3 | `results/loop_grid/ciciot2023_seed13_frame.json` |
| 2026-11-03 18:09:12 | loop grid | ciciot2023 | 15 | frame | 30,000 | 26.0 | `results/loop_grid/ciciot2023_seed15_frame.json` |
| 2026-11-03 18:09:13 | loop grid | ciciot2023 | 14 | frame | 30,000 | 26.5 | `results/loop_grid/ciciot2023_seed14_frame.json` |
| 2026-11-03 18:24:38 | cascade_grid | iotid20_campaign | 2 | s15 | 30,000 | 15.2 | `results/cascade_grid/iotid20_campaign_seed2_s15.json` |
| 2026-11-03 18:24:53 | cascade_grid | iotid20_campaign | 1 | s15 | 30,000 | 15.4 | `results/cascade_grid/iotid20_campaign_seed1_s15.json` |
| 2026-11-03 18:25:01 | cascade_grid | iotid20_campaign | 5 | s15 | 30,000 | 15.6 | `results/cascade_grid/iotid20_campaign_seed5_s15.json` |
| 2026-11-03 18:25:15 | cascade_grid | iotid20_campaign | 4 | s15 | 30,000 | 15.8 | `results/cascade_grid/iotid20_campaign_seed4_s15.json` |
| 2026-11-03 18:25:23 | cascade_grid | iotid20_campaign | 3 | s15 | 30,000 | 15.9 | `results/cascade_grid/iotid20_campaign_seed3_s15.json` |
| 2026-11-03 18:25:25 | cascade_grid | iotid20_campaign | 6 | s15 | 30,000 | 15.9 | `results/cascade_grid/iotid20_campaign_seed6_s15.json` |
| 2026-11-03 18:40:07 | cascade_grid | iotid20_campaign | 8 | s15 | 30,000 | 15.2 | `results/cascade_grid/iotid20_campaign_seed8_s15.json` |
| 2026-11-03 18:40:33 | cascade_grid | iotid20_campaign | 10 | s15 | 30,000 | 15.2 | `results/cascade_grid/iotid20_campaign_seed10_s15.json` |
| 2026-11-03 18:40:33 | cascade_grid | iotid20_campaign | 7 | s15 | 30,000 | 15.8 | `results/cascade_grid/iotid20_campaign_seed7_s15.json` |
| 2026-11-03 18:40:47 | cascade_grid | iotid20_campaign | 11 | s15 | 30,000 | 15.3 | `results/cascade_grid/iotid20_campaign_seed11_s15.json` |
| 2026-11-03 18:40:55 | cascade_grid | iotid20_campaign | 9 | s15 | 30,000 | 15.8 | `results/cascade_grid/iotid20_campaign_seed9_s15.json` |
| 2026-11-03 18:41:16 | cascade_grid | iotid20_campaign | 12 | s15 | 30,000 | 15.8 | `results/cascade_grid/iotid20_campaign_seed12_s15.json` |
| 2026-11-03 18:44:10 | loop grid | cicids2017 | 4 | s15 | 30,000 | 51.7 | `results/loop_grid/cicids2017_seed4_s15.json` |
| 2026-11-03 18:45:41 | loop grid | cicids2017 | 5 | s15 | 30,000 | 52.0 | `results/loop_grid/cicids2017_seed5_s15.json` |
| 2026-11-03 18:46:04 | loop grid | cicids2017 | 6 | s15 | 30,000 | 52.2 | `results/loop_grid/cicids2017_seed6_s15.json` |
| 2026-11-03 18:50:45 | cascade_grid | ciciot2023 | 2 | s15 | 30,000 | 9.8 | `results/cascade_grid/ciciot2023_seed2_s15.json` |
| 2026-11-03 18:50:47 | cascade_grid | ciciot2023 | 1 | s15 | 30,000 | 9.9 | `results/cascade_grid/ciciot2023_seed1_s15.json` |
| 2026-11-03 18:51:32 | cascade_grid | ciciot2023 | 3 | s15 | 30,000 | 10.2 | `results/cascade_grid/ciciot2023_seed3_s15.json` |
| 2026-11-03 18:55:28 | cascade_grid | iotid20_campaign | 13 | s15 | 30,000 | 15.3 | `results/cascade_grid/iotid20_campaign_seed13_s15.json` |
| 2026-11-03 18:55:54 | cascade_grid | iotid20_campaign | 14 | s15 | 30,000 | 15.3 | `results/cascade_grid/iotid20_campaign_seed14_s15.json` |
| 2026-11-03 18:56:18 | cascade_grid | iotid20_campaign | 15 | s15 | 30,000 | 15.7 | `results/cascade_grid/iotid20_campaign_seed15_s15.json` |
| 2026-11-03 19:00:14 | cascade_grid | ciciot2023 | 4 | s15 | 30,000 | 9.4 | `results/cascade_grid/ciciot2023_seed4_s15.json` |
| 2026-11-03 19:00:33 | cascade_grid | ciciot2023 | 5 | s15 | 30,000 | 9.7 | `results/cascade_grid/ciciot2023_seed5_s15.json` |
| 2026-11-03 19:01:06 | cascade_grid | ciciot2023 | 6 | s15 | 30,000 | 9.5 | `results/cascade_grid/ciciot2023_seed6_s15.json` |
| 2026-11-03 19:05:24 | cascade_grid | ciciot2023 | 7 | s15 | 30,000 | 9.9 | `results/cascade_grid/ciciot2023_seed7_s15.json` |
| 2026-11-03 19:05:37 | cascade_grid | ciciot2023 | 8 | s15 | 30,000 | 9.6 | `results/cascade_grid/ciciot2023_seed8_s15.json` |
| 2026-11-03 19:05:48 | cascade_grid | ciciot2023 | 9 | s15 | 30,000 | 9.4 | `results/cascade_grid/ciciot2023_seed9_s15.json` |
| 2026-11-03 19:09:42 | cascade_grid | ciciot2023 | 10 | s15 | 30,000 | 9.4 | `results/cascade_grid/ciciot2023_seed10_s15.json` |
| 2026-11-03 19:10:02 | cascade_grid | ciciot2023 | 11 | s15 | 30,000 | 9.4 | `results/cascade_grid/ciciot2023_seed11_s15.json` |
| 2026-11-03 19:10:27 | cascade_grid | ciciot2023 | 12 | s15 | 30,000 | 9.3 | `results/cascade_grid/ciciot2023_seed12_s15.json` |
| 2026-11-03 19:13:56 | cascade_grid | ciciot2023 | 14 | s15 | 30,000 | 8.2 | `results/cascade_grid/ciciot2023_seed14_s15.json` |
| 2026-11-03 19:13:59 | cascade_grid | ciciot2023 | 13 | s15 | 30,000 | 8.5 | `results/cascade_grid/ciciot2023_seed13_s15.json` |
| 2026-11-03 19:14:07 | cascade_grid | ciciot2023 | 15 | s15 | 30,000 | 8.2 | `results/cascade_grid/ciciot2023_seed15_s15.json` |
| 2026-11-03 19:25:27 | advtrain_grid | ciciot2023 | 1 | adaptive | 30,000 | 10.9 | `results/advtrain_grid/ciciot2023_seed1_adaptive.json` |
| 2026-11-03 19:32:56 | advtrain_grid | iotid20 | 2 | adaptive | 30,000 | 18.4 | `results/advtrain_grid/iotid20_seed2_adaptive.json` |
| 2026-11-03 19:33:01 | advtrain_grid | iotid20 | 3 | adaptive | 30,000 | 18.5 | `results/advtrain_grid/iotid20_seed3_adaptive.json` |
| 2026-11-03 19:33:27 | advtrain_grid | iotid20 | 1 | adaptive | 30,000 | 18.9 | `results/advtrain_grid/iotid20_seed1_adaptive.json` |
| 2026-11-03 19:33:31 | advtrain_grid | iotid20 | 4 | adaptive | 30,000 | 19.0 | `results/advtrain_grid/iotid20_seed4_adaptive.json` |
| 2026-11-03 19:33:38 | advtrain_grid | iotid20 | 5 | adaptive | 30,000 | 19.1 | `results/advtrain_grid/iotid20_seed5_adaptive.json` |
| 2026-11-03 19:35:15 | advtrain_grid | ciciot2023 | 2 | adaptive | 30,000 | 9.8 | `results/advtrain_grid/ciciot2023_seed2_adaptive.json` |
| 2026-11-03 19:37:47 | loop grid | cicids2017 | 8 | s15 | 30,000 | 52.1 | `results/loop_grid/cicids2017_seed8_s15.json` |
| 2026-11-03 19:38:02 | loop grid | cicids2017 | 7 | s15 | 30,000 | 53.8 | `results/loop_grid/cicids2017_seed7_s15.json` |
| 2026-11-03 19:39:15 | loop grid | cicids2017 | 9 | s15 | 30,000 | 53.1 | `results/loop_grid/cicids2017_seed9_s15.json` |
| 2026-11-03 19:41:31 | advtrain_grid | ciciot2023 | 3 | adaptive | 30,000 | 8.6 | `results/advtrain_grid/ciciot2023_seed3_adaptive.json` |
| 2026-11-03 19:41:31 | advtrain_grid | ciciot2023 | 4 | adaptive | 30,000 | 8.5 | `results/advtrain_grid/ciciot2023_seed4_adaptive.json` |
| 2026-11-03 19:41:34 | advtrain_grid | ciciot2023 | 5 | adaptive | 30,000 | 8.1 | `results/advtrain_grid/ciciot2023_seed5_adaptive.json` |
| 2026-11-03 19:52:46 | loop grid | iotid20 | 3 | audits | 30,000 | 11.1 | `results/loop_grid/iotid20_seed3_audits.json` |
| 2026-11-03 19:52:59 | loop grid | iotid20 | 2 | audits | 30,000 | 11.3 | `results/loop_grid/iotid20_seed2_audits.json` |
| 2026-11-03 19:53:03 | loop grid | iotid20 | 6 | audits | 30,000 | 11.4 | `results/loop_grid/iotid20_seed6_audits.json` |
| 2026-11-03 19:53:08 | loop grid | iotid20 | 1 | audits | 30,000 | 11.4 | `results/loop_grid/iotid20_seed1_audits.json` |
| 2026-11-03 19:53:10 | loop grid | iotid20 | 5 | audits | 30,000 | 11.5 | `results/loop_grid/iotid20_seed5_audits.json` |
| 2026-11-03 19:53:11 | loop grid | iotid20 | 4 | audits | 30,000 | 11.5 | `results/loop_grid/iotid20_seed4_audits.json` |
| 2026-11-03 20:04:07 | loop grid | iotid20 | 7 | audits | 30,000 | 11.3 | `results/loop_grid/iotid20_seed7_audits.json` |
| 2026-11-03 20:04:26 | loop grid | iotid20 | 12 | audits | 30,000 | 11.2 | `results/loop_grid/iotid20_seed12_audits.json` |
| 2026-11-03 20:04:26 | loop grid | iotid20 | 9 | audits | 30,000 | 11.4 | `results/loop_grid/iotid20_seed9_audits.json` |
| 2026-11-03 20:04:29 | loop grid | iotid20 | 11 | audits | 30,000 | 11.3 | `results/loop_grid/iotid20_seed11_audits.json` |
| 2026-11-03 20:04:32 | loop grid | iotid20 | 8 | audits | 30,000 | 11.5 | `results/loop_grid/iotid20_seed8_audits.json` |
| 2026-11-03 20:04:34 | loop grid | iotid20 | 10 | audits | 30,000 | 11.4 | `results/loop_grid/iotid20_seed10_audits.json` |
| 2026-11-03 20:11:13 | loop grid | ciciot2023 | 2 | audits | 30,000 | 6.6 | `results/loop_grid/ciciot2023_seed2_audits.json` |
| 2026-11-03 20:11:19 | loop grid | ciciot2023 | 1 | audits | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed1_audits.json` |
| 2026-11-03 20:11:37 | loop grid | ciciot2023 | 3 | audits | 30,000 | 7.0 | `results/loop_grid/ciciot2023_seed3_audits.json` |
| 2026-11-03 20:15:03 | loop grid | iotid20 | 13 | audits | 30,000 | 10.9 | `results/loop_grid/iotid20_seed13_audits.json` |
| 2026-11-03 20:15:35 | loop grid | iotid20 | 14 | audits | 30,000 | 11.1 | `results/loop_grid/iotid20_seed14_audits.json` |
| 2026-11-03 20:15:41 | loop grid | iotid20 | 15 | audits | 30,000 | 11.2 | `results/loop_grid/iotid20_seed15_audits.json` |
| 2026-11-03 20:17:59 | loop grid | ciciot2023 | 4 | audits | 30,000 | 6.7 | `results/loop_grid/ciciot2023_seed4_audits.json` |
| 2026-11-03 20:18:10 | loop grid | ciciot2023 | 5 | audits | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed5_audits.json` |
| 2026-11-03 20:18:24 | loop grid | ciciot2023 | 6 | audits | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed6_audits.json` |
| 2026-11-03 20:22:01 | loop grid | ciciot2023 | 7 | audits | 30,000 | 6.9 | `results/loop_grid/ciciot2023_seed7_audits.json` |
| 2026-11-03 20:22:28 | loop grid | ciciot2023 | 8 | audits | 30,000 | 6.9 | `results/loop_grid/ciciot2023_seed8_audits.json` |
| 2026-11-03 20:22:38 | loop grid | ciciot2023 | 9 | audits | 30,000 | 6.9 | `results/loop_grid/ciciot2023_seed9_audits.json` |
| 2026-11-03 20:24:37 | loop grid | ciciot2023 | 10 | audits | 30,000 | 6.6 | `results/loop_grid/ciciot2023_seed10_audits.json` |
| 2026-11-03 20:24:52 | loop grid | ciciot2023 | 11 | audits | 30,000 | 6.7 | `results/loop_grid/ciciot2023_seed11_audits.json` |
| 2026-11-03 20:25:02 | loop grid | ciciot2023 | 12 | audits | 30,000 | 6.6 | `results/loop_grid/ciciot2023_seed12_audits.json` |
| 2026-11-03 20:28:08 | loop grid | ciciot2023 | 13 | audits | 30,000 | 6.1 | `results/loop_grid/ciciot2023_seed13_audits.json` |
| 2026-11-03 20:28:20 | loop grid | ciciot2023 | 14 | audits | 30,000 | 5.8 | `results/loop_grid/ciciot2023_seed14_audits.json` |
| 2026-11-03 20:28:35 | loop grid | ciciot2023 | 15 | audits | 30,000 | 5.9 | `results/loop_grid/ciciot2023_seed15_audits.json` |
| 2026-11-03 20:29:47 | loop grid | cicids2017 | 10 | s15 | 30,000 | 52.0 | `results/loop_grid/cicids2017_seed10_s15.json` |
| 2026-11-03 20:30:28 | loop grid | cicids2017 | 12 | s15 | 30,000 | 51.2 | `results/loop_grid/cicids2017_seed12_s15.json` |
| 2026-11-03 20:31:00 | loop grid | cicids2017 | 11 | s15 | 30,000 | 52.9 | `results/loop_grid/cicids2017_seed11_s15.json` |
| 2026-11-03 20:39:44 | loop grid | iotid20 | 2 | auditsmix | 30,000 | 11.0 | `results/loop_grid/iotid20_seed2_auditsmix.json` |
| 2026-11-03 20:39:47 | loop grid | iotid20 | 3 | auditsmix | 30,000 | 11.1 | `results/loop_grid/iotid20_seed3_auditsmix.json` |
| 2026-11-03 20:39:52 | loop grid | iotid20 | 1 | auditsmix | 30,000 | 11.2 | `results/loop_grid/iotid20_seed1_auditsmix.json` |
| 2026-11-03 20:39:52 | loop grid | iotid20 | 5 | auditsmix | 30,000 | 11.2 | `results/loop_grid/iotid20_seed5_auditsmix.json` |
| 2026-11-03 20:40:01 | loop grid | iotid20 | 6 | auditsmix | 30,000 | 11.3 | `results/loop_grid/iotid20_seed6_auditsmix.json` |
| 2026-11-03 20:40:08 | loop grid | iotid20 | 4 | auditsmix | 30,000 | 11.4 | `results/loop_grid/iotid20_seed4_auditsmix.json` |
| 2026-11-03 20:50:42 | loop grid | iotid20 | 7 | auditsmix | 30,000 | 10.9 | `results/loop_grid/iotid20_seed7_auditsmix.json` |
| 2026-11-03 20:50:52 | loop grid | iotid20 | 9 | auditsmix | 30,000 | 11.0 | `results/loop_grid/iotid20_seed9_auditsmix.json` |
| 2026-11-03 20:50:58 | loop grid | iotid20 | 12 | auditsmix | 30,000 | 10.8 | `results/loop_grid/iotid20_seed12_auditsmix.json` |
| 2026-11-03 20:50:59 | loop grid | iotid20 | 11 | auditsmix | 30,000 | 10.9 | `results/loop_grid/iotid20_seed11_auditsmix.json` |
| 2026-11-03 20:51:00 | loop grid | iotid20 | 10 | auditsmix | 30,000 | 11.1 | `results/loop_grid/iotid20_seed10_auditsmix.json` |
| 2026-11-03 20:51:03 | loop grid | iotid20 | 8 | auditsmix | 30,000 | 11.2 | `results/loop_grid/iotid20_seed8_auditsmix.json` |
| 2026-11-03 20:57:45 | loop grid | ciciot2023 | 1 | auditsmix | 30,000 | 6.7 | `results/loop_grid/ciciot2023_seed1_auditsmix.json` |
| 2026-11-03 20:57:50 | loop grid | ciciot2023 | 2 | auditsmix | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed2_auditsmix.json` |
| 2026-11-03 20:58:06 | loop grid | ciciot2023 | 3 | auditsmix | 30,000 | 7.0 | `results/loop_grid/ciciot2023_seed3_auditsmix.json` |
| 2026-11-03 21:01:47 | loop grid | iotid20 | 13 | auditsmix | 30,000 | 11.1 | `results/loop_grid/iotid20_seed13_auditsmix.json` |
| 2026-11-03 21:02:05 | loop grid | iotid20 | 15 | auditsmix | 30,000 | 11.1 | `results/loop_grid/iotid20_seed15_auditsmix.json` |
| 2026-11-03 21:02:21 | loop grid | iotid20 | 14 | auditsmix | 30,000 | 11.5 | `results/loop_grid/iotid20_seed14_auditsmix.json` |
| 2026-11-03 21:04:35 | loop grid | ciciot2023 | 4 | auditsmix | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed4_auditsmix.json` |
| 2026-11-03 21:04:39 | loop grid | ciciot2023 | 5 | auditsmix | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed5_auditsmix.json` |
| 2026-11-03 21:04:55 | loop grid | ciciot2023 | 6 | auditsmix | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed6_auditsmix.json` |
| 2026-11-03 21:08:44 | loop grid | ciciot2023 | 7 | auditsmix | 30,000 | 6.9 | `results/loop_grid/ciciot2023_seed7_auditsmix.json` |
| 2026-11-03 21:08:49 | loop grid | ciciot2023 | 8 | auditsmix | 30,000 | 6.7 | `results/loop_grid/ciciot2023_seed8_auditsmix.json` |
| 2026-11-03 21:09:09 | loop grid | ciciot2023 | 9 | auditsmix | 30,000 | 6.8 | `results/loop_grid/ciciot2023_seed9_auditsmix.json` |
| 2026-11-03 21:11:12 | loop grid | ciciot2023 | 10 | auditsmix | 30,000 | 6.6 | `results/loop_grid/ciciot2023_seed10_auditsmix.json` |
| 2026-11-03 21:11:15 | loop grid | ciciot2023 | 11 | auditsmix | 30,000 | 6.6 | `results/loop_grid/ciciot2023_seed11_auditsmix.json` |
| 2026-11-03 21:11:34 | loop grid | ciciot2023 | 12 | auditsmix | 30,000 | 6.6 | `results/loop_grid/ciciot2023_seed12_auditsmix.json` |
| 2026-11-03 21:14:41 | loop grid | ciciot2023 | 14 | auditsmix | 30,000 | 5.8 | `results/loop_grid/ciciot2023_seed14_auditsmix.json` |
| 2026-11-03 21:14:45 | loop grid | ciciot2023 | 13 | auditsmix | 30,000 | 6.0 | `results/loop_grid/ciciot2023_seed13_auditsmix.json` |
| 2026-11-03 21:14:58 | loop grid | ciciot2023 | 15 | auditsmix | 30,000 | 5.8 | `results/loop_grid/ciciot2023_seed15_auditsmix.json` |
| 2026-11-03 21:20:27 | loop grid | cicids2017 | 13 | s15 | 30,000 | 50.6 | `results/loop_grid/cicids2017_seed13_s15.json` |
| 2026-11-03 21:21:38 | loop grid | cicids2017 | 14 | s15 | 30,000 | 51.1 | `results/loop_grid/cicids2017_seed14_s15.json` |
| 2026-11-03 21:22:15 | loop grid | cicids2017 | 15 | s15 | 30,000 | 51.2 | `results/loop_grid/cicids2017_seed15_s15.json` |
| 2026-11-03 21:35:08 | advtrain_grid | cicids2017 | 1 | s15 | 30,000 | 12.8 | `results/advtrain_grid/cicids2017_seed1_s15.json` |
| 2026-11-03 21:35:11 | advtrain_grid | cicids2017 | 2 | s15 | 30,000 | 12.8 | `results/advtrain_grid/cicids2017_seed2_s15.json` |
| 2026-11-03 21:35:16 | advtrain_grid | cicids2017 | 3 | s15 | 30,000 | 12.9 | `results/advtrain_grid/cicids2017_seed3_s15.json` |
| 2026-11-03 21:47:46 | advtrain_grid | cicids2017 | 4 | s15 | 30,000 | 12.6 | `results/advtrain_grid/cicids2017_seed4_s15.json` |
| 2026-11-03 21:47:59 | advtrain_grid | cicids2017 | 5 | s15 | 30,000 | 12.8 | `results/advtrain_grid/cicids2017_seed5_s15.json` |
| 2026-11-03 21:48:05 | advtrain_grid | cicids2017 | 6 | s15 | 30,000 | 12.8 | `results/advtrain_grid/cicids2017_seed6_s15.json` |
| 2026-11-03 22:00:40 | advtrain_grid | cicids2017 | 7 | s15 | 30,000 | 12.9 | `results/advtrain_grid/cicids2017_seed7_s15.json` |
| 2026-11-03 22:00:42 | advtrain_grid | cicids2017 | 8 | s15 | 30,000 | 12.7 | `results/advtrain_grid/cicids2017_seed8_s15.json` |
| 2026-11-03 22:00:49 | advtrain_grid | cicids2017 | 9 | s15 | 30,000 | 12.7 | `results/advtrain_grid/cicids2017_seed9_s15.json` |
| 2026-11-03 22:13:24 | advtrain_grid | cicids2017 | 10 | s15 | 30,000 | 12.7 | `results/advtrain_grid/cicids2017_seed10_s15.json` |
| 2026-11-03 22:13:35 | advtrain_grid | cicids2017 | 12 | s15 | 30,000 | 12.7 | `results/advtrain_grid/cicids2017_seed12_s15.json` |
| 2026-11-03 22:13:36 | advtrain_grid | cicids2017 | 11 | s15 | 30,000 | 12.9 | `results/advtrain_grid/cicids2017_seed11_s15.json` |
| 2026-11-03 22:26:09 | advtrain_grid | cicids2017 | 13 | s15 | 30,000 | 12.7 | `results/advtrain_grid/cicids2017_seed13_s15.json` |
| 2026-11-03 22:26:27 | advtrain_grid | cicids2017 | 15 | s15 | 30,000 | 12.8 | `results/advtrain_grid/cicids2017_seed15_s15.json` |
| 2026-11-03 22:26:32 | advtrain_grid | cicids2017 | 14 | s15 | 30,000 | 12.9 | `results/advtrain_grid/cicids2017_seed14_s15.json` |
| 2026-11-03 22:49:44 | cascade_grid | cicids2017 | 1 | s15 | 30,000 | 23.0 | `results/cascade_grid/cicids2017_seed1_s15.json` |
| 2026-11-03 22:49:44 | cascade_grid | cicids2017 | 2 | s15 | 30,000 | 23.0 | `results/cascade_grid/cicids2017_seed2_s15.json` |
| 2026-11-03 22:50:34 | cascade_grid | cicids2017 | 3 | s15 | 30,000 | 23.9 | `results/cascade_grid/cicids2017_seed3_s15.json` |
| 2026-11-03 23:43:08 | cascade_grid | cicids2017 | 4 | s15 | 30,000 | 53.2 | `results/cascade_grid/cicids2017_seed4_s15.json` |
| 2026-11-03 23:44:57 | cascade_grid | cicids2017 | 5 | s15 | 30,000 | 55.0 | `results/cascade_grid/cicids2017_seed5_s15.json` |
| 2026-11-03 23:46:43 | cascade_grid | cicids2017 | 6 | s15 | 30,000 | 55.8 | `results/cascade_grid/cicids2017_seed6_s15.json` |
| 2026-11-04 00:05:58 | loop grid | iotid20 | 3 | lowbudget | 30,000 | 92.6 | `results/loop_grid/iotid20_seed3_lowbudget.json` |
| 2026-11-04 00:06:30 | loop grid | iotid20 | 5 | lowbudget | 30,000 | 93.1 | `results/loop_grid/iotid20_seed5_lowbudget.json` |
| 2026-11-04 00:06:46 | loop grid | iotid20 | 2 | lowbudget | 30,000 | 93.4 | `results/loop_grid/iotid20_seed2_lowbudget.json` |
| 2026-11-04 00:08:06 | loop grid | iotid20 | 4 | lowbudget | 30,000 | 94.7 | `results/loop_grid/iotid20_seed4_lowbudget.json` |
| 2026-11-04 00:08:40 | loop grid | iotid20 | 1 | lowbudget | 30,000 | 95.3 | `results/loop_grid/iotid20_seed1_lowbudget.json` |
| 2026-11-04 00:08:42 | loop grid | iotid20 | 6 | lowbudget | 30,000 | 95.3 | `results/loop_grid/iotid20_seed6_lowbudget.json` |
| 2026-11-04 00:42:03 | cascade_grid | cicids2017 | 7 | s15 | 30,000 | 58.7 | `results/cascade_grid/cicids2017_seed7_s15.json` |
| 2026-11-04 00:42:32 | cascade_grid | cicids2017 | 8 | s15 | 30,000 | 57.4 | `results/cascade_grid/cicids2017_seed8_s15.json` |
| 2026-11-04 00:45:04 | cascade_grid | cicids2017 | 9 | s15 | 30,000 | 58.2 | `results/cascade_grid/cicids2017_seed9_s15.json` |
| 2026-11-04 01:08:52 | cascade_grid | cicids2017 | 10 | s15 | 30,000 | 26.5 | `results/cascade_grid/cicids2017_seed10_s15.json` |
| 2026-11-04 01:09:13 | cascade_grid | cicids2017 | 11 | s15 | 30,000 | 26.5 | `results/cascade_grid/cicids2017_seed11_s15.json` |
| 2026-11-04 01:09:26 | cascade_grid | cicids2017 | 12 | s15 | 30,000 | 24.2 | `results/cascade_grid/cicids2017_seed12_s15.json` |
| 2026-11-04 01:10:56 | loop grid | iotid20 | 7 | lowbudget | 30,000 | 64.9 | `results/loop_grid/iotid20_seed7_lowbudget.json` |
| 2026-11-04 01:11:16 | loop grid | iotid20 | 9 | lowbudget | 30,000 | 64.5 | `results/loop_grid/iotid20_seed9_lowbudget.json` |
| 2026-11-04 01:11:25 | loop grid | iotid20 | 12 | lowbudget | 30,000 | 62.7 | `results/loop_grid/iotid20_seed12_lowbudget.json` |
| 2026-11-04 01:11:31 | loop grid | iotid20 | 10 | lowbudget | 30,000 | 63.4 | `results/loop_grid/iotid20_seed10_lowbudget.json` |
| 2026-11-04 01:11:32 | loop grid | iotid20 | 8 | lowbudget | 30,000 | 65.0 | `results/loop_grid/iotid20_seed8_lowbudget.json` |
| 2026-11-04 01:11:47 | loop grid | iotid20 | 11 | lowbudget | 30,000 | 63.1 | `results/loop_grid/iotid20_seed11_lowbudget.json` |
| 2026-11-04 01:21:44 | cascade_grid | cicids2017 | 13 | s15 | 30,000 | 12.8 | `results/cascade_grid/cicids2017_seed13_s15.json` |
| 2026-11-04 01:22:15 | cascade_grid | cicids2017 | 14 | s15 | 30,000 | 12.9 | `results/cascade_grid/cicids2017_seed14_s15.json` |
| 2026-11-04 01:22:19 | cascade_grid | cicids2017 | 15 | s15 | 30,000 | 12.8 | `results/cascade_grid/cicids2017_seed15_s15.json` |
| 2026-11-04 01:25:20 | loop grid | ciciot2023 | 2 | lowbudget | 30,000 | 13.8 | `results/loop_grid/ciciot2023_seed2_lowbudget.json` |
| 2026-11-04 01:25:27 | loop grid | ciciot2023 | 1 | lowbudget | 30,000 | 13.9 | `results/loop_grid/ciciot2023_seed1_lowbudget.json` |
| 2026-11-04 01:26:06 | loop grid | ciciot2023 | 3 | lowbudget | 30,000 | 14.3 | `results/loop_grid/ciciot2023_seed3_lowbudget.json` |
| 2026-11-04 01:32:38 | loop grid | iotid20 | 13 | lowbudget | 30,000 | 21.7 | `results/loop_grid/iotid20_seed13_lowbudget.json` |
| 2026-11-04 01:32:49 | loop grid | iotid20 | 15 | lowbudget | 30,000 | 21.4 | `results/loop_grid/iotid20_seed15_lowbudget.json` |
| 2026-11-04 01:33:29 | loop grid | iotid20 | 14 | lowbudget | 30,000 | 22.2 | `results/loop_grid/iotid20_seed14_lowbudget.json` |
| 2026-11-04 01:37:32 | loop grid | ciciot2023 | 4 | lowbudget | 30,000 | 12.2 | `results/loop_grid/ciciot2023_seed4_lowbudget.json` |
| 2026-11-04 01:37:43 | loop grid | ciciot2023 | 5 | lowbudget | 30,000 | 12.2 | `results/loop_grid/ciciot2023_seed5_lowbudget.json` |
| 2026-11-04 01:38:08 | loop grid | ciciot2023 | 6 | lowbudget | 30,000 | 12.0 | `results/loop_grid/ciciot2023_seed6_lowbudget.json` |
| 2026-11-04 01:44:58 | loop grid | ciciot2023 | 8 | lowbudget | 30,000 | 12.1 | `results/loop_grid/ciciot2023_seed8_lowbudget.json` |
| 2026-11-04 01:45:08 | loop grid | ciciot2023 | 7 | lowbudget | 30,000 | 12.4 | `results/loop_grid/ciciot2023_seed7_lowbudget.json` |
| 2026-11-04 01:45:35 | loop grid | ciciot2023 | 9 | lowbudget | 30,000 | 12.1 | `results/loop_grid/ciciot2023_seed9_lowbudget.json` |
| 2026-11-04 01:49:25 | loop grid | ciciot2023 | 10 | lowbudget | 30,000 | 11.9 | `results/loop_grid/ciciot2023_seed10_lowbudget.json` |
| 2026-11-04 01:49:37 | loop grid | ciciot2023 | 11 | lowbudget | 30,000 | 11.9 | `results/loop_grid/ciciot2023_seed11_lowbudget.json` |
| 2026-11-04 01:49:53 | loop grid | ciciot2023 | 12 | lowbudget | 30,000 | 11.7 | `results/loop_grid/ciciot2023_seed12_lowbudget.json` |
| 2026-11-04 01:56:42 | loop grid | ciciot2023 | 14 | lowbudget | 30,000 | 11.5 | `results/loop_grid/ciciot2023_seed14_lowbudget.json` |
| 2026-11-04 01:56:59 | loop grid | ciciot2023 | 13 | lowbudget | 30,000 | 12.0 | `results/loop_grid/ciciot2023_seed13_lowbudget.json` |
| 2026-11-04 01:57:11 | loop grid | ciciot2023 | 15 | lowbudget | 30,000 | 11.6 | `results/loop_grid/ciciot2023_seed15_lowbudget.json` |
| 2026-11-04 05:39:05 | loop grid | iotid20 | 3 | frameunc | 30,000 | 26.7 | `results/loop_grid/iotid20_seed3_frameunc.json` |
| 2026-11-04 05:39:09 | loop grid | iotid20 | 2 | frameunc | 30,000 | 26.8 | `results/loop_grid/iotid20_seed2_frameunc.json` |
| 2026-11-04 05:39:13 | loop grid | iotid20 | 6 | frameunc | 30,000 | 26.8 | `results/loop_grid/iotid20_seed6_frameunc.json` |
| 2026-11-04 05:39:25 | loop grid | iotid20 | 4 | frameunc | 30,000 | 27.0 | `results/loop_grid/iotid20_seed4_frameunc.json` |
| 2026-11-04 05:39:27 | loop grid | iotid20 | 1 | frameunc | 30,000 | 27.1 | `results/loop_grid/iotid20_seed1_frameunc.json` |
| 2026-11-04 05:39:30 | loop grid | iotid20 | 5 | frameunc | 30,000 | 27.1 | `results/loop_grid/iotid20_seed5_frameunc.json` |
| 2026-11-04 06:05:26 | loop grid | iotid20 | 11 | frameunc | 30,000 | 26.0 | `results/loop_grid/iotid20_seed11_frameunc.json` |
| 2026-11-04 06:05:30 | loop grid | iotid20 | 7 | frameunc | 30,000 | 26.4 | `results/loop_grid/iotid20_seed7_frameunc.json` |
| 2026-11-04 06:05:31 | loop grid | iotid20 | 12 | frameunc | 30,000 | 26.0 | `results/loop_grid/iotid20_seed12_frameunc.json` |
| 2026-11-04 06:05:42 | loop grid | iotid20 | 10 | frameunc | 30,000 | 26.3 | `results/loop_grid/iotid20_seed10_frameunc.json` |
| 2026-11-04 06:05:42 | loop grid | iotid20 | 8 | frameunc | 30,000 | 26.5 | `results/loop_grid/iotid20_seed8_frameunc.json` |
| 2026-11-04 06:05:47 | loop grid | iotid20 | 9 | frameunc | 30,000 | 26.5 | `results/loop_grid/iotid20_seed9_frameunc.json` |
| 2026-11-04 06:21:22 | loop grid | ciciot2023 | 2 | frameunc | 30,000 | 15.6 | `results/loop_grid/ciciot2023_seed2_frameunc.json` |
| 2026-11-04 06:21:29 | loop grid | ciciot2023 | 1 | frameunc | 30,000 | 15.8 | `results/loop_grid/ciciot2023_seed1_frameunc.json` |
| 2026-11-04 06:21:31 | loop grid | ciciot2023 | 3 | frameunc | 30,000 | 15.7 | `results/loop_grid/ciciot2023_seed3_frameunc.json` |
| 2026-11-04 06:31:37 | loop grid | iotid20 | 13 | frameunc | 30,000 | 26.2 | `results/loop_grid/iotid20_seed13_frameunc.json` |
| 2026-11-04 06:31:37 | loop grid | iotid20 | 15 | frameunc | 30,000 | 26.1 | `results/loop_grid/iotid20_seed15_frameunc.json` |
| 2026-11-04 06:32:01 | loop grid | iotid20 | 14 | frameunc | 30,000 | 26.5 | `results/loop_grid/iotid20_seed14_frameunc.json` |
| 2026-11-04 06:37:06 | loop grid | ciciot2023 | 4 | frameunc | 30,000 | 15.7 | `results/loop_grid/ciciot2023_seed4_frameunc.json` |
| 2026-11-04 06:37:08 | loop grid | ciciot2023 | 6 | frameunc | 30,000 | 15.6 | `results/loop_grid/ciciot2023_seed6_frameunc.json` |
| 2026-11-04 06:37:15 | loop grid | ciciot2023 | 5 | frameunc | 30,000 | 15.7 | `results/loop_grid/ciciot2023_seed5_frameunc.json` |
| 2026-11-04 06:47:20 | loop grid | ciciot2023 | 8 | frameunc | 30,000 | 15.7 | `results/loop_grid/ciciot2023_seed8_frameunc.json` |
| 2026-11-04 06:47:28 | loop grid | ciciot2023 | 7 | frameunc | 30,000 | 15.8 | `results/loop_grid/ciciot2023_seed7_frameunc.json` |
| 2026-11-04 06:47:36 | loop grid | ciciot2023 | 9 | frameunc | 30,000 | 15.6 | `results/loop_grid/ciciot2023_seed9_frameunc.json` |
| 2026-11-04 06:52:36 | loop grid | ciciot2023 | 11 | frameunc | 30,000 | 15.5 | `results/loop_grid/ciciot2023_seed11_frameunc.json` |
| 2026-11-04 06:52:38 | loop grid | ciciot2023 | 10 | frameunc | 30,000 | 15.5 | `results/loop_grid/ciciot2023_seed10_frameunc.json` |
| 2026-11-04 06:53:01 | loop grid | ciciot2023 | 12 | frameunc | 30,000 | 15.7 | `results/loop_grid/ciciot2023_seed12_frameunc.json` |
| 2026-11-04 07:02:39 | loop grid | ciciot2023 | 13 | frameunc | 30,000 | 15.3 | `results/loop_grid/ciciot2023_seed13_frameunc.json` |
| 2026-11-04 07:02:45 | loop grid | ciciot2023 | 15 | frameunc | 30,000 | 15.1 | `results/loop_grid/ciciot2023_seed15_frameunc.json` |
| 2026-11-04 07:02:50 | loop grid | ciciot2023 | 14 | frameunc | 30,000 | 15.3 | `results/loop_grid/ciciot2023_seed14_frameunc.json` |
| 2026-11-04 17:28:18 | loop grid | cicids2017 | 4 | frameunc | 30,000 | 44.8 | `results/loop_grid/cicids2017_seed4_frameunc.json` |
| 2026-11-04 17:28:20 | loop grid | cicids2017 | 5 | frameunc | 30,000 | 44.8 | `results/loop_grid/cicids2017_seed5_frameunc.json` |
| 2026-11-04 17:28:32 | loop grid | cicids2017 | 3 | frameunc | 30,000 | 45.0 | `results/loop_grid/cicids2017_seed3_frameunc.json` |
| 2026-11-04 17:28:43 | loop grid | cicids2017 | 1 | frameunc | 30,000 | 45.2 | `results/loop_grid/cicids2017_seed1_frameunc.json` |
| 2026-11-04 17:28:45 | loop grid | cicids2017 | 2 | frameunc | 30,000 | 45.2 | `results/loop_grid/cicids2017_seed2_frameunc.json` |
| 2026-11-04 17:28:52 | loop grid | cicids2017 | 6 | frameunc | 30,000 | 45.3 | `results/loop_grid/cicids2017_seed6_frameunc.json` |
| 2026-11-04 17:51:15 | loop grid | cicids2017 | 10 | frameunc | 30,000 | 22.5 | `results/loop_grid/cicids2017_seed10_frameunc.json` |
| 2026-11-04 17:51:32 | loop grid | cicids2017 | 7 | frameunc | 30,000 | 23.2 | `results/loop_grid/cicids2017_seed7_frameunc.json` |
| 2026-11-04 17:51:35 | loop grid | cicids2017 | 12 | frameunc | 30,000 | 22.7 | `results/loop_grid/cicids2017_seed12_frameunc.json` |
| 2026-11-04 17:51:35 | loop grid | cicids2017 | 9 | frameunc | 30,000 | 23.0 | `results/loop_grid/cicids2017_seed9_frameunc.json` |
| 2026-11-04 17:52:02 | loop grid | cicids2017 | 11 | frameunc | 30,000 | 23.2 | `results/loop_grid/cicids2017_seed11_frameunc.json` |
| 2026-11-04 17:52:05 | loop grid | cicids2017 | 8 | frameunc | 30,000 | 23.7 | `results/loop_grid/cicids2017_seed8_frameunc.json` |
| 2026-11-04 18:13:15 | loop grid | cicids2017 | 13 | frameunc | 30,000 | 22.0 | `results/loop_grid/cicids2017_seed13_frameunc.json` |
| 2026-11-04 18:13:44 | loop grid | cicids2017 | 15 | frameunc | 30,000 | 22.1 | `results/loop_grid/cicids2017_seed15_frameunc.json` |
| 2026-11-04 18:13:55 | loop grid | cicids2017 | 14 | frameunc | 30,000 | 22.4 | `results/loop_grid/cicids2017_seed14_frameunc.json` |
| 2026-11-05 16:57:52 | loop grid | cicids2017 | 1 | frame | 30,000 | 133.5 | `results/loop_grid/cicids2017_seed1_frame.json` |
| 2026-11-05 16:58:56 | loop grid | cicids2017 | 4 | frame | 30,000 | 134.6 | `results/loop_grid/cicids2017_seed4_frame.json` |
| 2026-11-05 16:59:02 | loop grid | cicids2017 | 5 | frame | 30,000 | 134.7 | `results/loop_grid/cicids2017_seed5_frame.json` |
| 2026-11-05 16:59:41 | loop grid | cicids2017 | 2 | frame | 30,000 | 135.4 | `results/loop_grid/cicids2017_seed2_frame.json` |
| 2026-11-05 17:01:06 | loop grid | cicids2017 | 3 | frame | 30,000 | 136.8 | `results/loop_grid/cicids2017_seed3_frame.json` |
| 2026-11-05 17:02:14 | loop grid | cicids2017 | 6 | frame | 30,000 | 137.9 | `results/loop_grid/cicids2017_seed6_frame.json` |
| 2026-11-05 17:36:12 | loop grid | cicids2017 | 10 | frame | 30,000 | 36.5 | `results/loop_grid/cicids2017_seed10_frame.json` |
| 2026-11-05 17:36:12 | loop grid | cicids2017 | 7 | frame | 30,000 | 38.2 | `results/loop_grid/cicids2017_seed7_frame.json` |
| 2026-11-05 17:36:15 | loop grid | cicids2017 | 8 | frame | 30,000 | 37.3 | `results/loop_grid/cicids2017_seed8_frame.json` |
| 2026-11-05 17:36:39 | loop grid | cicids2017 | 9 | frame | 30,000 | 37.6 | `results/loop_grid/cicids2017_seed9_frame.json` |
| 2026-11-05 17:36:54 | loop grid | cicids2017 | 12 | frame | 30,000 | 34.6 | `results/loop_grid/cicids2017_seed12_frame.json` |
| 2026-11-05 17:37:15 | loop grid | cicids2017 | 11 | frame | 30,000 | 36.1 | `results/loop_grid/cicids2017_seed11_frame.json` |
| 2026-11-05 18:01:56 | loop grid | cicids2017 | 13 | frame | 30,000 | 25.7 | `results/loop_grid/cicids2017_seed13_frame.json` |
| 2026-11-05 18:01:56 | loop grid | cicids2017 | 14 | frame | 30,000 | 25.7 | `results/loop_grid/cicids2017_seed14_frame.json` |
| 2026-11-05 18:02:02 | loop grid | cicids2017 | 15 | frame | 30,000 | 25.8 | `results/loop_grid/cicids2017_seed15_frame.json` |

Dataset reports: `results/inspect_IoT_Network_Intrusion_Dataset.txt`, `results/inspect_friday.txt`, `results/inspect_part-00000.txt`
<!-- history:end -->
