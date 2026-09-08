"""
DrishtiAI — Database Layer (SQLite)
Stores patient records and scan history permanently.
Hardened: audit logging, N+1 fix, input validation, context-managed connections.
"""
import sqlite3
import os
import re
import json
import logging
import uuid
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Any

log = logging.getLogger("DrishtiAI.db")

DB_PATH = os.path.join(os.path.dirname(__file__), 'DrishtiAI.db')
_patient_id_lock = threading.Lock()

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
_PATIENT_ID_RE = re.compile(r"^P-\d{4,}$")
_ALLOWED_PATIENT_COLS = frozenset(
    ['name', 'age', 'gender', 'diabetes_duration', 'sugar_level', 'hba1c', 'notes']
)


def _validate_patient_id(pid: str) -> str:
    """Validate patient ID format (P-0001 .. P-9999)."""
    if not _PATIENT_ID_RE.match(pid):
        raise ValueError(f"Invalid patient ID format: {pid!r}. Expected P-NNNN.")
    return pid


def _sanitize_string(value: str, max_len: int = 1000) -> str:
    """Strip HTML tags and truncate to max_len to prevent XSS / overflow."""
    if not isinstance(value, str):
        return value
    # Strip HTML tags
    clean = re.sub(r'<[^>]+>', '', value)
    return clean[:max_len].strip()


