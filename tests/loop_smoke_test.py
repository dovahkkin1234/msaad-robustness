"""Fast self-check of the S4 adaptation-loop experiment (label poisoning and the defences).

Runs experiments/adaptation_loop.py on the synthetic stream (no data files needed) with
true and fully poisoned labels, and checks that
  * every scenario x label source x policy run is present,
  * poisoning works against the paper's update rule (vanilla ASR rises sharply),
  * the strict policy blocks it (ASR stays near the no-learning reference) by skipping the
    unverified benign labels,
  * the importance-weighted strict policy (iwstrict) blocks it too while learning each
    audited benign flow several times;
  v14: framing flows (frame:r) are injected and learned by strict but blocked by consensus,
    the copy cap (iwstrict:a:c) is honoured, noiseaware runs, and mixed audits are spent.
About two minutes. Run from the repo root:  python tests\\loop_smoke_test.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "loop.json"
        cmd = [sys.executable, str(ROOT / "experiments" / "adaptation_loop.py"), "--data", "synthetic",
               "--limit", "1500", "--no-progress", "--out", str(out),
               "--labels", "true", "poison:1.0", "--policies", "vanilla", "strict:0.1", "iwstrict:0.1"]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0 or not out.exists():
            print(proc.stdout[-2000:], proc.stderr[-2000:])
            print("[loop-smoke] FAIL: adaptation_loop.py did not finish")
            return 1
        r = json.load(open(out))

    rows = {(s["scenario"], s["learning"], s["policy"]): s for s in r["scenarios"]}
    problems = []
    scen = sorted({s["scenario"] for s in r["scenarios"]})
    for sc in scen:
        for key in [("frozen", "frozen"), ("true", "vanilla"), ("true", "strict:0.1"), ("true", "iwstrict:0.1"),
                    ("poison:1.0", "vanilla"), ("poison:1.0", "strict:0.1"), ("poison:1.0", "iwstrict:0.1")]:
            if (sc, *key) not in rows:
                problems.append(f"missing run {sc} / {key[0]} / {key[1]}")
    if problems:
        for p in problems:
            print("  -", p)
        print("[loop-smoke] FAIL")
        return 1

    clean_true = rows[("clean", "true", "vanilla")]["asr"]
    clean_pois = rows[("clean", "poison:1.0", "vanilla")]["asr"]
    strict_pois = rows[("clean", "poison:1.0", "strict:0.1")]
    frozen = rows[("clean", "frozen", "frozen")]["asr"]
    if not clean_pois > clean_true + 20:
        problems.append(f"poisoning did not raise vanilla ASR ({clean_true} -> {clean_pois})")
    if not strict_pois["asr"] <= frozen + 5:
        problems.append(f"strict policy did not contain poisoning (ASR {strict_pois['asr']} vs frozen {frozen})")
    if strict_pois["n_skipped"] <= 0 or strict_pois["n_poisoned_learned"] != 0:
        problems.append("strict policy learned unverified benign labels")
    iw_pois = rows[("clean", "poison:1.0", "iwstrict:0.1")]
    if not iw_pois["asr"] <= frozen + 5:
        problems.append(f"iwstrict policy did not contain poisoning (ASR {iw_pois['asr']} vs frozen {frozen})")
    if iw_pois["n_skipped"] <= 0 or iw_pois["n_poisoned_learned"] != 0:
        problems.append("iwstrict policy learned unverified benign labels")
    st_true, iw_true = rows[("clean", "true", "strict:0.1")], rows[("clean", "true", "iwstrict:0.1")]
    if not iw_true["n_learn"] > st_true["n_learn"]:
        problems.append("iwstrict did not re-learn the audited benign flows")
    print(f"[loop-smoke] ASR with true labels {clean_true}% | fully poisoned: vanilla {clean_pois}%, "
          f"strict {strict_pois['asr']}% (skipped {strict_pois['n_skipped']} unverified benign labels), "
          f"iwstrict {iw_pois['asr']}% | no learning {frozen}%")
    print(f"[loop-smoke] false alarms with true labels: vanilla {rows[('clean', 'true', 'vanilla')]['fpr']}%, "
          f"strict {st_true['fpr']}%, iwstrict {iw_true['fpr']}% (updates: {st_true['n_learn']} vs {iw_true['n_learn']})")

    # v14: framing, consensus, copy cap, noiseaware, mixed audits.
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "loop14.json"
        cmd = [sys.executable, str(ROOT / "experiments" / "adaptation_loop.py"), "--data", "synthetic",
               "--limit", "1500", "--no-progress", "--out", str(out), "--audits", "mixed",
               "--labels", "true", "frame:0.1", "poison:1.0",
               "--policies", "strict:0.1", "iwstrict:0.05:5", "consensus:0.1", "noiseaware:0.1"]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0 or not out.exists():
            print(proc.stdout[-2000:], proc.stderr[-2000:])
            print("[loop-smoke] FAIL: adaptation_loop.py (v14 options) did not finish")
            return 1
        r14 = json.load(open(out))
    rows14 = {(s["scenario"], s["learning"], s["policy"]): s for s in r14["scenarios"]}
    st_f, co_f = rows14[("clean", "frame:0.1", "strict:0.1")], rows14[("clean", "frame:0.1", "consensus:0.1")]
    st_t = rows14[("clean", "true", "strict:0.1")]
    if st_f["n_frame_learned"] <= 0 or st_f.get("fpr_frame_window") is None:
        problems.append("framing flows were not injected / learned by strict")
    if co_f["n_frame_blocked"] <= 0:
        problems.append("consensus did not block unverified framing labels")
    if not st_f["fpr"] >= st_t["fpr"]:
        problems.append(f"framing did not raise strict's false alarms ({st_t['fpr']} -> {st_f['fpr']})")
    cap_row = rows14[("clean", "true", "iwstrict:0.05:5")]
    if cap_row["iw_cap"] != 5:
        problems.append("the iwstrict copy cap was not recorded")
    if any(s["n_audited"] <= 0 for s in r14["scenarios"] if s["policy"] != "frozen"):
        problems.append("mixed audits were not spent")
    if ("clean", "poison:1.0", "noiseaware:0.1") not in rows14:
        problems.append("noiseaware run missing")
    print(f"[loop-smoke] framing (10%): strict FPR {st_t['fpr']}% -> {st_f['fpr']}% "
          f"(learned {st_f['n_frame_learned']} framing flows); consensus FPR {co_f['fpr']}% "
          f"(blocked {co_f['n_frame_blocked']}); noiseaware ASR under full poisoning "
          f"{rows14[('clean', 'poison:1.0', 'noiseaware:0.1')]['asr']}%")
    if problems:
        for p in problems:
            print("  -", p)
        print("[loop-smoke] FAIL")
        return 1
    print("[loop-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
