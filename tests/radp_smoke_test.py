"""Fast self-check of the RADP stack (MSAPG, GAN, RAD, purification) and the label modes.

Runs experiments/radp_defense.py and experiments/under_attack.py (delayed and self-labelled
modes) on the synthetic stream (no data files needed) and checks the outputs. About 2-3 min.

Run from the repo root:  python tests\\radp_smoke_test.py
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
           "--limit", "1500", "--no-progress", "--out", str(out), *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        print(proc.stdout[-2000:], proc.stderr[-2000:])
        return False
    return True


def main() -> int:
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        rp, ua = Path(tmp) / "radp.json", Path(tmp) / "labels.json"
        if not _run("radp_defense.py", rp, ["--attacks", "fgsm", "pgd"]):
            print("[radp-smoke] FAIL: radp_defense.py did not finish")
            return 1
        if not _run("under_attack.py", ua, ["--attacks", "pgd", "--perturb", "attack_only",
                                            "--learning", "online", "frozen", "delay:50", "self"]):
            print("[radp-smoke] FAIL: under_attack.py (label modes) did not finish")
            return 1
        r = json.load(open(rp))
        u = json.load(open(ua))

    rows = r["scenarios"]
    for v in ("rad", "rad_nogan", "loao_fgsm", "loao_pgd"):
        if v not in r["rad"]:
            problems.append(f"missing RAD variant {v}")
    for s in rows:
        if s["learning"] == "frozen" and s["asr_no_radp"] is not None and s["e2e_asr"] is not None \
                and s["e2e_asr"] > s["asr_no_radp"] + 1e-9:
            problems.append(f"{s['rad']}/{s['scenario']}: RADP raised the frozen attack success")
    if not any(s["learning"] == "online" and s["rad"] == "rad" for s in rows):
        problems.append("no online run on the purified stream")
    fid = r["rad"]["rad"]["gan_fidelity"]
    if not fid or fid.get("c2st_auc") is None:
        problems.append("GAN fidelity not reported")

    modes = {s["learning"] for s in u["scenarios"]}
    for m in ("online", "frozen", "delay:50", "self"):
        if m not in modes:
            problems.append(f"label mode {m} missing")

    rad_pgd = next(s for s in rows if s["rad"] == "rad" and s["scenario"] == "pgd/attack_only"
                   and s["learning"] == "frozen")
    print(f"[radp-smoke] RAD hold-out acc {r['rad']['rad']['holdout_acc']}% | PGD: RAD flags "
          f"{rad_pgd['rad_flag_ddos']}% of perturbed DDoS, deletes {rad_pgd['benign_deleted']}% of benign | "
          f"GAN two-sample AUC {fid['c2st_auc'] if fid else '-'} | label modes {sorted(modes)}")
    if problems:
        for p in problems:
            print("  -", p)
        print("[radp-smoke] FAIL")
        return 1
    print("[radp-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
