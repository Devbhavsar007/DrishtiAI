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
        require_anatomy: bool = False,
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
        # Explicitly distinguish:
        # A. Valid anatomy: valid_anatomy is True, landmarks geometrically plausible
        # B. Invalid anatomy: valid_anatomy is False
        # C. Anatomy unavailable: status UNAVAILABLE or available is False
        # D. Anatomy result missing: valid_anatomy is None or dictionary is empty
        # E. Anatomy exception: exception or error payload
        # F. Anatomy internally inconsistent: contradictory coordinates, impossible geometry
        if require_anatomy and anatomy_res is None:
            return SafetyEvaluationResult(
                screening_eligibility="INELIGIBLE",
                safety_state="ANATOMY_FAILED",
                automation_level="UNABLE_TO_CLASSIFY",
                human_review_required=True,
                confidence_score=0.0,
                clinical_action_allowed=False,
                reason_codes=["ANATOMY_RESULT_MISSING"],
                mitigation_instructions="Anatomical landmark evaluation missing. Screening cannot proceed without verified retinal anatomy.",
                audit_metadata=audit_meta,
            )

        if anatomy_res is not None:
            anatomy_failed = False
            anatomy_reasons = []
            guidance = "Retinal anatomical landmarks (optic disc/fovea) could not be reliably established. Retake or ophthalmology review required."

            # E. Anatomy Exception
            if isinstance(anatomy_res, Exception) or (isinstance(anatomy_res, dict) and ("exception" in anatomy_res or "error" in anatomy_res)):
                anatomy_failed = True
                anatomy_reasons.append("ANATOMY_EXCEPTION")
                guidance = f"Anatomical assessment raised an exception: {str(anatomy_res)}"

            # C. Anatomy Unavailable
            elif (isinstance(anatomy_res, dict) and (anatomy_res.get("available") is False or str(anatomy_res.get("status", "")).upper() == "UNAVAILABLE")) or getattr(anatomy_res, "available", True) is False:
                anatomy_failed = True
                anatomy_reasons.append("ANATOMY_UNAVAILABLE")
                guidance = "Anatomical analysis service unavailable. Manual clinician inspection required."

            # D. Anatomy Result Missing / Malformed
            elif (isinstance(anatomy_res, dict) and len(anatomy_res) == 0) or (isinstance(anatomy_res, dict) and "valid_anatomy" not in anatomy_res):
                anatomy_failed = True
                anatomy_reasons.append("ANATOMY_RESULT_MISSING")
                guidance = "Anatomical assessment dictionary contains no landmark data or valid_anatomy field."

            else:
                valid_anat = getattr(anatomy_res, "valid_anatomy", None) if not isinstance(anatomy_res, dict) else anatomy_res.get("valid_anatomy")
                if valid_anat is None:
                    anatomy_failed = True
                    anatomy_reasons.append("ANATOMY_RESULT_MISSING")
                    guidance = "Anatomy assessment valid_anatomy is null/missing. Fails safe."

                # B. Invalid Anatomy
                elif valid_anat is False:
                    anatomy_failed = True
                    anatomy_reasons.append("ANATOMY_DETECTION_FAILED")
                    notes = getattr(anatomy_res, "notes", []) if not isinstance(anatomy_res, dict) else anatomy_res.get("notes", [])
                    for note in notes:
                        if "ORIENTATION_ANOMALY" in note or "ORIENTATION_UNCERTAIN" in note or "ROTATION" in note:
                            anatomy_reasons.append("ORIENTATION_ANOMALY_SUSPECTED")
                        elif "boundary" in note.lower():
                            anatomy_reasons.append("LANDMARK_OUT_OF_BOUNDS")
                        elif "overlap" in note.lower() or "separation" in note.lower():
                            anatomy_reasons.append("LANDMARK_GEOMETRY_IMPLAUSIBLE")
                        elif "missing" in note.lower() or "not reliably located" in note.lower():
                            anatomy_reasons.append("LANDMARK_MISSING")

                # F. Internally Inconsistent Anatomy
                elif valid_anat is True:
                    disc_center = getattr(anatomy_res, "disc_center", None) if not isinstance(anatomy_res, dict) else anatomy_res.get("disc_center")
                    fovea_center = getattr(anatomy_res, "fovea_center", None) if not isinstance(anatomy_res, dict) else anatomy_res.get("fovea_center")
                    notes = getattr(anatomy_res, "notes", []) if not isinstance(anatomy_res, dict) else anatomy_res.get("notes", [])

                    if disc_center and (disc_center[0] < 0 or disc_center[1] < 0):
                        anatomy_failed = True
                        anatomy_reasons.extend(["ANATOMY_INTERNALLY_INCONSISTENT", "LANDMARK_OUT_OF_BOUNDS"])
                        guidance = "Internal inconsistency: Optic disc coordinates negative."
                    elif disc_center and fovea_center:
                        dist = ((disc_center[0] - fovea_center[0]) ** 2 + (disc_center[1] - fovea_center[1]) ** 2) ** 0.5
                        if dist < 5.0:
                            anatomy_failed = True
                            anatomy_reasons.extend(["ANATOMY_INTERNALLY_INCONSISTENT", "LANDMARK_GEOMETRY_IMPLAUSIBLE"])
                            guidance = "Internal inconsistency: Disc and fovea overlap (< 5px distance)."
                    elif any("implausible" in str(n).lower() or "boundary" in str(n).lower() for n in notes):
                        anatomy_failed = True
                        anatomy_reasons.append("ANATOMY_INTERNALLY_INCONSISTENT")
                        guidance = "Internal inconsistency: Landmarking notes indicate boundary or geometric conflict."

            if anatomy_failed:
                return SafetyEvaluationResult(
                    screening_eligibility="INELIGIBLE",
                    safety_state="ANATOMY_FAILED",
                    automation_level="UNABLE_TO_CLASSIFY",
                    human_review_required=True,
                    confidence_score=0.0,
                    clinical_action_allowed=False,
                    reason_codes=sorted(list(set(anatomy_reasons))),
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

        anat_req_conf = getattr(anatomy_res, "human_confirmation_required", False) if anatomy_res else False
        if not anat_req_conf and isinstance(anatomy_res, dict):
            anat_req_conf = anatomy_res.get("human_confirmation_required", False)

        op_eye = getattr(anatomy_res, "operator_selected_eye", None) if not isinstance(anatomy_res, dict) else anatomy_res.get("operator_selected_eye")
        inf_eye = getattr(anatomy_res, "inferred_laterality", None) if not isinstance(anatomy_res, dict) else anatomy_res.get("inferred_laterality")

        if lat_mismatch:
            reason_codes.append("LATERALITY_MISMATCH_SUSPECTED")
            eligibility = "REQUIRES_CONFIRMATION"
            instructions.append(
                f"Operator selected eye ({op_eye}) conflicts with detected anatomy "
                f"({inf_eye}). Operator confirmation required."
            )
        elif anat_req_conf or (op_eye and inf_eye and inf_eye != "UNKNOWN" and op_eye != inf_eye):
            reason_codes.append("LATERALITY_INDETERMINATE")
            eligibility = "REQUIRES_CONFIRMATION"
            instructions.append(
                f"Retinal landmark laterality is indeterminate or requires confirmation (Operator={op_eye}, Inferred={inf_eye})."
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
        if primary_detection is None or not primary_detection:
            return SafetyEvaluationResult(
                screening_eligibility="INELIGIBLE",
                safety_state="MODEL_FAILURE",
                automation_level="UNABLE_TO_CLASSIFY",
                human_review_required=True,
                confidence_score=0.0,
                clinical_action_allowed=False,
                reason_codes=["MODEL_FAILURE", "MODEL_OUTPUT_INVALID", "MODEL_OUTPUT_MISSING_OR_EMPTY"],
                mitigation_instructions="Primary AI prediction payload is missing or empty. Screening cannot proceed without inference.",
                audit_metadata=audit_meta,
            )

        from engine.detector import validate_model_output_detailed
        val_ok, val_err = validate_model_output_detailed(primary_detection)

        raw_conf = primary_detection.get("confidence")
        primary_stage = primary_detection.get("stage")
        try:
            primary_conf = float(raw_conf) if raw_conf is not None else 0.0
        except (ValueError, TypeError):
            primary_conf = 0.0

        if not val_ok:
            if val_err == "PROBABILITY_DISTRIBUTION_UNNORMALIZED":
                reason_codes.append("PROBABILITY_DISTRIBUTION_UNNORMALIZED")
                instructions.append("Model output probabilities do not sum to 100%; calibration uncertain.")
            else:
                reasons = ["MODEL_OUTPUT_INVALID"]
                if val_err:
                    reasons.append(val_err)
                target_state = "MODEL_FAILURE"
                if val_err in ("NUMERICAL_INSTABILITY_DETECTED", "INVALID_STAGE_INDEX", "INVALID_STAGE_FORMAT"):
                    target_state = "BLOCKED"
                return SafetyEvaluationResult(
                    screening_eligibility="INELIGIBLE",
                    safety_state=target_state,
                    automation_level="UNABLE_TO_CLASSIFY",
                    human_review_required=True,
                    confidence_score=0.0 if target_state == "MODEL_FAILURE" else primary_conf,
                    clinical_action_allowed=False,
                    reason_codes=sorted(list(set(reasons))),
                    mitigation_instructions=f"Model output validation failed: {val_err}. Fails safe to human review.",
                    audit_metadata=audit_meta,
                )

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
            from engine.detector import validate_model_output_detailed
            sec_ok, sec_err = validate_model_output_detailed(secondary_detection)
            if not sec_ok:
                reason_codes.append("SECONDARY_MODEL_OUTPUT_INVALID")
                instructions.append(f"Secondary model validation failed ({sec_err}); consensus unavailable.")
            else:
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
            "SECONDARY_MODEL_OUTPUT_INVALID",
            "LOW_CONFIDENCE",
            "OOD_SUSPECTED",
            "LATERALITY_MISMATCH_SUSPECTED",
            "LATERALITY_INDETERMINATE",
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
