"""Fast self-check: the full pipeline must learn on a synthetic drifting stream.

Run from the repo root:  python tests/smoke_test.py
Passes if final accuracy on the synthetic stream clears a sane floor.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.data.loaders import stream_synth
from src.eval.prequential import run_prequential
from src.models.mabtse import MABTSE
from src.models.pool import build_pool
from src.utils.seeding import seed_everything

FLOOR = 90.0  # synthetic classes are separable; a working pipeline clears this easily


def main() -> int:
    seed_everything(42)
    model = MABTSE(build_pool(seed=42), seed=42)
    res = run_prequential(model, stream_synth(n=6000, seed=42),
                          warmup=0, progress=False, log_every=1000)
    acc = res["accuracy"]
    print(f"[smoke] accuracy={acc}  f1={res['f1']}  "
          f"throughput={res['throughput_sps']} smp/s  curve={res['learning_curve']}")
    if acc >= FLOOR:
        print(f"[smoke] PASS (>= {FLOOR})")
        return 0
    print(f"[smoke] FAIL (< {FLOOR}) — investigate before handover")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
