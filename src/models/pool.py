"""Layer-2 classifier pool: the five online learners from the base paper.

ARF-ADWIN, ARF-DDM, SRP-ADWIN, SRP-DDM (River) and KNN-ADWIN (rebuilt, see knn_adwin.py).
Configs match the paper where stated: ARF/SRP use 3 base trees; KNN uses k=5, window=100.

Documented reproduction assumptions:
  * DDM lives under river.drift.binary in recent River; we import it from there.
  * KNN-ADWIN no longer exists in River; src/models/knn_adwin.py rebuilds its behaviour
    (exact k-NN over a 100-sample window + ADWIN-driven window shrinking).
No silent fallbacks: if the installed River API differs, construction fails loudly.
"""
from __future__ import annotations

from typing import Dict

from river import drift, ensemble, forest

from .knn_adwin import KNNADWIN


def _make_ddm():
    """DDM moved to river.drift.binary (River >= 0.17); older versions had drift.DDM."""
    try:
        from river.drift.binary import DDM
    except ImportError:  # pragma: no cover - only on old River
        from river.drift import DDM  # type: ignore[attr-defined,no-redef]
    return DDM()


def build_pool(seed: int = 42, n_trees: int = 3, knn_window: int = 100) -> Dict[str, object]:
    """Return the five named learners as a dict (insertion order = paper order)."""
    pool: Dict[str, object] = {}
    pool["ARF-ADWIN"] = forest.ARFClassifier(
        n_models=n_trees, drift_detector=drift.ADWIN(),
        warning_detector=drift.ADWIN(), seed=seed,
    )
    pool["ARF-DDM"] = forest.ARFClassifier(
        n_models=n_trees, drift_detector=_make_ddm(),
        warning_detector=_make_ddm(), seed=seed,
    )
    pool["SRP-ADWIN"] = ensemble.SRPClassifier(
        n_models=n_trees, drift_detector=drift.ADWIN(),
        warning_detector=drift.ADWIN(), seed=seed,
    )
    pool["SRP-DDM"] = ensemble.SRPClassifier(
        n_models=n_trees, drift_detector=_make_ddm(),
        warning_detector=_make_ddm(), seed=seed,
    )
    pool["KNN-ADWIN"] = KNNADWIN(n_neighbors=5, window_size=knn_window)
    return pool


def drift_counts(learners: Dict[str, object]) -> Dict[str, int]:
    """Drifts detected so far by each learner (ARF: trees reset; SRP: members reset;
    KNN-ADWIN: window shrinks). Used to log how often an attack trips the adaptation loop."""
    out: Dict[str, int] = {}
    for name, m in learners.items():
        if hasattr(m, "n_drifts_detected") and callable(m.n_drifts_detected):   # ARF
            out[name] = int(m.n_drifts_detected())
        elif isinstance(m, KNNADWIN):
            out[name] = int(m.n_shrinks)
        else:                                                                     # SRP members
            try:
                out[name] = int(sum(int(getattr(member, "n_drifts_detected", 0) or 0) for member in m))
            except TypeError:
                out[name] = 0
    return out
