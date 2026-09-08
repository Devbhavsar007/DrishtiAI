"""Active learning subpackage — uncertainty, prioritization, sampling queue."""

from ml_platform.active_learning.prioritization import (
    ActiveLearningCandidate,
    prioritize_candidates,
    build_active_learning_queue,
    compute_entropy,
)
from ml_platform.active_learning.uncertainty import (
    shannon_entropy,
    margin_sampling,
    least_confidence,
    ensemble_disagreement,
)

__all__ = [
    "ActiveLearningCandidate",
    "prioritize_candidates",
    "build_active_learning_queue",
    "compute_entropy",
    "shannon_entropy",
    "margin_sampling",
    "least_confidence",
    "ensemble_disagreement",
]
