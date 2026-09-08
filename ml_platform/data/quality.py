"""Batch data quality pipeline for training data.

Reuses existing engine/safety/image_validator and OOD checks for consistency.
Adds batch-level quality checks: corrupt detection, resolution validation,
blur, brightness, duplicate hashes, near-duplicates.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any

import cv2
import numpy as np

log = logging.getLogger(__name__)


@dataclass
class QualityCheckResult:
    """Result of a single quality check on a training image."""
    scan_id: str
    check_type: str
    passed: bool = True
    score: float = 1.0
    details: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BatchQualityReport:
    """Aggregate quality report for a batch of training candidates."""
    batch_id: str
    total_checked: int = 0
    total_passed: int = 0
    total_failed: int = 0
    checks: list[QualityCheckResult] = field(default_factory=list)
    failure_breakdown: dict[str, int] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        return self.total_passed / max(1, self.total_checked)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["pass_rate"] = self.pass_rate
        return d


# Quality thresholds
MIN_RESOLUTION = 128       # Minimum dimension in pixels
MAX_RESOLUTION = 8192      # Maximum dimension to prevent DoS
MIN_BRIGHTNESS = 20        # Minimum mean brightness (out of 255)
MAX_BRIGHTNESS = 240       # Maximum mean brightness
BLUR_THRESHOLD = 50.0      # Laplacian variance threshold for blur


def check_image_readable(image_path: str, scan_id: str = "") -> QualityCheckResult:
    """Check if the image can be read and decoded."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return QualityCheckResult(
                scan_id=scan_id, check_type="READABLE",
                passed=False, score=0.0, details="Image could not be decoded"
            )
        return QualityCheckResult(
            scan_id=scan_id, check_type="READABLE",
            passed=True, score=1.0, details=f"Decoded {img.shape}"
        )
    except Exception as e:
        return QualityCheckResult(
            scan_id=scan_id, check_type="READABLE",
            passed=False, score=0.0, details=f"Read error: {e}"
        )


def check_resolution(img: np.ndarray, scan_id: str = "") -> QualityCheckResult:
    """Check image resolution is within acceptable bounds."""
    h, w = img.shape[:2]
    if h < MIN_RESOLUTION or w < MIN_RESOLUTION:
        return QualityCheckResult(
            scan_id=scan_id, check_type="RESOLUTION",
            passed=False, score=0.3, details=f"Too small: {w}x{h} (min {MIN_RESOLUTION})"
        )
    if h > MAX_RESOLUTION or w > MAX_RESOLUTION:
        return QualityCheckResult(
            scan_id=scan_id, check_type="RESOLUTION",
            passed=False, score=0.3, details=f"Too large: {w}x{h} (max {MAX_RESOLUTION})"
        )
    # Score based on how close to ideal (512-1024 range)
    ideal_dim = 768
    dim_score = 1.0 - min(1.0, abs(min(h, w) - ideal_dim) / ideal_dim)
    return QualityCheckResult(
        scan_id=scan_id, check_type="RESOLUTION",
        passed=True, score=round(dim_score, 3), details=f"{w}x{h}"
    )


