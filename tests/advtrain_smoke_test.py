"""Fast self-check of the adversarial-training baseline (experiments/adv_training.py).

Runs it on the synthetic stream (no data files needed) next to under_attack.py and checks:
every variant and label mode is there, the adversarial copies were made, "seen" marks the
right attacks, and the "none" variant reproduces under_attack.py's frozen numbers exactly
(same data, model, attacker and perturbations). About a minute.

Run from the repo root:  python tests\\advtrain_smoke_test.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str, out: Path, extra) -> bool:
    cmd = [sys.executable, str(ROOT / "experiments" / script), "--data", "synthetic",
           "--limit", "2000", "--no-progress", "--out", str(out), *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        print(proc.stdout[-2000:], proc.stderr[-2000:])
        return False
    return True


def main() -> int:
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        at, ua = Path(tmp) / "at.json", Path(tmp) / "ua.json"
        if not _run("adv_training.py", at, ["--learning", "frozen", "delay:200"]):
            print("[advtrain-smoke] FAIL: adv_training.py did not finish")
            return 1
        if not _run("under_attack.py", ua, ["--perturb", "attack_only", "--learning", "frozen"]):
            print("[advtrain-smoke] FAIL: under_attack.py did not finish")
            return 1
        r, u = json.load(open(at)), json.load(open(ua))

    rows = r["scenarios"]
    for v in ("none", "at:pgd", "at:fgsm+bim+pgd+cw"):
        if not any(s["at"] == v for s in rows):
            problems.append(f"variant {v} missing")
    for m in ("frozen", "delay:200"):
        if not any(s["learning"] == m for s in rows):
            problems.append(f"label mode {m} missing")
    if r["training"]["at:pgd"]["n_copies"] <= 0:
        problems.append("no adversarial copies were made for at:pgd")
    for s in rows:
        if s["at"] == "at:pgd" and s["attack"] is not None and s["seen"] != (s["attack"] == "pgd"):
            problems.append(f"wrong 'seen' flag on {s['scenario']}")
            break
    ref = {s["scenario"]: (s["asr"], s["fpr"], s["accuracy"])
           for s in u["scenarios"] if s["learning"] == "frozen"}
    for s in rows:
        if s["at"] == "none" and s["learning"] == "frozen":
            if ref.get(s["scenario"]) != (s["asr"], s["fpr"], s["accuracy"]):
                problems.append(f"'none' differs from under_attack.py on {s['scenario']}")

    def asr(v, sc):
        return next(s["asr"] for s in rows if s["at"] == v and s["scenario"] == sc and s["learning"] == "frozen")

    print(f"[advtrain-smoke] frozen PGD (repaired) ASR: none {asr('none', 'pgd/attack_only/feasible')}% | "
          f"at:pgd {asr('at:pgd', 'pgd/attack_only/feasible')}% | unseen C&W under at:pgd "
          f"{asr('at:pgd', 'cw/attack_only/feasible')}%")
    if problems:
        for p in problems:
            print("  -", p)
        print("[advtrain-smoke] FAIL")
        return 1
    print("[advtrain-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
