"""Uncertainty estimation methods for Active Learning.

Implements information-theoretic and margin-based sampling strategies:
  - Shannon Entropy: H(p) = -sum(p * log(p))
  - Margin Sampling: difference between top-1 and top-2 probabilities
  - Least Confidence: 1 - max(p)
  - Ensemble / Multi-model Disagreement (variation ratio)
"""

from __future__ import annotations

import math
from typing import Sequence


def shannon_entropy(probs: Sequence[float]) -> float:
    """
    Compute normalized Shannon entropy for a probability distribution.
    Returns float in [0.0, 1.0].
    """
    clean_p = [p for p in probs if p > 1e-9]
    if len(clean_p) <= 1:
        return 0.0

    raw_entropy = -sum(p * math.log(p) for p in clean_p)
    max_entropy = math.log(len(probs))
    normalized = float(raw_entropy / max_entropy) if max_entropy > 0 else 0.0
    return float(max(0.0, min(1.0, normalized)))



def margin_sampling(probs: Sequence[float]) -> float:
    """
    Compute margin score: 1.0 - (p_top1 - p_top2).
    Small difference between top two classes indicates high uncertainty.
    Returns float in [0.0, 1.0] where 1.0 is highest uncertainty.
    """
    if len(probs) < 2:
        return 0.0
    sorted_probs = sorted(probs, reverse=True)
    margin = sorted_probs[0] - sorted_probs[1]
    return float(max(0.0, min(1.0, 1.0 - margin)))


def least_confidence(probs: Sequence[float]) -> float:
    """
    Compute least confidence score: (1.0 - max(probs)) * (K / (K - 1))
    Normalized so 1.0 indicates maximum uncertainty (uniform distribution).
    """
    k = len(probs)
    if k <= 1:
        return 0.0
    max_p = max(probs) if probs else 0.0
    normalized = (1.0 - max_p) * (k / (k - 1))
    return float(max(0.0, min(1.0, normalized)))


def ensemble_disagreement(model_predictions: Sequence[int | str]) -> float:
    """
    Compute variation ratio across multiple model predictions or MC-Dropout samples.
    Variation ratio = 1 - (frequency of modal prediction / N).
    """
    if not model_predictions:
        return 0.0
    n = len(model_predictions)
    counts: dict[int | str, int] = {}
    for pred in model_predictions:
        counts[pred] = counts.get(pred, 0) + 1
    modal_count = max(counts.values())
    return float(1.0 - (modal_count / n))
