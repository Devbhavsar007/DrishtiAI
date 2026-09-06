"""
Image Sanity and Payload Security Validator for DrishtiAI.

Protects against:
  - Non-image files / disguised executables (Magic byte inspection)
  - Corrupt or truncated image streams
  - Decompression bombs (Zip bombs / pixel bombs > 25 MP)
  - Blank / saturated / completely dark captures
  - Duplicate submissions via SHA-256 hashing
  - Screen / monitor re-photograph artifacts (Moiré pattern detection as soft warning)
"""

import os
import io
import hashlib
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from PIL import Image
import cv2
import numpy as np

# Security limit: 25 Megapixels maximum to prevent decompression bomb denial-of-service
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# Known magic bytes for supported formats
MAGIC_NUMBERS = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG\r\n\x1a\n": "PNG",
    b"BM": "BMP",
    b"II*\x00": "TIFF",
    b"MM\x00*": "TIFF",
}


@dataclass
class ImageValidationResult:
    valid: bool
    error: Optional[str] = None
    image_hash: str = ""
    width: int = 0
    height: int = 0
    channels: int = 3
    is_blank: bool = False
    possible_screen_capture: bool = False
    moire_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    rejection_reason: Optional[str] = None
    duplicate_detected: bool = False

    @property
    def is_valid(self) -> bool:
        return self.valid

    @property
    def sha256_hash(self) -> str:
        return self.image_hash

    @property
    def errors(self) -> List[str]:
        return [self.error] if self.error else []

    def to_dict(self):
        return {
            "valid": self.valid,
            "error": self.error,
            "image_hash": self.image_hash,
            "dimensions": {"width": self.width, "height": self.height, "channels": self.channels},
            "is_blank": self.is_blank,
            "possible_screen_capture": self.possible_screen_capture,
            "moire_score": round(self.moire_score, 4),
            "warnings": self.warnings,
            "rejection_reason": self.rejection_reason,
            "duplicate_detected": self.duplicate_detected,
        }


def _check_magic_bytes(header: bytes) -> Optional[str]:
    """Verify first bytes against known image magic numbers."""
    for magic, fmt in MAGIC_NUMBERS.items():
        if header.startswith(magic):
            return fmt
    return None


def _detect_screen_moire(gray_img: np.ndarray) -> Tuple[bool, float]:
    """
    Experimental detector for screen / monitor photograph artifacts (Moiré).
    Evaluates high-frequency spectral energy spikes in 2D Fourier Transform.
    NOTE: Emits an advisory warning only; NEVER triggers hard rejection.
    """
    try:
        h, w = gray_img.shape
        if h < 128 or w < 128:
            return False, 0.0

        resized = cv2.resize(gray_img, (256, 256))
        f = np.fft.fft2(resized)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-6)

        # Mask out low-frequency center
        cy, cx = 128, 128
        r = 30
        y, x = np.ogrid[:256, :256]
        mask = (x - cx) ** 2 + (y - cy) ** 2 > r ** 2
        high_freq = magnitude_spectrum[mask]

        # Calculate energy variance and peak-to-average ratio in high frequency ring
        mean_hf = np.mean(high_freq)
        max_hf = np.max(high_freq)
        ratio = float(max_hf / (mean_hf + 1e-6))

        # Peak spike > 2.8 indicates strong periodic line artifact (moiré or scanline grid)
        is_screen = ratio > 2.85
        return is_screen, ratio
    except Exception:
        return False, 0.0


