"""Role-Based Access Control (RBAC) and lightweight token authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from enum import Enum
from functools import wraps
from typing import Any, Callable
from flask import request, jsonify, g
from config import FLASK_SECRET, EDGE_DEVICE_SECRET


class Role(str, Enum):
    ADMIN = "ADMIN"
    DOCTOR = "DOCTOR"
    HEALTH_WORKER = "HEALTH_WORKER"
    PATIENT = "PATIENT"


def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(s: str) -> bytes:
    padding = 4 - (len(s) % 4)
    if padding != 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_access_token(user_id: str, role: str, expires_in_seconds: int = 86400) -> str:
    """Generate a tamper-proof HMAC-SHA256 signed access token."""
    role_clean = role.upper()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "role": role_clean,
        "iat": now,
        "exp": now + expires_in_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = _b64_encode(payload_bytes)

    secret = FLASK_SECRET.encode("utf-8")
    signature = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)

    return f"dr1.{payload_b64}.{sig_b64}"


def verify_token(token: str) -> dict[str, Any] | None:
    """Verify signature and expiration of an access token."""
    try:
        parts = token.split(".")
        if len(parts) != 3 or parts[0] != "dr1":
            return None

        _, payload_b64, sig_b64 = parts
        secret = FLASK_SECRET.encode("utf-8")
        expected_sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()

        actual_sig = _b64_decode(sig_b64)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload_bytes = _b64_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))

        if payload.get("exp", 0) < int(time.time()):
            return None  # Expired

        return payload
    except Exception:
        return None


def create_edge_signature(device_id: str, role: str, timestamp: int, secret: str | None = None) -> str:
    """Create cryptographic HMAC-SHA256 signature for offline edge device operations."""
    key = (secret or EDGE_DEVICE_SECRET).encode("utf-8")
    msg = f"{device_id}:{role.upper()}:{timestamp}".encode("utf-8")
    sig = hmac.new(key, msg, hashlib.sha256).digest()
    return _b64_encode(sig)


def verify_edge_signature(
    device_id: str,
    role: str,
    timestamp: int,
    signature: str,
    secret: str | None = None,
    max_drift_seconds: int = 300,
) -> bool:
    """
    Cryptographically verify edge device signature and enforce anti-replay timestamp bounds.
    """
    try:
        now = int(time.time())
        if abs(now - timestamp) > max_drift_seconds:
            return False

        key = (secret or EDGE_DEVICE_SECRET).encode("utf-8")
        msg = f"{device_id}:{role.upper()}:{timestamp}".encode("utf-8")
        expected_sig = hmac.new(key, msg, hashlib.sha256).digest()
        actual_sig = _b64_decode(signature)
        return hmac.compare_digest(expected_sig, actual_sig)
    except Exception:
        return False


def get_current_actor() -> dict[str, Any] | None:
    """
    Extract authoritative actor information from request headers and session.
    Enforces ZERO-TRUST authentication:
    1. Valid signed Bearer token (dr1.<payload>.<sig>)
    2. Cryptographically signed edge device credentials (HMAC-SHA256 with timestamp)
    
    Returns authoritative request context:
      - authenticated_actor: bool
      - actor_id: str
      - actor_role: str
      - actor_scope: str ('patient:<id>' for PATIENT, 'clinic:all' for clinicians)
      - device_id: str
      - session_id: str
      - request_id: str
    Returns None if unauthenticated. Never defaults to HEALTH_WORKER or DOCTOR.
    """
    req_id = ""
    try:
        from flask import has_request_context
        if has_request_context():
            if hasattr(g, "request_id"):
                req_id = str(g.request_id)
            elif "X-Request-ID" in request.headers:
                req_id = request.headers.get("X-Request-ID", "")
    except Exception:
        pass

    session_id = request.headers.get("X-Drishti-Session-Id", "") if request else ""

    # 1. Bearer Token Authentication
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        payload = verify_token(token)
        if payload:
            actor_id = payload.get("sub", "anonymous")
            actor_role = payload.get("role", Role.HEALTH_WORKER.value)
            actor_scope = f"patient:{actor_id}" if actor_role == Role.PATIENT.value else "clinic:all"
            device_id = payload.get("device_id") or request.headers.get("X-Drishti-Device-Id", "LOCAL-WEB-CLIENT")
            return {
                "authenticated_actor": True,
                "actor_id": actor_id,
                "actor_role": actor_role,
                "actor_scope": actor_scope,
                "device_id": device_id,
                "session_id": session_id,
                "request_id": req_id,
            }

    # 2. Cryptographically Signed Edge Device Credentials
    edge_device = request.headers.get("X-Drishti-Edge-Device-Id") or request.headers.get("X-Drishti-Actor-Id", "")
    edge_role = (request.headers.get("X-Drishti-Edge-Role") or request.headers.get("X-Drishti-Role", "")).upper()
    edge_timestamp_raw = request.headers.get("X-Drishti-Edge-Timestamp", "")
    edge_signature = request.headers.get("X-Drishti-Edge-Signature", "")

    if edge_device and edge_role and edge_timestamp_raw and edge_signature:
        if edge_role in {r.value for r in Role}:
            try:
                edge_timestamp = int(edge_timestamp_raw)
                if verify_edge_signature(edge_device, edge_role, edge_timestamp, edge_signature):
                    actor_scope = f"patient:{edge_device}" if edge_role == Role.PATIENT.value else "clinic:all"
                    return {
                        "authenticated_actor": True,
                        "actor_id": edge_device,
                        "actor_role": edge_role,
                        "actor_scope": actor_scope,
                        "device_id": edge_device,
                        "session_id": session_id,
                        "request_id": req_id,
                    }
            except (ValueError, TypeError):
                pass

    # Unauthenticated / invalid credentials - fail closed
    return None


def require_role(*allowed_roles: str | Role) -> Callable:
    """
    Flask route decorator enforcing role-based permissions with Zero-Trust authentication.
    Example: @require_role(Role.DOCTOR, Role.ADMIN)
    """
    normalized_allowed = {
        r.value if isinstance(r, Role) else str(r).upper() for r in allowed_roles
    }

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            actor = get_current_actor()
            if not actor or not actor.get("actor_role"):
                return jsonify({
                    "success": False,
                    "error": "Authentication required. Provide a valid Bearer token or signed edge credential."
                }), 401

            g.current_user = actor

            # Check if role matches
            if actor["actor_role"] not in normalized_allowed:
                return jsonify({
                    "success": False,
                    "error": (
                        f"Access forbidden: requires one of {sorted(list(normalized_allowed))}. "
                        f"Current role: {actor['actor_role']}."
                    )
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def verify_role_credentials(role: str, secret: str | None, user_id: str | None = None, env: str | None = None, demo_mode: bool | None = None) -> bool:
    """
    Verify credentials for requested role across deployment environments.
    - ADMIN: requires ADMIN_SECRET
    - DOCTOR: requires DOCTOR_SECRET
    - HEALTH_WORKER: in production (non-demo), requires WORKER_SECRET; in demo/dev/test, permits synthetic accounts
    - PATIENT: verifies patient exists in database (or synthetic demo namespace)
    """
    from config import ADMIN_SECRET, DOCTOR_SECRET, WORKER_SECRET, ENVIRONMENT, DEMO_MODE as CONFIG_DEMO_MODE
    current_env = (env or ENVIRONMENT).lower()
    is_demo = demo_mode if demo_mode is not None else CONFIG_DEMO_MODE
    role_clean = role.upper()

    if role_clean == Role.ADMIN.value:
        return bool(secret and hmac.compare_digest(str(secret), ADMIN_SECRET))

    if role_clean == Role.DOCTOR.value:
        return bool(secret and hmac.compare_digest(str(secret), DOCTOR_SECRET))

    if role_clean == Role.HEALTH_WORKER.value:
        # In production mode without demo flag, require valid worker secret or admin secret
        if current_env == "production" and not is_demo:
            if secret and (hmac.compare_digest(str(secret), WORKER_SECRET) or hmac.compare_digest(str(secret), ADMIN_SECRET)):
                return True
            return False
        # In demo, dev, or test mode, permit health worker logins
        return True

    if role_clean == Role.PATIENT.value:
        # Patient user_id must exist in database, or match a synthetic demo ID in demo mode
        if not user_id:
            return False
        if is_demo and (user_id.startswith("DEMO-") or user_id.startswith("pat-demo")):
            return True
        try:
            from database import get_patient
            pat = get_patient(user_id)
            return pat is not None
        except Exception:
            return False

    return False

