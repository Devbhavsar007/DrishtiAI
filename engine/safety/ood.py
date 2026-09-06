"""
Out-of-Distribution (OOD) and Domain Shift Monitoring for DrishtiAI.

Strictly adheres to scientific discipline:
  Level 1: Input-Domain Validation (Detects non-fundus, text, document, invalid anatomy)
  Level 2: Distribution-Shift Signal (Statistical distance against reference fundus features)
  Level 3: Decision Policy (Raises uncertainty & routes to human review; NEVER claims clinical OOD proof)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import numpy as np
import cv2


@dataclass
class OODResult:
    domain_valid: bool                     # False if non-fundus (Level 1 hard reject)
    is_ood_suspected: bool = False         # True if distribution shift detected (Level 2/3)
    ood_score: float = 0.0                 # 0.0 (in-distribution) to 1.0 (severe shift)
    rejection_reason: Optional[str] = None
    level_triggered: int = 0               # 0: In-dist, 1: Domain invalid, 2: Statistical shift
    features: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, any] = field(default_factory=lambda: {
        "method": "multivariate_heuristic_feature_shift",
        "clinically_validated": False,
        "policy": "ADVISORY_UNCERTAINTY_MULTIPLIER",
    })

    def to_dict(self) -> Dict:
        return {
            "domain_valid": self.domain_valid,
            "is_ood_suspected": self.is_ood_suspected,
            "ood_score": round(self.ood_score, 4),
            "rejection_reason": self.rejection_reason,
            "level_triggered": self.level_triggered,
            "features": {k: round(v, 4) for k, v in self.features.items()},
            "metadata": self.metadata,
        }


# Reference statistics computed across standard fundus cohorts (EyePACS / Messidor normalized)
# Used for Level 2 distribution shift scoring
REFERENCE_FUNDUS_STATS = {
    "red_mean": 128.0,
    "red_std": 48.0,
    "green_mean": 64.0,
    "green_std": 32.0,
    "blue_mean": 24.0,
    "blue_std": 20.0,
    "red_to_blue_ratio": 4.5,
    "edge_density": 0.035,
}


def evaluate_ood_signal(img_bgr: np.ndarray) -> OODResult:
    """
    Evaluate retinal image through the 3-level OOD pipeline.
    """
    if img_bgr is None or img_bgr.size == 0:
        return OODResult(
            domain_valid=False,
            rejection_reason="Empty image buffer provided.",
            level_triggered=1,
        )

    h, w, c = img_bgr.shape
    if c != 3:
        return OODResult(
            domain_valid=False,
            rejection_reason="Invalid channel count. Retinal fundus requires 3-channel RGB/BGR.",
            level_triggered=1,
        )

    # ── Level 1: Input-Domain Validation ──
    # Fundus images have a dominant red channel with much lower blue channel.
    # Non-fundus images (outdoor scenes, skin lesions, text, radiographs) violate this.
    b_mean = float(np.mean(img_bgr[:, :, 0]))
    g_mean = float(np.mean(img_bgr[:, :, 1]))
    r_mean = float(np.mean(img_bgr[:, :, 2]))

    # Aspect ratio check
    aspect = max(h, w) / max(1, min(h, w))
    if aspect > 2.5:
        return OODResult(
            domain_valid=False,
            rejection_reason=f"Extreme aspect ratio ({aspect:.2f}:1). Standard fundus imaging is approx 1:1 or 4:3.",
            level_triggered=1,
        )

    # Retinal color balance check: Red channel MUST be dominant over Blue channel
    rb_ratio = float((r_mean + 1e-4) / (b_mean + 1e-4))
    if r_mean < b_mean or rb_ratio < 1.15:
        return OODResult(
            domain_valid=False,
            rejection_reason=(
                f"Non-fundus image detected: Blue channel ({b_mean:.1f}) exceeds or closely matches "
                f"Red channel ({r_mean:.1f}). Retinal images must exhibit red/orange vascular dominance."
            ),
            level_triggered=1,
            features={"r_mean": r_mean, "g_mean": g_mean, "b_mean": b_mean, "rb_ratio": rb_ratio},
        )

    # Grayscale / monochromatic document check
    rg_diff = abs(r_mean - g_mean)
    gb_diff = abs(g_mean - b_mean)
    if rg_diff < 4.0 and gb_diff < 4.0:
        return OODResult(
            domain_valid=False,
            rejection_reason="Monochromatic or grayscale document image detected. Fundus photograph required.",
            level_triggered=1,
            features={"r_mean": r_mean, "g_mean": g_mean, "b_mean": b_mean},
        )

    # ── Level 2: Distribution-Shift Signal (Experimental) ──
    # Edge density
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = float(np.count_nonzero(edges)) / float(edges.size)

    # Compute normalized z-scores against reference fundus cohort
    z_rb = abs(rb_ratio - REFERENCE_FUNDUS_STATS["red_to_blue_ratio"]) / 2.5
    z_edges = abs(edge_density - REFERENCE_FUNDUS_STATS["edge_density"]) / 0.02
    z_green = abs(g_mean - REFERENCE_FUNDUS_STATS["green_mean"]) / REFERENCE_FUNDUS_STATS["green_std"]

    # Composite shift score (bounded [0.0, 1.0])
    raw_score = 0.4 * z_rb + 0.3 * z_edges + 0.3 * z_green
    ood_score = float(1.0 / (1.0 + np.exp(-(raw_score - 2.0))))  # Sigmoid scaling

    features = {
        "r_mean": r_mean,
        "g_mean": g_mean,
        "b_mean": b_mean,
        "rb_ratio": rb_ratio,
        "edge_density": edge_density,
        "composite_z": raw_score,
    }

    # ── Level 3: Decision Policy ──
    # Score > 0.70 flags advisory distribution shift
    is_shift = ood_score > 0.70

    return OODResult(
        domain_valid=True,
        is_ood_suspected=is_shift,
        ood_score=ood_score,
        level_triggered=2 if is_shift else 0,
        features=features,
    )
