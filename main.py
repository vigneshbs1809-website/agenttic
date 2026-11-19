"""
Literature Intelligence Platform - Root Application Entrypoint
Exposes the FastAPI 'app' instance for ASGI servers (Uvicorn, Hypercorn, Gunicorn)
and automated deployment runners.
"""
import os
import sys
from pathlib import Path

# Ensure project root is at the head of sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import the core FastAPI application instance
from backend.app.main import app

# Export app for ASGI entrypoint auto-discovery
__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

