from fastapi import APIRouter
import psutil
from backend.app.core.config import settings
from backend.app.core.database import get_db
from backend.app.services.ollama_service import ollama_service
from backend.app.models.schemas import SystemHealthResponse

router = APIRouter()

@router.get("/health", response_model=SystemHealthResponse)
async def check_system_health():
    # 1. System Memory Check
    mem = psutil.virtual_memory()
    ram_used_mb = round(mem.used / (1024 * 1024), 2)
    ram_total_mb = round(mem.total / (1024 * 1024), 2)
    ram_percent = mem.percent

    # 2. Ollama Status
    ollama_status = await ollama_service.check_health()

    # 3. SQLite Check
    db_connected = False
    doc_count = 0
    chunk_count = 0
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM document_chunks")
            chunk_count = cursor.fetchone()[0]
            db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "online" if db_connected else "degraded",
        "ollama_connected": ollama_status["connected"],
        "ollama_model": ollama_status["target_llm"],
        "embed_model": ollama_status["target_embed"],
        "ram_used_mb": ram_used_mb,
        "ram_total_mb": ram_total_mb,
        "ram_percent": ram_percent,
        "database_connected": db_connected,
        "total_documents": doc_count,
        "total_chunks": chunk_count
    }

