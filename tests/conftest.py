"""
Pytest configuration for DrishtiAI test suite.
Forces fast deterministic offline CPU execution across all test fixtures.
"""

import os
import sys
from pathlib import Path

# Ensure repo root is on sys.path
REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

try:
    import pytest
except ImportError:
    pytest = None

# Force test environment defaults before any torch/CUDA import
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TORCHDYNAMO_DISABLE"] = "1"
os.environ["DRISHTIAI_OFFLINE"] = "true"
os.environ["DEMO_MODE"] = "true"

try:
    import torch
    torch.cuda.is_available = lambda: False
except ImportError:
    pass

import config
config.OFFLINE_MODE = True
config.DEMO_MODE = True

try:
    import engine.gemma_report
    engine.gemma_report.OFFLINE_MODE = True
except (ImportError, AttributeError):
    pass