def validate_image_file(
    file_bytes_or_path,
    existing_hashes: Optional[set] = None
) -> Tuple[ImageValidationResult, Optional[np.ndarray]]:
    """
    Perform full sanity check on uploaded file.
    Returns (ImageValidationResult, np.ndarray image in BGR if valid else None).
    """
    warnings: List[str] = []

    # 1. Obtain raw bytes
    if isinstance(file_bytes_or_path, str):
        if not os.path.exists(file_bytes_or_path):
            return ImageValidationResult(valid=False, error=f"File not found: {file_bytes_or_path}"), None
        with open(file_bytes_or_path, "rb") as f:
            raw_bytes = f.read()
    elif isinstance(file_bytes_or_path, (bytes, bytearray)):
        raw_bytes = bytes(file_bytes_or_path)
    elif hasattr(file_bytes_or_path, "read"):
        raw_bytes = file_bytes_or_path.read()
        if hasattr(file_bytes_or_path, "seek"):
            file_bytes_or_path.seek(0)
    else:
        return ImageValidationResult(valid=False, error="Invalid input type for image validation."), None

    if len(raw_bytes) == 0:
        return ImageValidationResult(valid=False, error="Image file is completely empty (0 bytes)."), None

    if len(raw_bytes) > 16 * 1024 * 1024:
        return ImageValidationResult(valid=False, error="Image file exceeds maximum allowable size (16 MB)."), None

    # 2. Check Magic Bytes
    magic_fmt = _check_magic_bytes(raw_bytes[:16])
    if not magic_fmt:
        return ImageValidationResult(
            valid=False,
            error="Invalid image header. File signature does not match JPEG, PNG, BMP, or TIFF.",
            rejection_reason="UNSUPPORTED_FORMAT",
        ), None

    # 3. Compute SHA-256 hash for duplicate check
    img_hash = hashlib.sha256(raw_bytes).hexdigest()
    if existing_hashes and img_hash in existing_hashes:
        warnings.append("DUPLICATE_IMAGE_SUBMISSION: Image hash matches a previously analyzed scan.")

    # 4. Decompression bomb check & PIL verification
    try:
        bio = io.BytesIO(raw_bytes)
        with Image.open(bio) as pil_img:
            w, h = pil_img.size
            if w * h > MAX_IMAGE_PIXELS:
                return ImageValidationResult(
                    valid=False,
                    error=f"Image resolution ({w}x{h} = {w*h} pixels) exceeds safe limit of {MAX_IMAGE_PIXELS} pixels.",
                    rejection_reason="DIMENSIONS_EXCEED_LIMIT",
                ), None
            pil_img.verify()
    except Image.DecompressionBombError:
        return ImageValidationResult(valid=False, error="Decompression bomb detected. Upload rejected.", rejection_reason="DECOMPRESSION_BOMB_RISK"), None
    except Exception as e:
        return ImageValidationResult(valid=False, error=f"Corrupted or invalid image stream: {str(e)}", rejection_reason="CORRUPTED_IMAGE"), None

    # 5. Decode into OpenCV array (BGR)
    try:
        np_arr = np.frombuffer(raw_bytes, np.uint8)
        img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return ImageValidationResult(valid=False, error="OpenCV failed to decode image buffer.", rejection_reason="CORRUPTED_IMAGE"), None
    except Exception as e:
        return ImageValidationResult(valid=False, error=f"Decoding failure: {str(e)}", rejection_reason="CORRUPTED_IMAGE"), None

    h, w = img_bgr.shape[:2]
    channels = img_bgr.shape[2] if len(img_bgr.shape) > 2 else 1

    # 6. Blank / Saturated / Degenerate Check
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY) if channels == 3 else img_bgr
    mean_val = float(np.mean(gray))
    std_val = float(np.std(gray))

    if std_val < 3.0 or mean_val < 5.0 or mean_val > 250.0:
        return ImageValidationResult(
            valid=False,
            error="Blank or degenerate image detected (insufficient dynamic range or fully black/white).",
            image_hash=img_hash,
            width=w,
            height=h,
            channels=channels,
            is_blank=True,
            warnings=warnings,
            rejection_reason="BLANK_OR_UNINFORMATIVE",
        ), None

    # 7. Moiré / Screen photograph artifact detection (SOFT WARNING ONLY)
    is_screen, moire_score = _detect_screen_moire(gray)
    if is_screen:
        warnings.append("POSSIBLE_SCREEN_CAPTURE: High-frequency periodic pattern detected (possible monitor photograph).")

    return ImageValidationResult(
        valid=True,
        image_hash=img_hash,
        width=w,
        height=h,
        channels=channels,
        is_blank=False,
        possible_screen_capture=is_screen,
        moire_score=moire_score,
        warnings=warnings,
    ), img_bgr


class ImageValidator:
    """Class wrapper for image validation with duplicate fingerprint caching."""

    def __init__(self, max_megapixels: float = 25.0):
        self.max_megapixels = max_megapixels
        self.seen_hashes = set()

    def validate_bytes(self, raw_bytes: bytes) -> ImageValidationResult:
        res, _ = validate_image_file(raw_bytes, existing_hashes=self.seen_hashes)
        if res.valid and res.image_hash:
            if res.image_hash in self.seen_hashes:
                res.duplicate_detected = True
                res.warnings.append("DUPLICATE_IMAGE_SUBMISSION")
            else:
                self.seen_hashes.add(res.image_hash)
        return res
