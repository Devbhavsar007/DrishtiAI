"""
DrishtiAI — Flask Application (v2.1 Hardened Clinical System)
Multi-patient support, scan history, batch processing.
Security: rate limiting, CORS, security headers, input validation, audit trail.
"""
import os
import re
import time
import uuid
import json
import logging
import cv2
from flask import Flask, request, jsonify, render_template, send_from_directory, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Load environment
load_dotenv(override=True)

# ---------------------------------------------------------------------------
# Logging — structured with timestamps (replaces bare print statements)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("DrishtiAI")

# Import configuration
from config import DEMO_MODE, OFFLINE_MODE, SAFETY_POLICY_VERSION, TRIAGE_POLICY_VERSION

# Import engine (UNCHANGED)
from engine.preprocessor import preprocess_for_display
from engine.detector import predict
from engine.gradcam import generate_gradcam, get_heatmap_analysis
from engine.segmentor import segment_vessels
from engine.gemma_report import generate_report
from engine.clinical.progression import assess_progression_risk
from engine.clinical.referral import decide_referral
from engine.clinical.safety import evaluate_safety
from engine.clinical.rag import MedicalRAGRetriever
from engine.security.auth import (
    Role,
    create_access_token,
    require_role,
    get_current_actor,
    verify_role_credentials,
)

# Import database
from database import (
    create_patient, get_patient, get_all_patients, update_patient,
    delete_patient, save_scan, get_patient_scans, get_scan,
    get_dashboard_stats, save_progression_assessment, save_referral,
    get_patient_timeline, save_doctor_review, get_doctor_review,
    reconcile_sync_batch, get_sync_status, get_observability_metrics,
    get_pending_sync_events, create_or_update_screening_session,
    get_screening_session, update_screening_session_state, get_db
)
from engine.safety.state_machine import (
    ScreeningState,
    ScreeningStateMachine,
    InvalidStateTransitionError,
)
from engine.safety import SafetyDecisionEngine, validate_image_file, assess_anatomy_and_laterality, evaluate_ood_signal

safety_engine = SafetyDecisionEngine()
rag_retriever = MedicalRAGRetriever()

from config import (
    FLASK_SECRET,
    DEBUG,
    OFFLINE_MODE,
    UPLOAD_DIR,
    RESULTS_DIR,
    RATELIMIT_STORAGE_URI,
    CORS_ALLOWED_ORIGINS,
)

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

# ---------------------------------------------------------------------------
# CORS — restricted strictly to localhost, project-scoped Vercel domains, and configured origins
# ---------------------------------------------------------------------------
cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    re.compile(r"^https:\/\/(?:drishtiai[a-z0-9-]*|optigemma[a-z0-9-]*)\.vercel\.app$"),
]
cors_origins.extend(CORS_ALLOWED_ORIGINS)
frontend_url = os.getenv("FRONTEND_URL")
if frontend_url and frontend_url not in cors_origins:
    cors_origins.append(frontend_url)

CORS(app, origins=cors_origins, supports_credentials=True)

# ---------------------------------------------------------------------------
# Rate Limiting (Memory fallback, Redis-backed in production)
# ---------------------------------------------------------------------------
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri=RATELIMIT_STORAGE_URI,
)

# ---------------------------------------------------------------------------
# Request Correlation & Security Headers Middleware
# ---------------------------------------------------------------------------
@app.before_request
def assign_request_id():
    """Correlate each HTTP request with an audit-traceable Request ID."""
    g.request_id = request.headers.get("X-Request-ID") or f"req-{uuid.uuid4().hex[:12]}"


