"""
Literature Intelligence Platform - Dual-Mode Entrypoint
Supports:
1. Streamlit Cloud (share.streamlit.io): launches the Streamlit intelligence dashboard
2. ASGI / FastAPI / Vercel: exposes the FastAPI 'app' instance
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Detect if running under Streamlit (e.g. `streamlit run app.py` on Streamlit Cloud)
is_streamlit = (
    "streamlit" in sys.modules 
    or any("streamlit" in arg for arg in sys.argv)
    or os.environ.get("STREAMLIT_SERVER_PORT") is not None
)

if is_streamlit:
    # Run the full Streamlit literature intelligence interface
    import streamlit_app
else:
    # Standard ASGI export for FastAPI / Uvicorn / Vercel
    from main import app
    __all__ = ["app"]

    if __name__ == "__main__":
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=8000)