# ---------------------------------------------------------------------------
# Connection management — context manager for safe lifecycle
# ---------------------------------------------------------------------------
@contextmanager
def get_db():
    """Get a database connection as a context manager."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    """Initialize the database tables."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS patients (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                age INTEGER,
                gender TEXT DEFAULT '',
                diabetes_duration INTEGER,
                sugar_level REAL,
                hba1c REAL,
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS scans (
                id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                stage INTEGER NOT NULL,
                stage_name TEXT NOT NULL,
                confidence REAL NOT NULL,
                severity TEXT DEFAULT '',
                color TEXT DEFAULT '',
                all_probabilities TEXT DEFAULT '{}',
                model_used TEXT DEFAULT '',
                heatmap_analysis TEXT DEFAULT '{}',
                vessel_stats TEXT DEFAULT '{}',
                report TEXT DEFAULT '{}',
                image_original TEXT DEFAULT '',
                image_heatmap TEXT DEFAULT '',
                image_vessels TEXT DEFAULT '',
                processing_time REAL DEFAULT 0,
                laterality TEXT DEFAULT 'OD',
                operator_id TEXT DEFAULT 'operator-1',
                safety_state TEXT DEFAULT 'VERIFIED',
                automation_level TEXT DEFAULT 'AUTOMATED_ASSISTANCE',
                reason_codes_json TEXT DEFAULT '[]',
                image_hash TEXT DEFAULT '',
                device_id TEXT DEFAULT 'LOCAL-EDGE-01',
                screening_state TEXT DEFAULT 'FINALIZED',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                actor_id TEXT DEFAULT 'system',
                actor_role TEXT DEFAULT 'SYSTEM',
                request_id TEXT DEFAULT '',
                details TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS progression_assessments (
                id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                risk_category TEXT NOT NULL,
                six_month_risk REAL NOT NULL,
                twelve_month_risk REAL NOT NULL,
                payload TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (scan_id) REFERENCES scans(id),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                priority TEXT NOT NULL,
                reason_codes TEXT DEFAULT '[]',
                human_review_required INTEGER DEFAULT 0,
                doctor_review_status TEXT DEFAULT 'PENDING',
                doctor_notes TEXT DEFAULT '',
                payload TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (scan_id) REFERENCES scans(id),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE TABLE IF NOT EXISTS doctor_reviews (
                id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                doctor_id TEXT NOT NULL,
                doctor_name TEXT DEFAULT '',
                decision TEXT NOT NULL,
                original_stage INTEGER NOT NULL,
                adjusted_stage INTEGER,
                approved_priority TEXT NOT NULL,
                clinical_notes TEXT DEFAULT '',
                recommended_intervention TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (scan_id) REFERENCES scans(id),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            CREATE TABLE IF NOT EXISTS sync_events (
                id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT NOT NULL,
                action TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                payload TEXT DEFAULT '{}',
                sync_status TEXT DEFAULT 'PENDING',
                conflict_resolution TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                synced_at TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_scans_patient ON scans(patient_id);
            CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at);
            CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_log(entity_type, entity_id);
            CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
            CREATE INDEX IF NOT EXISTS idx_progression_scan ON progression_assessments(scan_id);
            CREATE INDEX IF NOT EXISTS idx_progression_patient ON progression_assessments(patient_id);
            CREATE INDEX IF NOT EXISTS idx_referrals_scan ON referrals(scan_id);
            CREATE INDEX IF NOT EXISTS idx_referrals_patient ON referrals(patient_id);
            CREATE INDEX IF NOT EXISTS idx_doc_reviews_scan ON doctor_reviews(scan_id);
            CREATE INDEX IF NOT EXISTS idx_doc_reviews_patient ON doctor_reviews(patient_id);
            CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_events(sync_status);
            CREATE INDEX IF NOT EXISTS idx_sync_entity ON sync_events(entity_type, entity_id);
        """)
        # Backward compatibility column migrations for existing SQLite file
        for col_def in ["actor_id TEXT DEFAULT 'system'", "actor_role TEXT DEFAULT 'SYSTEM'", "request_id TEXT DEFAULT ''"]:
            try:
                conn.execute(f"ALTER TABLE audit_log ADD COLUMN {col_def}")
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Schema migrations tracking table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT DEFAULT (datetime('now')),
                description TEXT
            );
        """)

        # Migration v1: Baseline tables
        conn.execute("""
            INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES (1, 'Baseline clinical tables, audit log, and sync events');
        """)

        # Migration v2: Screening sessions, safety attributes, and sync ledger extensions
        # 1. Add screening_sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS screening_sessions (
                session_id TEXT PRIMARY KEY,
                patient_id TEXT NOT NULL,
                operator_id TEXT NOT NULL,
                eye TEXT NOT NULL,
                current_state TEXT NOT NULL,
                image_hash TEXT DEFAULT '',
                safety_state TEXT DEFAULT 'VERIFIED',
                automation_level TEXT DEFAULT 'AUTOMATED_ASSISTANCE',
                reason_codes_json TEXT DEFAULT '[]',
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_patient ON screening_sessions(patient_id);")

        # 2. Add columns to scans table if missing
        scan_cols = [
            "laterality TEXT DEFAULT 'OD'",
            "operator_id TEXT DEFAULT 'operator-1'",
            "safety_state TEXT DEFAULT 'VERIFIED'",
            "automation_level TEXT DEFAULT 'AUTOMATED_ASSISTANCE'",
            "reason_codes_json TEXT DEFAULT '[]'",
            "image_hash TEXT DEFAULT ''",
            "device_id TEXT DEFAULT 'LOCAL-EDGE-01'",
            "screening_state TEXT DEFAULT 'FINALIZED'",
        ]
        for c in scan_cols:
            try:
                conn.execute(f"ALTER TABLE scans ADD COLUMN {c}")
            except sqlite3.OperationalError:
                pass

        # 3. Add columns to sync_events table if missing
        sync_cols = [
            "sync_attempt INTEGER DEFAULT 0",
            "retry_count INTEGER DEFAULT 0",
            "last_sync_at TEXT",
            "server_version INTEGER DEFAULT 1",
            "conflict_type TEXT DEFAULT ''",
            "sync_error TEXT DEFAULT ''",
        ]
        for c in sync_cols:
            try:
                conn.execute(f"ALTER TABLE sync_events ADD COLUMN {c}")
            except sqlite3.OperationalError:
                pass

        conn.execute("""
            INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES (2, 'Screening sessions, safety metadata, and sync ledger columns');
        """)

        # Migration v3: Audit log request_id correlation and unified schema
        conn.execute("""
            INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES (3, 'Audit log request_id correlation and unified schema');
        """)

        # Migration v4: Canonical schema indices & composite query optimization
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_patient_created ON scans(patient_id, created_at DESC);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_scans_safety ON scans(safety_state);")
        conn.execute("""
            INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES (4, 'Canonical schema indices and safety state optimization');
        """)

        # ---------------------------------------------------------------
        # Migration v5: Intelligence Control Plane — ML Platform Tables
        # ---------------------------------------------------------------
        conn.executescript("""
            -- Versioned training datasets
            CREATE TABLE IF NOT EXISTS training_datasets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                version TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'BUILDING',
                created_at TEXT DEFAULT (datetime('now')),
                finalized_at TEXT,
                total_samples INTEGER DEFAULT 0,
                total_patients INTEGER DEFAULT 0,
                class_distribution TEXT DEFAULT '{}',
                site_distribution TEXT DEFAULT '{}',
                device_distribution TEXT DEFAULT '{}',
                split_strategy TEXT DEFAULT 'patient_stratified',
                preprocessing_version TEXT DEFAULT '1.0',
                pipeline_version TEXT DEFAULT '1.0',
                git_sha TEXT DEFAULT '',
                manifest_checksum TEXT DEFAULT '',
                manifest_json TEXT DEFAULT '{}',
                exclusion_summary TEXT DEFAULT '{}',
                created_by TEXT DEFAULT 'system',
                UNIQUE(name, version)
            );

            -- Individual training sample records
            CREATE TABLE IF NOT EXISTS training_samples (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                scan_id TEXT NOT NULL,
                patient_id TEXT NOT NULL,
                split TEXT NOT NULL DEFAULT 'TRAIN',
                label INTEGER NOT NULL,
                label_provenance TEXT NOT NULL DEFAULT 'AI_ONLY',
                doctor_review_id TEXT DEFAULT '',
                eligibility_status TEXT NOT NULL DEFAULT 'ELIGIBLE',
                rejection_reason TEXT DEFAULT '',
                quality_score REAL DEFAULT 0.0,
                image_hash TEXT DEFAULT '',
                uncertainty_score REAL DEFAULT 0.0,
                active_learning_priority REAL DEFAULT 0.0,
                metadata_json TEXT DEFAULT '{}',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (dataset_id) REFERENCES training_datasets(id),
                FOREIGN KEY (scan_id) REFERENCES scans(id),
                FOREIGN KEY (patient_id) REFERENCES patients(id)
            );

            -- Training job records
            CREATE TABLE IF NOT EXISTS training_runs (
                id TEXT PRIMARY KEY,
                dataset_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'QUEUED',
                config_json TEXT DEFAULT '{}',
                parent_checkpoint TEXT DEFAULT '',
                started_at TEXT,
                completed_at TEXT,
                duration_seconds REAL DEFAULT 0,
                final_metrics_json TEXT DEFAULT '{}',
                best_checkpoint_path TEXT DEFAULT '',
                calibration_path TEXT DEFAULT '',
                history_json TEXT DEFAULT '[]',
                error_message TEXT DEFAULT '',
                git_sha TEXT DEFAULT '',
                triggered_by TEXT DEFAULT 'system',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (dataset_id) REFERENCES training_datasets(id)
            );

            -- Immutable model registry
            CREATE TABLE IF NOT EXISTS model_versions (
                version_id TEXT PRIMARY KEY,
                model_family TEXT NOT NULL DEFAULT 'drishti-retina',
                version_tag TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'EXPERIMENTAL',
                training_run_id TEXT DEFAULT '',
                dataset_id TEXT DEFAULT '',
                architecture TEXT DEFAULT 'EfficientNet-B3-Ordinal',
                input_schema TEXT DEFAULT '{}',
                output_schema TEXT DEFAULT '{}',
                preprocessing_version TEXT DEFAULT '1.0',
                calibration_version TEXT DEFAULT '1.0',
                threshold_schema TEXT DEFAULT '{}',
                weights_path TEXT DEFAULT '',
                weights_checksum TEXT DEFAULT '',
                calibration_path TEXT DEFAULT '',
                evaluation_summary_json TEXT DEFAULT '{}',
                compatibility_version TEXT DEFAULT '1.0',
                created_at TEXT DEFAULT (datetime('now')),
                promoted_at TEXT,
                archived_at TEXT,
                created_by TEXT DEFAULT 'system',
                FOREIGN KEY (training_run_id) REFERENCES training_runs(id),
                FOREIGN KEY (dataset_id) REFERENCES training_datasets(id),
                UNIQUE(model_family, version_tag)
            );

            -- Evaluation results per model version
            CREATE TABLE IF NOT EXISTS model_evaluations (
                id TEXT PRIMARY KEY,
                model_version_id TEXT NOT NULL,
                dataset_id TEXT DEFAULT '',
                eval_type TEXT NOT NULL DEFAULT 'STANDARD',
                metrics_json TEXT DEFAULT '{}',
                confusion_matrix_json TEXT DEFAULT '{}',
                per_class_json TEXT DEFAULT '{}',
                calibration_json TEXT DEFAULT '{}',
                regression_vs_production_json TEXT DEFAULT '{}',
                safety_gate_results_json TEXT DEFAULT '{}',
                passed_safety_gates INTEGER DEFAULT 0,
                evaluator_id TEXT DEFAULT 'system',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (model_version_id) REFERENCES model_versions(version_id),
                FOREIGN KEY (dataset_id) REFERENCES training_datasets(id)
            );

            -- Human approval records
            CREATE TABLE IF NOT EXISTS model_approvals (
                id TEXT PRIMARY KEY,
                model_version_id TEXT NOT NULL,
                evaluation_id TEXT DEFAULT '',
                decision TEXT NOT NULL DEFAULT 'PENDING',
                approver_id TEXT NOT NULL,
                approver_role TEXT NOT NULL,
                rationale TEXT DEFAULT '',
                conditions TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (model_version_id) REFERENCES model_versions(version_id),
                FOREIGN KEY (evaluation_id) REFERENCES model_evaluations(id)
            );

            -- Deployment history
            CREATE TABLE IF NOT EXISTS deployments (
                id TEXT PRIMARY KEY,
                model_version_id TEXT NOT NULL,
                environment TEXT NOT NULL DEFAULT 'staging',
                status TEXT NOT NULL DEFAULT 'DEPLOYING',
                approval_id TEXT DEFAULT '',
                deployed_by TEXT DEFAULT 'system',
                deployed_at TEXT DEFAULT (datetime('now')),
                rolled_back_at TEXT,
                rollback_reason TEXT DEFAULT '',
                previous_version_id TEXT DEFAULT '',
                FOREIGN KEY (model_version_id) REFERENCES model_versions(version_id),
                FOREIGN KEY (approval_id) REFERENCES model_approvals(id)
            );

            -- Drift observation events
            CREATE TABLE IF NOT EXISTS drift_events (
                id TEXT PRIMARY KEY,
                drift_type TEXT NOT NULL DEFAULT 'INPUT',
                severity TEXT NOT NULL DEFAULT 'NORMAL',
                model_version_id TEXT DEFAULT '',
                metrics_json TEXT DEFAULT '{}',
                detection_method TEXT DEFAULT '',
                window_start TEXT,
                window_end TEXT,
                sample_count INTEGER DEFAULT 0,
                details TEXT DEFAULT '',
                acknowledged_by TEXT DEFAULT '',
                acknowledged_at TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (model_version_id) REFERENCES model_versions(version_id)
            );

            -- Batch data quality assessments
            CREATE TABLE IF NOT EXISTS data_quality_events (
                id TEXT PRIMARY KEY,
                scan_id TEXT DEFAULT '',
                patient_id TEXT DEFAULT '',
                check_type TEXT NOT NULL,
                passed INTEGER NOT NULL DEFAULT 1,
                score REAL DEFAULT 0.0,
                details TEXT DEFAULT '',
                batch_id TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            );

            -- End-to-end pipeline orchestration records
            CREATE TABLE IF NOT EXISTS training_pipeline_runs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL DEFAULT 'INITIATED',
                dataset_id TEXT DEFAULT '',
                training_run_id TEXT DEFAULT '',
                model_version_id TEXT DEFAULT '',
                schedule_type TEXT DEFAULT 'manual',
                started_at TEXT DEFAULT (datetime('now')),
                completed_at TEXT,
                error_message TEXT DEFAULT '',
                report_json TEXT DEFAULT '{}',
                triggered_by TEXT DEFAULT 'system',
                FOREIGN KEY (dataset_id) REFERENCES training_datasets(id),
                FOREIGN KEY (training_run_id) REFERENCES training_runs(id),
                FOREIGN KEY (model_version_id) REFERENCES model_versions(version_id)
            );

            -- Indexes for Intelligence Control Plane queries
            CREATE INDEX IF NOT EXISTS idx_training_samples_dataset ON training_samples(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_training_samples_scan ON training_samples(scan_id);
            CREATE INDEX IF NOT EXISTS idx_training_samples_patient ON training_samples(patient_id);
            CREATE INDEX IF NOT EXISTS idx_training_samples_eligibility ON training_samples(eligibility_status);
            CREATE INDEX IF NOT EXISTS idx_training_runs_dataset ON training_runs(dataset_id);
            CREATE INDEX IF NOT EXISTS idx_training_runs_status ON training_runs(status);
            CREATE INDEX IF NOT EXISTS idx_model_versions_status ON model_versions(status);
            CREATE INDEX IF NOT EXISTS idx_model_approvals_version ON model_approvals(model_version_id);
            CREATE INDEX IF NOT EXISTS idx_drift_events_severity ON drift_events(severity);
            CREATE INDEX IF NOT EXISTS idx_drift_events_model ON drift_events(model_version_id);
            CREATE INDEX IF NOT EXISTS idx_data_quality_scan ON data_quality_events(scan_id);
            CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status ON training_pipeline_runs(status);
        """)

        conn.execute("""
            INSERT OR IGNORE INTO schema_migrations (version, description)
            VALUES (5, 'Intelligence Control Plane: datasets, samples, runs, model registry, approvals, drift, quality events');
        """)

        conn.commit()
    log.info("Database initialized at %s", DB_PATH)


def _audit(conn, action: str, entity_type: str, entity_id: str, details: str = "", actor_id: str = "system", actor_role: str = "SYSTEM", request_id: str = ""):
    """Record an audit trail entry with actor provenance and request correlation."""
    try:
        from flask import g, has_request_context
        if has_request_context():
            if not request_id and hasattr(g, "request_id"):
                request_id = str(g.request_id)
            if actor_id == "system" and hasattr(g, "current_user") and g.current_user:
                actor_id = g.current_user.get("actor_id", "system")
                actor_role = g.current_user.get("actor_role", "SYSTEM")
    except Exception:
        pass
    conn.execute(
        "INSERT INTO audit_log (action, entity_type, entity_id, actor_id, actor_role, request_id, details) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (action, entity_type, entity_id, _sanitize_string(actor_id, 100), _sanitize_string(actor_role, 50), _sanitize_string(request_id, 100), _sanitize_string(details, 2000))
    )


def log_audit_event(action: str, entity_type: str, entity_id: str, details: str = "", actor_id: str = "system", actor_role: str = "SYSTEM", request_id: str = ""):
    """Public wrapper to record audit log events."""
    with get_db() as conn:
        _audit(conn, action, entity_type, entity_id, details, actor_id, actor_role, request_id)
        conn.commit()


# === Screening Sessions CRUD ===

def create_or_update_screening_session(
    session_id: str,
    patient_id: str,
    operator_id: str,
    eye: str,
    current_state: str,
    image_hash: str = "",
    safety_state: str = "VERIFIED",
    automation_level: str = "AUTOMATED_ASSISTANCE",
    reason_codes: list = None,
):
    """Create or update a screening session record."""
    rc_json = json.dumps(reason_codes or [])
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO screening_sessions (
                session_id, patient_id, operator_id, eye, current_state,
                image_hash, safety_state, automation_level, reason_codes_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(session_id) DO UPDATE SET
                current_state = excluded.current_state,
                image_hash = excluded.image_hash,
                safety_state = excluded.safety_state,
                automation_level = excluded.automation_level,
                reason_codes_json = excluded.reason_codes_json,
                updated_at = datetime('now')
            """,
            (session_id, patient_id, operator_id, eye, current_state, image_hash, safety_state, automation_level, rc_json)
        )
        _audit(conn, "SESSION_UPDATE", "screening_session", session_id, f"state={current_state}", operator_id, "OPERATOR")
        conn.commit()


def get_screening_session(session_id: str):
    """Retrieve a screening session by session_id."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM screening_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            return None
        d = dict(row)
        if d.get("reason_codes_json"):
            try:
                d["reason_codes"] = json.loads(d["reason_codes_json"])
            except Exception:
                d["reason_codes"] = []
        return d


def update_screening_session_state(
    session_id: str,
    new_state: str,
    actor_id: str = "operator-1",
    reason: str = "",
    validate_transition: bool = True,
    actor_role: str | None = None,
):
    """Update state of an existing screening session with lifecycle enforcement."""
    with get_db() as conn:
        row = conn.execute("SELECT current_state FROM screening_sessions WHERE session_id = ?", (session_id,)).fetchone()
        if row and validate_transition:
            current_state = row["current_state"]
            if current_state and current_state != new_state:
                from engine.safety.state_machine import ALLOWED_TRANSITIONS, InvalidStateTransitionError
                allowed = ALLOWED_TRANSITIONS.get(current_state, set())
                # Clinically allow doctor/admin sign-off/finalize/cancel from active states
                is_doctor_override = (
                    new_state in ("FINALIZED", "CANCELLED") and
                    (
                        (actor_role and actor_role.upper() in ("DOCTOR", "ADMIN")) or
                        actor_id.startswith("dr-") or "doctor" in actor_id.lower() or "doc" in actor_id.lower()
                    )
                )
                if new_state not in allowed and not is_doctor_override:
                    raise InvalidStateTransitionError(
                        f"Illegal state transition from {current_state} to {new_state} by {actor_id}"
                    )

        is_human_override = (
            (actor_role and actor_role.upper() in ("DOCTOR", "ADMIN", "HEALTH_WORKER")) or
            actor_id.startswith("dr-") or "operator" in actor_id.lower() or "confirm" in reason.lower()
        )
        aut_level = "HUMAN_CONFIRMED" if (is_human_override and new_state in ("ANATOMY_VALIDATED", "FINALIZED") and ("override" in reason.lower() or "confirm" in reason.lower())) else None

        if aut_level:
            conn.execute(
                "UPDATE screening_sessions SET current_state = ?, automation_level = ?, updated_at = datetime('now') WHERE session_id = ?",
                (new_state, aut_level, session_id)
            )
        else:
            conn.execute(
                "UPDATE screening_sessions SET current_state = ?, updated_at = datetime('now') WHERE session_id = ?",
                (new_state, session_id)
            )
        audit_details = f"to_state={new_state} reason={reason} is_human_override={bool(aut_level == 'HUMAN_CONFIRMED')}"
        _audit(conn, "SESSION_STATE_TRANSITION", "screening_session", session_id, audit_details, actor_id, actor_role or "OPERATOR")
        conn.commit()


def generate_patient_id():
    """Generate a monotonically increasing unique patient ID like P-0001, immune to deletions and concurrent race conditions."""
    with _patient_id_lock:
        with get_db() as conn:
            row = conn.execute("""
                SELECT COALESCE(MAX(CAST(SUBSTR(id, 3) AS INTEGER)), 0) AS max_id 
                FROM patients 
                WHERE id LIKE 'P-%'
            """).fetchone()
            next_num = (row["max_id"] if row else 0) + 1
            while True:
                candidate = f"P-{next_num:04d}"
                exists = conn.execute("SELECT 1 FROM patients WHERE id = ?", (candidate,)).fetchone()
                if not exists:
                    return candidate
                next_num += 1


# === Patient CRUD & Input Validation ===

def validate_patient_metrics(
    age: Any = None,
    diabetes_duration: Any = None,
    sugar_level: Any = None,
    hba1c: Any = None
) -> None:
    """Enforce physiological and clinical validity bounds on patient measurements."""
    if age is not None:
        try:
            a = int(age)
            if a < 0 or a > 130:
                raise ValueError(f"Patient age {a} is outside valid clinical range (0-130 years).")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid patient age: {e}")

    if diabetes_duration is not None:
        try:
            d = float(diabetes_duration)
            if d < 0.0 or d > 80.0:
                raise ValueError(f"Diabetes duration {d} is outside valid clinical range (0-80 years).")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid diabetes duration: {e}")

    if sugar_level is not None:
        try:
            s = float(sugar_level)
            if s < 20.0 or s > 1000.0:
                raise ValueError(f"Blood sugar level {s} mg/dL is outside valid clinical range (20-1000 mg/dL).")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid blood sugar level: {e}")

    if hba1c is not None:
        try:
            h = float(hba1c)
            if h < 3.0 or h > 20.0:
                raise ValueError(f"HbA1c level {h}% is outside valid clinical range (3.0-20.0%).")
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid HbA1c level: {e}")


def create_patient(name, age=None, gender='', diabetes_duration=None,
                   sugar_level=None, hba1c=None, notes=''):
    """Create a new patient record with collision-proof atomic allocation and clinical bounds enforcement."""
    if not name or not str(name).strip():
        raise ValueError("Patient name cannot be empty.")
    validate_patient_metrics(age=age, diabetes_duration=diabetes_duration, sugar_level=sugar_level, hba1c=hba1c)

    with _patient_id_lock:
        with get_db() as conn:
            for attempt in range(10):
                row = conn.execute("""
                    SELECT COALESCE(MAX(CAST(SUBSTR(id, 3) AS INTEGER)), 0) AS max_id 
                    FROM patients 
                    WHERE id LIKE 'P-%'
                """).fetchone()
                next_num = (row["max_id"] if row else 0) + 1 + attempt
                pid = f"P-{next_num:04d}"
                try:
                    conn.execute(
                        """INSERT INTO patients (id, name, age, gender, diabetes_duration,
                           sugar_level, hba1c, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (pid, _sanitize_string(name), age, _sanitize_string(gender, 50),
                         diabetes_duration, sugar_level, hba1c, _sanitize_string(notes))
                    )
                    _audit(conn, "CREATE", "patient", pid, f"name={name}")
                    conn.commit()
                    patient = conn.execute("SELECT * FROM patients WHERE id = ?", (pid,)).fetchone()
                    return dict(patient)
                except sqlite3.IntegrityError:
                    continue
                except Exception as e:
                    conn.rollback()
                    raise e
            raise RuntimeError("Failed to allocate a unique patient ID after 10 attempts.")


def get_patient(patient_id):
    """Get a single patient by ID."""
    _validate_patient_id(patient_id)
    with get_db() as conn:
        row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if row:
        patient = dict(row)
        patient['scans'] = get_patient_scans(patient_id)
        return patient
    return None


def get_all_patients(search='', limit=100, offset=0):
    """Get all patients with latest scan info in a single optimized query (N+1 fix)."""
    with get_db() as conn:
        base_query = """
            SELECT
                p.*,
                COUNT(s.id) as scan_count,
                ls.stage as latest_stage,
                ls.stage_name as latest_stage_name,
                ls.confidence as latest_confidence,
                ls.created_at as latest_scan_date
            FROM patients p
            LEFT JOIN scans s ON s.patient_id = p.id
            LEFT JOIN (
                SELECT patient_id, stage, stage_name, confidence, created_at,
                       ROW_NUMBER() OVER (PARTITION BY patient_id ORDER BY created_at DESC) as rn
                FROM scans
            ) ls ON ls.patient_id = p.id AND ls.rn = 1
        """

        if search:
            search_param = f'%{_sanitize_string(search, 100)}%'
            rows = conn.execute(
                base_query + " WHERE p.name LIKE ? OR p.id LIKE ? GROUP BY p.id ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
                (search_param, search_param, limit, offset)
            ).fetchall()
        else:
            rows = conn.execute(
                base_query + " GROUP BY p.id ORDER BY p.created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            ).fetchall()

    patients = []
    for row in rows:
        p = dict(row)
        # Build latest_scan dict from the JOIN columns
        if p.get('latest_stage') is not None:
            p['latest_scan'] = {
                'stage': p['latest_stage'],
                'stage_name': p['latest_stage_name'],
                'confidence': p['latest_confidence'],
                'created_at': p['latest_scan_date'],
            }
        else:
            p['latest_scan'] = None
        # Clean up the extra columns
        for k in ('latest_stage', 'latest_stage_name', 'latest_confidence', 'latest_scan_date'):
            p.pop(k, None)
        patients.append(p)

    return patients


def update_patient(patient_id, **kwargs):
    """Update patient fields. Only allowlisted columns can be modified."""
    _validate_patient_id(patient_id)
    # Strict allowlist check to prevent SQL injection via dynamic column names
    updates = {k: v for k, v in kwargs.items() if k in _ALLOWED_PATIENT_COLS and v is not None}
    disallowed = set(kwargs.keys()) - _ALLOWED_PATIENT_COLS
    if disallowed:
        log.warning("Blocked disallowed update columns: %s", disallowed)

    if not updates:
        return get_patient(patient_id)

    if "name" in updates and not str(updates["name"]).strip():
        raise ValueError("Patient name cannot be empty.")

    validate_patient_metrics(
        age=updates.get("age"),
        diabetes_duration=updates.get("diabetes_duration"),
        sugar_level=updates.get("sugar_level"),
        hba1c=updates.get("hba1c"),
    )

    # Sanitize string values
    for k, v in updates.items():
        if isinstance(v, str):
            updates[k] = _sanitize_string(v)

    set_clause = ', '.join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [patient_id]

    with get_db() as conn:
        conn.execute(f"UPDATE patients SET {set_clause}, updated_at = datetime('now') WHERE id = ?", values)
        _audit(conn, "UPDATE", "patient", patient_id, json.dumps(list(updates.keys())))
        conn.commit()
    return get_patient(patient_id)


def delete_patient(patient_id):
    """Delete a patient and all their scans, assessments, and reviews."""
    _validate_patient_id(patient_id)
    with get_db() as conn:
        conn.execute("DELETE FROM doctor_reviews WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM progression_assessments WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM referrals WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM scans WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM screening_sessions WHERE patient_id = ?", (patient_id,))
        conn.execute("DELETE FROM patients WHERE id = ?", (patient_id,))
        _audit(conn, "DELETE", "patient", patient_id)
        conn.commit()


# === Workflow Consistency & Scan CRUD ===

def check_workflow_image_consistency(
    image_hash: str,
    dhash: str = "",
    patient_id: str = "",
    session_id: str | None = None,
    eye: str | None = None,
) -> list[str]:
    """
    Detect workflow-level discrepancies:
    - Same image attached to two different patients
    - Same image attached to two conflicting laterality eyes (OD vs OS)
    - Prior study reused in new session
    """
    warnings = []
    if not image_hash and not dhash:
        return warnings

    with get_db() as conn:
        if image_hash:
            rows = conn.execute(
                "SELECT id, patient_id, laterality, created_at FROM scans WHERE image_hash = ?",
                (image_hash,)
            ).fetchall()
            for r in rows:
                if patient_id and r["patient_id"] != patient_id:
                    warnings.append(
                        f"WORKFLOW_CROSS_PATIENT_DUPLICATE: CROSS_PATIENT_DUPLICATE_IMAGE_DETECTED - Image hash matches scan {r['id']} of patient {r['patient_id']}."
                    )
                if eye and r["laterality"] and str(eye).upper() != str(r["laterality"]).upper():
                    warnings.append(
                        f"WORKFLOW_LATERALITY_STUDY_CONFLICT: CROSS_EYE_IMAGE_REUSE_DETECTED - Image previously submitted as {r['laterality']} for scan {r['id']}."
                    )
                if patient_id and r["patient_id"] == patient_id and session_id and str(r["id"]) != str(session_id):
                    warnings.append(
                        f"WORKFLOW_HISTORICAL_IMAGE_REUSE: Prior scan {r['id']} matches submitted image for this patient."
                    )

        if dhash:
            # Check perceptual hash against past scans if dhash length is 16 hex characters
            try:
                cur_val = int(dhash, 16)
                past_scans = conn.execute("SELECT id, patient_id, laterality, image_hash FROM scans").fetchall()
                for s in past_scans:
                    shash = s["image_hash"]
                    if shash and len(shash) == 16:
                        try:
                            s_val = int(shash, 16)
                            dist = bin(cur_val ^ s_val).count("1")
                            if dist <= 4:
                                if patient_id and s["patient_id"] != patient_id:
                                    warnings.append(
                                        f"WORKFLOW_CROSS_PATIENT_DUPLICATE: CROSS_PATIENT_DUPLICATE_IMAGE_DETECTED - Perceptual dHash matches scan {s['id']} of patient {s['patient_id']} (Hamming dist={dist})."
                                    )
                                if eye and s["laterality"] and str(eye).upper() != str(s["laterality"]).upper():
                                    warnings.append(
                                        f"WORKFLOW_LATERALITY_STUDY_CONFLICT: CROSS_EYE_IMAGE_REUSE_DETECTED - Perceptual dHash matches opposite eye {s['laterality']} for scan {s['id']} (Hamming dist={dist})."
                                    )
                        except (ValueError, TypeError):
                            pass
            except (ValueError, TypeError):
                pass

    return list(set(warnings))


def save_scan(scan_id, patient_id, detection_result, heatmap_analysis,
              vessel_stats, report, image_paths, processing_time,
              laterality='OD', operator_id='operator-1', safety_state='VERIFIED',
              automation_level='AUTOMATED_ASSISTANCE', reason_codes=None,
              image_hash='', device_id='LOCAL-EDGE-01', screening_state='FINALIZED'):
    """Save a completed scan to the database idempotently with safety invariants."""
    if isinstance(patient_id, dict):
        patient_id = patient_id.get("id") or patient_id.get("patient_id")
    # Persistence Invariant: Unsafe scans cannot be persisted as normal cleared diagnoses
    if safety_state in ("MODEL_FAILURE", "ANATOMY_FAILED", "QUALITY_FAILED", "REJECTED"):
        detection_result = dict(detection_result)
        detection_result["stage_name"] = f"Ungradeable ({safety_state})"
        automation_level = "UNABLE_TO_CLASSIFY"
        if screening_state == "FINALIZED":
            screening_state = "RECOVERY_REQUIRED"

    reason_codes_str = json.dumps(reason_codes or [])
    with get_db() as conn:
        try:
            conn.execute(
                """INSERT INTO scans (id, patient_id, stage, stage_name, confidence,
                   severity, color, all_probabilities, model_used, heatmap_analysis,
                   vessel_stats, report, image_original, image_heatmap, image_vessels,
                   processing_time, laterality, operator_id, safety_state,
                   automation_level, reason_codes_json, image_hash, device_id, screening_state)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       stage = excluded.stage,
                       stage_name = excluded.stage_name,
                       confidence = excluded.confidence,
                       severity = excluded.severity,
                       color = excluded.color,
                       all_probabilities = excluded.all_probabilities,
                       model_used = excluded.model_used,
                       heatmap_analysis = excluded.heatmap_analysis,
                       vessel_stats = excluded.vessel_stats,
                       report = excluded.report,
                       image_original = excluded.image_original,
                       image_heatmap = excluded.image_heatmap,
                       image_vessels = excluded.image_vessels,
                       processing_time = excluded.processing_time,
                       laterality = excluded.laterality,
                       operator_id = excluded.operator_id,
                       safety_state = excluded.safety_state,
                       automation_level = excluded.automation_level,
                       reason_codes_json = excluded.reason_codes_json,
                       image_hash = excluded.image_hash,
                       screening_state = excluded.screening_state""",
                (
                    scan_id, patient_id,
                    detection_result.get('stage', 0),
                    detection_result.get('stage_name', 'Unknown'),
                    detection_result.get('confidence', 0),
                    detection_result.get('severity', ''),
                    detection_result.get('color', ''),
                    json.dumps(detection_result.get('all_probabilities', {})),
                    detection_result.get('_model', 'unknown'),
                    json.dumps(heatmap_analysis),
                    json.dumps(vessel_stats),
                    json.dumps(report),
                    image_paths.get('original', ''),
                    image_paths.get('heatmap', ''),
                    image_paths.get('vessels', ''),
                    processing_time,
                    laterality,
                    operator_id,
                    safety_state,
                    automation_level,
                    reason_codes_str,
                    image_hash,
                    device_id,
                    screening_state,
                )
            )
            _audit(conn, "CREATE_OR_UPDATE", "scan", scan_id,
                   f"patient={patient_id} stage={detection_result.get('stage', '?')}")
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e


def get_patient_scans(patient_id):
    """Get all scans for a patient, newest first."""
    _validate_patient_id(patient_id)
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM scans WHERE patient_id = ? ORDER BY created_at DESC, rowid DESC",
            (patient_id,)
        ).fetchall()

    scans = []
    for row in rows:
        s = dict(row)
        # Parse JSON fields
        for field in ['all_probabilities', 'heatmap_analysis', 'vessel_stats', 'report']:
            try:
                s[field] = json.loads(s[field]) if s[field] else {}
            except (json.JSONDecodeError, TypeError):
                s[field] = {}
        scans.append(s)
    return scans


def get_scan(scan_id):
    """Get a single scan by ID."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    if row:
        s = dict(row)
        for field in ['all_probabilities', 'heatmap_analysis', 'vessel_stats', 'report']:
            try:
                s[field] = json.loads(s[field]) if s[field] else {}
            except (json.JSONDecodeError, TypeError):
                s[field] = {}
        return s
    return None


# === Dashboard Stats ===

def get_dashboard_stats():
    """Get overview statistics for the dashboard."""
    with get_db() as conn:
        total_patients = conn.execute("SELECT COUNT(*) as cnt FROM patients").fetchone()['cnt']
        total_scans = conn.execute("SELECT COUNT(*) as cnt FROM scans").fetchone()['cnt']

        # Stage distribution
        stage_dist = {}
        rows = conn.execute(
            "SELECT stage, stage_name, COUNT(*) as cnt FROM scans GROUP BY stage ORDER BY stage"
        ).fetchall()
        for row in rows:
            stage_dist[row['stage']] = {'name': row['stage_name'], 'count': row['cnt']}

        # Recent scans (single query with JOIN)
        recent = conn.execute("""
            SELECT s.*, p.name as patient_name
            FROM scans s JOIN patients p ON s.patient_id = p.id
            ORDER BY s.created_at DESC LIMIT 5
        """).fetchall()

    recent_scans = []
    for row in recent:
        r = dict(row)
        try:
            r['report'] = json.loads(r['report']) if r['report'] else {}
        except (json.JSONDecodeError, TypeError):
            r['report'] = {}
        recent_scans.append(r)

    return {
        'total_patients': total_patients,
        'total_scans': total_scans,
        'stage_distribution': stage_dist,
        'recent_scans': recent_scans,
    }


# === Progression & Referral Persistence ===

def save_progression_assessment(scan_id: str, patient_id: str, progression_data: dict) -> dict:
    """Save or update a progression assessment for a scan idempotently."""
    predicted = progression_data.get("predicted_risk") or {}
    risk_cat = str(predicted.get("risk_category", "LOW")).upper()
    six_m = float(predicted.get("six_month_risk", 0.0))
    twelve_m = float(predicted.get("twelve_month_risk", 0.0))

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM progression_assessments WHERE scan_id = ? ORDER BY created_at DESC LIMIT 1",
            (scan_id,)
        ).fetchone()
        assessment_id = existing["id"] if existing else f"prog-{uuid.uuid4().hex[:12]}"

        conn.execute(
            """INSERT OR REPLACE INTO progression_assessments
               (id, scan_id, patient_id, risk_category, six_month_risk, twelve_month_risk, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (assessment_id, scan_id, patient_id, risk_cat, six_m, twelve_m, json.dumps(progression_data))
        )
        _audit(conn, "SAVE", "progression_assessment", scan_id, f"risk={risk_cat}")
        conn.commit()
    return {"id": assessment_id, "scan_id": scan_id, "risk_category": risk_cat}


def get_progression_assessment(scan_id: str) -> dict | None:
    """Retrieve progression assessment for a scan."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM progression_assessments WHERE scan_id = ? ORDER BY created_at DESC LIMIT 1",
            (scan_id,)
        ).fetchone()
    if not row:
        return None
    res = dict(row)
    try:
        res["payload"] = json.loads(res["payload"]) if res.get("payload") else {}
    except (json.JSONDecodeError, TypeError):
        res["payload"] = {}
    return res


def save_referral(
    scan_id: str,
    patient_id: str,
    triage_data: dict,
    doctor_review_status: str = "PENDING",
    doctor_notes: str = ""
) -> dict:
    """Save or update referral triage record for a scan idempotently."""
    priority = str(triage_data.get("priority", "ROUTINE")).upper()
    reason_codes = triage_data.get("reasonCodes", [])
    human_review = 1 if triage_data.get("humanReviewRequired", False) else 0

    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM referrals WHERE scan_id = ? ORDER BY created_at DESC LIMIT 1",
            (scan_id,)
        ).fetchone()
        referral_id = existing["id"] if existing else f"ref-{uuid.uuid4().hex[:12]}"

        conn.execute(
            """INSERT OR REPLACE INTO referrals
               (id, scan_id, patient_id, priority, reason_codes, human_review_required,
                doctor_review_status, doctor_notes, payload)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                referral_id, scan_id, patient_id, priority,
                json.dumps(reason_codes), human_review,
                _sanitize_string(doctor_review_status, 50),
                _sanitize_string(doctor_notes, 2000),
                json.dumps(triage_data)
            )
        )
        _audit(conn, "SAVE", "referral", scan_id, f"priority={priority}")
        conn.commit()
    return {"id": referral_id, "scan_id": scan_id, "priority": priority}


def get_referral(scan_id: str) -> dict | None:
    """Retrieve referral record for a scan."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM referrals WHERE scan_id = ? ORDER BY created_at DESC LIMIT 1",
            (scan_id,)
        ).fetchone()
    if not row:
        return None
    res = dict(row)
    for k in ["reason_codes", "payload"]:
        try:
            res[k] = json.loads(res[k]) if res.get(k) else {}
        except (json.JSONDecodeError, TypeError):
            res[k] = {} if k == "payload" else []
    return res


def save_doctor_review(
    scan_id: str,
    patient_id: str,
    doctor_id: str,
    decision: str,
    original_stage: int,
    adjusted_stage: int | None,
    approved_priority: str,
    doctor_name: str = "",
    clinical_notes: str = "",
    recommended_intervention: str = ""
) -> dict:
    """Record clinician evaluation/sign-off with strict validation and update referral triage status."""
    if not doctor_id or not str(doctor_id).strip():
        raise ValueError("doctor_id is required for clinician review.")

    decision_clean = str(decision).upper().strip()
    if decision_clean not in ("APPROVED", "MODIFIED", "REJECTED_RETAKE"):
        raise ValueError(f"Invalid review decision: '{decision}'. Must be APPROVED, MODIFIED, or REJECTED_RETAKE.")

    orig_stage = int(original_stage)
    if orig_stage < 0 or orig_stage > 4:
        raise ValueError(f"Invalid original_stage: {orig_stage}. Must be in range 0-4.")

    adj_stage = None
    if adjusted_stage is not None:
        adj_stage = int(adjusted_stage)
        if adj_stage < 0 or adj_stage > 4:
            raise ValueError(f"Invalid adjusted_stage: {adj_stage}. Must be in range 0-4.")

    priority_clean = str(approved_priority).upper().strip()
    if priority_clean not in ("ROUTINE", "EARLY", "URGENT", "EMERGENCY"):
        raise ValueError(f"Invalid approved_priority: '{approved_priority}'. Must be ROUTINE, EARLY, URGENT, or EMERGENCY.")

    review_id = f"rev-{uuid.uuid4().hex[:12]}"

    with get_db() as conn:
        p_row = conn.execute("SELECT id FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not p_row:
            raise ValueError(f"Patient '{patient_id}' not found in database.")
        conn.execute(
            """INSERT OR REPLACE INTO doctor_reviews
               (id, scan_id, patient_id, doctor_id, doctor_name, decision,
                original_stage, adjusted_stage, approved_priority,
                clinical_notes, recommended_intervention)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                review_id, scan_id, patient_id, _sanitize_string(doctor_id, 100),
                _sanitize_string(doctor_name, 100), decision_clean,
                int(original_stage), int(adjusted_stage) if adjusted_stage is not None else None,
                priority_clean, _sanitize_string(clinical_notes, 2000),
                _sanitize_string(recommended_intervention, 500)
            )
        )
        # Synchronize referral record with doctor's verified status
        conn.execute(
            """UPDATE referrals
               SET doctor_review_status = ?, priority = ?,
                   doctor_notes = CASE WHEN doctor_notes = '' THEN ? ELSE doctor_notes || '; ' || ? END
               WHERE scan_id = ?""",
            (decision_clean, priority_clean, clinical_notes, clinical_notes, scan_id)
        )
        _audit(conn, "SIGN_OFF", "doctor_review", scan_id, f"doctor={doctor_id} decision={decision_clean}")
        conn.commit()

    return {
        "id": review_id,
        "scan_id": scan_id,
        "decision": decision_clean,
        "approved_priority": priority_clean,
    }


def get_doctor_review(scan_id: str) -> dict | None:
    """Retrieve clinician review for a scan."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM doctor_reviews WHERE scan_id = ? ORDER BY created_at DESC LIMIT 1",
            (scan_id,)
        ).fetchone()
    return dict(row) if row else None


def get_patient_timeline(patient_id: str) -> dict:
    """
    Get chronological longitudinal timeline for a patient,
    combining scans, progression risks, triage referrals, and clinician reviews.
    """
    _validate_patient_id(patient_id)
    with get_db() as conn:
        p_row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
        if not p_row:
            raise ValueError(f"Patient {patient_id} not found.")

        # Get scans in chronological order (oldest to newest, with rowid tie-breaker)
        scan_rows = conn.execute(
            "SELECT * FROM scans WHERE patient_id = ? ORDER BY created_at ASC, rowid ASC",
            (patient_id,)
        ).fetchall()

    timeline_events = []
    prev_stage = None
    prev_date = None

    for r in scan_rows:
        s = dict(r)
        scan_id = s["id"]
        created_at = s.get("created_at", "")

        # Attach progression if exists
        prog = get_progression_assessment(scan_id)
        # Attach referral if exists
        ref = get_referral(scan_id)
        # Attach doctor review if exists
        doc_rev = get_doctor_review(scan_id)

        curr_stage = s.get("stage", 0)
        stage_delta = curr_stage - prev_stage if prev_stage is not None else None

        review_status = doc_rev.get("decision") if doc_rev else (ref.get("doctor_review_status", "PENDING") if ref else "PENDING")

        timeline_events.append({
            "scan_id": scan_id,
            "patient_id": patient_id,
            "date": created_at,
            "stage": curr_stage,
            "stage_name": s.get("stage_name", "Unknown"),
            "confidence": s.get("confidence", 0.0),
            "severity": s.get("severity", ""),
            "stage_delta": stage_delta,
            "progression": prog.get("payload") if prog else None,
            "referral": ref.get("payload") if ref else None,
            "doctor_review": doc_rev,
            "doctor_review_status": review_status,
            "image_thumbnail": s.get("image_original", ""),
        })

        prev_stage = curr_stage
        prev_date = created_at

    return {
        "patient": dict(p_row),
        "total_events": len(timeline_events),
        "events": timeline_events,
    }


# === Offline Sync Ledger & Conflict Reconciliation ===

def record_sync_event(
    device_id: str,
    entity_type: str,
    entity_id: str,
    action: str,
    payload: dict,
    version: int = 1
) -> str:
    """Record an offline edge change event into the sync ledger."""
    event_id = f"sync-{uuid.uuid4().hex[:12]}"
    with get_db() as conn:
        conn.execute(
            """INSERT INTO sync_events
               (id, device_id, entity_type, entity_id, action, version, payload, sync_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'PENDING')""",
            (
                event_id, _sanitize_string(device_id, 100),
                _sanitize_string(entity_type, 50), entity_id,
                _sanitize_string(action, 20).upper(), int(version),
                json.dumps(payload)
            )
        )
        conn.commit()
    return event_id


def get_pending_sync_events(device_id: str | None = None, limit: int = 100) -> list[dict]:
    """Retrieve pending sync events for replication."""
    with get_db() as conn:
        if device_id:
            rows = conn.execute(
                "SELECT * FROM sync_events WHERE sync_status = 'PENDING' AND device_id = ? ORDER BY created_at ASC LIMIT ?",
                (device_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sync_events WHERE sync_status = 'PENDING' ORDER BY created_at ASC LIMIT ?",
                (limit,)
            ).fetchall()

    events = []
    for r in rows:
        item = dict(r)
        try:
            item["payload"] = json.loads(item["payload"]) if item.get("payload") else {}
        except Exception:
            item["payload"] = {}
        events.append(item)
    return events


def reconcile_sync_batch(incoming_events: list[dict]) -> dict:
    """
    Reconcile an incoming batch of sync events from an edge device.
    Follows deterministic version-based arbitration:
    - If local version is newer: status is CONFLICT_REQUIRES_REVIEW, preserves local version.
    - If incoming version >= local version: status is SYNCED and changes are transactionally applied.
    """
    synced_ids = []
    conflict_ids = []

    with get_db() as conn:
        for evt in incoming_events:
            event_id = evt.get("id") or f"sync-{uuid.uuid4().hex[:12]}"
            device_id = evt.get("device_id", "unknown-edge")
            entity_type = str(evt.get("entity_type", "unknown")).lower()
            entity_id = evt.get("entity_id", "")
            action = str(evt.get("action", "UPDATE")).upper()
            payload = evt.get("payload") or {}
            incoming_version = int(evt.get("version", 1))

            # Idempotency check: if event_id or exact (entity_id, version) already processed
            already = conn.execute(
                "SELECT sync_status FROM sync_events WHERE id = ? OR (entity_id = ? AND version = ? AND sync_status = 'SYNCED')",
                (event_id, entity_id, incoming_version)
            ).fetchone()
            if already and already["sync_status"] == "SYNCED":
                if entity_id not in synced_ids:
                    synced_ids.append(entity_id)
                continue

            # Check if local record has higher version
            existing = conn.execute(
                "SELECT version, sync_status FROM sync_events WHERE entity_id = ? ORDER BY version DESC LIMIT 1",
                (entity_id,)
            ).fetchone()

            if existing and existing["version"] > incoming_version:
                # Conflict detected: local version is strictly newer
                conn.execute(
                    """INSERT OR REPLACE INTO sync_events
                       (id, device_id, entity_type, entity_id, action, version, payload, sync_status, conflict_resolution, conflict_type, synced_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'CONFLICT_REQUIRES_REVIEW', 'Retained local newer version', 'VERSION_SKEW', datetime('now'))""",
                    (event_id, device_id, entity_type, entity_id, action, incoming_version, json.dumps(payload))
                )
                conflict_ids.append(entity_id)
            else:
                # Clean apply to ledger
                conn.execute(
                    """INSERT OR REPLACE INTO sync_events
                       (id, device_id, entity_type, entity_id, action, version, payload, sync_status, synced_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, 'SYNCED', datetime('now'))""",
                    (event_id, device_id, entity_type, entity_id, action, incoming_version, json.dumps(payload))
                )

                # Transactionally apply entity state to canonical tables if payload provided
                if isinstance(payload, dict) and payload and entity_id:
                    if entity_type == "patient":
                        p_exists = conn.execute("SELECT id FROM patients WHERE id = ?", (entity_id,)).fetchone()
                        if p_exists:
                            for col in _ALLOWED_PATIENT_COLS:
                                if col in payload and payload[col] is not None:
                                    conn.execute(
                                        f"UPDATE patients SET {col} = ?, updated_at = datetime('now') WHERE id = ?",
                                        (_sanitize_string(str(payload[col])) if isinstance(payload[col], str) else payload[col], entity_id)
                                    )
                        else:
                            name = payload.get("name", "Unknown Synced Patient")
                            conn.execute(
                                """INSERT INTO patients (id, name, age, gender, diabetes_duration, sugar_level, hba1c, notes)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                                (entity_id, _sanitize_string(name), payload.get("age"), _sanitize_string(payload.get("gender", ""), 50),
                                 payload.get("diabetes_duration"), payload.get("sugar_level"), payload.get("hba1c"),
                                 _sanitize_string(payload.get("notes", "")))
                            )
                    elif entity_type == "doctor_review":
                        conn.execute(
                            """INSERT INTO doctor_reviews (
                                id, scan_id, patient_id, doctor_id, doctor_name, decision,
                                original_stage, adjusted_stage, approved_priority, clinical_notes, recommended_intervention
                               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                               ON CONFLICT(id) DO UPDATE SET
                                 decision = excluded.decision,
                                 adjusted_stage = excluded.adjusted_stage,
                                 approved_priority = excluded.approved_priority,
                                 clinical_notes = excluded.clinical_notes,
                                 recommended_intervention = excluded.recommended_intervention
                            """,
                            (
                                entity_id,
                                payload.get("scan_id", ""),
                                payload.get("patient_id", ""),
                                payload.get("doctor_id", "unknown-doc"),
                                payload.get("doctor_name", ""),
                                payload.get("decision", "APPROVED"),
                                int(payload.get("original_stage", 0)),
                                payload.get("adjusted_stage"),
                                payload.get("approved_priority", "ROUTINE"),
                                payload.get("clinical_notes", ""),
                                payload.get("recommended_intervention", "")
                            )
                        )

                synced_ids.append(entity_id)

        conn.commit()

    return {
        "synced_count": len(synced_ids),
        "synced_ids": synced_ids,
        "conflict_count": len(conflict_ids),
        "conflict_ids": conflict_ids,
        "server_timestamp": datetime.utcnow().isoformat() + "Z",
    }


def get_sync_status() -> dict:
    """Query current edge sync ledger health and queue depth."""
    with get_db() as conn:
        pending = conn.execute("SELECT COUNT(*) as cnt FROM sync_events WHERE sync_status = 'PENDING'").fetchone()["cnt"]
        synced = conn.execute("SELECT COUNT(*) as cnt FROM sync_events WHERE sync_status = 'SYNCED'").fetchone()["cnt"]
        conflicts = conn.execute("SELECT COUNT(*) as cnt FROM sync_events WHERE sync_status IN ('CONFLICT', 'CONFLICT_REQUIRES_REVIEW')").fetchone()["cnt"]
    return {
        "pending_events": pending,
        "synced_events": synced,
        "conflicts": conflicts,
        "is_synced": pending == 0,
    }


# === Observability & Health Metrics ===

def get_observability_metrics() -> dict:
    """Aggregate structured system metrics for screening throughput, clinical referrals, and sync health."""
    with get_db() as conn:
        total_patients = conn.execute("SELECT COUNT(*) as cnt FROM patients").fetchone()["cnt"]
        total_scans = conn.execute("SELECT COUNT(*) as cnt FROM scans").fetchone()["cnt"]

        # Stage distribution
        stage_counts = {0: 0, 1: 0, 2: 0, 3: 0, 4: 0}
        for row in conn.execute("SELECT stage, COUNT(*) as cnt FROM scans GROUP BY stage").fetchall():
            if row["stage"] in stage_counts:
                stage_counts[row["stage"]] = row["cnt"]

        # Referral breakdown
        triage_breakdown = {"ROUTINE": 0, "EARLY": 0, "URGENT": 0}
        for row in conn.execute("SELECT priority, COUNT(*) as cnt FROM referrals GROUP BY priority").fetchall():
            p = str(row["priority"]).upper()
            if p in triage_breakdown:
                triage_breakdown[p] = row["cnt"]

        # Doctor reviews summary
        doc_reviews = conn.execute("SELECT COUNT(*) as cnt FROM doctor_reviews").fetchone()["cnt"]

        # Avg processing latency
        avg_latency = conn.execute("SELECT AVG(processing_time) as lat FROM scans").fetchone()["lat"] or 0.0

    sync_health = get_sync_status()

    return {
        "system": "DrishtiAI",
        "version": "2.2.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "throughput": {
            "total_screenings": total_scans,
            "total_patients": total_patients,
            "average_inference_latency_seconds": round(float(avg_latency), 3),
        },
        "epidemiology": {
            "stage_distribution": stage_counts,
            "referable_percentage": round((sum(stage_counts[s] for s in [2, 3, 4]) / max(1, total_scans)) * 100, 1),
        },
        "clinical_triage": triage_breakdown,
        "human_oversight": {
            "doctor_reviews_recorded": doc_reviews,
        },
        "edge_sync": sync_health,
    }


# Initialize on import
init_db()
