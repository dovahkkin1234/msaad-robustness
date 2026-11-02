"""Prequential (test-then-train) evaluation loop.

For each sample: scale with stats-so-far, predict (score), then learn. This is the
interleaved protocol standard for data streams and the one the base paper uses. Throughput
is measured as samples / wall-second over the scored region.
"""
from __future__ import annotations

import itertools
import time
from typing import Dict, Iterable, Tuple

from tqdm import tqdm

from ..data.preprocessing import RunningMinMax
from ..eval.metrics import BinaryMetrics


def run_prequential(
    model,
    stream: Iterable[Tuple[Dict[str, float], int]],
    warmup: int = 0,
    scale: bool = True,
    progress: bool = True,
    log_every: int = 0,
) -> Dict:
    """Run test-then-train over ``stream``. Returns metrics + throughput + learning curve.

    warmup: first N samples are learned but not scored (optional; default 0 = pure
            prequential, which is the honest setting).
    """
    scaler = RunningMinMax() if scale else None
    metrics = BinaryMetrics()
    curve = []  # (n_scored, rolling_accuracy) snapshots for the learning-curve figure

    # Pull the first sample BEFORE the progress bar starts, so loader messages (e.g. the
    # stride-sampling summary) print on their own lines instead of inside the bar.
    stream = iter(stream)
    first = next(stream, None)
    if first is None:
        raise ValueError("the stream is empty: check the dataset path and row filter")
    stream = itertools.chain([first], stream)

    t0 = time.perf_counter()
    scored = 0

    it = enumerate(stream)
    if progress:
        it = tqdm(it, desc="prequential", unit="smp")

    for i, (x, y) in it:
        x_in = scaler.transform_then_learn(x) if scaler is not None else x
        if i >= warmup:
            y_pred = model.predict_one(x_in)
            metrics.update(y, y_pred)
            scored += 1
            if log_every and scored % log_every == 0:
                curve.append((scored, round(100 * metrics.rolling_accuracy, 2)))
        model.learn_one(x_in, y)

    elapsed = time.perf_counter() - t0
    out = metrics.as_dict()
    out["throughput_sps"] = round(scored / elapsed, 1) if elapsed > 0 else None
    out["elapsed_s"] = round(elapsed, 2)
    out["learning_curve"] = curve
    return out
