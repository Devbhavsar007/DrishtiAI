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


def get_current_actor() -> dict[str, str] | None:
    """
    Extract actor information from request headers.
    Enforces ZERO-TRUST authentication:
    1. Valid signed Bearer token (dr1.<payload>.<sig>)
    2. Cryptographically signed edge device credentials (HMAC-SHA256 with timestamp)
    Returns None if unauthenticated. Never defaults to HEALTH_WORKER or DOCTOR.
    """
    # 1. Bearer Token Authentication
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        payload = verify_token(token)
        if payload:
            return {
                "actor_id": payload.get("sub", "anonymous"),
                "actor_role": payload.get("role", Role.HEALTH_WORKER.value),
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
                    return {
                        "actor_id": edge_device,
                        "actor_role": edge_role,
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


def verify_role_credentials(role: str, secret: str | None) -> bool:
    """
    Verify credentials for privileged roles (ADMIN, DOCTOR) to prevent self-elevation.
    HEALTH_WORKER and PATIENT do not require master secrets to request tokens.
    """
    from config import ADMIN_SECRET, DOCTOR_SECRET
    role_clean = role.upper()
    if role_clean == Role.ADMIN.value:
        return bool(secret and hmac.compare_digest(str(secret), ADMIN_SECRET))
    if role_clean == Role.DOCTOR.value:
        return bool(secret and hmac.compare_digest(str(secret), DOCTOR_SECRET))
    return True
