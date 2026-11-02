"""The attacker's differentiable stand-in (surrogate model).

FGSM, BIM, PGD and C&W need gradients of the model with respect to its input. MABTSE's
learners (Hoeffding-tree ensembles and k-NN) have none, so — as the base paper must have
done without saying so — the attacker trains a differentiable model on the same features,
crafts perturbations against it, and transfers them to MABTSE.

Two surrogates, both fitted with scikit-learn and differentiated analytically in NumPy
(no deep-learning framework needed):
  * "lr"  – logistic regression
  * "mlp" – a ReLU multi-layer perceptron with a logistic output (default 64-32)

Inputs are the min-max-scaled feature vectors; missing features (NaN) are treated as 0.
"""
from __future__ import annotations

from typing import List, Sequence

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier


def sigmoid(z: np.ndarray) -> np.ndarray:
    """Numerically stable logistic function."""
    return 0.5 * (1.0 + np.tanh(0.5 * z))


class Surrogate:
    def __init__(self, kind: str = "mlp", hidden: Sequence[int] = (64, 32),
                 seed: int = 42, max_iter: int = 300) -> None:
        if kind not in ("mlp", "lr"):
            raise ValueError(f"surrogate kind must be 'mlp' or 'lr', got {kind!r}")
        self.kind, self.hidden, self.seed, self.max_iter = kind, tuple(hidden), seed, max_iter
        self.Ws: List[np.ndarray] = []
        self.bs: List[np.ndarray] = []

    # ---- training ---------------------------------------------------------------------
    def fit(self, X: np.ndarray, y: np.ndarray) -> "Surrogate":
        X = np.nan_to_num(np.asarray(X, dtype=float))
        y = np.asarray(y).astype(int)
        if len(np.unique(y)) < 2:
            raise ValueError("the surrogate needs both classes in its training data "
                             "(check the stream order and train_frac)")
        if self.kind == "lr":
            clf = LogisticRegression(max_iter=5000, random_state=self.seed).fit(X, y)
            self.Ws = [clf.coef_.T.astype(float)]
            self.bs = [clf.intercept_.astype(float)]
        else:
            clf = MLPClassifier(hidden_layer_sizes=self.hidden, activation="relu",
                                random_state=self.seed, max_iter=self.max_iter,
                                early_stopping=True, n_iter_no_change=10).fit(X, y)
            if getattr(clf, "out_activation_", "logistic") != "logistic":
                raise RuntimeError("expected a binary MLP with a logistic output unit")
            self.Ws = [w.astype(float) for w in clf.coefs_]
            self.bs = [b.astype(float) for b in clf.intercepts_]
        if list(clf.classes_) != [0, 1]:
            raise RuntimeError(f"unexpected class order {clf.classes_}")
        self.clf_ = clf
        return self

    # ---- forward / backward -----------------------------------------------------------
    def _forward(self, X: np.ndarray):
        """Return the output logit (n,) and the hidden pre-activations (for backprop)."""
        a = np.nan_to_num(np.asarray(X, dtype=float))
        pre = []
        for W, b in zip(self.Ws[:-1], self.bs[:-1]):
            p = a @ W + b
            pre.append(p)
            a = np.maximum(p, 0.0)
        z = (a @ self.Ws[-1] + self.bs[-1])[:, 0]
        return z, pre

    def logit(self, X: np.ndarray) -> np.ndarray:
        return self._forward(X)[0]

    def proba(self, X: np.ndarray) -> np.ndarray:
        """P(attack) for each row."""
        return sigmoid(self.logit(X))

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.logit(X) > 0).astype(int)

    def grad_logit(self, X: np.ndarray) -> np.ndarray:
        """d logit / d x for each row, shape (n, d)."""
        z, pre = self._forward(X)
        g = np.repeat(self.Ws[-1][:, 0][None, :], len(z), axis=0)  # d z / d a_last
        for W, p in zip(reversed(self.Ws[:-1]), reversed(pre)):
            g = (g * (p > 0)) @ W.T
        return g

    def loss_grad(self, X: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Gradient of the binary cross-entropy loss w.r.t. the input, shape (n, d)."""
        z = self.logit(X)
        return (sigmoid(z) - np.asarray(y, dtype=float))[:, None] * self.grad_logit(X)

    def accuracy(self, X: np.ndarray, y: np.ndarray) -> float:
        return float(np.mean(self.predict(X) == np.asarray(y).astype(int)))
