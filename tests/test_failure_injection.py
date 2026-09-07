"""
Failure Injection and Red-Teaming Test Suite for DrishtiAI.

Tests defensive boundaries against:
1. Decompression bomb payloads (>25 MP limit)
2. Corrupt byte streams and truncated headers
3. Zero-variance blank/black frames
4. Duplicate image SHA-256 fingerprinting
5. Non-fundus artifact injection (OOD)
6. Malformed JSON and payload boundaries
"""

import io
import os
import pytest
from PIL import Image
import numpy as np

from engine.safety.image_validator import ImageValidator, ImageValidationResult
from engine.safety.ood import evaluate_ood_signal, OODResult
from engine.safety.anatomy import assess_anatomy_and_laterality, AnatomyResult
from app import app
from engine.security.auth import create_access_token, Role
import database


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        token = create_access_token("test-hw", Role.HEALTH_WORKER.value)
        c.environ_base["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        yield c


def _create_test_image(width=512, height=512, color=(180, 50, 20), format="JPEG"):
    """Helper to generate a valid in-memory image."""
    img = Image.new("RGB", (width, height), color=color)
    # Add some high variance texture
    arr = np.array(img)
    arr[100:200, 100:200] = [240, 220, 150]
    arr[250:350, 250:350] = [30, 20, 10]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format=format)
    return buf.getvalue()


class TestImageValidatorRedTeam:
    """Adversarial image payload injection tests."""

    def test_corrupted_bytes_injection(self):
        """Random junk bytes must be rejected safely without crashing."""
        validator = ImageValidator()
        junk_bytes = b"NOT_AN_IMAGE_HEADER" + os.urandom(2048)
        result = validator.validate_bytes(junk_bytes)
        assert not result.is_valid
        assert result.rejection_reason in ("UNSUPPORTED_FORMAT", "CORRUPTED_IMAGE")
        assert len(result.errors) > 0

    def test_truncated_header_injection(self):
        """Image with truncated header (partial JPEG) must fail gracefully."""
        validator = ImageValidator()
        partial_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
        result = validator.validate_bytes(partial_jpeg)
        assert not result.is_valid
        assert result.rejection_reason in ("CORRUPTED_IMAGE", "UNSUPPORTED_FORMAT")

    def test_decompression_bomb_dimension_limit(self):
        """Images exceeding 25 megapixels (e.g. 6000x5000 = 30MP) must be rejected."""
        validator = ImageValidator(max_megapixels=25.0)
        # Create an image header with massive dimensions
        # Pillow allows creating image in memory
        large_img = Image.new("RGB", (6000, 5000), color=(100, 100, 100))
        buf = io.BytesIO()
        large_img.save(buf, format="JPEG", quality=20)
        large_bytes = buf.getvalue()

        result = validator.validate_bytes(large_bytes)
        assert not result.is_valid
        assert result.rejection_reason in ("DIMENSIONS_EXCEED_LIMIT", "DECOMPRESSION_BOMB_RISK")

    def test_blank_black_image_injection(self):
        """Completely black or flat uniform images must be rejected as uninformative."""
        validator = ImageValidator()
        flat_img = Image.new("RGB", (400, 400), color=(0, 0, 0))
        buf = io.BytesIO()
        flat_img.save(buf, format="PNG")
        flat_bytes = buf.getvalue()

        result = validator.validate_bytes(flat_bytes)
        assert not result.is_valid
        assert result.rejection_reason == "BLANK_OR_UNINFORMATIVE"

    def test_duplicate_sha256_detection(self):
        """Presenting identical image bytes twice must detect duplicate hash."""
        validator = ImageValidator()
        valid_bytes = _create_test_image(format="JPEG")
        
        # First submission
        res1 = validator.validate_bytes(valid_bytes)
        assert res1.is_valid
        assert not res1.duplicate_detected
        assert res1.sha256_hash != ""

        # Second submission of identical bytes
        res2 = validator.validate_bytes(valid_bytes)
        assert res2.is_valid
        assert res2.duplicate_detected
        assert res2.sha256_hash == res1.sha256_hash


