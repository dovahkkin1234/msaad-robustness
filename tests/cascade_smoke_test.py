"""Fast self-check of the v14 detector chain (experiments/cascade_eval.py) and of the
adaptive attackers in experiments/adv_training.py, on synthetic streams (no data files).

Checks: every scenario x condition x chain row is present; the graph stage runs (non-zero
drift coverage) and catches flows stage 1 misses on the synthetic flood; full label
poisoning hurts the chain under the paper's rule and strict contains it; the graph-aware
attacker scenarios (spoof, thin) are produced; the run without host addresses (--no-graph)
works; the adaptive attackers (distill, atsur, hsj) report results. About two minutes.

Run from the repo root:  python tests\\cascade_smoke_test.py
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script, out, extra):
    cmd = [sys.executable, str(ROOT / "experiments" / script), "--data", "synthetic", "--no-progress",
           "--out", str(out), *extra]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        print(proc.stdout[-2500:], proc.stderr[-2500:])
        return None
    return json.load(open(out))


def main() -> int:
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        r = _run("cascade_eval.py", Path(tmp) / "c.json", ["--limit", "3000", "--attacks", "pgd"])
        r0 = _run("cascade_eval.py", Path(tmp) / "c0.json", ["--limit", "2000", "--attacks", "pgd", "--no-graph",
                                                             "--conditions", "frozen"])
        a = _run("adv_training.py", Path(tmp) / "a.json", ["--limit", "2000", "--variants", "none",
                                                           "--learning", "frozen", "--adaptive", "distill", "atsur",
                                                           "hsj", "--hsj-flows", "5", "--hsj-queries", "300"])
    if r is None or r0 is None or a is None:
        print("[cascade-smoke] FAIL: a run did not finish")
        return 1
    rows = {(s["scenario"], s["learning"], s["chain"]): s for s in r["scenarios"]}
    need = [("pgd/attack_only/feasible", "frozen", c) for c in
            ("S1", "S2", "S1+S2", "S3:gnn_full", "S3:gnn_drift", "S3:ctx", "S1+S2+S3:gnn_drift")]
    need += [("pgd/attack_only/feasible", "delay:1000|poison:1.0|vanilla", "S1"),
             ("pgd/attack_only/feasible", "delay:1000|poison:1.0|strict:0.1", "S1"),
             ("pgd/attack_only/feasible/spoof:10", "frozen", "S1+S3:gnn_full"),
             ("pgd/attack_only/feasible/thin:0.25", "frozen", "S1+S3:gnn_full")]
    for k in need:
        if k not in rows:
            problems.append(f"missing row {k}")
    if not problems:
        s1 = rows[("pgd/attack_only/feasible", "frozen", "S1")]
        ch = rows[("pgd/attack_only/feasible", "frozen", "S1+S3:gnn_full")]
        if not ch["asr"] < s1["asr"]:
            problems.append(f"the graph stage caught nothing ({s1['asr']} -> {ch['asr']})")
        if not (rows[("pgd/attack_only/feasible", "frozen", "S3:gnn_drift")]["drift_coverage"] or 0) > 0:
            problems.append("drift focus covered no flows")
        van = rows[("pgd/attack_only/feasible", "delay:1000|poison:1.0|vanilla", "S1+S2+S3:gnn_full")]["asr"]
        st = rows[("pgd/attack_only/feasible", "delay:1000|poison:1.0|strict:0.1", "S1+S2+S3:gnn_full")]["asr"]
        if not st <= van:
            problems.append(f"strict did not protect the chain under poisoning ({van} vs {st})")
        if rows[("pgd/attack_only/feasible/thin:0.25", "frozen", "S1")].get("evaded_volume") is None:
            problems.append("thin scenario has no evaded volume")
        print(f"[cascade-smoke] frozen repaired PGD: S1 ASR {s1['asr']}% -> S1+GNN {ch['asr']}% | "
              f"poisoned chain: vanilla {van}% vs strict {st}% | params {r['training']}")
    if r0.get("graph") is not False or not any(s["chain"] == "S1+S2" for s in r0["scenarios"]):
        problems.append("the no-graph run did not produce the S1+S2 chain")
    hs = [s for s in a["scenarios"] if s.get("attack") == "hsj"]
    if not hs or "asr_feasible_by_budget" not in hs[0]:
        problems.append("HopSkipJump results missing")
    for nm in ("pgd-atsur/attack_only/feasible", "pgd-distill/attack_only/feasible"):
        if not any(s["scenario"] == nm for s in a["scenarios"]):
            problems.append(f"adaptive scenario {nm} missing")
    if problems:
        for p in problems:
            print("  -", p)
        print("[cascade-smoke] FAIL")
        return 1
    print("[cascade-smoke] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
