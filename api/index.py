import sys
from pathlib import Path

# Add project root so backend/ and core/ are importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.main import app  # noqa: E402

# Vercel Python serverless entry point
handler = app
