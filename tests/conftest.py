"""
Pytest configuration for DrishtiAI test suite.
Forces fast deterministic offline CPU execution across all test fixtures.
"""

import os
import pytest

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