class TestOutOfDistributionRedTeam:
    """Out-of-distribution artifact handling tests."""

    def test_non_fundus_domain_invalid(self):
        """Evaluating a non-fundus picture (e.g. skin rash or doc) flags domain shift."""
        # Create a non-fundus image (e.g. blue/white document-like image)
        img = Image.new("RGB", (300, 300), color=(240, 240, 255))
        arr = np.array(img)
        # In fundus, red channel dominates strongly; here blue dominates
        ood_res = evaluate_ood_signal(arr)
        # Should flag OOD heuristic shift or domain invalid
        assert not ood_res.domain_valid or ood_res.is_ood_suspected or ood_res.level_triggered > 0


class TestEndpointFailureBoundaries:
    """HTTP API error handling on malformed or malicious requests."""

    def test_ingest_validate_with_corrupt_payload(self, client):
        """POST /api/ingest/validate with corrupted file returns 400."""
        data = {
            "image": (io.BytesIO(b"MALICIOUS_GARBAGE_BYTES_12345"), "attack.jpg")
        }
        res = client.post("/api/ingest/validate", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        json_data = res.get_json()
        assert not json_data["is_valid"]
        assert "errors" in json_data

    def test_session_confirm_nonexistent(self, client):
        """POST /api/sessions/<invalid_id>/confirm returns 404."""
        res = client.post(
            "/api/sessions/SES-DOES-NOT-EXIST/confirm",
            json={"operator_id": "OP-99", "confirmed_eye": "OD"},
        )
        assert res.status_code == 404
        data = res.get_json()
        assert "error" in data

    def test_demo_run_invalid_scenario(self, client):
        """POST /api/demo/run with nonexistent scenario returns 400."""
        res = client.post("/api/demo/run", json={"scenario_id": "NON_EXISTENT_SCENARIO_XYZ"})
        assert res.status_code == 400
        data = res.get_json()
        assert "error" in data

    def test_analyze_rejects_corrupted_payload(self, client):
        """POST /analyze rejects corrupted bytes with 400 and safety_state REJECTED."""
        data = {"image": (io.BytesIO(b"MALICIOUS_GARBAGE_BYTES_CORRUPT"), "exploit.png")}
        res = client.post("/analyze", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["safety_state"] == "REJECTED"
        assert json_data["clinical_action_allowed"] is False

    def test_analyze_v2_rejects_corrupted_payload(self, client):
        """POST /api/analyze-v2 rejects corrupted bytes with 400."""
        data = {"image": (io.BytesIO(b"MALICIOUS_GARBAGE_BYTES_CORRUPT"), "exploit.png")}
        res = client.post("/api/analyze-v2", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["safety_state"] == "REJECTED"

    def test_analyze_v3_rejects_corrupted_payload(self, client):
        """POST /api/analyze-v3 rejects corrupted bytes with 400."""
        data = {"image": (io.BytesIO(b"MALICIOUS_GARBAGE_BYTES_CORRUPT"), "exploit.png")}
        res = client.post("/api/analyze-v3", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["safety_state"] == "REJECTED"

    def test_analyze_rejects_non_fundus_payload(self, client):
        """POST /analyze rejects non-fundus image (e.g. flat blue document) with 400."""
        blue_img = Image.new("RGB", (300, 300), color=(10, 50, 240))
        buf = io.BytesIO()
        blue_img.save(buf, format="JPEG")
        data = {"image": (io.BytesIO(buf.getvalue()), "non_fundus.jpg")}
        res = client.post("/analyze", data=data, content_type="multipart/form-data")
        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data["safety_state"] == "REJECTED"
        assert json_data["screening_eligibility"] == "INELIGIBLE"


class TestDatabaseIntegrityAndSyncRedTeam:
    """Database concurrency, deletion tolerance, and offline sync reconciliation tests."""

    def test_patient_id_monotonicity_after_deletions(self):
        """Deleting an existing patient does not cause ID collision on subsequent patient creation."""
        # Create patient A
        p1 = database.create_patient("Temp Patient 1", age=45)
        # Create patient B
        p2 = database.create_patient("Temp Patient 2", age=50)
        
        # Delete patient A
        database.delete_patient(p1["id"])
        
        # Create patient C — should not collide with p2
        p3 = database.create_patient("Temp Patient 3", age=55)
        assert p3["id"] != p2["id"]
        assert p3["id"] != p1["id"]

    def test_sync_reconciliation_conflict_requires_review(self):
        """Incoming sync batch with stale version generates CONFLICT_REQUIRES_REVIEW."""
        test_entity_id = f"P-TEST-SYNC-{os.urandom(4).hex()}"
        # Set a local version = 5
        with database.get_db() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO sync_events (id, device_id, entity_type, entity_id, action, version, sync_status)
                   VALUES ('evt-local-5', 'edge-1', 'patient', ?, 'UPDATE', 5, 'SYNCED')""",
                (test_entity_id,)
            )
            conn.commit()

        # Send incoming event with version = 3 (stale)
        incoming = [{
            "id": f"evt-in-{os.urandom(4).hex()}",
            "device_id": "edge-remote",
            "entity_type": "patient",
            "entity_id": test_entity_id,
            "version": 3,
            "action": "UPDATE",
            "payload": {"name": "Conflicted Name"}
        }]

        result = database.reconcile_sync_batch(incoming)
        assert result["conflict_count"] == 1
        assert test_entity_id in result["conflict_ids"]

        # Verify DB status is CONFLICT_REQUIRES_REVIEW
        with database.get_db() as conn:
            row = conn.execute(
                "SELECT sync_status FROM sync_events WHERE entity_id = ? AND version = 3",
                (test_entity_id,)
            ).fetchone()
            assert row is not None
            assert row["sync_status"] == "CONFLICT_REQUIRES_REVIEW"

    def test_sync_reconciliation_applies_clean_update(self):
        """Incoming sync batch with clean version updates the patient entity in the database."""
        test_entity_id = "P-9911"
        incoming = [{
            "id": f"evt-in-{os.urandom(4).hex()}",
            "device_id": "edge-remote",
            "entity_type": "patient",
            "entity_id": test_entity_id,
            "version": 1,
            "action": "CREATE",
            "payload": {"name": "Synced Verified Patient", "age": 62, "gender": "F"}
        }]

        result = database.reconcile_sync_batch(incoming)
        assert result["synced_count"] == 1
        assert test_entity_id in result["synced_ids"]

        # Verify patient exists in patients table
        patient = database.get_patient(test_entity_id)
        assert patient is not None
        assert patient["name"] == "Synced Verified Patient"
        assert patient["age"] == 62


class TestSafetyArbitrationAndLaterality:
    """Centralized safety arbitration logic and clinical invariant verification."""

    def test_laterality_mismatch_never_reports_consistent(self):
        """When operator eye and inferred eye disagree, notes must NEVER say consistent."""
        from engine.safety.anatomy import assess_anatomy_and_laterality
        # Synthetic test image
        img = np.zeros((400, 400, 3), dtype=np.uint8)
        # Force a laterality check with mismatch
        res = assess_anatomy_and_laterality(img, operator_eye="OD")
        for note in res.notes:
            assert "Laterality consistent: Operator=OD, Inferred=OS" not in note

    def test_central_safety_engine_blocks_clinical_action_on_uncertain(self):
        """When safety_state is UNCERTAIN or REJECTED, clinical_action_allowed must be False."""
        from engine.safety.decision_engine import SafetyDecisionEngine
        from engine.safety.image_validator import ImageValidationResult

        engine = SafetyDecisionEngine()
        val = ImageValidationResult(valid=True)
        # Detection with low confidence
        low_conf_det = {"stage": 2, "confidence": 45.0}

        res = engine.evaluate(image_val=val, primary_detection=low_conf_det)
        assert res.safety_state == "UNCERTAIN"
        assert res.human_review_required is True
        assert res.clinical_action_allowed is False

