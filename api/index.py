"""
Vercel Serverless Entrypoint for FastAPI
Directly imported and executed by the Vercel Python runtime.
"""
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path so backend packages resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import the core FastAPI instance
from backend.app.main import app

# Export app for Vercel Serverless execution
__all__ = ["app"]

