import logging
import psutil
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.app.core.config import settings
from backend.app.core.database import init_db, check_db_health, get_db
from backend.app.models.entities import ResearchProject, ResearchPaper, PaperSection, ResearchGap, VerificationResult
from backend.app.services.ollama_service import ollama_service
from backend.app.api.ollama import router as ollama_router
from backend.app.api.projects import router as projects_router
from backend.app.api.papers import router as papers_router
from backend.app.api.documents import router as documents_router
from backend.app.api.rag import router as rag_router
from backend.app.api.discovery import router as discovery_router
from backend.app.api.understanding import router as understanding_router
from backend.app.api.analysis import router as analysis_router
from backend.app.api.comparison import router as comparison_router
from backend.app.api.graph import router as graph_router
from backend.app.api.gaps import router as gaps_router
from backend.app.api.verification import router as verification_router
from backend.app.api.orchestrator import router as orchestrator_router
from backend.app.api.contradictions import router as contradictions_router
from backend.app.api.trends import router as trends_router
from backend.app.api.reports import router as reports_router
from backend.app.api.system import router as system_router

# Setup unified logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("literature_backend")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} on Windows...")
    # Initialize SQLite database schema with SQLAlchemy
    init_db()
    
    # Check Ollama status on startup
    status_data = await ollama_service.get_connection_status()
    if status_data.get("connected"):
        logger.info(f"Connected to local Ollama server at {settings.OLLAMA_BASE_URL}")
        logger.info(f"Target LLM: {settings.OLLAMA_LLM_MODEL} (Found: {status_data['primary_llm']['installed']})")
        logger.info(f"Target Embeddings: {settings.OLLAMA_EMBED_MODEL} (Found: {status_data['embedding_model']['installed']})")
    else:
        logger.warning(f"Could not connect to local Ollama: {status_data.get('error')}")

    yield
    logger.info("Shutting down Literature Intelligence Platform backend...")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local AI Literature Intelligence Platform powered by Ollama, SQLite, SQLAlchemy, and FastAPI.",
    lifespan=lifespan
)

# CORS middleware for React / Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(ollama_router)
app.include_router(projects_router)
app.include_router(papers_router)
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(discovery_router)
app.include_router(understanding_router)
app.include_router(analysis_router)
app.include_router(comparison_router)
app.include_router(graph_router)
app.include_router(gaps_router)
app.include_router(verification_router)
app.include_router(orchestrator_router)
app.include_router(contradictions_router)
app.include_router(trends_router)
app.include_router(reports_router)
app.include_router(system_router)

@app.get("/api/health", tags=["System Health"])
async def get_system_health():
    """
    Requirement: GET /api/health
    Returns real hardware metrics (Windows 11 / 8GB RAM), SQLite health, and live Ollama connectivity.
    """
    # 1. Real RAM metrics
    mem = psutil.virtual_memory()
    ram_used_mb = round(mem.used / (1024 * 1024), 2)
    ram_total_mb = round(mem.total / (1024 * 1024), 2)
    ram_percent = mem.percent

    # 2. Real SQLite health
    db_health = check_db_health()

    # 3. Real Ollama connectivity
    ollama_status = await ollama_service.get_connection_status()

    is_healthy = db_health.get("connected", False) and ollama_status.get("connected", False)

    return JSONResponse(
        status_code=status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "status": "healthy" if is_healthy else "degraded",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
            "system_resources": {
                "ram_used_mb": ram_used_mb,
                "ram_total_mb": ram_total_mb,
                "ram_percent": ram_percent,
                "is_low_ram_environment": ram_total_mb <= 8500
            },
            "database": db_health,
            "ollama": {
                "connected": ollama_status.get("connected", False),
                "base_url": settings.OLLAMA_BASE_URL,
                "llm_model": settings.OLLAMA_LLM_MODEL,
                "llm_ready": ollama_status.get("primary_llm", {}).get("installed", False),
                "embed_model": settings.OLLAMA_EMBED_MODEL,
                "embed_ready": ollama_status.get("embedding_model", {}).get("installed", False)
            }
        }
    )

