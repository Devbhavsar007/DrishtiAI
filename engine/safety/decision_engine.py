"""
Centralized Safety Decision Engine for DrishtiAI.

Consolidates all safety and risk signals into a single deterministic arbitration pipeline:
  Image Quality + Domain Validity + Landmark Laterality + Model Confidence + Multi-Model Agreement
                        ↓
             SAFETY DECISION ENGINE
                        ↓
  { screening_eligibility, safety_state, automation_level, human_review_required, reason_codes }
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from .image_validator import ImageValidationResult
from .anatomy import AnatomyResult
from .ood import OODResult

SAFETY_POLICY_VERSION = "SAFE-1.0"
TRIAGE_POLICY_VERSION = "TRIAGE-1.1"

# Default parameterized thresholds (can be overridden via config)
DEFAULT_THRESHOLDS = {
    "min_confidence": 70.0,
    "model_disagreement_stage_delta": 2,
    "ood_score_threshold": 0.70,
}


@dataclass
class SafetyEvaluationResult:
    screening_eligibility: str          # "ELIGIBLE", "INELIGIBLE", "REQUIRES_CONFIRMATION"
    safety_state: str                   # "VERIFIED", "UNCERTAIN", "BLOCKED", "REJECTED"
    automation_level: str               # "AUTOMATED_ASSISTANCE", "HUMAN_REVIEW_REQUIRED", "HUMAN_CONFIRMED", "UNABLE_TO_CLASSIFY"
    human_review_required: bool
    confidence_score: float
    clinical_action_allowed: bool = False
    safety_policy_version: str = SAFETY_POLICY_VERSION
    triage_policy_version: str = TRIAGE_POLICY_VERSION
    reason_codes: List[str] = field(default_factory=list)
    mitigation_instructions: Optional[str] = None
    audit_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        """Backwards-compatibility status string for clinical callers."""
        if self.safety_state in ("REJECTED", "ANATOMY_FAILED", "QUALITY_FAILED"):
            return "RETAKE_REQUIRED"
        if self.safety_state in ("UNCERTAIN", "BLOCKED", "MODEL_FAILURE", "LATERALITY_CONFLICT", "OOD_REVIEW") or self.human_review_required or not self.clinical_action_allowed:
            return "UNCERTAIN"
        return "PROCEED"

    @property
    def overall_quality_score(self) -> float:
        return float(self.audit_metadata.get("quality_score", 0.95))

    @property
    def model_confidence(self) -> float:
        return self.confidence_score

    @property
    def reasons(self) -> List[str]:
        res = list(self.reason_codes)
        if not res and self.safety_state == "VERIFIED":
            res.append("SCREENING_VALID")
        return res

    @property
    def retake_guidance(self) -> Optional[str]:
        return self.mitigation_instructions

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screening_eligibility": self.screening_eligibility,
            "safety_state": self.safety_state,
            "automation_level": self.automation_level,
            "clinical_action_allowed": self.clinical_action_allowed,
            "human_review_required": self.human_review_required,
            "confidence_score": round(self.confidence_score, 3),
            "safety_policy_version": self.safety_policy_version,
            "triage_policy_version": self.triage_policy_version,
            "reason_codes": self.reason_codes,
            "mitigation_instructions": self.mitigation_instructions,
            "audit_metadata": self.audit_metadata,
        }


class SafetyDecisionEngine:
    """
    Central authoritative safety arbitrator for DrishtiAI.
    Separates evidence collection (probabilistic AI) from decision policy (deterministic).
    """

    def __init__(self, thresholds: Optional[Dict[str, Any]] = None):
        self.thresholds = dict(DEFAULT_THRESHOLDS)
        if thresholds:
            self.thresholds.update(thresholds)

    def evaluate(
        self,
        image_val: ImageValidationResult,
        anatomy_res: Optional[AnatomyResult] = None,
        ood_res: Optional[OODResult] = None,
        primary_detection: Optional[Dict[str, Any]] = None,
        secondary_detection: Optional[Dict[str, Any]] = None,
        quality_assessment: Optional[Dict[str, Any]] = None,
        operator_id: Optional[str] = None,
        patient_id: Optional[str] = None,
    ) -> SafetyEvaluationResult:
        """
        Arbitrate all clinical, image, and model signals into a deterministic decision.
        """
        audit_meta = {
            "operator_id": operator_id,
            "patient_id": patient_id,
            "thresholds": self.thresholds,
        }

        # ── Gate 0: Image Quality Assessment (IQA Gate) ──
        if quality_assessment:
            q_dec = str(quality_assessment.get("decision", "ACCEPT")).upper()
            q_score = float(quality_assessment.get("quality_score", 0.85))
            audit_meta["quality_score"] = q_score
            if q_dec == "REJECT" or q_score < 0.40:
                feedback = quality_assessment.get("feedback", [])
                reasons = ["QUALITY_REJECTED"]
                if feedback:
                    reasons.extend([f"IQA_{f.upper().replace(' ', '_')}" for f in feedback])
                    guidance = "Fundus image quality is insufficient for screening: " + "; ".join(feedback)
                else:
                    guidance = "Image blur or illumination is below clinical diagnostic thresholds. Please recapture."
                return SafetyEvaluationResult(
                    screening_eligibility="INELIGIBLE",
                    safety_state="REJECTED",
                    automation_level="UNABLE_TO_CLASSIFY",
                    human_review_required=True,
                    confidence_score=float(primary_detection.get("confidence", 0.0)) if primary_detection else 0.0,
                    reason_codes=sorted(list(set(reasons))),
                    mitigation_instructions=guidance,
                    audit_metadata=audit_meta,
                )

        # ── Gate 1: Hard Image Validation Failures ──
        if not image_val.valid:
            return SafetyEvaluationResult(
                screening_eligibility="INELIGIBLE",
                safety_state="REJECTED",
                automation_level="UNABLE_TO_CLASSIFY",
                human_review_required=True,
                confidence_score=0.0,
                reason_codes=["IMAGE_VALIDATION_FAILED"],
                mitigation_instructions=image_val.error or "Uploaded image failed basic validation checks.",
                audit_metadata=audit_meta,
            )

        # ── Gate 2: Non-Fundus Domain Invalidation ──
        if ood_res and not ood_res.domain_valid:
            return SafetyEvaluationResult(
                screening_eligibility="INELIGIBLE",
                safety_state="REJECTED",
                automation_level="UNABLE_TO_CLASSIFY",
                human_review_required=True,
                confidence_score=0.0,
                reason_codes=["NON_FUNDUS_REJECTED"],
                mitigation_instructions=ood_res.rejection_reason or "Non-retinal image detected. Please provide a standard retinal fundus photograph.",
                audit_metadata=audit_meta,
            )

        # ── Gate 2b: Retinal Landmark & Anatomy Integrity Gate ──
        if anatomy_res:
            valid_anat = getattr(anatomy_res, "valid_anatomy", None)
            if valid_anat is None and isinstance(anatomy_res, dict):
                valid_anat = anatomy_res.get("valid_anatomy", True)
            if valid_anat is False:
                reasons = ["ANATOMY_DETECTION_FAILED"]
                notes = getattr(anatomy_res, "notes", []) if not isinstance(anatomy_res, dict) else anatomy_res.get("notes", [])
                for note in notes:
                    if "ORIENTATION_ANOMALY" in note or "ORIENTATION_UNCERTAIN" in note or "ROTATION" in note:
                        reasons.append("ORIENTATION_ANOMALY_SUSPECTED")
                    elif "boundary" in note.lower():
                        reasons.append("LANDMARK_OUT_OF_BOUNDS")
                    elif "overlap" in note.lower() or "separation" in note.lower():
                        reasons.append("LANDMARK_GEOMETRY_IMPLAUSIBLE")
                guidance = (
                    "Retinal anatomical landmarks (optic disc/fovea) could not be reliably established. "
                    "Image may be ungradeable, misaligned, or off-center. Retake or ophthalmology review required."
                )
                return SafetyEvaluationResult(
                    screening_eligibility="INELIGIBLE",
                    safety_state="ANATOMY_FAILED",
                    automation_level="UNABLE_TO_CLASSIFY",
                    human_review_required=True,
                    confidence_score=0.0,
                    clinical_action_allowed=False,
                    reason_codes=sorted(list(set(reasons))),
                    mitigation_instructions=guidance,
                    audit_metadata=audit_meta,
                )

        # ── Accumulate Safety Signals and Reason Codes ──
        reason_codes: List[str] = []
        instructions: List[str] = []
        eligibility = "ELIGIBLE"

        # 0. Borderline quality check
        if quality_assessment:
            q_dec = str(quality_assessment.get("decision", "ACCEPT")).upper()
            q_score = float(quality_assessment.get("quality_score", 0.85))
            if q_dec == "ENHANCE" or q_score < 0.65:
                reason_codes.append("QUALITY_BORDERLINE")
                instructions.append("Image quality is borderline; manual confirmation suggested.")

        # 1. Laterality Check
        lat_mismatch = getattr(anatomy_res, "laterality_mismatch", False) if anatomy_res else False
        if not lat_mismatch and isinstance(anatomy_res, dict):
            lat_mismatch = anatomy_res.get("laterality_mismatch", False)
        if lat_mismatch:
            reason_codes.append("LATERALITY_MISMATCH_SUSPECTED")
            eligibility = "REQUIRES_CONFIRMATION"
            op_eye = getattr(anatomy_res, "operator_selected_eye", None) if not isinstance(anatomy_res, dict) else anatomy_res.get("operator_selected_eye")
            inf_eye = getattr(anatomy_res, "inferred_laterality", None) if not isinstance(anatomy_res, dict) else anatomy_res.get("inferred_laterality")
            instructions.append(
                f"Operator selected eye ({op_eye}) conflicts with detected anatomy "
                f"({inf_eye}). Operator confirmation required."
            )

        # 2. Screen / Moiré Capture Warning (Advisory)
        if image_val.possible_screen_capture:
            reason_codes.append("POSSIBLE_SCREEN_CAPTURE")
            instructions.append("Image exhibits periodic screen artifacts; verify direct camera acquisition.")

        # 3. OOD Distribution Shift
        if ood_res and ood_res.is_ood_suspected:
            reason_codes.append("OOD_SUSPECTED")
            instructions.append("Image features deviate from training cohort distribution; advisory uncertainty elevated.")

        # 4. Duplicate Image & Workflow Inconsistency Warnings
        for warn in image_val.warnings:
            if "DUPLICATE_IMAGE_SUBMISSION" in warn:
                reason_codes.append("DUPLICATE_IMAGE_SUBMISSION")
                instructions.append("Duplicate image submission detected.")
            if "WORKFLOW_" in warn or "CROSS_PATIENT" in warn or "STUDY_CONFLICT" in warn:
                reason_codes.append("WORKFLOW_METADATA_INCONSISTENCY")
                eligibility = "REQUIRES_CONFIRMATION"
                instructions.append("Workflow anomaly: image attached to multiple patients or conflicting sessions.")
            if "EXIF_ORIENTATION_NON_STANDARD" in warn:
                reason_codes.append("EXIF_ORIENTATION_NON_STANDARD")
                instructions.append("Image EXIF contains non-standard rotation/mirror tag.")
            if "NON_DR_PATHOLOGY" in warn or "SUSPECTED_NON_DR_PATHOLOGY" in warn:
                reason_codes.append("NON_DR_PATHOLOGY_SUSPECTED")
                eligibility = "INELIGIBLE"
                instructions.append("Suspected non-DR retinal pathology detected; ophthalmologist review mandatory.")

        # 5. Primary Model Output & Fallback Masking Prevention
        primary_conf = 0.0
        primary_stage = None
        if primary_detection:
            import math
            raw_conf = primary_detection.get("confidence")
            primary_stage = primary_detection.get("stage")

            # Numerical stability / IEEE 754 check
            try:
                primary_conf = float(raw_conf) if raw_conf is not None else 0.0
            except (ValueError, TypeError):
                primary_conf = float('nan')

            if math.isnan(primary_conf) or math.isinf(primary_conf):
                return SafetyEvaluationResult(
                    screening_eligibility="INELIGIBLE",
                    safety_state="BLOCKED",
                    automation_level="UNABLE_TO_CLASSIFY",
                    human_review_required=True,
                    confidence_score=0.0,
                    clinical_action_allowed=False,
                    reason_codes=["NUMERICAL_INSTABILITY_DETECTED", "MODEL_OUTPUT_INVALID"],
                    mitigation_instructions="Model inference produced non-finite numerical output (NaN/Inf). Retake or restart engine.",
                    audit_metadata=audit_meta,
                )

            # Stage validity check
            if primary_stage is not None:
                try:
                    int_stage = int(primary_stage)
                    if int_stage not in (0, 1, 2, 3, 4):
                        return SafetyEvaluationResult(
                            screening_eligibility="INELIGIBLE",
                            safety_state="BLOCKED",
                            automation_level="UNABLE_TO_CLASSIFY",
                            human_review_required=True,
                            confidence_score=primary_conf,
                            clinical_action_allowed=False,
                            reason_codes=["INVALID_STAGE_INDEX", "MODEL_OUTPUT_INVALID"],
                            mitigation_instructions=f"Model output invalid stage index ({primary_stage}).",
                            audit_metadata=audit_meta,
                        )
                except (ValueError, TypeError):
                    return SafetyEvaluationResult(
                        screening_eligibility="INELIGIBLE",
                        safety_state="BLOCKED",
                        automation_level="UNABLE_TO_CLASSIFY",
                        human_review_required=True,
                        confidence_score=primary_conf,
                        clinical_action_allowed=False,
                        reason_codes=["INVALID_STAGE_FORMAT", "MODEL_OUTPUT_INVALID"],
                        mitigation_instructions="Model stage is non-integer or malformed.",
                        audit_metadata=audit_meta,
                    )

            # Probability distribution sum sanity check
            probs = primary_detection.get("all_probabilities")
            if isinstance(probs, dict) and probs:
                try:
                    prob_vals = [float(v) for v in probs.values()]
                    p_sum = sum(prob_vals)
                    if p_sum > 2.0:
                        if abs(p_sum - 100.0) > 10.0:
                            reason_codes.append("PROBABILITY_DISTRIBUTION_UNNORMALIZED")
                    else:
                        if abs(p_sum - 1.0) > 0.10:
                            reason_codes.append("PROBABILITY_DISTRIBUTION_UNNORMALIZED")
                except Exception:
                    pass

            # Check if model failure without fallback
            if primary_detection.get("model_available") is False or primary_detection.get("primary_failure") is True:
                if not primary_detection.get("fallback_used"):
                    return SafetyEvaluationResult(
                        screening_eligibility="INELIGIBLE",
                        safety_state="MODEL_FAILURE",
                        automation_level="UNABLE_TO_CLASSIFY",
                        human_review_required=True,
                        confidence_score=0.0,
                        clinical_action_allowed=False,
                        reason_codes=["MODEL_FAILURE"],
                        mitigation_instructions="Primary AI inference failed to complete. No clinical prediction available.",
                        audit_metadata=audit_meta,
                    )

            # Check if deterministic fallback / mock is active
            if (
                primary_detection.get("_deterministic_fallback")
                or primary_detection.get("model_available") is False
                or primary_detection.get("fallback_used") is True
            ):
                reason_codes.append("MODEL_FALLBACK_ACTIVE")
                instructions.append("Model fallback active: secondary or heuristic model in use. Requires physician review and sign-off.")

            if primary_conf < self.thresholds["min_confidence"]:
                reason_codes.append("LOW_CONFIDENCE")
                instructions.append(
                    f"AI detection confidence ({primary_conf:.1f}%) is below minimum screening threshold "
                    f"({self.thresholds['min_confidence']}%)."
                )

            # Referable disease requires human clinician sign-off
            if primary_stage is not None and int(primary_stage) >= 2:
                reason_codes.append("REFERABLE_DR_DETECTED")
                instructions.append(f"Referable DR detected (Stage {primary_stage}); ophthalmology clinical review required.")

            # Suspected non-DR pathology flag
            if primary_detection.get("suspected_non_dr_pathology"):
                reason_codes.append("NON_DR_PATHOLOGY_SUSPECTED")
                instructions.append(
                    "Possible non-diabetic retinal abnormality detected. "
                    "DrishtiAI screening is limited to DR; specialist review required."
                )

        # 6. Multi-Model Consensus / Disagreement
        if primary_detection and secondary_detection:
            sec_stage = secondary_detection.get("stage")
            if primary_stage is not None and sec_stage is not None:
                stage_delta = abs(int(primary_stage) - int(sec_stage))
                if stage_delta >= self.thresholds["model_disagreement_stage_delta"]:
                    reason_codes.append("MODEL_DISAGREEMENT")
                    instructions.append(
                        f"Models disagree significantly: Primary model graded Stage {primary_stage}, "
                        f"Secondary model graded Stage {sec_stage}."
                    )
                elif stage_delta == 1:
                    # Check referable threshold boundary crossing (Stage < 2 vs Stage >= 2)
                    is_prim_ref = int(primary_stage) >= 2
                    is_sec_ref = int(sec_stage) >= 2
                    if is_prim_ref != is_sec_ref:
                        reason_codes.append("REFERABLE_BOUNDARY_DISAGREEMENT")
                        instructions.append(
                            f"Models disagree across referable DR boundary (Stage {primary_stage} vs Stage {sec_stage})."
                        )

        # ── Final Safety State Resolution ──
        critical_reasons = {
            "MODEL_DISAGREEMENT",
            "REFERABLE_BOUNDARY_DISAGREEMENT",
            "LOW_CONFIDENCE",
            "OOD_SUSPECTED",
            "LATERALITY_MISMATCH_SUSPECTED",
            "MODEL_FALLBACK_ACTIVE",
            "QUALITY_BORDERLINE",
            "REFERABLE_DR_DETECTED",
            "WORKFLOW_METADATA_INCONSISTENCY",
            "NON_DR_PATHOLOGY_SUSPECTED",
            "PROBABILITY_DISTRIBUTION_UNNORMALIZED",
            "EXIF_ORIENTATION_NON_STANDARD",
        }

        has_critical_issue = any(rc in critical_reasons for rc in reason_codes)

        if "NON_DR_PATHOLOGY_SUSPECTED" in reason_codes:
            safety_state = "OOD_REVIEW"
            automation_level = "HUMAN_REVIEW_REQUIRED"
            human_review_required = True
        elif has_critical_issue:
            safety_state = "UNCERTAIN"
            automation_level = "HUMAN_REVIEW_REQUIRED"
            human_review_required = True
        else:
            safety_state = "VERIFIED"
            automation_level = "AUTOMATED_ASSISTANCE"
            human_review_required = False

        mitigation = " ".join(instructions) if instructions else None
        clinical_action_allowed = bool(safety_state == "VERIFIED" and eligibility == "ELIGIBLE" and not human_review_required)

        return SafetyEvaluationResult(
            screening_eligibility=eligibility,
            safety_state=safety_state,
            automation_level=automation_level,
            clinical_action_allowed=clinical_action_allowed,
            human_review_required=human_review_required,
            confidence_score=primary_conf,
            reason_codes=reason_codes,
            mitigation_instructions=mitigation,
            audit_metadata=audit_meta,
        )
