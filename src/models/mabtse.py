"""MABTSE — Layer 3: Multi-Armed Bandit (Thompson Sampling) + AUWPAE weighting.

Faithful reconstruction of the base paper's Layer 3, with ONE documented correction:

  The paper's Algorithm 1 initialises every arm to Beta(1, 1) but, as printed, never
  updates alpha/beta and never defines the reward — so as written the selector would
  stay uniform (random top-k) forever. The text says the estimates ARE updated, so we
  treat the omission as a typo and define the reward as per-arm correctness:
      correct prediction -> alpha += 1   (success)
      wrong prediction   -> beta  += 1   (failure)
  This reward channel is exactly the surface our later robustness analysis probes, so it
  is isolated here and configurable.

Per incoming sample:
  1. draw theta_i ~ Beta(alpha_i, beta_i) for each arm (learner)
  2. keep the top-k arms by theta (k=3 in the paper)
  3. AUWPAE: weight each kept arm by w_i = 1 / (recent_MSE_i + eps), eps=1e-4
  4. predict argmax of the weighted class-probability average
  5. on the true label: update each arm's rolling MSE, Beta posterior, and learn_one
"""
from __future__ import annotations

import collections
import random
from typing import Dict, List, Optional


class MABTSE:
    def __init__(
        self,
        learners: Dict[str, object],
        top_k: int = 3,
        eps: float = 1e-4,
        mse_window: int = 500,
        reward: str = "correctness",
        seed: int = 42,
        cache: bool = True,
    ) -> None:
        self.learners = learners
        self.names: List[str] = list(learners.keys())
        self.top_k = min(top_k, len(self.names))
        self.eps = eps
        self.reward = reward
        self.cache = cache  # reuse predict-time probabilities in learn_one (same outputs)
        self._cache_x = None
        self._cache: Dict[str, Dict] = {}
        self._rng = random.Random(seed)
        # Thompson-Sampling Beta posteriors (the corrected, learning version).
        self.alpha: Dict[str, float] = {n: 1.0 for n in self.names}
        self.beta: Dict[str, float] = {n: 1.0 for n in self.names}
        # Rolling squared error per arm, for the AUWPAE weight.
        self._sq_err: Dict[str, collections.deque] = {
            n: collections.deque(maxlen=mse_window) for n in self.names
        }
        self._last_selected: List[str] = []

    # -- internals -----------------------------------------------------------
    def _weight(self, name: str) -> float:
        errs = self._sq_err[name]
        mse = (sum(errs) / len(errs)) if errs else 1.0
        return 1.0 / (mse + self.eps)

    def _select(self) -> List[str]:
        draws = {n: self._rng.betavariate(self.alpha[n], self.beta[n]) for n in self.names}
        return sorted(self.names, key=lambda n: draws[n], reverse=True)[: self.top_k]

    # -- River-style API -----------------------------------------------------
    def predict_proba_one(self, x: Dict[str, float]) -> Dict[int, float]:
        selected = self._select()
        self._last_selected = selected
        probas = {n: (self.learners[n].predict_proba_one(x) or {}) for n in selected}
        if self.cache:
            self._cache_x, self._cache = x, probas
        agg: Dict[int, float] = collections.defaultdict(float)
        wsum = 0.0
        for n in selected:
            w = self._weight(n)
            proba = probas[n]
            for cls, p in proba.items():
                agg[cls] += w * p
            wsum += w
        if wsum > 0:
            for cls in list(agg):
                agg[cls] /= wsum
        return dict(agg)

    def predict_one(self, x: Dict[str, float]) -> Optional[int]:
        proba = self.predict_proba_one(x)
        return max(proba, key=proba.get) if proba else None

    def learn_one(self, x: Dict[str, float], y: int, update_selector: bool = True) -> "MABTSE":
        """Learn one labelled sample.

        update_selector=False lets the base learners learn (x, y) but leaves the selector
        untouched (no Thompson-Sampling reward, no AUWPAE error). The audited-selector defence
        (experiments/adaptation_loop.py) uses it so that only verified labels steer selection.
        The default (True) is the paper's behaviour."""
        # Probabilities computed at predict time for this same sample are reused: no learner
        # has changed between predict_one(x) and learn_one(x, y), so the outputs are identical.
        cached = self._cache if (self.cache and x is self._cache_x) else {}
        for n in self.names:
            if update_selector:
                proba = cached[n] if n in cached else (self.learners[n].predict_proba_one(x) or {})
                pred = max(proba, key=proba.get) if proba else None
                # AUWPAE error signal: squared error on the prob mass given to the true class.
                p_true = proba.get(y, 0.0)
                self._sq_err[n].append((1.0 - p_true) ** 2)
                # Thompson-Sampling reward update (the Algorithm-1 fix).
                if pred is not None and self.reward == "correctness":
                    if pred == y:
                        self.alpha[n] += 1.0
                    else:
                        self.beta[n] += 1.0
            self.learners[n].learn_one(x, y)
        self._cache_x, self._cache = None, {}
        return self

    def selection_counts(self) -> Dict[str, int]:
        """How often each arm sat in the last selection (for the ablation tables)."""
        return {n: int(n in self._last_selected) for n in self.names}
