import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.research_analysis_schemas import (
    ResearchAnalysisRequest,
    ResearchAnalysisResponse,
    ResearchAnalysisReport
)
from backend.app.services.research_analysis_agent import research_analysis_agent

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["Research Analysis Agent"])

@router.post("/analyze/{paper_id}", response_model=ResearchAnalysisResponse)
async def analyze_individual_paper(
    paper_id: str,
    req: ResearchAnalysisRequest = ResearchAnalysisRequest(),
    db: Session = Depends(get_db)
):
    """
    Research Analysis Agent:
    Performs serialized, deep-dive academic analysis of an individual paper across 14 dimensions:
    1. Research problem
    2. Objectives
    3. Motivation
    4. Methodology
    5. Algorithms
    6. Dataset characteristics
    7. Data preprocessing
    8. Experimental setup
    9. Evaluation metrics
    10. Results
    11. Strengths
    12. Limitations
    13. Future directions
    14. Reproducibility

    - Uses PDF Understanding Agent outputs + RAG hybrid retrieval for evidence.
    - Preserves supporting verbatim text and page references for every claim.
    - Saves analysis and markdown reports persistently in SQLite.
    - Set 'regenerate=True' to force re-analysis after document corrections.
    """
    report = await research_analysis_agent.analyze_paper(
        db=db,
        paper_id=paper_id,
        regenerate=req.regenerate,
        include_markdown_report=req.include_markdown_report
    )

    msg = "Retrieved cached 14-dimension analysis report." if report.is_cached else "Completed fresh 14-dimension scientific research analysis."

    return ResearchAnalysisResponse(
        paper_id=paper_id,
        paper_title=report.paper_title,
        report=report,
        message=msg
    )

@router.get("/report/{paper_id}", response_model=ResearchAnalysisReport)
async def get_analysis_report(
    paper_id: str,
    regenerate: bool = Query(False, description="Whether to regenerate analysis after corrections"),
    db: Session = Depends(get_db)
):
    """
    Retrieves the complete 14-dimensional structured report for a research paper.
    """
    return await research_analysis_agent.analyze_paper(
        db=db,
        paper_id=paper_id,
        regenerate=regenerate
    )

@router.get("/report/{paper_id}/markdown")
async def get_analysis_markdown(
    paper_id: str,
    db: Session = Depends(get_db)
):
    """
    Returns the publication-grade Markdown analysis report for export, reading, or downstream synthesis.
    """
    report = await research_analysis_agent.analyze_paper(
        db=db,
        paper_id=paper_id,
        regenerate=False
    )
    return Response(content=report.report_markdown, media_type="text/markdown")

