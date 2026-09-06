"""
DrishtiAI — Seed Data Shim.
Delegates to scripts/ops/seed_data.py for backwards compatibility.
"""
import sys
import runpy
from pathlib import Path

if __name__ == "__main__":
    target = Path(__file__).parent / "scripts" / "ops" / "seed_data.py"
    runpy.run_path(str(target), run_name="__main__")
