import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.entities import ResearchPaper, ResearchProject
from backend.app.models.analysis_schemas import (
    StructuredPaperAnalysis,
    AnalyzePaperRequest,
    AnalyzePaperResponse
)
from backend.app.services.pdf_understanding_agent import pdf_understanding_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/understanding", tags=["PDF Understanding Agent"])

@router.post("/analyze/{paper_id}", response_model=AnalyzePaperResponse)
async def analyze_paper_endpoint(
    paper_id: str,
    req: AnalyzePaperRequest = AnalyzePaperRequest(),
    db: Session = Depends(get_db)
):
    """
    PDF Understanding Agent:
    Converts academic paper sections into 13 structured research elements:
    - Research problem, objectives, motivation, methodology, algorithms
    - Datasets, dataset size, preprocessing, evaluation metrics, experimental results
    - Limitations, future work, conclusions
    
    Preserves supporting verbatim text, document ID, and page number for every field.
    Returns 'Not Reported' if missing (never fabricates dataset sizes or results).
    Persistently caches analysis to avoid reprocessing unchanged documents.
    """
    analysis = await pdf_understanding_agent.analyze_paper(
        db=db,
        paper_id=paper_id,
        force_reanalyze=req.force_reanalyze,
        allow_llm_assist=req.allow_llm_assist
    )

    msg = "Retrieved cached structured analysis." if analysis.is_cached else "Structured analysis extracted and persistently saved."

    return AnalyzePaperResponse(
        paper_id=paper_id,
        paper_title=analysis.paper_title,
        analysis=analysis,
        message=msg
    )

@router.get("/analysis/{paper_id}", response_model=StructuredPaperAnalysis)
async def get_paper_analysis(
    paper_id: str,
    force_reanalyze: bool = Query(False, description="Force re-extraction ignoring persistent cache"),
    allow_llm_assist: bool = Query(True, description="Allow targeted Qwen3 assistance"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the structured research analysis for a paper.
    If cached in SQLite, returns instantly; otherwise executes section-aware extraction.
    """
    return await pdf_understanding_agent.analyze_paper(
        db=db,
        paper_id=paper_id,
        force_reanalyze=force_reanalyze,
        allow_llm_assist=allow_llm_assist
    )

@router.get("/project/{project_id}", response_model=List[StructuredPaperAnalysis])
async def get_project_papers_analyses(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves structured research analyses for all papers in a given project.
    """
    project = db.query(ResearchProject).filter(ResearchProject.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )

    papers = db.query(ResearchPaper).filter(
        ResearchPaper.project_id == project_id,
        ResearchPaper.processed_status == "completed"
    ).all()

    analyses = []
    for paper in papers:
        try:
            analysis = await pdf_understanding_agent.analyze_paper(
                db=db,
                paper_id=paper.id,
                force_reanalyze=False,
                allow_llm_assist=False  # Fast retrieval of existing / rule-based analyses
            )
            analyses.append(analysis)
        except Exception as e:
            logger.warning(f"Could not retrieve analysis for paper {paper.id}: {e}")

    return analyses

