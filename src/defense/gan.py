"""A small tabular GAN in plain NumPy (no deep-learning framework needed).

Used by RADP, the base paper's Layer 1: its adversarial detector (RAD) is trained on GAN
samples that "mimic crafted adversarial samples", next to the crafted samples themselves.
The paper does not describe its GAN, so we use a standard one (documented assumption):

  generator       z ~ N(0, I_32) -> 128 -> 128 -> d   LeakyReLU(0.2) hidden, sigmoid output
  discriminator   x -> 128 -> 64 -> 1                 LeakyReLU(0.2) hidden, logit output
  losses          D: binary cross-entropy (real = 1, fake = 0); G: non-saturating -log D(G(z))
  optimiser       Adam (lr 2e-4, beta1 0.5, beta2 0.999), batch 128, 3,000 steps

For training, every feature is min-max rescaled to [0, 1] on the GAN's own training data
(missing values imputed with the feature median); samples are mapped back to the original
scale, and features that are constant in the training data are returned as that constant.
Features with only a few distinct values in the training data (flags, counts, categories:
at most ``discrete_max``) are snapped to the nearest value actually seen, as tabular GANs
usually do for discrete columns — otherwise a sigmoid output yields impossible in-between
values that give every generated row away. Likewise, values a feature takes very often
(point masses such as exact zeros, at least ``mass_min`` of the rows) attract generated
values lying within ``mass_tol`` of the feature's range.

``fidelity`` reports a classifier two-sample test: a random forest tries to tell real from
generated rows on held-out data. ROC AUC 0.5 = indistinguishable, 1.0 = trivially apart.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple

import numpy as np
from scipy.special import expit


class Dense:
    """One fully connected layer with Glorot-uniform initialisation."""

    def __init__(self, n_in: int, n_out: int, rng: np.random.Generator) -> None:
        lim = np.sqrt(6.0 / (n_in + n_out))
        self.W = rng.uniform(-lim, lim, size=(n_in, n_out))
        self.b = np.zeros(n_out)


class MLP:
    """LeakyReLU hidden layers, linear output, hand-written backpropagation."""

    def __init__(self, sizes: Sequence[int], rng: np.random.Generator, slope: float = 0.2) -> None:
        self.layers = [Dense(a, b, rng) for a, b in zip(sizes[:-1], sizes[1:])]
        self.slope = slope

    def forward(self, X: np.ndarray) -> Tuple[np.ndarray, list]:
        cache, h = [], X
        last = len(self.layers) - 1
        for i, L in enumerate(self.layers):
            z = h @ L.W + L.b
            cache.append((h, z))
            h = z if i == last else np.where(z > 0, z, self.slope * z)
        return h, cache

    def backward(self, grad_out: np.ndarray, cache: list) -> Tuple[List[np.ndarray], np.ndarray]:
        """Return ([dW0, db0, dW1, db1, ...], dLoss/dInput) for dLoss/dOutput = grad_out."""
        grads: List[np.ndarray] = [None] * (2 * len(self.layers))  # type: ignore[list-item]
        g = grad_out
        last = len(self.layers) - 1
        for i in range(last, -1, -1):
            h, z = cache[i]
            if i != last:
                g = g * np.where(z > 0, 1.0, self.slope)
            grads[2 * i] = h.T @ g
            grads[2 * i + 1] = g.sum(axis=0)
            g = g @ self.layers[i].W.T
        return grads, g

    def params(self) -> List[np.ndarray]:
        return [p for L in self.layers for p in (L.W, L.b)]


class Adam:
    def __init__(self, params: List[np.ndarray], lr: float = 2e-4, b1: float = 0.5,
                 b2: float = 0.999, eps: float = 1e-8) -> None:
        self.params, self.lr, self.b1, self.b2, self.eps = params, lr, b1, b2, eps
        self.m = [np.zeros_like(p) for p in params]
        self.v = [np.zeros_like(p) for p in params]
        self.t = 0

    def step(self, grads: List[np.ndarray]) -> None:
        self.t += 1
        c1, c2 = 1 - self.b1 ** self.t, 1 - self.b2 ** self.t
        for p, g, m, v in zip(self.params, grads, self.m, self.v):
            m *= self.b1
            m += (1 - self.b1) * g
            v *= self.b2
            v += (1 - self.b2) * g * g
            p -= self.lr * (m / c1) / (np.sqrt(v / c2) + self.eps)


def _softplus(x: np.ndarray) -> np.ndarray:
    return np.logaddexp(0.0, x)


class TabularGAN:
    def __init__(self, z_dim: int = 32, g_hidden: Sequence[int] = (128, 128),
                 d_hidden: Sequence[int] = (128, 64), lr: float = 2e-4, batch: int = 128,
                 steps: int = 3000, seed: int = 42, discrete_max: int = 10,
                 mass_min: float = 0.02, mass_tol: float = 0.01) -> None:
        self.z_dim, self.g_hidden, self.d_hidden = z_dim, tuple(g_hidden), tuple(d_hidden)
        self.lr, self.batch, self.steps, self.seed = lr, batch, steps, seed
        self.discrete_max, self.mass_min, self.mass_tol = discrete_max, mass_min, mass_tol
        self.history: List[Tuple[int, float, float]] = []

    # ---- data scaling ----------------------------------------------------------------
    def _prep(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        med = np.nanmedian(np.where(np.isfinite(X), X, np.nan), axis=0)
        med = np.where(np.isnan(med), 0.0, med)
        X = np.where(np.isfinite(X), X, med)
        self.lo_ = X.min(axis=0)
        self.span_ = X.max(axis=0) - self.lo_
        self.const_ = self.span_ <= 0
        self.levels_, self.masses_ = {}, {}
        for j in range(X.shape[1]):
            vals, counts = np.unique(X[:, j], return_counts=True)
            if 1 < len(vals) <= self.discrete_max:
                self.levels_[j] = vals
            elif len(vals) > 1:
                heavy = vals[counts >= max(2, self.mass_min * len(X))]
                if len(heavy):
                    self.masses_[j] = heavy
        return np.where(self.const_, 0.0, (X - self.lo_) / np.where(self.const_, 1.0, self.span_))

    def _unscale(self, U: np.ndarray) -> np.ndarray:
        out = np.where(self.const_, self.lo_, self.lo_ + U * self.span_)
        for j, vals in self.levels_.items():
            out[:, j] = vals[np.abs(out[:, j][:, None] - vals[None, :]).argmin(axis=1)]
        for j, vals in self.masses_.items():
            dist = np.abs(out[:, j][:, None] - vals[None, :])
            near = dist.argmin(axis=1)
            close = dist[np.arange(len(out)), near] <= self.mass_tol * self.span_[j]
            out[close, j] = vals[near[close]]
        return out

    # ---- training --------------------------------------------------------------------
    def fit(self, X: np.ndarray) -> "TabularGAN":
        Xn = self._prep(X)
        n, d = Xn.shape
        if n < 2:
            raise ValueError("the GAN needs at least two training rows")
        rng = np.random.default_rng(self.seed)
        self.G = MLP([self.z_dim, *self.g_hidden, d], rng)
        self.D = MLP([d, *self.d_hidden, 1], rng)
        opt_g, opt_d = Adam(self.G.params(), lr=self.lr), Adam(self.D.params(), lr=self.lr)
        b = min(self.batch, n)
        for step in range(1, self.steps + 1):
            # Discriminator: real -> 1, fake -> 0.
            real = Xn[rng.integers(0, n, b)]
            fake = expit(self.G.forward(rng.standard_normal((b, self.z_dim)))[0])
            l_r, c_r = self.D.forward(real)
            l_f, c_f = self.D.forward(fake)
            g_r, _ = self.D.backward((expit(l_r) - 1.0) / b, c_r)
            g_f, _ = self.D.backward(expit(l_f) / b, c_f)
            opt_d.step([a + c for a, c in zip(g_r, g_f)])
            # Generator: make D call its samples real (non-saturating loss).
            o, c_g = self.G.forward(rng.standard_normal((b, self.z_dim)))
            fake = expit(o)
            l_f2, c_f2 = self.D.forward(fake)
            _, dx = self.D.backward((expit(l_f2) - 1.0) / b, c_f2)
            g_g, _ = self.G.backward(dx * fake * (1.0 - fake), c_g)
            opt_g.step(g_g)
            if step % 500 == 0 or step == self.steps:
                d_loss = float(_softplus(-l_r).mean() + _softplus(l_f).mean())
                g_loss = float(_softplus(-l_f2).mean())
                self.history.append((step, round(d_loss, 4), round(g_loss, 4)))
        self._rng = np.random.default_rng(self.seed + 1)
        return self

    def sample(self, n: int) -> np.ndarray:
        U = expit(self.G.forward(self._rng.standard_normal((n, self.z_dim)))[0])
        return self._unscale(U)

    # ---- quality check ---------------------------------------------------------------
    def fidelity(self, X_real: np.ndarray, n: int = 2000, seed: int = 0) -> dict:
        """Classifier two-sample test on held-out rows, plus a spread (mode-collapse) check."""
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import roc_auc_score

        rng = np.random.default_rng(seed)
        R = np.asarray(X_real, dtype=float)
        R = R[rng.permutation(len(R))[: min(n, len(R))]]
        med = np.nanmedian(np.where(np.isfinite(R), R, np.nan), axis=0)
        R = np.where(np.isfinite(R), R, np.where(np.isnan(med), 0.0, med))
        F = self.sample(len(R))
        X = np.vstack([R, F])
        y = np.r_[np.zeros(len(R)), np.ones(len(F))]
        idx = rng.permutation(len(X))
        half = len(X) // 2
        tr, te = idx[:half], idx[half:]
        clf = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=seed, n_jobs=1)
        clf.fit(X[tr], y[tr])
        auc = roc_auc_score(y[te], clf.predict_proba(X[te])[:, 1])
        sr, sf = R.std(axis=0), F.std(axis=0)
        ok = sr > 1e-12
        ratio = float(np.median(sf[ok] / sr[ok])) if ok.any() else None
        return {"c2st_auc": round(float(auc), 4),
                "std_ratio_median": None if ratio is None else round(ratio, 3),
                "final_losses": self.history[-1] if self.history else None}
