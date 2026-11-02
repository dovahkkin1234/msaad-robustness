"""Binary streaming metrics (positive class = 1 = attack/DDoS).

Cumulative accuracy, precision, recall, F1 (the paper's table columns) plus a rolling
accuracy window for the learning curve. End-to-end attack-success / benign-drop metrics
are added in the robustness stage; this module is the clean baseline set.
"""
from __future__ import annotations

import collections
from dataclasses import dataclass, field


@dataclass
class BinaryMetrics:
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    n: int = 0
    _window: collections.deque = field(default_factory=lambda: collections.deque(maxlen=1000))

    def update(self, y_true: int, y_pred: int | None) -> None:
        if y_pred is None:
            y_pred = 0  # count an abstention as benign (conservative for a detector)
        self.n += 1
        self._window.append(1 if y_pred == y_true else 0)
        if y_true == 1 and y_pred == 1:
            self.tp += 1
        elif y_true == 0 and y_pred == 1:
            self.fp += 1
        elif y_true == 0 and y_pred == 0:
            self.tn += 1
        else:
            self.fn += 1

    @property
    def accuracy(self) -> float:
        tot = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.tn) / tot if tot else 0.0

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 0.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def rolling_accuracy(self) -> float:
        return sum(self._window) / len(self._window) if self._window else 0.0

    @property
    def fpr(self) -> float:
        """False-alarm rate: share of BENIGN samples flagged as attack."""
        d = self.fp + self.tn
        return self.fp / d if d else 0.0

    @property
    def attack_share(self) -> float:
        tot = self.tp + self.fp + self.tn + self.fn
        return (self.tp + self.fn) / tot if tot else 0.0

    def as_dict(self) -> dict:
        share = self.attack_share
        return {
            "n": self.n,
            "accuracy": round(100 * self.accuracy, 2),
            "precision": round(100 * self.precision, 2),
            "recall": round(100 * self.recall, 2),
            "f1": round(100 * self.f1, 2),
            # What accuracy hides on imbalanced IDS data:
            "fpr": round(100 * self.fpr, 2),                 # % of benign flagged as attack
            "tp": self.tp, "fp": self.fp, "tn": self.tn, "fn": self.fn,
            "attack_share": round(100 * share, 2),
            "majority_accuracy": round(100 * max(share, 1 - share), 2),  # "always guess the majority"
        }
