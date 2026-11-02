"""RADP — the base paper's Layer 1: Resilient Adversarial Detection and Purification.

What the paper specifies (Sec. III-B and the evaluation procedures 2-6 of Sec. IV-C):
  * MSAPG (multi-source adversarial perturbation generator) crafts adversarial samples with
    FGSM, BIM, PGD and C&W (ART defaults, eps 0.1);
  * a GAN "mimics crafted adversarial samples";
  * RAD, the detector, is "the same online model", trained on the original training data
    plus adversarial samples "to distinguish between adversarial samples and the original
    dataset";
  * purification removes ("prunes") every data point RAD flags.

Documented assumptions (the paper leaves these open):
  A1 The defender crafts its MSAPG samples on ITS OWN surrogate (same architecture as the
     attacker's, a different seed) from its own clean training flows. It never sees the
     attacker's model or the test-time perturbations.
  A2 MSAPG perturbs benign and DDoS training flows alike (untargeted, like the paper's
     attacks), so RAD learns "perturbed vs clean", not "DDoS vs benign".
  A3 RAD is a fresh MABTSE (the same five-learner pool, Thompson Sampling and AUWPAE)
     trained learn-only on a shuffled, balanced mix: clean flows (label 0) vs MSAPG + GAN
     samples (label 1). It is frozen on the test stream (no "adversarial" labels exist there).
  A4 A purified (deleted) flow never reaches the DDoS detector. We report both readings:
     deleted = blocked (counts as a DDoS verdict), and the paper's accuracy on survivors.
"""
from __future__ import annotations

from typing import Dict, Optional, Sequence, Tuple

import numpy as np

from ..attacks.evasion import run_attack
from ..attacks.surrogate import Surrogate
from ..data.matrix import to_dict
from ..models.mabtse import MABTSE
from ..models.pool import build_pool


def msapg(sur: Surrogate, S: np.ndarray, y: np.ndarray, attacks: Sequence[str], eps: float,
          params: Dict[str, dict], seed: int) -> Dict[str, np.ndarray]:
    """Every row perturbed by every attack, on the defender's own surrogate (A1, A2)."""
    rows = np.ones(len(y), dtype=bool)
    return {a: run_attack(a, sur, S, y, rows, eps, params=params.get(a), seed=seed) for a in attacks}


def training_mix(S_clean: np.ndarray, adv: Dict[str, np.ndarray], known: Sequence[str],
                 gan_rows: Optional[np.ndarray], rng: np.random.Generator
                 ) -> Tuple[np.ndarray, np.ndarray]:
    """Balanced, shuffled RAD training data: clean (0) vs MSAPG (+ GAN) samples (1)."""
    n = len(S_clean)
    n_gan = 0 if gan_rows is None else min(len(gan_rows), n // 2)
    per = max(1, (n - n_gan) // len(known))
    parts = []
    for a in known:
        A = adv[a]
        parts.append(A[rng.choice(len(A), size=min(per, len(A)), replace=False)])
    if n_gan:
        parts.append(gan_rows[:n_gan])
    P = np.vstack(parts)
    X = np.vstack([S_clean, P])
    y = np.r_[np.zeros(len(S_clean), dtype=int), np.ones(len(P), dtype=int)]
    order = rng.permutation(len(y))
    return X[order], y[order]


def with_missing_like(G: np.ndarray, source: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Give GAN rows the missing-value pattern of random real rows (no 'feature present' tell)."""
    masks = np.isnan(source[rng.integers(0, len(source), len(G))])
    return np.where(masks, np.nan, G)


def train_rad(X: np.ndarray, y: np.ndarray, names: Sequence[str], cfg: dict, seed: int) -> MABTSE:
    rad = MABTSE(build_pool(seed=seed), top_k=cfg["top_k"], eps=cfg["eps"],
                 mse_window=cfg["mse_window"], seed=seed)
    for i in range(len(y)):
        rad.learn_one(to_dict(X[i], names), int(y[i]))
    return rad


def flag(rad: MABTSE, S: np.ndarray, names: Sequence[str]) -> np.ndarray:
    """RAD's verdict for each row (True = adversarial -> deleted). RAD stays frozen."""
    out = np.zeros(len(S), dtype=bool)
    for i in range(len(S)):
        out[i] = rad.predict_one(to_dict(S[i], names)) == 1
    return out