def check_brightness(img: np.ndarray, scan_id: str = "") -> QualityCheckResult:
    """Check image is not too dark or washed out."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    mean_brightness = float(np.mean(gray))

    if mean_brightness < MIN_BRIGHTNESS:
        return QualityCheckResult(
            scan_id=scan_id, check_type="BRIGHTNESS",
            passed=False, score=0.2, details=f"Too dark: mean={mean_brightness:.1f}"
        )
    if mean_brightness > MAX_BRIGHTNESS:
        return QualityCheckResult(
            scan_id=scan_id, check_type="BRIGHTNESS",
            passed=False, score=0.2, details=f"Washed out: mean={mean_brightness:.1f}"
        )
    # Normalize score: ideal around 80-180
    ideal_low, ideal_high = 80, 180
    if ideal_low <= mean_brightness <= ideal_high:
        score = 1.0
    else:
        dist = min(abs(mean_brightness - ideal_low), abs(mean_brightness - ideal_high))
        score = max(0.3, 1.0 - dist / 100)
    return QualityCheckResult(
        scan_id=scan_id, check_type="BRIGHTNESS",
        passed=True, score=round(score, 3), details=f"mean={mean_brightness:.1f}"
    )


def check_blur(img: np.ndarray, scan_id: str = "") -> QualityCheckResult:
    """Detect blur using Laplacian variance."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if laplacian_var < BLUR_THRESHOLD:
        return QualityCheckResult(
            scan_id=scan_id, check_type="BLUR",
            passed=False, score=round(laplacian_var / BLUR_THRESHOLD, 3),
            details=f"Blurry: laplacian_var={laplacian_var:.1f} (threshold={BLUR_THRESHOLD})"
        )
    # Cap score at 1.0
    score = min(1.0, laplacian_var / (BLUR_THRESHOLD * 5))
    return QualityCheckResult(
        scan_id=scan_id, check_type="BLUR",
        passed=True, score=round(score, 3), details=f"laplacian_var={laplacian_var:.1f}"
    )


def compute_image_hash(img: np.ndarray) -> str:
    """Compute perceptual difference hash for near-duplicate detection."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    resized = cv2.resize(gray, (9, 8), interpolation=cv2.INTER_AREA)
    diff = resized[:, 1:] > resized[:, :-1]
    return "".join(str(int(b)) for row in diff for b in row)


def run_quality_checks(
    image_path: str,
    scan_id: str = "",
    known_hashes: set[str] | None = None,
) -> tuple[list[QualityCheckResult], bool]:
    """
    Run all quality checks on a single training image.

    Returns:
        (list of check results, overall_passed)
    """
    checks = []

    # 1. Readable
    readable_check = check_image_readable(image_path, scan_id)
    checks.append(readable_check)
    if not readable_check.passed:
        return checks, False

    img = cv2.imread(image_path)

    # 2. Resolution
    res_check = check_resolution(img, scan_id)
    checks.append(res_check)

    # 3. Brightness
    bright_check = check_brightness(img, scan_id)
    checks.append(bright_check)

    # 4. Blur
    blur_check = check_blur(img, scan_id)
    checks.append(blur_check)

    # 5. Near-duplicate detection
    if known_hashes is not None:
        dhash = compute_image_hash(img)
        if dhash in known_hashes:
            checks.append(QualityCheckResult(
                scan_id=scan_id, check_type="NEAR_DUPLICATE",
                passed=False, score=0.0, details="Near-duplicate detected via dhash"
            ))
        else:
            checks.append(QualityCheckResult(
                scan_id=scan_id, check_type="NEAR_DUPLICATE",
                passed=True, score=1.0, details="Unique image"
            ))
            known_hashes.add(dhash)

    overall_passed = all(c.passed for c in checks)
    return checks, overall_passed


def run_batch_quality(
    scan_image_pairs: list[tuple[str, str]],
) -> BatchQualityReport:
    """
    Run quality checks on a batch of (scan_id, image_path) pairs.

    Returns:
        BatchQualityReport with aggregate statistics.
    """
    batch_id = f"qc-{uuid.uuid4().hex[:12]}"
    report = BatchQualityReport(batch_id=batch_id)
    known_hashes: set[str] = set()
    failure_breakdown: dict[str, int] = {}

    for scan_id, image_path in scan_image_pairs:
        report.total_checked += 1
        checks, passed = run_quality_checks(image_path, scan_id, known_hashes)
        report.checks.extend(checks)

        if passed:
            report.total_passed += 1
        else:
            report.total_failed += 1
            for c in checks:
                if not c.passed:
                    failure_breakdown[c.check_type] = failure_breakdown.get(c.check_type, 0) + 1

    report.failure_breakdown = failure_breakdown
    log.info("Quality batch %s: %d/%d passed (%.1f%%)",
             batch_id, report.total_passed, report.total_checked,
             report.pass_rate * 100)
    return report
