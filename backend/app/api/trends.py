import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.database import get_db
from backend.app.models.trend_schemas import ResearchTrendsResponse
from backend.app.services.trend_analysis_service import trend_analysis_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/trends",
    tags=["Research Trend Analysis"]
)

@router.get("/overview", response_model=ResearchTrendsResponse)
def get_corpus_trends(
    db: Session = Depends(get_db)
):
    """
    Analyzes literature trends across all ingested papers in SQLite:
    - Publications by year
    - Frequently used algorithms
    - Frequently used datasets
    - Research topic distribution
    - Common limitations
    - Emerging research directions
    - Underexplored areas
    All metrics derived strictly from actual project database records (no fabricated stats).
    """
    try:
        return trend_analysis_service.analyze_trends(db=db, project_id=None)
    except Exception as e:
        logger.error(f"Error computing corpus trends: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate corpus research trends: {str(e)}"
        )

@router.get("/project/{project_id}", response_model=ResearchTrendsResponse)
def get_project_trends(
    project_id: str,
    db: Session = Depends(get_db)
):
    """
    Analyzes literature trends scoped to a specific research project:
    - Project-specific publication year trends
    - Algorithm and dataset frequencies
    - Topic breakdown
    - Project limitations and open research directions
    All metrics derived strictly from actual SQLite records.
    """
    try:
        return trend_analysis_service.analyze_trends(db=db, project_id=project_id)
    except Exception as e:
        logger.error(f"Error computing project trends for '{project_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate project research trends: {str(e)}"
        )