@app.after_request
def inject_security_headers(response):
    """Inject strict security headers into every HTTP response."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'camera=(self), microphone=(self), geolocation=()'
    if hasattr(g, "request_id"):
        response.headers['X-Request-ID'] = g.request_id

    # Anti-caching for Protected Health Information (PHI)
    if request.path.startswith(("/api/", "/results/")):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
        response.headers['Pragma'] = 'no-cache'

    if not DEBUG:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'"
        )
    return response

# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------
_PATIENT_ID_RE = re.compile(r"^P-\d{4}$")

def _validate_pid(pid: str) -> str:
    """Validate patient ID format or raise 400."""
    if not _PATIENT_ID_RE.match(pid):
        raise ValueError(f"Invalid patient ID: {pid}")
    return pid

# Directories
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), 'uploads')
RESULTS_DIR = os.path.join(os.path.dirname(__file__), 'results')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RESULTS_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'tif'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========================================
# HEALTH CHECK
# ========================================

@app.route("/api/health", methods=["GET"])
@limiter.exempt
def api_health():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "service": "DrishtiAI",
        "version": "2.1.0",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


@app.route("/api/health/ready", methods=["GET"])
@limiter.exempt
def api_health_ready():
    """Readiness probe: verifies database connectivity."""
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        return jsonify({
            "status": "ready",
            "database": "connected",
            "service": "DrishtiAI",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        })
    except Exception as e:
        return jsonify({"status": "not_ready", "error": str(e)}), 503


@app.route("/api/health/detailed", methods=["GET"])
@limiter.limit("30 per minute")
def api_health_detailed():
    """
    Detailed internal diagnostics.
    PROTECTED: Requires authenticated ADMIN or DOCTOR role to prevent reconnaissance.
    """
    actor = get_current_actor()
    if not actor or actor.get("actor_role") not in (Role.ADMIN.value, Role.DOCTOR.value):
        return jsonify({
            "error": "Forbidden: Detailed system diagnostics require authenticated ADMIN or DOCTOR role."
        }), 403

    with get_db() as conn:
        scans_cnt = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        pat_cnt = conn.execute("SELECT COUNT(*) FROM patients").fetchone()[0]
        sync_pending_cnt = conn.execute("SELECT COUNT(*) FROM sync_events WHERE sync_status = 'PENDING'").fetchone()[0]

    return jsonify({
        "status": "healthy",
        "service": "DrishtiAI",
        "version": "2.1.0",
        "actor": actor,
        "diagnostics": {
            "total_patients": pat_cnt,
            "total_scans": scans_cnt,
            "sync_pending_events": sync_pending_cnt,
            "offline_mode": OFFLINE_MODE,
            "models_loaded": {
                "efficientnet_b3": True,
                "offline_deterministic_engine": True,
            },
        },
    })


# ========================================
# SESSION BINDING & OPERATOR CONFIRMATION API
# ========================================

@app.route("/api/sessions/bind", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_sessions_bind():
    """
    Establish four-way binding: (patient_id, operator_id, eye, session_id).
    Prevents wrong-patient or wrong-eye mix-ups. Actor identity is enforced from JWT credentials.
    """
    data = request.get_json() or {}
    patient_id = data.get("patient_id")
    # Bind actor identity strictly to authenticated user to prevent identity spoofing
    operator_id = g.current_user["actor_id"] if hasattr(g, "current_user") and g.current_user else "operator-1"
    eye = (data.get("eye") or "OD").strip().upper()

    if not patient_id:
        return jsonify({"error": "patient_id is required for session binding."}), 400

    if eye not in ("OD", "OS"):
        return jsonify({"error": "Invalid eye laterality. Must be 'OD' (Right) or 'OS' (Left)."}), 400

    patient = get_patient(patient_id)
    if not patient:
        return jsonify({"error": f"Patient {patient_id} not found."}), 404

    session_id = f"sess-{uuid.uuid4().hex[:10]}"
    create_or_update_screening_session(
        session_id=session_id,
        patient_id=patient_id,
        operator_id=operator_id,
        eye=eye,
        current_state=ScreeningState.CREATED,
    )

    return jsonify({
        "success": True,
        "session_id": session_id,
        "patient_id": patient_id,
        "operator_id": operator_id,
        "eye": eye,
        "state": ScreeningState.CREATED,
    }), 201


@app.route("/api/sessions/<session_id>", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_sessions_get(session_id):
    """Get status of an active screening session."""
    sess = get_screening_session(session_id)
    if not sess:
        return jsonify({"error": "Session not found."}), 404
    return jsonify({"success": True, "session": sess})


@app.route("/api/sessions/<session_id>/confirm", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_sessions_confirm(session_id):
    """Operator signs off or confirms laterality override for a session."""
    sess = get_screening_session(session_id)
    if not sess:
        return jsonify({"error": "Session not found."}), 404

    data = request.get_json() or {}
    notes = data.get("notes", "Operator confirmed laterality and clinical review.")
    actor_id = g.current_user["actor_id"] if hasattr(g, "current_user") and g.current_user else sess.get("operator_id", "operator-1")

    try:
        update_screening_session_state(
            session_id=session_id,
            new_state=ScreeningState.ANATOMY_VALIDATED,
            actor_id=actor_id,
            reason=notes,
        )
    except InvalidStateTransitionError as te:
        return jsonify({"error": str(te)}), 409

    return jsonify({
        "success": True,
        "session_id": session_id,
        "state": ScreeningState.ANATOMY_VALIDATED,
        "message": "Operator confirmation recorded.",
    })


@app.route("/api/ingest/validate", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_ingest_validate():
    """
    Pre-inference image validation endpoint.
    Performs magic bytes, decompression bomb, blank frame, and SHA-256 fingerprint checks.
    """
    if "image" not in request.files:
        return jsonify({"is_valid": False, "errors": ["No image file provided in 'image' field."]}), 400

    file = request.files["image"]
    raw_bytes = file.read()

    from engine.safety.image_validator import ImageValidator
    validator = ImageValidator()
    result = validator.validate_bytes(raw_bytes)

    if not result.is_valid:
        return jsonify({
            "is_valid": False,
            "rejection_reason": result.rejection_reason or "VALIDATION_FAILED",
            "errors": result.errors,
            "warnings": result.warnings,
        }), 400

    return jsonify({
        "is_valid": True,
        "sha256_hash": result.sha256_hash,
        "dimensions": [result.width, result.height],
        "duplicate_detected": result.duplicate_detected,
        "warnings": result.warnings,
        "errors": [],
    }), 200


# ========================================
# DEMO & SIMULATION API (Active strictly in DEMO_MODE)
# ========================================

@app.route("/api/demo/scenarios", methods=["GET"])
def api_demo_scenarios():
    """List 10 pre-configured canonical demonstration scenarios."""
    if not DEMO_MODE:
        return jsonify({"error": "Demo mode is disabled in production configuration."}), 403
    from engine.demo.demo_engine import list_demo_scenarios
    return jsonify({"success": True, "scenarios": list_demo_scenarios()})


@app.route("/api/demo/run", methods=["POST"])
def api_demo_run():
    """Execute an isolated demonstration scenario against synthetic namespace."""
    if not DEMO_MODE:
        return jsonify({"error": "Demo simulations are disabled in production configuration."}), 403
    data = request.get_json() or {}
    scenario_id = data.get("scenario_id")
    if not scenario_id:
        return jsonify({"error": "scenario_id is required."}), 400

    from engine.demo.demo_engine import run_demo_scenario
    try:
        custom_patient_id = data.get("patient_id")
        result = run_demo_scenario(scenario_id, custom_patient_id)
        return jsonify({"success": True, "result": result})
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except PermissionError as pe:
        return jsonify({"error": str(pe)}), 403
    except Exception as e:
        log.exception("Demo scenario error")
        return jsonify({"error": str(e)}), 500


# ========================================
# PAGE ROUTES
# ========================================

@app.route("/")
def index():
    """Serve the main SPA."""
    return render_template("index.html")


@app.route("/results/<path:filename>")
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN, Role.PATIENT)
def serve_result(filename):
    """Serve generated result images securely with path traversal protection and RBAC."""
    safe_filename = os.path.basename(filename)
    safe_path = os.path.abspath(os.path.join(RESULTS_DIR, safe_filename))
    if not safe_path.startswith(os.path.abspath(RESULTS_DIR)):
        return jsonify({"success": False, "error": "Access denied: invalid file path."}), 403
    if not os.path.isfile(safe_path):
        return jsonify({"success": False, "error": "File not found."}), 404

    # IDOR protection: patient can only view their own scan artifacts
    if hasattr(g, "current_user") and g.current_user and g.current_user.get("actor_role") == Role.PATIENT.value:
        caller_id = g.current_user.get("actor_id")
        scan_id = safe_filename.split("_")[0]
        scan = get_scan(scan_id)
        if scan and scan.get("patient_id") != caller_id:
            return jsonify({"success": False, "error": "Access denied: patient cannot access other patient records."}), 403

    return send_from_directory(RESULTS_DIR, safe_filename)


# ========================================
# DASHBOARD API
# ========================================

@app.route("/api/dashboard", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_dashboard():
    """Get dashboard statistics."""
    try:
        stats = get_dashboard_stats()
        return jsonify({"success": True, **stats})
    except Exception as e:
        log.exception("Dashboard stats error")
        return jsonify({"success": False, "error": str(e)}), 500


# ========================================
# PATIENT API
# ========================================

@app.route("/api/patients", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_patients_list():
    """List all patients with optional search."""
    try:
        search = request.args.get('search', '')
        patients = get_all_patients(search)
        return jsonify({"success": True, "patients": patients})
    except Exception as e:
        log.exception("Patient list error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/patients", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_patients_create():
    """Create a new patient."""
    try:
        data = request.get_json()
        if not data or not data.get('name', '').strip():
            return jsonify({"success": False, "error": "Patient name is required."}), 400

        patient = create_patient(
            name=data['name'],
            age=data.get('age'),
            gender=data.get('gender', ''),
            diabetes_duration=data.get('diabetes_duration'),
            sugar_level=data.get('sugar_level'),
            hba1c=data.get('hba1c'),
            notes=data.get('notes', '')
        )
        return jsonify({"success": True, "patient": patient})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        log.exception("Patient create error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/patients/<patient_id>", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN, Role.PATIENT)
def api_patient_detail(patient_id):
    """Get patient details with scan history."""
    try:
        _validate_pid(patient_id)
        if hasattr(g, "current_user") and g.current_user and g.current_user.get("actor_role") == Role.PATIENT.value:
            if g.current_user.get("actor_id") != patient_id:
                return jsonify({"success": False, "error": "Access denied: patient cannot access other patient records."}), 403

        patient = get_patient(patient_id)
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404
        return jsonify({"success": True, "patient": patient})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        log.exception("Patient detail error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/patients/<patient_id>", methods=["PUT"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_patient_update(patient_id):
    """Update patient info."""
    try:
        _validate_pid(patient_id)
        data = request.get_json()
        patient = update_patient(patient_id, **data)
        if not patient:
            return jsonify({"success": False, "error": "Patient not found."}), 404
        return jsonify({"success": True, "patient": patient})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        log.exception("Patient update error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/patients/<patient_id>", methods=["DELETE"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_patient_delete(patient_id):
    """Delete a patient and all their scans."""
    try:
        _validate_pid(patient_id)
        delete_patient(patient_id)
        return jsonify({"success": True})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        log.exception("Patient delete error")
        return jsonify({"success": False, "error": str(e)}), 500


# ========================================
# SCAN API (core pipeline — UNCHANGED logic)
# ========================================

@app.route("/api/scans/<scan_id>", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN, Role.PATIENT)
def api_scan_detail(scan_id):
    """Get a single scan's full details."""
    try:
        scan = get_scan(scan_id)
        if not scan:
            return jsonify({"success": False, "error": "Scan not found."}), 404
        if hasattr(g, "current_user") and g.current_user and g.current_user.get("actor_role") == Role.PATIENT.value:
            if scan.get("patient_id") != g.current_user.get("actor_id"):
                return jsonify({"success": False, "error": "Access denied: patient cannot access other patient records."}), 403
        return jsonify({"success": True, "scan": scan})
    except Exception as e:
        log.exception("Scan detail error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scans/<scan_id>/progression", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_scan_progression(scan_id):
    """Compute deterministic progression risk for a scan using longitudinal context."""
    try:
        scan = get_scan(scan_id)
        if not scan:
            return jsonify({"success": False, "error": "Scan not found."}), 404

        patient_id = scan.get("patient_id")
        previous_scans = get_patient_scans(patient_id) if patient_id else []
        patient = get_patient(patient_id) if patient_id else None

        patient_profile = None
        if patient:
            patient_profile = {
                "hba1c": patient.get("hba1c"),
                "diabetes_duration": patient.get("diabetes_duration"),
                "sugar_level": patient.get("sugar_level"),
            }

        progression = assess_progression_risk(
            current_scan={
                "id": scan.get("id"),
                "stage": scan.get("stage"),
                "confidence": scan.get("confidence"),
            },
            previous_scans=previous_scans,
            patient_profile=patient_profile,
        )

        # Persist progression assessment if patient linked
        if patient_id:
            save_progression_assessment(scan_id, patient_id, progression)

        return jsonify({
            "success": True,
            "scan_id": scan_id,
            "progression": progression,
        })
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        log.exception("Progression assessment error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scans/<scan_id>/triage", methods=["POST"])
@require_role(Role.DOCTOR, Role.HEALTH_WORKER, Role.ADMIN)
def api_scan_triage(scan_id):
    """Compute deterministic referral priority (triage) for a scan."""
    try:
        scan = get_scan(scan_id)
        if not scan:
            return jsonify({"success": False, "error": "Scan not found."}), 404

        payload = request.get_json(silent=True) or {}
        # Zero-trust: DO NOT trust client-supplied doctor_review_present!
        # Query canonical doctor_reviews table to verify authentic clinician sign-off
        actual_review = get_doctor_review(scan_id)
        doctor_review_present = bool(actual_review and actual_review.get("decision") in ("APPROVED", "MODIFIED"))
        doctor_review_status = (
            str(actual_review.get("decision", "APPROVED")).upper()
            if doctor_review_present
            else "PENDING"
        )

        patient_id = scan.get("patient_id")
        previous_scans = get_patient_scans(patient_id) if patient_id else []
        patient = get_patient(patient_id) if patient_id else None
        patient_profile = None
        if patient:
            patient_profile = {
                "hba1c": patient.get("hba1c"),
                "diabetes_duration": patient.get("diabetes_duration"),
                "sugar_level": patient.get("sugar_level"),
            }

        progression = payload.get("progression")
        if not progression:
            progression = assess_progression_risk(
                current_scan={
                    "id": scan.get("id"),
                    "stage": scan.get("stage"),
                    "confidence": scan.get("confidence"),
                },
                previous_scans=previous_scans,
                patient_profile=patient_profile,
            )

        triage = decide_referral(
            screening={
                "stage": scan.get("stage", 0),
                "confidence": scan.get("confidence", 0.0),
            },
            progression=progression,
            doctor_review_present=doctor_review_present,
        )

        # Persist referral decision if patient linked
        if patient_id:
            save_referral(
                scan_id=scan_id,
                patient_id=patient_id,
                triage_data=triage,
                doctor_review_status=doctor_review_status,
            )

        return jsonify({
            "success": True,
            "scan_id": scan_id,
            "triage": triage,
            "progression": progression,
        })
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        log.exception("Triage policy error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/patients/<patient_id>/timeline", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN, Role.PATIENT)
def api_patient_timeline(patient_id):
    """Retrieve chronological longitudinal timeline for a patient."""
    try:
        _validate_pid(patient_id)
        if hasattr(g, "current_user") and g.current_user and g.current_user.get("actor_role") == Role.PATIENT.value:
            if g.current_user.get("actor_id") != patient_id:
                return jsonify({"success": False, "error": "Access denied: patient cannot access other patient records."}), 403

        timeline = get_patient_timeline(patient_id)
        return jsonify({"success": True, "timeline": timeline})
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 404
    except Exception as e:
        log.exception("Timeline retrieval error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/screenings/safety-check", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_screening_safety():
    """Evaluate image quality, confidence, and agreement to produce a safety decision."""
    try:
        payload = request.get_json(silent=True) or {}
        quality = payload.get("quality_assessment")
        primary = payload.get("primary_prediction")
        secondary = payload.get("secondary_prediction")

        safety = evaluate_safety(
            quality_assessment=quality,
            primary_prediction=primary,
            secondary_prediction=secondary,
        )

        return jsonify({
            "success": True,
            "safety": {
                "status": safety.status,
                "safety_state": safety.safety_state,
                "automation_level": safety.automation_level,
                "clinical_action_allowed": safety.clinical_action_allowed,
                "screening_eligibility": safety.screening_eligibility,
                "overall_quality_score": safety.overall_quality_score,
                "model_confidence": safety.model_confidence,
                "reasons": safety.reasons,
                "human_review_required": safety.human_review_required,
                "retake_guidance": safety.retake_guidance,
                "disclaimer": safety.disclaimer,
                "metadata": safety.metadata,
            }
        })
    except Exception as e:
        log.exception("Safety evaluation error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/medical/query", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_medical_query():
    """Execute grounded clinical guideline query with verified citations."""
    try:
        payload = request.get_json(silent=True) or {}
        query_text = payload.get("query", "").strip()
        clinical_context = payload.get("clinical_context")
        if not query_text:
            return jsonify({"success": False, "error": "Query string is required."}), 400

        resp = rag_retriever.query(query_text, clinical_context)
        return jsonify({
            "success": True,
            "query": query_text,
            "answer": resp.answer,
            "citations": [
                {
                    "id": c.id,
                    "title": c.title,
                    "organization": c.organization,
                    "year": c.year,
                    "section": c.section,
                    "citation": c.citation,
                    "relevance_score": c.relevance_score,
                }
                for c in resp.citations
            ],
            "confidence": resp.confidence,
            "evidence_found": resp.evidence_found,
            "disclaimer": resp.disclaimer,
            "metadata": resp.metadata,
        })
    except Exception as e:
        log.exception("Medical query RAG error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scans/<scan_id>/doctor-review", methods=["POST"])
@require_role(Role.DOCTOR)
def api_scan_doctor_review(scan_id):
    """Submit doctor sign-off / review for a screening with cryptographic identity binding."""
    try:
        scan = get_scan(scan_id)
        if not scan:
            return jsonify({"success": False, "error": "Scan not found."}), 404

        payload = request.get_json(silent=True) or {}
        # Zero-trust: Sourced from verified authenticated actor, never trusted blindly from client payload
        actor = getattr(g, "current_user", {})
        actor_id = actor.get("actor_id")
        if not actor_id:
            return jsonify({"success": False, "error": "No verified clinician identity present."}), 401

        client_doc_id = payload.get("doctor_id")
        if client_doc_id and client_doc_id != actor_id and actor.get("actor_role") != Role.ADMIN.value:
            return jsonify({
                "success": False,
                "error": f"Identity mismatch: Authenticated clinician '{actor_id}' cannot sign off as '{client_doc_id}'."
            }), 403

        doctor_id = client_doc_id if (client_doc_id and actor.get("actor_role") == Role.ADMIN.value) else actor_id
        doctor_name = payload.get("doctor_name") or f"Dr. {actor_id}"
        decision = payload.get("decision") or "APPROVED"  # APPROVED | MODIFIED | REJECTED_RETAKE
        original_stage = int(scan.get("stage", 0))
        adjusted_stage = payload.get("adjusted_stage")
        if adjusted_stage is not None:
            adjusted_stage = int(adjusted_stage)
        approved_priority = payload.get("approved_priority") or (
            "URGENT" if original_stage >= 3 else "EARLY" if original_stage >= 2 else "ROUTINE"
        )
        clinical_notes = payload.get("clinical_notes", "")
        recommended_intervention = payload.get("recommended_intervention", "")

        patient_id = scan.get("patient_id")
        saved = save_doctor_review(
            scan_id=scan_id,
            patient_id=patient_id,
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            decision=decision,
            original_stage=original_stage,
            adjusted_stage=adjusted_stage,
            approved_priority=approved_priority,
            clinical_notes=clinical_notes,
            recommended_intervention=recommended_intervention,
        )

        return jsonify({
            "success": True,
            "scan_id": scan_id,
            "review": saved,
        })
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        log.exception("Doctor review submission error")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/scans/<scan_id>/doctor-review", methods=["GET"])
@require_role(Role.DOCTOR, Role.HEALTH_WORKER, Role.ADMIN)
def api_get_doctor_review(scan_id):
    """Retrieve clinician sign-off details for a scan."""
    try:
        review = get_doctor_review(scan_id)
        return jsonify({
            "success": True,
            "scan_id": scan_id,
            "review": review,
        })
    except Exception as e:
        log.exception("Doctor review retrieval error")
        return jsonify({"success": False, "error": str(e)}), 500


# ========================================
# AUTH & RBAC ENDPOINTS
# ========================================

@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    """Generate session access token for DrishtiAI roles with credential verification for privileged tiers."""
    data = request.get_json(silent=True) or {}
    user_id = data.get("user_id", "").strip() or f"user-{uuid.uuid4().hex[:6]}"
    requested_role = str(data.get("role") or Role.HEALTH_WORKER.value).upper()
    valid_roles = {r.value for r in Role}
    if requested_role not in valid_roles:
        return jsonify({
            "success": False,
            "error": f"Invalid role: {requested_role}. Valid roles are: {sorted(list(valid_roles))}"
        }), 400

    secret = data.get("secret") or data.get("password") or request.headers.get("X-Drishti-Secret")
    if requested_role in (Role.ADMIN.value, Role.DOCTOR.value):
        if not verify_role_credentials(requested_role, secret):
            return jsonify({
                "success": False,
                "error": f"Privileged role '{requested_role}' requires valid secret credentials. Direct self-elevation is prohibited."
            }), 401

    token = create_access_token(user_id=user_id, role=requested_role)
    return jsonify({
        "success": True,
        "token": token,
        "user": {
            "user_id": user_id,
            "role": requested_role,
        }
    })


@app.route("/api/auth/me", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN, Role.PATIENT)
def api_auth_me():
    """Retrieve identity and privileges of active session actor."""
    actor = get_current_actor()
    return jsonify({
        "success": True,
        "actor": actor,
    })


# ========================================
# OFFLINE SYNC RECONCILIATION
# ========================================

@app.route("/api/sync", methods=["POST"])
@require_role(Role.ADMIN, Role.HEALTH_WORKER, Role.DOCTOR)
def api_sync_batch():
    """Reconcile offline sync events from edge screening devices."""
    payload = request.get_json(silent=True) or {}
    events = payload.get("events")
    if not isinstance(events, list):
        return jsonify({"success": False, "error": "Invalid format: 'events' must be an array"}), 400

    result = reconcile_sync_batch(events)
    return jsonify({
        "success": True,
        "reconciliation": result,
    })


@app.route("/api/sync/status", methods=["GET"])
@require_role(Role.ADMIN, Role.DOCTOR, Role.HEALTH_WORKER)
def api_sync_status():
    """Retrieve ledger synchronization health and backlog depth."""
    status = get_sync_status()
    return jsonify({
        "success": True,
        "status": status,
    })


@app.route("/api/sync/pending", methods=["GET"])
@require_role(Role.ADMIN, Role.DOCTOR)
def api_sync_pending():
    """Retrieve pending sync events for local device synchronization."""
    device_id = request.args.get("device_id")
    limit = int(request.args.get("limit", 100))
    events = get_pending_sync_events(device_id=device_id, limit=limit)
    return jsonify({
        "success": True,
        "count": len(events),
        "events": events,
    })


# ========================================
# OBSERVABILITY & CLINICAL METRICS
# ========================================

@app.route("/api/analytics/metrics", methods=["GET"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
def api_analytics_metrics():
    """Aggregate structured system observability, epidemiology, and referral metrics."""
    metrics = get_observability_metrics()
    return jsonify({
        "success": True,
        "metrics": metrics,
    })


@app.route("/analyze", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
@limiter.limit("10 per minute")
def analyze():
    """
    Run the FULL analysis pipeline on an uploaded fundus image.
    NOW saves to database if patient_id is provided.
    Core engine logic is UNCHANGED from v1.0.
    Rate limited to 10 inferences per minute.
    """
    start_time = time.time()

    # Validate file
    if "image" not in request.files:
        return jsonify({"error": "No image file uploaded."}), 400

    file = request.files["image"]
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PNG, JPG, JPEG, BMP, or TIFF."}), 400

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"error": "Empty file uploaded.", "safety_state": "REJECTED"}), 400

    from engine.safety.image_validator import ImageValidator
    validator = ImageValidator()
    val_result = validator.validate_bytes(file_bytes)
    if not val_result.is_valid:
        return jsonify({
            "error": val_result.rejection_reason or "Image validation failed",
            "is_valid": False,
            "safety_state": "REJECTED",
            "screening_eligibility": "INELIGIBLE",
            "automation_level": "UNABLE_TO_CLASSIFY",
            "clinical_action_allowed": False,
            "errors": val_result.errors,
            "warnings": val_result.warnings,
        }), 400

    # Save uploaded file
    analysis_id = str(uuid.uuid4())[:12]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, f"{analysis_id}_{filename}")
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    # Get patient info (optional for backward compatibility)
    patient_id = request.form.get("patient_id", "")
    patient_info = {}
    if request.form.get("age"):
        patient_info["age"] = request.form.get("age")
    if request.form.get("diabetes_duration"):
        patient_info["diabetes_duration"] = request.form.get("diabetes_duration")
    if request.form.get("sugar_level"):
        patient_info["sugar_level"] = request.form.get("sugar_level")
    if request.form.get("hba1c"):
        patient_info["hba1c"] = request.form.get("hba1c")

    try:
        raw_bgr = cv2.imread(filepath)
        if raw_bgr is None:
            return jsonify({
                "error": "Corrupted image payload could not be decoded.",
                "safety_state": "REJECTED",
                "screening_eligibility": "INELIGIBLE",
                "automation_level": "UNABLE_TO_CLASSIFY",
                "clinical_action_allowed": False
            }), 400

        # Evaluate Out-of-Distribution / Non-Fundus Domain
        ood_res = evaluate_ood_signal(raw_bgr)
        if not ood_res.domain_valid:
            return jsonify({
                "error": ood_res.rejection_reason or "Non-fundus or invalid domain image rejected.",
                "safety_state": "REJECTED",
                "screening_eligibility": "INELIGIBLE",
                "automation_level": "UNABLE_TO_CLASSIFY",
                "clinical_action_allowed": False,
                "ood": ood_res.to_dict(),
            }), 400

        # Landmark and Laterality Assessment
        operator_eye = request.form.get("eye")
        anatomy_res = assess_anatomy_and_laterality(raw_bgr, operator_eye=operator_eye)

        # --- 2. Preprocess Image ---
        processed = preprocess_for_display(filepath)
        model_input = processed["model_input"]
        model_input_raw = processed["model_input_raw"]
        model_input_enhanced_highres = processed["model_input_enhanced_highres"]
        original = processed["original"]

        # Save original resized for display
        original_path = os.path.join(RESULTS_DIR, f"{analysis_id}_scan.png")
        cv2.imwrite(original_path, original)

        # --- 3. Run Detection ---
        detection_result = predict(model_input_enhanced_highres)

        # --- 4. Centralized Safety Arbitration ---
        verified_operator = (g.current_user.get("actor_id") if hasattr(g, "current_user") and g.current_user else request.form.get("operator_id") or "operator-1")
        safety_eval = safety_engine.evaluate(
            image_val=val_result,
            anatomy_res=anatomy_res,
            ood_res=ood_res,
            primary_detection=detection_result,
            patient_id=patient_id,
            operator_id=verified_operator,
        )

        # --- 5. Generate Heatmap ---
        heatmap_path = os.path.join(RESULTS_DIR, f"{analysis_id}_heatmap.png")
        heatmap_overlay, heatmap_raw = generate_gradcam(model_input, original, save_path=heatmap_path)
        heatmap_analysis = get_heatmap_analysis(heatmap_raw)

        # --- 6. Vessel Segmentation ---
        vessel_path = os.path.join(RESULTS_DIR, f"{analysis_id}_vessels.png")
        vessel_map, vessel_stats = segment_vessels(original, save_path=vessel_path)

        # --- 7. Gemma Report ---
        report, _raw_gemma = generate_report(
            detection_result, heatmap_analysis, vessel_stats, patient_info
        )

        elapsed = round(time.time() - start_time, 2)
        log.info("Analysis %s completed in %.2fs — stage %s (Safety: %s)",
                 analysis_id, elapsed, detection_result.get('stage', '?'), safety_eval.safety_state)

        # --- 8. Save to Database ---
        image_paths = {
            "original": f"/results/{analysis_id}_scan.png",
            "heatmap": f"/results/{analysis_id}_heatmap.png",
            "vessels": f"/results/{analysis_id}_vessels.png",
        }

        if patient_id:
            try:
                save_scan(
                    scan_id=analysis_id,
                    patient_id=patient_id,
                    detection_result=detection_result,
                    heatmap_analysis=heatmap_analysis,
                    vessel_stats=vessel_stats,
                    report=report,
                    image_paths=image_paths,
                    processing_time=elapsed
                )
                log.info("Scan %s saved for patient %s", analysis_id, patient_id)
            except Exception as db_err:
                log.warning("Failed to save scan to DB: %s", db_err)

        # --- 9. Compile Response ---
        result = {
            "success": True,
            "analysis_id": analysis_id,
            "patient_id": patient_id,
            "processing_time": elapsed,
            "detection": detection_result,
            "safety": safety_eval.to_dict(),
            "safety_state": safety_eval.safety_state,
            "automation_level": safety_eval.automation_level,
            "clinical_action_allowed": safety_eval.clinical_action_allowed,
            "screening_eligibility": safety_eval.screening_eligibility,
            "heatmap_analysis": heatmap_analysis,
            "vessel_stats": vessel_stats,
            "report": report,
            "images": image_paths,
        }

        return jsonify(result)

    except Exception as e:
        log.exception("Analysis pipeline error for %s", analysis_id)
        error_response = {"error": str(e)}
        if DEBUG:
            import traceback
            error_response["traceback"] = traceback.format_exc()
        return jsonify(error_response), 500


@app.route("/translate", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN, Role.PATIENT)
def translate():
    """Translate an existing report to another language."""
    data = request.get_json()
    report = data.get("report")
    language = data.get("language", "hindi")

    if not report:
        return jsonify({"error": "No report provided"}), 400

    try:
        from engine.gemma_report import translate_report
        translated = translate_report(report, language)
        return jsonify({"success": True, "report": translated})
    except Exception as e:
        log.exception("Translation error")
        return jsonify({"error": str(e)}), 500


# ========================================
# V2 PIPELINE — Full Clinical Pipeline
# (IQA Gate → Structures → Grading → Explain → Report)
# ========================================

@app.route("/api/analyze-v2", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
@limiter.limit("10 per minute")
def analyze_v2():
    """
    DrishtiAI v2 Full Pipeline:
      1. Image Quality Assessment (accept / enhance / reject with feedback)
      2. Retinal structure segmentation (disc, fovea, vessels, lesions)
      3. Calibrated DR grading (ordinal + referable binary head)
      4. Explainability (Grad-CAM overlay + lesion evidence map)
      5. Report generation (online via Gemma API or offline template)

    Returns all brief-mandated deliverables in a single response.
    """
    start_time = time.time()

    # ── Validate file upload ──
    if "image" not in request.files:
        return jsonify({"error": "No image file uploaded."}), 400

    file = request.files["image"]
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PNG, JPG, JPEG, BMP, or TIFF."}), 400

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"error": "Empty file uploaded.", "safety_state": "REJECTED"}), 400

    from engine.safety.image_validator import ImageValidator
    validator = ImageValidator()
    val_result = validator.validate_bytes(file_bytes)
    if not val_result.is_valid:
        return jsonify({
            "error": val_result.rejection_reason or "Image validation failed",
            "is_valid": False,
            "safety_state": "REJECTED",
            "screening_eligibility": "INELIGIBLE",
            "automation_level": "UNABLE_TO_CLASSIFY",
            "clinical_action_allowed": False,
            "errors": val_result.errors,
            "warnings": val_result.warnings,
        }), 400

    # Save uploaded file
    analysis_id = str(uuid.uuid4())[:12]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, f"{analysis_id}_{filename}")
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    # Patient info
    patient_id = request.form.get("patient_id", "")
    patient_info = {}
    for field_name in ("age", "diabetes_duration", "sugar_level", "hba1c"):
        val = request.form.get(field_name)
        if val:
            patient_info[field_name] = val

    try:
        img_bgr = cv2.imread(filepath)
        if img_bgr is None:
            return jsonify({
                "error": "Could not decode image file.",
                "safety_state": "REJECTED",
                "screening_eligibility": "INELIGIBLE",
                "automation_level": "UNABLE_TO_CLASSIFY",
                "clinical_action_allowed": False
            }), 400

        # Evaluate Out-of-Distribution / Non-Fundus Domain
        ood_res = evaluate_ood_signal(img_bgr)
        if not ood_res.domain_valid:
            return jsonify({
                "error": ood_res.rejection_reason or "Non-fundus or invalid domain image rejected.",
                "safety_state": "REJECTED",
                "screening_eligibility": "INELIGIBLE",
                "automation_level": "UNABLE_TO_CLASSIFY",
                "clinical_action_allowed": False,
                "ood": ood_res.to_dict(),
            }), 400

        # Landmark and Laterality Assessment
        operator_eye = request.form.get("eye")
        anatomy_res = assess_anatomy_and_laterality(img_bgr, operator_eye=operator_eye)

        # ── MODULE 1: Image Quality Assessment ──
        from engine.pipeline.iqa import run_iqa
        iqa_result, processed_img = run_iqa(img_bgr)

        if iqa_result.decision == "REJECT" or processed_img is None:
            elapsed = round(time.time() - start_time, 2)
            log.info("Analysis %s REJECTED by IQA gate: %s",
                     analysis_id, iqa_result.feedback)
            return jsonify({
                "success": True,
                "analysis_id": analysis_id,
                "status": "REJECTED",
                "safety_state": "REJECTED",
                "screening_eligibility": "INELIGIBLE",
                "automation_level": "UNABLE_TO_CLASSIFY",
                "clinical_action_allowed": False,
                "iqa": iqa_result.to_dict(),
                "message": " ".join(iqa_result.feedback),
                "processing_time": elapsed,
            })

        # Save processed image for display
        original_path = os.path.join(RESULTS_DIR, f"{analysis_id}_scan.png")
        cv2.imwrite(original_path, processed_img)

        # ── MODULE 2: Structure Segmentation ──
        from engine.pipeline.structures import extract_structures
        from engine.pipeline.iqa import estimate_fov

        fov = estimate_fov(processed_img)
        structures = extract_structures(processed_img, fov)
        structures_dict = structures.to_dict()

        # Save vessel map for display
        vessel_path = os.path.join(RESULTS_DIR, f"{analysis_id}_vessels.png")
        if structures.vessel_mask is not None:
            vessel_display = cv2.cvtColor(structures.vessel_mask, cv2.COLOR_GRAY2BGR)
            vessel_display = cv2.resize(vessel_display, (224, 224))
            cv2.imwrite(vessel_path, vessel_display)

        # ── MODULE 3: DR Grading ──
        # Try the new ordinal grading model first, fall back to legacy detector
        from config import PIPELINE_WEIGHTS, PIPELINE_CALIBRATION
        import os as _os

        grading_result = None
        detection_result = None

        if _os.path.exists(PIPELINE_WEIGHTS):
            # New calibrated ordinal model
            try:
                import torch
                from engine.pipeline.grading import load_grading_model, Calibration, predict_batch

                device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
                model = load_grading_model(PIPELINE_WEIGHTS, device)
                calib = Calibration.load(PIPELINE_CALIBRATION)

                # Preprocess for grading
                img_resized = cv2.resize(processed_img, (300, 300))
                img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB).astype('float32') / 255.0
                import numpy as np
                mean = np.array([0.485, 0.456, 0.406], dtype='float32')
                std = np.array([0.229, 0.224, 0.225], dtype='float32')
                img_norm = (img_rgb - mean) / std
                x = torch.from_numpy(img_norm.transpose(2, 0, 1)).unsqueeze(0)
                lesion_feats = torch.from_numpy(structures.lesion_features).unsqueeze(0)

                pred = predict_batch(model, x, lesion_feats, calib, device)
                grade = int(pred["grade"][0])

                from config import DR_STAGES
                stage_info = DR_STAGES.get(grade, DR_STAGES[0])

                grading_result = {
                    "grade": grade,
                    "probs": [round(float(p), 4) for p in pred["probs"][0]],
                    "expected_grade": round(float(pred["expected_grade"][0]), 2),
                    "referable": bool(pred["referable"][0]),
                    "referable_prob": round(float(pred["referable_prob"][0]), 4),
                    "calibration_temperature": calib.temperature,
                    "calibration_threshold": calib.threshold,
                }

                # Build compatible detection_result for report generation
                detection_result = {
                    "stage": grade,
                    "stage_name": stage_info["name"],
                    "confidence": round(float(pred["probs"][0][grade]) * 100, 1),
                    "all_probabilities": {i: round(float(pred["probs"][0][i]) * 100, 1) for i in range(5)},
                    "severity": stage_info["severity"],
                    "color": stage_info["color"],
                    "_model": "DrishtiAI-Pipeline (ordinal+referable, calibrated)",
                    "_calibrated": True,
                }
                log.info("Analysis %s: pipeline grading — Grade %d, referable=%s",
                         analysis_id, grade, pred["referable"][0])

            except Exception as e:
                log.warning("Pipeline grading failed, falling back to legacy: %s", e)
                grading_result = None

        # Fallback to legacy EfficientNet-B3 detector
        if detection_result is None:
            processed = preprocess_for_display(filepath)
            model_input_enhanced = processed["model_input_enhanced_highres"]
            detection_result = predict(model_input_enhanced)
            detection_result["_calibrated"] = False

        # ── MODULE 4: Explainability ──
        processed_data = preprocess_for_display(filepath)
        model_input = processed_data["model_input"]
        original_display = processed_data["original"]

        heatmap_path = os.path.join(RESULTS_DIR, f"{analysis_id}_heatmap.png")
        heatmap_overlay, heatmap_raw = generate_gradcam(model_input, original_display, save_path=heatmap_path)
        heatmap_analysis = get_heatmap_analysis(heatmap_raw)

        # ── MODULE 5: Report Generation ──
        report, _raw_source = generate_report(
            detection_result, heatmap_analysis,
            {"vessel_density_percent": round(structures.vessel_density * 100, 2),
             "vessel_health_text": f"Vessel density: {structures.vessel_density * 100:.1f}%"},
            patient_info,
            structures=structures_dict,
        )

        elapsed = round(time.time() - start_time, 2)
        log.info("Analysis %s (v2) completed in %.2fs — Grade %s, referable=%s",
                 analysis_id, elapsed, detection_result.get('stage', '?'),
                 grading_result.get('referable', 'N/A') if grading_result else 'N/A')

        # Image paths for response
        image_paths = {
            "original": f"/results/{analysis_id}_scan.png",
            "heatmap": f"/results/{analysis_id}_heatmap.png",
            "vessels": f"/results/{analysis_id}_vessels.png",
        }

        # Save to database if patient_id provided
        if patient_id:
            try:
                save_scan(
                    scan_id=analysis_id,
                    patient_id=patient_id,
                    detection_result=detection_result,
                    heatmap_analysis=heatmap_analysis,
                    vessel_stats=structures_dict,
                    report=report,
                    image_paths=image_paths,
                    processing_time=elapsed
                )
            except Exception as db_err:
                log.warning("Failed to save scan to DB: %s", db_err)

        # ── Centralized Safety Arbitration ──
        verified_operator = (g.current_user.get("actor_id") if hasattr(g, "current_user") and g.current_user else request.form.get("operator_id") or "operator-1")
        safety_eval = safety_engine.evaluate(
            image_val=val_result,
            anatomy_res=anatomy_res,
            ood_res=ood_res,
            primary_detection=detection_result,
            patient_id=patient_id,
            operator_id=verified_operator,
        )

        # ── Compile v2 response ──
        result = {
            "success": True,
            "pipeline_version": "v2",
            "analysis_id": analysis_id,
            "patient_id": patient_id,
            "processing_time": elapsed,
            "status": "OK",

            # Central Safety Arbitration
            "safety": safety_eval.to_dict(),
            "safety_state": safety_eval.safety_state,
            "automation_level": safety_eval.automation_level,
            "clinical_action_allowed": safety_eval.clinical_action_allowed,
            "screening_eligibility": safety_eval.screening_eligibility,

            # Module 1: IQA
            "iqa": iqa_result.to_dict(),

            # Module 2: Structures
            "structures": structures_dict,

            # Module 3: Detection / Grading
            "detection": detection_result,
            "grading": grading_result,

            # Module 4: Explainability
            "heatmap_analysis": heatmap_analysis,

            # Module 5: Report
            "report": report,

            # Images
            "images": image_paths,
        }

        return jsonify(result)

    except Exception as e:
        log.exception("v2 pipeline error for %s", analysis_id)
        error_response = {"error": str(e)}
        if DEBUG:
            import traceback
            error_response["traceback"] = traceback.format_exc()
        return jsonify(error_response), 500


