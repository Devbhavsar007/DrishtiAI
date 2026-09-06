"""
Anatomical Integrity and Retinal Laterality Verification for DrishtiAI.

Implements the clinical hierarchy:
  Operator Eye Selection (Primary)
          +
  Landmark Localization (Disc & Fovea)
          ↓
  Laterality Consistency Evaluation
          ↓
  Conflict? → Flag LATERALITY_MISMATCH_SUSPECTED for Human Confirmation
  (Never silently or unilaterally overrides the operator).
"""

from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
import numpy as np
import cv2
from engine.pipeline.structures import localize_disc_fovea


@dataclass
class AnatomyResult:
    valid_anatomy: bool
    disc_center: Optional[Tuple[float, float]] = None
    disc_radius: int = 0
    fovea_center: Optional[Tuple[float, float]] = None
    inferred_laterality: str = "UNKNOWN"  # "OD" (Right Eye), "OS" (Left Eye), "UNKNOWN"
    operator_selected_eye: Optional[str] = None  # Normalized to "OD" or "OS"
    laterality_confidence: float = 0.0
    laterality_mismatch: bool = False
    human_confirmation_required: bool = False
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "valid_anatomy": self.valid_anatomy,
            "disc_center": list(self.disc_center) if self.disc_center else None,
            "disc_radius": self.disc_radius,
            "fovea_center": list(self.fovea_center) if self.fovea_center else None,
            "inferred_laterality": self.inferred_laterality,
            "operator_selected_eye": self.operator_selected_eye,
            "laterality_confidence": round(self.laterality_confidence, 3),
            "laterality_mismatch": self.laterality_mismatch,
            "human_confirmation_required": self.human_confirmation_required,
            "notes": self.notes,
        }


def _normalize_eye(eye_str: Optional[str]) -> Optional[str]:
    """Normalize user/operator eye input to standard clinical OD / OS."""
    if not eye_str:
        return None
    s = eye_str.strip().upper()
    if s in ("OD", "RIGHT", "RE", "R"):
        return "OD"
    if s in ("OS", "LEFT", "LE", "L"):
        return "OS"
    return None


def assess_anatomy_and_laterality(
    img_bgr: np.ndarray,
    operator_eye: Optional[str] = None
) -> AnatomyResult:
    """
    Assess anatomical landmark validity and check consistency with operator selection.
    """
    notes = []
    norm_operator_eye = _normalize_eye(operator_eye)

    if img_bgr is None or img_bgr.size == 0:
        return AnatomyResult(
            valid_anatomy=False,
            operator_selected_eye=norm_operator_eye,
            notes=["Empty image array provided for anatomical assessment."]
        )

    h, w = img_bgr.shape[:2]

    # 1. Localize Optic Disc and Fovea
    try:
        disc_center, disc_radius, fovea_center = localize_disc_fovea(img_bgr)
    except Exception as e:
        return AnatomyResult(
            valid_anatomy=False,
            operator_selected_eye=norm_operator_eye,
            notes=[f"Landmark localization failed: {str(e)}"]
        )

    if disc_center is None:
        return AnatomyResult(
            valid_anatomy=False,
            operator_selected_eye=norm_operator_eye,
            notes=["Optic disc could not be reliably located."]
        )

    cx, cy = disc_center
    inferred_lat = "UNKNOWN"
    confidence = 0.0

    # 2. Evaluate Laterality using Disc-Fovea spatial relationship
    if fovea_center is not None:
        fx, fy = fovea_center
        # In standard retinal imaging:
        # OD (Right Eye): Disc is Nasal (left side of macula/fovea in image coords: cx < fx)
        # OS (Left Eye):  Disc is Nasal (right side of macula/fovea in image coords: cx > fx)
        dx = cx - fx
        dist = np.hypot(cx - fx, cy - fy)
        
        # Expected disc-fovea distance is approx 2.0 to 3.5 disc diameters
        expected_dd = 2.0 * disc_radius
        if dist > 0.8 * expected_dd:
            if dx < -0.3 * expected_dd:
                inferred_lat = "OD"
                confidence = min(0.95, float(abs(dx) / (expected_dd * 2.0)))
            elif dx > 0.3 * expected_dd:
                inferred_lat = "OS"
                confidence = min(0.95, float(abs(dx) / (expected_dd * 2.0)))
            else:
                inferred_lat = "UNKNOWN"
                confidence = 0.4
                notes.append("Disc and fovea are vertically aligned; horizontal laterality indeterminate.")
    else:
        # Fallback to disc quadrant if fovea is occluded
        if cx < w * 0.45:
            inferred_lat = "OD"
            confidence = 0.65
            notes.append("Fovea not clearly defined; laterality inferred from disc position in nasal field.")
        elif cx > w * 0.55:
            inferred_lat = "OS"
            confidence = 0.65
            notes.append("Fovea not clearly defined; laterality inferred from disc position in nasal field.")

    # 3. Hierarchy Check: Compare Inferred vs Operator
    mismatch = False
    requires_confirmation = False

    if norm_operator_eye and inferred_lat != "UNKNOWN":
        if norm_operator_eye != inferred_lat and confidence >= 0.70:
            mismatch = True
            requires_confirmation = True
            notes.append(
                f"LATERALITY_MISMATCH_SUSPECTED: Operator selected {norm_operator_eye}, "
                f"but anatomical landmark orientation indicates {inferred_lat} (confidence: {confidence:.2f}). "
                "Human confirmation required before finalizing session."
            )
        else:
            notes.append(f"Laterality consistent: Operator={norm_operator_eye}, Inferred={inferred_lat}.")

    return AnatomyResult(
        valid_anatomy=True,
        disc_center=disc_center,
        disc_radius=disc_radius,
        fovea_center=fovea_center,
        inferred_laterality=inferred_lat,
        operator_selected_eye=norm_operator_eye,
        laterality_confidence=confidence,
        laterality_mismatch=mismatch,
        human_confirmation_required=requires_confirmation,
        notes=notes,
    )
