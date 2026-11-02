"""Fast self-check of the attack stack (surrogate, FGSM/BIM/PGD/C&W, constraints, scenarios).

Runs experiments/under_attack.py on the synthetic stream (no data files needed) and checks
the output. Takes about a minute.

Run from the repo root:  python tests\\attack_smoke_test.py
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
        out = Path(tmp) / "synthetic.json"
        cmd = [sys.executable, str(ROOT / "experiments" / "under_attack.py"), "--data", "synthetic",
               "--limit", "1500", "--no-progress", "--out", str(out)]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if proc.returncode != 0 or not out.exists():
            print(proc.stdout[-2000:], proc.stderr[-2000:])
            print("[attack-smoke] FAIL: the experiment did not finish")
            return 1
        r = json.load(open(out))
    problems = []
    names = {(s["scenario"], s["learning"]) for s in r["scenarios"]}
    for atk in ("fgsm", "bim", "pgd", "cw"):
        for need in ((f"{atk}/attack_only", "online"), (f"{atk}/attack_only", "frozen"),
                     (f"{atk}/all", "online"), (f"{atk}/attack_only/feasible", "online")):
            if need not in names:
                problems.append(f"missing scenario {need}")
    for key, info in r["attacks"].items():
        if key.split("/")[0] != "cw" and info["linf_max"] is not None and info["linf_max"] > r["settings"]["eps"] + 1e-9:
            problems.append(f"{key}: perturbation exceeds eps ({info['linf_max']})")
        f = info.get("feasible")
        if f and f["linf_max"] is not None and f["linf_max"] > info["linf_max"] + 1e-9:
            problems.append(f"{key}: feasible version is larger than the attack")
    clean = {s["learning"]: s for s in r["scenarios"] if s["scenario"] == "clean"}
    if clean["online"]["accuracy"] < 90:
        problems.append(f"clean accuracy too low ({clean['online']['accuracy']})")
    frozen_pgd = next(s for s in r["scenarios"] if s["scenario"] == "pgd/attack_only" and s["learning"] == "frozen")
    print(f"[attack-smoke] clean acc {clean['online']['accuracy']}% | frozen PGD: ASR {frozen_pgd['asr']}% "
          f"(clean miss {frozen_pgd['clean_miss']}%) | surrogate test acc {r['surrogate']['test_acc']}%")
    if problems:
        for p in problems:
            print("  -", p)
        print("[attack-smoke] FAIL")
        return 1
    print("[attack-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