# ========================================
# V3 PIPELINE — Two-Tiered Architecture
# (Tier 1: Edge HiResCAM/Grading + Tier 2: MedGemma Multimodal VLM)
# ========================================

@app.route("/api/analyze-v3", methods=["POST"])
@require_role(Role.HEALTH_WORKER, Role.DOCTOR, Role.ADMIN)
@limiter.limit("10 per minute")
def analyze_v3():
    """
    OptiGemma Two-Tiered Architecture Endpoint:
      Tier 1 (Edge): IQA -> Structures -> DR Grading -> HiResCAM + Grad-CAM -> Quantitative Localization Metrics
      Tier 2 (Cloud): MedGemma 27B multimodal vision-language verification + grounded clinical narrative
      (Graceful offline fallback if disconnected or timed out)
    """
    start_time = time.time()

    if "image" not in request.files:
        return jsonify({"error": "No image file uploaded."}), 400

    file = request.files["image"]
    if not file or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PNG, JPG, JPEG, BMP, or TIFF."}), 400

    file_bytes = file.read()
    if not file_bytes:
        return jsonify({"error": "Empty file uploaded.", "safety_state": "REJECTED"}), 400

    from engine.safety.image_validator import ImageValidator
    validator = ImageValidator()
    val_result = validator.validate_bytes(file_bytes)
    if not val_result.is_valid:
        return jsonify({
            "error": val_result.rejection_reason or "Image validation failed",
            "is_valid": False,
            "safety_state": "REJECTED",
            "screening_eligibility": "INELIGIBLE",
            "automation_level": "UNABLE_TO_CLASSIFY",
            "clinical_action_allowed": False,
            "errors": val_result.errors,
            "warnings": val_result.warnings,
        }), 400

    analysis_id = str(uuid.uuid4())[:12]
    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_DIR, f"{analysis_id}_{filename}")
    with open(filepath, "wb") as f:
        f.write(file_bytes)

    patient_id = request.form.get("patient_id", "")
    patient_info = {}
    for field_name in ("age", "diabetes_duration", "sugar_level", "hba1c"):
        val = request.form.get(field_name)
        if val:
            patient_info[field_name] = val

    force_offline = (
        request.form.get("offline", "").lower() in ("true", "1", "yes")
        or request.headers.get("X-Force-Offline", "").lower() == "true"
    )

    try:
        raw_bgr = cv2.imread(filepath)
        if raw_bgr is None:
            return jsonify({
                "error": "Could not decode image file.",
                "safety_state": "REJECTED",
                "screening_eligibility": "INELIGIBLE",
                "automation_level": "UNABLE_TO_CLASSIFY",
                "clinical_action_allowed": False
            }), 400

        # Evaluate Out-of-Distribution / Non-Fundus Domain
        ood_res = evaluate_ood_signal(raw_bgr)
        if not ood_res.domain_valid:
            return jsonify({
                "error": ood_res.rejection_reason or "Non-fundus or invalid domain image rejected.",
                "safety_state": "REJECTED",
                "screening_eligibility": "INELIGIBLE",
                "automation_level": "UNABLE_TO_CLASSIFY",
                "clinical_action_allowed": False,
                "ood": ood_res.to_dict(),
            }), 400

        # Landmark and Laterality Assessment
        operator_eye = request.form.get("eye")
        anatomy_res = assess_anatomy_and_laterality(raw_bgr, operator_eye=operator_eye)

        from engine.pipeline.two_tier_runner import run_two_tier_pipeline

        result = run_two_tier_pipeline(
            image_input=filepath,
            force_offline=force_offline,
            patient_info=patient_info,
            save_overlays=True,
            case_id=analysis_id,
        )

        result["analysis_id"] = analysis_id
        result["patient_id"] = patient_id

        # Centralized Safety Arbitration
        verified_operator = (g.current_user.get("actor_id") if hasattr(g, "current_user") and g.current_user else request.form.get("operator_id") or "operator-1")
        safety_eval = safety_engine.evaluate(
            image_val=val_result,
            anatomy_res=anatomy_res,
            ood_res=ood_res,
            primary_detection=result.get("detection"),
            patient_id=patient_id,
            operator_id=verified_operator,
        )
        result["safety"] = safety_eval.to_dict()
        result["safety_state"] = safety_eval.safety_state
        result["automation_level"] = safety_eval.automation_level
        result["clinical_action_allowed"] = safety_eval.clinical_action_allowed
        result["screening_eligibility"] = safety_eval.screening_eligibility

        # Save to DB if patient_id provided
        if patient_id and result.get("status") != "REJECTED":
            try:
                save_scan(
                    scan_id=analysis_id,
                    patient_id=patient_id,
                    detection_result=result.get("detection") or {},
                    heatmap_analysis=result.get("explanation") or {},
                    vessel_stats=result.get("structures") or {},
                    report=result.get("report") or {},
                    image_paths=result.get("images") or {},
                    processing_time=round(result.get("total_latency_ms", 0) / 1000.0, 2),
                )
                log.info("Scan %s saved for patient %s (v3 two-tiered)", analysis_id, patient_id)
            except Exception as db_err:
                log.warning("Failed to save v3 scan to DB: %s", db_err)

        return jsonify(result)

    except Exception as e:
        log.exception("v3 two-tier pipeline error for %s", analysis_id)
        error_response = {"error": str(e)}
        if DEBUG:
            import traceback
            error_response["traceback"] = traceback.format_exc()
        return jsonify(error_response), 500


# ========================================
# STARTUP
# ========================================

if __name__ == "__main__":
    log.info("=" * 60)
    log.info("  DrishtiAI v2.1 — Hardened Clinical System")
    log.info("  http://127.0.0.1:5000")
    log.info("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=DEBUG, use_reloader=False)
