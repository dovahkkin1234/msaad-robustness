"""Leakage-free, streaming preprocessing.

The base paper's global min-max scaling (Eq. 14) and offline feature selection are a
data-snooping risk (Arp et al., "Dos and Don'ts of ML in Computer Security", 2022).
We scale with statistics seen *so far only*: transform the current sample with the
running min/max, THEN update the stats with it. This is the prequential-correct order.
"""
from __future__ import annotations

from typing import Dict


class RunningMinMax:
    """Per-feature min-max scaler updated online. Transform-then-learn per sample."""

    def __init__(self) -> None:
        self._mn: Dict[str, float] = {}
        self._mx: Dict[str, float] = {}

    def transform_one(self, x: Dict[str, float]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        for k, v in x.items():
            mn = self._mn.get(k, v)
            mx = self._mx.get(k, v)
            rng = mx - mn
            out[k] = 0.0 if rng == 0 else (v - mn) / rng
        return out

    def learn_one(self, x: Dict[str, float]) -> "RunningMinMax":
        for k, v in x.items():
            self._mn[k] = v if k not in self._mn else min(self._mn[k], v)
            self._mx[k] = v if k not in self._mx else max(self._mx[k], v)
        return self

    def transform_then_learn(self, x: Dict[str, float]) -> Dict[str, float]:
        out = self.transform_one(x)
        self.learn_one(x)
        return out
