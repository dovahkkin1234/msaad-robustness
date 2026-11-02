"""KNN-ADWIN rebuilt for River 0.22.

The base paper's pool includes "KNN-ADWIN" (KNNADWINClassifier, which existed in early River
and in scikit-multiflow). Current River no longer ships it, so we rebuild its behaviour:

  * exact k-NN (k = 5) over a sliding window of the most recent ``window_size`` samples
    (River's LazySearch: brute-force, exact, deterministic);
  * an ADWIN detector watches the classifier's 0/1 error stream; when ADWIN signals drift
    and its window is shorter than the k-NN window, the k-NN window is shrunk to ADWIN's
    width, discarding samples from before the change (the original's behaviour).

Note: River's default KNNClassifier engine (SWINN) is an approximate, randomly seeded
search; we deliberately do not use it.
"""
from __future__ import annotations

import collections
from typing import Deque, Dict, Optional, Tuple

from river import drift, neighbors


class KNNADWIN:
    def __init__(self, n_neighbors: int = 5, window_size: int = 100) -> None:
        self.n_neighbors = n_neighbors
        self.window_size = window_size
        self._buf: Deque[Tuple[dict, int]] = collections.deque(maxlen=window_size)
        self._knn = self._new_knn()
        self._adwin = drift.ADWIN()
        self._last_x: Optional[dict] = None
        self._last_proba: Dict = {}
        self.n_shrinks = 0  # how often drift shrank the window (useful for logging)

    def _new_knn(self):
        return neighbors.KNNClassifier(
            n_neighbors=self.n_neighbors,
            engine=neighbors.LazySearch(window_size=self.window_size),
        )

    def predict_proba_one(self, x: dict) -> Dict:
        proba = self._knn.predict_proba_one(x) or {}
        self._last_x, self._last_proba = x, proba  # reused by learn_one for the same sample
        return proba

    def predict_one(self, x: dict):
        proba = self.predict_proba_one(x)
        return max(proba, key=proba.get) if proba else None

    def learn_one(self, x: dict, y) -> "KNNADWIN":
        proba = self._last_proba if x is self._last_x else (self._knn.predict_proba_one(x) or {})
        if proba:
            pred = max(proba, key=proba.get)
            self._adwin.update(int(pred != y))
            if self._adwin.drift_detected:
                width = int(self._adwin.width)
                if width < len(self._buf):
                    keep = list(self._buf)[-width:] if width > 0 else []
                    self._knn = self._new_knn()
                    for xi, yi in keep:
                        self._knn.learn_one(xi, yi)
                    self._buf = collections.deque(keep, maxlen=self.window_size)
                    self.n_shrinks += 1
        self._buf.append((x, y))
        self._knn.learn_one(x, y)
        self._last_x, self._last_proba = None, {}
        return self
