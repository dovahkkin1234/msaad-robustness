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

Dataset reports: `results/inspect_IoT_Network_Intrusion_Dataset.txt`, `results/inspect_part-00000.txt`
<!-- history:end -->
