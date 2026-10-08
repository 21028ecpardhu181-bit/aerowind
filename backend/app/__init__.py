"""
backend/app/__init__.py — AeroQuantum-Wind FastAPI Application Package.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root and backend dir are in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
