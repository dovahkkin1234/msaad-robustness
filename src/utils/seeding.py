"""Centralised seeding so every stage is reproducible (reviewers require this)."""
from __future__ import annotations
import os
import random

import numpy as np


def seed_everything(seed: int = 42) -> None:
    """Seed Python, NumPy and the hash seed. River models take their own seed=."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)
