"""
DrishtiAI Configuration
Handles API key rotation, model paths, and app settings.
"""
import os
import re
import secrets
import itertools
import logging
from dotenv import load_dotenv

load_dotenv(override=True)

log = logging.getLogger("DrishtiAI.config")

# ---------------------------------------------------------------------------
# Gemma API Key Pool — Round-Robin Rotation
# ---------------------------------------------------------------------------
_API_KEY_PATTERN = re.compile(r"^[A-Za-z0-9_\-]{20,}$")

def _load_gemma_keys():
    """Load all GEMMA_API_KEY_* from .env and return as a list."""
    keys = []
    for key, value in os.environ.items():
        if key.startswith("GEMMA_API_KEY_") and value and value != "your_key_here":
            if _API_KEY_PATTERN.match(value):
                keys.append(value)
            else:
                log.warning("Skipping %s — does not match expected API key format", key)
    if not keys:
        log.warning("No Gemma API keys found in .env! Add at least one GEMMA_API_KEY_1=...")
    return keys

GEMMA_KEYS = _load_gemma_keys()
_key_cycle = itertools.cycle(GEMMA_KEYS) if GEMMA_KEYS else None

def get_next_gemma_key():
    """Get the next API key from the rotation pool."""
    if _key_cycle is None:
        raise RuntimeError("No Gemma API keys configured. Add keys to .env file.")
    return next(_key_cycle)

# ---------------------------------------------------------------------------
# Flask Secret — cryptographically secure fallback
# ---------------------------------------------------------------------------
_env_secret = os.getenv("FLASK_SECRET_KEY") or os.getenv("FLASK_SECRET", "")
_INSECURE_DEFAULTS = {"DrishtiAI-dev-key", "DrishtiAI-secret-key-change-me", "DrishtiAI-2026", ""}

if _env_secret in _INSECURE_DEFAULTS:
    FLASK_SECRET = secrets.token_hex(32)
    log.warning("FLASK_SECRET_KEY not set or insecure — generated ephemeral key. Set a persistent key in .env for production.")
else:
    FLASK_SECRET = _env_secret

EDGE_DEVICE_SECRET = os.getenv("EDGE_DEVICE_SECRET", FLASK_SECRET)
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "drishti-admin-secret-2026")
DOCTOR_SECRET = os.getenv("DOCTOR_SECRET", "drishti-doctor-secret-2026")

# ---------------------------------------------------------------------------
# Model Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

# Tanwar-12 ResNet50 model
DR_MODEL_PATH = os.path.join(MODELS_DIR, "model.h5")

# RishiSwethan vessel segmentation model
VESSEL_MODEL_DIR = os.path.join(MODELS_DIR, "vessel_model")
PIPELINE_DIR = os.path.join(BASE_DIR, "engine", "pipeline")
PIPELINE_WEIGHTS = os.path.join(MODELS_DIR, "dr_pipeline", "best_model.pt")
PIPELINE_CALIBRATION = os.path.join(MODELS_DIR, "dr_pipeline", "calibration.json")

# ---------------------------------------------------------------------------
# App Settings
# ---------------------------------------------------------------------------
DEBUG = os.getenv("FLASK_DEBUG", "true").lower() == "true"

# Rate Limiting & Distributed Worker Storage
RATELIMIT_STORAGE_URI = os.getenv("RATELIMIT_STORAGE_URI") or os.getenv("REDIS_URL", "memory://")

# CORS Origin Whitelist
CORS_ALLOWED_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]

# Image settings
IMG_SIZE = 64    # Tanwar-12 model expects 64x64
DISPLAY_SIZE = 512  # Display images at higher resolution
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "bmp", "tiff"}

# DR Stage Labels
DR_STAGES = {
    0: {"name": "No DR", "severity": "none", "color": "#22c55e"},
    1: {"name": "Mild NPDR", "severity": "mild", "color": "#eab308"},
    2: {"name": "Moderate NPDR", "severity": "moderate", "color": "#f97316"},
    3: {"name": "Severe NPDR", "severity": "severe", "color": "#ef4444"},
    4: {"name": "Proliferative DR", "severity": "proliferative", "color": "#dc2626"},
}

# ---------------------------------------------------------------------------
# Offline Mode — bypass all cloud API calls (for rural deployments)
# ---------------------------------------------------------------------------
OFFLINE_MODE = os.getenv("DRISHTIAI_OFFLINE", "false").lower() == "true"
if not GEMMA_KEYS:
    OFFLINE_MODE = True
    log.info("No API keys found — forcing OFFLINE_MODE=True")

# Gemma Model — configurable via env to allow switching to MedGemma
# Options: "gemma-4-31b-it", "medgemma-27b-it", "gemma-4-4b-it" (edge)
GEMMA_MODEL_NAME = os.getenv("GEMMA_MODEL", "gemma-4-31b-it")
MEDGEMMA_MODEL_NAME = os.getenv("MEDGEMMA_MODEL", "medgemma-27b-it")
TIER2_TIMEOUT = int(os.getenv("TIER2_TIMEOUT", "30"))
HIRESCAM_THRESHOLD = float(os.getenv("HIRESCAM_THRESHOLD", "0.4"))

# ---------------------------------------------------------------------------
# Feature Flags & Policy Versions (Centralized Configuration)
# ---------------------------------------------------------------------------
DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes")
ENABLE_OOD = os.getenv("ENABLE_OOD", "true").lower() in ("true", "1", "yes")
ENABLE_LATERALITY = os.getenv("ENABLE_LATERALITY", "true").lower() in ("true", "1", "yes")
ENABLE_MULTIMODEL = os.getenv("ENABLE_MULTIMODEL", "true").lower() in ("true", "1", "yes")
ENABLE_PROGRESSIVE_RISK = os.getenv("ENABLE_PROGRESSIVE_RISK", "true").lower() in ("true", "1", "yes")
ENABLE_RAG = os.getenv("ENABLE_RAG", "true").lower() in ("true", "1", "yes")
ENABLE_OFFLINE_SYNC = os.getenv("ENABLE_OFFLINE_SYNC", "true").lower() in ("true", "1", "yes")

SAFETY_POLICY_VERSION = "SAFE-1.0"
TRIAGE_POLICY_VERSION = "TRIAGE-1.1"
REPORT_TEMPLATE_VERSION = "REPORT-2.0"

MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "70.0"))
MODEL_DISAGREEMENT_DELTA = int(os.getenv("MODEL_DISAGREEMENT_DELTA", "2"))

# Ensure directories exist
for d in [MODELS_DIR, UPLOAD_DIR, RESULTS_DIR, VESSEL_MODEL_DIR, PIPELINE_DIR]:
    os.makedirs(d, exist_ok=True)