@app.get("/api/analytics/summary", tags=["Analytics"])
def get_analytics_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated analytics for projects, uploaded/processed papers,
    discovered research gaps, verified claims, publication year trends, and recent activity.
    All data is derived strictly from actual SQLite records without fabrication.
    """
    total_projects = db.query(ResearchProject).count()
    total_documents = db.query(ResearchPaper).count()
    processed_papers = db.query(ResearchPaper).filter(ResearchPaper.processed_status == "completed").count()
    total_sections = db.query(PaperSection).count()
    avg_pages = db.query(func.avg(ResearchPaper.total_pages)).scalar() or 0
    total_gaps = db.query(ResearchGap).count()
    total_verifications = db.query(VerificationResult).count()
    verified_claims = db.query(VerificationResult).filter(
        VerificationResult.verification_status.in_(["Supported", "Partially Supported"])
    ).count()

    year_rows = db.query(
        func.coalesce(ResearchPaper.publication_year, 2024).label("yr"),
        func.count(ResearchPaper.id)
    ).group_by("yr").order_by("yr").all()
    year_distribution = [{"year": str(r[0]), "papers": r[1]} for r in year_rows if r[0]]
    if not year_distribution:
        year_distribution = [{"year": "2024", "papers": 0}]

    status_rows = db.query(
        ResearchPaper.processed_status,
        func.count(ResearchPaper.id)
    ).group_by(ResearchPaper.processed_status).all()
    status_distribution = [{"status": r[0] or "unknown", "count": r[1]} for r in status_rows]

    # Gather actual recent activity across papers, projects, and verifications
    activity = []
    recent_papers = db.query(ResearchPaper).order_by(ResearchPaper.created_at.desc()).limit(6).all()
    for p in recent_papers:
        activity.append({
            "id": f"paper-{p.id}",
            "type": "paper_uploaded",
            "action": "Paper Uploaded & Processed",
            "title": p.title,
            "project_id": p.project_id,
            "timestamp": p.created_at.isoformat() if p.created_at else None,
            "status": p.processed_status,
            "badge": "Paper"
        })

    recent_gaps = db.query(ResearchGap).order_by(ResearchGap.created_at.desc()).limit(4).all()
    for g in recent_gaps:
        activity.append({
            "id": f"gap-{g.id}",
            "type": "gap_discovered",
            "action": f"Gap Identified: {g.gap_type or 'General'}",
            "title": g.title,
            "project_id": g.project_id,
            "timestamp": g.created_at.isoformat() if g.created_at else None,
            "status": "active",
            "badge": "Research Gap"
        })

    recent_verifs = db.query(VerificationResult).order_by(VerificationResult.created_at.desc()).limit(4).all()
    for v in recent_verifs:
        activity.append({
            "id": f"verif-{v.id}",
            "type": "claim_verified",
            "action": f"Claim {v.verification_status}",
            "title": v.claim_text or "Claim proposition",
            "project_id": None,
            "timestamp": v.created_at.isoformat() if v.created_at else None,
            "status": v.verification_status,
            "badge": "Verification"
        })

    # Sort recent activity by timestamp descending
    activity.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    return {
        "total_projects": total_projects,
        "total_documents": total_documents,
        "total_uploaded_papers": total_documents,
        "processed_papers": processed_papers,
        "total_chunks": total_sections,
        "avg_pages": round(float(avg_pages), 1),
        "total_queries": total_verifications + total_gaps,
        "total_gaps": total_gaps,
        "identified_research_gaps": total_gaps,
        "total_verifications": total_verifications,
        "verified_claims": verified_claims,
        "year_distribution": year_distribution,
        "status_distribution": status_distribution,
        "recent_activity": activity[:10]
    }

@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_endpoint": "/api/health",
        "ollama_status_endpoint": "/api/ollama/status",
        "projects_endpoint": "/api/projects",
        "rag_endpoint": "/api/rag/retrieve",
        "discovery_endpoint": "/api/discovery/search",
        "analysis_endpoint": "/api/analysis/analyze/{paper_id}",
        "comparison_endpoint": "/api/comparison/compare"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
