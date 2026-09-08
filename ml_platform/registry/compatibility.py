"""Model compatibility and schema verification.

Checks that candidate models conform to DrishtiAI runtime requirements:
  - Input resolution and normalization
  - Output class dimensions (5 classes: No DR, Mild, Moderate, Severe, PDR)
  - Temperature scaling calibration parameters
"""

from __future__ import annotations

from typing import Any

SUPPORTED_ARCHITECTURES = {"resnet50", "pipeline_v3", "efficientnet", "vit", "convnext"}
EXPECTED_NUM_CLASSES = 5


def check_runtime_compatibility(
    architecture: str,
    input_size: int = 300,
    num_classes: int = EXPECTED_NUM_CLASSES,
    calibration_config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Verify model architecture and configuration compatibility with clinical inference.
    """
    issues: list[str] = []

    arch_clean = architecture.lower().strip()
    if not any(supported in arch_clean for supported in SUPPORTED_ARCHITECTURES):
        issues.append(f"Architecture '{architecture}' not in supported runtime list: {sorted(list(SUPPORTED_ARCHITECTURES))}")

    if num_classes != EXPECTED_NUM_CLASSES:
        issues.append(f"Expected {EXPECTED_NUM_CLASSES} output classes, got {num_classes}")

    if input_size < 64 or input_size > 1024:
        issues.append(f"Input size {input_size} is outside clinical allowable range [64, 1024]")

    if calibration_config:
        if "temperature" in calibration_config:
            temp = float(calibration_config["temperature"])
            if temp <= 0.0 or temp > 10.0:
                issues.append(f"Unreasonable calibration temperature: {temp}")

    return {
        "is_compatible": len(issues) == 0,
        "issues": issues,
        "architecture": architecture,
        "input_size": input_size,
        "num_classes": num_classes,
    }
