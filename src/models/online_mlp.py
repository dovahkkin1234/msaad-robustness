"""A small online MLP (PyTorch), the second stage of the detector chain.

Why our own and not deep-river: deep-river 0.2.7 pins River 0.21, numpy 1.26 and torch 2.2,
which would change the River version every other result in this repository was produced
with. This class follows the same idea (a PyTorch module trained one sample at a time,
River-style predict/learn) on the scaled feature vector the other learners see.

Design: d -> 64 -> 32 -> 1 (ReLU), logistic output, Adam (lr 1e-3), one gradient step per
learned flow, class-balanced binary cross-entropy (running class counts, weights clipped to
[0.1, 10]) because DDoS dominates both datasets. Missing features (NaN) are fed as 0.
Deterministic: seeded initialisation, one CPU thread, deterministic algorithms.
"""
from __future__ import annotations

import numpy as np
import torch
from torch import nn


def torch_setup(seed: int) -> None:
    """Reproducible single-thread CPU torch (several runs share the laptop's cores)."""
    torch.manual_seed(int(seed))
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


class OnlineMLP:
    def __init__(self, n_features: int, hidden=(64, 32), lr: float = 1e-3, seed: int = 0) -> None:
        g = torch.Generator().manual_seed(int(seed))
        layers, d = [], n_features
        for h in hidden:
            lin = nn.Linear(d, h)
            nn.init.kaiming_uniform_(lin.weight, a=0.0, generator=g)
            nn.init.zeros_(lin.bias)
            layers += [lin, nn.ReLU()]
            d = h
        out = nn.Linear(d, 1)
        nn.init.xavier_uniform_(out.weight, generator=g)
        nn.init.zeros_(out.bias)
        self.net = nn.Sequential(*layers, out)
        self.opt = torch.optim.Adam(self.net.parameters(), lr=lr)
        self.counts = np.ones(2)            # running class counts (Laplace prior)
        self.n_features = n_features

    @staticmethod
    def _vec(v) -> torch.Tensor:
        a = np.nan_to_num(np.asarray(v, dtype=np.float32), nan=0.0)
        return torch.from_numpy(a).reshape(1, -1)

    def predict_proba(self, v) -> float:
        """P(DDoS) for one scaled feature vector."""
        with torch.no_grad():
            return float(torch.sigmoid(self.net(self._vec(v))).item())

    def predict_proba_many(self, V: np.ndarray) -> np.ndarray:
        with torch.no_grad():
            a = torch.from_numpy(np.nan_to_num(np.asarray(V, dtype=np.float32), nan=0.0))
            return torch.sigmoid(self.net(a)).squeeze(1).numpy().astype(float)

    def learn(self, v, y: int, weight: float = 1.0) -> None:
        """One Adam step on (v, y); weight multiplies the loss (importance weighting)."""
        y = int(y)
        self.counts[y] += 1.0
        cw = float(np.clip(self.counts.sum() / (2.0 * self.counts[y]), 0.1, 10.0))
        self.opt.zero_grad()
        logit = self.net(self._vec(v)).squeeze()
        loss = nn.functional.binary_cross_entropy_with_logits(logit, torch.tensor(float(y))) * (cw * float(weight))
        loss.backward()
        self.opt.step()

    def n_params(self) -> int:
        return int(sum(p.numel() for p in self.net.parameters()))
