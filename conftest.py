"""Pytest configuration and root path resolution for IndustryLab."""
import sys
from pathlib import Path

# Ensure repo root is always in sys.path for test runners
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
